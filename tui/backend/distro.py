from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

_DISTRO_PATTERN = re.compile(r"Ubuntu|Debian|Fedora|CentOS|Arch")
_PM_CANDIDATES = ("apt", "dnf", "pacman")


@dataclass(frozen=True)
class DistroInfo:
    distro_name: str
    package_manager: str
    package_manager_path: str


def detect_distro(os_release_path: str | Path = "/etc/os-release") -> str:
    """Ports: grep -Eo 'Ubuntu|Debian|Fedora|CentOS|Arch' /etc/os-release | head -n1"""
    try:
        text = Path(os_release_path).read_text()
    except OSError:
        return "Unknown"
    match = _DISTRO_PATTERN.search(text)
    return match.group(0) if match else "Unknown"


def detect_package_manager(which=shutil.which) -> tuple[str, str]:
    """Ports: command -v apt || command -v dnf || command -v pacman"""
    for candidate in _PM_CANDIDATES:
        path = which(candidate)
        if path:
            return candidate, path
    return "", ""


def get_distro_info(
    os_release_path: str | Path = "/etc/os-release", which=shutil.which
) -> DistroInfo:
    distro_name = detect_distro(os_release_path)
    pm_name, pm_path = detect_package_manager(which)
    return DistroInfo(
        distro_name=distro_name, package_manager=pm_name, package_manager_path=pm_path
    )
