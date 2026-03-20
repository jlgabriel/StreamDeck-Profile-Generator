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
    "SPACE":"SPACE","TAB":"TAB","ENTER":"ENTER","ESC":"ESC","ESCAPE":"ESC",
    "BACKSPACE":"BACKSPACE","DELETE":"DELETE","INSERT":"INSERT",
    "HOME":"HOME","END":"END","PAGEUP":"PAGEUP","PAGEDOWN":"PAGEDOWN",
    "UP":"UP","DOWN":"DOWN","LEFT":"LEFT","RIGHT":"RIGHT",
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
    return None

def _mods_from_xplane(modifier: str) -> list[str]:
    if not modifier or modifier.upper() == "<NONE>":
        return []
    return [m.strip().upper() for m in modifier.split("+") if m.strip()]

def _split_command(command: str):
    """sim/flight_controls/flaps_up -> ('Flight Controls', 'Flaps Up')"""
    s = command.replace("sim/", "")
    parts = [p for p in s.split("/") if p]
    if not parts:
        return "Sim", command
    cat = parts[0].replace("_", " ").title()
    tail = " ".join(p.replace("_", " ").title() for p in parts[1:])
    return cat, (f"{cat} - {tail}" if tail else cat)

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
        # search for 'sim/...' token
        try:
            sim_idx = next(i for i, t in enumerate(toks) if t.startswith("sim/"))
        except StopIteration:
            continue  # not a keyboard binding

        command = toks[sim_idx]
        others = toks[:sim_idx] + toks[sim_idx+1:]

        key = None
        modifier = "<NONE>"

        if len(others) == 2:
            a, b = others
            if _is_modifier(a) and not _is_modifier(b):
                modifier, key = a, b
            elif _is_modifier(b) and not _is_modifier(a):
                key, modifier = a, b
            else:
                # heuristic: the one that looks like main key stays as key
                key = b if _canon_key(b) else _canon_key(a) and a or b
        elif len(others) == 1:
            if _is_modifier(others[0]):
                modifier = others[0]
            else:
                key = others[0]
        else:
            # classic fallback: key mod sim/... or key sim/...
            m = re.match(r'^\s*(\S+)\s+(\S+)\s+(sim/.*)$', s)
            if m:
                key, modifier, command = m.groups()
            else:
                m2 = re.match(r'^\s*(\S+)\s+(sim/.*)$', s)
                if m2:
                    key, command = m2.groups()
                    modifier = "<NONE>"

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
            "icon": "",
        })

    return rows
