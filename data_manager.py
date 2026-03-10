import json
import os

from config_utils import APP_DATA_DIR

DATA_FILE = os.path.join(APP_DATA_DIR, "albion_truth_data.json")

def save_to_json(data):
    with open(DATA_FILE, "w") as f: 
        json.dump(data, f, indent=4)

def load_from_json():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f: 
            return json.load(f)
    return {}