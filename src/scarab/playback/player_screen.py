"""Playback screen - workout execution with animations."""

from pathlib import Path

from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Label, Static

from scarab.data import WORKOUTS_DIR
from scarab.data.loader import get_exercise_by_id, load_exercise_catalog
from scarab.models.workout import Workout
from scarab.playback.player import PlaybackEngine, PlaybackItem, PlaybackState
from scarab.playback.animation import AnimationWidget
from scarab.playback.stat_tracker import (
    compute_workout_points,
    load_stats,
    save_stats,
)


class PlaybackScreen(Container):
    """Play workout with ASCII animation and timer."""

    DEFAULT_CSS = """
    PlaybackScreen {
        padding: 1 2;
        height: 1fr;
    }
    #playback-header { height: auto; padding: 1 0; }
    #playback-animation {
        height: 1fr;
        min-height: 10;
        overflow: hidden;
    }
    #playback-controls { height: auto; padding: 1 0; }
    """

    def __init__(self, workout_path: Path | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.workout_path = workout_path
        self.workout: Workout | None = None
        self.engine: PlaybackEngine | None = None
        self._catalog = load_exercise_catalog()
        self._level = 1

    def compose(self):
        from textual.app import ComposeResult

        yield Vertical(
            Label("Playback — Select workout and level", id="playback-header"),
            Static("(Load a workout to start)", id="playback-placeholder"),
            id="playback-content",
        )
        yield Horizontal(
            Button("Load workout", id="load-workout"),
            Button("Start (Level 1)", id="start-playback"),
            Button("Back (h)", id="back"),
            id="playback-controls",
        )

    def on_mount(self) -> None:
        # Try to load first workout from library
        if self.workout_path and self.workout_path.exists():
            self._load_workout(self.workout_path)
        else:
            workouts = list(WORKOUTS_DIR.glob("*.yaml"))
            if workouts:
                self._load_workout(workouts[0])

    def _load_workout(self, path: Path) -> None:
        self.workout = Workout.from_yaml(path)
        self.workout_path = path
        header = self.query_one("#playback-header", Label)
        header.update(f"Ready: {self.workout.name}")

    def _start_playback(self) -> None:
        if not self.workout:
            self.notify("Load a workout first", severity="warning")
            return
        self.engine = PlaybackEngine(self.workout, self._level)
        item = self.engine.start()
        self._replace_content_with_playback(item)

    def _replace_content_with_playback(self, item: PlaybackItem | None) -> None:
        content = self.query_one("#playback-content", Vertical)
        content.remove_children()
        if item is None:
            self._show_complete()
            return
        ex = item.exercise
        catalog_ex = get_exercise_by_id(self._catalog, ex.id)
        static = catalog_ex.static if catalog_ex else False
        anim = AnimationWidget(ex.id, static=static, id="playback-animation")
        label_text = f"{ex.id}: {ex.reps} reps"
        if item.loop_label:
            label_text = f"[{item.loop_label}] Set {item.set_num} — {label_text}"
        content.mount(Vertical(
            Label(label_text, id="exercise-label"),
            anim,
            id="playback-animation-container",
        ))
        content.mount(Horizontal(
            Button("Next", id="next-exercise"),
            Button("Skip", id="skip-exercise"),
            Button("Pause", id="pause-playback"),
            id="playback-buttons",
        ))

    def _show_complete(self) -> None:
        if not self.engine or not self.workout:
            return
        # Count exercises (non-rest items)
        exercise_count = sum(1 for i in self.engine.items if not i.is_rest)
        loop_count = len(set((i.loop_label, i.set_num) for i in self.engine.items if not i.is_rest))
        points, xp = compute_workout_points(exercise_count, loop_count)
        stats = load_stats()
        stats.add_workout_completion(points, xp, exercise_count)
        save_stats(stats)
        content = self.query_one("#playback-content", Vertical)
        content.remove_children()
        content.mount(Static(
            f"Workout complete!\n\n"
            f"Points: +{points}  |  XP: +{xp}\n"
            f"Level: {stats.level()}  |  Total XP: {stats.total_xp}",
            id="complete-message",
        ))
        content.mount(Button("Back", id="back-from-complete"))

    def on_button_pressed(self, event) -> None:
        if event.button.id == "load-workout":
            workouts = list(WORKOUTS_DIR.glob("*.yaml"))
            if workouts:
                self._load_workout(workouts[0])
                self.notify(f"Loaded {self.workout.name}")
            else:
                self.notify("No workouts found", severity="warning")
        elif event.button.id == "start-playback":
            self._start_playback()
        elif event.button.id == "back" or event.button.id == "back-from-complete":
            self.app.action_home()
        elif event.button.id == "next-exercise" or event.button.id == "skip-exercise":
            if self.engine:
                item = self.engine.next_item()
                if self.engine.is_complete():
                    self._show_complete()
                else:
                    self._replace_content_with_playback(item)
        elif event.button.id == "pause-playback":
            self.notify("Pause not yet implemented", severity="information")
