# --- VERSION & IDENTITY ---
# MANAGER_VERSION = "v5.1.4 (Integrity & Polish)"

# config.py
import configparser
import os
import constants

def get_manager_config():
    """Reads manager_config.ini and returns the parser object."""
    config = configparser.ConfigParser(interpolation=None)
    if os.path.exists(constants.MANAGER_CONFIG_FILE):
        config.read(constants.MANAGER_CONFIG_FILE)
    return config

def save_manager_config(config_obj):
    """Writes the parser object to disk."""
    try:
        with open(constants.MANAGER_CONFIG_FILE, 'w') as f:
            config_obj.write(f)
    except Exception as e:
        print(f"Error saving config: {e}")

def get_game_ini_path(server_path):
    if not server_path: return None
    return os.path.join(server_path, 'Vein', 'Saved', 'Config', 'WindowsServer', 'Game.ini')

def get_engine_ini_path(server_path):
    if not server_path: return None
    return os.path.join(server_path, 'Vein', 'Saved', 'Config', 'WindowsServer', 'Engine.ini')

def get_existing_section_name(config_obj, target_section):
    """Finds a section case-insensitively."""
    for section in config_obj.sections():
        if section.lower() == target_section.lower():
            return section
    return target_section

def load_game_ini(server_path):
    """Safely loads Game.ini considering Case Sensitivity."""
    path = get_game_ini_path(server_path)
    config = configparser.ConfigParser(strict=False)
    config.optionxform = str # Preserve Case
    if path and os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                config.read_file(f)
        except:
            try: config.read(path)
            except: pass
    return config

def save_game_ini(server_path, config_obj):
    """Writes Game.ini."""
    path = get_game_ini_path(server_path)
    if not path: return
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            config_obj.write(f, space_around_delimiters=False)
    except Exception as e:
        print(f"Failed to write Game.ini: {e}")

# --- THE SAFE CONFIG ENGINE (MODDING SUITE) ---

def get_modifiable_sections(server_path):
    """
    Scans Game.ini and returns a list of section names that are NOT protected.
    Used for the Modding UI Dropdown.
    """
    path = get_game_ini_path(server_path)
    if not path or not os.path.exists(path): return []
    
    found_sections = []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('[') and line.endswith(']'):
                    section = line[1:-1]
                    # THE SHIELD: Check if section is protected
                    if section.lower() not in constants.PROTECTED_SECTIONS:
                        found_sections.append(section)
    except: pass
    return sorted(list(set(found_sections)))

def read_mod_config_section(server_path, section_name):
    """
    Reads a specific section raw, preserving array structure (+Key).
    Returns a list of tuples: [(Key, Value), (Key, Value)]
    """
    path = get_game_ini_path(server_path)
    if not path or not os.path.exists(path): return []
    
    data = []
    in_section = False
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('[') and line.endswith(']'):
                    current_sec = line[1:-1]
                    if current_sec.lower() == section_name.lower():
                        in_section = True
                    else:
                        in_section = False
                    continue
                
                if in_section and '=' in line:
                    parts = line.split('=', 1)
                    key = parts[0].strip()
                    val = parts[1].strip()
                    data.append((key, val))
    except: pass
    return data

def write_mod_config_section(server_path, section_name, data_list):
    """
    Surgically replaces a section in Game.ini without touching other parts.
    data_list: List of (Key, Value) tuples.
    """
    path = get_game_ini_path(server_path)
    if not path: return False
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except: lines = []
    
    new_lines = []
    in_target_section = False
    section_found = False
    
    # Rebuild file, skipping the old target section
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('[') and stripped.endswith(']'):
            current_sec = stripped[1:-1]
            if current_sec.lower() == section_name.lower():
                in_target_section = True
                section_found = True
                # Trigger replacement here
                new_lines.append(f"[{section_name}]\n")
                for k, v in data_list:
                    # Handle UE5 Array syntax if key starts with +
                    if k.startswith("+"):
                        new_lines.append(f"{k}={v}\n")
                    else:
                        new_lines.append(f"{k}={v}\n")
            else:
                in_target_section = False
                new_lines.append(line)
            continue
        
        if not in_target_section:
            new_lines.append(line)
            
    # If section didn't exist, append it
    if not section_found:
        new_lines.append(f"\n[{section_name}]\n")
        for k, v in data_list:
             new_lines.append(f"{k}={v}\n")
             
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        return True
    except: return False

