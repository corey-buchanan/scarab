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
            "[bold]Scarab Workout Sequencer[/bold]\n\n"
            "Press [bold]e[/] for Editor  |  [bold]p[/] for Playback  |  [bold]l[/] for Library  |  [bold]q[/] to quit",
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
    """Placeholder for workout library (Phase 4)."""

    def compose(self) -> ComposeResult:
        yield Static("Workout Library — Phase 4", id="library-placeholder")


class ScarabApp(App):
    """Main Scarab TUI application."""

    CSS_PATH = Path(__file__).parent / "styles" / "scarab.css"

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
        Binding("p", "playback", "Playback", show=True),
        Binding("l", "library", "Library", show=True),
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
        """Switch to editor screen. Phase 2 will replace placeholder."""
        from scarab.editor.sequence_editor import SequenceEditorScreen

        try:
            container = self.query_one("#main-container")
            container.remove_children()
            container.mount(SequenceEditorScreen(id="editor"))
            self._current_screen = "editor"
        except ImportError:
            self._show_screen("editor", EditorPlaceholder)

    def action_playback(self) -> None:
        """Switch to playback screen."""
        from scarab.playback.player_screen import PlaybackScreen

        try:
            container = self.query_one("#main-container")
            container.remove_children()
            container.mount(PlaybackScreen(id="playback"))
            self._current_screen = "playback"
        except ImportError:
            self._show_screen("playback", PlaybackPlaceholder)

    def action_library(self) -> None:
        """Switch to library screen."""
        from scarab.screens.library_screen import LibraryScreen
        try:
            container = self.query_one("#main-container")
            container.remove_children()
            container.mount(LibraryScreen(id="library"))
            self._current_screen = "library"
        except ImportError:
            self._show_screen("library", LibraryPlaceholder)

    def action_home(self) -> None:
        """Return to home screen."""
        container = self.query_one("#main-container")
        container.remove_children()
        container.mount(WelcomeScreen(id="welcome"))
        self._current_screen = "home"

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
