"""Workout library picker screen."""

from pathlib import Path

from textual.containers import Container, Vertical, ScrollableContainer
from textual.widgets import Button, Label

from scarab.data import WORKOUTS_DIR
from scarab.models.workout import Workout


class LibraryScreen(Container):
    """List workouts; pick to edit or play."""

    DEFAULT_CSS = """
    LibraryScreen {
        padding: 1 2;
        height: 1fr;
    }
    #library-list {
        height: 1fr;
        overflow-y: auto;
    }
    #library-actions { height: auto; padding: 1 0; }
    .workout-btn { width: 100%; }
    """

    def compose(self):
        from textual.app import ComposeResult

        yield Label("Workout Library", id="library-header")
        yield ScrollableContainer(id="library-list")
        yield Vertical(
            Button("Back (h)", id="back"),
            id="library-actions",
        )

    def on_mount(self) -> None:
        self._populate_list()

    def _populate_list(self) -> None:
        container = self.query_one("#library-list", ScrollableContainer)
        container.remove_children()
        workouts = list(WORKOUTS_DIR.glob("*.yaml"))
        for p in sorted(workouts):
            try:
                w = Workout.from_yaml(p)
                name = w.name
            except Exception:
                name = p.stem
            btn = Button(f"📄 {name}", id=f"workout-{p.stem}", classes="workout-btn")
            btn._workout_path = p  # type: ignore
            container.mount(btn)
        if not workouts:
            container.mount(Label("(No workouts yet — create one in Editor)"))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.action_home()
        elif event.button.id and event.button.id.startswith("workout-"):
            path = getattr(event.button, "_workout_path", None)
            if path and path.exists():
                # Show Edit/Play choice as sub-buttons - for simplicity go to playback
                from scarab.playback.player_screen import PlaybackScreen
                container = self.app.query_one("#main-container")
                container.remove_children()
                container.mount(PlaybackScreen(workout_path=path, id="playback"))
                self.app._current_screen = "playback"
