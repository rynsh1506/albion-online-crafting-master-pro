import json
import os
import platform

def get_db_path():
    if platform.system() == "Windows":
        base_dir = os.path.join(os.environ.get('APPDATA'), "AlbionCraftingMaster")
    else:
        base_dir = os.path.join(os.path.expanduser("~"), ".config", "AlbionCraftingMaster")

    if not os.path.exists(base_dir):
        os.makedirs(base_dir) 
    return os.path.join(base_dir, "albion_truth_data.json")

DATA_FILE = get_db_path()

def save_to_json(data):
    with open(DATA_FILE, "w") as f: 
        json.dump(data, f, indent=4)

def load_from_json():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f: 
            return json.load(f)
    return {}