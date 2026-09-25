from __future__ import annotations

import asyncio
from pathlib import Path

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, ContentSwitcher, Input, RichLog, Static

from backend.catalog import CatalogEntry, CatalogError, load_catalog, resolve_target
from backend.critical_packages import is_critical
from backend.distro import DistroInfo
from backend.fonts import install_font_from_url
from backend.logging_setup import SessionLogger
from backend.models import InstalledProgram, InstallOutcome
from backend.pm import get_backend
from backend.prereq import ensure as ensure_prereq
from ui.banner import KNLB_ASCII
from ui.screens.confirm_uninstall_modal import ConfirmUninstallModal
from ui.widgets.font_panel import FontPanel
from ui.widgets.program_catalog import ProgramCatalog
from ui.widgets.selection_panel import SelectionPanel
from ui.widgets.uninstall_catalog import UninstallCatalog

_PANES = ("installer-pane", "uninstaller-pane", "fonts-pane")
_NAV_IDS = {
    "installer-pane": "nav-installer",
    "uninstaller-pane": "nav-uninstaller",
    "fonts-pane": "nav-fonts",
}

# The default behavior is always to search the distro's own default repos —
# never a third-party one automatically. When that search comes up empty, say
# so plainly rather than a bare "not found", since the actual next step is
# usually enabling another repo or reading the program's own install docs.
_NOT_FOUND_HINT = "you may have to add additional repos or check the installation instructions"


