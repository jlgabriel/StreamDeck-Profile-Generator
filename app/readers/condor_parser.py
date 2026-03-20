"""
Condor 3 Parser for Stream Deck Profile Generator
Parses controls.ini files and extracts keyboard bindings
"""

import re
import configparser
from pathlib import Path
from typing import List, Dict, Optional

# Windows Virtual Key Codes to standard key names
# Based on Windows VK codes used in Condor controls.ini
VK_CODE_MAP = {
    # Letters (A-Z: 65-90 but Condor uses 30-56)
    30: "A", 48: "B", 46: "C", 32: "D", 18: "E", 33: "F", 34: "G", 35: "H",
    23: "I", 36: "J", 37: "K", 38: "L", 50: "M", 49: "N", 24: "O", 25: "P",
    16: "Q", 19: "R", 31: "S", 20: "T", 22: "U", 47: "V", 17: "W", 45: "X",
    21: "Y", 44: "Z",
    
    # Numbers (top row)
    11: "1", 12: "2", 13: "3", 14: "4", 15: "5", 16: "6", 17: "7", 18: "8", 19: "9", 10: "0",
    
    # Function keys
    59: "F1", 60: "F2", 61: "F3", 62: "F4", 63: "F5", 64: "F6", 65: "F7", 66: "F8",
    67: "F9", 68: "F10", 87: "F11", 88: "F12",
    
    # Arrow keys
    200: "UP", 208: "DOWN", 203: "LEFT", 205: "RIGHT",
    
    # Special keys
    1: "ESC", 15: "TAB", 28: "ENTER", 57: "SPACE", 14: "BACKSPACE",
    211: "DELETE", 210: "INSERT", 199: "HOME", 207: "END", 201: "PAGEUP", 209: "PAGEDOWN",
    
    # Numpad
    82: "NUM0", 79: "NUM1", 80: "NUM2", 81: "NUM3", 75: "NUM4", 76: "NUM5", 
    77: "NUM6", 71: "NUM7", 72: "NUM8", 73: "NUM9",
    78: "NUMPLUS", 74: "NUMMINUS", 55: "NUMMULTIPLY", 181: "NUMDIVIDE", 83: "NUMDECIMAL",
    
    # Punctuation and symbols
    26: "LBRACKET", 27: "RBRACKET", 39: "SEMICOLON", 40: "QUOTE", 41: "BACKQUOTE",
    51: "COMMA", 52: "PERIOD", 53: "SLASH", 43: "BACKSLASH", 12: "MINUS", 13: "EQUALS",
    
    # Modifier keys
    42: "SHIFT", 54: "SHIFT",  # Left/Right Shift
    29: "CTRL", 157: "CTRL",   # Left/Right Ctrl
    56: "ALT", 184: "ALT",     # Left/Right Alt
}

# Command ID mappings for Condor 3
CONDOR3_COMMANDS = {
    0: "Bank", 1: "Pitch", 2: "Rudder", 3: "Airbrakes", 4: "Trimmer", 5: "Flaps", 6: "Throttle",
    1000: "Bank mouse", 1001: "Pitch mouse", 2000: "View POV", 2001: "LX stick joystick",
    3000: "Bank left", 3001: "Bank right", 3002: "Pitch up", 3003: "Pitch down",
    3004: "Rudder left", 3005: "Rudder right", 3006: "Rudder center",
    3007: "Trimmer up", 3008: "Trimmer down", 3009: "Trimmer center",
    3010: "Airbrakes in", 3011: "Airbrakes out", 3012: "Flaps up", 3013: "Flaps down",
    3014: "Gear", 3015: "Wheel brake", 3016: "Release", 3017: "Water", 3018: "Smoke",
    3019: "Extract motor", 3020: "Start motor", 3021: "Throttle up", 3022: "Throttle down",
    3023: "Bug wipers", 3024: "Check time", 3025: "Swap controls",
    3026: "Vario volume up", 3027: "Vario volume down", 3028: "Altimeter up", 3029: "Altimeter down",
    3030: "G Meter reset", 3031: "Radio frequency up", 3032: "Radio frequency down", 3033: "Radio Push To Talk",
    3034: "LX stick left / flight comp zoom out", 3035: "LX stick right / flight comp zoom in",
    3036: "LX stick up / flight comp up", 3037: "LX stick down / flight comp down",
    3038: "LX stick OK", 3039: "LX stick cancel", 3040: "LX stick / flight comp mode left",
    3041: "LX stick / flight comp mode right", 3042: "Flight comp next TP", 3043: "Flight comp prior TP",
    3044: "Flight comp advance TP", 3045: "Move AAT TP toggle", 3046: "MC up", 3047: "MC down",
    3048: "Lift / cruise toggle", 3049: "View pan left", 3050: "View pan right",
    3051: "View pan up", 3052: "View pan down", 3053: "View snap left", 3054: "View snap right",
    3055: "View center", 3056: "VR center", 3057: "Cockpit camera", 3058: "External camera",
    3059: "Chase camera", 3060: "Tower camera", 3061: "Towplane camera", 3062: "Fly-by camera",
    3063: "Padlock camera", 3064: "Net player camera", 3065: "Replay camera",
    3066: "Zoom in", 3067: "Zoom out", 3068: "Panel zoom", 3069: "Game menu",
    3070: "Start flight", 3071: "Pause", 3072: "Miracle", 3073: "Auto rudder toggle",
    3074: "Send message", 3075: "Show classification", 3076: "Show icons", 3077: "HUD toggle",
    3078: "Extend chat log", 3079: "Screenshot", 3080: "Lift helpers", 3081: "Task helpers"
}


