"""
X-Plane PRF (Preferences) file parser for keybindings.
Parses .prf files and extracts hotkey assignments.
"""

from pathlib import Path
import re

# -------- helpers --------

# X-Plane modifier token? (<NONE>, SHIFT, CTRL, ALT, combined with +)
_MOD_RE = re.compile(r'^(<NONE>|(SHIFT|CTRL|ALT)(\+(SHIFT|CTRL|ALT))*)$', re.I)
def _is_modifier(tok: str) -> bool:
    return bool(_MOD_RE.match(tok.strip()))

# symbol map -> canonical name
_PUNCT = {
    "+":"PLUS", "-":"MINUS", "=":"EQUALS", ",":"COMMA", ".":"PERIOD", "/":"SLASH",
    ";":"SEMICOLON", "'":"QUOTE", "`":"BACKQUOTE", "[":"LBRACKET", "]":"RBRACKET", "\\":"BACKSLASH"
}
_SPECIAL = {
    "SPACE":"SPACE","TAB":"TAB","ENTER":"ENTER","RETURN":"ENTER",
    "ESC":"ESC","ESCAPE":"ESC",
    "BACKSPACE":"BACKSPACE","DELETE":"DELETE","INSERT":"INSERT",
    "HOME":"HOME","END":"END","PAGEUP":"PAGEUP","PAGEDOWN":"PAGEDOWN",
    "UP":"UP","DOWN":"DOWN","LEFT":"LEFT","RIGHT":"RIGHT",
}

# X-Plane Numpad tokens → internal names (matching keys.py canonical names)
_NUMPAD = {
    "NUMPAD-0":"NUM0","NUMPAD-1":"NUM1","NUMPAD-2":"NUM2","NUMPAD-3":"NUM3",
    "NUMPAD-4":"NUM4","NUMPAD-5":"NUM5","NUMPAD-6":"NUM6","NUMPAD-7":"NUM7",
    "NUMPAD-8":"NUM8","NUMPAD-9":"NUM9",
    "NUMPAD-+":"NUMPLUS","NUMPAD--":"NUMMINUS",
    "NUMPAD-*":"NUMMULTIPLY","NUMPAD-/":"NUMDIVIDE",
    "NUMPAD-.":"NUMDECIMAL",
}

def _canon_key(token: str) -> str | None:
    t = token.strip()
    if len(t) == 1 and t.isalpha():  # letter
        return t.upper()
    if len(t) == 1 and t.isdigit():  # digit
        return t
    u = t.upper()
    if u.startswith("F") and u[1:].isdigit():
        return u  # F1..F24
    if u in _SPECIAL:
        return _SPECIAL[u]
    if t in _PUNCT:
        return _PUNCT[t]
    if u in _NUMPAD:
        return _NUMPAD[u]
    return None

def _mods_from_xplane(modifier: str) -> list[str]:
    if not modifier or modifier.upper() == "<NONE>":
        return []
    return [m.strip().upper() for m in modifier.split("+") if m.strip()]

def _split_command(command: str):
    """
    Split a command path into (category, label).
    Built-in:  sim/flight_controls/flaps_up   -> ('Flight Controls', 'Flaps Up')
    Plugin:    SRS/X-Camera/Toggle_Pan_Speed  -> ('X-Camera', 'Toggle Pan Speed')
    Plugin 2:  FlyWithLua/WindVane/toggle_wind -> ('WindVane', 'Toggle Wind')
    Short:     walkaround/move_back           -> ('Walkaround', 'Move Back')
    """
    parts = [p for p in command.split("/") if p]
    if not parts:
        return "Unknown", command

    if parts[0].lower() == "sim":
        # built-in: skip "sim", first remaining part = category, rest = label
        parts = parts[1:]
        if not parts:
            return "Sim", command
        cat = parts[0].replace("_", " ").title()
        tail = " ".join(p.replace("_", " ").title() for p in parts[1:])
        return cat, (tail if tail else cat)

    # plugin command: skip vendor/plugin name (first part), use second as category
    if len(parts) >= 3:
        # e.g. SRS/X-Camera/Toggle -> cat="X-Camera", label="Toggle"
        cat = parts[1].replace("_", " ").title()
        tail = " ".join(p.replace("_", " ").title() for p in parts[2:])
        return cat, (tail if tail else cat)
    elif len(parts) == 2:
        # e.g. walkaround/move_back -> cat="Walkaround", label="Move Back"
        cat = parts[0].replace("_", " ").title()
        label = parts[1].replace("_", " ").title()
        return cat, label
    else:
        cat = parts[0].replace("_", " ").title()
        return cat, cat

# -------- main parser --------

def read_prf_file(file_path: str):
    """
    Returns [(key, modifier, command)].
    Supports tabs/spaces, and the 'sim/...' token in any position.
    """
    triples = []
    lines = Path(file_path).read_text(encoding="utf-8", errors="ignore").splitlines()

    for line in lines:
        s = line.strip()
        if not s or s.startswith("#"):
            continue

        toks = re.split(r"\s+", s)  # any whitespace
        # search for first command token (any path with '/')
        # skip version line ("1005 Version") and similar non-binding lines
        try:
            cmd_idx = next(i for i, t in enumerate(toks)
                          if "/" in t and not _is_modifier(t))
        except StopIteration:
            continue  # not a keyboard binding

        command = toks[cmd_idx]
        # tokens before command are key + modifier; tokens after are description (ignored)
        before = toks[:cmd_idx]

        key = None
        modifier = "<NONE>"

        if len(before) == 2:
            a, b = before
            if _is_modifier(a) and not _is_modifier(b):
                modifier, key = a, b
            elif _is_modifier(b) and not _is_modifier(a):
                key, modifier = a, b
            else:
                key = b if _canon_key(b) else _canon_key(a) and a or b
        elif len(before) == 1:
            if _is_modifier(before[0]):
                modifier = before[0]
            else:
                key = before[0]

        if not key:
            continue

        triples.append((key, modifier, command))

    return triples

def parse_xplane_prf(file_path: str) -> list[dict]:
    """
    Converts to rows for the app:
    {include, order, original, label, keystroke, category, bg_color, icon}
    """
    triples = read_prf_file(file_path)
    rows: list[dict] = []

    for i, (key_tok, mod_tok, command) in enumerate(triples, start=1):
        base = _canon_key(key_tok)
        mods = _mods_from_xplane(mod_tok)
        # if we couldn't canonicalize the key (rare), skip
        if base is None:
            continue

        keystroke = "+".join([*mods, base]) if mods else base
        category, label = _split_command(command)

        rows.append({
            "include": True,
            "order": i,
            "original": command,
            "label": label,          # clean: "General - Backward"
            "keystroke": keystroke,  # canonical: "SHIFT+COMMA", "CTRL+MINUS", etc.
            "category": category,    # "General", "Instruments", ...
            "text_color": "#FFFFFF",
            "split_label": True,
        })

    skipped = len(triples) - len(rows)
    print(f"X-Plane 12: parsed {len(rows)} keyboard bindings ({len(triples)} total, {skipped} skipped)")
    return rows
