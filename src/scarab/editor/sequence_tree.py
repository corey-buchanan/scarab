"""Custom sequence tree: no arrows, drag-and-drop, reorder bindings."""

from rich.style import Style
from rich.text import Text

from textual import events
from textual.binding import Binding
from textual.message import Message
from textual.widgets import Tree


class ReorderUp(Message):
    """Request to move selected item up. Bubbles to parent."""
    pass


class ReorderDown(Message):
    """Request to move selected item down. Bubbles to parent."""
    pass


class DropItem(Message):
    """Request to move item from source_path to target_path. Bubbles to parent."""
    def __init__(self, source_path: tuple[int, ...], target_path: tuple[int, ...], drop_as_child: bool) -> None:
        self.source_path = source_path
        self.target_path = target_path
        self.drop_as_child = drop_as_child
        super().__init__()


class SequenceTree(Tree):
    """Tree with no arrows, drag-and-drop, and reorder bindings."""

    ICON_NODE = ""
    ICON_NODE_EXPANDED = ""

    BINDINGS = [*Tree.BINDINGS] + [
        Binding("alt+up", "move_up", "Move up", show=False),
        Binding("alt+down", "move_down", "Move down", show=False),
        Binding("option+up", "move_up", show=False),
        Binding("option+down", "move_down", show=False),
        Binding("ctrl+up", "move_up", show=False),
        Binding("ctrl+down", "move_down", show=False),
    ]

    DEFAULT_CSS = """
    SequenceTree .tree--guides {
        color: $surface-lighten-2;
    }
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._drag_node = None
        self._drag_line = -1

    def render_label(self, node, base_style: Style, style: Style) -> Text:
        """Render label without expand/collapse arrow prefix. Show drop indicator when dragging."""
        node_label = node._label.copy()
        node_label.stylize(style)
        if self._drag_node is not None and self.hover_line >= 0:
            node_line = getattr(node, "_line", -1)
            if node_line == self.hover_line:
                return Text.assemble("▸ ", node_label)
        return Text.assemble(node_label)

    def action_move_up(self) -> None:
        self.post_message(ReorderUp())

    def action_move_down(self) -> None:
        self.post_message(ReorderDown())

    def _get_line_from_event(self, event: events.MouseEvent) -> int:
        """Extract line number from event style meta, hover_line, or y offset."""
        style = getattr(event, "style", None)
        meta = getattr(style, "meta", None) if style else None
        if meta and isinstance(meta, dict) and "line" in meta:
            return int(meta["line"])
        if self.hover_line >= 0:
            return self.hover_line
        # Fallback: y offset in scrollable content
        try:
            offset = getattr(event, "offset", None)
            if offset is not None and hasattr(self, "scroll_offset") and hasattr(offset, "y"):
                scroll_y = self.scroll_offset.y
                return scroll_y + offset.y
        except Exception:
            pass
        return -1

    def _get_path_from_line(self, line: int) -> tuple[int, ...] | None:
        """Get path for node at line. Root returns () for root-level drop."""
        if line < 0:
            return None
        node = self.get_node_at_line(line)
        if node is None:
            return None
        if node == self.root:
            return ()  # Drop on root = add at root level
        return getattr(node, "_path", None)

    def on_mouse_down(self, event: events.MouseDown) -> None:
        line = self._get_line_from_event(event)
        if line >= 0:
            node = self.get_node_at_line(line)
            if node is not None and hasattr(node, "_path") and node._path is not None:
                self._drag_node = node
                self._drag_line = line

    def on_mouse_up(self, event: events.MouseUp) -> None:
        if self._drag_node is None:
            return
        source_path = getattr(self._drag_node, "_path", None)
        if source_path is None:
            self._drag_node = None
            self._drag_line = -1
            return
        line = self._get_line_from_event(event)
        target_path = self._get_path_from_line(line)
        node = self.get_node_at_line(line)
        self._drag_node = None
        self._drag_line = -1
        if target_path is None and node != self.root:
            return
        if source_path == target_path:
            return
        # drop_as_child: root or superset (has children)
        drop_as_child = node == self.root or (node is not None and hasattr(node, "_children") and len(node._children) > 0)
        if target_path is None:
            target_path = ()
        self.post_message(DropItem(source_path, target_path, drop_as_child))
