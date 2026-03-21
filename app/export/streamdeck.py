#!/usr/bin/env python3
"""
Stream Deck Profile Generator - Format V3
Compatible with Stream Deck software v7.3+
"""

import json
import platform
import zipfile
import uuid
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Device presets
DEVICE_PRESETS = {
    "mini":    {"cols": 3, "rows": 2, "model": "20GAI9901"},
    "mk2":    {"cols": 5, "rows": 3, "model": "20GAA9901"},
    "xl":     {"cols": 8, "rows": 4, "model": "20GAT9902"},
    "generic": {"cols": 5, "rows": 3, "model": "20GAA9901"},
}

# Virtual Key Codes mapping
VK_CODES = {
    # Letters
    'A': 65, 'B': 66, 'C': 67, 'D': 68, 'E': 69, 'F': 70, 'G': 71, 'H': 72,
    'I': 73, 'J': 74, 'K': 75, 'L': 76, 'M': 77, 'N': 78, 'O': 79, 'P': 80,
    'Q': 81, 'R': 82, 'S': 83, 'T': 84, 'U': 85, 'V': 86, 'W': 87, 'X': 88,
    'Y': 89, 'Z': 90,
    # Digits (top row)
    '0': 48, '1': 49, '2': 50, '3': 51, '4': 52, '5': 53, '6': 54, '7': 55, '8': 56, '9': 57,
    # Function keys
    'F1': 112, 'F2': 113, 'F3': 114, 'F4': 115, 'F5': 116, 'F6': 117, 'F7': 118, 'F8': 119,
    'F9': 120, 'F10': 121, 'F11': 122, 'F12': 123, 'F13': 124, 'F14': 125, 'F15': 126,
    'F16': 127, 'F17': 128, 'F18': 129, 'F19': 130, 'F20': 131, 'F21': 132, 'F22': 133,
    'F23': 134, 'F24': 135,
    # Navigation and editing
    'SPACE': 32, 'ENTER': 13, 'TAB': 9, 'ESC': 27, 'BACKSPACE': 8,
    'DELETE': 46, 'INSERT': 45, 'HOME': 36, 'END': 35, 'PAGEUP': 33, 'PAGEDOWN': 34,
    'LEFT': 37, 'UP': 38, 'RIGHT': 39, 'DOWN': 40,
    # Punctuation (OEM keys)
    'PLUS': 187, 'EQUALS': 187, 'MINUS': 189, 'COMMA': 188, 'PERIOD': 190, 'SLASH': 191,
    'SEMICOLON': 186, 'QUOTE': 222, 'BACKQUOTE': 192, 'LBRACKET': 219, 'RBRACKET': 221,
    'BACKSLASH': 220,
    # Numpad
    'NUM0': 96, 'NUM1': 97, 'NUM2': 98, 'NUM3': 99, 'NUM4': 100, 'NUM5': 101,
    'NUM6': 102, 'NUM7': 103, 'NUM8': 104, 'NUM9': 105,
    'NUMPLUS': 107, 'NUMMINUS': 109, 'NUMMULTIPLY': 106, 'NUMDIVIDE': 111,
    'NUMDECIMAL': 110, 'NUMENTER': 13,
}

