"""
单实例 / 更新接管：新进程启动时结束同目录残留的旧桌宠。

解决：旧版更新逻辑只 start 新进程却关不掉旧进程时，用户仍要手动关一次。
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from config import BASE_DIR, DATA_DIR

PID_FILE = DATA_DIR / "app.pid"
RESTART_MARKER = DATA_DIR / "_restarting.flag"


def _write_pid() -> None:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        PID_FILE.write_text(str(os.getpid()), encoding="utf-8")
    except Exception:
        pass


def _read_pid_file() -> int | None:
    try:
        if not PID_FILE.is_file():
            return None
        raw = PID_FILE.read_text(encoding="utf-8").strip()
        return int(raw) if raw.isdigit() else None
    except Exception:
        return None


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform.startswith("win"):
        try:
            # 0 信号在 Windows 上不可用；用 tasklist
            r = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                capture_output=True,
                text=True,
                timeout=8,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            out = (r.stdout or "") + (r.stderr or "")
            return str(pid) in out and "No tasks" not in out and "没有运行" not in out
        except Exception:
            return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def kill_pid(pid: int) -> bool:
    """强制结束指定 PID。"""
    if pid <= 0 or pid == os.getpid():
        return False
    try:
        if sys.platform.startswith("win"):
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/F"],
                capture_output=True,
                timeout=15,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        else:
            os.kill(pid, 9)
        return True
    except Exception:
        return False


def _kill_siblings_windows() -> int:
    """结束命令行含本安装目录 main.py / 本 exe 的其它进程。"""
    me = os.getpid()
    base = str(BASE_DIR.resolve())
    # PowerShell 单引号转义
    base_ps = base.replace("'", "''")
    exe_name = Path(sys.executable).name
    script = f"""
$me = {me}
$base = '{base_ps}'.ToLowerInvariant()
$names = @('python.exe','pythonw.exe','{exe_name}')
Get-CimInstance Win32_Process | Where-Object {{
  $_.ProcessId -ne $me -and $names -contains $_.Name
}} | ForEach-Object {{
  $cl = $_.CommandLine
  if (-not $cl) {{ return }}
  $low = $cl.ToLowerInvariant()
  $hit = $false
  if ($low.Contains($base) -and ($low.Contains('main.py') -or $low.Contains('desktoppet') -or $low.Contains('doraemon_pet'))) {{
    $hit = $true
  }}
  if (-not $hit -and $low.Contains($base) -and $_.Name -like 'DesktopPet*') {{
    $hit = $true
  }}
  if ($hit) {{
    try {{ Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop; Write-Output $_.ProcessId }} catch {{}}
  }}
}}
"""
    try:
        r = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                script,
            ],
            capture_output=True,
            text=True,
            timeout=25,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        lines = [ln.strip() for ln in (r.stdout or "").splitlines() if ln.strip().isdigit()]
        return len(lines)
    except Exception:
        return 0


def claim_instance(*, kill_others: bool = True) -> int:
    """
    声明当前为唯一实例。
    kill_others=True 时结束同目录旧桌宠（更新后新进程接管）。
    返回被结束的进程数（约数）。
    """
    killed = 0
    if kill_others:
        old = _read_pid_file()
        if old and old != os.getpid() and _pid_alive(old):
            if kill_pid(old):
                killed += 1
        if sys.platform.startswith("win"):
            killed += _kill_siblings_windows()
        # 清理重启标记
        try:
            if RESTART_MARKER.is_file():
                RESTART_MARKER.unlink(missing_ok=True)  # type: ignore[call-arg]
        except Exception:
            try:
                if RESTART_MARKER.is_file():
                    RESTART_MARKER.unlink()
            except Exception:
                pass
    _write_pid()
    return killed


def mark_restarting(old_pid: int | None = None) -> None:
    """更新前写入标记，供新进程优先清理。"""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        pid = int(old_pid if old_pid is not None else os.getpid())
        RESTART_MARKER.write_text(str(pid), encoding="utf-8")
        PID_FILE.write_text(str(pid), encoding="utf-8")
    except Exception:
        pass
