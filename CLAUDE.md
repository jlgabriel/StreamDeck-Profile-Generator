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
- **Stream Deck V3 format**: ZIP containing `package.json` at root + `Profiles/UUID.sdProfile/` with JSON manifests. The `.sdProfile` folder UUID must be independent from page UUIDs. Default page UUID goes in `Pages.Default`, NOT in the `Pages.Pages` array.
- **Pagination modes**: "Pages" (prev/next arrows) or "Folders" (parent/child navigation)
- **Font settings are global** (apply to all buttons); text_color is per-button
- **Device presets**: mini (3x2), mk2 (5x3), xl (8x4), generic (5x3)

## Supported Simulators
- X-Plane 12 (.prf files)
- Microsoft Flight Simulator 2024 (CSV import)
- Aerofly FS4 (gc-map.mcf files)
- Condor 3 (controls.ini files)

## Conventions
- User communicates in Spanish
- Keep the GUI simple — toolbar-based controls, no complex dialogs
- Settings persist in user config directory via `platformdirs`
- Export validates keystrokes before generating profiles