# Qt Key Codes mapping (QTKeyCode field in Stream Deck hotkey actions)
# Only keys where Qt code differs from VK code need to be listed here.
# Letters (A-Z), digits (0-9), SPACE, and numpad keys use VK code directly.
QT_KEY_CODES = {
    # Navigation and editing — Qt::Key_* constants (0x01000000+)
    'ESC': 16777216, 'TAB': 16777217, 'BACKSPACE': 16777219,
    'ENTER': 16777220, 'INSERT': 16777222, 'DELETE': 16777223,
    'HOME': 16777232, 'END': 16777233,
    'LEFT': 16777234, 'UP': 16777235, 'RIGHT': 16777236, 'DOWN': 16777237,
    'PAGEUP': 16777238, 'PAGEDOWN': 16777239,
    # Function keys — Qt::Key_F1 = 0x01000030 = 16777264
    'F1': 16777264, 'F2': 16777265, 'F3': 16777266, 'F4': 16777267,
    'F5': 16777268, 'F6': 16777269, 'F7': 16777270, 'F8': 16777271,
    'F9': 16777272, 'F10': 16777273, 'F11': 16777274, 'F12': 16777275,
    'F13': 16777276, 'F14': 16777277, 'F15': 16777278, 'F16': 16777279,
    'F17': 16777280, 'F18': 16777281, 'F19': 16777282, 'F20': 16777283,
    'F21': 16777284, 'F22': 16777285, 'F23': 16777286, 'F24': 16777287,
    # Punctuation — ASCII code of the character (US keyboard layout)
    'PLUS': 43, 'EQUALS': 61, 'MINUS': 45, 'COMMA': 44, 'PERIOD': 46,
    'SLASH': 47, 'SEMICOLON': 59, 'QUOTE': 39, 'BACKQUOTE': 96,
    'LBRACKET': 91, 'RBRACKET': 93, 'BACKSLASH': 92,
    # Numpad — ASCII code of the character they produce
    'NUM0': 48, 'NUM1': 49, 'NUM2': 50, 'NUM3': 51, 'NUM4': 52,
    'NUM5': 53, 'NUM6': 54, 'NUM7': 55, 'NUM8': 56, 'NUM9': 57,
    'NUMPLUS': 43, 'NUMMINUS': 45, 'NUMMULTIPLY': 42, 'NUMDIVIDE': 47,
    'NUMDECIMAL': 46, 'NUMENTER': 16777221,
}

# Plugin definitions for V3 format
PLUGIN_HOTKEY = {"Name": "Activate a Key Command", "UUID": "com.elgato.streamdeck.system.hotkey", "Version": "1.0"}
PLUGIN_PAGE_NEXT = {"Name": "Pages", "UUID": "com.elgato.streamdeck.page", "Version": "1.0"}
PLUGIN_PAGE_PREV = {"Name": "Pages", "UUID": "com.elgato.streamdeck.page", "Version": "1.0"}


def generate_uuid_v4() -> str:
    return str(uuid.uuid4())


def process_label_for_display(label: str, split_label: bool = False) -> str:
    if not label or not label.strip():
        return label
    if not split_label:
        return label

    words = label.strip().split()
    if len(words) <= 1:
        return label
    if len(words) == 2:
        return '\n'.join(words)
    if len(words) <= 4:
        mid = len(words) // 2
        return f"{' '.join(words[:mid])}\n{' '.join(words[mid:])}"

    result_lines = []
    i = 0
    while i < len(words):
        if i + 1 < len(words):
            result_lines.append(f"{words[i]} {words[i+1]}")
            i += 2
        else:
            result_lines.append(words[i])
            i += 1
    return '\n'.join(result_lines)


def coord_key(row: int, col: int) -> str:
    return f"{col},{row}"


def parse_hotkey(hotkey_str: str) -> List[Dict]:
    """Convert string like 'CTRL+ALT+A' to hotkey array (4 elements)."""
    placeholder = {
        "KeyCmd": False, "KeyCtrl": False, "KeyModifiers": 0,
        "KeyOption": False, "KeyShift": False,
        "NativeCode": 146, "QTKeyCode": 33554431, "VKeyCode": -1
    }
    if not hotkey_str or not hotkey_str.strip():
        return [placeholder, placeholder, placeholder, placeholder]

    parts = [p.strip().upper() for p in hotkey_str.split('+')]

    key_ctrl = 'CTRL' in parts or 'CONTROL' in parts
    key_shift = 'SHIFT' in parts
    key_alt = 'ALT' in parts or 'OPTION' in parts
    key_cmd = 'CMD' in parts or 'COMMAND' in parts or 'WIN' in parts or 'WINDOWS' in parts

    key_modifiers = 0
    if key_shift: key_modifiers |= 1
    if key_ctrl: key_modifiers |= 2
    if key_alt: key_modifiers |= 4
    if key_cmd: key_modifiers |= 8

    main_key = None
    for part in parts:
        if part not in ('CTRL', 'CONTROL', 'SHIFT', 'ALT', 'OPTION', 'CMD', 'COMMAND', 'WIN', 'WINDOWS'):
            main_key = part
            break
    if not main_key:
        main_key = 'A'

    # Numpad keys need Qt::KeypadModifier (0x4000 = 16384)
    if main_key.startswith('NUM'):
        key_modifiers |= 16384

    vkey_code = VK_CODES.get(main_key, 65)
    qt_key_code = QT_KEY_CODES.get(main_key, vkey_code)

    hotkey_obj = {
        "KeyCmd": key_cmd, "KeyCtrl": key_ctrl, "KeyModifiers": key_modifiers,
        "KeyOption": key_alt, "KeyShift": key_shift,
        "NativeCode": vkey_code, "QTKeyCode": qt_key_code, "VKeyCode": vkey_code
    }
    return [hotkey_obj, placeholder, placeholder, placeholder]


