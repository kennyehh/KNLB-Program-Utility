from __future__ import annotations

from rich.segment import Segment
from rich.style import Style
from textual.strip import Strip
from textual.widgets import SelectionList
from textual.widgets._option_list import OptionDoesNotExist
from textual.widgets._toggle_button import ToggleButton


class ColorableSelectionList(SelectionList):
    """A SelectionList that supports assigning an extra CSS component class
    per option value, so individual rows can be colored via CSS.

    This exists because Textual's OptionList/SelectionList always renders the
    widget's own CSS `color` "on top of" whatever style is embedded in an
    option's prompt content — a plain string, a Rich Text with an inline
    style, and a styled `textual.content.Content` are all overridden the same
    way. The only mechanism Textual actually respects for per-row color is
    its CSS component-class system (the same one used for e.g.
    `.option-list--option-highlighted`), so this subclass extends that
    system with app-defined classes instead of fighting the content style.

    render_line() below re-implements (rather than calls super() on)
    SelectionList.render_line and OptionList.render_line, because
    SelectionList.render_line builds its checkbox glyph by calling
    OptionList.render_line via `super()` — a plain method override can't
    inject a custom style into that inner call without also reproducing the
    checkbox-prepending step, or the checkbox itself silently disappears.
    Verified against Textual 8.2.8; a Textual upgrade that changes either of
    those two methods' internals would need this re-checked against them.
    """

    COMPONENT_CLASSES = SelectionList.COMPONENT_CLASSES | {
        "option-list--option-green",
        "option-list--option-lightblue",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._option_style_classes: dict[object, str] = {}

    def set_option_style_class(self, value: object, class_name: str | None) -> None:
        """Assign (or clear, with class_name=None) an extra CSS component
        class for the option with this value, e.g. "option-list--option-green"."""
        if class_name is None:
            self._option_style_classes.pop(value, None)
        else:
            self._option_style_classes[value] = class_name

    def render_line(self, y: int) -> Strip:
        line_number = self.scroll_offset.y + y
        try:
            option_index, line_offset = self._lines[line_number]
            # get_option_at_index (not the raw self.options[...] list) is what
            # SelectionList itself types as returning Selection rather than
            # the base Option, which is what actually has .value.
            option = self.get_option_at_index(option_index)
        except (IndexError, OptionDoesNotExist):
            return super().render_line(y)

        mouse_over = self._mouse_hovering_over == option_index
        component_classes: list[str] = []
        if option.disabled:
            component_classes.append("option-list--option-disabled")
        elif self.highlighted == option_index:
            component_classes.append("option-list--option-highlighted")
        elif mouse_over:
            component_classes.append("option-list--option-hover")

        extra_class = self._option_style_classes.get(option.value)
        if extra_class:
            component_classes.append(extra_class)

        style = (
            self.get_visual_style("option-list--option", *component_classes)
            if component_classes
            else self.get_visual_style("option-list--option")
        )

        strips = self._get_option_render(option, style)
        try:
            label_line = strips[line_offset]
        except IndexError:
            return super().render_line(y)

        # From here down: SelectionList.render_line's own checkbox-prepending
        # logic, reproduced so it applies on top of our styled label instead
        # of a freshly-rendered unstyled one.
        _, scroll_y = self.scroll_offset
        selection_index = scroll_y + y
        try:
            selection = self.get_option_at_index(selection_index)
        except OptionDoesNotExist:
            return label_line

        component_style = "selection-list--button"
        if selection.value in self._selected:
            component_style += "-selected"
        if self.highlighted == selection_index:
            component_style += "-highlighted"

        underlying_style = next(iter(label_line)).style or self.rich_style
        button_style = self.get_component_rich_style(component_style)
        side_style = Style.from_color(button_style.bgcolor, underlying_style.bgcolor)
        side_style += Style(meta={"option": selection_index})
        button_style += Style(meta={"option": selection_index})

        return Strip(
            [
                Segment(ToggleButton.BUTTON_LEFT, style=side_style),
                Segment(ToggleButton.BUTTON_INNER, style=button_style),
                Segment(ToggleButton.BUTTON_RIGHT, style=side_style),
                Segment(" ", style=underlying_style),
                *label_line,
            ]
        )
