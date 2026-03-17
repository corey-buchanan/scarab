"""Stat tracking for workout completion."""

from pathlib import Path

from scarab.data import DATA_DIR
from scarab.models.stats import UserStats

STATS_PATH = DATA_DIR / "user_stats.json"


def load_stats() -> UserStats:
    """Load user stats from disk."""
    if STATS_PATH.exists():
        import json
        data = json.loads(STATS_PATH.read_text())
        return UserStats(**data)
    return UserStats()


def save_stats(stats: UserStats) -> None:
    """Persist user stats."""
    import json
    STATS_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = getattr(stats, "model_dump", lambda **kw: stats.dict(**kw))()
    STATS_PATH.write_text(json.dumps(data, indent=2))


def compute_workout_points(exercise_count: int, loops_completed: int) -> tuple[int, int]:
    """Return (points, xp) for workout completion."""
    base_points = exercise_count * 10
    bonus = loops_completed * 5
    points = base_points + bonus
    xp = points  # 1:1 for now
    return points, xp
