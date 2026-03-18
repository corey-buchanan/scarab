"""Exercise row and super-set detail widgets."""

from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Collapsible, Input, Label
from textual_autocomplete import AutoComplete, DropdownItem

from scarab.models.workout import ExerciseRef, SuperSet


class ExerciseRow(Horizontal):
    """Single exercise row: id (autocomplete), reps, rest, optional sets."""

    DEFAULT_CSS = """
    ExerciseRow {
        height: auto;
        padding: 0 1;
    }
    ExerciseRow .exercise-id-input { width: 28; min-width: 15; }
    ExerciseRow .reps-input { width: 10; min-width: 6; }
    ExerciseRow .rest-input { width: 10; min-width: 6; }
    ExerciseRow .sets-input { width: 6; min-width: 4; }
    """

    def __init__(
        self,
        ref: ExerciseRef,
        candidates: list[str],
        *,
        show_sets: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.ref = ref
        self.candidates = candidates
        self.show_sets = show_sets

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
        if self.show_sets:
            yield Label("sets:")
            yield Input(
                value=str(self.ref.sets),
                placeholder="1",
                type="integer",
                classes="sets-input",
            )
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
            reps = max(1, int(reps_inp.value or "10"))
        except ValueError:
            reps = 10
        try:
            rest_sec = int(rest_inp.value or "30")
        except ValueError:
            rest_sec = 30
        sets_val = 1
        if self.show_sets:
            sets_inp = self.query_one(".sets-input", Input)
            try:
                sets_val = max(1, int(sets_inp.value or "1"))
            except ValueError:
                sets_val = 1
        return ExerciseRef(
            id=id_inp.value.strip() or "unknown",
            sets=sets_val,
            reps=reps,
            rest_sec=rest_sec,
        )


class LoopSection(Collapsible):
    """Collapsible super-set block with label, sets, rest, items (exercises or nested super-sets)."""

    def __init__(self, superset: SuperSet, candidates: list[str], index: int, **kwargs) -> None:
        super().__init__(
            title=superset.label or f"Super-set {index + 1}",
            collapsed=False,
            **kwargs,
        )
        self.superset = superset
        self.candidates = candidates
        self.index = index

    def compose(self):
        from textual.app import ComposeResult

        from scarab.models.workout import WorkoutItem

        with Vertical(id="loop-content"):
            yield Horizontal(
                Label("Label:"),
                Input(value=self.superset.label or "", placeholder="e.g. Warmup", classes="loop-label"),
            )
            sets_val = self.superset.sets
            if isinstance(sets_val, dict):
                fixed = list(sets_val.values())[0] if sets_val else 3
            else:
                fixed = sets_val
            yield Horizontal(
                Label("Sets:"),
                Input(value=str(fixed), type="integer", classes="loop-sets"),
            )
            rest_val = self.superset.rest_between_sets or 0
            if len(self.superset.items) > 1:
                yield Horizontal(
                    Label("Rest between sets:"),
                    Input(value=str(rest_val), type="integer", placeholder="0", classes="loop-rest"),
                )
            yield Label("Items:", id="exercises-label")
            for ref in self.superset.items:
                if isinstance(ref, ExerciseRef):
                    yield ExerciseRow(ref, self.candidates, show_sets=False)
                else:
                    yield Label(f"(nested super-set: {ref.label or 'Unnamed'})")
            yield Horizontal(
                Button("+ Add exercise", id="add-exercise"),
                Button("Remove super-set", id="remove-loop", variant="warning"),
            )

    def get_superset(self) -> SuperSet:
        """Build SuperSet from current inputs."""
        from scarab.models.workout import WorkoutItem

        label_inp = self.query_one(".loop-label", Input)
        sets_inp = self.query_one(".loop-sets", Input)
        rest_inp = self.query_one(".loop-rest", Input) if self.query(".loop-rest") else None
        try:
            sets = int(sets_inp.value or "3")
        except ValueError:
            sets = 3
        try:
            rest = int(rest_inp.value or "0") if rest_inp else None
        except ValueError:
            rest = None
        items: list[WorkoutItem] = []
        for row in self.query(ExerciseRow):
            items.append(row.get_ref())
        return SuperSet(
            label=label_inp.value.strip() or None,
            sets=sets,
            items=items,
            rest_between_sets=rest if rest and rest > 0 else None,
        )
