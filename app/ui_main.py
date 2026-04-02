import csv
import re
import os
import json
from dataclasses import dataclass
from pathlib import Path
from typing import List
from platformdirs import user_config_dir

import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import tkinter as tk
from tkinter import filedialog, messagebox, colorchooser, Toplevel

from .export.streamdeck import export_profile, DEVICE_PRESETS
from .keys import normalize_keystroke, KeystrokeError
from .preview import PreviewWindow, PreviewItem
from .readers.xplane_prf import parse_xplane_prf

# ---- Simulator List ----
SIMS = [
    ("xp12",      "X-Plane 12"),
    ("msfs2024",  "MSFS 2024"),
    ("af_fs4",    "Aerofly FS4"),
    ("condor3",   "Condor 3"),
]

# Removed local keystroke validator; the app now uses keys.normalize_keystroke

APP_TITLE = "Stream Deck Profile Generator"

# ---- Minimal ToolTip ----
class ToolTip:
    def __init__(self, widget, text, delay=400):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.id = None
        self.tw = None
        widget.bind("<Enter>", self._enter, add="+")
        widget.bind("<Leave>", self._leave, add="+")
        widget.bind("<ButtonPress>", self._leave, add="+")

    def _enter(self, _=None):
        self._schedule()

    def _leave(self, _=None):
        self._unschedule()
        self._hide()

    def _schedule(self):
        self._unschedule()
        self.id = self.widget.after(self.delay, self._show)

    def _unschedule(self):
        if self.id:
            self.widget.after_cancel(self.id)
            self.id = None

    def _show(self):
        if self.tw:
            return
        x = self.widget.winfo_rootx() + 10
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.tw = tw = ttk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        frm = ttk.Frame(tw, padding=(8, 6), bootstyle="secondary")
        frm.pack(fill="both", expand=True)
        lbl = ttk.Label(frm, text=self.text, anchor="w", justify="left", wraplength=320)
        lbl.pack(fill="both", expand=True)

    def _hide(self):
        if self.tw:
            try: self.tw.destroy()
            except: pass
            self.tw = None

@dataclass
class RowItem:
    include: bool = True
    order: int = 0
    original: str = ""
    label: str = ""
    keystroke: str = ""
    category: str = ""
    text_color: str = "#FFFFFF"
    split_label: bool = True

