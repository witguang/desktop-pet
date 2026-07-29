"""
应用编排层：连接 UI、定时器逻辑、数据存储与角色包系统。


引擎与具体角色解耦——换角色 = 加载另一个 characters/<id>/ 包。
"""
from __future__ import annotations


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
        self.reminders = ReminderSession()
        self.state_machine = PetStateMachine()

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

        self.state_machine.add_listener(self._on_state_changed)
        self.timer.add_listener(self._on_timer_changed)
        self.hunger.add_listener(self._on_hunger_changed)
        self.mood.add_listener(self._on_mood_changed)
        self.water.add_listener(self._on_water_remind)
        self.reminders.add_start_listener(self._on_reminder_started)
        self.reminders.add_complete_listener(self._on_reminder_completed)


        self._try_register_hotkeys()
        self._schedule_loops()


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
        self.root.after(WATER_CHECK_INTERVAL_MS, self._tick_water)


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
        self.start_meal_reminder(period="测试")


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
    def run(self) -> None:
        self.root.mainloop()
        self._cleanup()


    def _cleanup(self) -> None:
        if self._hotkeys_enabled:
            try:
                import keyboard  # type: ignore


                keyboard.unhook_all_hotkeys()
            except Exception:
                pass



# 向后兼容
DoraemonPetApp = DesktopPetApp



def main() -> int:
    # 支持：python main.py --character codex_spark
    character_id = None
    args = sys.argv[1:]
    if "--character" in args:
        i = args.index("--character")
        if i + 1 < len(args):
            character_id = args[i + 1]
    elif args and not args[0].startswith("-"):
        character_id = args[0]


    if "--list-characters" in args:
        ensure_builtin_packs()
        for p in discover_characters():
            print(f"  {p.id:20s}  {p.name}  ({p.description[:40]}…)" if len(p.description) > 40 else f"  {p.id:20s}  {p.name}  {p.description}")
        print(f"\n角色目录: {CHARACTERS_DIR}")
        return 0


    app = DesktopPetApp(character_id=character_id)
    app.run()
    return 0



if __name__ == "__main__":
    sys.exit(main())