class KNLBApp(App):
    CSS_PATH = "app.css"
    TITLE = "KNLB Installer"

    def __init__(self, logger: SessionLogger, distro: DistroInfo):
        super().__init__()
        self.logger = logger
        self.distro = distro
        self.catalog_entries: list[CatalogEntry] = []
        self._installed_names: set[str] = set()

    def compose(self) -> ComposeResult:
        yield Static(KNLB_ASCII, id="banner")
        with Horizontal(id="nav-buttons"):
            yield Button("Installer", id="nav-installer", variant="primary")
            yield Button("Uninstaller", id="nav-uninstaller")
            yield Button("Fonts", id="nav-fonts")
        yield Static(
            f"Distro: {self.distro.distro_name}  |  "
            f"Package manager: {self.distro.package_manager or 'none detected'}",
            id="distro-info",
        )
        with ContentSwitcher(initial="installer-pane", id="content-switcher"):
            with Vertical(id="installer-pane"):
                with Horizontal(id="main-body"):
                    yield ProgramCatalog(id="program-catalog", on_selection_changed=self._refresh_install_panel)
                    yield SelectionPanel(title="Selected to install", id="install-selection-panel")
                with Horizontal(id="action-buttons"):
                    yield Button("Install Selected", id="install-selected", variant="success")
                    yield Button("Reset", id="reset-selections", variant="warning")
            with Vertical(id="uninstaller-pane"):
                with Horizontal(id="uninstall-body"):
                    yield UninstallCatalog(
                        id="uninstall-catalog", on_selection_changed=self._refresh_uninstall_panel
                    )
                    yield SelectionPanel(title="Selected to uninstall", id="uninstall-selection-panel")
                with Horizontal(id="uninstall-action-buttons"):
                    yield Button("Uninstall Selected", id="uninstall-selected", variant="error")
                    yield Button("Reset", id="reset-uninstall-selections", variant="warning")
            with Vertical(id="fonts-pane"):
                yield FontPanel(id="font-panel")
                with Horizontal(id="font-action-buttons"):
                    yield Button("Install Font", id="install-font", variant="success")
                    yield Button("Reset", id="reset-font-fields", variant="warning")
        yield RichLog(id="output-log", wrap=True, highlight=False)

    def on_mount(self) -> None:
        log = self.query_one("#output-log", RichLog)
        try:
            self.catalog_entries = load_catalog()
        except CatalogError as exc:
            self.catalog_entries = []
            log.write(f"Failed to load catalog: {exc}")

        available = [
            entry for entry in self.catalog_entries if resolve_target(entry, self.distro) is not None
        ]
        self.query_one(ProgramCatalog).set_entries(available)

        catalog_terms = set()
        for entry in available:
            target = resolve_target(entry, self.distro)
            if target:
                catalog_terms.add(target.term.lower())
        self.query_one(UninstallCatalog).set_catalog_names(catalog_terms)

        if not self.distro.package_manager:
            log.write("Warning: no supported package manager (dnf/apt/pacman) detected.")

        self._check_installed_async(available)
        self._load_uninstall_list_async()
        self.query_one("#filter-input").focus()

    @work()
    async def _check_installed_async(self, entries: list[CatalogEntry]) -> None:
        # A full rescan each time (not a merge into the existing set), so a
        # program uninstalled outside the app since the last scan correctly
        # loses its green highlight too, not just gains new ones.
        installed = set()
        for entry in entries:
            target = resolve_target(entry, self.distro)
            if target is None:
                continue
            backend = get_backend(target.package_manager)
            if await asyncio.to_thread(backend.is_installed, target.term):
                installed.add(entry.name)
        self._installed_names = installed
        self.query_one(ProgramCatalog).set_installed_names(self._installed_names)

    def on_input_changed(self, event) -> None:
        if event.input.id == "filter-input":
            self.query_one(ProgramCatalog).filter(event.value)
        elif event.input.id == "uninstall-filter-input":
            self.query_one(UninstallCatalog).filter(event.value)

    def on_input_submitted(self, event) -> None:
        if event.input.id == "manual-name-input":
            self._start_program_search()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "install-selected":
            self._start_install_selected()
        elif event.button.id == "reset-selections":
            self._reset_selections()
        elif event.button.id == "search-program-button":
            self._start_program_search()
        elif event.button.id in _NAV_IDS.values():
            pane_id = next(pane for pane, nav_id in _NAV_IDS.items() if nav_id == event.button.id)
            self._set_active_pane(pane_id)
        elif event.button.id == "uninstall-selected":
            self._start_uninstall_selected()
        elif event.button.id == "reset-uninstall-selections":
            self._reset_uninstall_selections()
        elif event.button.id == "install-font":
            self._start_font_install()
        elif event.button.id == "reset-font-fields":
            self._reset_font_fields()

    def _set_active_pane(self, pane_id: str) -> None:
        self.query_one("#content-switcher", ContentSwitcher).current = pane_id
        for pane, nav_id in _NAV_IDS.items():
            self.query_one(f"#{nav_id}", Button).variant = "primary" if pane == pane_id else "default"

    def _refresh_install_panel(self) -> None:
        catalog = self.query_one(ProgramCatalog)
        panel = self.query_one("#install-selection-panel", SelectionPanel)
        panel.update_selection([(e.name, e.description) for e in catalog.selected_entries])

    def _refresh_uninstall_panel(self) -> None:
        catalog = self.query_one(UninstallCatalog)
        panel = self.query_one("#uninstall-selection-panel", SelectionPanel)
        panel.update_selection([(p.name, p.description) for p in catalog.selected_programs])

    def _reset_selections(self) -> None:
        self.query_one(ProgramCatalog).reset()
        self.query_one("#output-log", RichLog).write("Reset program selections. Rescanning installed programs...")
        available = [
            entry for entry in self.catalog_entries if resolve_target(entry, self.distro) is not None
        ]
        self._check_installed_async(available)

    def _reset_uninstall_selections(self) -> None:
        self.query_one(UninstallCatalog).reset()
        self.query_one("#output-log", RichLog).write("Reset uninstall selections. Rescanning installed programs...")
        self._load_uninstall_list_async()

    def _reset_font_fields(self) -> None:
        self.query_one(FontPanel).reset()
        self.query_one("#output-log", RichLog).write("Reset font fields.")

    def _start_program_search(self) -> None:
        catalog_widget = self.query_one(ProgramCatalog)
        name_input = catalog_widget.query_one("#manual-name-input", Input)
        raw = name_input.value.strip()
        if not raw:
            return
        # A leading "~" requests a broad search (like running `dnf search` /
        # `apt-cache search` yourself) that lists every match, instead of the
        # default single exact-name lookup.
        if raw.startswith("~"):
            term = raw[1:].strip()
            if term:
                self._broad_search_async(term)
        else:
            self._exact_search_async(raw)

    def _make_entry(self, pm_name: str, name: str, description: str) -> CatalogEntry:
        return CatalogEntry(
            name=name,
            description=description or "Found via search",
            package_manager_override=None,
            search_terms={pm_name: name},
            prereqs=[],
        )

    @work()
    async def _exact_search_async(self, name: str) -> None:
        log = self.query_one("#output-log", RichLog)
        pm_name = self.distro.package_manager
        if not pm_name:
            log.write(f"Cannot search for {name}: no package manager detected")
            return

        backend = get_backend(pm_name)
        match = await asyncio.to_thread(backend.exact_match, name)
        if match is None:
            log.write(f"'{name}' not found — {_NOT_FOUND_HINT} (or try ~{name} to see all matches)")
            return

        matched_name, description = match
        entry = self._make_entry(pm_name, matched_name, description)
        catalog_widget = self.query_one(ProgramCatalog)
        catalog_widget.add_search_result(entry, select=True)
        if await asyncio.to_thread(backend.is_installed, matched_name):
            self._installed_names.add(matched_name)
            catalog_widget.set_installed_names(self._installed_names)
        log.write(f"Found: {entry.name} — {entry.description} (added to the list, selected)")

    @work()
    async def _broad_search_async(self, term: str) -> None:
        log = self.query_one("#output-log", RichLog)
        pm_name = self.distro.package_manager
        if not pm_name:
            log.write(f"Cannot search for {term}: no package manager detected")
            return

        backend = get_backend(pm_name)
        results = await asyncio.to_thread(backend.search_results, term)
        if not results:
            log.write(f"No matches found for '{term}' — {_NOT_FOUND_HINT}")
            return

        catalog_widget = self.query_one(ProgramCatalog)
        for matched_name, description in results:
            catalog_widget.add_search_result(self._make_entry(pm_name, matched_name, description), select=False)
            if await asyncio.to_thread(backend.is_installed, matched_name):
                self._installed_names.add(matched_name)
        catalog_widget.set_installed_names(self._installed_names)
        log.write(f"Search '{term}' found {len(results)} result(s), added to the list (not selected)")

    def _start_install_selected(self) -> None:
        catalog_widget = self.query_one(ProgramCatalog)
        log = self.query_one("#output-log", RichLog)

        selected_entries = catalog_widget.selected_entries
        if not selected_entries:
            log.write("Nothing selected to install.")
            return

        self._install_selected_async(selected_entries)

    @work()
    async def _install_selected_async(self, selected_entries: list[CatalogEntry]) -> None:
        log = self.query_one("#output-log", RichLog)
        outcomes: list[InstallOutcome] = []

        for entry in selected_entries:
            outcome = await self._install_catalog_entry(entry)
            outcomes.append(outcome)
            if outcome.ok:
                self._installed_names.add(entry.name)
            log.write(f"[{'OK' if outcome.ok else 'FAILED'}] {outcome.name}: {outcome.message}")

        self.logger.log_install_batch(outcomes)
        log.write("--- Install Selected finished ---")
        catalog_widget = self.query_one(ProgramCatalog)
        catalog_widget.clear_selection()
        catalog_widget.set_installed_names(self._installed_names)

    async def _install_catalog_entry(self, entry: CatalogEntry) -> InstallOutcome:
        target = resolve_target(entry, self.distro)
        if target is None:
            return InstallOutcome(
                name=entry.name, ok=False, message="Not available for this distro/package manager"
            )

        for prereq in target.entry.prereqs:
            prereq_result = await asyncio.to_thread(ensure_prereq, prereq, self.logger)
            if not prereq_result.ok:
                return InstallOutcome(
                    name=entry.name,
                    package_manager=target.package_manager,
                    prereq_results=[prereq_result],
                    ok=False,
                    message=f"Prerequisite failed: {prereq.type.value}",
                )

        backend = get_backend(target.package_manager)
        found = await asyncio.to_thread(backend.search, target.term)
        if not found:
            return InstallOutcome(
                name=entry.name,
                package_manager=target.package_manager,
                ok=False,
                message=f"Not found in the default repos — {_NOT_FOUND_HINT}",
            )

        install_result = await asyncio.to_thread(backend.install, target.term)
        self.logger.log_command(install_result)
        return InstallOutcome(
            name=entry.name,
            package_manager=target.package_manager,
            install_result=install_result,
            ok=install_result.ok,
            message="Installed" if install_result.ok else install_result.stderr.strip(),
        )

    def _start_font_install(self) -> None:
        font_panel = self.query_one(FontPanel)
        log = self.query_one("#output-log", RichLog)

        font_url = font_panel.url
        if not font_url:
            log.write("No font URL entered.")
            return

        custom_path_value = font_panel.custom_path
        use_custom_font_path = font_panel.use_custom_path
        self._font_install_async(font_url, custom_path_value, use_custom_font_path)

    @work()
    async def _font_install_async(self, font_url: str, custom_path_value: str, use_custom_font_path: bool) -> None:
        log = self.query_one("#output-log", RichLog)
        dest = Path(custom_path_value) if (use_custom_font_path and custom_path_value) else None
        result = await asyncio.to_thread(install_font_from_url, font_url, dest, self.logger)
        log.write(f"[{'OK' if result.ok else 'FAILED'}] font ({font_url}): {result.message}")
        self.logger.log_install_batch(
            [InstallOutcome(name=f"font: {font_url}", ok=result.ok, message=result.message)]
        )

    @work()
    async def _load_uninstall_list_async(self) -> None:
        pm_name = self.distro.package_manager
        if not pm_name:
            return

        backend = get_backend(pm_name)
        raw = await asyncio.to_thread(backend.list_installed)
        programs = sorted(
            (InstalledProgram(name, description) for name, description in raw if not is_critical(name)),
            key=lambda p: p.name.lower(),
        )
        self.query_one(UninstallCatalog).set_programs(programs)

        log = self.query_one("#output-log", RichLog)
        hidden = len(raw) - len(programs)
        suffix = f" ({hidden} critical system package(s) hidden)" if hidden else ""
        log.write(f"Uninstaller: loaded {len(programs)} user-installed program(s){suffix}")

    def _start_uninstall_selected(self) -> None:
        selected = self.query_one(UninstallCatalog).selected_programs
        log = self.query_one("#output-log", RichLog)
        if not selected:
            log.write("Nothing selected to uninstall.")
            return
        self._confirm_and_uninstall_async(selected)

    @work()
    async def _confirm_and_uninstall_async(self, programs: list[InstalledProgram]) -> None:
        log = self.query_one("#output-log", RichLog)
        names = [p.name for p in programs]
        confirmed = await self.push_screen_wait(ConfirmUninstallModal(names))
        if not confirmed:
            log.write("Uninstall cancelled.")
            return

        pm_name = self.distro.package_manager
        if not pm_name:
            log.write("Cannot uninstall: no package manager detected")
            return

        backend = get_backend(pm_name)
        outcomes: list[InstallOutcome] = []
        for program in programs:
            result = await asyncio.to_thread(backend.uninstall, program.name)
            self.logger.log_command(result)
            outcome = InstallOutcome(
                name=program.name,
                package_manager=pm_name,
                install_result=result,
                ok=result.ok,
                message="Uninstalled" if result.ok else result.stderr.strip(),
            )
            outcomes.append(outcome)
            if outcome.ok:
                self._installed_names.discard(program.name)
            log.write(f"[{'OK' if outcome.ok else 'FAILED'}] {outcome.name}: {outcome.message}")

        self.logger.log_install_batch(outcomes)
        log.write("--- Uninstall Selected finished ---")
        self.query_one(UninstallCatalog).clear_selection()
        self.query_one(ProgramCatalog).set_installed_names(self._installed_names)
        self._load_uninstall_list_async()