class MainWindow(ttk.Window):
    def __init__(self, args=None):
        super().__init__(themename="darkly")
        self.title(APP_TITLE)
        self.geometry("1200x760")
        self.args = args

        self._load_settings()
        
        # ensure container for sim paths
        self.settings.setdefault("sim_paths", {})
        
        # Restore saved window geometry
        geom = (self.settings or {}).get("geometry")
        if geom:
            try:
                self.geometry(geom)
            except Exception:
                pass
        
        self._build_menu()
        self._build_toolbar()
        self._build_table()
        self._build_status()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # Keyboard shortcut to duplicate rows
        self.bind_all("<Control-d>", lambda e: self.duplicate_selected())

        # Delete key to remove selected rows
        self.bind_all("<Delete>", lambda e: self.delete_selected())

        # Selection shortcuts
        self.bind_all("<Control-a>", lambda e: self.select_all())
        self.bind_all("<Escape>", lambda e: self.clear_selection())
        self.bind_all("<Control-i>", lambda e: self.toggle_include_selected())
        self.bind_all("<Control-s>", lambda e: self.toggle_split_selected())

        # Block movement shortcuts
        self.bind_all("<Control-Up>", lambda e: self.move_selected(-1))
        self.bind_all("<Control-Down>", lambda e: self.move_selected(1))

        # Additional utility shortcuts
        self.bind_all("<F2>", lambda e: self.edit_focused_label())
        self.bind_all("<Control-n>", lambda e: self.add_row())
        self.bind_all("<Control-p>", lambda e: self.open_preview())

        # Help shortcut
        self.bind_all("<F1>", lambda e: self.show_keyboard_shortcuts())
        # Space toggles Include/Split depending on focused/last clicked column
        self.tree.bind("<space>", self.on_space_toggle)
        self._last_tree_column = None

        # Readability improvement and row/entry height
        style = ttk.Style()
        style.configure('Treeview', rowheight=30)         # taller rows
        style.configure('Edit.TEntry',
                       font=('Segoe UI', 11),             # taller/more readable editor
                       fieldbackground='white',            # white background
                       foreground='black',                 # black text for contrast
                       relief='solid',                     # solid border
                       borderwidth=1,                      # visible border
                       padding=(2, 1))                    # reduced padding: (horizontal, vertical)
        style.configure('TEntry', font=("Segoe UI", 10))  # Slightly larger font
        style.configure('TLabel', font=("Segoe UI", 10))

        # Restore saved font settings after widgets are created
        self._restore_font_settings()

    # ---------------- UI Builders ----------------
    def _build_menu(self):
        menubar = ttk.Menu(self)

        filemenu = ttk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="New", command=self.new_project)
        filemenu.add_command(label="Open CSV…", command=self.open_csv)
        filemenu.add_command(label="Save CSV…", command=self.save_csv)
        filemenu.add_separator()
        filemenu.add_command(label="Export .streamDeckProfile…", command=self.export_profile_dialog)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.destroy)
        menubar.add_cascade(label="File", menu=filemenu)

        editmenu = ttk.Menu(menubar, tearoff=0)
        editmenu.add_command(label="Duplicate Row\tCtrl+D", command=self.duplicate_selected)
        editmenu.add_separator()
        editmenu.add_command(label="Mark duplicate hotkeys", command=self.mark_duplicate_hotkeys)
        editmenu.add_command(label="Clear markers", command=self.clear_markers)
        menubar.add_cascade(label="Edit", menu=editmenu)

        simmenu = ttk.Menu(menubar, tearoff=0)

        # Aerofly FS4 (submenu)
        af4 = ttk.Menu(simmenu, tearoff=0)
        af4.add_command(label="Auto-detect & Import", command=self.auto_detect_aerofly)
        af4.add_separator()
        af4.add_command(label="Import gc-map.mcf (saved path)", command=self.import_aerofly_from_saved)
        af4.add_command(label="Import gc-map.mcf… (browse)", command=self.import_aerofly_mcf)
        af4.add_separator()
        af4.add_command(label="Set gc-map.mcf path…", command=self.open_sim_paths_dialog)

        # Condor 3 submenu
        condor3 = ttk.Menu(simmenu, tearoff=0)
        condor3.add_command(label="Auto-detect & Import", command=self.auto_detect_condor)
        condor3.add_separator()
        condor3.add_command(label="Import controls.ini (saved path)", command=lambda: self.import_condor_from_saved_for("condor3"))
        condor3.add_command(label="Import controls.ini… (browse)", command=lambda: self.import_condor_ini_for("condor3"))
        condor3.add_separator()
        condor3.add_command(label="Set controls.ini path…", command=self.open_sim_paths_dialog)

        # MSFS 2024
        msfs2024 = ttk.Menu(simmenu, tearoff=0)
        msfs2024.add_command(label="Auto-detect & Import", command=self.auto_detect_msfs2024)
        msfs2024.add_separator()
        msfs2024.add_command(label="Import XML (saved path)", command=self.import_msfs2024_from_saved)
        msfs2024.add_command(label="Import XML… (browse)", command=self.import_msfs2024_xml)
        msfs2024.add_separator()
        msfs2024.add_command(label="Set XML path…", command=self.open_sim_paths_dialog)

        # X-Plane 12 submenu
        xp12 = ttk.Menu(simmenu, tearoff=0)
        xp12.add_command(label="Import Keys.prf (saved path)", command=lambda: self.import_xplane_from_saved_for("xp12"))
        xp12.add_command(label="Import Keys.prf… (browse)", command=lambda: self.import_xplane_prf_for("xp12"))
        xp12.add_separator()
        xp12.add_command(label="Set Keys.prf path…", command=self.open_sim_paths_dialog)

        # Add entries in alphabetical order
        entries = [
            ("Aerofly FS4", af4),
            ("Condor 3", condor3),
            ("MSFS 2024", msfs2024),
            ("X-Plane 12", xp12),
        ]
        for label, submenu in sorted(entries, key=lambda t: t[0].lower()):
            if submenu is None:
                simmenu.add_command(label=label, command=lambda name=label: self.load_sim(name))
            else:
                simmenu.add_cascade(label=label, menu=submenu)

        simmenu.add_separator()
        simmenu.add_command(label="Paths…", command=self.open_sim_paths_dialog)
        menubar.add_cascade(label="Simulator", menu=simmenu)

        help_menu = ttk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Keyboard shortcuts…", command=self.show_keyboard_shortcuts)
        help_menu.add_separator()
        help_menu.add_command(label="Keystroke format…", command=self.show_keystroke_help)
        from . import __version__
        help_menu.add_command(label="About…", command=lambda: messagebox.showinfo(APP_TITLE,
            f"Stream Deck Profile Generator v{__version__}\nMIT License\n\nhttps://github.com/jlgabriel/StreamDeck-Profile-Generator"))
        menubar.add_cascade(label="Help", menu=help_menu)

        self.config(menu=menubar)

    def _build_toolbar(self):
        bar = ttk.Frame(self, padding=8)
        bar.pack(side=TOP, fill=X)

        ttk.Label(bar, text="Device:").pack(side=LEFT, padx=4)
        self.device = ttk.Combobox(bar, values=list(DEVICE_PRESETS.keys()), width=10)
        self.device.set("xl")
        self.device.pack(side=LEFT)
        self.device.bind("<<ComboboxSelected>>", lambda e: self.update_capacity_label())

        ttk.Label(bar, text="Max pages:").pack(side=LEFT, padx=8)
        self.max_pages = ttk.Spinbox(bar, from_=1, to=50, width=5)
        self.max_pages.set(10)
        self.max_pages.pack(side=LEFT)
        self.max_pages.bind("<FocusOut>", lambda e: self.update_capacity_label())

        ttk.Label(bar, text="Text align:").pack(side=LEFT, padx=8)
        self.text_alignment = ttk.Combobox(bar, values=["bottom", "middle", "top"], width=8, state="readonly")
        self.text_alignment.set("middle")  # Default to middle as preferred
        self.text_alignment.pack(side=LEFT)

        ttk.Label(bar, text="Profile name:").pack(side=LEFT, padx=8)
        self.profile_entry = ttk.Entry(bar, width=30)
        self.profile_entry.insert(0, "My Stream Deck Profile")
        self.profile_entry.pack(side=LEFT, padx=12)

        # Spacer to separate from the right
        ttk.Frame(bar).pack(side=LEFT, fill=X, expand=True)

        self.capacity_lbl = ttk.Label(bar, text="Capacity: -")
        self.capacity_lbl.pack(side=LEFT, padx=12)

        # Row ops
        btn_add = ttk.Button(bar, text="Add Row", command=self.add_row)
        btn_add.pack(side=LEFT, padx=6)

        btn_del = ttk.Button(bar, text="Delete Row", command=self.delete_selected)
        btn_del.pack(side=LEFT)

        btn_up = ttk.Button(bar, text="Move Up", command=lambda: self.move_selected(-1))
        btn_up.pack(side=LEFT, padx=6)

        btn_dn = ttk.Button(bar, text="Move Down", command=lambda: self.move_selected(1))
        btn_dn.pack(side=LEFT)

        # Button to duplicate selected rows
        btn_dup = ttk.Button(bar, text="Duplicate", command=self.duplicate_selected)
        btn_dup.pack(side=LEFT, padx=6)

        # Button to apply color to selected rows
        btn_color = ttk.Button(bar, text="Color…", command=self.pick_color_for_selection)
        btn_color.pack(side=LEFT, padx=6)

        btn_preview = ttk.Button(bar, text="Preview", bootstyle=INFO, command=self.open_preview)
        btn_preview.pack(side=LEFT, padx=6)

        self.btn_export = ttk.Button(bar, text="Export Profile", bootstyle=SUCCESS, command=self.export_profile_dialog)
        self.btn_export.pack(side=RIGHT)

        self._preview_window = None

        # --- Tooltips ---
        ToolTip(self.device, "Device preset (Mini/MK2/XL) to calculate grid and pagination.")
        ToolTip(self.max_pages, "Maximum pages to generate for this profile.")
        ToolTip(self.text_alignment, "Global text alignment for all buttons: top, middle, or bottom.")
        ToolTip(self.profile_entry, "Profile name (used on each page).")
        ToolTip(btn_add, "Add a row (action) at the end. (Ctrl+N)")
        ToolTip(btn_del, "Delete selected row(s). Use Ctrl+Click for multiple selection, Shift+Click for range. (Delete key, Ctrl+A to select all, Escape to clear selection)")
        ToolTip(btn_up, "Move selected row(s) up. Contiguous selections move as block. (Ctrl+Up)")
        ToolTip(btn_dn, "Move selected row(s) down. Contiguous selections move as block. (Ctrl+Down)")
        ToolTip(btn_dup, "Duplicate selected row(s). (Ctrl+D)")
        ToolTip(btn_color, "Choose text color for selected row(s).")
        ToolTip(btn_preview, "Preview grid layout and reorder with drag & drop. (Ctrl+P)")

        ToolTip(self.btn_export, "Export to .streamDeckProfile ready to import in Stream Deck.")

        # ---- Font settings toolbar (second row) ----
        font_bar = ttk.Frame(self, padding=(8, 0, 8, 4))
        font_bar.pack(side=TOP, fill=X)

        ttk.Label(font_bar, text="Font:").pack(side=LEFT, padx=4)
        self.font_family = ttk.Combobox(font_bar, values=["", "Verdana", "Tahoma", "Trebuchet MS", "Arial", "Segoe UI", "Calibri", "Consolas"], width=14)
        self.font_family.set("")
        self.font_family.pack(side=LEFT)
        ToolTip(self.font_family, "Global font family for all buttons.\nEmpty = Stream Deck default.")

        ttk.Label(font_bar, text="Size:").pack(side=LEFT, padx=(8, 4))
        self.font_size = ttk.Spinbox(font_bar, from_=6, to=24, width=4)
        self.font_size.set(12)
        self.font_size.pack(side=LEFT)
        ToolTip(self.font_size, "Global font size in px for all buttons.")

        ttk.Label(font_bar, text="Style:").pack(side=LEFT, padx=(8, 4))
        self.font_style = ttk.Combobox(font_bar, values=["", "Regular", "Bold", "Italic", "Bold Italic"], width=11, state="readonly")
        self.font_style.set("")
        self.font_style.pack(side=LEFT)
        ToolTip(self.font_style, "Global font style for all buttons.\nEmpty = Stream Deck default.")

        self.font_underline_var = ttk.BooleanVar(value=False)
        chk_underline = ttk.Checkbutton(font_bar, text="Underline", variable=self.font_underline_var)
        chk_underline.pack(side=LEFT, padx=(12, 4))
        ToolTip(chk_underline, "Enable underline for all button titles.")

        self.show_title_var = ttk.BooleanVar(value=True)
        chk_show = ttk.Checkbutton(font_bar, text="Show Title", variable=self.show_title_var)
        chk_show.pack(side=LEFT, padx=4)
        ToolTip(chk_show, "Show or hide title text on all buttons.")

        self.include_category_var = ttk.BooleanVar(value=False)
        chk_cat = ttk.Checkbutton(font_bar, text="Include Category", variable=self.include_category_var)
        chk_cat.pack(side=LEFT, padx=(12, 4))
        ToolTip(chk_cat, "Prepend category to display label when importing.\nE.g. 'Flaps Up' → 'Flight Controls - Flaps Up'")

    def _build_table(self):
        # container for tree + horizontal scrollbar
        container = ttk.Frame(self)
        container.pack(side=TOP, fill=BOTH, expand=True, padx=8, pady=8)

        self.columns = ("include","order","original","label","keystroke","category","text_color","split_label")
        self.tree = ttk.Treeview(
            container,
            columns=self.columns,
            show="headings",
            height=22,
            bootstyle=INFO,
            selectmode="extended"   # allows multi-selection
        )

        headings = {
            "include":"Include","order":"Order","original":"Original Name","label":"Display Label",
            "keystroke":"Keystroke","category":"Category","text_color":"Text Color","split_label":"Split Label"
        }
        widths = {"include":80,"order":80,"original":320,"label":380,"keystroke":200,"category":160,"text_color":140,"split_label":100}

        for c in self.columns:
            self.tree.heading(c, text=headings[c], command=lambda col=c: self.sort_by(col))
            self.tree.column(c, width=widths[c], anchor="w")

        # Style for rows with invalid hotkey (if used in export)
        self.tree.tag_configure('invalid', background='#4b1c1c')
        # Style for rows with duplicate hotkey
        self.tree.tag_configure('dupe', background='#3a2b00')  # dark amber

        # Horizontal scrollbar
        xscroll = ttk.Scrollbar(container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(xscrollcommand=xscroll.set)

        # Layout
        self.tree.pack(side=TOP, fill=BOTH, expand=True)
        xscroll.pack(side=BOTTOM, fill=X)

        # Apply saved widths (if they exist)
        colw = (self.settings or {}).get("col_widths", {})
        for c, w in colw.items():
            if c in self.columns and isinstance(w, int) and w > 20:
                self.tree.column(c, width=w)

        # Save on mouse release (captures width changes in headers)
        self.tree.bind("<ButtonRelease-1>", lambda e: self._save_settings())

        # events
        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Button-1>", self._on_tree_click, add="+")

        # Update status when selection changes
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.update_selection_status())

    def _build_status(self):
        self.status = ttk.Label(self, text="Ready • Use Ctrl+Click for multi-select, Shift+Click for range • Press F1 for shortcuts", anchor="w")
        self.status.pack(side=BOTTOM, fill=X)
        self.update_capacity_label()

    # ---------------- Actions ----------------
    def new_project(self):
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        self.profile_entry.delete(0, END)
        self.profile_entry.insert(0, "My Stream Deck Profile")
        self.status.configure(text="New project")
        self.update_capacity_label()

    def add_row(self, item: RowItem | None = None):
        current = len(self.tree.get_children()) + 1
        item = item or RowItem(True, current, "", "", "", "", "#FFFFFF", False)
        self.tree.insert("", END, values=("✓" if item.include else "", item.order, item.original, item.label, item.keystroke, item.category, item.text_color, "✓" if item.split_label else ""))
        self.update_capacity_label()

    def delete_selected(self):
        """Delete all selected rows. If no selection, delete focused row."""
        sel = list(self.tree.selection())
        if not sel:
            # Fallback to focused row if no selection
            iid = self.tree.focus()
            if iid:
                sel = [iid]
            else:
                messagebox.showinfo(APP_TITLE, "Select rows to delete.")
                return

        # Confirm deletion if multiple rows selected
        if len(sel) > 1:
            response = messagebox.askyesno(
                APP_TITLE,
                f"Delete {len(sel)} selected rows?",
                icon="question"
            )
            if not response:
                return

        # Delete all selected rows
        for iid in sel:
            self.tree.delete(iid)

        self.renumber_orders()
        self.update_capacity_label()
        self.status.configure(text=f"Deleted {len(sel)} row(s).")

    def duplicate_selected(self):
        """Duplicates the selected row(s) as a contiguous BLOCK,
        inserting it right after the last selected row."""
        sel = list(self.tree.selection())
        if not sel:
            f = self.tree.focus()
            if f:
                sel = [f]
            else:
                messagebox.showinfo(APP_TITLE, "Select one or more rows to duplicate.")
                return

        siblings = list(self.tree.get_children(""))
        if not siblings:
            return

        # Sort selection by current position
        idx_map = {iid: i for i, iid in enumerate(siblings)}
        sel_sorted = sorted(sel, key=lambda iid: idx_map[iid])

        # Insertion point: right AFTER the last selected
        insert_pos = idx_map[sel_sorted[-1]] + 1

        # Take values once (preserving relative order)
        copies = []
        for iid in sel_sorted:
            copies.append((
                self.tree.set(iid, "include"),
                self.tree.set(iid, "order"),
                self.tree.set(iid, "original"),
                self.tree.set(iid, "label"),
                self.tree.set(iid, "keystroke"),
                self.tree.set(iid, "category"),
                self.tree.set(iid, "text_color") or "#FFFFFF",
                self.tree.set(iid, "split_label"),
            ))

        # Insert copies in block, in consecutive positions
        new_iids = []
        for j, vals in enumerate(copies):
            new_iid = self.tree.insert("", insert_pos + j, values=vals)
            new_iids.append(new_iid)

        # Renumber 'Order' and select the new block
        self.renumber_orders()
        self.tree.selection_set(new_iids)
        if new_iids:
            self.tree.focus(new_iids[-1])
            self.tree.see(new_iids[-1])

        self.update_capacity_label()
        self.status.configure(text=f"Duplicated {len(new_iids)} row(s) in block.")

    def select_all(self):
        """Select all rows in the table."""
        children = self.tree.get_children("")
        if children:
            self.tree.selection_set(children)
            self.status.configure(text=f"Selected all {len(children)} rows.")
        else:
            self.status.configure(text="No rows to select.")

    def clear_selection(self):
        """Clear current selection."""
        sel_count = len(self.tree.selection())
        if sel_count > 0:
            self.tree.selection_remove(self.tree.selection())
            self.status.configure(text="Selection cleared.")
        else:
            self.status.configure(text="No selection to clear.")

    def toggle_include_selected(self):
        """Toggle Include checkbox for all selected rows."""
        sel = list(self.tree.selection())
        if not sel:
            # If no selection, try to use focused row
            iid = self.tree.focus()
            if iid:
                sel = [iid]
            else:
                messagebox.showinfo(APP_TITLE, "Select rows to toggle Include status.")
                return

        # Determine new state based on first selected row
        # If first row is included, we'll exclude all selected rows (and vice versa)
        first_included = bool(self.tree.set(sel[0], "include"))
        new_state = not first_included

        # Apply the new state to all selected rows
        for iid in sel:
            self.tree.set(iid, "include", "✓" if new_state else "")

        # Update capacity label since include status changed
        self.update_capacity_label()

        # Provide user feedback
        action = "Included" if new_state else "Excluded"
        self.status.configure(text=f"{action} {len(sel)} row(s).")

    def toggle_split_selected(self):
        """Toggle Split Label checkbox for all selected rows."""
        sel = list(self.tree.selection())
        if not sel:
            # If no selection, try to use focused row
            iid = self.tree.focus()
            if iid:
                sel = [iid]
            else:
                messagebox.showinfo(APP_TITLE, "Select rows to toggle Split Label status.")
                return

        # Determine new state based on first selected row
        # If first row has split enabled, we'll disable all selected rows (and vice versa)
        first_split = bool(self.tree.set(sel[0], "split_label"))
        new_state = not first_split

        # Apply the new state to all selected rows
        for iid in sel:
            self.tree.set(iid, "split_label", "✓" if new_state else "")

        # Provide user feedback
        action = "Enabled" if new_state else "Disabled"
        self.status.configure(text=f"Split Label {action.lower()} for {len(sel)} row(s).")

    def is_selection_contiguous(self, selection_list):
        """Check if a list of tree item IDs represents contiguous rows."""
        if len(selection_list) <= 1:
            return True

        # Get all children (rows) and their indices
        all_children = list(self.tree.get_children(""))
        indices = []

        for item_id in selection_list:
            try:
                index = all_children.index(item_id)
                indices.append(index)
            except ValueError:
                return False  # Item not found

        # Sort indices and check if they form a contiguous sequence
        indices.sort()
        for i in range(1, len(indices)):
            if indices[i] != indices[i-1] + 1:
                return False

        return True

    def move_selected(self, direction: int):
        """Move selected row(s). If selection is contiguous, move as block. Otherwise, move only focused row."""
        sel = list(self.tree.selection())

        # If no selection, try to use focused row
        if not sel:
            iid = self.tree.focus()
            if iid:
                sel = [iid]
            else:
                return

        # Check if selection is contiguous
        if not self.is_selection_contiguous(sel):
            # Non-contiguous selection: only move focused row (Excel-like behavior)
            focused = self.tree.focus()
            if not focused:
                self.status.configure(text="Cannot move non-contiguous selection. Only focused row moved.")
                focused = sel[0]  # Use first selected if no focus

            self._move_single_row(focused, direction)
            self.status.configure(text="Moved focused row (selection not contiguous).")
            return

        # Contiguous selection: move entire block
        self._move_block(sel, direction)

    def _move_single_row(self, iid, direction):
        """Move a single row up or down."""
        siblings = list(self.tree.get_children(""))
        if iid not in siblings:
            return

        idx = siblings.index(iid)
        new_idx = idx + direction

        if 0 <= new_idx < len(siblings):
            self.tree.move(iid, "", new_idx)
            self.renumber_orders()
            self.update_capacity_label()
            # Keep the moved row selected and focused
            self.tree.selection_set([iid])
            self.tree.focus(iid)
            self.tree.see(iid)

    def _move_block(self, selection_list, direction):
        """Move a contiguous block of rows up or down."""
        siblings = list(self.tree.get_children(""))

        # Get indices of selected items
        indices = [siblings.index(iid) for iid in selection_list if iid in siblings]
        if not indices:
            return

        indices.sort()
        min_idx = min(indices)
        max_idx = max(indices)

        # Check bounds
        if direction < 0:  # Moving up
            if min_idx + direction < 0:
                self.status.configure(text="Cannot move block further up.")
                return
            new_position = min_idx + direction
        else:  # Moving down
            if max_idx + direction >= len(siblings):
                self.status.configure(text="Cannot move block further down.")
                return
            new_position = min_idx + direction

        # Move the entire block
        # We need to move in the correct order to avoid index conflicts
        if direction < 0:  # Moving up
            for i, idx in enumerate(indices):
                iid = siblings[idx]
                self.tree.move(iid, "", new_position + i)
        else:  # Moving down
            for i in reversed(range(len(indices))):
                idx = indices[i]
                iid = siblings[idx]
                self.tree.move(iid, "", new_position + i)

        self.renumber_orders()
        self.update_capacity_label()

        # Maintain selection after move
        self.tree.selection_set(selection_list)
        if selection_list:
            self.tree.focus(selection_list[0])
            self.tree.see(selection_list[0])

        block_size = len(selection_list)
        direction_text = "up" if direction < 0 else "down"
        self.status.configure(text=f"Moved block of {block_size} rows {direction_text}.")

    def edit_focused_label(self):
        """Start editing the label column of the focused row."""
        iid = self.tree.focus()
        if not iid:
            # If no focus, try first selected row
            sel = self.tree.selection()
            if sel:
                iid = sel[0]
                self.tree.focus(iid)
            else:
                self.status.configure(text="No row focused for editing.")
                return

        # Get the label column bounding box and trigger edit
        try:
            # Label is the 4th column (0-indexed as column #4)
            bbox = self.tree.bbox(iid, column="#4")
            if bbox:
                # Create a synthetic double-click event
                class SyntheticEvent:
                    def __init__(self, x, y):
                        self.x = x + 5  # Small offset to ensure we're in the cell
                        self.y = y + 5

                x, y, w, h = bbox
                event = SyntheticEvent(x, y)
                self.on_double_click(event)
                self.status.configure(text="Editing label...")
            else:
                self.status.configure(text="Cannot edit: row not visible.")
        except Exception:
            # Fallback: just focus and scroll to the row
            self.tree.see(iid)
            self.status.configure(text="Row focused. Double-click label to edit.")

    def renumber_orders(self):
        for i, iid in enumerate(self.tree.get_children(""), start=1):
            self.tree.set(iid, "order", i)

    def sort_by(self, column: str):
        data = [(self.tree.set(k, column), k) for k in self.tree.get_children("")]
        if column == "order":
            data.sort(key=lambda t: int(t[0]) if str(t[0]).isdigit() else 1e9)
        else:
            data.sort(key=lambda t: str(t[0]).lower())
        for idx, (_, k) in enumerate(data):
            self.tree.move(k, "", idx)
        self.renumber_orders()
        self.status.configure(text=f"Sorted by {column}")

    def on_double_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        iid = self.tree.focus()
        if not iid:
            return
        col = self.tree.identify_column(event.x)
        col_index = int(col.replace('#','')) - 1
        columns = ["include","order","original","label","keystroke","category","text_color","split_label"]
        field = columns[col_index]

        if field == "include":
            current = self.tree.set(iid, "include")
            self.tree.set(iid, "include", "" if current else "✓")
            self.update_capacity_label()
            return

        if field == "split_label":
            current = self.tree.set(iid, "split_label")
            self.tree.set(iid, "split_label", "" if current else "✓")
            self.status.configure(text="Split label toggled")
            return

        if field == "text_color":
            # Open color picker and save directly
            current = self.tree.set(iid, "text_color") or "#FFFFFF"
            _, hx = colorchooser.askcolor(initialcolor=current, title="Choose text color")
            if hx:
                self.tree.set(iid, "text_color", hx)
                self.status.configure(text=f"Text Color: {hx}")
            return



        self.tree.see(iid)
        bbox = self.tree.bbox(iid, column=col)
        if not bbox:
            return
        x, y, w, h = bbox

        # Close previous editor if exists
        if hasattr(self, "_cell_editor") and self._cell_editor:
            try:
                self._cell_editor.destroy()
            except:
                pass

        value = self.tree.set(iid, field)
        editor = ttk.Entry(self.tree, style="Edit.TEntry")
        editor.insert(0, value)
        editor.select_range(0, "end")

        # Increase editor height to fit complete letters
        editor_height = max(28, h)  # Minimum height of 28px or cell height
        editor.place(x=x+1, y=y-2, width=w-2, height=editor_height)  # y-2 for better centering
        editor.lift()
        editor.focus_set()

        # Ensure immediate visual contrast
        editor.configure(foreground='black', background='white')

        def save_edit(e=None):
            txt = editor.get().strip()
            if field == "keystroke":
                try:
                    norm = normalize_keystroke(txt)
                    self.tree.set(iid, field, norm)   # shows CTRL+E without user typing '+'
                    self.tree.item(iid, tags=tuple(t for t in self.tree.item(iid, 'tags') if t != 'invalid'))
                    self.status.configure(text=f"Keystroke: {norm}")
                except KeystrokeError as ex:
                    # leave what was written but mark the error (optional: 'invalid' tag)
                    self.tree.set(iid, field, txt)
                    tags = set(self.tree.item(iid, 'tags'))
                    tags.add('invalid')
                    self.tree.item(iid, tags=tuple(tags))
                    self.status.configure(text=f"Invalid keystroke: {ex}")
            else:
                self.tree.set(iid, field, txt)
            editor.destroy()
            self._cell_editor = None

        def cancel_edit(e=None):
            editor.destroy()
            self._cell_editor = None

        editor.bind("<Return>", save_edit)
        editor.bind("<Escape>", cancel_edit)
        editor.bind("<FocusOut>", save_edit)
        self._cell_editor = editor

    # ---------------- Helpers ----------------
    def pick_color_for_selection(self):
        """Opens color picker and applies text color to all selected rows (Text Color column)."""
        sel = self.tree.selection()
        if not sel:
            # if no selection, try to apply to focused row
            f = self.tree.focus()
            if f:
                sel = (f,)
            else:
                messagebox.showinfo(APP_TITLE, "Select one or more rows first.")
                return

        # initial color: from first selected or default
        initial = self.tree.set(sel[0], "text_color") or "#FFFFFF"
        _, hx = colorchooser.askcolor(initialcolor=initial, title="Choose text color")
        if not hx:
            return  # cancelled

        for iid in sel:
            self.tree.set(iid, "text_color", hx)
        self.status.configure(text=f"Text color applied to {len(sel)} row(s): {hx}")



    # ------- Settings (column widths) -------
    def _settings_path(self):
        cfg_dir = user_config_dir("StreamDeckProfileGen", "Community")
        os.makedirs(cfg_dir, exist_ok=True)
        return os.path.join(cfg_dir, "settings.json")

    def _load_settings(self):
        self.settings = {}
        try:
            with open(self._settings_path(), "r", encoding="utf-8") as f:
                self.settings = json.load(f)
        except Exception:
            self.settings = {}

    def _save_settings(self):
        try:
            col_widths = {c: self.tree.column(c, "width") for c in self.columns}
            font = {
                "font_family": self.font_family.get(),
                "font_size": int(self.font_size.get()),
                "font_style": self.font_style.get(),
                "font_underline": self.font_underline_var.get(),
                "show_title": self.show_title_var.get(),
                "include_category": self.include_category_var.get(),
            }
            data = {**self.settings, "col_widths": col_widths, "font": font}
            with open(self._settings_path(), "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def _restore_font_settings(self):
        font = self.settings.get("font", {})
        if font.get("font_family"):
            self.font_family.set(font["font_family"])
        if font.get("font_size"):
            self.font_size.set(font["font_size"])
        if font.get("font_style"):
            self.font_style.set(font["font_style"])
        if font.get("font_underline") is not None:
            self.font_underline_var.set(font["font_underline"])
        if font.get("show_title") is not None:
            self.show_title_var.set(font["show_title"])
        if font.get("include_category") is not None:
            self.include_category_var.set(font["include_category"])

    def on_close(self):
        self._save_settings()
        try:
            self.settings["geometry"] = self.winfo_geometry()
            with open(self._settings_path(), "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2)
        except Exception:
            pass

        self.destroy()

    def show_keystroke_help(self):
        messagebox.showinfo(APP_TITLE,
            "Keystroke format (quick):\n"
            "• Separators: space or '+'. E.g.:  CTRL e  →  CTRL+E\n"
            "• Modifiers: CTRL, ALT, SHIFT, WIN/CMD\n"
            "• Function: F1..F24  |  Specials: ENTER, TAB, ESC, SPACE...\n"
            "• Punctuation: EQUALS, MINUS, PLUS, COMMA, PERIOD, SLASH, SEMICOLON...\n"
            "• Numpad: NUM0..NUM9, NUMPLUS, NUMENTER, etc.\n\n"
            "Tips:\n"
            "• For the '+' key use PLUS (or SHIFT+EQUALS).\n"
            "• Comma sequences not supported (CTRL+K, CTRL+C).")

    def show_keyboard_shortcuts(self):
        """Show comprehensive list of available keyboard shortcuts."""
        shortcuts_text = """Keyboard Shortcuts Reference:

SELECTION:
• Click                    Select single row
• Ctrl+Click               Add/remove row from selection
• Shift+Click              Select range from last selection
• Ctrl+A                   Select all rows
• Escape                   Clear selection

ROW OPERATIONS:
• Delete                   Delete selected row(s)
• Ctrl+D                   Duplicate selected row(s)
• Ctrl+I                   Toggle Include for selected row(s)
• Ctrl+S                   Toggle Split Label for selected row(s)
• Ctrl+N                   Add new row

MOVEMENT:
• Ctrl+Up                  Move selection up (blocks if contiguous)
• Ctrl+Down                Move selection down (blocks if contiguous)

EDITING:
• Double-click             Edit cell content
• F2                       Edit focused row label
• Space                    Toggle checkboxes (Include, Split Label)

HELP:
• F1                       Show this shortcuts dialog

NOTES:
• Block movement only works with contiguous selections
• Non-contiguous selections move focused row only
• Multiple row operations show confirmation dialogs
• Status bar provides feedback for all operations"""

        # Create a custom dialog with monospace font for better alignment
        dialog = Toplevel(self)
        dialog.title("Keyboard Shortcuts")
        dialog.transient(self)
        dialog.grab_set()
        dialog.geometry("500x400")
        dialog.geometry("+%d+%d" % (self.winfo_rootx()+100, self.winfo_rooty()+100))

        # Create frame with padding
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill=BOTH, expand=True)

        # Create text widget with scrollbar
        text_frame = ttk.Frame(frame)
        text_frame.pack(fill=BOTH, expand=True)

        # Text widget with monospace font
        import tkinter as tk
        text_widget = tk.Text(text_frame, wrap=tk.WORD, font=("Consolas", 10),
                             bg="#2b2b2b", fg="#ffffff", padx=10, pady=10)
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)

        text_widget.insert("1.0", shortcuts_text)
        text_widget.config(state=tk.DISABLED)  # Make read-only

        text_widget.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)

        # Close button
        close_btn = ttk.Button(frame, text="Close", command=dialog.destroy)
        close_btn.pack(pady=(10, 0))

        # Focus on dialog
        dialog.focus_set()

    # ---------------- CSV I/O ----------------
    def open_csv(self):
        path = filedialog.askopenfilename(title="Open CSV", filetypes=[("CSV","*.csv")])
        if not path:
            return
        try:
            self.load_csv(Path(path))
            self.status.configure(text=f"Loaded: {path}")
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Error loading CSV: {e}")

    def save_csv(self):
        path = filedialog.asksaveasfilename(title="Save CSV", defaultextension=".csv")
        if not path:
            return
        try:
            self.dump_csv(Path(path))
            self.status.configure(text=f"Saved: {path}")
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Error saving CSV: {e}")

    def load_csv(self, path: Path):
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        with path.open(newline='', encoding='utf-8') as f:
            rdr = csv.DictReader(f)
            first_name_set = False
            for i, r in enumerate(rdr):
                if not first_name_set:
                    name = (r.get('name') or '').strip()
                    if name:
                        self.profile_entry.delete(0, END)
                        self.profile_entry.insert(0, name)
                        first_name_set = True
                item = RowItem(
                    include=(str(r.get('include', '1')).strip() not in ('0','false','False','')),
                    order=int(r.get('order') or i+1) if 'order' in r else i+1,
                    original=(r.get('original') or r.get('label') or '').strip(),
                    label=(r.get('label') or '').strip(),
                    keystroke=(r.get('keystroke') or '').strip(),
                    category=(r.get('category') or '').strip(),
                    text_color=(r.get('text_color') or r.get('bg_color') or '#FFFFFF').strip(),  # backward compatibility
                    split_label=(str(r.get('split_label', '0')).strip() not in ('0','false','False','')),
                )
                self.tree.insert("", END, values=("✓" if item.include else "", item.order, item.original, item.label, item.keystroke, item.category, item.text_color, "✓" if item.split_label else ""))
        self.update_capacity_label()

    def dump_csv(self, path: Path):
        cols = ["name","include","order","original","label","keystroke","category","text_color","split_label"]
        with path.open('w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            name = self.profile_entry.get().strip() or "Profile"
            for i, iid in enumerate(self.tree.get_children(""), start=1):
                w.writerow({
                    "name": name if i == 1 else "",
                    "include": 1 if self.tree.set(iid, "include") else 0,
                    "order": self.tree.set(iid, "order") or i,
                    "original": self.tree.set(iid, "original"),
                    "label": self.tree.set(iid, "label"),
                    "keystroke": self.tree.set(iid, "keystroke"),
                    "category": self.tree.set(iid, "category"),
                    "text_color": self.tree.set(iid, "text_color") or "#FFFFFF",
                    "split_label": 1 if self.tree.set(iid, "split_label") else 0,
                })

    # ---------------- Preview ----------------
    def open_preview(self):
        """Open the floating preview window."""
        if self._preview_window is not None:
            try:
                self._preview_window.lift()
                self._preview_window.focus_set()
                return
            except tk.TclError:
                self._preview_window = None

        # Collect included rows in visual order
        items = []
        for iid in self.tree.get_children(""):
            if not self.tree.set(iid, "include"):
                continue
            items.append(PreviewItem(
                iid=iid,
                label=self.tree.set(iid, "label") or self.tree.set(iid, "original"),
                keystroke=self.tree.set(iid, "keystroke"),
                text_color=self.tree.set(iid, "text_color") or "#FFFFFF",
                split_label=bool(self.tree.set(iid, "split_label")),
            ))

        if not items:
            messagebox.showwarning("Preview", "No included rows to preview.")
            return

        preset = DEVICE_PRESETS.get(self.device.get(), DEVICE_PRESETS["generic"])
        max_pages = int(self.max_pages.get())

        self._preview_window = PreviewWindow(self, items, preset, max_pages)

    def _apply_preview_order(self, new_iid_order):
        """Reorder Treeview rows to match the preview arrangement."""
        for new_idx, iid in enumerate(new_iid_order):
            self.tree.move(iid, "", new_idx)
        self.renumber_orders()
        self.update_capacity_label()
        self.status.configure(text=f"Preview applied: {len(new_iid_order)} buttons reordered.")

    # ---------------- Export ----------------
    def export_profile_dialog(self):
        # gather rows
        items = []
        invalid_rows = []

        for i, iid in enumerate(self.tree.get_children(""), start=1):
            include = bool(self.tree.set(iid, "include"))
            order = i  # use visual order from the table
            original = self.tree.set(iid, "original")
            label = self.tree.set(iid, "label")
            keystroke = self.tree.set(iid, "keystroke")
            category = self.tree.set(iid, "category")
            text_color = self.tree.set(iid, "text_color") or "#FFFFFF"
            split_label = bool(self.tree.set(iid, "split_label"))

            # clear previous error marker
            self.tree.item(iid, tags=tuple(t for t in self.tree.item(iid, 'tags') if t != 'invalid'))

            if include:
                if not keystroke:
                    invalid_rows.append((i, "Empty keystroke"))
                    self.tree.item(iid, tags=(*self.tree.item(iid, 'tags'), 'invalid'))
                    continue
                try:
                    ks_norm = normalize_keystroke(keystroke)
                except KeystrokeError as ex:
                    invalid_rows.append((i, str(ex)))
                    self.tree.item(iid, tags=(*self.tree.item(iid, 'tags'), 'invalid'))
                    continue

                items.append({
                    "include": True,
                    "order": order,
                    "original": original,
                    "label": label or original,
                    "keystroke": ks_norm,   # using normalized
                    "category": category,
                    "text_color": text_color,
                    "split_label": split_label,
                })

        # If there are invalid ones, inform and cancel export
        if invalid_rows:
            msg = "\n".join([f"Row {row}: {why}" for row, why in invalid_rows[:12]])
            if len(invalid_rows) > 12:
                msg += f"\n… and {len(invalid_rows)-12} more."
            messagebox.showerror(APP_TITLE, f"Cannot export: there are invalid hotkeys.\n\n{msg}\n\n"
                                            f"Tip: separate with '+'. For the '+' key, use 'PLUS'.")
            return

        # Warn about duplicate hotkeys and allow user to proceed or cancel
        # Group by normalized keystroke
        dupe_map = {}
        for r in items:
            ks = (r.get("keystroke") or "").strip().upper()
            if not ks:
                continue
            dupe_map.setdefault(ks, []).append(r)

        dupe_groups = {k: v for k, v in dupe_map.items() if len(v) > 1}
        if dupe_groups:
            total_rows = sum(len(v) for v in dupe_groups.values())
            groups_count = len(dupe_groups)

            # Build a compact preview message
            lines = ["Duplicate hotkeys found:"]
            shown = 0
            for ks, rows in list(dupe_groups.items())[:6]:
                labels = [r.get("label") or r.get("original") or "(no label)" for r in rows]
                preview = ", ".join(f"'{lbl}'" for lbl in labels[:3])
                if len(labels) > 3:
                    preview += f" and {len(labels)-3} more"
                lines.append(f"• {ks}: {preview}")
                shown += 1
            if groups_count > shown:
                lines.append(f"… and {groups_count - shown} more group(s)")
            lines.append("")
            lines.append(f"Total: {total_rows} rows with {groups_count} duplicate hotkey group(s).")
            lines.append("")
            lines.append("Do you want to export anyway?")

            msg = "\n".join(lines)

            # Ask user with Yes/No/Cancel if available
            try:
                resp = messagebox.askyesnocancel(APP_TITLE, msg, icon="warning")
            except Exception:
                resp = messagebox.askyesno(APP_TITLE, msg, icon="warning")

            if resp is None or resp is False:
                # Cancel or No
                return

        items.sort(key=lambda r: int(r.get("order", 1e9)))
        preset = DEVICE_PRESETS.get(self.device.get(), DEVICE_PRESETS["xl"])
        capacity = preset["cols"] * preset["rows"] * int(self.max_pages.get())
        if len(items) > capacity:
            if not messagebox.askyesno(APP_TITLE, f"Selected {len(items)} keys exceed capacity {capacity}. Continue with pagination limited to {capacity}? (Extra items will be dropped)"):
                return
            items = items[:capacity]
        out = filedialog.asksaveasfilename(title="Save .streamDeckProfile", defaultextension=".streamDeckProfile")
        if not out:
            return
        try:
            export_profile(
                rows=items,
                out_path=out,
                profile_name=self.profile_entry.get().strip() or "Profile",
                device=self.device.get(),
                max_pages=int(self.max_pages.get()),
                text_alignment=self.text_alignment.get(),
                font_family=self.font_family.get(),
                font_size=int(self.font_size.get()),
                font_style=self.font_style.get(),
                font_underline=self.font_underline_var.get(),
                show_title=self.show_title_var.get(),
            )
            messagebox.showinfo(APP_TITLE, f"Exported to: {out}")
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Export error: {e}")

    def load_sim(self, name: str):
        self.profile_entry.delete(0, END)
        self.profile_entry.insert(0, f"{name} Profile")
        self.status.configure(text=f"Simulator set: {name}")
        self.update_capacity_label()

    def update_capacity_label(self):
        preset = DEVICE_PRESETS.get(self.device.get(), DEVICE_PRESETS["xl"])
        grid_size = preset["cols"] * preset["rows"]
        max_pages = int(self.max_pages.get())

        # Nav buttons: first/last page use 1 slot, middle pages use 2
        capped_pages = min(max_pages, 10)
        if capped_pages <= 1:
            capacity = grid_size
        elif capped_pages == 2:
            capacity = (grid_size - 1) * 2
        else:
            capacity = (grid_size - 1) * 2 + (grid_size - 2) * (capped_pages - 2)

        included = sum(1 for iid in self.tree.get_children("") if self.tree.set(iid, "include"))

        self.capacity_lbl.configure(
            text=f"Capacity: {included}/{capacity}  |  Grid {preset['cols']}×{preset['rows']} × {max_pages} Pages mode (max 10)"
        )

    def update_selection_status(self):
        """Update status bar with selection information."""
        sel_count = len(self.tree.selection())
        if sel_count == 0:
            return  # Don't override other status messages
        elif sel_count == 1:
            self.status.configure(text="1 row selected")
        else:
            self.status.configure(text=f"{sel_count} rows selected")

    def _on_tree_click(self, event):
        """Track last clicked column in the tree for Space toggle behavior."""
        try:
            col = self.tree.identify_column(event.x)
            self._last_tree_column = col
        except Exception:
            self._last_tree_column = None

    def on_space_toggle(self, event=None):
        """Toggle Include or Split depending on focused/last clicked column or selection.
        - If last column is Include (#1) -> toggle_include_selected
        - If last column is Split Label (#8) -> toggle_split_selected
        - Otherwise: if only one row focused, toggle Include on that row; if multiple selected, toggle Include for selection.
        """
        # If an editor is open, let Entry handle Space
        if hasattr(self, "_cell_editor") and self._cell_editor:
            return

        # Determine intended action by last clicked column
        if self._last_tree_column in ("#1", "#8"):
            if self._last_tree_column == "#1":
                self.toggle_include_selected()
                return "break"
            if self._last_tree_column == "#8":
                self.toggle_split_selected()
                return "break"

        # Fallback behavior: toggle include for selection or focused row
        sel = list(self.tree.selection())
        if not sel:
            focused = self.tree.focus()
            if focused:
                sel = [focused]
        if sel:
            # Decide new state based on first item
            first_included = bool(self.tree.set(sel[0], "include"))
            new_state = not first_included
            for iid in sel:
                self.tree.set(iid, "include", "✓" if new_state else "")
            self.update_capacity_label()
            action = "Included" if new_state else "Excluded"
            self.status.configure(text=f"{action} {len(sel)} row(s).")
            return "break"

    def open_sim_paths_dialog(self):
        dlg = Toplevel(self)
        dlg.title("Simulator Paths")
        dlg.transient(self)
        dlg.grab_set()
        dlg.geometry("+%d+%d" % (self.winfo_rootx()+80, self.winfo_rooty()+80))

        frm = ttk.Frame(dlg, padding=12)
        frm.pack(fill=BOTH, expand=True)

        ttk.Label(frm, text="Configure the path to keybindings (file or folder) for each simulator.", anchor="w").grid(row=0, column=0, columnspan=5, sticky="w", pady=(0,8))

        # headers
        ttk.Label(frm, text="Simulator", width=18).grid(row=1, column=0, sticky="w")
        ttk.Label(frm, text="Path").grid(row=1, column=1, sticky="w", padx=(6,0))

        entries = {}

        for r, (key, name) in enumerate(SIMS, start=2):
            ttk.Label(frm, text=name).grid(row=r, column=0, sticky="w", padx=(0,8), pady=3)
            var = ttk.StringVar(value=self.settings["sim_paths"].get(key, ""))
            ent = ttk.Entry(frm, textvariable=var, width=72)
            ent.grid(row=r, column=1, sticky="we", pady=3)
            entries[key] = var

            def browse_file(k=key, v=var):
                path = filedialog.askopenfilename(title=f"{name} — choose file")
                if path: v.set(path)

            def browse_folder(k=key, v=var):
                path = filedialog.askdirectory(title=f"{name} — choose folder")
                if path: v.set(path)

            ttk.Button(frm, text="File…", command=browse_file).grid(row=r, column=2, padx=4)
            ttk.Button(frm, text="Folder…", command=browse_folder).grid(row=r, column=3, padx=0)
            ttk.Button(frm, text="Clear", command=lambda v=var: v.set("")).grid(row=r, column=4, padx=6)

        # buttons
        btns = ttk.Frame(frm)
        btns.grid(row=len(SIMS)+2, column=0, columnspan=5, sticky="e", pady=(12,0))
        def on_save():
            # guarda en settings y a disco
            for key, var in entries.items():
                val = var.get().strip()
                if val:
                    self.settings["sim_paths"][key] = val
                else:
                    self.settings["sim_paths"].pop(key, None)
            try:
                with open(self._settings_path(), "w", encoding="utf-8") as f:
                    json.dump(self.settings, f, indent=2)
                self.status.configure(text="Simulator paths saved.")
            except Exception as e:
                messagebox.showerror(APP_TITLE, f"Error saving settings: {e}")
            dlg.destroy()

        ttk.Button(btns, text="Cancel", command=dlg.destroy).pack(side=RIGHT)
        ttk.Button(btns, text="Save", bootstyle=SUCCESS, command=on_save).pack(side=RIGHT, padx=8)

        # make columns stretch
        frm.columnconfigure(1, weight=1)

    def get_sim_path(self, key: str) -> str | None:
        return (self.settings.get("sim_paths") or {}).get(key)

    def clear_markers(self):
        for iid in self.tree.get_children(""):
            tags = tuple(t for t in self.tree.item(iid, 'tags') if t not in ('dupe',))
            self.tree.item(iid, tags=tags)
        self.status.configure(text="Markers cleared.")

    def mark_duplicate_hotkeys(self):
        # clear previous marks
        self.clear_markers()

        # group by keystroke (only included rows)
        groups = {}
        for iid in self.tree.get_children(""):
            include = self.tree.set(iid, "include")
            if not include:  # empty -> not included
                continue
            ks = (self.tree.set(iid, "keystroke") or "").strip().upper()
            if not ks:
                continue
            groups.setdefault(ks, empty_list := []).append(iid)

        # mark duplicates
        dup_rows = 0
        dup_groups = 0
        for ks, iids in groups.items():
            if len(iids) > 1:
                dup_groups += 1
                dup_rows += len(iids)
                for iid in iids:
                    self.tree.item(iid, tags=(*self.tree.item(iid, 'tags'), 'dupe'))

        if dup_groups:
            self.status.configure(text=f"{dup_groups} hotkey group(s) duplicated, {dup_rows} row(s) marked.")
            # optional: sort by keystroke to see them together
            # self.sort_by("keystroke")
        else:
            self.status.configure(text="No duplicate hotkeys among included rows.")

    def import_xplane_from_saved_for(self, xp_key: str):
        path = self.get_sim_path(xp_key)
        if not path:
            messagebox.showinfo(APP_TITLE, f"No saved path for {xp_key.upper()}. Use 'Set Keys.prf path…' first.")
            return
        if not os.path.isfile(path):
            messagebox.showwarning(APP_TITLE, "Saved path is not a file. Please set it again.")
            return
        self._import_xplane_common(path)

    def import_xplane_prf_for(self, xp_key: str):
        base = self.get_sim_path(xp_key)
        initialdir = os.path.dirname(base) if base and os.path.isfile(base) else (base if base and os.path.isdir(base) else None)
        initialfile = os.path.basename(base) if base and os.path.isfile(base) else None

        path = filedialog.askopenfilename(
            title=f"Select X-Plane Keys.prf ({xp_key.upper()})",
            filetypes=[("X-Plane Keys .prf", "*Keys*.prf"), ("All .prf", "*.prf"), ("All files", "*.*")],
            initialdir=initialdir if initialdir else None,
            initialfile=initialfile if initialfile else None,
        )
        if not path:
            return
        self._import_xplane_common(path)

    def _is_likely_xp_keys_prf(self, path: str) -> bool:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                hits = 0
                for i, line in enumerate(f, start=1):
                    s = line.strip()
                    if not s or s.startswith("#"): 
                        continue
                    parts = s.split(" ", 2)
                    if len(parts) >= 3 and parts[2].startswith("sim/"):
                        hits += 1
                    if i > 600 or hits >= 5:  # pronto y barato
                        break
                return hits >= 5
        except Exception:
            return False

    def _apply_category_to_label(self, row: dict):
        """Prepend category to label if 'Include Category' is checked."""
        if self.include_category_var.get() and row.get("category"):
            cat = row["category"]
            lbl = row.get("label", "")
            if lbl and not lbl.startswith(cat):
                row["label"] = f"{cat} - {lbl}"

    def _import_xplane_common(self, path: str):
        if not self._is_likely_xp_keys_prf(path):
            if not messagebox.askyesno(APP_TITLE, "This doesn't look like a Keys.prf. Continue anyway?"):
                return
        try:
            from .readers.xplane_prf import parse_xplane_prf
            rows = parse_xplane_prf(path)

            if not rows:
                messagebox.showwarning(APP_TITLE,
                    "No bindings found in this file.\n\n"
                    "Make sure you select the *X-Plane Keys.prf* (keyboard).\n"
                    "Typical location: Output/preferences/*Keys*.prf")
                self.status.configure(text="Imported 0 bindings (check file).")
                return

            # Replace or add?
            if self.tree.get_children(""):
                if messagebox.askyesno(APP_TITLE, "Replace current rows with PRF?\n\nYes = Replace\nNo = Append", icon="question"):
                    for iid in self.tree.get_children(""):
                        self.tree.delete(iid)

            start = len(self.tree.get_children("")) + 1
            invalid = 0
            for j, r in enumerate(rows, start=start):
                ks = r["keystroke"]; tag = ()
                try:
                    ks = normalize_keystroke(ks) if ks else ""
                except Exception:
                    if ks:
                        tag = ("invalid",); invalid += 1

                self._apply_category_to_label(r)
                self.tree.insert("", "end", values=(
                    "✓" if r["include"] else "",
                    j, r["original"], r["label"], ks,
                    r["category"], r["text_color"], "✓" if r.get("split_label", True) else ""
                ), tags=tag)

            base = os.path.splitext(os.path.basename(path))[0]
            self.profile_entry.delete(0, END)
            self.profile_entry.insert(0, f"X-Plane Import ({base})")

            self.renumber_orders()
            self.update_capacity_label()
            note = f"Imported {len(rows)} bindings."
            if invalid: note += f"  {invalid} need review."
            self.status.configure(text=note)
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Error importing PRF: {e}")

    def import_aerofly_from_saved(self):
        """Import Aerofly FS 4 gc-map.mcf from saved path"""
        path = self.get_sim_path("af_fs4")
        if not path:
            messagebox.showinfo(APP_TITLE, "No saved path. Use 'Set gc-map.mcf path…' first.")
            return
        if not os.path.isfile(path):
            messagebox.showwarning(APP_TITLE, "Saved path is not a file. Please set it again.")
            return
        self._import_aerofly_common(path)

    def import_aerofly_mcf(self):
        """Browse and import Aerofly FS 4 gc-map.mcf"""
        base = self.get_sim_path("af_fs4")
        initialdir = os.path.dirname(base) if base and os.path.isfile(base) else None
        initialfile = "gc-map.mcf"

        path = filedialog.askopenfilename(
            title="Select Aerofly FS 4 gc-map.mcf",
            filetypes=[("Aerofly config", "*.mcf"), ("All files", "*.*")],
            initialdir=initialdir,
            initialfile=initialfile,
        )
        if not path:
            return
        self._import_aerofly_common(path)

    def auto_detect_aerofly(self):
        """Auto-detect Aerofly FS 4 installation"""
        from .readers.aerofly import Reader
        reader = Reader()
        path = reader.detect_install()

        if path:
            # Save detected path
            self.settings.setdefault("sim_paths", {})
            self.settings["sim_paths"]["af_fs4"] = str(path)
            self._save_settings()

            # Ask to import
            if messagebox.askyesno(APP_TITLE,
                f"Found Aerofly FS 4 configuration:\n{path}\n\n"
                f"Import keyboard bindings now?"):
                self._import_aerofly_common(str(path))
            else:
                self.status.configure(text=f"Aerofly FS 4 path detected: {path.parent}")
        else:
            messagebox.showinfo(APP_TITLE,
                "Aerofly FS 4 not found in standard location.\n"
                "Please browse manually for gc-map.mcf file.")

    def _is_likely_aerofly_mcf(self, path: str) -> bool:
        """Check if file looks like Aerofly FS 4 config"""
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(20000)
                return "tmcontroller_configuration" in content and "tmchannelmap" in content
        except:
            return False

    def _import_aerofly_common(self, path: str):
        """Common import logic for Aerofly FS 4"""
        if not self._is_likely_aerofly_mcf(path):
            if not messagebox.askyesno(APP_TITLE,
                "This doesn't look like Aerofly FS 4 gc-map.mcf. Continue anyway?"):
                return

        try:
            from .readers.aerofly_parser import parse_aerofly_mcf
            rows = parse_aerofly_mcf(path)

            if not rows:
                messagebox.showwarning(APP_TITLE,
                    "No keyboard bindings found.\n\n"
                    "This configuration may use only hardware controls.\n"
                    "Check your Aerofly FS 4 input settings.")
                return

            # Replace or append
            if self.tree.get_children(""):
                if messagebox.askyesno(APP_TITLE,
                    "Replace current rows with Aerofly FS 4 bindings?\n\nYes = Replace\nNo = Append"):
                    for iid in self.tree.get_children(""):
                        self.tree.delete(iid)

            start = len(self.tree.get_children("")) + 1
            invalid = 0

            for j, r in enumerate(rows, start=start):
                ks = r["keystroke"]
                tag = ()

                # Validate keystroke
                try:
                    ks = normalize_keystroke(ks) if ks else ""
                except Exception:
                    if ks:
                        tag = ("invalid",)
                        invalid += 1

                self._apply_category_to_label(r)
                self.tree.insert("", "end", values=(
                    "✓" if r["include"] else "",
                    j, r["original"], r["label"], ks,
                    r["category"], r["text_color"],
                    "✓" if r.get("split_label", True) else ""
                ), tags=tag)

            # Update profile name
            base = os.path.splitext(os.path.basename(path))[0]
            self.profile_entry.delete(0, END)
            self.profile_entry.insert(0, f"Aerofly FS 4 ({base})")

            self.renumber_orders()
            self.update_capacity_label()

            note = f"Imported {len(rows)} keyboard bindings."
            if invalid:
                note += f" {invalid} need review."
            self.status.configure(text=note)

        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Error importing Aerofly FS 4: {e}")

    def auto_detect_condor(self):
        """Auto-detect Condor 2/3 installation"""
        from .readers.condor import Reader
        reader = Reader()
        path = reader.detect_install()

        if path:
            # Save detected path (use condor3 as default key)
            self.settings.setdefault("sim_paths", {})
            self.settings["sim_paths"]["condor3"] = str(path)
            self._save_settings()

            # Ask to import
            if messagebox.askyesno(APP_TITLE,
                f"Found Condor controls.ini:\n{path}\n\n"
                f"Import keyboard bindings now?"):
                self._import_condor_common(str(path))
            else:
                self.status.configure(text=f"Condor path detected: {path.parent}")
        else:
            messagebox.showinfo(APP_TITLE,
                "Condor installation not found in standard location.\n"
                "Please browse manually for controls.ini file.")

    def import_condor_from_saved_for(self, condor_key: str):
        path = self.get_sim_path(condor_key)
        if not path:
            messagebox.showinfo(APP_TITLE, f"No saved path for {condor_key}. Use 'Set controls.ini path…' first.")
            return
        if not os.path.isfile(path):
            messagebox.showwarning(APP_TITLE, "Saved path is not a file. Please set it again.")
            return
        self._import_condor_common(path)

    def import_condor_ini_for(self, condor_key: str):
        base = self.get_sim_path(condor_key)
        initialdir = os.path.dirname(base) if base and os.path.isfile(base) else None
        initialfile = "controls.ini"

        path = filedialog.askopenfilename(
            title=f"Select Condor controls.ini ({condor_key})",
            filetypes=[("Condor controls", "controls.ini"), ("INI files", "*.ini"), ("All files", "*.*")],
            initialdir=initialdir,
            initialfile=initialfile,
        )
        if not path:
            return
        self._import_condor_common(path)

    def _is_likely_condor_ini(self, path: str) -> bool:
        """Check if file looks like Condor controls.ini"""
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(2000)

                # Look for typical Condor patterns
                if "{" not in content or "}" not in content:
                    return False

                # Count numeric keys (Condor uses numeric command IDs)
                import re
                numeric_lines = len(re.findall(r'^\s*\d+\s*=', content, re.MULTILINE))

                # Condor controls.ini typically has many numeric command mappings
                return numeric_lines > 10
        except:
            return False

    def _import_condor_common(self, path: str):
        """Common import logic for Condor"""
        if not self._is_likely_condor_ini(path):
            if not messagebox.askyesno(APP_TITLE,
                "This doesn't look like a Condor controls.ini file. Continue anyway?"):
                return

        try:
            from .readers.condor_parser import parse_condor_controls_ini
            rows = parse_condor_controls_ini(path)

            if not rows:
                messagebox.showwarning(APP_TITLE,
                    "No keyboard bindings found in this controls.ini file.\n\n"
                    "This may be an empty configuration or contain only hardware controls.")
                return

            # Replace or append
            if self.tree.get_children(""):
                if messagebox.askyesno(APP_TITLE,
                    "Replace current rows with Condor bindings?\n\nYes = Replace\nNo = Append"):
                    for iid in self.tree.get_children(""):
                        self.tree.delete(iid)

            start = len(self.tree.get_children("")) + 1
            invalid = 0

            for j, r in enumerate(rows, start=start):
                ks = r["keystroke"]
                tag = ()

                # Validate keystroke
                try:
                    ks = normalize_keystroke(ks) if ks else ""
                except Exception:
                    if ks:
                        tag = ("invalid",)
                        invalid += 1

                self._apply_category_to_label(r)
                self.tree.insert("", "end", values=(
                    "✓" if r["include"] else "",
                    j, r["original"], r["label"], ks,
                    r["category"], r["text_color"],
                    "✓" if r.get("split_label", True) else ""
                ), tags=tag)

            # Update profile name
            base = os.path.splitext(os.path.basename(path))[0]
            self.profile_entry.delete(0, END)
            self.profile_entry.insert(0, f"Condor Import ({base})")

            self.renumber_orders()
            self.update_capacity_label()

            note = f"Imported {len(rows)} keyboard bindings."
            if invalid:
                note += f" {invalid} need review."
            self.status.configure(text=note)

        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Error importing Condor: {e}")

    # ── MSFS 2024 ──────────────────────────────────────────────

    def auto_detect_msfs2024(self):
        """Auto-detect MSFS 2024 inputprofile XML."""
        try:
            from .readers.msfs2024 import Reader
            reader = Reader()
            path = reader.detect_install()
            if path:
                if messagebox.askyesno(APP_TITLE,
                    f"Found MSFS 2024 profile:\n{path}\n\nImport it?"):
                    self._import_msfs2024_common(str(path))
            else:
                messagebox.showinfo(APP_TITLE,
                    "Could not auto-detect MSFS 2024 inputprofile.\n\n"
                    "Use 'Import XML… (browse)' to select the file manually.")
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Error detecting MSFS 2024: {e}")

    def import_msfs2024_from_saved(self):
        """Import MSFS 2024 XML from saved path."""
        path = self.get_sim_path("msfs2024")
        if not path:
            messagebox.showinfo(APP_TITLE, "No saved path for MSFS 2024. Use 'Set XML path…' first.")
            return
        if not os.path.isfile(path):
            messagebox.showwarning(APP_TITLE, "Saved path is not a file. Please set it again.")
            return
        self._import_msfs2024_common(path)

    def import_msfs2024_xml(self):
        """Browse and import MSFS 2024 inputprofile XML."""
        base = self.get_sim_path("msfs2024")
        initialdir = os.path.dirname(base) if base and os.path.isfile(base) else (base if base and os.path.isdir(base) else None)

        path = filedialog.askopenfilename(
            title="Select MSFS 2024 Inputprofile XML",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")],
            initialdir=initialdir,
        )
        if not path:
            return
        self._import_msfs2024_common(path)

    def _import_msfs2024_common(self, path: str):
        """Common import logic for MSFS 2024 XML."""
        try:
            from .readers.msfs2024_parser import parse_msfs2024_xml
            rows = parse_msfs2024_xml(path)

            if not rows:
                messagebox.showwarning(APP_TITLE,
                    "No keyboard bindings found in this XML file.\n\n"
                    "Make sure you export the keyboard inputprofile from MSFS 2024.")
                return

            # Replace or append
            if self.tree.get_children(""):
                if messagebox.askyesno(APP_TITLE,
                    "Replace current rows with MSFS 2024 bindings?\n\nYes = Replace\nNo = Append"):
                    for iid in self.tree.get_children(""):
                        self.tree.delete(iid)

            start = len(self.tree.get_children("")) + 1
            invalid = 0

            for j, r in enumerate(rows, start=start):
                ks = r["keystroke"]
                tag = ()

                try:
                    ks = normalize_keystroke(ks) if ks else ""
                except Exception:
                    if ks:
                        tag = ("invalid",)
                        invalid += 1

                self._apply_category_to_label(r)
                self.tree.insert("", "end", values=(
                    "✓" if r["include"] else "",
                    j, r["original"], r["label"], ks,
                    r["category"], r["text_color"],
                    "✓" if r.get("split_label", True) else ""
                ), tags=tag)

            # Update profile name
            base = os.path.splitext(os.path.basename(path))[0]
            self.profile_entry.delete(0, END)
            self.profile_entry.insert(0, f"MSFS 2024 Import ({base})")

            self.renumber_orders()
            self.update_capacity_label()

            note = f"Imported {len(rows)} keyboard bindings from MSFS 2024."
            if invalid:
                note += f" {invalid} need review."
            self.status.configure(text=note)

        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Error importing MSFS 2024: {e}")

def run_gui(args=None):
    app = MainWindow(args)
    app.mainloop()
