# CLAUDE.md

## Project Overview
Stream Deck Profile Generator v0.9.0 — a Python GUI + CLI tool that reads flight simulator keybindings and generates Elgato Stream Deck profile files (.streamDeckProfile) in V3 format (compatible with Stream Deck software v7.3+).

## Tech Stack
- **Python 3.8+** with `ttkbootstrap` (themed tkinter) for the GUI
- **Dependencies**: `ttkbootstrap>=1.10.0`, `platformdirs>=3.0.0`
- No database, no web framework — it's a desktop app

## How to Run
```bash
# GUI mode (default)
python -m app

# CLI mode
python -m app --input keys.csv --output profile.streamDeckProfile --device xl
```

## Building Standalone EXE
```bash
# Requires PyInstaller
pip install pyinstaller

# Build (output: dist/StreamDeckProfileGenerator.exe)
pyinstaller StreamDeckProfileGenerator.spec --noconfirm

# Or use the batch script
build.bat
```
- Entry point wrapper: `run.py` (avoids relative import issues)
- Config: `StreamDeckProfileGenerator.spec` (--onefile, --windowed, hidden imports for ttkbootstrap)
- User settings stored in `%LOCALAPPDATA%/Community/StreamDeckProfileGen/` (not bundled)

## Project Structure
```
app/
├── __main__.py            # Entry point: CLI args + GUI launcher
├── ui_main.py             # Main GUI window (ttkbootstrap)
├── preview.py             # Visual preview window with drag & drop reordering
├── keys.py                # Keystroke validation/normalization
├── export/
│   └── streamdeck.py      # V3 profile builder + ZIP export
├── readers/
│   ├── base.py            # SimBindingReader base class
│   ├── xplane_prf.py      # X-Plane 12 .prf parser
│   ├── msfs2024.py        # MSFS 2024 reader
│   ├── msfs2024_parser.py # MSFS 2024 XML inputprofile parser
│   ├── aerofly.py         # Aerofly FS4 reader
│   ├── aerofly_parser.py  # Aerofly MCF parser
│   ├── condor.py          # Condor 3 reader
│   └── condor_parser.py   # Condor controls.ini parser
└── assets/                # App icons (ico, icns, png)
```

## Key Concepts

### Stream Deck V3 Format
The exported `.streamDeckProfile` is a ZIP file with this internal structure:
```
profile.streamDeckProfile (ZIP)
├── package.json                     # App version, device model, plugins
└── Profiles/
    └── {UUID}.sdProfile/
        ├── manifest.json            # Top-level: Pages.Default (empty) + Pages.Pages (content)
        └── Profiles/
            ├── {default-UUID}/      # Empty default page (required by Stream Deck)
            │   └── manifest.json
            ├── {page1-UUID}/        # Content page 1 (listed in Pages.Pages array)
            │   └── manifest.json
            ├── {page2-UUID}/        # Content page 2
            │   └── manifest.json
            └── ...
```

**Critical rules:**
- The `.sdProfile` folder UUID must be **independent** from page UUIDs
- **Default page must be empty** — Stream Deck uses it as a landing page
- **All content pages go in the `Pages.Pages` array** — Stream Deck displays them as pages 1, 2, 3...
- Stream Deck auto-adds navigation arrows in the software UI, but **explicit Prev/Next Page buttons are needed for hardware navigation**
- Navigation buttons: first page has Next only, middle pages have both, last page has Prev only
- Each page manifest has `Actions` dict keyed by `"{col},{row}"` coordinates
- Plugin field must appear between Name and Resources in action JSON

### Pagination (Pages mode only)
- First page: Next arrow at bottom-right → capacity = total_slots - 1
- Middle pages: Prev at bottom-left + Next at bottom-right → capacity = total_slots - 2
- Last page: Prev arrow at bottom-left → capacity = total_slots - 1
- Single page: no navigation → capacity = total_slots
- Maximum 10 pages

### Font & Text
- Font settings (family, size, style, underline) are **global** — apply to all buttons
- `text_color` is **per-button** (hex string, e.g. `#FFFFFF`)
- `text_alignment` is global: `bottom`, `middle`, or `top`
- `show_title` toggles visibility of all button labels
- `include_category` (GUI checkbox / CLI flag) prepends category to label at import time (e.g. "Flaps Up" → "Flight Controls - Flaps Up"). Applied uniformly across all readers.
- `split_label` breaks long names into multiple lines (per-button, default True)

### Device Presets
| Preset | Grid (cols × rows) | Model ID |
|--------|-------------------|----------|
| mini   | 3 × 2             | 20GAI9901 |
| mk2    | 5 × 3             | 20GAA9901 |
| xl     | 8 × 4             | 20GAT9902 |
| generic| 5 × 3             | 20GAA9901 |

