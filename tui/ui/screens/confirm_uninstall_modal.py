from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static


class ConfirmUninstallModal(ModalScreen[bool]):
    """Confirms the exact set of programs before an uninstall actually runs."""

    def __init__(self, names: list[str]):
        super().__init__()
        self.names = names

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-modal"):
            yield Static(f"Uninstall {len(self.names)} program(s)?")
            yield Static(", ".join(self.names), classes="hint")
            with Horizontal(id="confirm-modal-buttons"):
                yield Button("Uninstall", id="confirm-uninstall-yes", variant="error")
                yield Button("Cancel", id="confirm-uninstall-no", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-uninstall-yes":
            self.dismiss(True)
        else:
            self.dismiss(False)
