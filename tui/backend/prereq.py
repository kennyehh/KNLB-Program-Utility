from __future__ import annotations

import shutil
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from backend.exec import CommandResult, run_command
from backend.logging_setup import SessionLogger

_FLATHUB_URL = "https://flathub.org/repo/flathub.flatpakrepo"


class PrereqType(str, Enum):
    FLATPAK = "flatpak"
    SNAP = "snap"
    COPR = "copr"


@dataclass(frozen=True)
class PrereqSpec:
    type: PrereqType
    repo: str | None = None


def is_satisfied(spec: PrereqSpec, which=None) -> bool:
    # `which` is resolved at call time (not as a default-arg alias captured at
    # import time) so tests can monkeypatch shutil.which and have it apply
    # even when ensure() calls this without passing `which` explicitly.
    which = which or shutil.which
    if spec.type == PrereqType.FLATPAK:
        return which("flatpak") is not None
    if spec.type == PrereqType.SNAP:
        return which("snap") is not None
    if spec.type == PrereqType.COPR:
        return run_command(["dnf", "copr", "--help"]).ok
    return True


def _noop_ok() -> CommandResult:
    return CommandResult(argv=[], returncode=0, stdout="", stderr="")


def ensure(spec: PrereqSpec, logger: SessionLogger | None = None) -> CommandResult:
    """Idempotent: silently installs/enables a missing prerequisite.

    Mirrors fedora_reinstall/required_pm/install_{flatpak,snap}_PM.sh, plus
    ensuring dnf-plugins-core is present before enabling a copr repo (phase 1
    assumed it was already there).
    """

    def log_result(result: CommandResult) -> None:
        if logger:
            logger.log_command(result)

    if is_satisfied(spec):
        if logger:
            logger.info(f"Prerequisite already satisfied: {spec.type.value}")
        return _noop_ok()

    if spec.type == PrereqType.FLATPAK:
        result = run_command(["dnf", "-y", "install", "flatpak"])
        log_result(result)
        if not result.ok:
            return result
        remote_result = run_command(
            ["flatpak", "remote-add", "--if-not-exists", "flathub", _FLATHUB_URL]
        )
        log_result(remote_result)
        return remote_result

    if spec.type == PrereqType.SNAP:
        result = run_command(["dnf", "-y", "install", "snapd"])
        log_result(result)
        if not result.ok:
            return result
        socket_result = run_command(["systemctl", "enable", "--now", "snapd.socket"])
        log_result(socket_result)
        if not Path("/snap").exists():
            log_result(run_command(["ln", "-s", "/var/lib/snapd/snap", "/snap"]))
        return socket_result

    if spec.type == PrereqType.COPR:
        plugin_result = run_command(["dnf", "-y", "install", "dnf-plugins-core"])
        log_result(plugin_result)
        if not plugin_result.ok:
            return plugin_result
        if not spec.repo:
            return plugin_result
        copr_result = run_command(["dnf", "-y", "copr", "enable", spec.repo])
        log_result(copr_result)
        return copr_result

    return _noop_ok()
