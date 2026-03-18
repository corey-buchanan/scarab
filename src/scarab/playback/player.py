"""Playback engine - iterates loops and exercises with timer."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from scarab.models.workout import ExerciseRef, Loop, Workout


class PlaybackState(Enum):
    IDLE = "idle"
    EXERCISE = "exercise"
    REST = "rest"
    PAUSED = "paused"
    COMPLETE = "complete"


@dataclass
class PlaybackItem:
    """Single item to perform (exercise or rest)."""
    loop_label: str | None
    set_num: int
    exercise: ExerciseRef
    is_rest: bool = False


@dataclass
class PlaybackProgress:
    """Current playback position."""
    loop_idx: int = 0
    set_num: int = 1
    exercise_idx: int = 0
    item_idx: int = 0
    items: list[PlaybackItem] = field(default_factory=list)


def build_playback_items(workout: Workout, level: int) -> list[PlaybackItem]:
    """Flatten workout into ordered items for playback. Exercises only (no rest steps)."""
    items: list[PlaybackItem] = []
    for loop in workout.loops:
        sets_count = loop.get_sets_for_level(level)
        for s in range(1, sets_count + 1):
            for ex in loop.exercises:
                items.append(PlaybackItem(
                    loop_label=loop.label,
                    set_num=s,
                    exercise=ex,
                    is_rest=False,
                ))
    return items


class PlaybackEngine:
    """Drives playback through workout items."""

    def __init__(self, workout: Workout, level: int = 1):
        self.workout = workout
        self.level = level
        self.items = build_playback_items(workout, level)
        self.state = PlaybackState.IDLE
        self.item_idx = 0

    def current_item(self) -> PlaybackItem | None:
        if 0 <= self.item_idx < len(self.items):
            return self.items[self.item_idx]
        return None

    def next_item(self) -> PlaybackItem | None:
        self.item_idx += 1
        return self.current_item()

    def is_complete(self) -> bool:
        return self.item_idx >= len(self.items)

    def start(self) -> PlaybackItem | None:
        self.state = PlaybackState.EXERCISE
        self.item_idx = 0
        return self.current_item()
