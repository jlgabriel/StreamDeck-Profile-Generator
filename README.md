# Stream Deck Profile Generator

A Python desktop application (GUI + CLI) that reads flight simulator keybindings and generates Elgato Stream Deck profile files (`.streamDeckProfile`) in **V3 format**, compatible with Stream Deck software v7.3+.

![Stream Deck Profile Generator](app/assets/icon.png)

---

## Table of Contents

- [Features](#features)
- [Supported Simulators](#supported-simulators)
- [Compatible Devices](#compatible-devices)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
  - [GUI Mode](#gui-mode)
  - [CLI Mode](#cli-mode)
  - [CSV Format](#csv-format)
- [Keyboard Shortcuts](#keyboard-shortcuts)
- [Key Format](#key-format)
- [Pagination Modes](#pagination-modes)
- [Project Architecture](#project-architecture)
- [License](#license)

---

## Features

- **Import keybindings** directly from flight simulators
- **Visual table editor** — reorder, rename, colorize, and organize keys
- **Global font controls** — family, size, style, underline, show/hide titles
- **Per-button text color** with color picker
- **Smart label splitting** — automatic text wrapping for long names across multiple lines
- **Pagination modes** — Pages (prev/next arrows) or Folders (parent/child navigation)
- **Device presets** — Stream Deck Mini, Mk2, XL, and Generic
- **CLI mode** for batch or automated profile generation
- **Key validation** with modifier normalization
- **Duplicate detection** — identifies and marks duplicate hotkeys
- **Settings persistence** — saves preferences between sessions

## Supported Simulators

| Simulator | File Format | Auto-Detection |
|-----------|------------|----------------|
| X-Plane 12 | `.prf` (preferences) | No — manual file selection |
| Microsoft Flight Simulator 2024 | `.csv` (CSV import) | No — manual file selection |
| Aerofly FS4 | `gc-map.mcf` | Yes — searches in Documents |
| Condor 3 | `controls.ini` | Yes — searches in Documents |

### Parser Details

- **X-Plane 12**: Reads `.prf` files and extracts `sim/*` command bindings with modifiers (CTRL, ALT, SHIFT). Converts command names like `sim/flight_controls/flaps_up` into readable categories ("Flight Controls" → "Flaps Up").

- **Aerofly FS4**: Parses the `gc-map.mcf` configuration file with XML-like structure. Filters keyboard-only bindings (specific device ID) and converts CamelCase names to readable format.

- **Condor 3**: Reads `controls.ini` files in INI format. Maps virtual key codes (VK codes) to standard key names and classifies commands by category (flight controls, views, instruments, etc.).

## Compatible Devices

| Device | Grid | Buttons | Model ID |
|--------|------|---------|----------|
| Stream Deck Mini | 3 × 2 | 6 | 20GAI9901 |
| Stream Deck Mk2 | 5 × 3 | 15 | 20GAA9901 |
| Stream Deck XL | 8 × 4 | 32 | 20GAT9902 |
| Generic | 5 × 3 | 15 | 20GAA9901 |

## Requirements

- Python 3.8 or higher
- Dependencies:
  ```
  ttkbootstrap>=1.10.0
  platformdirs>=3.0.0
  ```

## Installation

```bash
git clone https://github.com/jlgabriel/StreamDeck-Profile-Generator.git
cd StreamDeck-Profile-Generator
pip install -r requirements.txt
```

## Usage

### GUI Mode

```bash
python -m app
```

The GUI provides:
- **Toolbar** with device selector, max pages, text alignment, pagination mode, and profile name
- **Editable table** with columns: Include, Order, Original Name, Label, Keystroke, Category, Text Color, Split Label
- **Simulator menu** to import directly from supported simulators
- **File menu** to open/save CSV and export profiles
- **Edit menu** to duplicate rows, mark duplicates, and clear markers

### CLI Mode

For batch generation without a graphical interface:

```bash
python -m app --input keys.csv --output profile.streamDeckProfile --device xl
```

#### CLI Options

| Option | Description | Default |
|--------|-------------|---------|
| `--input` | Input CSV file | — |
| `--output` | Output `.streamDeckProfile` file | — |
| `--device` | `mini`, `mk2`, `xl`, `generic` | `xl` |
| `--max-pages` | Maximum pages/folders (1-10) | `10` |
| `--pagination` | `Pages` or `Folders` | `Pages` |
| `--text-alignment` | `bottom`, `middle`, `top` | `middle` |
| `--font-family` | Font name (e.g., `Arial`, `Verdana`) | System |
| `--font-size` | Font size in px (6-24) | `12` |
| `--font-style` | `Regular`, `Bold`, `Italic`, `Bold Italic` | — |
| `--font-underline` | Enable underline | Disabled |
| `--no-show-title` | Hide button titles | Show |
| `--gui` | Force GUI mode | — |

#### Full CLI Example

```bash
python -m app \
  --input my_keys.csv \
  --output xplane_profile.streamDeckProfile \
  --device xl \
  --max-pages 5 \
  --pagination Folders \
  --text-alignment bottom \
  --font-family "Verdana" \
  --font-size 10 \
  --font-style Bold
```

### CSV Format

The CSV file uses the following columns:

| Column | Description | Required |
|--------|-------------|----------|
| `name` | Profile name (only read from the first row) | No |
| `include` | `1` to include, `0` to exclude | No (default: `1`) |
| `order` | Numeric button order | No (auto) |
| `original` | Original command name from the simulator | No |
| `label` | Label displayed on the button | Yes |
| `keystroke` | Key combination (e.g., `CTRL+ALT+F1`) | Yes |
| `category` | Category for organization | No |
| `text_color` | Hex text color (e.g., `#FFFFFF`) | No (default: `#FFFFFF`) |
| `split_label` | `1` to split label into lines, `0` to not | No (default: `1`) |

#### CSV Example

```csv
name,include,order,original,label,keystroke,category,text_color,split_label
My Profile,1,1,sim/operation/quit,Quit,ALT+F4,Operation,#FF4444,1
,1,2,sim/engines/throttle_up,Throttle Up,F2,Engines,#00FF00,1
,1,3,sim/flight/flaps_down,Flaps Down,F6,Controls,#FFFFFF,1
,0,4,sim/view/free_camera,Free Camera,CTRL+F9,Views,#FFFFFF,1
```

> The fourth row has `include=0`, so it will be excluded from the exported profile.

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+N` | Add new row |
| `Ctrl+D` | Duplicate selected rows |
| `Ctrl+A` | Select all rows |
| `Ctrl+I` | Toggle inclusion (Include checkbox) |
| `Ctrl+S` | Toggle split label |
| `Ctrl+↑` | Move rows up |
| `Ctrl+↓` | Move rows down |
| `Delete` | Delete selected rows |
| `Space` | Toggle checkboxes |
| `F1` | Help (keyboard shortcuts) |
| `F2` | Edit selected row label |

## Key Format

Keys are written as modifier + key combinations, separated by `+`:

```
MODIFIER+MODIFIER+KEY
```

### Valid Modifiers

| Modifier | Synonyms |
|----------|----------|
| `CTRL` | `CONTROL`, `CTL` |
| `ALT` | `OPT`, `OPTION` |
| `SHIFT` | `SHF` |
| `WIN` | `CMD`, `COMMAND`, `META`, `SUPER` |

### Special Keys

- **Function**: `F1` through `F24`
- **Navigation**: `UP`, `DOWN`, `LEFT`, `RIGHT`, `HOME`, `END`, `PAGEUP`, `PAGEDOWN`
- **Editing**: `BACKSPACE`, `DELETE`, `INSERT`, `TAB`, `ENTER`, `RETURN`, `ESCAPE`, `SPACE`
- **Numpad**: `NUM0`-`NUM9`, `NUMADD`, `NUMSUB`, `NUMMUL`, `NUMDIV`, `NUMDECIMAL`, `NUMENTER`, `NUMLOCK`
- **Punctuation**: `COMMA`, `PERIOD`, `SEMICOLON`, `QUOTE`, `BACKQUOTE`, `MINUS`, `EQUAL`, `SLASH`, `BACKSLASH`, `LEFTBRACKET`, `RIGHTBRACKET`
- **Letters and Numbers**: `A`-`Z`, `0`-`9`

### Examples

```
CTRL+C              → Copy
CTRL+ALT+DELETE     → Ctrl+Alt+Delete
SHIFT+F5            → Shift+F5
WIN+CTRL+LEFT       → Win+Ctrl+Left
F12                 → Single key without modifiers
```

## Pagination Modes

### Pages Mode

Creates multiple pages with **prev/next** navigation buttons:
- Reserves **2 buttons per page** for navigation (arrows)
- First page has only a "next" arrow
- Last page has only a "previous" arrow
- Maximum 10 pages

### Folders Mode

Creates a folder structure with **parent/child** navigation:
- First page uses all available buttons
- Additional pages reserve **1 button** to go back
- Subfolders are accessed from the main page
- More space-efficient than Pages mode

## Project Architecture

```
StreamDeck-Profile-Generator/
├── app/
│   ├── __main__.py            # Entry point: CLI args + GUI launcher
│   ├── ui_main.py             # Main GUI window (ttkbootstrap)
│   ├── keys.py                # Key validation and normalization
│   ├── export/
│   │   └── streamdeck.py      # V3 profile builder + ZIP exporter
│   ├── readers/
│   │   ├── base.py            # SimBindingReader base class
│   │   ├── xplane_prf.py      # X-Plane 12 parser (.prf)
│   │   ├── aerofly.py         # Aerofly FS4 reader
│   │   ├── aerofly_parser.py  # Aerofly parser (gc-map.mcf)
│   │   ├── condor.py          # Condor 3 reader
│   │   └── condor_parser.py   # Condor parser (controls.ini)
│   └── assets/                # App icons (ico, icns, png)
├── requirements.txt
├── LICENSE
├── CLAUDE.md
└── README.md
```

### Data Flow

```
Simulator (.prf, .mcf, .ini)
        │
        ▼
   readers/*          ← Parse and normalize bindings
        │
        ▼
   keys.py            ← Validate and normalize keystrokes
        │
        ▼
   ui_main.py         ← Visual table editor (or CSV via CLI)
        │
        ▼
   export/streamdeck.py  ← Generate V3 profile (.streamDeckProfile)
        │
        ▼
   ZIP file           ← package.json + manifests + page structure
```

## Author

Developed by **Juan Luis Gabriel** ([@jlgabriel](https://github.com/jlgabriel))

## License

[MIT](LICENSE) - Copyright (c) 2026 Juan Luis Gabriel