# ---- Action classes ----

class Action:
    """Base Stream Deck action (V3 format)"""

    def __init__(self, name: str, action_uuid: str, title: str = "",
                 settings: Optional[Dict] = None, plugin: Optional[Dict] = None):
        self.action_id = generate_uuid_v4()
        self.name = name
        self.action_uuid = action_uuid
        self.title = title
        self.settings = settings or {}
        self.plugin = plugin

    def _build_state(self) -> Dict:
        state = {}
        if self.title:
            state["Title"] = self.title
        return state

    def to_dict(self) -> Dict:
        result = {
            "ActionID": self.action_id,
            "LinkedTitle": True,
            "Name": self.name,
        }
        if self.plugin:
            result["Plugin"] = self.plugin
        result["Resources"] = None
        result["Settings"] = self.settings
        result["State"] = 0
        result["States"] = [self._build_state()]
        result["UUID"] = self.action_uuid
        return result


class HotkeyAction(Action):
    """Hotkey action with V3 font formatting support"""

    def __init__(self, title: str = "", hotkey: str = "", split_label: bool = False,
                 text_color: str = "#FFFFFF", text_alignment: str = "middle",
                 font_family: str = "", font_size: int = 12, font_style: str = "",
                 font_underline: bool = False, show_title: bool = True):
        processed_title = process_label_for_display(title, split_label)
        settings = {"Coalesce": True, "Hotkeys": parse_hotkey(hotkey)}
        super().__init__(
            name="Hotkey",
            action_uuid="com.elgato.streamdeck.system.hotkey",
            title=processed_title,
            settings=settings,
            plugin=PLUGIN_HOTKEY
        )
        self.text_color = text_color
        self.text_alignment = text_alignment
        self.font_family = font_family
        self.font_size = font_size
        self.font_style = font_style
        self.font_underline = font_underline
        self.show_title = show_title

    def _has_formatting(self) -> bool:
        return (self.font_family != "" or self.font_size != 12 or
                self.font_style != "" or self.font_underline or
                self.text_color.lower() != "#ffffff" or
                self.text_alignment != "bottom" or not self.show_title)

    def _build_state(self) -> Dict:
        state = {}
        if self.title:
            state["Title"] = self.title
        if self._has_formatting():
            state["FontFamily"] = self.font_family
            state["FontSize"] = self.font_size
            state["FontStyle"] = self.font_style
            state["FontUnderline"] = self.font_underline
            state["OutlineThickness"] = 2
            state["ShowTitle"] = self.show_title
            state["TitleAlignment"] = self.text_alignment
            state["TitleColor"] = self.text_color
        return state


class NextPageAction(Action):
    def __init__(self):
        super().__init__(
            name="Next Page",
            action_uuid="com.elgato.streamdeck.page.next",
            plugin=PLUGIN_PAGE_NEXT
        )


class PreviousPageAction(Action):
    def __init__(self):
        super().__init__(
            name="Previous Page",
            action_uuid="com.elgato.streamdeck.page.previous",
            plugin=PLUGIN_PAGE_PREV
        )



# ---- Profile & StreamDeckProfile ----

