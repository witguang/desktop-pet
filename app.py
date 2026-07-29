"""
应用编排层：连接 UI、定时器逻辑、数据存储与角色包系统。


引擎与具体角色解耦——换角色 = 加载另一个 characters/<id>/ 包。
"""
from __future__ import annotations

import random
import sys
import tkinter as tk
from tkinter import messagebox

from config import (
    ACTION_STILL_HOLD_MS,
    CHARACTERS_DIR,
    FLY_ANIMATION_MS,
    HOTKEY_SPAWN_FOOD,
    HOTKEY_SWITCH_CHARACTER,
    HOTKEY_TOGGLE_PANEL,
    IDLE_RANDOM_MAX_SEC,
    IDLE_RANDOM_MIN_SEC,
    IDLE_RANDOM_STATES,
    IDLE_RANDOM_STILL_HOLD_MS,
    WATER_CHECK_INTERVAL_MS,
    PetState,
)
from core.character_pack import (
    CharacterPack,
    discover_characters,
    get_character,
    get_default_character,
)
from core.hunger import HungerSystem
from core.meal_reminder import MealReminder
from core.mood import MoodSystem
from core.pet_state import PetStateMachine
from core.pomodoro import PomodoroTimer, TimerMode, TimerStatus
from core.reminder_session import ActiveReminder, ReminderKind, ReminderSession
from core.water_reminder import WaterReminder
from data.settings import Settings
from data.storage import TaskStorage
from ui.bubble import SpeechBubble
from ui.character_picker import CharacterPicker
from ui.control_panel import ControlPanel
from ui.eat_drink_settings import EatDrinkSettingsPanel
from ui.food_item import FoodItem
from ui.memo_panel import MemoPanel
from ui.pet_window import PetWindow
from ui.reminder_bar import ReminderBar
from ui.settings_panel import SettingsPanel
from ui.time_machine_panel import TimeMachinePanel
from utils.asset_loader import AssetLoader



def ensure_builtin_packs() -> None:
    """若 characters/ 下没有可用角色，自动生成内置包。"""
    packs = discover_characters()
    if packs:
        return
    from utils.pack_generator import generate_all


    generate_all()



