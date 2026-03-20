# Stream Deck Profile Generator

Aplicación de escritorio (GUI + CLI) en Python que lee keybindings de simuladores de vuelo y genera archivos de perfil para Elgato Stream Deck (`.streamDeckProfile`) en **formato V3**, compatible con Stream Deck software v7.3+.

![Stream Deck Profile Generator](app/assets/icon.png)

---

## Tabla de Contenidos

- [Características](#características)
- [Simuladores Soportados](#simuladores-soportados)
- [Dispositivos Compatibles](#dispositivos-compatibles)
- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Uso](#uso)
  - [Modo GUI](#modo-gui)
  - [Modo CLI](#modo-cli)
  - [Formato CSV](#formato-csv)
- [Atajos de Teclado](#atajos-de-teclado)
- [Formato de Teclas](#formato-de-teclas)
- [Modos de Paginación](#modos-de-paginación)
- [Arquitectura del Proyecto](#arquitectura-del-proyecto)
- [Licencia](#licencia)

---

## Características

- **Importar keybindings** directamente desde simuladores de vuelo
- **Editor visual en tabla** — reordenar, renombrar, colorear y organizar teclas
- **Controles de fuente globales** — familia, tamaño, estilo, subrayado, mostrar/ocultar títulos
- **Color de texto por botón** con selector de color
- **División inteligente de etiquetas** — ajuste automático de texto largo en múltiples líneas
- **Modos de paginación** — Páginas (flechas prev/next) o Carpetas (navegación padre/hijo)
- **Presets de dispositivos** — Stream Deck Mini, Mk2, XL y Genérico
- **Modo CLI** para generación de perfiles por lotes o automatizada
- **Validación de teclas** con normalización de modificadores
- **Detección de duplicados** — identifica y marca hotkeys duplicadas
- **Persistencia de configuración** — guarda preferencias entre sesiones

## Simuladores Soportados

| Simulador | Formato de Archivo | Detección Automática |
|-----------|-------------------|---------------------|
| X-Plane 12 | `.prf` (preferences) | No — selección manual del archivo |
| Microsoft Flight Simulator 2024 | `.csv` (importar CSV) | No — selección manual del archivo |
| Aerofly FS4 | `gc-map.mcf` | Sí — busca en Documentos |
| Condor 3 | `controls.ini` | Sí — busca en Documentos |

### Detalles de cada parser

- **X-Plane 12**: Lee archivos `.prf` y extrae las asignaciones `sim/*` con sus modificadores (CTRL, ALT, SHIFT). Convierte nombres de comando como `sim/flight_controls/flaps_up` a categorías legibles ("Flight Controls" → "Flaps Up").

- **Aerofly FS4**: Parsea el archivo de configuración `gc-map.mcf` con estructura XML-like. Filtra únicamente las asignaciones de teclado (device ID específico) y convierte nombres CamelCase a formato legible.

- **Condor 3**: Lee archivos `controls.ini` en formato INI. Mapea códigos de tecla virtual (VK codes) a nombres estándar y clasifica comandos por categoría (controles de vuelo, vistas, instrumentos, etc.).

## Dispositivos Compatibles

| Dispositivo | Grilla | Botones | Model ID |
|-------------|--------|---------|----------|
| Stream Deck Mini | 3 × 2 | 6 | 20GAI9901 |
| Stream Deck Mk2 | 5 × 3 | 15 | 20GAA9901 |
| Stream Deck XL | 8 × 4 | 32 | 20GAT9902 |
| Genérico | 5 × 3 | 15 | 20GAA9901 |

## Requisitos

- Python 3.8 o superior
- Dependencias:
  ```
  ttkbootstrap>=1.10.0
  platformdirs>=3.0.0
  ```

## Instalación

```bash
git clone https://github.com/jlgabriel/StreamDeck-Profile-Generator.git
cd StreamDeck-Profile-Generator
pip install -r requirements.txt
```

## Uso

### Modo GUI

```bash
python -m app
```

El modo GUI ofrece:
- **Barra de herramientas** con selector de dispositivo, páginas máximas, alineación de texto, modo de paginación y nombre del perfil
- **Tabla editable** con columnas: Incluir, Orden, Nombre Original, Etiqueta, Keystroke, Categoría, Color de Texto, Split Label
- **Menú Simulador** para importar directamente desde los simuladores soportados
- **Menú Archivo** para abrir/guardar CSV y exportar perfiles
- **Menú Editar** para duplicar filas, marcar duplicados y limpiar marcadores

### Modo CLI

Para generación por lotes sin interfaz gráfica:

```bash
python -m app --input keys.csv --output profile.streamDeckProfile --device xl
```

#### Opciones CLI

| Opción | Descripción | Por defecto |
|--------|-------------|-------------|
| `--input` | Archivo CSV de entrada | — |
| `--output` | Archivo `.streamDeckProfile` de salida | — |
| `--device` | `mini`, `mk2`, `xl`, `generic` | `xl` |
| `--max-pages` | Máximo de páginas/carpetas (1-10) | `10` |
| `--pagination` | `Pages` o `Folders` | `Pages` |
| `--text-alignment` | `bottom`, `middle`, `top` | `middle` |
| `--font-family` | Nombre de fuente (ej: `Arial`, `Verdana`) | Sistema |
| `--font-size` | Tamaño de fuente en px (6-24) | `12` |
| `--font-style` | `Regular`, `Bold`, `Italic`, `Bold Italic` | — |
| `--font-underline` | Habilitar subrayado | Desactivado |
| `--no-show-title` | Ocultar títulos en los botones | Mostrar |
| `--gui` | Forzar modo GUI | — |

#### Ejemplo completo CLI

```bash
python -m app \
  --input mis_teclas.csv \
  --output perfil_xplane.streamDeckProfile \
  --device xl \
  --max-pages 5 \
  --pagination Folders \
  --text-alignment bottom \
  --font-family "Verdana" \
  --font-size 10 \
  --font-style Bold
```

### Formato CSV

El archivo CSV usa las siguientes columnas:

| Columna | Descripción | Obligatorio |
|---------|-------------|-------------|
| `name` | Nombre del perfil (solo se lee de la primera fila) | No |
| `include` | `1` para incluir, `0` para excluir | No (default: `1`) |
| `order` | Orden numérico del botón | No (auto) |
| `original` | Nombre original del comando en el simulador | No |
| `label` | Etiqueta que se muestra en el botón | Sí |
| `keystroke` | Combinación de teclas (ej: `CTRL+ALT+F1`) | Sí |
| `category` | Categoría para organización | No |
| `text_color` | Color hexadecimal del texto (ej: `#FFFFFF`) | No (default: `#FFFFFF`) |
| `split_label` | `1` para dividir etiqueta en líneas, `0` para no | No (default: `1`) |

#### Ejemplo CSV

```csv
name,include,order,original,label,keystroke,category,text_color,split_label
Mi Perfil,1,1,sim/operation/quit,Salir,ALT+F4,Operación,#FF4444,1
,1,2,sim/engines/throttle_up,Throttle Up,F2,Motores,#00FF00,1
,1,3,sim/flight/flaps_down,Flaps Down,F6,Controles,#FFFFFF,1
,0,4,sim/view/free_camera,Cámara Libre,CTRL+F9,Vistas,#FFFFFF,1
```

> La cuarta fila tiene `include=0`, por lo que será excluida del perfil exportado.

## Atajos de Teclado

| Atajo | Acción |
|-------|--------|
| `Ctrl+N` | Agregar nueva fila |
| `Ctrl+D` | Duplicar filas seleccionadas |
| `Ctrl+A` | Seleccionar todas las filas |
| `Ctrl+I` | Alternar inclusión (checkbox Include) |
| `Ctrl+S` | Alternar split label |
| `Ctrl+↑` | Mover filas hacia arriba |
| `Ctrl+↓` | Mover filas hacia abajo |
| `Delete` | Eliminar filas seleccionadas |
| `Espacio` | Alternar checkboxes |
| `F1` | Ayuda (atajos de teclado) |
| `F2` | Editar etiqueta de la fila seleccionada |

## Formato de Teclas

Las teclas se escriben como combinaciones de modificadores + tecla, separados por `+`:

```
MODIFICADOR+MODIFICADOR+TECLA
```

### Modificadores válidos

| Modificador | Sinónimos |
|-------------|-----------|
| `CTRL` | `CONTROL`, `CTL` |
| `ALT` | `OPT`, `OPTION` |
| `SHIFT` | `SHF` |
| `WIN` | `CMD`, `COMMAND`, `META`, `SUPER` |

### Teclas especiales

- **Función**: `F1` a `F24`
- **Navegación**: `UP`, `DOWN`, `LEFT`, `RIGHT`, `HOME`, `END`, `PAGEUP`, `PAGEDOWN`
- **Edición**: `BACKSPACE`, `DELETE`, `INSERT`, `TAB`, `ENTER`, `RETURN`, `ESCAPE`, `SPACE`
- **Numérico**: `NUM0`-`NUM9`, `NUMADD`, `NUMSUB`, `NUMMUL`, `NUMDIV`, `NUMDECIMAL`, `NUMENTER`, `NUMLOCK`
- **Puntuación**: `COMMA`, `PERIOD`, `SEMICOLON`, `QUOTE`, `BACKQUOTE`, `MINUS`, `EQUAL`, `SLASH`, `BACKSLASH`, `LEFTBRACKET`, `RIGHTBRACKET`
- **Letras y números**: `A`-`Z`, `0`-`9`

### Ejemplos

```
CTRL+C              → Copiar
CTRL+ALT+DELETE     → Ctrl+Alt+Supr
SHIFT+F5            → Shift+F5
WIN+CTRL+LEFT       → Win+Ctrl+Izquierda
F12                 → Tecla sola sin modificadores
```

## Modos de Paginación

### Modo Páginas (Pages)

Crea múltiples páginas con botones de navegación **prev/next**:
- Se reservan **2 botones por página** para navegación (flechas)
- La primera página tiene solo flecha "siguiente"
- La última página tiene solo flecha "anterior"
- Máximo 10 páginas

### Modo Carpetas (Folders)

Crea una estructura de carpetas con navegación **padre/hijo**:
- La primera página usa todos los botones disponibles
- Las páginas adicionales reservan **1 botón** para volver
- Desde la página principal se accede a las subcarpetas
- Más eficiente en uso de espacio que el modo Páginas

## Arquitectura del Proyecto

```
StreamDeck-Profile-Generator/
├── app/
│   ├── __main__.py            # Punto de entrada: args CLI + lanzador GUI
│   ├── ui_main.py             # Ventana principal GUI (ttkbootstrap)
│   ├── keys.py                # Validación y normalización de teclas
│   ├── export/
│   │   └── streamdeck.py      # Constructor de perfiles V3 + exportador ZIP
│   ├── readers/
│   │   ├── base.py            # Clase base SimBindingReader
│   │   ├── xplane_prf.py      # Parser de X-Plane 12 (.prf)
│   │   ├── aerofly.py         # Reader de Aerofly FS4
│   │   ├── aerofly_parser.py  # Parser de Aerofly (gc-map.mcf)
│   │   ├── condor.py          # Reader de Condor 3
│   │   └── condor_parser.py   # Parser de Condor (controls.ini)
│   └── assets/                # Iconos de la aplicación (ico, icns, png)
├── requirements.txt
├── LICENSE
├── CLAUDE.md
└── README.md
```

### Flujo de datos

```
Simulador (.prf, .mcf, .ini)
        │
        ▼
   readers/*          ← Parsean y normalizan bindings
        │
        ▼
   keys.py            ← Validan y normalizan keystrokes
        │
        ▼
   ui_main.py         ← Editor visual en tabla (o CSV vía CLI)
        │
        ▼
   export/streamdeck.py  ← Genera perfil V3 (.streamDeckProfile)
        │
        ▼
   Archivo ZIP         ← package.json + manifests + estructura de páginas
```

## Autor

Desarrollado por **Juan Luis Gabriel** ([@jlgabriel](https://github.com/jlgabriel))

## Licencia

[MIT](LICENSE) - Copyright (c) 2026 Juan Luis Gabriel
