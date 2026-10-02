import os

def read_env(env_path=".env"):
    config = {}
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if "=" in line:
                        key, val = line.split("=", 1)
                        config[key.strip()] = val.strip()
    return config

def write_env(env_path=".env", new_config=None):
    if new_config is None:
        new_config = {}
        
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
    # Update existing keys
    updated_keys = set()
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            if "=" in line:
                key, _ = line.split("=", 1)
                key = key.strip()
                if key in new_config:
                    lines[i] = f"{key}={new_config[key]}\n"
                    updated_keys.add(key)
                    
    # Append new keys
    for key, val in new_config.items():
        if key not in updated_keys:
            lines.append(f"{key}={val}\n")
            
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
