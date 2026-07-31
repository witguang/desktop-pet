"""
从 GitHub 检查 / 下载更新（支持 gh-proxy 加速）。

默认拉取 main 分支 archive zip，覆盖应用代码，保留 data_store 用户数据。
"""
from __future__ import annotations

import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from config import BASE_DIR, DATA_DIR, RESOURCE_DIR

# 内置代理前缀（末尾建议带 /）
BUILTIN_GH_PROXIES: list[str] = [
    "https://gh-proxy.org/",
    "https://v4.gh-proxy.org/",
    "https://v6.gh-proxy.org/",
    "https://cdn.gh-proxy.org/",
]

DEFAULT_GITHUB_REPO = "witguang/desktop-pet"
DEFAULT_GITHUB_BRANCH = "main"

# 更新时跳过（不覆盖）的相对路径前缀/文件
_SKIP_PREFIXES = (
    "data_store/",
    "data_store\\",
    "__pycache__/",
    ".git/",
)
_SKIP_NAMES = {".git", "__pycache__", "data_store", ".memo_history"}

ProgressCb = Callable[[str], None]


@dataclass
class UpdateInfo:
    local_version: str
    remote_version: str
    repo: str
    branch: str
    has_update: bool
    message: str
    used_proxy: str = ""


def read_local_version(base: Path | None = None) -> str:
    candidates = []
    if base is not None:
        candidates.append(Path(base))
    candidates.extend([BASE_DIR, RESOURCE_DIR])
    seen: set[str] = set()
    for root in candidates:
        key = str(root)
        if key in seen:
            continue
        seen.add(key)
        for rel in ("VERSION", "packaging/VERSION"):
            path = root / rel
            if path.is_file():
                return path.read_text(encoding="utf-8").strip() or "0.0.0"
    return "0.0.0"


def normalize_proxy(proxy: str) -> str:
    p = (proxy or "").strip()
    if not p:
        return ""
    if not p.endswith("/"):
        p += "/"
    return p


def build_proxied_url(url: str, proxy: str) -> str:
    """把 https://github.com/... 包一层代理。空代理 = 直连。"""
    proxy = normalize_proxy(proxy)
    if not proxy:
        return url
    # 代理站通常要完整 URL 跟在后面
    if url.startswith(proxy):
        return url
    return proxy + url


def _http_get(url: str, timeout: float = 25.0) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "DesktopPet-Updater/1.0",
            "Accept": "*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _try_get(urls: list[str], timeout: float = 25.0) -> tuple[bytes, str]:
    errors: list[str] = []
    for url in urls:
        try:
            data = _http_get(url, timeout=timeout)
            return data, url
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{url}: {exc}")
    raise RuntimeError("全部下载源失败:\n" + "\n".join(errors[:6]))


def parse_repo(repo: str) -> tuple[str, str]:
    repo = (repo or "").strip().removeprefix("https://github.com/").removesuffix(".git").strip("/")
    parts = repo.split("/")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(f"仓库格式应为 owner/name，当前: {repo}")
    return parts[0], parts[1]


def version_tuple(v: str) -> tuple[int, ...]:
    nums = re.findall(r"\d+", v or "0")
    if not nums:
        return (0,)
    return tuple(int(x) for x in nums)


def is_newer(remote: str, local: str) -> bool:
    return version_tuple(remote) > version_tuple(local)


def candidate_urls(raw_url: str, proxies: list[str]) -> list[str]:
    """直连 + 各代理。proxies 含空字符串表示直连。"""
    urls: list[str] = []
    seen: set[str] = set()
    ordered = list(proxies)
    if "" not in ordered:
        ordered = [""] + ordered
    for p in ordered:
        u = build_proxied_url(raw_url, p) if p else raw_url
        if u not in seen:
            seen.add(u)
            urls.append(u)
    return urls