class Profile:
    def __init__(self, name: str, actions: List[List[Optional[Action]]] = None):
        self.name = name
        self.uuid = generate_uuid_v4()
        self.actions = actions or []

    def get_manifest(self) -> Dict:
        actions_dict = {}
        for row_idx, row in enumerate(self.actions):
            for col_idx, action in enumerate(row):
                if action is not None:
                    actions_dict[coord_key(row_idx, col_idx)] = action.to_dict()
        return {
            "Controllers": [
                {
                    "Actions": actions_dict if actions_dict else None,
                    "Type": "Keypad"
                }
            ],
            "Icon": "",
            "Name": ""
        }


class StreamDeckProfile:
    """V3 Stream Deck profile generator"""

    def __init__(self, main_profile: Profile, additional_profiles: List[Profile] = None,
                 device: str = "xl", profile_name: str = "Profile",
                 page_uuids: List[str] = None):
        self.profile_uuid = generate_uuid_v4()  # independent UUID for .sdProfile folder
        self.main_profile = main_profile
        self.additional_profiles = additional_profiles or []
        self.device = device
        self.profile_name = profile_name
        self.page_uuids = page_uuids

    def _get_model(self) -> str:
        preset = DEVICE_PRESETS.get(self.device, DEVICE_PRESETS["generic"])
        return preset["model"]

    def generate_package_json(self) -> Dict:
        os_ver = platform.version()
        return {
            "AppVersion": "7.3.1.22604",
            "DeviceModel": self._get_model(),
            "DeviceSettings": None,
            "FormatVersion": 1,
            "OSType": "Windows",
            "OSVersion": os_ver,
            "RequiredPlugins": ["com.elgato.streamdeck.system.hotkey"]
        }

    def generate_top_level_manifest(self) -> Dict:
        if self.page_uuids:
            default_page = self.page_uuids[0]
            # Default page must NOT be in the Pages array — only additional pages
            extra_pages = self.page_uuids[1:]
        else:
            default_page = self.main_profile.uuid
            extra_pages = []

        return {
            "Device": {"Model": self._get_model(), "UUID": ""},
            "Name": self.profile_name,
            "Pages": {
                "Current": "00000000-0000-0000-0000-000000000000",
                "Default": default_page,
                "Pages": extra_pages
            },
            "Version": "3.0"
        }

    def save(self, output_path: str):
        """Save profile as V3 .streamDeckProfile (ZIP)."""
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # V3 structure: package.json at root
            zf.writestr("package.json", json.dumps(self.generate_package_json(), indent=2))

            # Profile root: Profiles/UUID.sdProfile/ (independent UUID, uppercase)
            root_dir = f"Profiles/{self.profile_uuid.upper()}.sdProfile"

            # Top-level manifest
            zf.writestr(
                f"{root_dir}/manifest.json",
                json.dumps(self.generate_top_level_manifest(), indent=2)
            )

            # All sub-profiles use uppercase UUID as folder name
            all_profiles = [self.main_profile] + self.additional_profiles
            for profile in all_profiles:
                folder_id = profile.uuid.upper()
                profile_dir = f"{root_dir}/Profiles/{folder_id}"

                manifest = profile.get_manifest()
                zf.writestr(
                    f"{profile_dir}/manifest.json",
                    json.dumps(manifest, indent=2)
                )

        logger.info("Profile saved (V3): %s", output_path)


# ---- Export helpers ----

def _make_hotkey(item, text_alignment, font_settings):
    """Create a HotkeyAction from an item dict and global font settings."""
    return HotkeyAction(
        title=item.get("label", ""),
        hotkey=item.get("keystroke", ""),
        split_label=item.get("split_label", False),
        text_color=item.get("text_color", "#FFFFFF"),
        text_alignment=text_alignment,
        **font_settings
    )


