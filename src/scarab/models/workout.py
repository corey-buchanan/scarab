"""Workout, Loop, and ExerciseRef models for YAML workout schema."""

from pathlib import Path

from pydantic import BaseModel, Field


class ExerciseRef(BaseModel):
    """Reference to an exercise within a loop."""

    id: str = Field(..., description="Exercise ID from catalog")
    reps: int = Field(default=10, ge=1, description="Repetitions")
    rest_sec: int = Field(default=30, ge=0, description="Rest seconds after exercise")
    notes: str = Field(default="", description="Optional notes")
    hold_sec: int | None = Field(default=None, ge=0, description="Hold seconds for static exercises")


class Loop(BaseModel):
    """A loop (section) within a workout with optional label and sets config."""

    label: str | None = Field(default=None, description="Optional label, e.g. Warmup, Cooldown")
    sets: int | dict[int, int] = Field(
        ...,
        description="Sets: int for all levels, or {1: 3, 2: 5, 3: 7} per level",
    )
    exercises: list[ExerciseRef] = Field(default_factory=list)

    def get_sets_for_level(self, level: int) -> int:
        """Return number of sets for given level."""
        if isinstance(self.sets, int):
            return self.sets
        return self.sets.get(level, self.sets.get(1, 1))


class Workout(BaseModel):
    """Top-level workout schema."""

    name: str = Field(..., description="Workout name")
    loops: list[Loop] = Field(default_factory=list, description="Ordered list of loops")

    @classmethod
    def from_yaml(cls, path: str | Path) -> "Workout":
        """Load workout from YAML file."""
        import ruamel.yaml

        path = Path(path)
        yaml = ruamel.yaml.YAML()
        with open(path) as f:
            data = yaml.load(f)
        if data is None:
            data = {}
        # Normalize sets dict keys to int (YAML may load as str)
        for loop in data.get("loops", []):
            s = loop.get("sets")
            if isinstance(s, dict):
                loop["sets"] = {int(k): int(v) for k, v in s.items()}
        try:
            return cls.model_validate(data)
        except AttributeError:
            return cls.parse_obj(data)

    def to_yaml(self, path: str) -> None:
        """Save workout to YAML file."""
        import ruamel.yaml

        yaml = ruamel.yaml.YAML()
        yaml.indent(mapping=2, sequence=4, offset=2)
        with open(path, "w") as f:
            data = getattr(self, "model_dump", lambda **kw: self.dict(**kw))(exclude_none=True)
            yaml.dump(data, f)
