import os
import sys
from PIL import Image
import customtkinter as ctk

def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# ==========================================
# SETUP DIREKTORI CACHE (.config / AppData)
# ==========================================
if sys.platform == "win32":
    APP_DATA_DIR = os.path.join(os.getenv("APPDATA"), "CraftingMasterPro")
else:
    APP_DATA_DIR = os.path.join(os.path.expanduser("~"), ".config", "CraftingMasterPro")

os.makedirs(APP_DATA_DIR, exist_ok=True)

CACHE_FILE = os.path.join(APP_DATA_DIR, "albion_universal_cache.json")
IMG_DIR = os.path.join(APP_DATA_DIR, "item_icons")
os.makedirs(IMG_DIR, exist_ok=True)

# ==========================================
# FUNGSI CACHE GAMBAR ALBION (LOKAL ONLY)
# ==========================================
def get_item_image(item_id, size=40):
    file_path = os.path.join(IMG_DIR, f"{item_id}.png")
    if os.path.exists(file_path):
        try:
            img = Image.open(file_path)
            return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
        except: pass
    return None