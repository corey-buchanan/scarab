"""ASCII animation renderer - viewport-sized frames."""

from pathlib import Path

from textual.widgets import Static

from scarab.data import FRAMES_DIR

SizeVariant = str  # "small" | "medium" | "large"

COLS_SMALL = 80
COLS_MEDIUM = 120


def get_size_variant(cols: int) -> SizeVariant:
    """Select frame size based on viewport width."""
    if cols < COLS_SMALL:
        return "small"
    if cols < COLS_MEDIUM:
        return "medium"
    return "large"


def load_frames(exercise_id: str, size: SizeVariant) -> list[str]:
    """Load ASCII frames for exercise. Returns list of frame strings."""
    base = FRAMES_DIR / exercise_id
    # Try size-specific subdir first (for multi-frame)
    size_dir = base / size
    if size_dir.is_dir():
        frames = sorted(size_dir.glob("frame_*.txt"))
        if frames:
            return [_read_frame(f) for f in frames]
    # Fallback: single frame per size
    frame_file = base / f"{size}.txt"
    if frame_file.exists():
        return [_read_frame(frame_file)]
    # Try any .txt in base
    for f in base.glob("*.txt"):
        return [_read_frame(f)]
    return [f"(no animation: {exercise_id})"]


def _read_frame(path: Path) -> str:
    return path.read_text(errors="replace")


class AnimationWidget(Static):
    """Displays ASCII animation - cycles frames or shows static."""

    def __init__(self, exercise_id: str, static: bool = False, **kwargs) -> None:
        super().__init__(**kwargs)
        self.exercise_id = exercise_id
        self.static = static
        self._frames: list[str] = []
        self._frame_index = 0

    def on_mount(self) -> None:
        self._load_frames()
        self._start_timer()

    def _load_frames(self) -> None:
        # Get viewport size from container
        size = get_size_variant(self.size.width if self.size else 80)
        self._frames = load_frames(self.exercise_id, size)
        if self._frames:
            self.update(self._frames[0])

    def _start_timer(self) -> None:
        if self.static or len(self._frames) <= 1:
            return
        self.set_interval(0.2, self._tick)

    def _tick(self) -> None:
        if not self._frames:
            return
        self._frame_index = (self._frame_index + 1) % len(self._frames)
        self.update(self._frames[self._frame_index])

    def refresh_frames(self, cols: int | None = None) -> None:
        """Reload frames (e.g. after resize)."""
        cols = cols or (self.size.width if self.size else 80)
        size = get_size_variant(cols)
        self._frames = load_frames(self.exercise_id, size)
        if self._frames:
            self.update(self._frames[0])
