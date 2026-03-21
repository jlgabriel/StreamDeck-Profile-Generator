"""
MSFS 2024 XML Parser for Stream Deck Profile Generator
Parses inputprofile XML files exported from Microsoft Flight Simulator 2024
and extracts keyboard bindings.
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict


# Windows Virtual Key codes used in MSFS 2024 inputprofiles
# Maps VK code (int) -> canonical key name matching app/keys.py
VK_CODE_MAP = {
    # Modifier keys (used to detect CTRL/ALT/SHIFT combos)
    160: "SHIFT", 161: "SHIFT",   # Left/Right Shift
    162: "CTRL",  163: "CTRL",    # Left/Right Ctrl
    164: "ALT",   165: "ALT",     # Left/Right Alt

    # Letters (VK 65-90)
    **{vk: chr(vk) for vk in range(65, 91)},

    # Digits (VK 48-57)
    **{vk: str(vk - 48) for vk in range(48, 58)},

    # Function keys (VK 112-135)
    **{vk: f"F{vk - 111}" for vk in range(112, 136)},

    # Navigation
    37: "LEFT", 38: "UP", 39: "RIGHT", 40: "DOWN",
    36: "HOME", 35: "END", 33: "PAGEUP", 34: "PAGEDOWN",

    # Editing
    27: "ESC", 9: "TAB", 13: "ENTER", 32: "SPACE",
    8: "BACKSPACE", 46: "DELETE", 45: "INSERT",

    # Numpad
    96: "NUM0", 97: "NUM1", 98: "NUM2", 99: "NUM3", 100: "NUM4",
    101: "NUM5", 102: "NUM6", 103: "NUM7", 104: "NUM8", 105: "NUM9",
    107: "NUMPLUS", 109: "NUMMINUS", 106: "NUMMULTIPLY",
    111: "NUMDIVIDE", 110: "NUMDECIMAL",

    # Punctuation
    187: "EQUALS", 189: "MINUS", 188: "COMMA", 190: "PERIOD",
    191: "SLASH", 186: "SEMICOLON", 222: "QUOTE", 192: "BACKQUOTE",
    219: "LBRACKET", 221: "RBRACKET", 220: "BACKSLASH",

    # Misc
    19: "PAUSE", 145: "SCROLLLOCK", 144: "NUMLOCK",
    20: "CAPSLOCK", 44: "PRINTSCREEN",

    # OEM keys (region-dependent)
    226: "OEM102",  # <> key on European keyboards
}

# Modifier VK codes
MODIFIER_VKS = {160, 161, 162, 163, 164, 165}

# Context names -> human-readable categories
CONTEXT_CATEGORIES = {
    "3RD_PARTY": "3rd Party",
    "ALWAYS": "General",
    "ATC": "ATC",
    "COCKPIT_CAMERA": "Cockpit Camera",
    "COCKPIT_GLOBAL_CAMERA": "Cockpit Camera",
    "COCKPIT_GLOBAL_CAMERA_TRANSLATE": "Cockpit Camera",
    "COCKPIT_INTERACTIONS": "Cockpit",
    "COCKPIT_INTERACTIONS_LOCK": "Cockpit",
    "COCKPIT_VR_CAMERA": "VR",
    "CURSOR": "Cursor",
    "CURSOR_LOCK": "Cursor",
    "CURSOR_MODE_SWITCHES": "Cursor",
    "DEBUG": "Debug",
    "DEVMODE": "Dev Mode",
    "DEVMODECAMERA": "Dev Mode",
    "DRONE": "Drone Camera",
    "DRONE_GLOBAL": "Drone Camera",
    "EFB": "EFB",
    "EFB_CORE": "EFB",
    "EXTERNAL_CAMERA": "External Camera",
    "FIXED_CAMERA": "Fixed Camera",
    "HANGAR_CAMERA": "Hangar",
    "INGAME_UI": "UI",
    "INSTRUMENTS_CAMERA": "Instruments Camera",
    "MENU": "Menu",
    "MENU_CORE": "Menu",
    "MENU_GLOBAL": "Menu",
    "MENU_MOUSE": "Menu",
    "MISSION_FLOW_TOOLS": "Mission",
    "MODE_INTERACTION": "Modes",
    "MODE_PAUSE": "Modes",
    "MODES": "Modes",
    "PC_MODE_SWITCHES": "Modes",
    "PHOTO_MODE_ACTIONS": "Photo Mode",
    "PHOTO_MODE_ROTATION": "Photo Mode",
    "PHOTO_MODE_SWITCHES": "Photo Mode",
    "PHOTO_MODE_TRANSLATION": "Photo Mode",
    "PLAYER_CHARACTER_FPV": "Player Character",
    "PLAYER_CHARACTER_INTERACTION": "Player Character",
    "PLAYER_CHARACTER_MOVEMENT": "Player Character",
    "REPLAY": "Replay",
    "RTC": "RTC",
    "SIM_SHORTCUT": "Sim Shortcuts",
    "SLEW": "Slew",
    "SMART_CAMERA": "Smart Camera",
    "SPECTATOR": "Spectator",
    "TOOLBAR": "Toolbar",
    "TOUCHSCREEN_INTERACTIONS": "Touchscreen",
    "TRUE_COCKPIT": "Cockpit",
    "USER_CAMERA": "User Camera",
    "VIEW_MODE_SWITCHES": "View Modes",
    "WORLDMAP_COMMON": "World Map",
    "WORLDMAP_PAD": "World Map",
}

# Contexts to skip (not useful for Stream Deck)
SKIP_CONTEXTS = {
    "DEBUG", "DEVMODE", "DEVMODECAMERA",
    "CURSOR", "CURSOR_LOCK", "CURSOR_MODE_SWITCHES",
    "MENU_MOUSE", "TOUCHSCREEN_INTERACTIONS",
    "COCKPIT_VR_CAMERA", "HANGAR_CAMERA",
    "WORLDMAP_PAD",
}


# Words that should stay uppercase in labels
_UPPERCASE_WORDS = {
    "ATC", "EFB", "VR", "HUD", "UI", "SR", "IFR", "VFR",
    "GPS", "NAV", "COM", "DME", "ADF", "AP", "FPS",
    "RPM", "HDG", "ALT", "VS", "FLC", "FD", "YD",
    "ILS", "VOR", "NDB", "OBS", "CDI", "HSI",
    "XCLOUD", "RTC", "DOF", "DEC", "INC",
}


def _clean_action_name(action_name: str) -> str:
    """Convert KEY_SOMETHING_TOGGLE -> Something Toggle, keeping acronyms uppercase."""
    name = action_name
    # Remove KEY_ prefix
    if name.startswith("KEY_"):
        name = name[4:]
    # Remove CAMERA_ prefix (already categorized)
    elif name.startswith("CAMERA_"):
        name = name[7:]

    # Replace underscores with spaces, apply casing
    parts = name.split("_")
    result = []
    for p in parts:
        upper = p.upper()
        if upper in _UPPERCASE_WORDS:
            result.append(upper)
        else:
            result.append(p.capitalize())
    return " ".join(result)


def _parse_keys(key_elements) -> str:
    """Parse <KEY> elements into a keystroke string like CTRL+ALT+K."""
    modifiers = []
    main_keys = []

    for key_elem in key_elements:
        vk = int(key_elem.text)
        if vk in MODIFIER_VKS:
            mod_name = VK_CODE_MAP[vk]
            if mod_name not in modifiers:
                modifiers.append(mod_name)
        elif vk in VK_CODE_MAP:
            main_keys.append(VK_CODE_MAP[vk])
        else:
            # Unknown VK code — use Information attribute as fallback
            info = key_elem.get("Information", f"VK{vk}")
            main_keys.append(info.upper())

    # Build keystroke: modifiers in canonical order, then main key
    mod_order = {"CTRL": 0, "ALT": 1, "SHIFT": 2}
    modifiers.sort(key=lambda m: mod_order.get(m, 99))

    parts = modifiers + main_keys
    return "+".join(parts) if parts else ""


def parse_msfs2024_xml(file_path: str) -> List[Dict]:
    """
    Parse MSFS 2024 inputprofile XML and extract keyboard bindings.
    Returns list of binding dictionaries for Stream Deck Profile Generator.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # MSFS XML is not well-formed (no single root element),
    # so strip the XML declaration and wrap in a root tag
    content = path.read_text(encoding="utf-8")
    # Remove <?xml ...?> declaration if present
    if content.startswith("<?xml"):
        content = content[content.index("?>") + 2:].lstrip()
    wrapped = f"<Root>{content}</Root>"

    try:
        root = ET.fromstring(wrapped)
    except ET.ParseError as e:
        raise Exception(f"Could not parse XML: {e}")

    rows = []
    order = 0

    for context in root.findall(".//Context"):
        context_name = context.get("ContextName", "")

        if context_name in SKIP_CONTEXTS:
            continue

        category = CONTEXT_CATEGORIES.get(context_name, context_name.replace("_", " ").title())

        for action in context.findall("Action"):
            action_name = action.get("ActionName", "")
            flag = action.get("Flag", "2")

            # Find Primary keybinding
            primary = action.find("Primary")
            if primary is None:
                continue  # No key assigned

            key_elements = primary.findall("KEY")
            if not key_elements:
                continue

            keystroke = _parse_keys(key_elements)
            if not keystroke:
                continue

            # Clean up action name for display
            label = _clean_action_name(action_name)

            order += 1
            row = {
                "include": True,
                "order": order,
                "original": action_name,
                "label": label,
                "keystroke": keystroke,
                "category": category,
                "text_color": "#FFFFFF",
                "split_label": True,
            }
            rows.append(row)

    if not rows:
        raise Exception("No keyboard bindings found in the XML file")

    print(f"MSFS 2024: parsed {len(rows)} keyboard bindings")
    return rows


if __name__ == "__main__":
    import sys
    try:
        path = sys.argv[1] if len(sys.argv) > 1 else "Keyboard layout v1.xml"
        bindings = parse_msfs2024_xml(path)
        print(f"\nParsed {len(bindings)} bindings:")

        by_cat = {}
        for b in bindings:
            by_cat.setdefault(b["category"], []).append(b)

        for cat, items in sorted(by_cat.items()):
            print(f"\n{cat} ({len(items)}):")
            for item in items[:3]:
                print(f"  {item['label']:<40} {item['keystroke']:<20}")
            if len(items) > 3:
                print(f"  ... and {len(items) - 3} more")
    except Exception as e:
        print(f"Error: {e}")
