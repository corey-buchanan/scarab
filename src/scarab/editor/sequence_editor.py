"""Interactive sequence editor using Tree widget + detail panel."""

from pathlib import Path

from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Button, Input, Label, Static, Tree
from scarab.data import WORKOUTS_DIR
from scarab.editor.sequence_tree import DropItem, ReorderDown, ReorderUp, SequenceTree
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


def _path_for_index(
    tgt_path: tuple[int, ...], insert_idx: int, drop_as_child: bool
) -> tuple[int, ...]:
    """Compute path of inserted item after drop."""
    if drop_as_child:
        return tgt_path + (insert_idx,)
    if not tgt_path:
        return (insert_idx,)
    return tgt_path[:-1] + (insert_idx,)


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

        def add_children(parent_node, items: list[WorkoutItem], base_path: tuple[int, ...]) -> None:
            for i, item in enumerate(items):
                path = base_path + (i,)
                if isinstance(item, ExerciseRef):
                    label = f"{item.id or '(empty)'} ×{item.reps} rest {item.rest_sec}s"
                    if item.sets > 1:
                        label += f" ({item.sets} sets)"
                    node = parent_node.add_leaf(label)
                else:
                    fixed = list(item.sets.values())[0] if isinstance(item.sets, dict) else item.sets
                    rest = item.rest_between_sets or 0
                    label = item.label or f"Super-set"
                    suffix = f" ({fixed} sets" + (f", {rest}s rest" if rest else "") + ")"
                    node = parent_node.add(f"{label}{suffix}", expand=True, allow_expand=False)
                    add_children(node, item.items, path)
                node._path = path  # type: ignore

        add_children(root, self.workout.items, ())

    def _persist_current_detail(self) -> None:
        """Persist detail form into workout model at _selected_path. Call before switching selection."""
        if self._selected_path is None:
            return
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
            content.mount(Static("Drag items to reorder or move in/out of super-sets. Ctrl+↑/↓ to reorder.", classes="detail-section"))
            return

        item = _get_item_at_path(self.workout, self._selected_path)
        if item is None:
            content.mount(Static("Invalid selection.", classes="detail-section"))
            return

        if isinstance(item, ExerciseRef):
            is_standalone = _parent_path(self._selected_path) is None
            content.mount(Label("Exercise", classes="detail-section"))
            content.mount(ExerciseRow(item, self._candidates, show_sets=is_standalone))
            content.mount(
                Horizontal(
                    Button("Remove", id="remove-item", variant="warning"),
                    classes="detail-row",
                )
            )
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
                Input(value=str(rest_val), type="integer", placeholder="0", classes="superset-rest"),
                classes="detail-row",
            ))
            content.mount(
                Horizontal(
                    Button("Remove", id="remove-item", variant="warning"),
                    classes="detail-row",
                )
            )

    def _rebuild_and_reselect(self) -> None:
        """Rebuild tree and keep current selection if still valid."""
        path = self._selected_path
        self._build_tree()
        self._selected_path = path
        self._update_detail()

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
        # Validate path still exists (node may be stale after drag/rebuild)
        if _get_item_at_path(self.workout, new_path) is None:
            return
        # Persist current before switching
        self._persist_current_detail()
        self._selected_path = new_path
        self._update_detail()

    def _add_exercise_or_superset(self, is_superset: bool) -> None:
        """Add exercise or superset at root, or into selected superset."""
        self._persist_current_detail()
        if self._selected_path is not None:
            item = _get_item_at_path(self.workout, self._selected_path)
            if isinstance(item, SuperSet):
                if is_superset:
                    item.items.append(SuperSet(sets=3, items=[ExerciseRef(id="", reps=10, rest_sec=30)]))
                    self._selected_path = self._selected_path + (len(item.items) - 1,)
                else:
                    item.items.append(ExerciseRef(id="", reps=10, rest_sec=30))
                    self._selected_path = self._selected_path + (len(item.items) - 1,)
                self._rebuild_and_reselect()
                return
        # Add at root
        if is_superset:
            self.workout.items.append(SuperSet(sets=3, items=[ExerciseRef(id="", reps=10, rest_sec=30)]))
        else:
            self.workout.items.append(ExerciseRef(id="", sets=1, reps=10, rest_sec=30))
        self._selected_path = (len(self.workout.items) - 1,)
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
            name_inp = self.query_one("#workout-name-input", Input) if self.query("#workout-name-input") else None
            if name_inp:
                self.workout.name = name_inp.value.strip() or self.workout.name
            self.query_one("#editor-tree", SequenceTree).root.label = self.workout.name
            path = self.workout_path or WORKOUTS_DIR / f"{self._slug(self.workout.name)}.yaml"
            self.workout.to_yaml(path)
            self.workout_path = path
            self.notify(f"Saved to {path}", severity="information")

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
                    self._selected_path = _parent_path(self._selected_path)
                    if idx > 0:
                        self._selected_path = (self._selected_path or ()) + (idx - 1,)
                    self._rebuild_and_reselect()

    def _handle_move_up(self) -> None:
        """Move selected item up (Alt+Up)."""
        if self._selected_path is None:
            return
        parent_info = _get_parent_and_index(self.workout, self._selected_path)
        if parent_info is None:
            return
        parent_list, idx = parent_info
        if idx <= 0:
            return
        self._persist_current_detail()
        parent_list[idx], parent_list[idx - 1] = parent_list[idx - 1], parent_list[idx]
        self._selected_path = self._selected_path[:-1] + (idx - 1,)
        self._rebuild_and_reselect()

    def _handle_move_down(self) -> None:
        """Move selected item down (Alt+Down)."""
        if self._selected_path is None:
            return
        parent_info = _get_parent_and_index(self.workout, self._selected_path)
        if parent_info is None:
            return
        parent_list, idx = parent_info
        if idx >= len(parent_list) - 1:
            return
        self._persist_current_detail()
        parent_list[idx], parent_list[idx + 1] = parent_list[idx + 1], parent_list[idx]
        self._selected_path = self._selected_path[:-1] + (idx + 1,)
        self._rebuild_and_reselect()

    def on_reorder_up(self, _event: ReorderUp) -> None:
        """Handle Alt+Up from SequenceTree."""
        self._handle_move_up()

    def on_reorder_down(self, _event: ReorderDown) -> None:
        """Handle Ctrl/Alt+Down from SequenceTree."""
        self._handle_move_down()

    def on_drop_item(self, event: DropItem) -> None:
        """Handle drag-drop: move item from source to target."""
        self._persist_current_detail()
        src_path = event.source_path
        tgt_path = event.target_path
        drop_as_child = event.drop_as_child
        if not src_path:
            return
        # Prevent dropping parent into its own descendant
        if drop_as_child and tgt_path and len(tgt_path) >= len(src_path) and tgt_path[: len(src_path)] == src_path:
            return
        src_info = _get_parent_and_index(self.workout, src_path)
        src_item = _get_item_at_path(self.workout, src_path)
        if src_info is None or src_item is None:
            return
        src_parent, src_idx = src_info
        src_parent.pop(src_idx)
        if drop_as_child:
            if not tgt_path:
                tgt_parent = self.workout.items
                insert_idx = len(tgt_parent)
            else:
                tgt_item = _get_item_at_path(self.workout, tgt_path)
                if not isinstance(tgt_item, SuperSet):
                    src_parent.insert(src_idx, src_item)
                    self._rebuild_and_reselect()
                    return
                tgt_parent = tgt_item.items
                insert_idx = len(tgt_parent)
        else:
            if not tgt_path:
                tgt_parent = self.workout.items
                insert_idx = 0
            else:
                tgt_info = _get_parent_and_index(self.workout, tgt_path)
                if tgt_info is None:
                    src_parent.insert(src_idx, src_item)
                    self._rebuild_and_reselect()
                    return
                tgt_parent, tgt_idx = tgt_info
                insert_idx = tgt_idx
                if src_parent is tgt_parent and src_idx < tgt_idx:
                    insert_idx = tgt_idx - 1
        tgt_parent.insert(insert_idx, src_item)
        self._selected_path = _path_for_index(tgt_path, insert_idx, drop_as_child)
        self._suppress_node_selected = True  # Drop will trigger NodeSelected from click; ignore it
        self._rebuild_and_reselect()

    def _slug(self, name: str) -> str:
        return "".join(c if c.isalnum() or c in " -_" else "" for c in name).strip().replace(" ", "_").lower() or "workout"
