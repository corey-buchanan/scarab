"""Workout, SuperSet, and ExerciseRef models for YAML workout schema."""

from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator


class ExerciseRef(BaseModel):
    """Standalone exercise or exercise within a super-set."""

    type: Literal["exercise"] = "exercise"
    id: str = Field(default="", description="Exercise ID from catalog")
    sets: int = Field(default=1, ge=1, description="Sets (for standalone); ignored when inside super-set")
    reps: int = Field(default=10, ge=1, description="Repetitions")
    rest_sec: int = Field(default=30, ge=0, description="Rest seconds after exercise")
    notes: str = Field(default="", description="Optional notes")
    hold_sec: int | None = Field(default=None, ge=0, description="Hold seconds for static exercises")

    @field_validator("reps", "sets", mode="before")
    @classmethod
    def _clamp_min_one(cls, v):
        """Coerce to at least 1 instead of raising validation error."""
        if v is not None and isinstance(v, (int, float)):
            return max(1, int(v))
        return v


class SuperSet(BaseModel):
    """Super-set: labeled group with sets, optional rest, and nested items (exercises or super-sets)."""

    type: Literal["superset"] = "superset"
    label: str | None = Field(default=None, description="Optional label, e.g. Warmup")
    sets: int | dict[int, int] = Field(
        default=3,
        description="Sets: int for all levels, or {1: 3, 2: 5} per level",
    )
    rest_between_sets: int | None = Field(
        default=None,
        description="Rest (seconds) between sets",
    )
    items: list["WorkoutItem"] = Field(
        default_factory=list,
        description="Nested items: exercises or super-sets",
    )

    def get_sets_for_level(self, level: int) -> int:
        """Return number of sets for given level."""
        if isinstance(self.sets, int):
            return self.sets
        return self.sets.get(level, self.sets.get(1, 1))


WorkoutItem = Annotated[ExerciseRef | SuperSet, Field(discriminator="type")]

SuperSet.model_rebuild()


class Workout(BaseModel):
    """Top-level workout schema."""

    name: str = Field(..., description="Workout name")
    items: list[WorkoutItem] = Field(
        default_factory=list,
        description="Top-level items: exercises or super-sets",
    )

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

        # Migrate legacy "loops" to "items"
        if "loops" in data and "items" not in data:
            items = []
            for loop in data["loops"]:
                s = loop.get("sets")
                if isinstance(s, dict):
                    loop["sets"] = {int(k): int(v) for k, v in s.items()}
                items.append({
                    "type": "superset",
                    "label": loop.get("label"),
                    "sets": loop.get("sets", 3),
                    "rest_between_sets": loop.get("rest_between_sets"),
                    "items": [{"type": "exercise", **ex} for ex in loop.get("exercises", [])],
                })
            data["items"] = items
            del data["loops"]

        # Normalize sets in nested supersets
        def _norm(d):
            if isinstance(d, dict):
                if d.get("type") == "superset":
                    s = d.get("sets")
                    if isinstance(s, dict):
                        d["sets"] = {int(k): int(v) for k, v in s.items()}
                    for it in d.get("items", []):
                        _norm(it)
            elif isinstance(d, list):
                for x in d:
                    _norm(x)
        _norm(data.get("items", []))

        try:
            return cls.model_validate(data)
        except AttributeError:
            return cls.parse_obj(data)

    def to_yaml(self, path: str) -> None:
        """Save workout to YAML file."""
        import ruamel.yaml

        def _to_dict(obj):
            if isinstance(obj, ExerciseRef):
                d = obj.model_dump(exclude_none=True)
                return {"type": "exercise", **d}
            if isinstance(obj, SuperSet):
                d = {
                    "type": "superset",
                    "label": obj.label,
                    "sets": obj.sets,
                    "items": [_to_dict(i) for i in obj.items],
                }
                if obj.rest_between_sets is not None:
                    d["rest_between_sets"] = obj.rest_between_sets
                return d
            return obj

        data = {
            "name": self.name,
            "items": [_to_dict(i) for i in self.items],
        }
        yaml = ruamel.yaml.YAML()
        yaml.indent(mapping=2, sequence=4, offset=2)
        with open(path, "w") as f:
            yaml.dump({k: v for k, v in data.items() if v is not None}, f)


# Legacy alias for playback compatibility during migration
Loop = SuperSet
