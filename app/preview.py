"""
Preview window – visual grid preview with drag & drop reordering.
"""

import tkinter as tk
from dataclasses import dataclass
from typing import List, Optional

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from .export.streamdeck import DEVICE_PRESETS, process_label_for_display

# Sentinel values for navigation button slots
NAV_PREV = "__NAV_PREV__"
NAV_NEXT = "__NAV_NEXT__"

# Visual constants
CELL_SIZE = 72
CELL_GAP = 4
BG_ITEM = "#2a2a2a"
BG_EMPTY = "#3a3a3a"
BG_NAV = "#555555"
BG_DRAG_SOURCE = "#1a5276"
BG_DRAG_TARGET = "#1e8449"
BORDER_COLOR = "#555555"
NAV_TEXT_COLOR = "#FFFFFF"


@dataclass
class PreviewItem:
    """Lightweight copy of a Treeview row for preview purposes."""
    iid: str
    label: str
    keystroke: str
    text_color: str
    split_label: bool


class PreviewWindow(tk.Toplevel):
    """Floating preview window showing the Stream Deck grid layout."""

    def __init__(self, parent, items: List[PreviewItem], preset: dict, max_pages: int):
        super().__init__(parent)
        self.parent = parent
        self.all_items = list(items)  # flat ordered list of included items
        self.cols = preset["cols"]
        self.rows = preset["rows"]
        self.max_pages = max_pages
        self.total_slots = self.cols * self.rows

        # Page slot arrays: each is a list of length total_slots
        # containing PreviewItem, NAV_PREV, NAV_NEXT, or None
        self.page_slots: List[List] = []
        self.overflow_count = 0

        # Drag state
        self._drag_source: Optional[tuple] = None  # (page_idx, slot_idx)
        self._drag_highlight: Optional[tuple] = None  # (page_idx, slot_idx)

        # Canvas references per page
        self._canvases: List[tk.Canvas] = []

        self._paginate()
        self._build_ui()

        self.title(f"Preview — {self.cols}×{self.rows}")
        self.resizable(True, True)
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.transient(parent)
        self.grab_set()
        self.focus_set()

    # ------------------------------------------------------------------
    # Pagination (mirrors _export_with_pages logic)
    # ------------------------------------------------------------------
    def _paginate(self):
        n = len(self.all_items)

        if n <= self.total_slots:
            total_pages = 1
        else:
            first_cap = self.total_slots - 1
            last_cap = self.total_slots - 1
            mid_cap = self.total_slots - 2
            remaining = n - first_cap
            if remaining <= last_cap:
                total_pages = 2
            else:
                remaining -= last_cap
                total_pages = 2 + max(0, (remaining + mid_cap - 1) // mid_cap)

        total_pages = min(total_pages, self.max_pages, 10)

        self.page_slots = []
        item_offset = 0

        for page_num in range(total_pages):
            has_prev = total_pages > 1 and page_num > 0
            has_next = total_pages > 1 and page_num < total_pages - 1
            nav_count = (1 if has_prev else 0) + (1 if has_next else 0)
            page_capacity = self.total_slots - nav_count

            page_items = self.all_items[item_offset:item_offset + page_capacity]
            item_offset += len(page_items)

            slots = [None] * self.total_slots
            item_idx = 0
            for row_idx in range(self.rows):
                for col_idx in range(self.cols):
                    slot_idx = row_idx * self.cols + col_idx
                    if (col_idx, row_idx) == (0, self.rows - 1) and has_prev:
                        slots[slot_idx] = NAV_PREV
                    elif (col_idx, row_idx) == (self.cols - 1, self.rows - 1) and has_next:
                        slots[slot_idx] = NAV_NEXT
                    elif item_idx < len(page_items):
                        slots[slot_idx] = page_items[item_idx]
                        item_idx += 1

            self.page_slots.append(slots)

        self.overflow_count = max(0, n - item_offset)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        canvas_w = self.cols * (CELL_SIZE + CELL_GAP) + CELL_GAP
        canvas_h = self.rows * (CELL_SIZE + CELL_GAP) + CELL_GAP

        # Use 2-column grid layout when there are 2+ pages
        num_pages = len(self.page_slots)
        self._grid_cols = 2 if num_pages >= 2 else 1

        # Scrollable container for pages
        container = ttk.Frame(self)
        container.pack(fill=BOTH, expand=True)

        # Calculate content size for 2-column layout
        grid_rows = (num_pages + self._grid_cols - 1) // self._grid_cols
        total_content_h = grid_rows * (canvas_h + 40) + 10
        total_content_w = self._grid_cols * (canvas_w + 24) + 10
        max_h = min(700, total_content_h)

        outer_canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar_y = ttk.Scrollbar(container, orient=VERTICAL,
                                    command=outer_canvas.yview)
        outer_canvas.configure(yscrollcommand=scrollbar_y.set)
        scrollbar_y.pack(side=RIGHT, fill=Y)
        outer_canvas.pack(side=LEFT, fill=BOTH, expand=True)

        inner_frame = ttk.Frame(outer_canvas)
        self._inner_window = outer_canvas.create_window((0, 0), window=inner_frame, anchor="nw")
        inner_frame.bind("<Configure>",
                         lambda e: outer_canvas.configure(
                             scrollregion=outer_canvas.bbox("all")))
        # Mouse wheel scrolling
        def _on_mousewheel(event):
            outer_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        outer_canvas.bind_all("<MouseWheel>", _on_mousewheel)
        self._scroll_canvas = outer_canvas
        pages_parent = inner_frame

        self._canvases = []
        for page_idx, slots in enumerate(self.page_slots):
            grid_r = page_idx // self._grid_cols
            grid_c = page_idx % self._grid_cols

            lf = ttk.LabelFrame(pages_parent,
                                text=f"  Page {page_idx + 1}  ",
                                padding=4)
            lf.grid(row=grid_r, column=grid_c, padx=8, pady=(8, 0), sticky="n")

            c = tk.Canvas(lf, width=canvas_w, height=canvas_h,
                          bg="#1a1a1a", highlightthickness=0)
            c.pack()
            c.page_idx = page_idx  # tag for cross-page lookup
            self._canvases.append(c)
            self._draw_page(page_idx)

            # Bind drag events on each canvas
            c.bind("<ButtonPress-1>", lambda e, pi=page_idx: self._on_press(e, pi))
            c.bind("<B1-Motion>", lambda e, pi=page_idx: self._on_motion(e, pi))
            c.bind("<ButtonRelease-1>", lambda e, pi=page_idx: self._on_release(e, pi))

        # Overflow note
        if self.overflow_count > 0:
            ttk.Label(pages_parent,
                      text=f"{self.overflow_count} items not shown (exceeds page capacity)",
                      foreground="orange").grid(row=grid_rows, column=0,
                                                columnspan=self._grid_cols, pady=(4, 0))

        # Set initial window size
        self.update_idletasks()
        win_w = min(total_content_w + 40, self.winfo_screenwidth() - 100)
        win_h = min(max_h + 60, self.winfo_screenheight() - 100)
        self.geometry(f"{win_w}x{win_h}")

        # Bottom button bar
        btn_bar = ttk.Frame(self, padding=8)
        btn_bar.pack(fill=X)
        ttk.Button(btn_bar, text="Cancel", command=self._cancel).pack(side=RIGHT, padx=(4, 0))
        ttk.Button(btn_bar, text="Apply", bootstyle=SUCCESS,
                   command=self._apply).pack(side=RIGHT)

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def _cell_bbox(self, col, row):
        """Return (x1, y1, x2, y2) for a cell."""
        x1 = CELL_GAP + col * (CELL_SIZE + CELL_GAP)
        y1 = CELL_GAP + row * (CELL_SIZE + CELL_GAP)
        return x1, y1, x1 + CELL_SIZE, y1 + CELL_SIZE

    def _draw_page(self, page_idx):
        c = self._canvases[page_idx]
        c.delete("all")
        slots = self.page_slots[page_idx]

        for row_idx in range(self.rows):
            for col_idx in range(self.cols):
                slot_idx = row_idx * self.cols + col_idx
                item = slots[slot_idx]
                self._draw_cell(c, col_idx, row_idx, item)

    def _draw_cell(self, canvas, col, row, item, highlight=None):
        x1, y1, x2, y2 = self._cell_bbox(col, row)
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        tag = f"cell_{col}_{row}"
        canvas.delete(tag)

        if item is NAV_PREV:
            canvas.create_rectangle(x1, y1, x2, y2, fill=BG_NAV,
                                    outline=BORDER_COLOR, width=1, tags=tag)
            canvas.create_text(cx, cy, text="\u25C0", fill=NAV_TEXT_COLOR,
                               font=("", 16), tags=tag)
        elif item is NAV_NEXT:
            canvas.create_rectangle(x1, y1, x2, y2, fill=BG_NAV,
                                    outline=BORDER_COLOR, width=1, tags=tag)
            canvas.create_text(cx, cy, text="\u25B6", fill=NAV_TEXT_COLOR,
                               font=("", 16), tags=tag)
        elif item is None:
            bg = BG_DRAG_TARGET if highlight == "target" else BG_EMPTY
            canvas.create_rectangle(x1, y1, x2, y2, fill=bg,
                                    outline=BORDER_COLOR, width=1, tags=tag)
        else:
            # PreviewItem
            if highlight == "source":
                bg = BG_DRAG_SOURCE
            elif highlight == "target":
                bg = BG_DRAG_TARGET
            else:
                bg = BG_ITEM
            canvas.create_rectangle(x1, y1, x2, y2, fill=bg,
                                    outline=BORDER_COLOR, width=1, tags=tag)
            display_text = process_label_for_display(item.label, item.split_label)
            canvas.create_text(cx, cy, text=display_text,
                               fill=item.text_color,
                               font=("", 8), width=CELL_SIZE - 8,
                               justify="center", tags=tag)

    # ------------------------------------------------------------------
    # Drag & Drop
    # ------------------------------------------------------------------
    def _coords_to_cell(self, x, y):
        """Convert canvas-local coordinates to (col, row) or None."""
        col = int((x - CELL_GAP) / (CELL_SIZE + CELL_GAP))
        row = int((y - CELL_GAP) / (CELL_SIZE + CELL_GAP))
        if 0 <= col < self.cols and 0 <= row < self.rows:
            # Verify click is within the cell area (not in the gap)
            cx1, cy1, cx2, cy2 = self._cell_bbox(col, row)
            if cx1 <= x <= cx2 and cy1 <= y <= cy2:
                return col, row
        return None

    def _slot_idx(self, col, row):
        return row * self.cols + col

    def _is_nav(self, page_idx, slot_idx):
        item = self.page_slots[page_idx][slot_idx]
        return item is NAV_PREV or item is NAV_NEXT

    def _on_press(self, event, page_idx):
        cell = self._coords_to_cell(event.x, event.y)
        if cell is None:
            return
        col, row = cell
        slot_idx = self._slot_idx(col, row)
        item = self.page_slots[page_idx][slot_idx]

        # Can only drag actual items
        if not isinstance(item, PreviewItem):
            return

        self._drag_source = (page_idx, slot_idx)
        self._draw_cell(self._canvases[page_idx], col, row, item, highlight="source")
        self.config(cursor="fleur")

    def _on_motion(self, event, page_idx):
        if self._drag_source is None:
            return

        # Clear previous highlight
        if self._drag_highlight is not None:
            hp, hs = self._drag_highlight
            hcol = hs % self.cols
            hrow = hs // self.cols
            self._draw_cell(self._canvases[hp], hcol, hrow,
                            self.page_slots[hp][hs])
            self._drag_highlight = None

        # Find target - check if mouse is over a different canvas (cross-page)
        target_page, target_col, target_row = self._find_target(event, page_idx)
        if target_page is None:
            return

        target_slot = self._slot_idx(target_col, target_row)
        src_page, src_slot = self._drag_source

        # Don't highlight source cell as target
        if target_page == src_page and target_slot == src_slot:
            return

        # Don't highlight nav buttons
        if self._is_nav(target_page, target_slot):
            return

        self._drag_highlight = (target_page, target_slot)
        self._draw_cell(self._canvases[target_page], target_col, target_row,
                        self.page_slots[target_page][target_slot],
                        highlight="target")

    def _on_release(self, event, page_idx):
        if self._drag_source is None:
            return

        src_page, src_slot = self._drag_source
        self._drag_source = None
        self.config(cursor="")

        # Clear highlight
        if self._drag_highlight is not None:
            hp, hs = self._drag_highlight
            self._drag_highlight = None

        # Find target
        target_page, target_col, target_row = self._find_target(event, page_idx)
        if target_page is None:
            self._draw_page(src_page)
            return

        target_slot = self._slot_idx(target_col, target_row)

        # Validate target
        if target_page == src_page and target_slot == src_slot:
            self._draw_page(src_page)
            return
        if self._is_nav(target_page, target_slot):
            self._draw_page(src_page)
            return

        # Perform swap (or move to empty)
        src_item = self.page_slots[src_page][src_slot]
        tgt_item = self.page_slots[target_page][target_slot]

        self.page_slots[src_page][src_slot] = tgt_item
        self.page_slots[target_page][target_slot] = src_item

        # Redraw affected pages
        self._draw_page(src_page)
        if target_page != src_page:
            self._draw_page(target_page)

    def _find_target(self, event, current_page_idx):
        """Find target cell, supporting cross-page drag via winfo_containing."""
        # Convert to root coordinates
        rx = event.x_root
        ry = event.y_root

        # Find which canvas the cursor is over
        widget = self.winfo_containing(rx, ry)
        target_canvas = None
        for c in self._canvases:
            if widget is c or (widget and self._is_child_of(widget, c)):
                target_canvas = c
                break

        if target_canvas is None:
            return None, None, None

        # Convert root coords to canvas-local
        local_x = rx - target_canvas.winfo_rootx()
        local_y = ry - target_canvas.winfo_rooty()

        cell = self._coords_to_cell(local_x, local_y)
        if cell is None:
            return None, None, None

        return target_canvas.page_idx, cell[0], cell[1]

    @staticmethod
    def _is_child_of(widget, parent):
        """Check if widget is a descendant of parent."""
        w = widget
        while w is not None:
            if w is parent:
                return True
            try:
                w = w.master
            except AttributeError:
                break
        return None

    # ------------------------------------------------------------------
    # Apply / Cancel
    # ------------------------------------------------------------------
    def _apply(self):
        """Collect items in new order and update the main Treeview."""
        new_order = []
        for slots in self.page_slots:
            for item in slots:
                if isinstance(item, PreviewItem):
                    new_order.append(item.iid)

        self.parent._apply_preview_order(new_order)
        self._close()

    def _cancel(self):
        self._close()

    def _close(self):
        if self._scroll_canvas:
            self._scroll_canvas.unbind_all("<MouseWheel>")
        self.grab_release()
        self.destroy()
        self.parent._preview_window = None
