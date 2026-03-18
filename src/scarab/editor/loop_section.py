"""Per-loop block: label, sets config, exercise list."""

from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Collapsible, Input, Label
from textual_autocomplete import AutoComplete, DropdownItem

from scarab.models.workout import ExerciseRef, Loop


class ExerciseRow(Horizontal):
    """Single exercise row: id (autocomplete), reps, rest, notes."""

    DEFAULT_CSS = """
    ExerciseRow {
        height: auto;
        padding: 0 1;
        min-width: 60;
    }
    ExerciseRow .exercise-id-input { width: 28; min-width: 20; }
    ExerciseRow .reps-input { width: 10; min-width: 8; }
    ExerciseRow .rest-input { width: 10; min-width: 8; }
    """

    def __init__(self, ref: ExerciseRef, candidates: list[str], **kwargs) -> None:
        super().__init__(**kwargs)
        self.ref = ref
        self.candidates = candidates

    def compose(self):
        from textual.app import ComposeResult

        inp = Input(
            value=self.ref.id,
            placeholder="Exercise...",
            classes="exercise-id-input",
        )
        items = [DropdownItem(main=c) for c in self.candidates]
        yield inp
        yield AutoComplete(inp, items)
        yield Label("reps:")
        yield Input(
            value=str(self.ref.reps),
            placeholder="10",
            type="integer",
            classes="reps-input",
        )
        yield Label("rest:")
        yield Input(
            value=str(self.ref.rest_sec),
            placeholder="30",
            type="integer",
            classes="rest-input",
        )
        yield Button("−", id="remove-exercise", variant="warning")

    def get_ref(self) -> ExerciseRef:
        """Build ExerciseRef from current inputs."""
        id_inp = self.query_one(".exercise-id-input", Input)
        reps_inp = self.query_one(".reps-input", Input)
        rest_inp = self.query_one(".rest-input", Input)
        try:
            reps = int(reps_inp.value or "10")
        except ValueError:
            reps = 10
        try:
            rest_sec = int(rest_inp.value or "30")
        except ValueError:
            rest_sec = 30
        return ExerciseRef(id=id_inp.value.strip() or "unknown", reps=reps, rest_sec=rest_sec)


class LoopSection(Collapsible):
    """Collapsible loop block with label, sets, exercises."""

    def __init__(self, loop: Loop, candidates: list[str], loop_index: int, **kwargs) -> None:
        super().__init__(
            title=loop.label or f"Loop {loop_index + 1}",
            collapsed=False,
            **kwargs,
        )
        self.loop = loop
        self.candidates = candidates
        self.loop_index = loop_index

    def compose(self):
        from textual.app import ComposeResult

        with Vertical(id="loop-content"):
            yield Horizontal(
                Label("Label:"),
                Input(value=self.loop.label or "", placeholder="e.g. Warmup", classes="loop-label"),
            )
            sets_val = self.loop.sets
            if isinstance(sets_val, dict):
                fixed = list(sets_val.values())[0] if sets_val else 3
            else:
                fixed = sets_val
            yield Horizontal(
                Label("Sets:"),
                Input(value=str(fixed), type="integer", classes="loop-sets"),
            )
            yield Label("Exercises:", id="exercises-label")
            for ref in self.loop.exercises:
                yield ExerciseRow(ref, self.candidates)
            yield Horizontal(
                Button("+ Add exercise", id="add-exercise"),
                Button("Remove loop", id="remove-loop", variant="warning"),
            )

    def get_loop(self) -> Loop:
        """Build Loop from current inputs."""
        label_inp = self.query_one(".loop-label", Input)
        sets_inp = self.query_one(".loop-sets", Input)
        try:
            sets = int(sets_inp.value or "3")
        except ValueError:
            sets = 3
        exercises = []
        for row in self.query(ExerciseRow):
            exercises.append(row.get_ref())
        return Loop(
            label=label_inp.value.strip() or None,
            sets=sets,
            exercises=exercises,
        )
