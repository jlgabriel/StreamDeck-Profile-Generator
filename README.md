# Stream Deck Profile Generator

A Python desktop application (GUI + CLI) that reads flight simulator keybindings and generates Elgato Stream Deck profile files (`.streamDeckProfile`).

Supports **Stream Deck V3 format** compatible with Stream Deck software v7.3+.

![Stream Deck Profile Generator](app/assets/icon.png)

## Features

- **Import keybindings** from flight simulators:
  - X-Plane 12 (`.prf` files)
  - Microsoft Flight Simulator 2024 (CSV)
  - Aerofly FS4 (`gc-map.mcf`)
  - Condor 3 (`controls.ini`)
- **Visual table editor** — reorder, rename, color-code, and organize keys
- **Global font controls** — family, size, style, underline, show/hide titles
- **Per-button text color** with color picker
- **Smart label splitting** — automatically wraps long labels across lines
- **Pagination modes** — Pages (prev/next arrows) or Folders (parent/child)
- **Device presets** — Stream Deck Mini, Mk2, XL, and Generic
- **CLI mode** for batch/automated profile generation
- **Keystroke validation** with modifier normalization

## Requirements

- Python 3.8+
- Dependencies:
  ```
  ttkbootstrap>=1.10.0
  platformdirs>=3.0.0
  ```

## Installation

```bash
git clone https://github.com/YOUR_USER/StreamDeck-Profile-Generator.git
cd StreamDeck-Profile-Generator
pip install -r requirements.txt
```

## Usage

### GUI Mode (default)

```bash
python -m app
```

### CLI Mode

```bash
python -m app --input keys.csv --output profile.streamDeckProfile --device xl
```

#### CLI Options

| Option | Description | Default |
|--------|-------------|---------|
| `--input` | Input CSV file | — |
| `--output` | Output `.streamDeckProfile` | — |
| `--device` | `mini`, `mk2`, `xl`, `generic` | `xl` |
| `--max-pages` | Maximum pages/folders | `10` |
| `--pagination` | `Pages` or `Folders` | `Pages` |
| `--text-alignment` | `bottom`, `middle`, `top` | `middle` |
| `--font-family` | Font name (e.g., `Arial`) | System default |
| `--font-size` | Font size in px (6-24) | `12` |
| `--font-style` | `Regular`, `Bold`, `Italic`, `Bold Italic` | — |
| `--font-underline` | Enable underline | Off |
| `--no-show-title` | Hide button titles | Show |

### CSV Format

```csv
name,include,order,original,label,keystroke,category,text_color,split_label
My Profile,1,1,sim/operation/quit,Quit,ALT+F4,Operation,#FFFFFF,1
,1,2,sim/engines/throttle_up,Throttle Up,F2,Engines,#00FF00,1
```

## Supported Devices

| Device | Grid | Model ID |
|--------|------|----------|
| Stream Deck Mini | 3x2 | 20GAI9901 |
| Stream Deck Mk2 | 5x3 | 20GAA9901 |
| Stream Deck XL | 8x4 | 20GAT9902 |

## License

[MIT](LICENSE)