def extract_category_from_command(command_name: str) -> str:
    """Extract category from command name"""
    command_lower = command_name.lower()
    
    # Flight controls
    if any(word in command_lower for word in ['bank', 'pitch', 'rudder', 'trimmer', 'aileron', 'elevator']):
        return "Flight Controls"
    
    # Engine & propulsion
    if any(word in command_lower for word in ['throttle', 'motor', 'engine']):
        return "Engine & Propulsion"
    
    # Landing & surfaces
    if any(word in command_lower for word in ['gear', 'flaps', 'airbrakes', 'brake', 'release']):
        return "Landing & Surfaces"
    
    # Views & camera
    if any(word in command_lower for word in ['view', 'camera', 'cockpit', 'external', 'chase', 'tower', 'padlock', 'replay']):
        return "Views & Camera"
    
    # Navigation & instruments
    if any(word in command_lower for word in ['pda', 'altimeter', 'vario', 'radio', 'mc ', 'flight comp', 'lx stick']):
        return "Navigation & Instruments"
    
    # Environment & effects
    if any(word in command_lower for word in ['water', 'smoke', 'miracle', 'lift', 'cruise']):
        return "Environment & Effects"
    
    # Interface & system
    if any(word in command_lower for word in ['menu', 'pause', 'screenshot', 'message', 'hud', 'classification', 'icons', 'chat']):
        return "Interface & System"
    
    # Helpers & assistance
    if any(word in command_lower for word in ['helper', 'auto', 'check']):
        return "Helpers & Assistance"
    
    return "General"

def parse_condor_controls_ini(file_path: str) -> List[Dict]:
    """
    Parse Condor controls.ini file and extract keyboard bindings.
    Returns list of binding dictionaries for Stream Deck Profile Generator.
    """
    if not Path(file_path).exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Read file with proper encoding
    try:
        config = configparser.ConfigParser()
        config.read(file_path, encoding='utf-8')
    except UnicodeDecodeError:
        try:
            config = configparser.ConfigParser()
            config.read(file_path, encoding='latin1')
        except Exception as e:
            raise Exception(f"Could not read file with any encoding: {e}")
    
    # Look for keyboard device section (the GUID that contains keyboard mappings)
    # In your example: {6F1D2B61-D5A0-11CF-BFC7-444553540000}
    keyboard_section = None
    
    for section_name in config.sections():
        section = config[section_name]
        # Keyboard sections typically have many entries starting from 3000+
        keyboard_commands = [int(key) for key in section.keys() if key.isdigit() and int(key) >= 3000]
        if len(keyboard_commands) > 10:  # Heuristic: keyboard section has many commands
            keyboard_section = section
            break
    
    if not keyboard_section:
        raise Exception("No keyboard bindings section found in controls.ini")
    
    command_map = CONDOR3_COMMANDS
    
    rows = []
    processed_count = 0
    invalid_keys = []
    
    for key, value in keyboard_section.items():
        if not key.isdigit():
            continue
            
        command_id = int(key)
        vk_code = int(value) if value.isdigit() else None
        
        # Skip if command is not recognized
        if command_id not in command_map:
            continue
            
        # Skip if no valid key code
        if vk_code is None or vk_code == 0:
            continue
            
        command_name = command_map[command_id]
        
        # Convert VK code to standard key name
        if vk_code in VK_CODE_MAP:
            keystroke = VK_CODE_MAP[vk_code]
        else:
            # Log unrecognized key codes for debugging
            invalid_keys.append((command_name, vk_code))
            print(f"Warning: Unknown VK code {vk_code} for command '{command_name}'")
            continue
        
        # Create binding entry
        category = extract_category_from_command(command_name)
        
        row = {
            "include": True,
            "order": len(rows) + 1,
            "original": f"condor3_{command_id}",
            "label": command_name,
            "keystroke": keystroke,
            "category": category,
            "text_color": "#FFFFFF",
            "split_label": False
        }
        
        rows.append(row)
        processed_count += 1
    
    print(f"Successfully processed {processed_count} keyboard bindings")
    if invalid_keys:
        print(f"Found {len(invalid_keys)} unrecognized key codes:")
        for cmd, vk in invalid_keys[:5]:  # Show first 5
            print(f"  {cmd}: VK {vk}")
        if len(invalid_keys) > 5:
            print(f"  ... and {len(invalid_keys) - 5} more")
    
    if not rows:
        raise Exception("No valid keyboard bindings found")
    
    return rows

# Test function
if __name__ == "__main__":
    try:
        # Test with the provided controls.ini
        bindings = parse_condor_controls_ini("controls.ini")
        print(f"\nSuccessfully parsed {len(bindings)} keyboard bindings:")
        
        # Group by category for display
        by_category = {}
        for binding in bindings:
            cat = binding['category']
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(binding)
        
        # Display by category
        for category, items in by_category.items():
            print(f"\n{category}:")
            for item in items[:3]:  # Show first 3 per category
                print(f"  {item['label']:<30} → {item['keystroke']:<15}")
            if len(items) > 3:
                print(f"  ... and {len(items) - 3} more")
                
    except Exception as e:
        print(f"Error: {e}")
