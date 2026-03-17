"""User stats, XP, and character leveling."""

from pydantic import BaseModel, Field


class UserStats(BaseModel):
    """User progress and character leveling."""

    total_points: int = Field(default=0, ge=0)
    total_xp: int = Field(default=0, ge=0)
    workouts_completed: int = Field(default=0, ge=0)
    exercises_completed: int = Field(default=0, ge=0)

    def add_workout_completion(self, points: int, xp: int, exercise_count: int) -> None:
        """Record a completed workout."""
        self.total_points += points
        self.total_xp += xp
        self.workouts_completed += 1
        self.exercises_completed += exercise_count

    def level(self) -> int:
        """Character level from XP. Simple curve: 100 XP per level."""
        if self.total_xp <= 0:
            return 1
        return 1 + self.total_xp // 100

    def xp_for_next_level(self) -> int:
        """XP needed from current level to reach next."""
        return 100
