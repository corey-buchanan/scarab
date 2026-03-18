"""Workouts page - list, select, start playback."""

from pathlib import Path

from textual.containers import Container, Vertical, ScrollableContainer
from textual.widgets import Button, Label, Static

from scarab.data import WORKOUTS_DIR
from scarab.models.workout import Workout


class WorkoutsScreen(Container):
    """List workouts, select one, start playback. Replaces Library + Playback."""

    DEFAULT_CSS = """
    WorkoutsScreen {
        padding: 1 2;
        height: 1fr;
    }
    #workouts-header { height: auto; padding: 1 0; }
    #workouts-list { height: 1fr; overflow-y: auto; }
    #workouts-actions { height: auto; padding: 1 0; }
    .workout-btn { width: 100%; margin: 1 0; }
    """

    def compose(self):
        from textual.app import ComposeResult

        yield Label("Workouts", id="workouts-header")
        yield ScrollableContainer(id="workouts-list")
        yield Vertical(
            Button("Back (h)", id="back"),
            id="workouts-actions",
        )

    def on_mount(self) -> None:
        self._populate_list()

    def _populate_list(self) -> None:
        container = self.query_one("#workouts-list", ScrollableContainer)
        container.remove_children()
        workouts = list(WORKOUTS_DIR.glob("*.yaml"))
        for p in sorted(workouts):
            try:
                w = Workout.from_yaml(p)
                name = w.name
            except Exception:
                name = p.stem
            btn = Button(f"{name}", id=None, classes="workout-btn")
            btn._workout_path = p  # type: ignore
            container.mount(btn)
        if not workouts:
            container.mount(Label("(No workouts yet — create one in Editor)"))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.action_home()
        elif getattr(event.button, "_workout_path", None) is not None:
            path = event.button._workout_path
            if path and path.exists():
                from scarab.playback.player_screen import PlaybackScreen

                container = self.app.query_one("#main-container")
                container.remove_children()
                container.mount(PlaybackScreen(workout_path=path, id="playback"))
                self.app._current_screen = "playback"
