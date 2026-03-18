"""Scarab main app - Textual TUI with navigation."""

from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.widgets import Footer, Header, Static

from scarab.data import WORKOUTS_DIR
from scarab.data.loader import load_exercise_catalog


class WelcomeScreen(Static):
    """Placeholder welcome / home screen."""

    def compose(self) -> ComposeResult:
        yield Static(
            "[bold]Scarab Workouts[/bold]\n\n"
            "Press [bold]e[/] for Editor  |  [bold]w[/] for Workouts  |  [bold]q[/] to quit",
            id="welcome-text",
        )


class EditorPlaceholder(Static):
    """Placeholder for sequence editor (Phase 2)."""

    def compose(self) -> ComposeResult:
        yield Static("Sequence Editor — Phase 2", id="editor-placeholder")


class PlaybackPlaceholder(Static):
    """Placeholder for playback (Phase 3)."""

    def compose(self) -> ComposeResult:
        yield Static("Playback — Phase 3", id="playback-placeholder")


class LibraryPlaceholder(Static):
    """Placeholder fallback."""

    def compose(self) -> ComposeResult:
        yield Static("Workouts (placeholder)", id="library-placeholder")


class ScarabApp(App):
    """Main Scarab TUI application."""

    CSS_PATH = str(Path(__file__).parent / "styles" / "scarab.css")

    CSS = """
    Screen {
        layout: vertical;
    }
    #main-container {
        height: 1fr;
        padding: 1 2;
    }
    #welcome-text, #editor-placeholder, #playback-placeholder, #library-placeholder {
        padding: 2;
        width: 100%;
        height: auto;
    }
    """

    TITLE = "Scarab"

    BINDINGS = [
        Binding("h", "home", "Home", show=True),
        Binding("e", "editor", "Editor", show=True),
        Binding("w", "workouts", "Workouts", show=True),
        Binding("q", "quit", "Quit", show=True),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._catalog = load_exercise_catalog()
        self._current_screen = "home"

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="main-container"):
            yield WelcomeScreen(id="welcome")
        yield Footer()

    def _ensure_workouts_dir(self) -> None:
        """Ensure workouts directory exists."""
        WORKOUTS_DIR.mkdir(parents=True, exist_ok=True)

    def on_mount(self) -> None:
        self._ensure_workouts_dir()

    def _show_screen(self, screen_id: str, widget_class: type) -> None:
        """Replace main content with given widget."""
        container = self.query_one("#main-container")
        container.remove_children()
        container.mount(widget_class(id=screen_id))
        self._current_screen = screen_id

    def action_editor(self) -> None:
        """Switch to editor picker, then sequence editor."""
        from scarab.screens.editor_picker_screen import EditorPickerScreen

        try:
            container = self.query_one("#main-container")
            container.remove_children()
            container.mount(EditorPickerScreen(id="editor-picker"))
            self._current_screen = "editor-picker"
        except ImportError:
            self._show_screen("editor", EditorPlaceholder)

    def action_workouts(self) -> None:
        """Switch to workouts screen."""
        from scarab.screens.workouts_screen import WorkoutsScreen

        try:
            container = self.query_one("#main-container")
            container.remove_children()
            container.mount(WorkoutsScreen(id="workouts"))
            self._current_screen = "workouts"
        except ImportError:
            self._show_screen("workouts", LibraryPlaceholder)

    def action_home(self) -> None:
        """Return to home screen."""
        container = self.query_one("#main-container")
        container.remove_children()
        container.mount(WelcomeScreen(id="welcome"))
        self._current_screen = "home"

    def action_editor_picker(self) -> None:
        """Return to editor picker (from within editor)."""
        from scarab.screens.editor_picker_screen import EditorPickerScreen
        container = self.query_one("#main-container")
        container.remove_children()
        container.mount(EditorPickerScreen(id="editor-picker"))
        self._current_screen = "editor-picker"

    def action_quit(self) -> None:
        """Quit the app."""
        self.exit()

    @property
    def catalog(self) -> list:
        """Exercise catalog for editor/playback."""
        return self._catalog


def main() -> None:
    """Entry point."""
    app = ScarabApp()
    app.run()


if __name__ == "__main__":
    main()
