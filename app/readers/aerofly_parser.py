"""
Aerofly FS 4 Parser for Stream Deck Profile Generator
Parses gc-map.mcf files and extracts keyboard bindings
Based on real user configuration file
"""

import re
from pathlib import Path
from typing import List, Dict

# Keyboard device ID from Aerofly FS 4
KEYBOARD_DEVICE_ID = "9960793825445316444"

# Input mapping from Aerofly format to standard keystroke format
AEROFLY_INPUT_MAP = {
    # Letters (already standard)
    **{chr(i): chr(i) for i in range(ord('A'), ord('Z') + 1)},
    
    # Numbers (already standard)
    **{str(i): str(i) for i in range(10)},
    
    # Special keys
    "SPACE": "SPACE",
    "TAB": "TAB", 
    "RETURN": "ENTER",
    "ESCAPE": "ESC",
    "BACKSPACE": "BACKSPACE",
    "DELETE": "DELETE",
    "INSERT": "INSERT",
    "HOME": "HOME",
    "END": "END",
    "PAGEUP": "PAGEUP",
    "PAGEDOWN": "PAGEDOWN",
    "LEFT": "LEFT",
    "RIGHT": "RIGHT", 
    "UP": "UP",
    "DOWN": "DOWN",
    
    # Punctuation - based on actual bindings in the file
    "APOSTROPHE": "QUOTE",
    "PERIOD": "PERIOD",
    "COMMA": "COMMA", 
    "MINUS": "MINUS",
    "PLUS": "PLUS",
    "BACKSLASH": "BACKSLASH",
    
    # Function keys
    **{f"F{i}": f"F{i}" for i in range(1, 13)}
}

def convert_aerofly_input_to_keystroke(input_id: str) -> str:
    """
    Convert Aerofly InputID format to normalized keystroke.
    Examples:
        "SHIFT-APOSTROPHE" -> "SHIFT+QUOTE"
        "PERIOD" -> "PERIOD"
        "G" -> "G"
        "SHIFT-F" -> "SHIFT+F"
    """
    if not input_id or not input_id.strip():
        return ""
    
    input_clean = input_id.strip()
    
    # Handle modifier combinations (SHIFT-X format)
    if "-" in input_clean:
        parts = input_clean.split("-")
        modifiers = []
        main_key = None
        
        for part in parts:
            part = part.strip().upper()
            
            # Check for modifiers
            if part in ["SHIFT", "CTRL", "CONTROL", "ALT", "WIN", "CMD", "COMMAND"]:
                if part not in modifiers:
                    modifiers.append(part)
            else:
                # This is the main key
                main_key = part
        
        # Convert main key using mapping
        if main_key and main_key in AEROFLY_INPUT_MAP:
            main_key = AEROFLY_INPUT_MAP[main_key]
        
        # Build keystroke
        if main_key:
            if modifiers:
                return "+".join(modifiers + [main_key])
            else:
                return main_key
    
    # Handle simple keys (no modifiers)
    key_upper = input_clean.upper()
    if key_upper in AEROFLY_INPUT_MAP:
        return AEROFLY_INPUT_MAP[key_upper]
    
    # Return as-is if not in mapping (fallback)
    return key_upper

def format_function_name(function_id: str) -> str:
    """
    Convert Aerofly FunctionID to readable label.
    Examples:
        "GliderEngine" -> "Glider Engine"
        "PanelLighting" -> "Panel Lighting"
        "ViewExternal" -> "View External"
        "ThrustReverse" -> "Thrust Reverse"
    """
    if not function_id:
        return ""
    
    # Split camelCase words
    result = re.sub(r'([a-z])([A-Z])', r'\1 \2', function_id)
    
    # Handle specific abbreviations
    result = result.replace("HUD", "HUD")
    result = result.replace("VR", "VR") 
    
    return result.title()

def extract_category_from_function(function_id: str) -> str:
    """
    Extract category from function ID based on patterns.
    """
    function_lower = function_id.lower()
    
    # Flight controls & Autopilot
    if any(word in function_lower for word in ['aileron', 'elevator', 'rudder', 'trim', 'collective', 'cyclic', 'autopilot', 'copilot']):
        return "Flight Controls"
    
    # Engine & Propulsion  
    if any(word in function_lower for word in ['engine', 'throttle', 'mixture', 'propeller', 'thrust']):
        return "Engine & Propulsion"
    
    # Landing gear & surfaces
    if any(word in function_lower for word in ['gear', 'flaps', 'airbrake', 'brake']):
        return "Landing & Surfaces"
    
    # Views & Camera
    if any(word in function_lower for word in ['view', 'pan', 'look', 'zoom', 'cockpit', 'external', 'tower', 'world', 'favorite', 'pilot']):
        return "Views & Camera"
    
    # Lighting
    if any(word in function_lower for word in ['light', 'lighting']):
        return "Lighting"
    
    # Interface & Navigation
    if any(word in function_lower for word in ['command', 'select', 'execute', 'back', 'pushback']):
        return "Interface"
    
    # Glider specific
    if any(word in function_lower for word in ['glider', 'hook']):
        return "Glider"
    
    # Environment & Settings
    if any(word in function_lower for word in ['time', 'visibility', 'weather', 'sound', 'landmarks']):
        return "Environment"
    
    # Information & HUD
    if any(word in function_lower for word in ['hud', 'information', 'map', 'overlay', 'flight']):
        return "Information"
    
    # Simulation control
    if any(word in function_lower for word in ['pause', 'playback', 'screenshot', 'record', 'toggle']):
        return "Simulation"
    
    return "General"