class DesktopPetApp:
    """可换角色的桌面宠物主应用。"""


    def __init__(self, character_id: str | None = None) -> None:
        ensure_builtin_packs()


        self.settings = Settings()
        self.storage = TaskStorage()
        self.timer = PomodoroTimer()
        self.hunger = HungerSystem()
        self.mood = MoodSystem()
        self.water = WaterReminder()
        self.meal = MealReminder()
        self.reminders = ReminderSession()
        self.state_machine = PetStateMachine()
        self.apply_reminder_schedules()

        cid = character_id or self.settings.character_id
        try:
            self.character: CharacterPack = get_character(cid)
        except FileNotFoundError:
            self.character = get_default_character()
            self.settings.character_id = self.character.id

        self.root = tk.Tk()
        self.loader = AssetLoader(self.character)

        self.current_task_id: str | None = None
        self._food_items: list[FoodItem] = []
        self._temp_job: str | None = None
        self._hotkeys_enabled = False
        self._loops_started = False
        self._random_idle_job: str | None = None

        self.pet = PetWindow(
            self.root,
            self.loader,
            on_right_click=lambda _e: self.panel.toggle(),
            on_double_click=lambda _e: self.spawn_food(),
        )
        self.bubble = SpeechBubble(self.pet)
        self.reminder_bar = ReminderBar(self.pet, on_complete=self.complete_reminder)
        self.panel = ControlPanel(self)
        self.time_machine = TimeMachinePanel(self)
        self.character_picker = CharacterPicker(self)
        self.memo_panel = MemoPanel(self)
        self.settings_panel = SettingsPanel(self)
        self.eat_drink_panel = EatDrinkSettingsPanel(self)

        self.state_machine.add_listener(self._on_state_changed)
        self.timer.add_listener(self._on_timer_changed)
        self.hunger.add_listener(self._on_hunger_changed)
        self.mood.add_listener(self._on_mood_changed)
        self.water.add_listener(self._on_water_remind)
        self.meal.add_listener(self._on_meal_remind)
        self.reminders.add_start_listener(self._on_reminder_started)
        self.reminders.add_complete_listener(self._on_reminder_completed)


        self._try_register_hotkeys()
        self._schedule_loops()
        self._schedule_random_idle()

        self.root.after(
            600,
            lambda: self.bubble.show(self.character.line("greeting"), 4000),
        )


    # ------------------------------------------------------------------
    # 角色切换（热替换，无需重启）
    # ------------------------------------------------------------------
    def switch_character(self, character_id: str) -> None:
        if character_id == self.character.id:
            return
        pack = get_character(character_id)


        # 清掉屏幕上的旧食物与锁定提醒
        for item in list(self._food_items):
            item.destroy()
        self._food_items.clear()
        if self.reminders.is_locked:
            self.reminders.cancel_all()
            self.reminder_bar.hide()


        self.character = pack
        self.settings.character_id = pack.id
        self.loader.bind(pack)
        self.pet.apply_character()
        # 同步计量条对应的视觉状态（饥饿 / 低愉悦）
        if pack.uses_mood:
            self.state_machine.set_hungry(self.mood.is_low)
        else:
            self.state_machine.set_hungry(self.hunger.is_hungry)
        self.pet.set_state(self.state_machine.state)
        self.panel.on_character_changed()
        if self.character_picker.win and self.character_picker.win.winfo_exists():
            self.character_picker.refresh()
        self.bubble.show(self.character.line("character_switched"), 3500)


    def open_character_picker(self) -> None:
        self.character_picker.open()

    def open_memo(self) -> None:
        self.memo_panel.open()

    def open_main_settings(self) -> None:
        self.settings_panel.open()

    def open_eat_drink_settings(self) -> None:
        self.eat_drink_panel.open()

    def apply_reminder_schedules(self) -> None:
        """从设置加载喝水 / 用餐时刻表。"""
        self.water.set_schedule(self.settings.water_reminders)
        self.meal.set_schedule(self.settings.meal_reminders)

    def list_characters(self) -> list[CharacterPack]:
        return discover_characters()


    # ------------------------------------------------------------------
    # 热键
    # ------------------------------------------------------------------
    def _try_register_hotkeys(self) -> None:
        try:
            import keyboard  # type: ignore


            keyboard.add_hotkey(HOTKEY_SPAWN_FOOD, lambda: self.root.after(0, self.spawn_food))
            keyboard.add_hotkey(HOTKEY_TOGGLE_PANEL, lambda: self.root.after(0, self.panel.toggle))
            keyboard.add_hotkey(
                HOTKEY_SWITCH_CHARACTER,
                lambda: self.root.after(0, self.open_character_picker),
            )
            self._hotkeys_enabled = True
        except Exception:
            self._hotkeys_enabled = False


    # ------------------------------------------------------------------
    # 主循环
    # ------------------------------------------------------------------
    def _schedule_loops(self) -> None:
        if self._loops_started:
            return
        self._loops_started = True
        self.root.after(1000, self._tick_second)
        self.root.after(WATER_CHECK_INTERVAL_MS, self._tick_water)


    def _tick_second(self) -> None:
        finished = self.timer.tick()
        if finished:
            self._on_timer_finished()
        if self.character.uses_mood:
            self.mood.advance(1.0)
        else:
            self.hunger.advance(1.0)
        self.bubble.follow_pet()
        self.reminder_bar.follow_pet()
        self.root.after(1000, self._tick_second)


    def _tick_water(self) -> None:
        self.water.check()
        self.meal.check()
        self.root.after(WATER_CHECK_INTERVAL_MS, self._tick_water)

    # ------------------------------------------------------------------
    # 空闲随机动作（生动感）
    # ------------------------------------------------------------------
    def _schedule_random_idle(self) -> None:
        if self._random_idle_job:
            try:
                self.root.after_cancel(self._random_idle_job)
            except Exception:
                pass
        delay_ms = random.randint(IDLE_RANDOM_MIN_SEC, IDLE_RANDOM_MAX_SEC) * 1000
        self._random_idle_job = self.root.after(delay_ms, self._tick_random_idle)

    def _tick_random_idle(self) -> None:
        self._random_idle_job = None
        try:
            self._maybe_random_action()
        finally:
            self._schedule_random_idle()

    def _maybe_random_action(self) -> None:
        """仅在真正空闲时随机播一段动作，再回 idle。"""
        if self.reminders.is_locked:
            return
        if self._temp_job is not None:
            return
        if self.timer.is_focus_running():
            return
        # 面板打开时也允许随机；仅限基础态
        if self.state_machine.state not in (PetState.IDLE, PetState.HUNGRY):
            return

        candidates: list[str] = []
        for st in IDLE_RANDOM_STATES:
            if st in self.character.states:
                candidates.append(st)
            elif self.character.state_path(st) is not None:
                candidates.append(st)
        # 去掉当前 hungy 时再播 hungry 意义不大；drink 随机只做短动画非锁定
        if not candidates:
            return

        state = random.choice(candidates)
        anim = self.character.raw.get("animation") or {}
        if state == PetState.FLY:
            duration = int(anim.get("fly_ms", FLY_ANIMATION_MS))
        elif state == PetState.TIME_MACHINE:
            duration = int(anim.get("timemachine_ms", self.character.timemachine_animation_ms))
        elif state == PetState.DRINK:
            duration = int(anim.get("drink_ms", 2200))
        else:
            duration = int(anim.get("eat_ms", self.character.eat_animation_ms))

        # 随机动作不弹长气泡，保持轻量
        self._enter_temporary(
            state,
            duration_ms=duration,
            bubble=None,
            still_hold_ms=IDLE_RANDOM_STILL_HOLD_MS,
        )

    # ------------------------------------------------------------------
    # 状态同步
    # ------------------------------------------------------------------
    def _on_state_changed(self, _old: str, new: str) -> None:
        self.pet.set_state(new)


    def _on_timer_changed(self) -> None:
        self.state_machine.set_focusing(self.timer.is_focus_running())
        self.panel.refresh()


    def _on_hunger_changed(self, hunger: int, is_hungry: bool) -> None:
        if self.character.uses_mood:
            return
        self.state_machine.set_hungry(is_hungry)
        self.panel.refresh()
        if is_hungry and self.state_machine.state in (PetState.HUNGRY, PetState.IDLE):
            if hunger == self.hunger.threshold:
                self.bubble.show(self.character.line("hungry"), 6000)

    def _on_mood_changed(self, mood: int, is_low: bool) -> None:
        if not self.character.uses_mood:
            return
        self.state_machine.set_hungry(is_low)
        self.panel.refresh()
        if is_low and self.state_machine.state in (PetState.HUNGRY, PetState.IDLE):
            if mood == self.mood.low_threshold:
                self.bubble.show(self.character.line("hungry"), 6000)


    def _on_water_remind(self, time_str: str, period: str) -> None:
        # 锁定直到用户点击「已喝完」，不再自动闪回 idle
        self.reminders.start(
            ReminderKind.WATER,
            state=PetState.DRINK,
            message=self.character.line("water", time=time_str, period=period),
            time_str=time_str,
            period=period,
        )

    def _on_meal_remind(self, time_str: str, period: str) -> None:
        self.start_meal_reminder(time_str=time_str, period=period)

    def start_meal_reminder(self, time_str: str = "", period: str = "用餐") -> None:
        """用餐锁定提醒（可接自定义时刻表）。"""
        message = self.character.line("meal", time=time_str or "现在", period=period)
        self.reminders.start(
            ReminderKind.MEAL,
            state=PetState.EAT,
            message=message,
            time_str=time_str,
            period=period,
        )


    def debug_water_remind(self) -> None:
        self.water.force_remind("测试")


    def debug_meal_remind(self) -> None:
        self.meal.force_remind("测试")


    def complete_reminder(self) -> None:
        """确认条 / 外部调用：结束当前锁定提醒。"""
        self.reminders.complete()


    def _on_reminder_started(self, reminder: ActiveReminder) -> None:
        # 取消任何自动结束的临时动画，进入锁定态
        if self._temp_job:
            try:
                self.root.after_cancel(self._temp_job)
            except Exception:
                pass
            self._temp_job = None
        self.state_machine.enter_temporary(reminder.state)
        # duration_ms=0 → 气泡不自动消失
        self.bubble.show(reminder.message, duration_ms=0)
        self.reminder_bar.show(reminder)


    def _on_reminder_completed(self, reminder: ActiveReminder) -> None:
        self.reminder_bar.hide()
        self.bubble.hide()
        # 若队列里下一条马上 start，会再次 enter；否则回到基础态
        if not self.reminders.is_locked:
            self.state_machine.leave_temporary()
            kind_label = "喝水" if reminder.kind == ReminderKind.WATER else "用餐"
            self.bubble.show(f"好的，{kind_label}打卡完成 ✓", 2500)


    def _enter_temporary(
        self,
        state: str,
        duration_ms: int,
        bubble: str | None = None,
        *,
        still_hold_ms: int | None = None,
    ) -> None:
        """
        进入临时动作态。

        - still_hold_ms 为 None：固定 duration_ms 后离开（兼容旧逻辑）
        - still_hold_ms 有值：动作 GIF 播完并定格 PNG 后，再停留 still_hold_ms 毫秒回到 idle
        """
        # 生命提醒锁定中时，不打断锁定态（投递/时光机等延后）
        if self.reminders.is_locked:
            if bubble:
                self.bubble.show(bubble, min(duration_ms, 3000))
            return
        if self._temp_job:
            try:
                self.root.after_cancel(self._temp_job)
            except Exception:
                pass
            self._temp_job = None

        self.state_machine.enter_temporary(state)

        if still_hold_ms is not None:
            bubble_ms = max(duration_ms, still_hold_ms + 800)
            if bubble:
                self.bubble.show(bubble, bubble_ms)

            def on_settle() -> None:
                # 取消兜底定时器，改为：定格 PNG 后再停留 still_hold_ms
                if self._temp_job:
                    try:
                        self.root.after_cancel(self._temp_job)
                    except Exception:
                        pass
                self._temp_job = self.root.after(still_hold_ms, self._leave_temporary)

            # 先挂兜底（须在 set_state 之前，避免同步 settle 被覆盖）
            safety_ms = max(duration_ms, 15_000) + still_hold_ms
            self._temp_job = self.root.after(safety_ms, self._leave_temporary)
            # 覆盖 listener 的 set_state，挂上 settle 回调
            self.pet.set_state(state, on_settle=on_settle)
        else:
            if bubble:
                self.bubble.show(bubble, duration_ms)
            self._temp_job = self.root.after(duration_ms, self._leave_temporary)

    def _leave_temporary(self) -> None:
        self._temp_job = None
        if self.reminders.is_locked:
            active = self.reminders.active
            if active:
                self.state_machine.enter_temporary(active.state)
            return
        self.state_machine.leave_temporary()


    # ------------------------------------------------------------------
    # 番茄钟
    # ------------------------------------------------------------------
    def start_pomodoro(self, task_title: str, focus_minutes: int, break_minutes: int) -> None:
        if self.timer.status == TimerStatus.IDLE and self.timer.mode == TimerMode.FOCUS:
            task = self.storage.add_task(task_title)
            self.current_task_id = task["id"]
            self.timer.configure(
                focus_minutes=focus_minutes,
                break_minutes=break_minutes,
                task_title=task_title,
                task_id=task["id"],
            )
        else:
            self.timer.configure(
                focus_minutes=focus_minutes,
                break_minutes=break_minutes,
                task_title=task_title,
                task_id=self.current_task_id,
            )
        self.timer.start()
        if self.timer.mode == TimerMode.FOCUS:
            self.bubble.show(self.character.line("focus_start", task=task_title), 3000)
        else:
            self.bubble.show(self.character.line("break_start"), 3000)


    def pause_pomodoro(self) -> None:
        self.timer.pause()
        self.bubble.show(self.character.line("paused"), 2000)


    def reset_pomodoro(self) -> None:
        if self.timer.status in (TimerStatus.RUNNING, TimerStatus.PAUSED) and self.timer.elapsed_seconds > 0:
            self.storage.log_pomodoro_session(
                task_title=self.timer.task_title,
                task_id=self.timer.task_id,
                mode=self.timer.mode.value,
                planned_minutes=self.timer.planned_minutes,
                actual_seconds=self.timer.elapsed_seconds,
                completed=False,
            )
        self.timer.reset()
        self.current_task_id = None
        self.bubble.show(self.character.line("reset"), 2000)


    def _on_timer_finished(self) -> None:
        self.storage.log_pomodoro_session(
            task_title=self.timer.task_title,
            task_id=self.timer.task_id,
            mode=self.timer.mode.value,
            planned_minutes=self.timer.planned_minutes,
            actual_seconds=self.timer.elapsed_seconds,
            completed=True,
        )
        if self.timer.mode == TimerMode.FOCUS:
            self.bubble.show(self.character.line("focus_done"), 5000)
            messagebox.showinfo("番茄钟", self.character.line("focus_done"), parent=self.root)
            self.timer.switch_to_break()
        else:
            self.bubble.show(self.character.line("break_done"), 4000)
            messagebox.showinfo("番茄钟", self.character.line("break_done"), parent=self.root)
            self.timer.switch_to_focus()
        self.panel.refresh()


    def complete_current_task(self) -> None:
        if not self.current_task_id:
            messagebox.showinfo(
                "任务",
                self.character.line("no_task"),
                parent=self.panel.win or self.root,
            )
            return
        self.storage.complete_task(self.current_task_id)
        self.bubble.show(self.character.line("task_done"), 3000)


    # ------------------------------------------------------------------
    # 喂食
    # ------------------------------------------------------------------
    def spawn_food(self) -> None:
        cx, cy = self.pet.center()
        item = FoodItem(
            master=self.root,
            loader=self.loader,
            start_xy=(cx - 100, cy - 20),
            on_feed=self._on_fed,
            pet_bbox_getter=self.pet.bbox,
            transparent_color=self.character.transparent_color,
            size=self.character.food_size,
        )
        self._food_items.append(item)
        self.bubble.show(self.character.line("spawn_food"), 2500)


    # 兼容旧名
    def spawn_dorayaki(self) -> None:
        self.spawn_food()


    def _on_fed(self) -> None:
        """喂食（饥饿）或投递包裹（愉悦值）。"""
        if self.character.uses_mood:
            self.mood.deliver_package()
            # 有飞行素材：GIF → fly.png 停留 5 秒 → idle
            if "fly" in self.character.states:
                anim = self.character.raw.get("animation") or {}
                duration = int(anim.get("fly_ms", FLY_ANIMATION_MS))
                state = PetState.FLY
            else:
                duration = self.character.eat_animation_ms
                state = PetState.EAT
            self._enter_temporary(
                state,
                duration_ms=duration,
                bubble=self.character.line("eat"),
                still_hold_ms=ACTION_STILL_HOLD_MS,
            )
        else:
            self.hunger.feed()
            self._enter_temporary(
                PetState.EAT,
                duration_ms=self.character.eat_animation_ms,
                bubble=self.character.line("eat"),
            )
        self._food_items = [f for f in self._food_items if not self._is_destroyed(f)]


    @staticmethod
    def _is_destroyed(item: FoodItem) -> bool:
        try:
            return not item.win.winfo_exists()
        except tk.TclError:
            return True


    # ------------------------------------------------------------------
    # 时光机
    # ------------------------------------------------------------------
    def open_time_machine(self) -> None:
        self._enter_temporary(
            PetState.TIME_MACHINE,
            duration_ms=self.character.timemachine_animation_ms,
            bubble=self.character.line("timemachine"),
        )
        self.root.after(800, self.time_machine.open)


    # ------------------------------------------------------------------
    def quit_app(self, *, confirm: bool = True) -> None:
        """关闭退出桌宠（停止 mainloop 并清理热键等）。"""
        parent = self.root
        try:
            if self.panel.win and self.panel.win.winfo_exists():
                parent = self.panel.win
        except Exception:
            pass
        if confirm:
            if not messagebox.askyesno(
                "退出桌宠",
                "确定要关闭桌宠吗？\n关闭后需重新运行程序才会出现。",
                parent=parent,
            ):
                return
        self._cleanup()
        try:
            self.root.quit()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass

    def restart_app(self, *, delay_sec: float = 2.0) -> None:
        """
        安排：独立脚本强制结束当前进程并启动新桌宠。
        不要求用户手动关闭；taskkill 兜底，不依赖窗口能否正常退出。
        """
        from utils.updater import schedule_relaunch

        ok, msg = schedule_relaunch(delay_sec=delay_sec)
        if not ok:
            messagebox.showwarning(
                "自动重启",
                f"更新已安装，但自动重启脚本启动失败：\n{msg}\n\n"
                "可再点一次「立即更新」并保持勾选自动重启；\n"
                "或用任务管理器结束本进程后重新运行。",
                parent=self.root,
            )
            return
        # 软退出辅助；真正结束靠脚本 taskkill，用户无需再操作
        try:
            self.root.after(200, lambda: self.quit_app(confirm=False))
        except Exception:
            try:
                self.quit_app(confirm=False)
            except Exception:
                pass

    def run(self) -> None:
        self.root.mainloop()
        self._cleanup()


    def _cleanup(self) -> None:
        if self._random_idle_job:
            try:
                self.root.after_cancel(self._random_idle_job)
            except Exception:
                pass
            self._random_idle_job = None
        if self._temp_job:
            try:
                self.root.after_cancel(self._temp_job)
            except Exception:
                pass
            self._temp_job = None
        if self._hotkeys_enabled:
            try:
                import keyboard  # type: ignore

                keyboard.unhook_all_hotkeys()
            except Exception:
                pass
            self._hotkeys_enabled = False


