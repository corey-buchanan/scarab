"""Interactive sequence editor with multi-loop structure."""

from pathlib import Path

from textual.containers import Container, Vertical, ScrollableContainer
from textual.widgets import Button, Input, Label, Static

from scarab.data import WORKOUTS_DIR
from scarab.data.loader import catalog_autocomplete_items, load_exercise_catalog
from scarab.models.workout import Loop, Workout
from scarab.editor.loop_section import ExerciseRow, LoopSection


class SequenceEditorScreen(Container):
    """Interactive sequence builder with multi-loop support."""

    DEFAULT_CSS = """
    SequenceEditorScreen {
        padding: 1 2;
        height: 1fr;
    }
    #editor-toolbar {
        height: auto;
        padding: 1 0;
    }
    #workout-name-row {
        height: 1;
        padding: 0 0 1 0;
    }
    #workout-name-input {
        width: 40;
    }
    #loops-container {
        height: 1fr;
        overflow-y: auto;
    }
    #editor-actions {
        height: auto;
        padding: 1 0;
    }
    """

    def __init__(self, workout_path: Path | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.workout_path = workout_path
        self.workout = self._load_or_new(workout_path)
        self._catalog = load_exercise_catalog()
        self._candidates = catalog_autocomplete_items(self._catalog)
        self._render_counter = 0

    def _load_or_new(self, path: Path | None) -> Workout:
        if path and Path(path).exists():
            return Workout.from_yaml(path)
        return Workout(name="New Workout", loops=[Loop(sets=3, exercises=[])])

    def compose(self):
        from textual.app import ComposeResult

        yield Vertical(
            # Toolbar
            Label("Workout name:", id="name-label"),
            Input(
                value=self.workout.name,
                placeholder="e.g. Full Body Circuit",
                id="workout-name-input",
                classes="workout-name",
            ),
            id="workout-name-row",
        )
        yield Button("+ Add loop", id="add-loop", variant="primary")
        yield ScrollableContainer(id="loops-container")
        yield Vertical(
            Button("Save", id="save-workout", variant="success"),
            Button("Back (h)", id="back"),
            id="editor-actions",
        )

    def on_mount(self) -> None:
        self._render_loops()

    def _render_loops(self) -> None:
        self._render_counter += 1
        container = self.query_one("#loops-container", ScrollableContainer)
        container.remove_children()
        for i, loop in enumerate(self.workout.loops):
            section = LoopSection(loop, self._candidates, i, id=f"loop-{i}-r{self._render_counter}")
            container.mount(section)

    def _collect_workout(self) -> Workout:
        name_inp = self.query_one("#workout-name-input", Input)
        loops = []
        for section in self.query(LoopSection):
            loops.append(section.get_loop())
        return Workout(name=name_inp.value.strip() or "Unnamed", loops=loops)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add-loop":
            self.workout.loops.append(Loop(sets=3, exercises=[]))
            self._render_loops()
        elif event.button.id == "save-workout":
            self._save()
        elif event.button.id == "back":
            self.app.action_editor_picker()
        elif event.button.id == "add-exercise":
            from scarab.models.workout import ExerciseRef
            section = event.button.query_ancestor(LoopSection)
            if section:
                content = section.query_one("#loop-content", Vertical)
                buttons_row = event.button.parent
                row = ExerciseRow(ExerciseRef(id="", reps=10, rest_sec=30), self._candidates)
                content.mount(row, before=buttons_row)
        elif event.button.id == "remove-loop":
            section = event.button.query_ancestor(LoopSection)
            if section and section.id:
                parts = section.id.split("-")
                idx = int(parts[1]) if len(parts) >= 2 else 0
                self.workout.loops.pop(idx)
                self._render_loops()
        elif event.button.id == "remove-exercise":
            row = event.button.parent
            if isinstance(row, ExerciseRow):
                row.remove()

    def _save(self) -> None:
        self.workout = self._collect_workout()
        path = self.workout_path or WORKOUTS_DIR / f"{self._slug(self.workout.name)}.yaml"
        self.workout.to_yaml(path)
        self.notify(f"Saved to {path}", severity="information")

    def _slug(self, name: str) -> str:
        return "".join(c if c.isalnum() or c in " -_" else "" for c in name).strip().replace(" ", "_").lower() or "workout"
