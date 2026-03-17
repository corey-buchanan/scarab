"""Load exercise catalog and workouts."""

from pathlib import Path

import ruamel.yaml

from scarab.data import EXERCISE_CATALOG_PATH
from scarab.models.exercise import Exercise
from scarab.models.workout import Workout


def load_exercise_catalog(path: Path | None = None) -> list[Exercise]:
    """Load exercise catalog from YAML."""
    path = path or EXERCISE_CATALOG_PATH
    if not path.exists():
        return []
    yaml = ruamel.yaml.YAML()
    with open(path) as f:
        data = yaml.load(f)
    entries = data.get("exercises", [])
    result = []
    for e in entries:
        try:
            result.append(Exercise.model_validate(e))
        except AttributeError:
            result.append(Exercise.parse_obj(e))
    return result


def get_exercise_by_id(catalog: list[Exercise], exercise_id: str) -> Exercise | None:
    """Look up exercise by id."""
    for ex in catalog:
        if ex.id == exercise_id:
            return ex
    return None


def catalog_autocomplete_items(catalog: list[Exercise]) -> list[str]:
    """Return list of searchable strings for autocomplete (id, name, aliases)."""
    items: list[str] = []
    for ex in catalog:
        items.append(ex.id)
        items.append(ex.name)
        items.extend(ex.aliases)
    return list(dict.fromkeys(items))  # preserve order, dedupe
