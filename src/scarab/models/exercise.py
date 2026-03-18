"""Exercise catalog model."""

from pydantic import BaseModel, Field


class Exercise(BaseModel):
    """Exercise definition from catalog."""

    id: str = Field(..., description="Unique ID, e.g. jumping_jacks")
    name: str = Field(..., description="Display name")
    category: str = Field(default="general", description="cardio, strength, metcon, hiit, combat, stretching, yoga, wellness")
    difficulty: int = Field(default=3, ge=1, le=5, description="1=Light to 5=Advanced")
    static: bool = Field(default=False, description="True for holds (e.g. plank), False for dynamic")
    animation_id: str | None = Field(default=None, description="Links to frames; defaults to id if not set")

    def resolve_animation_id(self) -> str:
        """Return animation_id or fallback to id."""
        return self.animation_id or self.id
