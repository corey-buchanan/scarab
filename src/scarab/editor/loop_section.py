"""Exercise row and super-set detail widgets."""

from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Collapsible, Input, Label, Select
from textual_autocomplete import AutoComplete, DropdownItem

from scarab.models.workout import ExerciseRef, SuperSet


class ExerciseRow(Horizontal):
    """Single exercise row: id (autocomplete), reps or timed, rest, optional sets."""

    DEFAULT_CSS = """
    ExerciseRow {
        height: auto;
        padding: 0 1;
    }
    ExerciseRow .exercise-id-input { width: 28; min-width: 15; }
    ExerciseRow .reps-input { width: 15; min-width: 10; }
    ExerciseRow .seconds-input { width: 15; min-width: 10; }
    ExerciseRow .rest-input { width: 15; min-width: 10; }
    ExerciseRow .sets-input { width: 15; min-width: 10; }
    ExerciseRow .mode-select { width: 15; min-width: 10; }
    ExerciseRow .reps-label.hidden,
    ExerciseRow .reps-input.hidden,
    ExerciseRow .timed-label.hidden,
    ExerciseRow .seconds-input.hidden { display: none; }
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
        self._is_timed = ref.hold_sec is not None and ref.hold_sec > 0

    def compose(self):
        from textual.app import ComposeResult

        inp = Input(
            value=self.ref.id or "",
            placeholder="Exercise...",
            classes="exercise-id-input",
        )
        items = [DropdownItem(main=c) for c in self.candidates]
        yield inp
        yield AutoComplete(inp, items)
        if self.show_sets:
            yield Label("Sets:")
            yield Input(
                value=str(self.ref.sets),
                placeholder="1",
                type="integer",
                classes="sets-input",
            )
        yield Label("Type:")
        yield Select(
            [("Reps", "reps"), ("Timed (s)", "timed")],
            value="timed" if self._is_timed else "reps",
            classes="mode-select",
        )
        reps_val = str(self.ref.reps)
        sec_val = str(self.ref.hold_sec or 30)
        hidden_reps = " hidden" if self._is_timed else ""
        hidden_timed = " hidden" if not self._is_timed else ""
        yield Label("Reps:", classes="reps-label" + hidden_reps)
        yield Input(value=reps_val, placeholder="10", type="integer", classes="reps-input" + hidden_reps)
        yield Label("Seconds:", classes="timed-label" + hidden_timed)
        yield Input(value=sec_val, placeholder="30", type="integer", classes="seconds-input" + hidden_timed)
        yield Label("Rest:")
        yield Input(
            value="" if self.ref.rest_sec == 0 else str(self.ref.rest_sec),
            placeholder="0",
            type="integer",
            valid_empty=True,
            classes="rest-input",
        )
        yield Button("Remove", id="remove-exercise", variant="warning")

    def on_select_changed(self, event: Select.Changed) -> None:
        value = str(event.value) if event.value is not None else "reps"
        is_timed = value == "timed"
        for node in self.query(".reps-label, .reps-input"):
            node.add_class("hidden") if is_timed else node.remove_class("hidden")
        for node in self.query(".timed-label, .seconds-input"):
            node.remove_class("hidden") if is_timed else node.add_class("hidden")

    def get_ref(self) -> ExerciseRef:
        """Build ExerciseRef from current inputs."""
        id_inp = self.query_one(".exercise-id-input", Input)
        rest_inp = self.query_one(".rest-input", Input)
        mode_select = self.query_one(".mode-select", Select)
        mode = str(mode_select.value) if mode_select.value is not None else "reps"
        try:
            rest_sec = int(rest_inp.value or "0")
        except ValueError:
            rest_sec = 0
        sets_val = 1
        if self.show_sets:
            sets_inp = self.query_one(".sets-input", Input)
            try:
                sets_val = max(1, int(sets_inp.value or "1"))
            except ValueError:
                sets_val = 1
        if mode == "timed":
            sec_inp = self.query_one(".seconds-input", Input)
            try:
                hold_sec = max(1, int(sec_inp.value or "30"))
            except ValueError:
                hold_sec = 30
            return ExerciseRef(
                id=id_inp.value.strip() or "",
                sets=sets_val,
                reps=1,
                rest_sec=rest_sec,
                hold_sec=hold_sec,
            )
        else:
            reps_inp = self.query_one(".reps-input", Input)
            try:
                reps = max(1, int(reps_inp.value or "10"))
            except ValueError:
                reps = 10
            return ExerciseRef(
                id=id_inp.value.strip() or "",
                sets=sets_val,
                reps=reps,
                rest_sec=rest_sec,
                hold_sec=None,
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