def fetch_remote_version(
    repo: str = DEFAULT_GITHUB_REPO,
    branch: str = DEFAULT_GITHUB_BRANCH,
    proxies: list[str] | None = None,
) -> tuple[str, str]:
    """返回 (version, used_url)。优先 packaging/VERSION，兼容旧根目录 VERSION。"""
    owner, name = parse_repo(repo)
    proxy_list = proxies if proxies is not None else [""] + BUILTIN_GH_PROXIES
    paths = (
        f"https://raw.githubusercontent.com/{owner}/{name}/{branch}/packaging/VERSION",
        f"https://raw.githubusercontent.com/{owner}/{name}/{branch}/VERSION",
    )
    last_err: Exception | None = None
    for raw in paths:
        try:
            data, used = _try_get(candidate_urls(raw, proxy_list))
            text = data.decode("utf-8", errors="replace").strip()
            first_line = text.splitlines()[0].strip() if text else "0.0.0"
            if first_line.startswith("<"):
                raise RuntimeError("获取 VERSION 失败：返回了网页而非版本文件")
            return first_line, used
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            continue
    raise RuntimeError(f"无法获取远程版本: {last_err}")


def check_update(
    repo: str = DEFAULT_GITHUB_REPO,
    branch: str = DEFAULT_GITHUB_BRANCH,
    proxies: list[str] | None = None,
    base: Path | None = None,
) -> UpdateInfo:
    local = read_local_version(base)
    try:
        remote, used = fetch_remote_version(repo, branch, proxies)
        newer = is_newer(remote, local)
        return UpdateInfo(
            local_version=local,
            remote_version=remote,
            repo=repo,
            branch=branch,
            has_update=newer,
            message=("发现新版本" if newer else "已是最新版本"),
            used_proxy=used,
        )
    except Exception as exc:  # noqa: BLE001
        return UpdateInfo(
            local_version=local,
            remote_version="?",
            repo=repo,
            branch=branch,
            has_update=False,
            message=f"检查失败: {exc}",
            used_proxy="",
        )


def _should_skip(rel: str) -> bool:
    rel_norm = rel.replace("\\", "/")
    if any(rel_norm.startswith(p.replace("\\", "/")) for p in _SKIP_PREFIXES):
        return True
    parts = Path(rel_norm).parts
    if parts and parts[0] in _SKIP_NAMES:
        return True
    if "__pycache__" in parts:
        return True
    if parts and parts[-1].endswith(".pyc"):
        return True
    return False


def apply_zip_update(
    zip_bytes: bytes,
    target: Path,
    progress: ProgressCb | None = None,
) -> int:
    """
    解压 GitHub archive zip 到 target。
    GitHub zip 根目录通常是 repo-branch/。
    返回写入文件数。
    """
    log = progress or (lambda _m: None)
    target = target.resolve()
    count = 0
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = zf.namelist()
        if not names:
            raise RuntimeError("更新包为空")
        # 根前缀 repo-main/
        root_prefix = names[0].split("/")[0] + "/"
        for info in zf.infolist():
            name = info.filename
            if name.endswith("/"):
                continue
            if name.startswith(root_prefix):
                rel = name[len(root_prefix) :]
            else:
                rel = name
            if not rel or _should_skip(rel):
                continue
            # 拒绝绝对路径与 .. 穿越
            rel_path = Path(rel)
            if rel_path.is_absolute() or ".." in rel_path.parts:
                continue
            dest = (target / rel_path).resolve()
            # 路径穿越防护：禁止 prefix 误判（如 C:\App vs C:\AppEvil）
            try:
                dest.relative_to(target)
            except ValueError:
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(dest, "wb") as out:
                shutil.copyfileobj(src, out)
            count += 1
            if count % 40 == 0:
                log(f"已写入 {count} 个文件…")
    log(f"更新完成，共写入 {count} 个文件")
    return count


def resolve_relaunch_command() -> tuple[list[str], Path]:
    """
    返回 (命令行, 工作目录)，用于重新启动当前桌宠。
    打包 exe：直接启动自身；开发模式：python packaging/entry_main.py。
    """
    if getattr(sys, "frozen", False):
        exe = Path(sys.executable).resolve()
        return [str(exe)], exe.parent

    here = Path(__file__).resolve()
    if here.parent.name == "utils" and here.parent.parent.name == "src":
        root = here.parent.parent.parent
    else:
        root = here.parent.parent
    entry = root / "packaging" / "entry_main.py"
    if not entry.is_file():
        # 兼容旧布局
        entry = root / "main.py"
    if not entry.is_file():
        entry = BASE_DIR / "packaging" / "entry_main.py"
    python = Path(sys.executable).resolve()
    return [str(python), str(entry)], root if entry.name == "entry_main.py" else entry.parent


def read_auto_restart_preference() -> bool:
    """从 data_store/settings.json 读取是否自动重启；缺省 True。"""
    try:
        path = DATA_DIR / "settings.json"
        if not path.is_file():
            return True
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return True
        if "auto_restart_after_update" not in data:
            return True
        return bool(data.get("auto_restart_after_update"))
    except Exception:
        return True


