# app/keys.py
import re
import sys

class KeystrokeError(ValueError):
    pass

# Canonical order by OS
ORDER_WIN = ("WIN", "CTRL", "ALT", "SHIFT")
ORDER_MAC = ("CMD", "CTRL", "ALT", "SHIFT")

# Modifier synonyms
MOD_SYNONYMS = {
    "CTRL": {"CTRL", "CONTROL", "CTL"},
    "ALT": {"ALT", "OPTION", "OPT"},
    "SHIFT": {"SHIFT", "SHFT"},
    "CMD": {"CMD", "COMMAND"},
    "WIN": {"WIN", "WINDOWS", "META", "SUPER"},
}

# Allowed main keys (besides A..Z, 0..9)
SPECIAL_KEYS = {
    # function
    *[f"F{i}" for i in range(1, 25)],
    # navigation
    "UP","DOWN","LEFT","RIGHT","HOME","END","PAGEUP","PAGEDOWN",
    # editing
    "ESC","TAB","ENTER","SPACE","BACKSPACE","DELETE","INSERT",
    # numpad
    "NUM0","NUM1","NUM2","NUM3","NUM4","NUM5","NUM6","NUM7","NUM8","NUM9",
    "NUMPLUS","NUMMINUS","NUMMULTIPLY","NUMDIVIDE","NUMDECIMAL","NUMENTER",
    # punctuation
    "PLUS","MINUS","EQUALS","COMMA","PERIOD","SLASH","SEMICOLON",
    "QUOTE","BACKQUOTE","LBRACKET","RBRACKET","BACKSLASH",
    # OEM
    "OEM102",
}

# Main key synonyms (punctuation and variants)
KEY_SYNONYMS = {
    "+": "PLUS",
    "-": "MINUS",
    "=": "EQUALS",
    ",": "COMMA",
    ".": "PERIOD",
    "/": "SLASH",
    ";": "SEMICOLON",
    "'": "QUOTE",
    "`": "BACKQUOTE",
    "[": "LBRACKET",
    "]": "RBRACKET",
    "\\": "BACKSLASH",
    "RETURN": "ENTER",
    "DEL": "DELETE",
    "INS": "INSERT",
    "PGUP": "PAGEUP",
    "PGDN": "PAGEDOWN",
    "ESCAPE": "ESC",
    "SPACEBAR": "SPACE",
    "KP_0": "NUM0", "KP_1": "NUM1", "KP_2": "NUM2", "KP_3": "NUM3", "KP_4": "NUM4",
    "KP_5": "NUM5", "KP_6": "NUM6", "KP_7": "NUM7", "KP_8": "NUM8", "KP_9": "NUM9",
    "KP_PLUS": "NUMPLUS", "KP_MINUS": "NUMMINUS",
    "KP_MULTIPLY": "NUMMULTIPLY", "KP_DIVIDE": "NUMDIVIDE",
    "KP_DECIMAL": "NUMDECIMAL", "KP_ENTER": "NUMENTER",
}

def _os_order(os_mode: str):
    return ORDER_MAC if os_mode == "mac" else ORDER_WIN

def _canonical_modifier(tok: str):
    up = tok.upper()
    for canon, alts in MOD_SYNONYMS.items():
        if up in alts:
            return canon
    return None

def _canonical_key(tok: str):
    up = tok.upper()
    # letters and digits
    if re.fullmatch(r"[A-Z]", up):
        return up
    if re.fullmatch(r"\d", up):
        return up
    # function
    if re.fullmatch(r"F([1-9]|1\d|2[0-4])", up):
        return up
    # synonyms
    up = KEY_SYNONYMS.get(up, up)
    if up in SPECIAL_KEYS:
        return up
    return None

def normalize_keystroke(text: str, os_mode: str | None = None) -> str:
    """
    Normalizes a shortcut. Raises KeystrokeError if invalid.
    Final format: MOD+MOD+KEY (e.g.: CTRL+ALT+F11)
    """
    if not text or not text.strip():
        raise KeystrokeError("Empty keystroke.")

    # Default OS based on platform
    if os_mode is None:
        os_mode = "mac" if sys.platform == "darwin" else "win"

    raw = text.strip()
    # Separator: '+' (we allow spaces around). Commas indicate sequences → not supported.
    if "," in raw:
        raise KeystrokeError("Comma sequences not supported (e.g.: CTRL+K, CTRL+C). Use a single shortcut.")

    # Remove redundant spaces and normalize multiple separators '++'
    parts = [p for p in re.split(r"\s*\+\s*", raw) if p]
    if not parts:
        raise KeystrokeError("Invalid format.")

    modifiers = []
    main_key = None

    for p in parts:
        m = _canonical_modifier(p)
        if m:
            if m not in modifiers:
                modifiers.append(m)
            continue
        k = _canonical_key(p)
        if k:
            if main_key is not None:
                raise KeystrokeError("Only one main key is supported (no sequences).")
            main_key = k
            continue
        # not a mod nor known key
        raise KeystrokeError(f"Unknown token: '{p}'.")

    if not main_key:
        raise KeystrokeError("Missing main key (e.g.: ... + F12).")

    # Re-order modifiers according to OS
    order = _os_order(os_mode)
    modifiers.sort(key=lambda x: order.index(x) if x in order else 99)

    # On mac, if WIN comes it can be mapped to CMD if there's no CMD (optional)
    if os_mode == "mac" and "WIN" in modifiers and "CMD" not in modifiers:
        modifiers = ["CMD" if m == "WIN" else m for m in modifiers]

    return "+".join([*modifiers, main_key])