# 向后兼容
DoraemonPetApp = DesktopPetApp


def main() -> int:
    """
    入口参数：
      --install          完整安装向导（自选安装目录 + 备忘录目录）
      --setup            强制再跑一次初始设置（仅备忘录，当前目录运行）
      --list-characters  列出角色
      --character <id>   指定角色启动
    """
    character_id = None
    args = list(sys.argv[1:])

    # 新进程启动时接管：清掉更新后残留的旧桌宠（用户无需手动结束旧进程）
    if "--install" not in args and "--list-characters" not in args:
        try:
            from utils.instance import claim_instance

            claim_instance(kill_others=True)
        except Exception:
            pass

    if "--install" in args:
        from ui.setup_wizard import SetupWizard

        ok = SetupWizard(mode="install").run()
        return 0 if ok else 1

    if "--list-characters" in args:
        ensure_builtin_packs()
        for p in discover_characters():
            desc = p.description
            if len(desc) > 40:
                desc = desc[:40] + "…"
            print(f"  {p.id:20s}  {p.name}  {desc}")
        print(f"\n角色目录: {CHARACTERS_DIR}")
        return 0

    force_setup = "--setup" in args
    from ui.setup_wizard import SetupWizard, needs_setup
    from utils.install_util import find_app_source, find_main_exe

    if force_setup or needs_setup():
        # 打包 exe 首次启动：完整安装（自选目录）；开发模式：只配备忘录
        if force_setup:
            mode = "first_run"
        elif getattr(sys, "frozen", False):
            mode = "install"
        else:
            mode = "first_run"
        wizard = SetupWizard(mode=mode)
        ok = wizard.run()
        if not ok:
            if force_setup or needs_setup():
                return 1
        elif mode == "install":
            # 已复制到新目录：从安装目录启动并退出当前进程
            installed = find_main_exe(wizard.install_dir)
            src = find_app_source()
            if (
                installed
                and installed.suffix.lower() == ".exe"
                and installed.parent.resolve() != src.resolve()
            ):
                import subprocess

                subprocess.Popen([str(installed)], cwd=str(installed.parent))
                return 0

    if "--character" in args:
        i = args.index("--character")
        if i + 1 < len(args):
            character_id = args[i + 1]
    elif args and not args[0].startswith("-") and not args[0].startswith("--"):
        character_id = args[0]

    app = DesktopPetApp(character_id=character_id)
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
