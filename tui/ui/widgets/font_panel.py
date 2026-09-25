from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Input, RadioButton, RadioSet, Static

from backend.fonts import DEFAULT_FONT_BASE, default_font_dir


class FontPanel(Vertical):
    """Font zip URL entry with a choice of default or custom install location."""

    def compose(self) -> ComposeResult:
        yield Static("Font install", classes="pane-title")
        yield Input(placeholder="Font zip URL", id="font-url-input")
        with RadioSet(id="font-location-radio"):
            yield RadioButton("Default location", value=True, id="font-default-radio")
            yield RadioButton("Custom location", id="font-custom-radio")
        yield Static(self._default_location_text(""), id="font-default-preview", classes="hint")
        yield Input(placeholder="Custom font directory", id="font-path-input", disabled=True)

    def _default_location_text(self, url: str) -> str:
        if url:
            return f"Default location: {default_font_dir(url)}"
        return f"Default location: {DEFAULT_FONT_BASE}/<font-name>"

    @property
    def url(self) -> str:
        return self.query_one("#font-url-input", Input).value.strip()

    @property
    def use_custom_path(self) -> bool:
        return self.query_one("#font-custom-radio", RadioButton).value

    @property
    def custom_path(self) -> str:
        return self.query_one("#font-path-input", Input).value.strip()

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        if event.radio_set.id == "font-location-radio":
            custom_selected = event.pressed.id == "font-custom-radio"
            self.query_one("#font-path-input", Input).disabled = not custom_selected

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "font-url-input":
            self.query_one("#font-default-preview", Static).update(
                self._default_location_text(event.value.strip())
            )

    def reset(self) -> None:
        self.query_one("#font-url-input", Input).value = ""
        self.query_one("#font-path-input", Input).value = ""
        self.query_one("#font-path-input", Input).disabled = True
        self.query_one("#font-default-radio", RadioButton).value = True
        self.query_one("#font-default-preview", Static).update(self._default_location_text(""))
