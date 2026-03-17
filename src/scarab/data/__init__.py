"""Data loading and paths."""

from pathlib import Path

DATA_DIR = Path(__file__).parent
EXERCISES_DIR = DATA_DIR / "exercises"
WORKOUTS_DIR = DATA_DIR / "workouts"
FRAMES_DIR = DATA_DIR / "frames"

EXERCISE_CATALOG_PATH = EXERCISES_DIR / "catalog.yaml"