def schedule_relaunch(
    *,
    delay_sec: float = 2.0,
    kill_pid: int | None = None,
) -> tuple[bool, str]:
    """
    写独立脚本：延迟 → 强制结束旧进程 → 启动新桌宠。
    不依赖当前 Tk 能否正常 quit，解决「无退出按钮 / 关不掉 / 需手动关闭」问题。
    脚本与当前进程分离，即使本进程卡死也会被 taskkill 掉。
    """
    cmd, cwd = resolve_relaunch_command()
    cwd = Path(cwd)
    if not cwd.is_dir():
        return False, f"工作目录不存在: {cwd}"

    delay = max(1.0, float(delay_sec))
    pid = int(kill_pid if kill_pid is not None else os.getpid())

    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        # 供新进程 claim_instance 二次清理
        try:
            from utils.instance import mark_restarting

            mark_restarting(pid)
        except Exception:
            pass

        if sys.platform.startswith("win"):
            helper = DATA_DIR / "_auto_restart.cmd"
            # ping -n N ≈ N-1 秒
            n = max(2, int(delay) + 1)
            # 每段参数单独加引号，避免路径空格
            start_parts = " ".join(f'"{part}"' for part in cmd)
            # 先杀旧再启新：不依赖用户点退出 / 关窗
            lines = [
                "@echo off",
                f"ping -n {n} 127.0.0.1 >nul",
                f"taskkill /PID {pid} /F >nul 2>&1",
                f"taskkill /PID {pid} /T /F >nul 2>&1",
                "ping -n 2 127.0.0.1 >nul",
                f'cd /d "{cwd}"',
                f'start "" {start_parts}',
                'del "%~f0" >nul 2>&1',
            ]
            helper.write_text("\r\n".join(lines) + "\r\n", encoding="gbk", errors="replace")

            creationflags = 0
            if hasattr(subprocess, "DETACHED_PROCESS"):
                creationflags |= subprocess.DETACHED_PROCESS  # type: ignore[attr-defined]
            if hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
                creationflags |= subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
            if hasattr(subprocess, "CREATE_NO_WINDOW"):
                creationflags |= subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]

            subprocess.Popen(
                ["cmd.exe", "/c", str(helper)],
                cwd=str(cwd),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
                creationflags=creationflags,
            )
        else:
            helper = DATA_DIR / "_auto_restart.sh"
            script = (
                "#!/bin/sh\n"
                f"sleep {delay}\n"
                f"kill -9 {pid} 2>/dev/null || true\n"
                f"sleep 0.5\n"
                f"cd {shlex_quote(str(cwd))}\n"
                + " ".join(shlex_quote(c) for c in cmd)
                + " &\n"
                f"rm -f {shlex_quote(str(helper))}\n"
            )
            helper.write_text(script, encoding="utf-8")
            helper.chmod(0o755)
            subprocess.Popen(
                ["/bin/sh", str(helper)],
                cwd=str(cwd),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        return True, f"已安排约 {delay:.0f}s 后自动结束旧进程并启动新桌宠 (PID={pid})"
    except Exception as exc:  # noqa: BLE001
        return False, f"安排重启失败: {exc}"


def shlex_quote(s: str) -> str:
    """Minimal shell quote without importing shlex on odd platforms first."""
    try:
        import shlex

        return shlex.quote(s)
    except Exception:
        return "'" + s.replace("'", "'\"'\"'") + "'"


def download_and_apply(
    repo: str = DEFAULT_GITHUB_REPO,
    branch: str = DEFAULT_GITHUB_BRANCH,
    proxies: list[str] | None = None,
    target: Path | None = None,
    progress: ProgressCb | None = None,
    auto_restart: bool | None = None,
    *,
    allow_downgrade: bool = False,
    restart_delay_sec: float = 3.0,
) -> str:
    """
    下载 zip 并覆盖安装。返回使用的下载 URL。

    auto_restart:
      - None: 读设置 auto_restart_after_update（默认 True）
      - True/False: 强制指定
    为 True 时，安装完成后立刻安排「结束旧进程 + 启动新桌宠」，
    用户无需手动关闭。

    allow_downgrade=False 时，若远程 VERSION 不高于本地则拒绝覆盖，
    避免把已修好的自动重启等功能又降回旧版。
    """
    owner, name = parse_repo(repo)
    proxy_list = proxies if proxies is not None else [""] + BUILTIN_GH_PROXIES
    log = progress or (lambda _m: None)

    dest = target or BASE_DIR
    local_ver = read_local_version(dest)
    try:
        remote_ver, _ver_url = fetch_remote_version(repo, branch, proxy_list)
    except Exception as exc:  # noqa: BLE001
        remote_ver = ""
        log(f"预读远程版本失败（仍将尝试下载包）: {exc}")

    if remote_ver and not allow_downgrade:
        if not is_newer(remote_ver, local_ver):
            if version_tuple(remote_ver) == version_tuple(local_ver):
                raise RuntimeError(
                    f"远程与本地版本相同（{local_ver}），无需更新。\n"
                    "若只想重装，请勾选强制安装后再试（开发用途）。"
                )
            raise RuntimeError(
                f"远程版本 {remote_ver} 不高于本地 {local_ver}，已取消覆盖，"
                "以免降级丢失「更新后自动重启」等功能。\n"
                "请先把新版本推送到 GitHub，或等待远程发布更新。"
            )

    zip_url = f"https://github.com/{owner}/{name}/archive/refs/heads/{branch}.zip"
    log("正在下载更新包…")
    data, used = _try_get(candidate_urls(zip_url, proxy_list), timeout=60.0)
    log(f"下载完成（{len(data) // 1024} KB），正在安装…")
    apply_zip_update(data, dest, progress=log)

    # 打包版：代码在 RESOURCE_DIR（_internal），尽量同步一份
    try:
        if (
            getattr(sys, "frozen", False)
            and RESOURCE_DIR.resolve() != Path(dest).resolve()
            and RESOURCE_DIR.is_dir()
        ):
            log("同步更新到运行时资源目录…")
            apply_zip_update(data, RESOURCE_DIR, progress=log)
    except Exception as exc:  # noqa: BLE001
        log(f"资源目录同步跳过: {exc}")

    # 默认自动重启。打包版强制自动重启：旧 UI 无勾选项时也要能直接起来。
    if auto_restart is None:
        do_restart = True if getattr(sys, "frozen", False) else read_auto_restart_preference()
    else:
        do_restart = bool(auto_restart)
    if getattr(sys, "frozen", False):
        do_restart = True

    if do_restart:
        ok, msg = schedule_relaunch(
            delay_sec=restart_delay_sec,
            kill_pid=os.getpid(),
        )
        log(msg if ok else f"自动重启未成功: {msg}")
        if not ok:
            log("自动重启脚本失败：将尝试直接拉起新进程。")
            # 最后兜底：直接 start 新实例（新进程 claim_instance 会清旧进程）
            try:
                cmd, cwd = resolve_relaunch_command()
                subprocess.Popen(
                    cmd,
                    cwd=str(cwd),
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    close_fds=True,
                    creationflags=(
                        getattr(subprocess, "DETACHED_PROCESS", 0)
                        | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                        | getattr(subprocess, "CREATE_NO_WINDOW", 0)
                    )
                    if sys.platform.startswith("win")
                    else 0,
                )
                log("已直接启动新实例（接管旧进程）。")
            except Exception as exc:  # noqa: BLE001
                log(f"兜底启动失败: {exc}")
    else:
        log("已关闭「更新后自动重启」：请点控制面板「退出桌宠」后再打开。")
    return used


def proxy_chain_from_settings(
    preferred: str,
    custom_list: list[str],
    *,
    include_direct: bool = True,
) -> list[str]:
    """
    生成尝试顺序：首选 → 自定义 → 内置 → 直连。
    列表元素为代理前缀；空串表示直连。
    """
    chain: list[str] = []
    seen: set[str] = set()

    def add(p: str) -> None:
        key = normalize_proxy(p) if p else ""
        if key in seen:
            return
        # 允许空直连
        if p == "" or key:
            seen.add(key)
            chain.append(key if p else "")

    pref = (preferred or "").strip()
    if pref.lower() in ("direct", "none", "直连", "(direct)", "(直连)"):
        add("")
    elif pref:
        add(pref)

    for c in custom_list:
        if c and c.strip():
            add(c.strip())

    for b in BUILTIN_GH_PROXIES:
        add(b)

    if include_direct:
        add("")

    return chain
