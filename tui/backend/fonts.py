from __future__ import annotations

import os
import pwd
import shutil
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from backend.exec import run_command
from backend.logging_setup import SessionLogger


@dataclass(frozen=True)
class FontOwner:
    """The real (non-root) user who launched the app via sudo/pkexec."""

    name: str
    uid: int
    gid: int
    home: Path


def invoking_user(environ: os._Environ[str] | dict[str, str] | None = None) -> FontOwner | None:
    """The app runs as root, so Path.home() is /root. Fonts belong to the
    person who ran `sudo ./run.sh`, so look them up via SUDO_UID (or
    pkexec's PKEXEC_UID). None when not elevated from another user."""
    env = os.environ if environ is None else environ
    raw_uid = env.get("SUDO_UID") or env.get("PKEXEC_UID")
    if not raw_uid:
        return None
    try:
        uid = int(raw_uid)
        entry = pwd.getpwuid(uid)
    except (ValueError, KeyError):
        return None
    if uid == 0:
        return None
    return FontOwner(name=entry.pw_name, uid=uid, gid=entry.pw_gid, home=Path(entry.pw_dir))


def _user_home() -> Path:
    owner = invoking_user()
    return owner.home if owner else Path.home()


# Mirrors fonts_install.sh's "$HOME/.local/share/fonts", where $HOME is the
# invoking user's home, not root's.
DEFAULT_FONT_BASE = _user_home() / ".local" / "share" / "fonts"


def _basename_from_url(url: str) -> str:
    return Path(urlparse(url).path).name


def default_font_dir(url: str, base: Path = DEFAULT_FONT_BASE) -> Path:
    """Mirrors fonts_install.sh: FONT_DIR="$HOME/.local/share/fonts/$FONT_NAME"
    where FONT_NAME is basename(url) with a trailing .zip stripped."""
    name = _basename_from_url(url)
    name = name.removesuffix(".zip")
    return base / (name or "font")


def _default_downloader(url: str, dest: Path) -> None:
    urllib.request.urlretrieve(url, dest)


def _topmost_missing(path: Path) -> Path | None:
    """The highest ancestor of path (or path itself) that doesn't exist yet,
    i.e. the root of everything mkdir(parents=True) is about to create."""
    missing = None
    for candidate in (path, *path.parents):
        if candidate.exists():
            break
        missing = candidate
    return missing


def _chown_tree(root: Path, owner: FontOwner) -> None:
    os.chown(root, owner.uid, owner.gid, follow_symlinks=False)
    for dirpath, dirnames, filenames in os.walk(root):
        for name in (*dirnames, *filenames):
            os.chown(Path(dirpath) / name, owner.uid, owner.gid, follow_symlinks=False)


@dataclass(frozen=True)
class FontInstallResult:
    ok: bool
    dest_dir: Path
    message: str


def install_font_from_url(
    url: str,
    dest_dir: Path | None = None,
    logger: SessionLogger | None = None,
    *,
    downloader=_default_downloader,
    run=run_command,
    owner: FontOwner | None = None,
) -> FontInstallResult:
    """Download url (a font zip), extract it, refresh the font cache.
    On any failure, removes the partially-created directory, matching
    fonts_install.sh's cleanup-on-error behavior.

    owner defaults to the user who launched the app via sudo. Anything
    created inside their home is chowned to them (otherwise root would own
    their ~/.local/share/fonts), and fc-cache runs as them so the fonts show
    up in their own font cache rather than root's."""
    target_dir = dest_dir or default_font_dir(url)
    if owner is None:
        owner = invoking_user()

    def log(msg: str) -> None:
        if logger:
            logger.info(msg)

    def err(msg: str) -> None:
        if logger:
            logger.error(msg)

    created_root = _topmost_missing(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    zip_path = target_dir / "font.zip"

    log(f"Downloading font from {url} to {zip_path}")
    try:
        downloader(url, zip_path)
    except Exception as exc:  # noqa: BLE001 - downloader is pluggable; any failure mode must still clean up
        err(f"Failed to download font: {exc}")
        shutil.rmtree(target_dir, ignore_errors=True)
        return FontInstallResult(ok=False, dest_dir=target_dir, message=f"Download failed: {exc}")

    log(f"Extracting {zip_path} to {target_dir}")
    try:
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(target_dir)
    except (zipfile.BadZipFile, OSError) as exc:
        err(f"Failed to extract font zip: {exc}")
        shutil.rmtree(target_dir, ignore_errors=True)
        return FontInstallResult(
            ok=False, dest_dir=target_dir, message=f"Extraction failed: {exc}"
        )

    zip_path.unlink(missing_ok=True)

    if owner and target_dir.resolve().is_relative_to(owner.home.resolve()):
        chown_root = created_root if created_root is not None else target_dir
        log(f"Setting ownership of {chown_root} to {owner.name}")
        _chown_tree(chown_root, owner)

    fc_cache = ["fc-cache", "-f", str(target_dir)]
    if owner:
        fc_cache = ["runuser", "-u", owner.name, "--", *fc_cache]
    cache_result = run(fc_cache)
    if logger:
        logger.log_command(cache_result)

    log(f"Font installed to: {target_dir}")
    return FontInstallResult(ok=True, dest_dir=target_dir, message=f"Font installed to: {target_dir}")
