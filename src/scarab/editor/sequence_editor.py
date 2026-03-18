"""Interactive sequence editor using Tree widget + detail panel."""

from pathlib import Path

from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Button, Input, Label, Static, Tree
from scarab.data import WORKOUTS_DIR
from scarab.editor.sequence_tree import DropItem, SequenceTree
from scarab.data.loader import catalog_autocomplete_items, load_exercise_catalog
from scarab.models.workout import ExerciseRef, SuperSet, Workout, WorkoutItem
from scarab.editor.loop_section import ExerciseRow


def _get_item_at_path(workout: Workout, path: tuple[int, ...]) -> WorkoutItem | None:
    """Get WorkoutItem at path. path=() is invalid; (0,) = first root item."""
    if not path:
        return None
    items: list[WorkoutItem] = workout.items
    for i, idx in enumerate(path):
        if idx < 0 or idx >= len(items):
            return None
        item = items[idx]
        if i == len(path) - 1:
            return item
        if not isinstance(item, SuperSet):
            return None
        items = item.items
    return None


def _get_parent_and_index(workout: Workout, path: tuple[int, ...]) -> tuple[list[WorkoutItem], int] | None:
    """Get (parent_list, index) for the item at path, or None if invalid."""
    if not path:
        return None
    items: list[WorkoutItem] = workout.items
    for i, idx in enumerate(path[:-1]):
        if idx < 0 or idx >= len(items):
            return None
        item = items[idx]
        if not isinstance(item, SuperSet):
            return None
        items = item.items
    last = path[-1]
    if last < 0 or last >= len(items):
        return None
    return (items, last)


def _parent_path(path: tuple[int, ...]) -> tuple[int, ...] | None:
    """Path to parent. None for root-level items (parent is workout)."""
    if len(path) <= 1:
        return None
    return path[:-1]


def _is_end_path(path: tuple[int, ...]) -> bool:
    """True if path is a blank-row 'insert at end' marker."""
    return bool(path and path[-1] == "__end__")


def _get_insert_parent_and_index(
    workout: Workout, path: tuple[int, ...]
) -> tuple[list[WorkoutItem], int] | None:
    """Get (parent_list, insert_index) for inserting before the given path. Handles __end__ paths."""
    if not path:
        return (workout.items, 0)
    if path == ("__end__",):
        return (workout.items, len(workout.items))
    if path[-1] == "__end__":
        # Path like (i, "__end__") or (i, j, "__end__") - insert at end of that superset
        parent_path = path[:-1]
        items: list[WorkoutItem] = workout.items
        for idx in parent_path:
            if idx < 0 or idx >= len(items):
                return None
            item = items[idx]
            if not isinstance(item, SuperSet):
                return None
            items = item.items
        return (items, len(items))
    # Normal path: insert before this item
    info = _get_parent_and_index(workout, path)
    if info is None:
        return None
    return info


def _format_exercise_label(item: ExerciseRef) -> str:
    """Format exercise for tree: (empty), reps or timed, rest only if > 0, set/sets."""
    name = item.id or "(empty)"
    if item.hold_sec and item.hold_sec > 0:
        amount = f"{item.hold_sec}s"
    else:
        amount = f"×{item.reps}"
    rest_part = f" rest {item.rest_sec}s" if item.rest_sec and item.rest_sec > 0 else ""
    label = f"{name} {amount}{rest_part}"
    if item.sets > 1:
        label += f" ({item.sets} sets)"
    return label


def _format_superset_suffix(sets: int, rest: int) -> str:
    """Format superset suffix with correct set/sets pluralization, omit rest if 0."""
    s = "set" if sets == 1 else "sets"
    rest_part = f", {rest}s rest" if rest else ""
    return f" ({sets} {s}{rest_part})"


def _has_blank_exercise_ids(workout: Workout) -> bool:
    """Return True if any ExerciseRef has empty id."""

    def check(items: list[WorkoutItem]) -> bool:
        for item in items:
            if isinstance(item, ExerciseRef):
                if not (item.id or "").strip():
                    return True
            elif isinstance(item, SuperSet):
                if check(item.items):
                    return True
        return False

    return check(workout.items)


