"""
从 GitHub 检查 / 下载更新（支持 gh-proxy 加速）。

默认拉取 main 分支 archive zip，覆盖应用代码，保留 data_store 用户数据。
"""
from __future__ import annotations

import io
import json
import re
import shutil
import tempfile
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from config import BASE_DIR, RESOURCE_DIR

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
        path = root / "VERSION"
        if path.exists():
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
    """返回 (version, used_url)。"""
    owner, name = parse_repo(repo)
    raw = f"https://raw.githubusercontent.com/{owner}/{name}/{branch}/VERSION"
    proxy_list = proxies if proxies is not None else [""] + BUILTIN_GH_PROXIES
    data, used = _try_get(candidate_urls(raw, proxy_list))
    text = data.decode("utf-8", errors="replace").strip()
    # 去掉可能的 HTML 噪声
    first_line = text.splitlines()[0].strip() if text else "0.0.0"
    if first_line.startswith("<"):
        raise RuntimeError("获取 VERSION 失败：返回了网页而非版本文件")
    return first_line, used


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
            dest = (target / rel).resolve()
            # 路径穿越防护
            if not str(dest).startswith(str(target)):
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(dest, "wb") as out:
                shutil.copyfileobj(src, out)
            count += 1
            if count % 40 == 0:
                log(f"已写入 {count} 个文件…")
    log(f"更新完成，共写入 {count} 个文件")
    return count


def download_and_apply(
    repo: str = DEFAULT_GITHUB_REPO,
    branch: str = DEFAULT_GITHUB_BRANCH,
    proxies: list[str] | None = None,
    target: Path | None = None,
    progress: ProgressCb | None = None,
) -> str:
    """下载 zip 并覆盖安装。返回使用的下载 URL。"""
    owner, name = parse_repo(repo)
    zip_url = f"https://github.com/{owner}/{name}/archive/refs/heads/{branch}.zip"
    proxy_list = proxies if proxies is not None else [""] + BUILTIN_GH_PROXIES
    log = progress or (lambda _m: None)
    log("正在下载更新包…")
    data, used = _try_get(candidate_urls(zip_url, proxy_list), timeout=60.0)
    log(f"下载完成（{len(data) // 1024} KB），正在安装…")
    apply_zip_update(data, target or BASE_DIR, progress=log)
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
