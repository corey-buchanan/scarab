"""Sets input - single value or per-level mapping."""

from textual.containers import Horizontal, Vertical
from textual.widgets import Input, Label
from textual.validation import Number


class SetsInput(Vertical):
    """Input for sets: fixed (all levels) or per-level (1-5)."""

    DEFAULT_CSS = """
    SetsInput {
        height: auto;
    }
    #sets-fixed-row {
        height: 1;
    }
    #sets-fixed-input {
        width: 6;
    }
    .level-input {
        width: 4;
    }
    """

    def __init__(
        self,
        *,
        fixed: int = 3,
        per_level: dict[int, int] | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self._fixed = fixed
        self._per_level = per_level or {1: 3, 2: 5, 3: 7}
        self._use_per_level = per_level is not None and len(per_level) > 0

    def compose(self):
        from textual.app import ComposeResult

        yield Horizontal(
            Label("Sets (all levels):"),
            Input(
                value=str(self._fixed),
                placeholder="e.g. 3",
                type="integer",
                validators=[Number(minimum=1, maximum=99)],
                id="sets-fixed-input",
            ),
            id="sets-fixed-row",
        )
        with Vertical(id="sets-levels-container"):
            for level in range(1, 6):
                val = self._per_level.get(level, 3)
                yield Horizontal(
                    Label(f"L{level}:"),
                    Input(
                        value=str(val),
                        type="integer",
                        validators=[Number(minimum=1, maximum=99)],
                        id=f"sets-level-{level}",
                        classes="level-input",
                    ),
                )

    def get_value(self) -> int | dict[int, int]:
        """Return current sets as int (fixed) or dict (per-level)."""
        fixed_inp = self.query_one("#sets-fixed-input", Input)
        try:
            fixed_val = int(fixed_inp.value or "3")
        except ValueError:
            fixed_val = 3

        # If any level input is different from fixed, we're in per-level mode
        level_values = {}
        for level in range(1, 6):
            inp = self.query_one(f"#sets-level-{level}", Input)
            try:
                level_values[level] = int(inp.value or str(fixed_val))
            except ValueError:
                level_values[level] = fixed_val

        if all(v == fixed_val for v in level_values.values()):
            return fixed_val
        return level_values