def parse_aerofly_mcf(file_path: str) -> List[Dict]:
    """
    Parse Aerofly FS 4 gc-map.mcf file and extract keyboard bindings.
    Returns list of binding dictionaries for Stream Deck Profile Generator.
    """
    if not Path(file_path).exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
    except Exception as e:
        raise Exception(f"Error reading file: {e}")
    
    # Extract channel mappings using regex
    channel_pattern = re.compile(
        r'<\[tmchannelmap\].*?'
        r'<\[string8u\]\[FunctionID\]\[(.*?)\]>.*?'
        r'<\[string8u\]\[InputID\]\[(.*?)\]>.*?'
        r'<\[uint64\]\[DeviceUniqueID\]\[(\d+)\]>.*?'
        r'<\[string8u\]\[DeviceIDString\]\[(.*?)\]>.*?'
        r'<\[bool\]\[IsDigital\]\[(.*?)\]>.*?'
        r'<\[bool\]\[IsValue\]\[(.*?)\]>.*?'
        r'<\[float64\]\[Sign\]\[(.*?)\]>.*?'
        r'<\[float64\]\[Direction\]\[(.*?)\]>',
        re.DOTALL | re.MULTILINE
    )
    
    channel_matches = channel_pattern.findall(content)
    
    if not channel_matches:
        raise Exception("No channel mappings found. Verify this is a valid Aerofly FS 4 gc-map.mcf file.")
    
    
    rows = []
    processed_combinations = set()  # Avoid duplicates
    keyboard_bindings_found = 0
    
    for match in channel_matches:
        function_id, input_id, device_id, device_name, is_digital, is_value, sign, direction = match
        
        # Filter: Only keyboard bindings
        if device_id != KEYBOARD_DEVICE_ID:
            continue
        if device_name.lower() != "keyboard":
            continue
        if is_digital.lower() != "true":
            continue  # Skip analog inputs
            
        keyboard_bindings_found += 1
        
        try:
            # Convert input to keystroke
            keystroke = convert_aerofly_input_to_keystroke(input_id)
            if not keystroke:
                print(f"  Warning: Could not convert input '{input_id}' for '{function_id}'")
                continue
            
            # Create unique combination key
            combination_key = f"{function_id}_{keystroke}"
            if combination_key in processed_combinations:
                continue  # Skip duplicates
            processed_combinations.add(combination_key)
            
            # Generate readable label and category
            label = format_function_name(function_id)
            category = extract_category_from_function(function_id)
            
            # Handle directional bindings (+ and -)
            sign_value = float(sign)
            if sign_value < 0:
                label += " -"
            elif sign_value > 0:
                # Check if there's also a negative binding for same function
                has_negative = any(
                    m[0] == function_id and float(m[6]) < 0 
                    for m in channel_matches 
                    if m[2] == KEYBOARD_DEVICE_ID
                )
                if has_negative:
                    label += " +"
            
            # Create row dictionary
            row = {
                "include": True,
                "order": len(rows) + 1,
                "original": function_id,
                "label": label,
                "keystroke": keystroke,
                "category": category,
                "text_color": "#FFFFFF",
                "split_label": True
            }
            
            rows.append(row)
            
        except Exception as e:
            print(f"  Warning: Error processing {function_id} -> {input_id}: {e}")
            continue
    
    print(f"Aerofly FS4: parsed {len(rows)} keyboard bindings ({keyboard_bindings_found} total, {keyboard_bindings_found - len(rows)} skipped)")
    
    if not rows:
        raise Exception("No valid keyboard bindings found. This may be a hardware-only configuration.")
    
    return rows

# Test function
if __name__ == "__main__":
    try:
        bindings = parse_aerofly_mcf("gc-map.mcf")
        print(f"\nSuccessfully parsed {len(bindings)} keyboard bindings:")
        
        # Group by category for better display
        by_category = {}
        for binding in bindings:
            cat = binding['category']
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(binding)
        
        # Display by category
        for category, items in by_category.items():
            print(f"\n{category}:")
            for item in items:
                print(f"  {item['label']:<25} → {item['keystroke']:<15}")
                
    except Exception as e:
        print(f"Error: {e}")