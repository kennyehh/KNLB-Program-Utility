from __future__ import annotations

import re

from backend.exec import run_command
from backend.pm import PackageManagerBackend, register

# Matches the first line of a `pacman -Ss` result pair, e.g.:
# core/nut 2.8.0-1
#     Network UPS Tools
# Format is stable/documented ("repo/pkgname version" then an indented
# description line), but unverified here since pacman isn't available on this
# (Fedora) machine to test against.
_HEADER_LINE = re.compile(r"^\S+/(\S+)\s+\S+")


class PacmanBackend(PackageManagerBackend):
    name = "pacman"

    def search_argv(self, term: str) -> list[str]:
        return ["pacman", "-Ss", term]

    def install_argv(self, term: str) -> list[str]:
        return ["pacman", "-S", "--noconfirm", term]

    def search_results(self, term: str) -> list[tuple[str, str]]:
        result = run_command(self.search_argv(term))
        if not result.ok:
            return []
        return _parse_pairs(result.stdout, _HEADER_LINE)

    def list_installed(self) -> list[tuple[str, str]]:
        # `pacman -Qei` gives detailed info blocks for explicitly-installed
        # packages only, in one call. Unverified: pacman isn't available on
        # this (Fedora) machine to test against.
        result = run_command(["pacman", "-Qei"])
        if not result.ok:
            return []
        results = []
        name = None
        description = ""
        for line in result.stdout.splitlines():
            if line.startswith("Name"):
                name = line.split(":", 1)[1].strip() if ":" in line else None
            elif line.startswith("Description"):
                description = line.split(":", 1)[1].strip() if ":" in line else ""
            elif not line.strip():
                if name:
                    results.append((name, description))
                name, description = None, ""
        if name:
            results.append((name, description))
        return results

    def uninstall_argv(self, term: str) -> list[str]:
        # -s / --recursive also removes now-unneeded dependencies.
        return ["pacman", "-R", "-s", "--noconfirm", term]

    def is_installed(self, term: str) -> bool:
        # Documented behavior: `pacman -Q <name>` exits 0 if installed, 1
        # otherwise. Unverified: pacman isn't available on this (Fedora)
        # machine to test against.
        return run_command(["pacman", "-Q", term]).ok


def _parse_pairs(stdout: str, header_pattern: re.Pattern) -> list[tuple[str, str]]:
    lines = stdout.splitlines()
    results = []
    i = 0
    while i < len(lines):
        match = header_pattern.match(lines[i])
        if match:
            name = match.group(1)
            description = lines[i + 1].strip() if i + 1 < len(lines) else ""
            results.append((name, description))
            i += 2
        else:
            i += 1
    return results


register(PacmanBackend())