## Supported Simulators
- **X-Plane 12** (.prf files) — parses `sim/*` command bindings with modifiers
- **Microsoft Flight Simulator 2024** (XML inputprofiles) — parses exported keyboard profiles, maps Windows VK codes, categorizes by Context
- **Aerofly FS4** (gc-map.mcf files) — XML-like config, filters keyboard device bindings
- **Condor 3** (controls.ini files) — INI format, maps VK codes to standard key names

## Architecture & Data Flow

```
Simulator file (.prf / .xml / .mcf / .ini / .csv)
        │
        ▼
  readers/*.py        Parse simulator-specific format
        │               → Returns list of row dicts
        ▼
  keys.py             Validate & normalize keystrokes
        │               → "CTRL+ALT+F1" format
        ▼
  ui_main.py          GUI table editor (or CLI bypasses this)
        │               → User edits labels, colors, ordering
        │
        ├──► preview.py Visual grid preview + drag & drop reorder
        │               → Swap button positions, apply new order
        ▼
  export/streamdeck.py  Build V3 profile
        │               → Paginate, create actions, build manifests
        ▼
  ZIP output          .streamDeckProfile file ready for import
```

### Reader Pattern
Each simulator has a pair of files:
- **Reader** (`msfs2024.py`, `aerofly.py`, `condor.py`): Implements `SimBindingReader` base class with `detect_install()` and `read_bindings()`. Handles installation detection and delegates parsing.
- **Parser** (`msfs2024_parser.py`, `aerofly_parser.py`, `condor_parser.py`): Contains the actual parsing logic. Returns a list of row dicts with keys: `include`, `order`, `original`, `label`, `keystroke`, `category`, `text_color`, `split_label`.

X-Plane is a single file (`xplane_prf.py`) since it doesn't need auto-detection.

All parsers output a standardized console message: `"SimName: parsed N keyboard bindings (M total, K skipped)"`

### Export Pipeline (export/streamdeck.py)
1. `export_profile()` — main entry point, receives rows + settings
2. Filters included rows, creates `HotkeyAction` for each
3. Paginates based on device grid (Pages mode with nav buttons)
4. Creates empty default `Profile` + content `Profile` objects (one per page)
5. Creates `StreamDeckProfile` with manifests and `package.json`
6. Saves as ZIP with proper V3 directory structure

### Key Classes in export/streamdeck.py
- `Action` — base class with UUID, ActionID, settings, serialization
- `HotkeyAction` — hotkey with title, font formatting, VK code mapping
- `NextPageAction`, `PreviousPageAction` — page navigation
- `Profile` — single page with grid layout and manifest generation
- `StreamDeckProfile` — top-level container, ZIP generation

### Preview Window (preview.py)
- `PreviewItem` — lightweight dataclass copy of a Treeview row (iid, label, keystroke, text_color, split_label)
- `PreviewWindow` (Toplevel) — floating modal window showing the device grid
  - Replicates pagination logic from `_export_with_pages()` into slot arrays
  - All pages visible simultaneously, stacked vertically with scroll
  - Canvas-based rendering: item cells (dark), nav button cells (gray), empty cells
  - **Drag & drop swap**: click item → drag → release on target to swap positions
  - Cross-page drag supported via `winfo_containing()` for root coordinate mapping
  - **Apply**: collects items in new slot order, calls `MainWindow._apply_preview_order(iid_list)` which reorders Treeview rows via `tree.move()`
  - Nav button slots (NAV_PREV/NAV_NEXT sentinels) are fixed and not draggable

### Keystroke Validation (keys.py)
- `normalize_keystroke(raw, platform)` — main function
- Parses `"MOD+MOD+KEY"` format
- Validates modifiers (CTRL, ALT, SHIFT, WIN/CMD) and keys (A-Z, F1-F24, specials, OEM102)
- Reorders modifiers consistently (Windows: WIN→CTRL→ALT→SHIFT; Mac: CMD→CTRL→ALT→SHIFT)
- Maps synonyms: CONTROL→CTRL, OPT→ALT, COMMAND→CMD, etc.

## GUI Architecture (ui_main.py)
- Single `MainWindow` class (ttkbootstrap `Window`)
- Toolbar-based controls — no complex dialogs
- Treeview widget with editable cells (double-click)
- Font toolbar (second row): Font, Size, Style, Underline, Show Title
- Preview button (Ctrl+P) opens `PreviewWindow` for visual grid layout and drag & drop reordering
- `open_preview()` collects included rows as `PreviewItem` list, `_apply_preview_order()` reorders Treeview
- Settings persist to user config dir via `platformdirs`
- Keyboard shortcuts for all common operations
- `ToolTip` helper class for hover tooltips

## Conventions
- User communicates in **Spanish** (Chilean)
- Keep the GUI simple — toolbar-based controls, no complex dialogs
- Settings persist in user config directory via `platformdirs`
- Export validates keystrokes before generating profiles
- Row dict format is consistent across all readers and the CSV format
- Device-specific behavior is driven by `DEVICE_PRESETS` dict, not conditionals
- UUIDs are generated fresh on each export (no persistent IDs)
- `split_label` defaults to True in all parsers
