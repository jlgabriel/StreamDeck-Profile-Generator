# Stream Deck Profile Generator

**v0.8.2** — A Python desktop application (GUI + CLI) that reads flight simulator keybindings and generates Elgato Stream Deck profile files (`.streamDeckProfile`) in **V3 format**, compatible with Stream Deck software v7.3+.

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
- [Project Architecture](#project-architecture)
- [Building a Standalone EXE](#building-a-standalone-exe)
- [License](#license)

---

## Features

- **Import keybindings** directly from flight simulators (native file formats)
- **Visual table editor** — reorder, rename, colorize, and organize keys
- **Global font controls** — family, size, style, underline, show/hide titles
- **Per-button text color** with color picker
- **Smart label splitting** — automatic text wrapping for long button names
- **Multi-page profiles** with automatic navigation buttons (up to 10 pages)
- **Device presets** — Stream Deck Mini, Mk2, XL, and Generic
- **CLI mode** for batch or automated profile generation
- **Key validation** with modifier normalization
- **Settings persistence** — saves preferences between sessions

## Supported Simulators

| Simulator | File Format | Import Method |
|-----------|------------|---------------|
| X-Plane 12 | `.prf` (preferences) | Manual file selection |
| Microsoft Flight Simulator 2024 | `.xml` (inputprofile) | Auto-detect or browse |
| Aerofly FS4 | `gc-map.mcf` | Auto-detect or browse |
| Condor 3 | `controls.ini` | Auto-detect or browse |

### Parser Details

- **X-Plane 12**: Reads `.prf` files and extracts `sim/*` command bindings with modifiers (CTRL, ALT, SHIFT). Converts command paths into readable categories and labels.

- **MSFS 2024**: Parses XML inputprofile files exported from the simulator. Maps Windows VK codes to standard key names, organizes by Context (ATC, Cockpit Camera, Drone, etc.), and preserves acronyms (ATC, EFB, VR, HUD) in labels.

- **Aerofly FS4**: Parses the `gc-map.mcf` configuration file. Filters keyboard-only bindings and converts function names to readable format with directional indicators (+/-).

- **Condor 3**: Reads `controls.ini` files in INI format. Maps virtual key codes to standard key names and classifies commands by category (flight controls, views, instruments, etc.).

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
- **Toolbar** with device selector, max pages, text alignment, and profile name
- **Font toolbar** with font family, size, style, underline, and show title controls
- **Editable table** with columns: Include, Order, Original Name, Label, Keystroke, Category, Text Color, Split Label
- **Simulator menu** to import directly from supported simulators
- **File menu** to open/save CSV and export profiles

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
| `--max-pages` | Maximum pages (1-10) | `10` |
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
  --text-alignment middle \
  --font-family "Arial" \
  --font-size 12 \
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

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+N` | Add new row |
| `Ctrl+D` | Duplicate selected rows |
| `Ctrl+A` | Select all rows |
| `Ctrl+I` | Toggle inclusion (Include checkbox) |
| `Ctrl+S` | Toggle split label |
| `Ctrl+Up` | Move rows up |
| `Ctrl+Down` | Move rows down |
| `Delete` | Delete selected rows |
| `Space` | Toggle checkboxes (when table is focused) |
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
- **Editing**: `BACKSPACE`, `DELETE`, `INSERT`, `TAB`, `ENTER`, `ESCAPE`, `SPACE`
- **Numpad**: `NUM0`-`NUM9`, `NUMPLUS`, `NUMMINUS`, `NUMMULTIPLY`, `NUMDIVIDE`, `NUMDECIMAL`, `NUMENTER`
- **Punctuation**: `COMMA`, `PERIOD`, `SEMICOLON`, `QUOTE`, `BACKQUOTE`, `MINUS`, `EQUALS`, `SLASH`, `BACKSLASH`, `LBRACKET`, `RBRACKET`
- **OEM**: `OEM102` (European keyboard `<>` key)
- **Letters and Numbers**: `A`-`Z`, `0`-`9`

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
│   │   ├── msfs2024.py        # MSFS 2024 reader
│   │   ├── msfs2024_parser.py # MSFS 2024 parser (XML inputprofile)
│   │   ├── aerofly.py         # Aerofly FS4 reader
│   │   ├── aerofly_parser.py  # Aerofly parser (gc-map.mcf)
│   │   ├── condor.py          # Condor 3 reader
│   │   └── condor_parser.py   # Condor parser (controls.ini)
│   └── assets/                # App icons (ico, icns, png)
├── requirements.txt
├── run.py                       # PyInstaller entry point
├── StreamDeckProfileGenerator.spec  # PyInstaller build config
├── build.bat                    # Windows build script
├── LICENSE
├── CLAUDE.md
└── README.md
```

### Data Flow

```
Simulator (.prf, .xml, .mcf, .ini)
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

## Building a Standalone EXE

You can build a standalone Windows executable that doesn't require Python installed:

### Prerequisites

```bash
pip install pyinstaller
```

### Build

Run the build script:

```bash
build.bat
```

Or manually:

```bash
pyinstaller StreamDeckProfileGenerator.spec --noconfirm
```

The executable will be generated at `dist/StreamDeckProfileGenerator.exe` (~26 MB).

### Notes

- The EXE is a single-file portable executable — no installation needed
- User settings are stored in `%LOCALAPPDATA%/Community/StreamDeckProfileGen/` and are not bundled with the EXE
- `build/` and `dist/` directories are excluded from version control

## Author

Developed by **Juan Luis Gabriel** ([@jlgabriel](https://github.com/jlgabriel))

## License

[MIT](LICENSE) - Copyright (c) 2026 Juan Luis Gabriel
