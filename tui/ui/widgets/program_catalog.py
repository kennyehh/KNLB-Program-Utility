from __future__ import annotations

from collections.abc import Callable

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Input

from backend.catalog import CatalogEntry
from ui.widgets.colorable_selection_list import ColorableSelectionList


class ProgramCatalog(Vertical):
    """Filterable, multi-select list of catalog programs, plus a search box
    for looking up an arbitrary program name. A found program is added to the
    list as a normal selectable item rather than being queued for install
    automatically. Distro-agnostic: the app decides which entries are
    available/found and passes them in via set_entries/add_search_result.

    Selection state (_selected_names) persists across filtering: filtering
    only changes which options are *rendered*, it never implicitly changes
    what's selected, even for entries currently hidden by the filter."""

    def __init__(self, on_selection_changed: Callable[[], None] | None = None, **kwargs):
        super().__init__(**kwargs)
        self._base_entries: list[CatalogEntry] = []
        self._extra_entries: list[CatalogEntry] = []
        self._entries_by_name: dict[str, CatalogEntry] = {}
        self._selected_names: set[str] = set()
        self._visible_names: set[str] = set()
        self._installed_names: set[str] = set()
        self._current_view: list[CatalogEntry] = []
        self._rebuilding = False
        self._on_selection_changed = on_selection_changed or (lambda: None)

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Filter programs...", id="filter-input")
        yield ColorableSelectionList(id="program-list")
        with Horizontal(id="search-row"):
            yield Input(
                placeholder="Program name to add, or ~name to search all matches",
                id="manual-name-input",
            )
            yield Button("Search", id="search-program-button")

    def set_entries(self, entries: list[CatalogEntry]) -> None:
        self._base_entries = entries
        self._extra_entries = []
        self._selected_names = set()
        self._installed_names = set()
        self._rebuild_entries_by_name()
        self._populate_options(self._base_entries)
        self._on_selection_changed()

    def set_installed_names(self, names: set[str]) -> None:
        """Refresh which entries should be shown as already-installed
        (green), without changing what's currently selected or filtered."""
        self._installed_names = set(names)
        self._populate_options(self._current_view)

    def filter(self, query: str) -> None:
        query = query.strip().lower()
        combined = self._base_entries + self._extra_entries
        if not query:
            self._populate_options(combined)
        else:
            self._populate_options([e for e in combined if query in e.name.lower()])

    def add_search_result(self, entry: CatalogEntry, select: bool = True) -> None:
        """Add a found-via-search program to the list, leaving the choice of
        whether to actually install it to the user. A single exact-match
        result is pre-selected; broad-search results are added unselected
        since it's ambiguous which of several matches the user wants."""
        self._extra_entries = [e for e in self._extra_entries if e.name != entry.name]
        self._extra_entries.append(entry)
        self._rebuild_entries_by_name()
        if select:
            self._selected_names.add(entry.name)
        self._populate_options(self._base_entries + self._extra_entries)
        self._on_selection_changed()

    def reset(self) -> None:
        """Clear all selections, drop any ad hoc search results, and clear
        the filter/search inputs."""
        self._extra_entries = []
        self._selected_names = set()
        self._rebuild_entries_by_name()
        self.query_one("#filter-input", Input).value = ""
        self.query_one("#manual-name-input", Input).value = ""
        self._populate_options(self._base_entries)
        self._on_selection_changed()

    def clear_selection(self) -> None:
        """Deselect everything (e.g. after Install Selected finishes) without
        touching the filter text or ad hoc search results."""
        self._selected_names = set()
        self.query_one("#program-list", ColorableSelectionList).deselect_all()
        self._on_selection_changed()

    def _rebuild_entries_by_name(self) -> None:
        self._entries_by_name = {e.name: e for e in self._base_entries + self._extra_entries}

    def _populate_options(self, entries: list[CatalogEntry]) -> None:
        selection_list = self.query_one("#program-list", ColorableSelectionList)
        self._current_view = entries
        self._rebuilding = True
        try:
            selection_list.clear_options()
            self._visible_names = {e.name for e in entries}
            for entry in entries:
                label = f"{entry.name} - {entry.description}" if entry.description else entry.name
                # CatalogEntry contains a dict/list, which is unhashable, so
                # SelectionList (which hashes option values) gets the name instead.
                selection_list.add_option((label, entry.name))
                selection_list.set_option_style_class(
                    entry.name, "option-list--option-green" if entry.name in self._installed_names else None
                )
                if entry.name in self._selected_names:
                    selection_list.select(entry.name)
        finally:
            self._rebuilding = False

    def on_selection_list_selected_changed(self, event: ColorableSelectionList.SelectedChanged) -> None:
        if self._rebuilding or event.selection_list.id != "program-list":
            return
        # Only the currently-visible portion of the selection can have
        # genuinely changed (hidden/filtered-out items aren't touchable), so
        # merge the freshly-checked visible set back into the persistent one
        # rather than replacing it wholesale.
        checked_now = set(event.selection_list.selected)
        self._selected_names = (self._selected_names - self._visible_names) | checked_now
        self._on_selection_changed()

    @property
    def selected_entries(self) -> list[CatalogEntry]:
        return [self._entries_by_name[name] for name in self._selected_names if name in self._entries_by_name]
