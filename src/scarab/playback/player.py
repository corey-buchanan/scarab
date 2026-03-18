"""Playback engine - iterates workout items (exercises and super-sets) with timer."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from scarab.models.workout import ExerciseRef, SuperSet, Workout, WorkoutItem


class PlaybackState(Enum):
    IDLE = "idle"
    EXERCISE = "exercise"
    REST = "rest"
    PAUSED = "paused"
    COMPLETE = "complete"


@dataclass
class PlaybackItem:
    """Single item to perform (exercise or rest)."""
    superset_label: str | None
    set_num: int
    exercise: ExerciseRef
    is_rest: bool = False


@dataclass
class PlaybackProgress:
    """Current playback position."""
    item_idx: int = 0
    set_num: int = 1
    items: list[PlaybackItem] = field(default_factory=list)


def _flatten_one_round(
    items: list[WorkoutItem],
    level: int,
    parent_label: str | None,
) -> list[PlaybackItem]:
    """One round of items (no set replication). Nested SuperSets are fully expanded."""
    out: list[PlaybackItem] = []
    for item in items:
        if isinstance(item, ExerciseRef):
            out.append(PlaybackItem(
                superset_label=parent_label,
                set_num=1,
                exercise=item,
                is_rest=False,
            ))
        elif isinstance(item, SuperSet):
            nested = _flatten_one_round(item.items, level, item.label)
            sets_count = item.get_sets_for_level(level)
            for s in range(1, sets_count + 1):
                for p in nested:
                    out.append(PlaybackItem(
                        superset_label=p.superset_label or item.label,
                        set_num=s,
                        exercise=p.exercise,
                        is_rest=False,
                    ))
        else:
            raise TypeError(f"Unexpected item type: {type(item)}")
    return out


def build_playback_items(workout: Workout, level: int) -> list[PlaybackItem]:
    """Flatten workout into ordered items for playback. Exercises only (no rest steps)."""
    out: list[PlaybackItem] = []
    for item in workout.items:
        if isinstance(item, ExerciseRef):
            for s in range(1, item.sets + 1):
                out.append(PlaybackItem(
                    superset_label=None,
                    set_num=s,
                    exercise=item,
                    is_rest=False,
                ))
        elif isinstance(item, SuperSet):
            one_round = _flatten_one_round(item.items, level, item.label)
            sets_count = item.get_sets_for_level(level)
            for s in range(1, sets_count + 1):
                for p in one_round:
                    out.append(PlaybackItem(
                        superset_label=p.superset_label or item.label,
                        set_num=s,
                        exercise=p.exercise,
                        is_rest=False,
                    ))
        else:
            raise TypeError(f"Unexpected item type: {type(item)}")
    return out


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
