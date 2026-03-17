"""Exercise picker with autocomplete."""

from textual.widgets import Input
from textual_autocomplete import AutoComplete, DropdownItem


def make_dropdown_items(candidates: list[str]) -> list[DropdownItem | str]:
    """Convert candidate strings to DropdownItems for display."""
    return [DropdownItem(main=c) for c in candidates]


def exercise_input_with_autocomplete(
    candidates: list[str],
    value: str = "",
    placeholder: str = "Exercise ID or name...",
) -> tuple[Input, AutoComplete]:
    """Create an Input and AutoComplete pair. Caller must yield both."""
    inp = Input(value=value, placeholder=placeholder)
    items = make_dropdown_items(candidates)
    ac = AutoComplete(inp, items)
    return inp, ac
