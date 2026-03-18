"""Picker to select which workout to edit or create new."""

from pathlib import Path

from textual.containers import Container, Vertical, ScrollableContainer
from textual.widgets import Button, Input, Label

from scarab.data import WORKOUTS_DIR
from scarab.models.workout import Workout


class EditorPickerScreen(Container):
    """Choose existing workout to edit or create new one."""

    DEFAULT_CSS = """
    EditorPickerScreen { padding: 1 2; height: 1fr; }
    #editor-picker-list { height: 1fr; overflow-y: auto; }
    .workout-edit-btn { width: 100%; margin: 1 0; }
    #new-name-input { width: 40; }
    """

    def compose(self):
        from textual.app import ComposeResult

        yield Label("Edit workout", id="editor-picker-header")
        yield ScrollableContainer(id="editor-picker-list")
        yield Vertical(
            Label("Or create new:"),
            Input(placeholder="Workout name...", id="new-name-input"),
            Button("Create new", id="create-new-workout", variant="primary"),
            Button("Back (h)", id="back"),
            id="editor-picker-actions",
        )

    def on_mount(self) -> None:
        self._populate_list()

    def _populate_list(self) -> None:
        container = self.query_one("#editor-picker-list", ScrollableContainer)
        container.remove_children()
        workouts = list(WORKOUTS_DIR.glob("*.yaml"))
        for p in sorted(workouts):
            try:
                w = Workout.from_yaml(p)
                name = w.name
            except Exception:
                name = p.stem
            btn = Button(f"{name}", id=f"edit-{p.stem}", classes="workout-edit-btn")
            btn._workout_path = p  # type: ignore
            container.mount(btn)
        if not workouts:
            container.mount(Label("(No workouts yet — create one below)"))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.action_home()
        elif event.button.id == "create-new-workout":
            name_inp = self.query_one("#new-name-input", Input)
            name = name_inp.value.strip() or "New Workout"
            from scarab.editor.sequence_editor import SequenceEditorScreen
            from scarab.models.workout import Loop
            workout = Workout(name=name, loops=[Loop(sets=3, exercises=[])])
            container = self.app.query_one("#main-container")
            container.remove_children()
            editor = SequenceEditorScreen(workout_path=None, id="editor")
            editor.workout = workout
            editor.workout_path = None
            editor._render_counter = 0
            container.mount(editor)
            self.app._current_screen = "editor"
        elif event.button.id and event.button.id.startswith("edit-"):
            path = getattr(event.button, "_workout_path", None)
            if path and path.exists():
                from scarab.editor.sequence_editor import SequenceEditorScreen
                container = self.app.query_one("#main-container")
                container.remove_children()
                container.mount(SequenceEditorScreen(workout_path=path, id="editor"))
                self.app._current_screen = "editor"
