from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import RichLog, Static


class SelectionPanel(Vertical):
    """Read-only, live-updating list of the programs currently selected for
    install/uninstall, showing name and description. Refreshed by the app
    whenever the paired catalog widget's selection changes."""

    def __init__(self, title: str = "Selected", **kwargs):
        super().__init__(**kwargs)
        self._title = title

    def compose(self) -> ComposeResult:
        yield Static(self._title, classes="pane-title")
        yield RichLog(id="selection-log", wrap=True, highlight=False)

    def update_selection(self, items: list[tuple[str, str]]) -> None:
        log = self.query_one("#selection-log", RichLog)
        log.clear()
        if not items:
            log.write("(none selected)")
            return
        for name, description in items:
            log.write(f"{name} - {description}" if description else name)
