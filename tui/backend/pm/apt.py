from __future__ import annotations

import re

from backend.exec import run_command
from backend.pm import PackageManagerBackend, register

# Matches an `apt-cache search` result line, e.g.:
# nut - Network UPS Tools - core system
# Format is stable/documented ("pkgname - description"), but unverified here
# since apt-cache isn't available on this (Fedora) machine to test against.
_RESULT_LINE = re.compile(r"^(\S+)\s+-\s+(.+)$")


class AptBackend(PackageManagerBackend):
    name = "apt"

    def search_argv(self, term: str) -> list[str]:
        return ["apt-cache", "search", term]

    def install_argv(self, term: str) -> list[str]:
        return ["apt-get", "-y", "install", term]

    def search_results(self, term: str) -> list[tuple[str, str]]:
        result = run_command(self.search_argv(term))
        if not result.ok:
            return []
        results = []
        for line in result.stdout.splitlines():
            match = _RESULT_LINE.match(line)
            if match:
                results.append((match.group(1), match.group(2).strip()))
        return results

    def list_installed(self) -> list[tuple[str, str]]:
        # `apt-mark showmanual` lists names only; batch every name through a
        # single dpkg-query call (rather than one apt-cache call per package)
        # to get name+summary in as few subprocess calls as possible.
        # Unverified: neither apt-mark nor dpkg-query is available on this
        # (Fedora) machine to test against.
        names_result = run_command(["apt-mark", "showmanual"])
        if not names_result.ok:
            return []
        names = [n.strip() for n in names_result.stdout.splitlines() if n.strip()]
        if not names:
            return []

        desc_result = run_command(
            ["dpkg-query", "-W", "-f=${Package}\t${binary:Summary}\n", *names]
        )
        descriptions: dict[str, str] = {}
        if desc_result.ok:
            for line in desc_result.stdout.splitlines():
                if "\t" in line:
                    pkg, desc = line.split("\t", 1)
                    descriptions[pkg.strip()] = desc.strip()
        return [(name, descriptions.get(name, "")) for name in names]

    def uninstall_argv(self, term: str) -> list[str]:
        return ["apt-get", "-y", "remove", "--autoremove", term]

    def is_installed(self, term: str) -> bool:
        # Documented behavior: `dpkg -s <name>` exits 0 if installed, non-zero
        # otherwise. Unverified live: dpkg on this (Fedora) machine has no real
        # package database to check against.
        return run_command(["dpkg", "-s", term]).ok


register(AptBackend())