def _export_with_pages(items, out_path, profile_name, preset, device,
                       max_pages, text_alignment, font_settings):
    cols = preset["cols"]
    rows_per_page = preset["rows"]
    total_slots = cols * rows_per_page

    # Navigation: reserve bottom-left for Prev, bottom-right for Next
    # First page: no Prev, has Next → capacity = total_slots - 1
    # Middle pages: Prev + Next → capacity = total_slots - 2
    # Last page: Prev, no Next → capacity = total_slots - 1
    # Single page: no nav → capacity = total_slots
    if len(items) <= total_slots:
        total_pages = 1
    else:
        first_cap = total_slots - 1
        mid_cap = total_slots - 2
        last_cap = total_slots - 1
        remaining = len(items) - first_cap
        if remaining <= last_cap:
            total_pages = 2
        else:
            remaining -= last_cap
            total_pages = 2 + max(0, (remaining + mid_cap - 1) // mid_cap)

    total_pages = min(total_pages, max_pages)

    page_profiles = []
    page_uuids = []
    item_offset = 0

    for page_num in range(total_pages):
        page_uuid = generate_uuid_v4()
        page_uuids.append(page_uuid)

        has_prev = total_pages > 1 and page_num > 0
        has_next = total_pages > 1 and page_num < total_pages - 1
        nav_count = (1 if has_prev else 0) + (1 if has_next else 0)
        page_capacity = total_slots - nav_count

        page_items = items[item_offset:item_offset + page_capacity]
        item_offset += len(page_items)

        actions_grid = []
        item_idx = 0
        for row_idx in range(rows_per_page):
            actions_row = []
            for col_idx in range(cols):
                if (col_idx, row_idx) == (0, rows_per_page - 1) and has_prev:
                    actions_row.append(PreviousPageAction())
                elif (col_idx, row_idx) == (cols - 1, rows_per_page - 1) and has_next:
                    actions_row.append(NextPageAction())
                elif item_idx < len(page_items):
                    actions_row.append(_make_hotkey(page_items[item_idx], text_alignment, font_settings))
                    item_idx += 1
                else:
                    actions_row.append(None)
            actions_grid.append(actions_row)

        page_profile = Profile(name=f"{profile_name} - Page {page_num + 1}", actions=actions_grid)
        page_profile.uuid = page_uuid
        page_profiles.append(page_profile)

    # Default page must be empty — content pages go in Pages array.
    # Stream Deck shows Pages array as pages 1, 2, 3...
    empty_default = Profile(name=profile_name, actions=[])
    all_page_uuids = [empty_default.uuid] + page_uuids

    sd_profile = StreamDeckProfile(
        main_profile=empty_default,
        additional_profiles=page_profiles,
        device=device,
        profile_name=profile_name,
        page_uuids=all_page_uuids
    )
    sd_profile.save(out_path)


def _export_single_page(items, out_path, profile_name, preset, device,
                         text_alignment, font_settings):
    cols = preset["cols"]
    rows_per_page = preset["rows"]

    actions_grid = []
    item_idx = 0
    for row_idx in range(rows_per_page):
        actions_row = []
        for col_idx in range(cols):
            if item_idx < len(items):
                actions_row.append(_make_hotkey(items[item_idx], text_alignment, font_settings))
                item_idx += 1
            else:
                actions_row.append(None)
        actions_grid.append(actions_row)

    main_profile = Profile(name=profile_name, actions=actions_grid)
    sd_profile = StreamDeckProfile(main_profile, device=device, profile_name=profile_name)
    sd_profile.save(out_path)


def export_profile(
    rows: List[Dict],
    out_path: str,
    profile_name: str,
    device: str = "xl",
    max_pages: int = 1,
    text_alignment: str = "middle",
    font_family: str = "",
    font_size: int = 12,
    font_style: str = "",
    font_underline: bool = False,
    show_title: bool = True,
):
    """Export profile in V3 format with font settings."""
    preset = DEVICE_PRESETS.get(device, DEVICE_PRESETS["generic"])

    items = [r for r in rows if r.get("include", True)]
    items.sort(key=lambda x: int(x.get("order", 1e9)))

    font_settings = {
        "font_family": font_family,
        "font_size": font_size,
        "font_style": font_style,
        "font_underline": font_underline,
        "show_title": show_title,
    }

    _export_with_pages(items, out_path, profile_name, preset, device,
                       max_pages, text_alignment, font_settings)
