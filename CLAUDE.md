# CLAUDE.md

## Project Overview
Stream Deck Profile Generator — a Python GUI + CLI tool that reads flight simulator keybindings and generates Elgato Stream Deck profile files (.streamDeckProfile) in V3 format (compatible with Stream Deck software v7.3+).

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

## Project Structure
```
app/
├── __main__.py          # Entry point: CLI args + GUI launcher
├── ui_main.py           # Main GUI window (ttkbootstrap)
├── keys.py              # Keystroke validation/normalization
├── export/
│   └── streamdeck.py    # V3 profile builder + ZIP export
├── readers/
│   ├── base.py          # SimBindingReader base class
│   ├── xplane_prf.py    # X-Plane 12 .prf parser
│   ├── aerofly.py       # Aerofly FS4 reader
│   ├── aerofly_parser.py# Aerofly MCF parser
│   ├── condor.py        # Condor 3 reader
│   └── condor_parser.py # Condor controls.ini parser
└── assets/              # App icons (ico, icns, png)
```

## Key Concepts

### Stream Deck V3 Format
The exported `.streamDeckProfile` is a ZIP file with this internal structure:
```
profile.streamDeckProfile (ZIP)
├── package.json                     # App version, device model, plugins
└── Profiles/
    └── {UUID}.sdProfile/
        ├── manifest.json            # Top-level manifest with Pages.Default + Pages.Pages
        └── Profiles/
            ├── {page1-UUID}/
            │   └── manifest.json    # Page manifest with grid actions
            ├── {page2-UUID}/
            │   └── manifest.json
            └── ...
```

**Critical rules:**
- The `.sdProfile` folder UUID must be **independent** from page UUIDs
- Default page UUID goes in `Pages.Default`, NOT in the `Pages.Pages` array
- `Pages.Pages` only contains additional pages beyond the default
- Each page manifest has `Actions` dict keyed by `"{col},{row}"` coordinates

### Pagination Modes
- **Pages**: prev/next arrow buttons for linear navigation. Reserves 2 buttons per page for navigation arrows.
- **Folders**: parent/child folder navigation. First page uses full grid; subsequent pages reserve 1 button for "back". More space-efficient.

### Font & Text
- Font settings (family, size, style, underline) are **global** — apply to all buttons
- `text_color` is **per-button** (hex string, e.g. `#FFFFFF`)
- `text_alignment` is global: `bottom`, `middle`, or `top`
- `show_title` toggles visibility of all button labels
- Smart label splitting breaks long names at word/CamelCase/underscore boundaries

### Device Presets
| Preset | Grid (cols × rows) | Model ID |
|--------|-------------------|----------|
| mini   | 3 × 2             | 20GAI9901 |
| mk2    | 5 × 3             | 20GAA9901 |
| xl     | 8 × 4             | 20GAT9902 |
| generic| 5 × 3             | 20GAA9901 |

## Supported Simulators
- **X-Plane 12** (.prf files) — parses `sim/*` command bindings with modifiers
- **Microsoft Flight Simulator 2024** (CSV import) — no native parser yet, uses CSV format
- **Aerofly FS4** (gc-map.mcf files) — XML-like config, filters keyboard device bindings
- **Condor 3** (controls.ini files) — INI format, maps VK codes to standard key names

## Architecture & Data Flow

```
Simulator file (.prf / .mcf / .ini / .csv)
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
        ▼
  export/streamdeck.py  Build V3 profile
        │               → Paginate, create actions, build manifests
        ▼
  ZIP output          .streamDeckProfile file ready for import
```

### Reader Pattern
Each simulator has a pair of files:
- **Reader** (`aerofly.py`, `condor.py`): Implements `SimBindingReader` base class with `detect_install()` and `read_bindings()`. Handles installation detection and delegates parsing.
- **Parser** (`aerofly_parser.py`, `condor_parser.py`): Contains the actual parsing logic. Returns a list of row dicts with keys: `include`, `order`, `original`, `label`, `keystroke`, `category`, `text_color`, `icon`.

X-Plane is a single file (`xplane_prf.py`) since it doesn't need auto-detection.

### Export Pipeline (export/streamdeck.py)
1. `export_profile()` — main entry point, receives rows + settings
2. Filters included rows, creates `HotkeyAction` for each
3. Paginates based on device grid and pagination mode
4. Builds `Profile` objects (one per page) with grid positions
5. Creates `StreamDeckProfile` with manifests and `package.json`
6. Saves as ZIP with proper V3 directory structure

### Key Classes in export/streamdeck.py
- `Action` — base class with UUID, ActionID, settings, serialization
- `HotkeyAction` — hotkey with title, font formatting, VK code mapping
- `FolderAction`, `NextPageAction`, `PreviousPageAction`, `BackAction` — navigation
- `Profile` — single page with grid layout and manifest generation
- `StreamDeckProfile` — top-level container, ZIP generation

### Keystroke Validation (keys.py)
- `normalize_keystroke(raw, platform)` — main function
- Parses `"MOD+MOD+KEY"` format
- Validates modifiers (CTRL, ALT, SHIFT, WIN/CMD) and keys (A-Z, F1-F24, specials)
- Reorders modifiers consistently (Windows: WIN→CTRL→ALT→SHIFT; Mac: CMD→CTRL→ALT→SHIFT)
- Maps synonyms: CONTROL→CTRL, OPT→ALT, COMMAND→CMD, etc.

## GUI Architecture (ui_main.py)
- Single `MainWindow` class (ttkbootstrap `Window`)
- Toolbar-based controls — no complex dialogs
- `RowItem` dataclass represents each table row
- Treeview widget with editable cells (double-click)
- Settings persist to user config dir via `platformdirs`
- Keyboard shortcuts for all common operations
- `ToolTip` helper class for hover tooltips

## Conventions
- User communicates in **Spanish**
- Keep the GUI simple — toolbar-based controls, no complex dialogs
- Settings persist in user config directory via `platformdirs`
- Export validates keystrokes before generating profiles
- Row dict format is consistent across all readers and the CSV format
- Device-specific behavior is driven by `DEVICE_PRESETS` dict, not conditionals
- UUIDs are generated fresh on each export (no persistent IDs)
