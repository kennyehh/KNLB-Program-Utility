from __future__ import annotations

import shutil
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from backend.exec import run_command
from backend.logging_setup import SessionLogger

DEFAULT_FONT_BASE = Path.home() / ".local" / "share" / "fonts"


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
) -> FontInstallResult:
    """Download url (a font zip), extract it, refresh the font cache.
    On any failure, removes the partially-created directory, matching
    fonts_install.sh's cleanup-on-error behavior."""
    target_dir = dest_dir or default_font_dir(url)

    def log(msg: str) -> None:
        if logger:
            logger.info(msg)

    def err(msg: str) -> None:
        if logger:
            logger.error(msg)

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

    cache_result = run(["fc-cache", "-f", str(target_dir)])
    if logger:
        logger.log_command(cache_result)

    log(f"Font installed to: {target_dir}")
    return FontInstallResult(ok=True, dest_dir=target_dir, message=f"Font installed to: {target_dir}")
