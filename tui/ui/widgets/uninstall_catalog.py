from __future__ import annotations

from collections.abc import Callable

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Input

from backend.models import InstalledProgram
from ui.widgets.colorable_selection_list import ColorableSelectionList


class UninstallCatalog(Vertical):
    """Filterable, multi-select list of user-installed programs to remove.

    Selection state (_selected_names) persists across filtering: filtering
    only changes which options are *rendered*, it never implicitly changes
    what's selected, even for entries currently hidden by the filter."""

    def __init__(self, on_selection_changed: Callable[[], None] | None = None, **kwargs):
        super().__init__(**kwargs)
        self._all_programs: list[InstalledProgram] = []
        self._by_name: dict[str, InstalledProgram] = {}
        self._selected_names: set[str] = set()
        self._visible_names: set[str] = set()
        self._catalog_names: set[str] = set()
        self._current_view: list[InstalledProgram] = []
        self._rebuilding = False
        self._on_selection_changed = on_selection_changed or (lambda: None)

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Filter installed programs...", id="uninstall-filter-input")
        yield ColorableSelectionList(id="uninstall-list")

    def set_programs(self, programs: list[InstalledProgram]) -> None:
        self._all_programs = programs
        self._selected_names = set()
        self._by_name = {p.name: p for p in programs}
        self._populate_options(programs)
        self._on_selection_changed()

    def filter(self, query: str) -> None:
        query = query.strip().lower()
        if not query:
            self._populate_options(self._all_programs)
        else:
            self._populate_options([p for p in self._all_programs if query in p.name.lower()])

    def reset(self) -> None:
        self._selected_names = set()
        self.query_one("#uninstall-filter-input", Input).value = ""
        self._populate_options(self._all_programs)
        self._on_selection_changed()

    def clear_selection(self) -> None:
        """Deselect everything (e.g. after Uninstall Selected finishes)
        without touching the filter text."""
        self._selected_names = set()
        self.query_one("#uninstall-list", ColorableSelectionList).deselect_all()
        self._on_selection_changed()

    def set_catalog_names(self, names: set[str]) -> None:
        """Programs (by resolved package name, lowercased) that also appear in
        the Installer's catalog are highlighted light blue, without changing
        what's currently selected or filtered."""
        self._catalog_names = {n.lower() for n in names}
        self._populate_options(self._current_view)

    def _populate_options(self, programs: list[InstalledProgram]) -> None:
        selection_list = self.query_one("#uninstall-list", ColorableSelectionList)
        self._current_view = programs
        self._rebuilding = True
        try:
            selection_list.clear_options()
            self._visible_names = {p.name for p in programs}
            for program in programs:
                label = f"{program.name} - {program.description}" if program.description else program.name
                is_in_catalog = program.name.lower() in self._catalog_names
                selection_list.add_option((label, program.name))
                selection_list.set_option_style_class(
                    program.name, "option-list--option-lightblue" if is_in_catalog else None
                )
                if program.name in self._selected_names:
                    selection_list.select(program.name)
        finally:
            self._rebuilding = False

    def on_selection_list_selected_changed(self, event: ColorableSelectionList.SelectedChanged) -> None:
        if self._rebuilding or event.selection_list.id != "uninstall-list":
            return
        checked_now = set(event.selection_list.selected)
        self._selected_names = (self._selected_names - self._visible_names) | checked_now
        self._on_selection_changed()

    @property
    def selected_programs(self) -> list[InstalledProgram]:
        return [self._by_name[name] for name in self._selected_names if name in self._by_name]
