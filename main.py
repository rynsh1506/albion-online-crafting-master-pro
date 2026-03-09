import customtkinter as ctk
import tkinter as tk
from PIL import Image 
import sys
import os
import requests
import json
import threading
import traceback
import math
from concurrent.futures import ThreadPoolExecutor, as_completed

from logic_engine import calculate_refining_logic
from salvage_engine import calculate_salvage_flip # IMPORT ENGINE BARU
from data_manager import save_to_json, load_from_json

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

# ==========================================
# CLASS: ALBION MARKET SEARCH DIALOG (MODERN UI)
# ==========================================
class ItemSearchDialog(ctk.CTkToplevel):
    def __init__(self, parent, universal_db, on_select_callback):
        super().__init__(parent)
        self.title("Albion Marketplace")
        self.geometry("900x700") 
        self.resizable(False, False)
        
        self.universal_db = universal_db
        self.on_select_callback = on_select_callback
        
        self.ITEMS_PER_PAGE = 8 
        self.current_page = 1
        self.filtered_data = list(self.universal_db.keys())
        
        self.transient(parent)
        self.wait_visibility()
        self.grab_set()

        self.setup_ui()
        self.apply_filters()

        self.bind("<MouseWheel>", self._on_mousewheel)
        self.bind("<Button-4>", self._on_mousewheel)
        self.bind("<Button-5>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        try:
            if hasattr(event, 'delta') and event.delta != 0:
                self.list_bg._parent_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            elif event.num == 4:
                self.list_bg._parent_canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                self.list_bg._parent_canvas.yview_scroll(1, "units")
        except Exception: pass

    def setup_ui(self):
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        ctk.CTkLabel(header_frame, text="Albion Marketplace", font=ctk.CTkFont(size=24, weight="bold"), text_color=("#1d4ed8", "#60a5fa")).pack(side="left")
        
        control_frame = ctk.CTkFrame(self, fg_color=("#e4e4e4", "#1a1c1e"), corner_radius=10)
        control_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        inner_f = ctk.CTkFrame(control_frame, fg_color="transparent")
        inner_f.pack(fill="x", padx=15, pady=12)

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.reset_page_and_filter())
        
        self.search_entry = ctk.CTkEntry(inner_f, textvariable=self.search_var, placeholder_text="Cari Nama Bahan (Kayu, Leather, dll)...", height=36, width=400, border_width=0, corner_radius=6)
        self.search_entry.pack(side="left", padx=(0, 15))

        self.tier_var = ctk.StringVar(value="Tier")
        ctk.CTkComboBox(inner_f, values=["Tier", "T2", "T3", "T4", "T5", "T6", "T7", "T8"], variable=self.tier_var, command=self.reset_page_and_filter, width=100, height=36, button_color="#3b82f6", border_width=0, corner_radius=6).pack(side="left", padx=5)

        self.ench_var = ctk.StringVar(value="Enchant")
        ctk.CTkComboBox(inner_f, values=["Enchant", "Base (0)", "Level 1", "Level 2", "Level 3", "Level 4"], variable=self.ench_var, command=self.reset_page_and_filter, width=130, height=36, button_color="#3b82f6", border_width=0, corner_radius=6).pack(side="left", padx=5)
        
        ctk.CTkButton(inner_f, text="✖ Reset", width=80, height=36, fg_color="#e74c3c", hover_color="#c0392b", font=ctk.CTkFont(weight="bold"), corner_radius=6, command=self.reset_all_filters).pack(side="right")

        self.list_bg = ctk.CTkScrollableFrame(self, fg_color=("#f4f5f7", "#121416"), corner_radius=10)
        self.list_bg.pack(fill="both", expand=True, padx=20, pady=5)
        
        page_frame = ctk.CTkFrame(self, fg_color="transparent")
        page_frame.pack(fill="x", padx=20, pady=15)

        self.btn_prev = ctk.CTkButton(page_frame, text="◀ Prev", command=self.prev_page, width=100, height=35, corner_radius=6, fg_color=("#e4e4e4", "#2d3135"), hover_color=("#d4d4d4", "#3e4348"), text_color=("black", "white"), font=ctk.CTkFont(weight="bold"))
        self.btn_prev.pack(side="left")

        self.lbl_page = ctk.CTkLabel(page_frame, text="Page 1", font=ctk.CTkFont(weight="bold", size=13))
        self.lbl_page.pack(side="left", expand=True)

        self.btn_next = ctk.CTkButton(page_frame, text="Next ▶", command=self.next_page, width=100, height=35, corner_radius=6, fg_color=("#e4e4e4", "#2d3135"), hover_color=("#d4d4d4", "#3e4348"), text_color=("black", "white"), font=ctk.CTkFont(weight="bold"))
        self.btn_next.pack(side="right")
        
        self.search_entry.focus()

    def reset_all_filters(self):
        self.search_var.set(""); self.tier_var.set("Tier"); self.ench_var.set("Enchant")
        self.reset_page_and_filter()

    def reset_page_and_filter(self, *args):
        self.current_page = 1
        self.apply_filters()

    def apply_filters(self):
        query = self.search_var.get().lower()
        tier_f = self.tier_var.get()
        ench_f = self.ench_var.get()

        temp_list = []
        for name, data in self.universal_db.items():
            item_id = data["id"]
            
            if query and query not in name.lower(): continue
            if tier_f != "Tier" and str(data.get("tier")) != tier_f.replace("T", ""): continue
            
            if ench_f != "Enchant":
                e_num = ench_f.replace("Level ", "").replace("Base (0)", "0")
                if e_num == "0":
                    if "@" in item_id or "_LEVEL" in item_id: continue
                else:
                    if f"@{e_num}" not in item_id and f"_LEVEL{e_num}" not in item_id: 
                        continue

            temp_list.append(name)

        self.filtered_data = sorted(temp_list)
        self.render_page()

    def render_page(self):
        for widget in self.list_bg.winfo_children(): widget.destroy()
        
        total_items = len(self.filtered_data)
        total_pages = max(1, (total_items + self.ITEMS_PER_PAGE - 1) // self.ITEMS_PER_PAGE)
        if self.current_page > total_pages: self.current_page = total_pages
        
        start_idx = (self.current_page - 1) * self.ITEMS_PER_PAGE
        end_idx = start_idx + self.ITEMS_PER_PAGE
        page_items = self.filtered_data[start_idx:end_idx]

        if not page_items:
            ctk.CTkLabel(self.list_bg, text="Item tidak ditemukan. Coba reset filter.", text_color="#8e949a").pack(pady=50)
        else:
            for item in page_items:
                item_data = self.universal_db[item]
                item_id = item_data["id"]
                
                card = ctk.CTkFrame(self.list_bg, fg_color=("#ffffff", "#1e2124"), corner_radius=8, border_width=1, border_color=("#e4e4e4", "#2d3135"))
                card.pack(fill="x", pady=5, padx=5)
                
                img = get_item_image(item_id, size=45)
                lbl_img = ctk.CTkLabel(card, text="" if img else "IMG", image=img, width=50, height=50)
                lbl_img.pack(side="left", padx=12, pady=8)
                
                info_frame = ctk.CTkFrame(card, fg_color="transparent")
                info_frame.pack(side="left", fill="y", pady=10)
                
                ctk.CTkLabel(info_frame, text=item, font=ctk.CTkFont(size=14, weight="bold"), anchor="w").pack(fill="x")
                meta_text = f"Tier: {item_data.get('tier', '?')}  |  Output: {item_data.get('out_qty', 1)}"
                ctk.CTkLabel(info_frame, text=meta_text, font=ctk.CTkFont(size=12), text_color="#8e949a", anchor="w").pack(fill="x", pady=(2,0))
                
                btn = ctk.CTkButton(card, text="Pilih", width=80, height=35, corner_radius=6, fg_color="#3b82f6", font=ctk.CTkFont(weight="bold"),
                                    command=lambda i=item: self.select_item(i))
                btn.pack(side="right", padx=15)

        self.lbl_page.configure(text=f"Page {self.current_page} of {total_pages}")
        self.btn_prev.configure(state="normal" if self.current_page > 1 else "disabled")
        self.btn_next.configure(state="normal" if self.current_page < total_pages else "disabled")

    def prev_page(self):
        if self.current_page > 1: self.current_page -= 1; self.render_page()

    def next_page(self):
        total_pages = (len(self.filtered_data) + self.ITEMS_PER_PAGE - 1) // self.ITEMS_PER_PAGE
        if self.current_page < total_pages: self.current_page += 1; self.render_page()

    def select_item(self, item_name):
        self.on_select_callback(item_name)
        self.destroy()

# ==========================================
# CLASS UTAMA APLIKASI
# ==========================================
class AlbionApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.saved_data = load_from_json()
        
        self.is_dark = self.saved_data.get("dark_mode", True)
        ctk.set_appearance_mode("dark" if self.is_dark else "light")
        ctk.set_default_color_theme("blue")

        self.title("Crafting Master Pro - Universal")
        self.minsize(1280, 850) 
        
        try:
            if sys.platform == "win32":
                self.iconpath = get_resource_path("logo.ico")
                self.after(200, lambda: self.iconbitmap(self.iconpath))
            else:
                app_icon = tk.PhotoImage(file=get_resource_path("logo1.png"))
                self.iconphoto(True, app_icon)
        except: pass
        
        self.update()
        try:
            if sys.platform == "win32": self.state('zoomed')
            else: self.attributes('-zoomed', True)
        except Exception:
            self.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")

        saved_method = self.saved_data.get("sell_method", "Direct")
        if saved_method.islower(): saved_method = saved_method.capitalize()
        self.sell_method = tk.StringVar(value=saved_method)
        
        self.material_entries = []
        self.history = self.saved_data.get("history", []) 
        
        self.setup_ui()
        self.load_saved_materials()
        for res in self.history:
            self.render_expandable_card(res)
            
        self.universal_db = {}
        
        has_images = any(f.endswith('.png') for f in os.listdir(IMG_DIR)) if os.path.exists(IMG_DIR) else False
        
        if os.path.exists(CACHE_FILE) and has_images:
            self.load_local_db()
        else:
            self.show_startup_overlay()
            threading.Thread(target=self.run_first_time_setup, daemon=True).start()

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def show_startup_overlay(self):
        self.overlay = ctk.CTkFrame(self, fg_color=("#f4f5f7", "#121416"))
        self.overlay.place(relwidth=1, relheight=1, relx=0, rely=0)
        
        box = ctk.CTkFrame(self.overlay, corner_radius=15, fg_color=("#ffffff", "#1e2124"))
        box.place(relx=0.5, rely=0.5, anchor="center")
        
        try:
            logo_img = Image.open(get_resource_path("logo1.png")) if not self.is_dark else Image.open(get_resource_path("logo2.png"))
            img = ctk.CTkImage(light_image=logo_img, dark_image=logo_img, size=(60, 65))
            ctk.CTkLabel(box, text="", image=img).pack(pady=(20,10))
        except: pass
        
        ctk.CTkLabel(box, text="Client Setup - Mendownload Data", font=ctk.CTkFont(size=20, weight="bold")).pack(padx=40, pady=(0, 10))
        
        self.setup_progress = ctk.CTkProgressBar(box, width=300, progress_color="#3b82f6")
        self.setup_progress.pack(pady=10)
        self.setup_progress.set(0)
        
        self.setup_status = ctk.CTkLabel(box, text="Menghubungkan ke server Albion...", text_color="#8e949a")
        self.setup_status.pack(pady=(0, 20))

    def update_setup_ui(self, text, progress_val):
        self.setup_status.configure(text=text)
        self.setup_progress.set(progress_val)

    def run_first_time_setup(self):
        def report_error(msg):
            self.update_setup_ui(f"ERROR: {msg}\nCoba restart aplikasi.", 0)
            
        try:
            self.after(0, self.update_setup_ui, "Mendownload Database Resep (30MB+)...", 0.1)
            db = self.download_json_data()
            
            if not db:
                self.after(0, report_error, "Gagal mendownload JSON dari API (Kemungkinan Data Korup).")
                return

            self.after(0, self.update_setup_ui, "Mengekstrak list aset gambar...", 0.3)
            all_ids = set()
            for name, data in db.items():
                all_ids.add(data["id"])
                for mat in data.get("recipe", []):
                    all_ids.add(mat["id"])
            
            ids_list = list(all_ids)
            total_img = len(ids_list)
            
            downloaded = 0
            self.after(0, self.update_setup_ui, f"Mendownload {total_img} Gambar (0/{total_img})...", 0.3)
            
            def dl_img(i_id):
                path = os.path.join(IMG_DIR, f"{i_id}.png")
                if not os.path.exists(path):
                    try:
                        url = f"https://render.albiononline.com/v1/item/{i_id}.png?size=40"
                        resp = requests.get(url, timeout=5)
                        if resp.status_code == 200:
                            with open(path, "wb") as f: f.write(resp.content)
                    except: pass
            
            with ThreadPoolExecutor(max_workers=20) as executor:
                futures = [executor.submit(dl_img, i) for i in ids_list]
                for future in as_completed(futures):
                    downloaded += 1
                    prog = 0.3 + (0.7 * (downloaded / total_img))
                    if downloaded % 50 == 0 or downloaded == total_img: 
                        self.after(0, self.update_setup_ui, f"Mendownload Gambar ({downloaded}/{total_img})...", prog)

            self.after(0, self.update_setup_ui, "Setup Selesai! Membuka aplikasi...", 1.0)
            self.after(1000, self.finish_setup, db)
            
        except Exception as e:
            self.after(0, report_error, str(e))

    def finish_setup(self, db):
        self.universal_db = db
        self.overlay.destroy()
        
    def load_local_db(self):
        try:
            with open(CACHE_FILE, "r") as f:
                self.universal_db = json.load(f)
        except Exception:
            self.universal_db = {}

    def download_json_data(self):
        url_names = "https://raw.githubusercontent.com/broderickhyman/ao-bin-dumps/master/formatted/items.json"
        url_items = "https://raw.githubusercontent.com/broderickhyman/ao-bin-dumps/master/items.json"
        try:
            resp1 = requests.get(url_names, timeout=30)
            if resp1.status_code != 200: raise Exception(f"API Error {resp1.status_code}")
            resp1_data = resp1.json()
            id_to_name = {}
            if isinstance(resp1_data, list):
                for i in resp1_data:
                    if isinstance(i, dict):
                        uid = i.get("UniqueName"); loc = i.get("LocalizedNames")
                        if uid and isinstance(loc, dict):
                            en_name = loc.get("EN-US")
                            if en_name: id_to_name[uid] = en_name

            resp2 = requests.get(url_items, timeout=30)
            if resp2.status_code != 200: raise Exception(f"API Error {resp2.status_code}")
            raw_items_data = resp2.json()
            
            id_to_iv = {}
            def extract_iv(obj):
                if isinstance(obj, dict):
                    uid = obj.get("@uniquename"); iv = obj.get("@itemvalue")
                    if uid and iv is not None:
                        try: id_to_iv[uid] = float(iv)
                        except: pass
                    for k, v in obj.items():
                        if isinstance(v, (dict, list)): extract_iv(v)
                elif isinstance(obj, list):
                    for item in obj:
                        if isinstance(item, (dict, list)): extract_iv(item)
            extract_iv(raw_items_data)

            raw_items_list = []
            def find_items(obj):
                if isinstance(obj, dict):
                    uid = obj.get("@uniquename")
                    if uid:
                        is_res = any(k in uid for k in ["_WOOD", "_ROCK", "_ORE", "_FIBER", "_HIDE", "_PLANKS", "_METALBAR", "_LEATHER", "_CLOTH", "_STONEBLOCK"])
                        if "craftingrequirements" in obj or "_LEVEL" in uid or is_res:
                            raw_items_list.append(obj)
                        
                        if "enchantments" in obj:
                            enchs = obj["enchantments"].get("enchantment", [])
                            if isinstance(enchs, dict): enchs = [enchs]
                            for e in enchs:
                                if isinstance(e, dict) and "craftingrequirements" in e:
                                    lvl = e.get("@enchantmentlevel")
                                    if lvl:
                                        ench_item = e.copy()
                                        ench_item["@uniquename"] = f"{uid}@{lvl}"
                                        if "@tier" in obj:
                                            ench_item["@tier"] = obj["@tier"]
                                        raw_items_list.append(ench_item)

                    for k, v in obj.items():
                        if isinstance(v, (dict, list)): find_items(v)
                elif isinstance(obj, list):
                    for item in obj:
                        if isinstance(item, (dict, list)): find_items(item)
            find_items(raw_items_data)
            
            db = {}
            for item in raw_items_list:
                if not isinstance(item, dict): continue
                uid = item.get("@uniquename")
                if not uid: continue
                
                base_uid = uid.split("@")[0].split("_LEVEL")[0] if ("@" in uid or "_LEVEL" in uid) else uid
                base_name = id_to_name.get(uid) or id_to_name.get(base_uid)
                
                is_raw_resource = any(k in uid for k in ["_WOOD", "_ROCK", "_ORE", "_FIBER", "_HIDE", "_PLANKS", "_METALBAR", "_LEATHER", "_CLOTH", "_STONEBLOCK"])
                if not base_name and is_raw_resource:
                    base_name = uid
                    
                if not base_name or "Token" in base_name or "Journal" in base_name: continue
                
                try:
                    current_tier = uid.split('_')[0].replace('T', '')
                    if not current_tier.isdigit(): current_tier = "1"
                except: current_tier = "4"
                
                enchant_val = "0"
                if "@" in uid: enchant_val = uid.split("@")[1]
                elif "_LEVEL" in uid: enchant_val = uid.split("_LEVEL")[1]
                
                display_name = f"{base_name} [{current_tier}.{enchant_val}]"
                
                reqs = item.get("craftingrequirements")
                if isinstance(reqs, list) and len(reqs) > 0: req = reqs[0]
                else: req = reqs
                
                mats = []
                dynamic_item_value = 0 
                out_qty_val = 1
                
                if isinstance(req, dict):
                    try: out_qty_val = int(req.get("@amountcrafted", 1))
                    except: out_qty_val = 1
                    
                    craft_res = req.get("craftresource")
                    if craft_res:
                        if not isinstance(craft_res, list): craft_res = [craft_res]
                        for res in craft_res:
                            if not isinstance(res, dict): continue
                            r_uid = res.get("@uniquename")
                            if not r_uid: continue
                            
                            try: r_qty = int(res.get("@count", 1))
                            except: r_qty = 1
                            
                            r_base = r_uid.split("@")[0].split("_LEVEL")[0] if ("@" in r_uid or "_LEVEL" in r_uid) else r_uid
                            r_ench = "0"
                            if "@" in r_uid: r_ench = r_uid.split("@")[1]
                            elif "_LEVEL" in r_uid: r_ench = r_uid.split("_LEVEL")[1]
                            
                            try:
                                r_tier = r_uid.split('_')[0].replace('T', '')
                                if not r_tier.isdigit(): r_tier = current_tier
                            except: r_tier = current_tier

                            r_iv_base = id_to_iv.get(r_base, 0)
                            r_iv = r_iv_base * (2 ** int(r_ench))
                            dynamic_item_value += (r_iv * r_qty)
                            
                            r_raw_name = id_to_name.get(r_uid) or id_to_name.get(r_base) or r_uid
                            r_display_name = f"{r_raw_name} [{r_tier}.{r_ench}]"
                                
                            is_returnable = True
                            if res.get("@maxreturnamount") == "0": is_returnable = False
                            uid_upper = r_uid.upper()
                            if any(keyword in uid_upper for keyword in ["_RUNE", "_SOUL", "_RELIC", "_SHARD", "ARTIFACT_", "_MOUNT_", "FARM_"]):
                                is_returnable = False
                                
                            mats.append({
                                "id": r_uid, "name": r_display_name, "qty": r_qty, "is_returnable": is_returnable
                            })

                if not mats and not is_raw_resource:
                    continue

                try: item_val = float(item.get("@itemvalue", 0))
                except: item_val = 0
                
                if item_val == 0:
                    item_val = dynamic_item_value
                    
                t = 4
                try: t = int(item.get("@tier", current_tier))
                except: pass
                
                if display_name in db and not mats and db[display_name]["recipe"]:
                    continue

                db[display_name] = {"id": uid, "tier": t, "out_qty": out_qty_val, "item_value": item_val, "recipe": mats}
            
            with open(CACHE_FILE, "w") as f: json.dump(db, f)
            return db
        except Exception as e:
            traceback.print_exc()
            return None

    def trigger_manual_update(self):
        self.btn_update_api.configure(text="Mendownload JSON...", state="disabled")
        
        def bg_update():
            db = self.download_json_data()
            if not db: 
                self.after(0, lambda: self.btn_update_api.configure(text="Update API (Gagal)", text_color="#e74c3c"))
                self.after(3000, lambda: self.btn_update_api.configure(text="Update API Data", state="normal", text_color=("black", "white")))
                return
                
            self.universal_db = db
            self.after(0, lambda: self.btn_update_api.configure(text="Mengecek Gambar Baru..."))
            
            all_ids = set()
            for name, data in db.items():
                all_ids.add(data["id"])
                for mat in data.get("recipe", []):
                    all_ids.add(mat["id"])
            
            missing_ids = []
            for i_id in all_ids:
                if not os.path.exists(os.path.join(IMG_DIR, f"{i_id}.png")):
                    missing_ids.append(i_id)
            
            total_missing = len(missing_ids)
            
            if total_missing > 0:
                self.after(0, lambda: self.btn_update_api.configure(text=f"Download {total_missing} Gambar..."))
                
                def dl_img(item_id):
                    url = f"https://render.albiononline.com/v1/item/{item_id}.png?size=40"
                    try:
                        resp = requests.get(url, timeout=10)
                        if resp.status_code == 200:
                            with open(os.path.join(IMG_DIR, f"{item_id}.png"), "wb") as f:
                                f.write(resp.content)
                        elif resp.status_code == 404:
                            with open(os.path.join(IMG_DIR, f"{item_id}.png"), "wb") as f:
                                f.write(b"") 
                    except: pass
                
                downloaded = 0
                with ThreadPoolExecutor(max_workers=10) as executor:
                    futures = [executor.submit(dl_img, i) for i in missing_ids]
                    for future in as_completed(futures):
                        downloaded += 1
                        if downloaded % 5 == 0 or downloaded == total_missing:
                            self.after(0, lambda d=downloaded: self.btn_update_api.configure(text=f"Download ({d}/{total_missing})..."))

            self.after(0, lambda: self.btn_update_api.configure(text="Update Selesai!", text_color="#2ecc71"))
            self.after(3000, lambda: self.btn_update_api.configure(text="Update API Data", state="normal", text_color=("black", "white")))
            
        threading.Thread(target=bg_update, daemon=True).start()

    def on_city_changed(self, choice):
        target_name = self.ent_name.get().strip()
        if not target_name or target_name not in self.universal_db: return
            
        data = self.universal_db[target_name]
        target_id = data["id"]
        recipe_mats = data.get("recipe", [])
        
        items_to_fetch = [target_id]
        for mat in recipe_mats: items_to_fetch.append(mat["id"])
            
        self.ent_sell.delete(0, tk.END)
        self.ent_sell.insert(0, "Fetching...")
        
        for i in range(len(self.material_entries)):
            self.material_entries[i]["price"].delete(0, tk.END)
            self.material_entries[i]["price"].insert(0, "...")
            
        threading.Thread(target=self.fetch_prices_async, args=(items_to_fetch, target_id, recipe_mats), daemon=True).start()

    def on_target_selected(self, selected_name):
        self.ent_name.delete(0, tk.END)
        self.ent_name.insert(0, selected_name)
        
        for widget in self.mats_container.winfo_children():
            widget.destroy()
            
        self.material_entries = []
        self.ent_sell.delete(0, tk.END); self.ent_item_val.delete(0, tk.END); self.ent_out_qty.delete(0, tk.END)
        
        if selected_name not in self.universal_db: return
            
        data = self.universal_db[selected_name]
        target_id = data["id"]
        
        try: out_qty_safe = str(data.get("out_qty", 1))
        except: out_qty_safe = "1"
        self.ent_out_qty.insert(0, out_qty_safe)
        
        try: iv_safe = str(int(float(data.get("item_value", 0) or 0)))
        except: iv_safe = "0"
        self.ent_item_val.insert(0, iv_safe)
        
        recipe_mats = data.get("recipe", [])
        items_to_fetch = [target_id]
        
        for mat in recipe_mats:
            self.add_static_material_row(
                name_val=mat["name"], 
                price_val="...", 
                qty_val=mat["qty"], 
                is_ret=mat.get("is_returnable", True), 
                own_qty_val="0"
            )
            items_to_fetch.append(mat["id"])
            
        self.ent_sell.insert(0, "Fetching...")
        threading.Thread(target=self.fetch_prices_async, args=(items_to_fetch, target_id, recipe_mats), daemon=True).start()
    
    def fetch_prices_async(self, item_ids, target_id, recipe_mats):
        try:
            city = self.market_filter.get()
            clean_ids = [i.strip() for i in item_ids if i]
            
            url = f"https://www.albion-online-data.com/api/v2/stats/prices/{','.join(clean_ids)}.json"
            all_asia = "Singapore,Brecilien,Caerleon,Martlock,Thetford,FortSterling,Lymhurst,Bridgewatch"
            
            if city == "All Asia": url += f"?locations={all_asia}"
            else: url += f"?locations={city.replace(' ', '')},{all_asia}"

            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200: return

            data = resp.json()
            user_prices = {}
            fallback_prices = {}
            
            for row in data:
                i_id = row['item_id']
                p = row.get('sell_price_min', 0)
                loc = row.get('location', '')
                
                if p > 0:
                    if loc.replace(' ', '') == city.replace(' ', ''):
                        if i_id not in user_prices or p < user_prices[i_id]:
                            user_prices[i_id] = p
                    if i_id not in fallback_prices or p < fallback_prices[i_id]:
                        fallback_prices[i_id] = p
            
            final_prices = {}
            for i_id in clean_ids:
                if i_id in user_prices: final_prices[i_id] = user_prices[i_id]
                elif i_id in fallback_prices: final_prices[i_id] = fallback_prices[i_id]
            
            self.after(0, self.update_prices_ui, final_prices, target_id, recipe_mats)
            
        except Exception as e:
            print(f"Gagal tarik harga: {e}")
            self.after(0, self.clear_fetching_text, recipe_mats)
    
    def update_prices_ui(self, prices, target_id, recipe_mats):
        self.ent_sell.delete(0, tk.END)
        self.ent_sell.insert(0, str(prices.get(target_id, 0)))
        
        for i, mat in enumerate(recipe_mats):
            if i < len(self.material_entries):
                self.material_entries[i]["price"].delete(0, tk.END)
                self.material_entries[i]["price"].insert(0, str(prices.get(mat["id"], 0)))
            
    def clear_fetching_text(self, recipe_mats):
        self.ent_sell.delete(0, tk.END)
        for i in range(len(self.material_entries)):
            self.material_entries[i]["price"].delete(0, tk.END)

    def on_closing(self):
        self.save_current_state()
        self.destroy()

    def toggle_theme(self):
        new_mode = "dark" if self.theme_var.get() else "light"
        ctk.set_appearance_mode(new_mode)
        self.save_current_state()

    def _scroll_handler(self, event, canvas_target):
        if canvas_target.yview() == (0.0, 1.0): return 
        if hasattr(event, 'delta') and event.delta != 0: canvas_target.yview_scroll(int(-1*(event.delta/120)), "units")
        elif event.num == 4: canvas_target.yview_scroll(-1, "units")
        elif event.num == 5: canvas_target.yview_scroll(1, "units")

    def bind_global_scroll(self, widget, scroll_func):
        if not isinstance(widget, ctk.CTkSegmentedButton): 
            try:
                widget.bind("<MouseWheel>", scroll_func); widget.bind("<Button-4>", scroll_func); widget.bind("<Button-5>", scroll_func)
            except Exception: pass
        for child in widget.winfo_children(): self.bind_global_scroll(child, scroll_func)

    def _scroll_main(self, event): self._scroll_handler(event, self.scrollable_list._parent_canvas)

    def create_section_label(self, parent, text):
        ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(size=12, weight="bold"), text_color=("#1d4ed8", "#60a5fa")).pack(pady=(12, 2), padx=15, anchor="w")

    def create_field_label(self, parent, text):
        ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(size=10), text_color=("#6c757d", "#8e949a")).pack(anchor="w")

    def create_2col_input(self, parent, label1, key1, def1, label2, key2, def2):
        frame = ctk.CTkFrame(parent, fg_color="transparent"); frame.pack(fill="x", padx=15, pady=(2, 4))
        f_l = ctk.CTkFrame(frame, fg_color="transparent"); f_l.pack(side="left", fill="x", expand=True, padx=(0, 5)); self.create_field_label(f_l, label1)
        ent1 = ctk.CTkEntry(f_l, height=35, corner_radius=6, fg_color=("#e4e4e4", "#2d3135"), border_width=0); ent1.insert(0, self.saved_data.get(key1, def1)); ent1.pack(fill="x")
        f_r = ctk.CTkFrame(frame, fg_color="transparent"); f_r.pack(side="right", fill="x", expand=True, padx=(5, 0)); self.create_field_label(f_r, label2)
        ent2 = ctk.CTkEntry(f_r, height=35, corner_radius=6, fg_color=("#e4e4e4", "#2d3135"), border_width=0); ent2.insert(0, self.saved_data.get(key2, def2)); ent2.pack(fill="x")
        return ent1, ent2

    def auto_calculate_rrr(self, *args):
        try:
            basic = float(self.var_basic.get() or 0); local = float(self.var_local.get() or 0); daily = float(self.var_daily.get() or 0)
            focus = 59.0 if self.focus_toggle_var.get() else 0.0 
            total_bonus = basic + local + daily + focus
            rrr = (total_bonus / (100 + total_bonus)) * 100 if total_bonus > 0 else 0
            self.ent_rrr.configure(state="normal"); self.ent_rrr.delete(0, tk.END); self.ent_rrr.insert(0, f"{rrr:.7f}"); self.ent_rrr.configure(state="readonly")
        except: pass 

    def toggle_focus_mode(self):
        if self.focus_toggle_var.get():
            self.f_focb.pack(side="right", fill="x", expand=True, padx=(5, 0))
            self.frame_focus_inputs.pack(fill="x", padx=15, pady=(2, 4), after=self.frame_focus_toggle)
        else:
            self.f_focb.pack_forget(); self.frame_focus_inputs.pack_forget()
            self.ent_focus_cost.delete(0, tk.END); self.ent_focus_cost.insert(0, "")
        self.auto_calculate_rrr()

    def setup_ui(self):
        self.sidebar_wrapper = ctk.CTkFrame(self, width=420, fg_color=("#f4f5f7", "#1a1c1e"), corner_radius=0)
        self.sidebar_wrapper.pack(side="left", fill="y"); self.sidebar_wrapper.pack_propagate(False)
        
        try:
            logo_black = Image.open(get_resource_path("logo1.png")); logo_white = Image.open(get_resource_path("logo2.png"))
            self.my_logo = ctk.CTkImage(light_image=logo_black, dark_image=logo_white, size=(40, 45))
            self.logo_label = ctk.CTkLabel(self.sidebar_wrapper, text=" CRAFTING PRO", image=self.my_logo, compound="left", font=ctk.CTkFont(size=20, weight="bold"), text_color=("black", "white"))
            self.logo_label.pack(pady=(20, 5), padx=20, anchor="w")
        except:
            self.logo_label = ctk.CTkLabel(self.sidebar_wrapper, text="CRAFTING PRO", font=ctk.CTkFont(size=22, weight="bold"), text_color=("black", "white"))
            self.logo_label.pack(pady=(20, 5), padx=20, anchor="w")
            
        self.theme_var = ctk.BooleanVar(value=self.is_dark)
        self.theme_switch = ctk.CTkSwitch(self.sidebar_wrapper, text="Dark Mode", variable=self.theme_var, command=self.toggle_theme, progress_color="#3b82f6")
        self.theme_switch.pack(pady=5, padx=25, anchor="w")
        
        btn_frame = ctk.CTkFrame(self.sidebar_wrapper, fg_color="transparent")
        btn_frame.pack(side="bottom", fill="x", padx=20, pady=(0, 20))
        
        # --- TOMBOL CRAFTING & SALVAGE BARU ---
        ctk.CTkButton(btn_frame, text="Calculate Crafting", command=self.add_to_list, height=45, fg_color="#3b82f6", hover_color="#2563eb", font=ctk.CTkFont(weight="bold")).pack(fill="x", pady=(0, 5))
        ctk.CTkButton(btn_frame, text="🛠️ Test Salvage", command=self.run_salvage_test, height=35, fg_color="#9b59b6", hover_color="#8e44ad", font=ctk.CTkFont(weight="bold")).pack(fill="x", pady=(0, 10))
        
        btn_update_frame = ctk.CTkFrame(btn_frame, fg_color="transparent")
        btn_update_frame.pack(fill="x")
        self.btn_update_api = ctk.CTkButton(btn_update_frame, text="Update API Data", fg_color="transparent", border_width=1, border_color="#3b82f6", text_color=("black", "white"), command=self.trigger_manual_update)
        self.btn_update_api.pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(btn_update_frame, text="Clear List", fg_color="transparent", border_width=1, border_color="#e74c3c", text_color="#e74c3c", hover_color="#c0392b", command=self.clear_list).pack(side="right", fill="x", expand=True, padx=(5, 0))

        self.tabview = ctk.CTkTabview(
            self.sidebar_wrapper, 
            segmented_button_selected_color="#3b82f6", 
            segmented_button_selected_hover_color="#2563eb",
            segmented_button_unselected_color=("#e4e4e4", "#24282c"),
            segmented_button_fg_color=("#e4e4e4", "#24282c"),
            fg_color="transparent", 
            bg_color="transparent",
            corner_radius=10
        )
        self.tabview.pack(side="top", fill="both", expand=True, padx=10, pady=5)
        
        try: self.tabview._segmented_button.configure(font=ctk.CTkFont(size=13, weight="bold"))
        except: pass
        
        self.tab_prod = self.tabview.add("Batch")
        self.tab_rec = self.tabview.add("Recipe")
        self.tab_strat = self.tabview.add("Strategy")
        
        self.create_section_label(self.tab_prod, "MARKET STATUS")
        
        self.method_seg = ctk.CTkSegmentedButton(
            self.tab_prod, 
            values=["Direct", "Order"], 
            variable=self.sell_method, 
            selected_color="#3b82f6",
            selected_hover_color="#2563eb",
            unselected_color=("#e4e4e4", "#24282c"),
            unselected_hover_color=("#d4d4d4", "#3e4348"),
            fg_color=("#e4e4e4", "#24282c"),
            font=ctk.CTkFont(size=12, weight="bold"),
            corner_radius=8
        )
        self.method_seg.pack(pady=(5, 10), padx=15, fill="x")

        self.create_section_label(self.tab_prod, "SELECT MARKET (ASIA)")
        self.market_filter = tk.StringVar(value=self.saved_data.get("market_filter", "All Asia"))
        
        self.market_dropdown = ctk.CTkComboBox(
            self.tab_prod, 
            values=["All Asia", "Singapore", "Brecilien", "Caerleon", "Martlock", "Thetford", "Fort Sterling", "Lymhurst", "Bridgewatch"],
            variable=self.market_filter,
            height=38,
            corner_radius=10,
            border_width=1,
            border_color=("#3b82f6", "#3b82f6"),
            fg_color=("#e4e4e4", "#2d3135"),
            button_color=("#3b82f6", "#3b82f6"),
            button_hover_color=("#2563eb", "#2563eb"),
            dropdown_fg_color=("#ffffff", "#1e2124"),
            dropdown_hover_color=("#e4e4e4", "#2d3135"),
            dropdown_text_color=("black", "white"),
            font=ctk.CTkFont(size=12, weight="bold"),
            dropdown_font=ctk.CTkFont(size=12),
            command=self.on_city_changed
        )
        self.market_dropdown.pack(pady=(5, 10), padx=15, fill="x")

        self.premium_var = ctk.BooleanVar(value=self.saved_data.get("premium", True))
        ctk.CTkSwitch(self.tab_prod, text="Premium Status", variable=self.premium_var, progress_color="#f1c40f").pack(pady=5, padx=15, anchor="w")
        
        self.create_section_label(self.tab_prod, "PRODUCTION TARGET")
        
        f_n = ctk.CTkFrame(self.tab_prod, fg_color="transparent"); f_n.pack(fill="x", padx=15, pady=(2, 4))
        self.create_field_label(f_n, "Target Item")
        
        f_n_inner = ctk.CTkFrame(f_n, fg_color="transparent"); f_n_inner.pack(fill="x")
        self.ent_name = ctk.CTkEntry(f_n_inner, height=35, corner_radius=6, border_width=0, fg_color=("#e4e4e4", "#2d3135"), text_color=("#1d4ed8", "#60a5fa"), font=ctk.CTkFont(weight="bold"))
        self.ent_name.insert(0, self.saved_data.get("name", ""))
        self.ent_name.pack(side="left", fill="x", expand=True)
        
        btn_search_target = ctk.CTkButton(f_n_inner, text="Search", width=70, height=35, corner_radius=6, fg_color="#3b82f6", font=ctk.CTkFont(weight="bold"), command=lambda: ItemSearchDialog(self, self.universal_db, self.on_target_selected))
        btn_search_target.pack(side="right", padx=(5, 0))
        
        self.ent_target, self.ent_out_qty = self.create_2col_input(self.tab_prod, "Target Craft", "target", "", "Output / Recipe", "out_qty", "")
        self.create_section_label(self.tab_prod, "MARKET & FEES")
        self.ent_sell, self.ent_item_val = self.create_2col_input(self.tab_prod, "Item Price (Sell/Buy)", "sell_price", "", "Item Value", "item_val", "")

        self.create_section_label(self.tab_rec, "MATERIAL LIST (AUTO)")
        
        h_f = ctk.CTkFrame(self.tab_rec, fg_color="transparent")
        h_f.pack(fill="x", padx=10, pady=(0, 5)) 
        
        h_f.grid_columnconfigure(0, weight=1)
        h_f.grid_columnconfigure(1, weight=0, minsize=65)
        h_f.grid_columnconfigure(2, weight=0, minsize=45)
        h_f.grid_columnconfigure(3, weight=0, minsize=45)
        h_f.grid_columnconfigure(4, weight=0, minsize=35)

        ctk.CTkLabel(h_f, text="Name", font=ctk.CTkFont(size=10, weight="bold"), anchor="w", padx=10).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(h_f, text="Price", font=ctk.CTkFont(size=10, weight="bold"), anchor="center").grid(row=0, column=1, sticky="ew")
        ctk.CTkLabel(h_f, text="Qty", font=ctk.CTkFont(size=10, weight="bold"), anchor="center").grid(row=0, column=2, sticky="ew")
        ctk.CTkLabel(h_f, text="Stok", font=ctk.CTkFont(size=10, weight="bold"), anchor="center").grid(row=0, column=3, sticky="ew")
        ctk.CTkLabel(h_f, text="Ret", font=ctk.CTkFont(size=10, weight="bold"), anchor="center").grid(row=0, column=4, sticky="ew")
        
        self.mats_container = ctk.CTkFrame(self.tab_rec, fg_color="transparent")
        self.mats_container.pack(fill="both", expand=True, padx=10, pady=5)

        self.create_section_label(self.tab_strat, "RRR MODIFIERS")
        self.var_basic = tk.StringVar(value=self.saved_data.get("basic", "")); self.var_local = tk.StringVar(value=self.saved_data.get("local", "")); self.var_daily = tk.StringVar(value=self.saved_data.get("daily", ""))
        for v in [self.var_basic, self.var_local, self.var_daily]: v.trace_add("write", self.auto_calculate_rrr)

        f_rrr1 = ctk.CTkFrame(self.tab_strat, fg_color="transparent"); f_rrr1.pack(fill="x", padx=15, pady=(2, 4))
        f_b = ctk.CTkFrame(f_rrr1, fg_color="transparent"); f_b.pack(side="left", fill="x", expand=True, padx=(0, 5)); self.create_field_label(f_b, "Basic"); ctk.CTkEntry(f_b, textvariable=self.var_basic, height=35, corner_radius=6, fg_color=("#e4e4e4", "#2d3135"), border_width=0).pack(fill="x")
        f_l = ctk.CTkFrame(f_rrr1, fg_color="transparent"); f_l.pack(side="right", fill="x", expand=True, padx=(5, 0)); self.create_field_label(f_l, "Local"); ctk.CTkEntry(f_l, textvariable=self.var_local, height=35, corner_radius=6, fg_color=("#e4e4e4", "#2d3135"), border_width=0).pack(fill="x")

        self.f_rrr_row_2 = ctk.CTkFrame(self.tab_strat, fg_color="transparent"); self.f_rrr_row_2.pack(fill="x", padx=15, pady=(2, 4))
        f_d = ctk.CTkFrame(self.f_rrr_row_2, fg_color="transparent"); f_d.pack(side="left", fill="x", expand=True, padx=(0, 5)); self.create_field_label(f_d, "Daily"); ctk.CTkEntry(f_d, textvariable=self.var_daily, height=35, corner_radius=6, fg_color=("#e4e4e4", "#2d3135"), border_width=0).pack(fill="x")
        self.f_focb = ctk.CTkFrame(self.f_rrr_row_2, fg_color="transparent"); self.create_field_label(self.f_focb, "Focus yield"); ent_fb = ctk.CTkEntry(self.f_focb, height=35, corner_radius=6, fg_color=("#cbd4db", "#34495e"), border_width=0); ent_fb.insert(0, "59"); ent_fb.configure(state="readonly"); ent_fb.pack(fill="x")

        self.create_section_label(self.tab_strat, "FOCUS & STATION FEE")
        f_st1 = ctk.CTkFrame(self.tab_strat, fg_color="transparent"); f_st1.pack(fill="x", padx=15, pady=(2, 4))
        f_fee = ctk.CTkFrame(f_st1, fg_color="transparent"); f_fee.pack(side="left", fill="x", expand=True, padx=(0, 5)); self.create_field_label(f_fee, "Station Fee"); self.ent_fee = ctk.CTkEntry(f_fee, height=35, corner_radius=6, fg_color=("#e4e4e4", "#2d3135"), border_width=0); self.ent_fee.insert(0, self.saved_data.get("fee", "")); self.ent_fee.pack(fill="x")
        f_rs = ctk.CTkFrame(f_st1, fg_color="transparent"); f_rs.pack(side="right", fill="x", expand=True, padx=(5, 0)); self.create_field_label(f_rs, "Total RRR (%)"); self.ent_rrr = ctk.CTkEntry(f_rs, height=35, corner_radius=6, fg_color=("#e4e4e4", "#2d3135"), text_color=("#1d4ed8", "#60a5fa"), border_width=0, font=ctk.CTkFont(weight="bold")); self.ent_rrr.pack(fill="x")
        
        self.frame_focus_toggle = ctk.CTkFrame(self.tab_strat, fg_color="transparent"); self.frame_focus_toggle.pack(fill="x", padx=15, pady=(15, 5))
        self.focus_toggle_var = ctk.BooleanVar(value=self.saved_data.get("focus_toggle", False))
        ctk.CTkSwitch(self.frame_focus_toggle, text="Craft Pakai Focus?", variable=self.focus_toggle_var, command=self.toggle_focus_mode, progress_color="#9b59b6").pack(side="left")

        self.frame_focus_inputs = ctk.CTkFrame(self.tab_strat, fg_color="transparent")
        f_fcl = ctk.CTkFrame(self.frame_focus_inputs, fg_color="transparent"); f_fcl.pack(side="left", fill="x", expand=True, padx=(0, 5)); self.create_field_label(f_fcl, "Focus Cost / Craft"); self.ent_focus_cost = ctk.CTkEntry(f_fcl, height=35, corner_radius=6, fg_color=("#e4e4e4", "#2d3135"), border_width=0); self.ent_focus_cost.insert(0, self.saved_data.get("focus_cost", "")); self.ent_focus_cost.pack(fill="x")
        f_fcr = ctk.CTkFrame(self.frame_focus_inputs, fg_color="transparent"); f_fcr.pack(side="right", fill="x", expand=True, padx=(5, 0)); self.create_field_label(f_fcr, "Focus Bank"); self.ent_focus_pool = ctk.CTkEntry(f_fcr, height=35, corner_radius=6, fg_color=("#e4e4e4", "#2d3135"), border_width=0); self.ent_focus_pool.insert(0, self.saved_data.get("focus_pool", "")); self.ent_focus_pool.pack(fill="x")
        self.toggle_focus_mode()

        self.main_container = ctk.CTkFrame(self, fg_color=("#ffffff", "#121416"), corner_radius=0); self.main_container.pack(side="right", fill="both", expand=True)
        self.h_res = ctk.CTkFrame(self.main_container, fg_color="transparent"); self.h_res.pack(side="top", fill="x", padx=30, pady=(20, 5))
        ctk.CTkLabel(self.h_res, text="Market Analysis Result", font=ctk.CTkFont(size=24, weight="bold"), text_color=("black", "white")).pack(side="left")
        
        self.scrollable_list = ctk.CTkScrollableFrame(self.main_container, fg_color="transparent"); self.scrollable_list.pack(side="top", fill="both", expand=True, padx=25, pady=0)
        self.bind_global_scroll(self.main_container, self._scroll_main)

    def add_static_material_row(self, name_val="", price_val="", qty_val="", is_ret=True, own_qty_val=""):
        row = ctk.CTkFrame(self.mats_container, fg_color="transparent")
        row.pack(fill="x", pady=2)
        
        row.grid_columnconfigure(0, weight=1)       
        row.grid_columnconfigure(1, weight=0, minsize=65) 
        row.grid_columnconfigure(2, weight=0, minsize=45) 
        row.grid_columnconfigure(3, weight=0, minsize=45) 
        row.grid_columnconfigure(4, weight=0, minsize=35) 

        lbl_n = ctk.CTkLabel(row, text=name_val, height=35, corner_radius=6, fg_color=("#dfe6e9", "#2d3436"), font=ctk.CTkFont(size=11, weight="bold"), anchor="w", padx=10)
        lbl_n.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        
        ent_p = ctk.CTkEntry(row, height=35, width=60, corner_radius=6, border_width=0, fg_color=("#e4e4e4", "#2d3135"))
        ent_p.grid(row=0, column=1, sticky="w", padx=2)
        ent_p.insert(0, price_val)
        
        lbl_q = ctk.CTkLabel(row, text=str(qty_val), height=35, width=40, corner_radius=6, fg_color=("#dfe6e9", "#2d3436"), font=ctk.CTkFont(weight="bold"))
        lbl_q.grid(row=0, column=2, sticky="w", padx=2)
        
        ent_o = ctk.CTkEntry(row, height=35, width=40, placeholder_text="0", corner_radius=6, border_width=0, fg_color=("#e4e4e4", "#2d3135"), text_color=("#b45309", "#fbbf24"), font=ctk.CTkFont(weight="bold"))
        ent_o.grid(row=0, column=3, sticky="w", padx=2)
        ent_o.insert(0, own_qty_val)
        
        ret_var = ctk.BooleanVar(value=is_ret)
        chk_ret = ctk.CTkCheckBox(row, text="", variable=ret_var, width=20, checkbox_width=18, checkbox_height=18, state="disabled", fg_color="#3b82f6")
        chk_ret.grid(row=0, column=4, sticky="w", padx=(5, 0))
        
        self.material_entries.append({"name": lbl_n, "price": ent_p, "qty": lbl_q, "is_ret": ret_var, "own_qty": ent_o})

    def load_saved_materials(self):
        saved_mats = self.saved_data.get("materials", [])
        for i in range(len(saved_mats)):
            m = saved_mats[i]
            self.add_static_material_row(m.get("name", ""), m.get("price", ""), m.get("qty", ""), m.get("is_ret", True), m.get("own_qty", ""))

    # --- FUNGSI TEST SALVAGE BARU ---
    def run_salvage_test(self):
        try:
            mats_data = []
            for mat in self.material_entries:
                p_str = mat['price'].get().strip()
                q_str = mat['qty'].cget("text")
                if p_str and q_str:
                    try:
                        p_val = float(p_str)
                        q_val = float(q_str)
                        if p_val >= 0 and q_val > 0:
                            mats_data.append({
                                "name": mat['name'].cget("text"),
                                "qty_in_recipe": q_val,
                                "market_sell_price": p_val
                            })
                    except ValueError: pass
            
            if not mats_data: return
            
            target_name = self.ent_name.get().strip() or "Item"
            item_buy_price = float(self.ent_sell.get() or 0)
            item_value = float(self.ent_item_val.get() or 0)
            
            res = calculate_salvage_flip(target_name, item_buy_price, item_value, mats_data, self.premium_var.get())
            
            if "error" in res:
                print(res["error"])
                return
                
            self.render_salvage_card(res)
        except Exception as e:
            print(f"Error Salvage Test: {e}")

    # --- DESAIN KARTU KHUSUS SALVAGE (Tanpa Save History) ---
    def render_salvage_card(self, res):
        card = ctk.CTkFrame(self.scrollable_list, corner_radius=8, fg_color=("#f4f5f7", "#1a1c1e"), border_width=1, border_color="#9b59b6")
        card.pack(pady=5, padx=10, fill="x") 
        
        status_color = "#2ecc71" if res.get('is_profitable', False) else "#e74c3c"
        ctk.CTkFrame(card, width=4, height=0, corner_radius=2, fg_color="#9b59b6").pack(side="left", fill="y", padx=(10, 0), pady=10)
        
        c_w = ctk.CTkFrame(card, fg_color="transparent")
        c_w.pack(side="left", fill="x", expand=True, padx=20, pady=12) 
        
        h_f = ctk.CTkFrame(c_w, fg_color="transparent")
        h_f.pack(fill="x")
        
        i_l = ctk.CTkFrame(h_f, fg_color="transparent")
        i_l.pack(side="left")
        
        ctk.CTkLabel(i_l, text=f"🛠️ SALVAGE: {res.get('name', 'Item').upper()}", font=ctk.CTkFont(size=14, weight="bold"), text_color="#9b59b6").pack(anchor="w")
        profit_val = res.get('profit', 0)
        ctk.CTkLabel(i_l, text=f"Salvage Profit: Rp {profit_val:+,.0f}  |  Margin: {res.get('margin', 0):.1f}%", font=ctk.CTkFont(size=12, weight="bold"), text_color=status_color).pack(anchor="w", pady=(2, 0))
        
        btn_frame = ctk.CTkFrame(h_f, fg_color="transparent")
        btn_frame.pack(side="right")
        
        details_visible = tk.BooleanVar(value=False)
        det_f = ctk.CTkFrame(c_w, fg_color="transparent")
        
        def toggle():
            if details_visible.get():
                det_f.pack_forget()
                btn_t.configure(text="Detail ▼")
                details_visible.set(False)
            else:
                det_f.pack(fill="x", pady=(15, 0))
                btn_t.configure(text="Tutup ▲")
                details_visible.set(True)
                self.bind_global_scroll(det_f, self._scroll_main)
                
        btn_t = ctk.CTkButton(btn_frame, text="Detail ▼", width=60, height=28, font=ctk.CTkFont(size=11), fg_color=("#e4e4e4", "#2d3135"), hover_color=("#c0c0c0", "#3e4348"), text_color=("black", "white"), command=toggle)
        btn_t.pack(side="left", padx=(0, 5))
        
        def remove_card():
            card.destroy()
            
        ctk.CTkButton(btn_frame, text="✕", font=ctk.CTkFont(size=14, weight="bold"), width=30, height=30, corner_radius=6, fg_color="transparent", text_color=("#888888", "#5a5e63"), hover_color="#ff4d4d", command=remove_card).pack(side="left")

        ctk.CTkFrame(det_f, height=2, fg_color=("#d4d4d4", "#2d3135")).pack(fill="x", pady=(10, 10))

        ctk.CTkLabel(det_f, text="RECOVERED MATERIALS (25%)", font=ctk.CTkFont(size=12, weight="bold"), text_color=("#6c757d", "#8e949a")).pack(anchor="w", pady=(0, 5), padx=5)
        
        table_f = ctk.CTkFrame(det_f, fg_color="transparent")
        table_f.pack(fill="x", pady=2, padx=5)
        
        table_f.grid_columnconfigure(0, weight=1)
        table_f.grid_columnconfigure(1, weight=0, minsize=80)
        table_f.grid_columnconfigure(2, weight=0, minsize=100)
        table_f.grid_columnconfigure(3, weight=0, minsize=120)
        
        headers = ["Material Name", "Recovered", "Unit Sell Price", "Net Revenue (After Tax)"]
        for col_idx, h_text in enumerate(headers):
            anchor_pos = "w" if col_idx == 0 else "e"
            ctk.CTkLabel(table_f, text=h_text, font=ctk.CTkFont(size=11, weight="bold"), text_color=("#6c757d", "#8e949a"), anchor=anchor_pos).grid(row=0, column=col_idx, sticky="ew", padx=5, pady=2)
            
        total_mats_revenue = 0
        for row_idx, mat in enumerate(res.get('materials_salvaged', []), start=1):
            mat_name = mat['name'][:30] + ".." if len(mat['name']) > 30 else mat['name']
            
            ctk.CTkLabel(table_f, text=mat_name, font=ctk.CTkFont(size=11, weight="bold"), text_color="#3498db", anchor="w", justify="left").grid(row=row_idx, column=0, sticky="ew", padx=5, pady=4)
            ctk.CTkLabel(table_f, text=f"{mat['qty_returned']:,.0f}", font=ctk.CTkFont(size=12, weight="bold"), anchor="e").grid(row=row_idx, column=1, sticky="ew", padx=5)
            ctk.CTkLabel(table_f, text=f"Rp {mat.get('unit_price', 0):,.0f}", font=ctk.CTkFont(size=11), text_color=("#adb5bd", "#5a5e63"), anchor="e").grid(row=row_idx, column=2, sticky="ew", padx=5)
            ctk.CTkLabel(table_f, text=f"Rp {mat['net_value']:,.0f}", font=ctk.CTkFont(size=12, weight="bold"), text_color="#f1c40f", anchor="e").grid(row=row_idx, column=3, sticky="ew", padx=5)
            
            total_mats_revenue += mat['net_value']

        ctk.CTkFrame(det_f, height=2, fg_color=("#d4d4d4", "#2d3135")).pack(fill="x", pady=(10, 15))

        b_c = ctk.CTkFrame(det_f, fg_color="transparent")
        b_c.pack(fill="x", padx=5)
        
        l_c = ctk.CTkFrame(b_c, fg_color="transparent")
        l_c.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        def add_fin_row(parent, label, val, is_bold=False, color=None):
            rf = ctk.CTkFrame(parent, fg_color="transparent")
            rf.pack(fill="x", pady=4)
            fnt = ctk.CTkFont(size=12, weight="bold" if is_bold else "normal")
            c = color if color else ("black", "white")
            lbl_c = ("#6c757d", "#8e949a") if not is_bold else ("black", "white")
            ctk.CTkLabel(rf, text=label, font=ctk.CTkFont(size=12), text_color=lbl_c).pack(side="left")
            ctk.CTkLabel(rf, text=val, font=fnt, text_color=c).pack(side="right")

        add_fin_row(l_c, "Harga Beli Rongsok (Modal)", f"Rp {res.get('buy_price', 0):,.0f}", True, "#e74c3c")
        add_fin_row(l_c, "Silver Refund NPC (25% IV)", f"Rp {res.get('silver_from_npc', 0):,.0f}", False, "#3498db")
        add_fin_row(l_c, "Jual Balik Material ke Market", f"Rp {total_mats_revenue:,.0f}", False, "#3498db")
        
        r_c = ctk.CTkFrame(b_c, fg_color="transparent")
        r_c.pack(side="right", fill="both", expand=True, padx=(10, 0))
        
        add_fin_row(r_c, "Total Uang Kembali", f"Rp {res.get('total_revenue', 0):,.0f}", True, "#3498db")
        add_fin_row(r_c, "Salvage Profit", f"Rp {res.get('profit', 0):,.0f}", True, status_color)

        self.bind_global_scroll(card, self._scroll_main)

    def add_to_list(self):
        try:
            mats_data = []
            for mat in self.material_entries:
                p_str = mat['price'].get().strip()
                q_str = mat['qty'].cget("text") 
                own_qty_str = mat['own_qty'].get().strip()
                
                if p_str and q_str:
                    try:
                        p_val = float(p_str)
                        q_val = float(q_str)
                        own_q_val = float(own_qty_str) if own_qty_str else 0.0
                        
                        if p_val >= 0 and q_val > 0: 
                            mat_name_val = mat['name'].cget("text")
                            
                            mats_data.append({
                                "name": mat_name_val, 
                                "price": p_val, 
                                "qty": q_val, 
                                "is_return": mat['is_ret'].get(), 
                                "qty_from_stock": own_q_val 
                            })
                    except ValueError: pass
            
            if not mats_data: return 
            
            target_name = self.ent_name.get().strip() or "Item"
            res = calculate_refining_logic(
                target_name, mats_data, float(self.ent_target.get() or 0), float(self.ent_out_qty.get() or 1), 
                float(self.ent_sell.get() or 0), float(self.ent_item_val.get() or 0), float(self.ent_fee.get() or 0), 
                float(self.ent_rrr.get() or 0), self.premium_var.get(), self.focus_toggle_var.get(), 
                float(self.ent_focus_cost.get() or 0), float(self.ent_focus_pool.get() or 30000), 
                sell_method=self.sell_method.get().lower()
            )
            
            if "error" in res:
                print(f"Peringatan: {res['error']}")
                return

            self.history.append(res); self.render_expandable_card(res); self.save_current_state()
        except Exception as e: 
            print(f"Error di add_to_list: {e}")
            
    def render_expandable_card(self, res):
        card = ctk.CTkFrame(self.scrollable_list, corner_radius=8, fg_color=("#f4f5f7", "#1a1c1e"))
        card.pack(pady=5, padx=10, fill="x") 
        
        status_color = "#2ecc71" if res.get('is_profitable', False) else "#e74c3c"
        
        ctk.CTkFrame(card, width=4, height=0, corner_radius=2, fg_color=status_color).pack(side="left", fill="y", padx=(10, 0), pady=10)
        
        c_w = ctk.CTkFrame(card, fg_color="transparent")
        c_w.pack(side="left", fill="x", expand=True, padx=20, pady=12) 
        
        h_f = ctk.CTkFrame(c_w, fg_color="transparent")
        h_f.pack(fill="x")
        
        i_l = ctk.CTkFrame(h_f, fg_color="transparent")
        i_l.pack(side="left")
        
        title_text = f"{res.get('name', 'Item').upper()}  |  TOTAL OUTPUT: {res.get('total_produced', 0):,} ITEM"
        ctk.CTkLabel(i_l, text=title_text, font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w")
        
        profit_val = res.get('real_profit', 0)
        ctk.CTkLabel(i_l, text=f"Total Profit: Rp {profit_val:+,.0f}  |  Margin: {res.get('margin', 0):.1f}%", 
                     font=ctk.CTkFont(size=12, weight="bold"), text_color=status_color).pack(anchor="w", pady=(2, 0))
        
        btn_frame = ctk.CTkFrame(h_f, fg_color="transparent")
        btn_frame.pack(side="right")
        
        details_visible = tk.BooleanVar(value=False)
        det_f = ctk.CTkFrame(c_w, fg_color="transparent")
        
        def toggle():
            if details_visible.get():
                det_f.pack_forget()
                btn_t.configure(text="Detail ▼")
                details_visible.set(False)
            else:
                det_f.pack(fill="x", pady=(15, 0))
                btn_t.configure(text="Tutup ▲")
                details_visible.set(True)
                self.bind_global_scroll(det_f, self._scroll_main)
                
        btn_t = ctk.CTkButton(btn_frame, text="Detail ▼", width=60, height=28, font=ctk.CTkFont(size=11), 
                             fg_color=("#e4e4e4", "#2d3135"), hover_color=("#c0c0c0", "#3e4348"), 
                             text_color=("black", "white"), command=toggle)
        btn_t.pack(side="left", padx=(0, 5))
        
        def remove_card():
            if res in self.history: 
                self.history.remove(res)
                self.save_current_state()
            card.destroy()
            
        ctk.CTkButton(btn_frame, text="✕", font=ctk.CTkFont(size=14, weight="bold"), width=30, height=30, 
                     corner_radius=6, fg_color="transparent", text_color=("#888888", "#5a5e63"), 
                     hover_color="#ff4d4d", command=remove_card).pack(side="left")
        
        target_input = int(self.ent_target.get() or 0)
        if res.get('actual_craft', 0) < target_input and self.focus_toggle_var.get():
            f_warn = ctk.CTkFrame(det_f, fg_color=("#fff3e0", "#3e2723"), corner_radius=6)
            f_warn.pack(fill="x", pady=(10, 5)) 
            ctk.CTkLabel(f_warn, text=f"⚠️ FOCUS TERBATAS: Sisa Focus hanya cukup untuk {res.get('actual_craft', 0)}x siklus craft!", 
                         text_color=("#e65100", "#ffcc80"), font=ctk.CTkFont(size=11, weight="bold")).pack(pady=8, padx=10)

        ctk.CTkFrame(det_f, height=2, fg_color=("#d4d4d4", "#2d3135")).pack(fill="x", pady=(10, 10))

        ctk.CTkLabel(det_f, text="MATERIAL LIST TO BUY", font=ctk.CTkFont(size=12, weight="bold"), text_color=("#6c757d", "#8e949a")).pack(anchor="w", pady=(0, 5), padx=5)
        
        table_f = ctk.CTkFrame(det_f, fg_color="transparent")
        table_f.pack(fill="x", pady=2, padx=5)
        
        table_f.grid_columnconfigure(0, weight=1)                 
        table_f.grid_columnconfigure(1, weight=0, minsize=70)     
        table_f.grid_columnconfigure(2, weight=0, minsize=60)     
        table_f.grid_columnconfigure(3, weight=0, minsize=90)     
        table_f.grid_columnconfigure(4, weight=0, minsize=100)    
        table_f.grid_columnconfigure(5, weight=0, minsize=60)     
        
        headers = ["Material Name", "To Buy", "Stock", "Unit Price", "Cost", "Leftover"]
        for col_idx, h_text in enumerate(headers):
            anchor_pos = "w" if col_idx == 0 else "e"
            ctk.CTkLabel(table_f, text=h_text, font=ctk.CTkFont(size=11, weight="bold"), text_color=("#6c757d", "#8e949a"), anchor=anchor_pos).grid(row=0, column=col_idx, sticky="ew", padx=5, pady=2)
            
        for row_idx, mat in enumerate(res.get('buy_list', []), start=1):
            raw_stok = mat.get('qty_from_stock', 0)
            qty_stok = int(raw_stok) if float(raw_stok).is_integer() else raw_stok
            base_color = "#3498db" if float(qty_stok) == 0 else "#e67e22" 
            
            is_ret = mat.get('is_return', True)
            ret_symbol = "✓" if is_ret else "✗"
            
            mat_name = mat['name'][:22] + ".." if len(mat['name']) > 22 else mat['name']
            name_text = f"{mat_name}\nRet: {ret_symbol}"
            
            ctk.CTkLabel(table_f, text=name_text, font=ctk.CTkFont(size=11, weight="bold"), text_color=base_color, anchor="w", justify="left").grid(row=row_idx, column=0, sticky="ew", padx=5, pady=4)
            ctk.CTkLabel(table_f, text=f"{mat['qty_to_buy']:,.0f}", font=ctk.CTkFont(size=12, weight="bold"), anchor="e").grid(row=row_idx, column=1, sticky="ew", padx=5)
            ctk.CTkLabel(table_f, text=f"{qty_stok:,.0f}", font=ctk.CTkFont(size=11), text_color=("#adb5bd", "#5a5e63"), anchor="e").grid(row=row_idx, column=2, sticky="ew", padx=5)
            ctk.CTkLabel(table_f, text=f"Rp {mat['price']:,.0f}", font=ctk.CTkFont(size=11), anchor="e").grid(row=row_idx, column=3, sticky="ew", padx=5)
            ctk.CTkLabel(table_f, text=f"Rp {mat['cash_out']:,.0f}", font=ctk.CTkFont(size=12, weight="bold"), text_color="#f1c40f", anchor="e").grid(row=row_idx, column=4, sticky="ew", padx=5)
            ctk.CTkLabel(table_f, text=f"{mat['leftover']:.0f}", font=ctk.CTkFont(size=11), text_color=("#adb5bd", "#5a5e63"), anchor="e").grid(row=row_idx, column=5, sticky="ew", padx=5)

        ctk.CTkFrame(det_f, height=2, fg_color=("#d4d4d4", "#2d3135")).pack(fill="x", pady=(10, 15))

        b_c = ctk.CTkFrame(det_f, fg_color="transparent")
        b_c.pack(fill="x", padx=5)
        
        l_c = ctk.CTkFrame(b_c, fg_color="transparent")
        l_c.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        def add_fin_row(parent, label, val, is_bold=False, color=None):
            rf = ctk.CTkFrame(parent, fg_color="transparent")
            rf.pack(fill="x", pady=4)
            fnt = ctk.CTkFont(size=12, weight="bold" if is_bold else "normal")
            c = color if color else ("black", "white")
            lbl_c = ("#6c757d", "#8e949a") if not is_bold else ("black", "white")
            ctk.CTkLabel(rf, text=label, font=ctk.CTkFont(size=12), text_color=lbl_c).pack(side="left")
            ctk.CTkLabel(rf, text=val, font=fnt, text_color=c).pack(side="right")

        add_fin_row(l_c, "Total Material Cost", f"Rp {res.get('total_material_cost', 0):,.0f}", False, "#e67e22")
        add_fin_row(l_c, f"Station Fee ({res.get('actual_craft', 0)}x)", f"Rp {res.get('total_tax_cost', 0):,.0f}", False, "#e67e22")
        ctk.CTkFrame(l_c, height=1, fg_color=("#d4d4d4", "#3e4348")).pack(fill="x", pady=2)
        add_fin_row(l_c, "Total Prod. Cost", f"Rp {res.get('net_production_cost', 0):,.0f}", True, "#e67e22")
        add_fin_row(l_c, "Prod. Cost / Item", f"Rp {res.get('cost_per_item', 0):,.0f}", True, "#e67e22")

        r_c = ctk.CTkFrame(b_c, fg_color="transparent")
        r_c.pack(side="right", fill="both", expand=True, padx=(10, 0))
        
        add_fin_row(r_c, "Gross Revenue", f"Rp {res.get('gross_revenue', 0):,.0f}", False, "#3498db")
        add_fin_row(r_c, "Market Tax", f"- Rp {res.get('market_fee_deduction', 0):,.0f}", False, "#e74c3c")
        ctk.CTkFrame(r_c, height=1, fg_color=("#d4d4d4", "#3e4348")).pack(fill="x", pady=2)
        add_fin_row(r_c, "Net Revenue", f"Rp {res.get('total_revenue', 0):,.0f}", True, "#3498db")
        add_fin_row(r_c, "Profit / Item", f"Rp {res.get('profit_per_item', 0):,.0f}", True, status_color)

        ctk.CTkFrame(det_f, height=2, fg_color=("#d4d4d4", "#2d3135")).pack(fill="x", pady=(15, 10))

        if 'suggested' in res:
            s_box = ctk.CTkFrame(det_f, fg_color=("#e9ecef", "#24282c"), corner_radius=8)
            s_box.pack(fill="x", pady=5, padx=5)
            ctk.CTkLabel(s_box, text="💡 REKOMENDASI HARGA JUAL (Target Margin Bersih)", font=ctk.CTkFont(size=12, weight="bold"), text_color="#3498db").pack(pady=(10, 5))
            
            s_grid = ctk.CTkFrame(s_box, fg_color="transparent")
            s_grid.pack(fill="x", pady=(0, 15), padx=10)
            
            sug = res['suggested']
            for m_lbl, m_key in [("Margin 5%", "m5"), ("Margin 10%", "m10"), ("Margin 20%", "m20")]:
                f = ctk.CTkFrame(s_grid, fg_color="transparent")
                f.pack(side="left", expand=True, fill="x")
                ctk.CTkLabel(f, text=m_lbl, font=ctk.CTkFont(size=11), text_color="#8e949a").pack()
                val_fmt = int(sug.get(m_key, 0)) 
                ctk.CTkLabel(f, text=f"Rp {val_fmt:,}", font=ctk.CTkFont(size=14, weight="bold"), text_color=("black", "white")).pack()

        self.bind_global_scroll(card, self._scroll_main)
    
    def clear_list(self):
        for child in self.scrollable_list.winfo_children(): child.destroy()
        self.history.clear(); self.save_current_state()

    def save_current_state(self):
        saved_mats = []
        for mat in self.material_entries:
            p = mat['price'].get().strip()
            q = mat['qty'].cget("text")         
            o_q = mat['own_qty'].get().strip()
            m_name = mat['name'].cget("text")   
            
            if p and q: 
                saved_mats.append({
                    "name": m_name, "price": p, "qty": q, 
                    "is_ret": mat['is_ret'].get(), "own_qty": o_q 
                })
        
        save_to_json({
            "name": self.ent_name.get().strip(), "target": self.ent_target.get(), "out_qty": self.ent_out_qty.get(), 
            "premium": self.premium_var.get(), "sell_price": self.ent_sell.get(), "item_val": self.ent_item_val.get(), 
            "fee": self.ent_fee.get(), "rrr_manual": self.ent_rrr.get(), "focus_cost": self.ent_focus_cost.get(), 
            "focus_pool": self.ent_focus_pool.get(), "focus_toggle": self.focus_toggle_var.get(), "basic": self.var_basic.get(), 
            "local": self.var_local.get(), "daily": self.var_daily.get(), "dark_mode": self.theme_var.get(), "materials": saved_mats, 
            "history": self.history, "sell_method": self.sell_method.get().lower() 
        })

if __name__ == "__main__":
    app = AlbionApp(); app.mainloop()