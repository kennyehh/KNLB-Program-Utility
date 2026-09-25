from __future__ import annotations

import re

from backend.exec import run_command
from backend.pm import PackageManagerBackend, register

# Verified live: `snap find <term>` prints a header line ("Name  Version
# Publisher  Notes  Summary") then space-aligned columns, e.g.:
# firefox   156.0.1-1   mozilla**   -   Mozilla Firefox web browser
_COLUMN_SPLIT = re.compile(r"\s{2,}")


class SnapBackend(PackageManagerBackend):
    name = "snap"

    def search_argv(self, term: str) -> list[str]:
        return ["snap", "find", term]

    def install_argv(self, term: str) -> list[str]:
        return ["snap", "install", term]

    def search_results(self, term: str) -> list[tuple[str, str]]:
        result = run_command(self.search_argv(term))
        if not result.ok:
            return []
        lines = result.stdout.splitlines()[1:]  # skip the header row
        results = []
        for line in lines:
            if not line.strip():
                continue
            columns = _COLUMN_SPLIT.split(line.strip(), maxsplit=4)
            if len(columns) < 5:
                continue
            name, summary = columns[0], columns[4]
            results.append((name, summary.strip()))
        return results

    def is_installed(self, term: str) -> bool:
        # Verified live: `snap list <name>` exits 0 if installed, 1 otherwise.
        return run_command(["snap", "list", term]).ok


register(SnapBackend())