# --- ENGINE.INI LOGIC ---

def update_engine_ini_cvar(server_path, updates_dict):
    """Parses Engine.ini specifically for [ConsoleVariables]."""
    path = get_engine_ini_path(server_path)
    if not path: return

    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    lines = []
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

    new_lines = []
    in_cvar_section = False
    section_found = False
    keys_written = set()

    for line in lines:
        stripped = line.strip()
        
        if stripped.startswith('[') and stripped.endswith(']'):
            if stripped.lower() == '[consolevariables]':
                in_cvar_section = True
                section_found = True
                new_lines.append(line)
                continue
            else:
                if in_cvar_section:
                    # End of section, dump remaining new keys
                    for k, v in updates_dict.items():
                        if k not in keys_written:
                            new_lines.append(f"{k}={v}\n")
                            keys_written.add(k)
                in_cvar_section = False
                new_lines.append(line)
                continue

        if in_cvar_section:
            matched_key = None
            for k in updates_dict:
                # Basic check, might need strict split if keys share prefixes
                if stripped.lower().startswith(k.lower() + "="):
                    matched_key = k
                    break
            
            if matched_key:
                new_lines.append(f"{matched_key}={updates_dict[matched_key]}\n")
                keys_written.add(matched_key)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    if not section_found:
        new_lines.append("\n[ConsoleVariables]\n")
        in_cvar_section = True

    if in_cvar_section:
        for k, v in updates_dict.items():
            if k not in keys_written:
                new_lines.append(f"{k}={v}\n")

    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
    except Exception as e:
        print(f"Failed to write Engine.ini: {e}")

def load_engine_ini_raw(filepath, keys_to_find):
    if not filepath or not os.path.exists(filepath): return {}
    found_values = {}
    in_cvar = False
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                s = line.strip()
                if s.lower() == '[consolevariables]': 
                    in_cvar = True
                    continue
                if s.startswith('[') and s.lower() != '[consolevariables]': 
                    in_cvar = False
                    continue
                
                if in_cvar and '=' in s:
                    parts = s.split('=', 1)
                    key = parts[0].strip()
                    val = parts[1].strip()
                    for target in keys_to_find:
                        if key.lower() == target.lower():
                            found_values[target] = val
    except: pass
    return found_values

def save_game_ini_array(server_path, section_name, key_name, values_list):
    path = get_game_ini_path(server_path)
    if not path or not os.path.exists(path): return

    try:
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except: lines = []

    new_lines = []
    in_target_section = False
    section_found = False
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('[') and stripped.endswith(']'):
            if stripped[1:-1].lower() == section_name.lower():
                in_target_section = True
                section_found = True
            else:
                in_target_section = False
            new_lines.append(line)
            continue
        
        if in_target_section:
            if stripped.lower().startswith(key_name.lower() + "=") or stripped.lower().startswith("+" + key_name.lower() + "="):
                continue 
        
        new_lines.append(line)

    if not section_found:
        new_lines.append(f"\n[{section_name}]\n")
        in_target_section = True 
        insert_index = len(new_lines)
    else:
        insert_index = len(new_lines)
        for i, line in enumerate(new_lines):
            if line.strip().lower() == f"[{section_name}]".lower():
                insert_index = i + 1
                break
    
    generated_lines = []
    for idx, val in enumerate(values_list):
        val = val.strip()
        if not val: continue
        if idx == 0: generated_lines.append(f"{key_name}={val}\n")
        else: generated_lines.append(f"+{key_name}={val}\n")
            
    for l in reversed(generated_lines):
        new_lines.insert(insert_index, l)

    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
    except Exception as e:
        print(f"Failed to write Array to Game.ini: {e}")