def _path_for_inserted_item(
    workout: Workout, parent_list: list[WorkoutItem], insert_idx: int
) -> tuple[int, ...]:
    """Compute path of item after inserting into parent_list at insert_idx."""
    if parent_list is workout.items:
        return (insert_idx,)
    for i, item in enumerate(workout.items):
        if isinstance(item, SuperSet) and item.items is parent_list:
            return (i, insert_idx)
    return (insert_idx,)  # fallback


class SequenceEditorScreen(Container):
    """Tree-based sequence builder: super-sets and exercises."""

    DEFAULT_CSS = """
    SequenceEditorScreen {
        layout: vertical;
        height: 1fr;
        padding: 1 2;
    }
    #workout-name-row { height: auto; padding: 0 0 1 0; }
    #editor-main {
        height: 1fr;
        layout: horizontal;
    }
    #editor-tree {
        width: 35%;
        min-width: 20;
        height: 100%;
        border: solid $primary;
        padding: 1;
    }
    #editor-detail {
        width: 1fr;
        height: 100%;
        padding: 0 0 0 2;
        layout: vertical;
    }
    #editor-detail-content {
        height: 1fr;
        overflow-y: auto;
        border: solid $primary;
        padding: 1;
    }
    #editor-toolbar {
        height: auto;
        padding: 1 0 0 0;
    }
    #workout-name-input {
        width: 100%;
        min-width: 15;
    }
    .detail-section { padding: 0 0 1 0; }
    .detail-row { padding: 0 0 0 1; margin: 0 0 1 0; }
    """

    def __init__(self, workout_path: Path | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.workout_path = workout_path
        self.workout = self._load_or_new(workout_path)
        self._catalog = load_exercise_catalog()
        self._candidates = catalog_autocomplete_items(self._catalog)
        self._selected_path: tuple[int, ...] | None = None  # path to selected item
        self._refresh_timer: object | None = None  # Timer for debounced tree refresh
        self._suppress_node_selected: bool = False  # Skip next NodeSelected (after drop rebuild)

    def _load_or_new(self, path: Path | None) -> Workout:
        if path and Path(path).exists():
            return Workout.from_yaml(path)
        return Workout(
            name="New Workout",
            items=[SuperSet(sets=3, items=[ExerciseRef(id="", reps=10, rest_sec=30)])],
        )

    def compose(self):
        from textual.app import ComposeResult

        yield Horizontal(
            Label("Workout name:"),
            Input(value=self.workout.name, placeholder="e.g. Full Body Circuit", id="workout-name-input"),
            id="workout-name-row",
        )
        with Horizontal(id="editor-main"):
            yield SequenceTree(self.workout.name, id="editor-tree")
            with Vertical(id="editor-detail"):
                yield ScrollableContainer(id="editor-detail-content")
        yield Horizontal(
            Button("+ Exercise", id="add-exercise"),
            Button("+ Super-set", id="add-superset"),
            Button("Save", id="save-workout", variant="success"),
            Button("Back (h)", id="back"),
            id="editor-toolbar",
        )

    def on_mount(self) -> None:
        self._build_tree()
        self._update_detail()

    def _build_tree(self) -> None:
        tree = self.query_one("#editor-tree", SequenceTree)
        tree.clear()
        root = tree.root
        root.label = self.workout.name
        root.expand()

        def add_children(parent_node, items: list[WorkoutItem], superset_path: tuple[int, ...]) -> None:
            """Add items to parent_node. base_path is path to this superset (for blank row)."""
            for i, item in enumerate(items):
                path = superset_path + (i,)
                if isinstance(item, ExerciseRef):
                    label = _format_exercise_label(item)
                    node = parent_node.add_leaf(label)
                else:
                    fixed = list(item.sets.values())[0] if isinstance(item.sets, dict) else item.sets
                    rest = item.rest_between_sets or 0
                    label = item.label or f"Super-set"
                    suffix = _format_superset_suffix(fixed, rest)
                    node = parent_node.add(f"{label}{suffix}", expand=True, allow_expand=False)
                    add_children(node, item.items, path)
                    end_node = node.add_leaf("")
                    end_node._path = path + ("__end__",)  # type: ignore
                node._path = path  # type: ignore

        items = self.workout.items
        for i, item in enumerate(items):
            path = (i,)
            if isinstance(item, ExerciseRef):
                label = _format_exercise_label(item)
                node = root.add_leaf(label)
            else:
                fixed = list(item.sets.values())[0] if isinstance(item.sets, dict) else item.sets
                rest = item.rest_between_sets or 0
                label = item.label or f"Super-set"
                suffix = _format_superset_suffix(fixed, rest)
                node = root.add(f"{label}{suffix}", expand=True, allow_expand=False)
                add_children(node, item.items, path)
                end_node = node.add_leaf("")
                end_node._path = (i, "__end__")  # type: ignore  # path is (i,) for top-level superset
            node._path = path  # type: ignore
        end_node = root.add_leaf("")
        end_node._path = ("__end__",)  # type: ignore

    def _persist_current_detail(self) -> None:
        """Persist detail form into workout model at _selected_path. Call before switching selection."""
        if self._selected_path is None:
            return
        if _is_end_path(self._selected_path):
            return  # Nothing to persist for blank row
        item = _get_item_at_path(self.workout, self._selected_path)
        parent_info = _get_parent_and_index(self.workout, self._selected_path)
        if item is None or parent_info is None:
            return
        parent_list, idx = parent_info

        if isinstance(item, ExerciseRef):
            if not self.query(ExerciseRow):
                return
            try:
                row = self.query_one(ExerciseRow)
                parent_list[idx] = row.get_ref()
            except Exception:
                pass  # Widget may have been removed (e.g. by rebuild during drag)
        elif isinstance(item, SuperSet):
            if not self.query(".superset-label"):
                return
            try:
                label_inp = self.query_one(".superset-label", Input)
                sets_inp = self.query_one(".superset-sets", Input)
                rest_inp = self.query_one(".superset-rest", Input) if self.query(".superset-rest") else None
                sets_val = int(sets_inp.value or "3")
            except (ValueError, Exception):
                return
            try:
                rest_val = int(rest_inp.value or "0") if rest_inp else None
            except ValueError:
                rest_val = None
            parent_list[idx] = SuperSet(
                label=label_inp.value.strip() or None,
                sets=sets_val,
                items=list(item.items),
                rest_between_sets=rest_val if rest_val and rest_val > 0 else None,
            )

    def _update_detail(self) -> None:
        content = self.query_one("#editor-detail-content", ScrollableContainer)
        content.remove_children()

        if self._selected_path is None:
            content.mount(Static("Select an exercise or super-set in the tree.", classes="detail-section"))
            content.mount(Static("Drag items to reorder. Use + Exercise / + Super-set to add at same level.", classes="detail-section"))
            return

        if _is_end_path(self._selected_path):
            content.mount(Static("Insert at end.", classes="detail-section"))
            content.mount(Static("Drop items here or use + Exercise / + Super-set to add.", classes="detail-section"))
            return

        item = _get_item_at_path(self.workout, self._selected_path)
        if item is None:
            content.mount(Static("Invalid selection.", classes="detail-section"))
            return

        if isinstance(item, ExerciseRef):
            is_standalone = _parent_path(self._selected_path) is None
            content.mount(Label("Exercise", classes="detail-section"))
            content.mount(ExerciseRow(item, self._candidates, show_sets=is_standalone))
        elif isinstance(item, SuperSet):
            fixed = list(item.sets.values())[0] if isinstance(item.sets, dict) else item.sets
            rest_val = item.rest_between_sets or 0
            content.mount(Label("Super-set", classes="detail-section"))
            section = Vertical(classes="detail-section")
            content.mount(section)
            section.mount(Horizontal(
                Label("Label:"),
                Input(value=item.label or "", placeholder="e.g. Warmup", classes="superset-label"),
                classes="detail-row",
            ))
            section.mount(Horizontal(
                Label("Sets:"),
                Input(value=str(fixed), type="integer", classes="superset-sets"),
                classes="detail-row",
            ))
            section.mount(Horizontal(
                Label("Rest between sets:"),
                Input(
                    value="" if rest_val == 0 else str(rest_val),
                    type="integer",
                    placeholder="0",
                    valid_empty=True,
                    classes="superset-rest",
                ),
                classes="detail-row",
            ))
            content.mount(
                Horizontal(
                    Button("Remove", id="remove-item", variant="warning"),
                    classes="detail-row",
                )
            )

    def _rebuild_and_reselect(self) -> None:
        """Rebuild tree and keep current selection if still valid. Selects the node in the tree."""
        path = self._selected_path
        self._build_tree()
        self._selected_path = path
        self._update_detail()
        if path is not None and not _is_end_path(path):
            self.call_later(self._select_node_at_path, path)

    def _select_node_at_path(self, path: tuple[int, ...]) -> None:
        """Find and select the tree node at the given path. Expands parents so it's visible."""
        tree = self.query_one("#editor-tree", SequenceTree)
        node = tree.root
        for i, idx in enumerate(path):
            children = list(node.children)
            if idx < 0 or idx >= len(children):
                return
            node = children[idx]
            if i < len(path) - 1:
                node.expand()
        tree.select_node(node)

    def _schedule_tree_refresh(self) -> None:
        """Debounce: persist and refresh tree after input changes."""
        if self._refresh_timer is not None:
            self._refresh_timer.stop()
        self._refresh_timer = self.set_timer(0.35, self._do_tree_refresh)

    def _do_tree_refresh(self) -> None:
        """Persist detail and refresh tree labels."""
        self._refresh_timer = None
        name_inp = self.query_one("#workout-name-input", Input) if self.query("#workout-name-input") else None
        if name_inp:
            self.workout.name = name_inp.value.strip() or self.workout.name
        self._persist_current_detail()
        self._build_tree()

    def on_input_changed(self, event: Input.Changed) -> None:
        """When inputs change, schedule tree refresh so labels update."""
        name_inp = self.query_one("#workout-name-input", Input) if self.query("#workout-name-input") else None
        if name_inp and event.control == name_inp:
            self._schedule_tree_refresh()
            return
        detail = self.query_one("#editor-detail-content", ScrollableContainer)
        if detail in event.control.ancestors:
            self._schedule_tree_refresh()

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        if self._suppress_node_selected:
            self._suppress_node_selected = False
            return
        node = event.node
        if not hasattr(node, "_path"):
            return
        new_path = getattr(node, "_path", None)
        if new_path is None:
            return
        # Validate: real item exists, or valid __end__ path
        if _is_end_path(new_path):
            if _get_insert_parent_and_index(self.workout, new_path) is None:
                return
        elif _get_item_at_path(self.workout, new_path) is None:
            return
        # Persist current before switching
        self._persist_current_detail()
        self._selected_path = new_path
        self._update_detail()

    def _add_exercise_or_superset(self, is_superset: bool) -> None:
        """Add exercise or superset at same level as selection, just below it (or at end if blank row)."""
        self._persist_current_detail()
        insert_info = None
        if self._selected_path is not None:
            insert_info = _get_insert_parent_and_index(self.workout, self._selected_path)
            if insert_info is not None and _is_end_path(self._selected_path):
                # Blank row: insert at end (already correct from _get_insert_parent_and_index)
                pass
            elif insert_info is not None:
                # Real item: insert below it (index + 1)
                parent_list, idx = insert_info
                insert_info = (parent_list, idx + 1)
        if insert_info is None:
            insert_info = (self.workout.items, len(self.workout.items))
        parent_list, insert_idx = insert_info
        new_item: WorkoutItem = (
            SuperSet(sets=3, items=[ExerciseRef(id="", reps=10, rest_sec=30)])
            if is_superset
            else ExerciseRef(id="", sets=1, reps=10, rest_sec=30)
        )
        parent_list.insert(insert_idx, new_item)
        self._selected_path = _path_for_inserted_item(self.workout, parent_list, insert_idx)
        self._rebuild_and_reselect()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id

        if btn_id == "add-exercise":
            self._add_exercise_or_superset(is_superset=False)
            return
        if btn_id == "add-superset":
            self._add_exercise_or_superset(is_superset=True)
            return
        if btn_id == "save-workout":
            self._persist_current_detail()
            if _has_blank_exercise_ids(self.workout):
                self.notify("Cannot save: all exercises must have a name.", severity="error")
                return
            name_inp = self.query_one("#workout-name-input", Input) if self.query("#workout-name-input") else None
            if name_inp:
                self.workout.name = name_inp.value.strip() or self.workout.name
            self.query_one("#editor-tree", SequenceTree).root.label = self.workout.name
            path = self.workout_path or WORKOUTS_DIR / f"{self._slug(self.workout.name)}.yaml"
            self.workout.to_yaml(path)
            self.workout_path = path
            self.notify(f"Saved successfully", severity="information")

        elif btn_id == "back":
            self._persist_current_detail()
            self.app.action_editor_picker()

        elif btn_id == "remove-item":
            if self._selected_path is None:
                return
            parent_info = _get_parent_and_index(self.workout, self._selected_path)
            if parent_info is None:
                return
            self._persist_current_detail()
            parent_list, idx = parent_info
            parent_list.pop(idx)
            p_path = _parent_path(self._selected_path)
            if p_path is not None:
                if parent_list:
                    new_idx = min(idx, len(parent_list) - 1)
                    self._selected_path = p_path + (new_idx,)
                else:
                    self._selected_path = p_path
            else:
                self._selected_path = (0,) if self.workout.items else None
            self._rebuild_and_reselect()

        elif btn_id == "remove-exercise":
            row = event.button.query_ancestor(ExerciseRow)
            if row is not None and self._selected_path is not None:
                parent_info = _get_parent_and_index(self.workout, self._selected_path)
                if parent_info:
                    parent_list, idx = parent_info
                    parent_list.pop(idx)
                    p_path = _parent_path(self._selected_path)
                    if p_path is not None:
                        if parent_list:
                            new_idx = min(idx, len(parent_list) - 1)
                            self._selected_path = p_path + (new_idx,)
                        else:
                            self._selected_path = p_path
                    else:
                        self._selected_path = (0,) if self.workout.items else None
                    self._rebuild_and_reselect()

    def on_drop_item(self, event: DropItem) -> None:
        """Handle drag-drop: insert source before target (same level). Target can be __end__ for insert-at-end."""
        self._persist_current_detail()
        src_path = event.source_path
        tgt_path = event.target_path
        if not src_path:
            return
        # Prevent dropping parent into its own descendant
        if tgt_path and len(tgt_path) >= len(src_path) and tgt_path[: len(src_path)] == src_path:
            return
        src_info = _get_parent_and_index(self.workout, src_path)
        src_item = _get_item_at_path(self.workout, src_path)
        if src_info is None or src_item is None:
            return
        insert_info = _get_insert_parent_and_index(self.workout, tgt_path)
        if insert_info is None:
            return
        src_parent, src_idx = src_info
        tgt_parent, insert_idx = insert_info
        src_parent.pop(src_idx)
        if src_parent is tgt_parent and src_idx < insert_idx:
            insert_idx -= 1
        tgt_parent.insert(insert_idx, src_item)
        self._selected_path = _path_for_inserted_item(self.workout, tgt_parent, insert_idx)
        self._suppress_node_selected = True  # Drop will trigger NodeSelected from click; ignore it
        self._rebuild_and_reselect()

    def _slug(self, name: str) -> str:
        return "".join(c if c.isalnum() or c in " -_" else "" for c in name).strip().replace(" ", "_").lower() or "workout"
