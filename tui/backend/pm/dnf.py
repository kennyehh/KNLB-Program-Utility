from __future__ import annotations

import re

from backend.exec import run_command
from backend.pm import PackageManagerBackend, register

# Matches a dnf search result line, e.g.:
#  strawberry.x86_64	Audio player and music collection organizer
# The package.arch token must contain a dot, which distinguishes result lines
# from the "Matched fields: ..." header line and blank lines.
_RESULT_LINE = re.compile(r"^\s*(\S+)\.(\S+)\s+(.+)$")


class DnfBackend(PackageManagerBackend):
    name = "dnf"

    def search_argv(self, term: str) -> list[str]:
        # `dnf search` (not `dnf list`) does a fuzzy name/summary match, so a
        # partial term like "straw" finds "strawberry" the same way the real
        # `dnf search straw` command does.
        return ["dnf", "search", term]

    def install_argv(self, term: str) -> list[str]:
        return ["dnf", "-y", "install", term]

    def search_results(self, term: str) -> list[tuple[str, str]]:
        result = run_command(self.search_argv(term))
        if not result.ok:
            return []
        results = []
        for line in result.stdout.splitlines():
            match = _RESULT_LINE.match(line)
            if match:
                pkg_name, _arch, description = match.groups()
                results.append((pkg_name, description.strip()))
        return results

    def list_installed(self) -> list[tuple[str, str]]:
        # Single local rpmdb query for every user-installed package's name and
        # summary at once, verified live (526 packages, ~instant) rather than
        # one `dnf search` per package which would be far too slow.
        result = run_command(
            ["dnf", "repoquery", "--userinstalled", "--qf", "%{name}\t%{summary}\n"]
        )
        if not result.ok:
            return []
        results = []
        for line in result.stdout.splitlines():
            if "\t" not in line:
                continue
            name, description = line.split("\t", 1)
            results.append((name.strip(), description.strip()))
        return results

    def uninstall_argv(self, term: str) -> list[str]:
        # dnf removes now-unneeded dependencies by default
        # (clean_requirements_on_remove), so this is already a "clean" removal.
        return ["dnf", "-y", "remove", term]

    def is_installed(self, term: str) -> bool:
        # Verified live: `rpm -q <name>` exits 0 if installed, 1 otherwise.
        return run_command(["rpm", "-q", term]).ok


register(DnfBackend())
