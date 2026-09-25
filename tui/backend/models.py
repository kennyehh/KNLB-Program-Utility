from __future__ import annotations

from dataclasses import dataclass, field

from backend.exec import CommandResult


@dataclass
class InstallOutcome:
    name: str
    package_manager: str = ""
    prereq_results: list[CommandResult] = field(default_factory=list)
    install_result: CommandResult | None = None
    ok: bool = False
    message: str = ""


@dataclass(frozen=True)
class InstalledProgram:
    """A single user-installed program offered on the uninstaller page."""

    name: str
    description: str
