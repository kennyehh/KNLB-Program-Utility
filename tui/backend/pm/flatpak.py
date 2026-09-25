from __future__ import annotations

from backend.exec import run_command
from backend.pm import PackageManagerBackend, register

# Verified live: `flatpak search <term>` prints tab-separated columns with no
# header row: Name, Description, Application ID, Version, Branch, Remotes.
# e.g.: Firefox\tWeb Browser\torg.mozilla.firefox\t155.0\tstable\tfedora,flathub


class FlatpakBackend(PackageManagerBackend):
    name = "flatpak"

    def search_argv(self, term: str) -> list[str]:
        return ["flatpak", "search", term]

    def install_argv(self, term: str) -> list[str]:
        return ["flatpak", "install", "-y", "flathub", term]

    def search_results(self, term: str) -> list[tuple[str, str]]:
        result = run_command(self.search_argv(term))
        if not result.ok:
            return []
        results = []
        for line in result.stdout.splitlines():
            columns = line.split("\t")
            if len(columns) < 3:
                continue
            _name, description, app_id = columns[0], columns[1], columns[2]
            # The Application ID (e.g. org.mozilla.firefox) is what
            # `flatpak install` actually needs, not the display Name.
            results.append((app_id, description.strip()))
        return results

    def exact_match(self, term: str) -> tuple[str, str] | None:
        # A typed term like "firefox" won't equal the app ID
        # "org.mozilla.firefox" directly, so also match on its last segment.
        term_lower = term.lower()
        for app_id, description in self.search_results(term):
            last_segment = app_id.rsplit(".", 1)[-1].lower()
            if term_lower in (app_id.lower(), last_segment):
                return app_id, description
        return None

    def is_installed(self, term: str) -> bool:
        # Verified live: `flatpak info <app id>` exits 0 if installed, 1
        # otherwise.
        return run_command(["flatpak", "info", term]).ok


register(FlatpakBackend())
