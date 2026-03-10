import customtkinter as ctk
import tkinter as tk
from PIL import Image 
import sys
import os
import requests
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

import db_manager
import api_engine # <-- IMPORT MESIN API BARU KITA
from logic_engine import calculate_refining_logic
from salvage_engine import calculate_salvage_flip
from data_manager import save_to_json, load_from_json

# IMPORT DARI FILE PECAHAN
from config_utils import get_resource_path, IMG_DIR, get_item_image
from db_manager import DB_PATH
from ui_search import ItemSearchModal
from ui_cards import create_crafting_card, create_salvage_card

# ==========================================
# CLASS UTAMA APLIKASI
# ==========================================
class AlbionApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        db_manager.initialize_db()
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
            if res.get('type') == 'salvage':
                create_salvage_card(self, self.salvage_list, res)
            else:
                create_crafting_card(self, self.crafting_list, res)
            
        self.universal_db = {}
        
        # CEK STARTUP SEKARANG PAKE DB_PATH (SQLITE), BUKAN JSON LAGI
        has_images = any(f.endswith('.png') for f in os.listdir(IMG_DIR)) if os.path.exists(IMG_DIR) else False
        
        if os.path.exists(DB_PATH) and has_images:
            self.universal_db = {} # Kosongin aja karena search udah pake SQLite langsung
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
            self.after(0, self.update_setup_ui, "Mendownload Database Resep & Build SQLite (30MB+)...", 0.1)
            
            # PANGGIL API ENGINE YANG UDAH DIPISAH
            db = api_engine.download_and_build_db()
            
            if not db:
                self.after(0, report_error, "Gagal mendownload data dari API (Kemungkinan Data Korup).")
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

    def trigger_manual_update(self):
        self.btn_update_api.configure(text="Mendownload & Build DB...", state="disabled")
        
        def bg_update():
            # PANGGIL API ENGINE
            db = api_engine.download_and_build_db()
            
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

    def on_target_selected(self, selected_name):
        data = db_manager.get_item_detail_db(selected_name)
        if not data: return
        
        self.ent_name.delete(0, tk.END)
        self.ent_name.insert(0, selected_name)
        
        for widget in self.mats_container.winfo_children(): widget.destroy()
        self.material_entries = []
        
        self.ent_out_qty.delete(0, tk.END)
        self.ent_out_qty.insert(0, str(data['out_qty']))
        
        self.ent_item_val.delete(0, tk.END)
        self.ent_item_val.insert(0, str(int(data['item_value'])))
        
        for mat in data['recipe']:
            self.add_static_material_row(
                name_val=mat["name"], 
                price_val="", 
                qty_val=mat["qty"], 
                is_ret=mat.get("is_returnable", True), 
                own_qty_val="0"
            )

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

    def _scroll_main(self, event): 
        if self.result_tabview.get() == "Crafting Results":
            target_canvas = self.crafting_list._parent_canvas
        else:
            target_canvas = self.salvage_list._parent_canvas
        self._scroll_handler(event, target_canvas)

    def create_section_label(self, parent, text):
        lbl = ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(size=12, weight="bold"), text_color=("#1d4ed8", "#60a5fa"))
        lbl.pack(pady=(12, 2), padx=15, anchor="w")
        return lbl

    def create_field_label(self, parent, text):
        lbl = ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(size=10), text_color=("#6c757d", "#8e949a"))
        lbl.pack(anchor="w")
        return lbl

    def create_2col_input(self, parent, label1, key1, def1, label2, key2, def2):
        frame = ctk.CTkFrame(parent, fg_color="transparent"); frame.pack(fill="x", padx=15, pady=(2, 4))
        f_l = ctk.CTkFrame(frame, fg_color="transparent"); f_l.pack(side="left", fill="x", expand=True, padx=(0, 5)); 
        lbl_1 = self.create_field_label(f_l, label1)
        ent1 = ctk.CTkEntry(f_l, height=35, corner_radius=6, fg_color=("#e4e4e4", "#2d3135"), border_width=0); ent1.insert(0, self.saved_data.get(key1, def1)); ent1.pack(fill="x")
        f_r = ctk.CTkFrame(frame, fg_color="transparent"); f_r.pack(side="right", fill="x", expand=True, padx=(5, 0)); 
        lbl_2 = self.create_field_label(f_r, label2)
        ent2 = ctk.CTkEntry(f_r, height=35, corner_radius=6, fg_color=("#e4e4e4", "#2d3135"), border_width=0); ent2.insert(0, self.saved_data.get(key2, def2)); ent2.pack(fill="x")
        return ent1, ent2, lbl_1, lbl_2

    def auto_calculate_rrr(self, *args):
        try:
            val_b = self.var_basic.get().replace(',', '.') if self.var_basic.get() else '0'
            val_l = self.var_local.get().replace(',', '.') if self.var_local.get() else '0'
            val_d = self.var_daily.get().replace(',', '.') if self.var_daily.get() else '0'
            
            basic = float(val_b)
            local = float(val_l)
            daily = float(val_d)
            focus = 59.0 if self.focus_toggle_var.get() else 0.0 
            
            total_bonus = basic + local + daily + focus
            rrr = (total_bonus / (100 + total_bonus)) * 100 if total_bonus > 0 else 0
            
            self.ent_rrr.configure(state="normal")
            self.ent_rrr.delete(0, tk.END)
            self.ent_rrr.insert(0, f"{rrr:.7f}")
            self.ent_rrr.configure(state="readonly")
        except: pass 

    def toggle_focus_mode(self):
        if self.focus_toggle_var.get():
            self.f_focb.pack(side="right", fill="x", expand=True, padx=(5, 0))
            self.frame_focus_inputs.pack(fill="x", padx=15, pady=(2, 4), after=self.frame_focus_toggle)
        else:
            self.f_focb.pack_forget(); self.frame_focus_inputs.pack_forget()
            self.ent_focus_cost.delete(0, tk.END); self.ent_focus_cost.insert(0, "")
        self.auto_calculate_rrr()

    def toggle_app_mode(self):
        is_salvage = self.mode_toggle_var.get()
        
        if is_salvage:
            self.lbl_target_craft.configure(text="Jumlah Item di-Salvage")
            self.lbl_out_qty.configure(text="Abaikan (Tidak perlu diisi)")
            self.ent_out_qty.configure(state="disabled", fg_color=("#d4d4d4", "#24282c"))
            
            self.method_seg.configure(state="disabled")
            
            self.ent_basic.configure(state="disabled", fg_color=("#d4d4d4", "#24282c"))
            self.ent_local.configure(state="disabled", fg_color=("#d4d4d4", "#24282c"))
            self.ent_daily.configure(state="disabled", fg_color=("#d4d4d4", "#24282c"))
            self.ent_fee.configure(state="disabled", fg_color=("#d4d4d4", "#24282c"))
            self.ent_rrr.configure(state="disabled", fg_color=("#d4d4d4", "#24282c"))
            self.switch_focus.configure(state="disabled")
            self.ent_focus_cost.configure(state="disabled", fg_color=("#d4d4d4", "#24282c"))
            self.ent_focus_pool.configure(state="disabled", fg_color=("#d4d4d4", "#24282c"))
            
            self.tabview.set("Batch")
            self.result_tabview.set("Salvage Results")
            
            self.btn_main_action.configure(text="Hitung Salvage", fg_color="#9b59b6", hover_color="#8e44ad", command=self.run_salvage_test)
            
        else:
            self.lbl_target_craft.configure(text="Target Craft")
            self.lbl_out_qty.configure(text="Output / Recipe")
            self.ent_out_qty.configure(state="normal", fg_color=("#e4e4e4", "#2d3135"))
            
            self.method_seg.configure(state="normal")
            
            self.ent_basic.configure(state="normal", fg_color=("#e4e4e4", "#2d3135"))
            self.ent_local.configure(state="normal", fg_color=("#e4e4e4", "#2d3135"))
            self.ent_daily.configure(state="normal", fg_color=("#e4e4e4", "#2d3135"))
            self.ent_fee.configure(state="normal", fg_color=("#e4e4e4", "#2d3135"))
            
            self.ent_rrr.configure(state="readonly", fg_color=("#e4e4e4", "#2d3135"))
            
            self.switch_focus.configure(state="normal")
            self.ent_focus_cost.configure(state="normal", fg_color=("#e4e4e4", "#2d3135"))
            self.ent_focus_pool.configure(state="normal", fg_color=("#e4e4e4", "#2d3135"))
            
            self.result_tabview.set("Crafting Results")
            
            self.btn_main_action.configure(text="Calculate Crafting", fg_color="#3b82f6", hover_color="#2563eb", command=self.add_to_list)

    def setup_ui(self):
        self.sidebar_wrapper = ctk.CTkFrame(self, width=420, fg_color=("#f4f5f7", "#1a1c1e"), corner_radius=0)
        self.sidebar_wrapper.pack(side="left", fill="y"); self.sidebar_wrapper.pack_propagate(False)
        
        header_f = ctk.CTkFrame(self.sidebar_wrapper, fg_color="transparent")
        header_f.pack(fill="x", padx=20, pady=(20, 5))
        
        try:
            logo_black = Image.open(get_resource_path("logo1.png")); logo_white = Image.open(get_resource_path("logo2.png"))
            self.my_logo = ctk.CTkImage(light_image=logo_black, dark_image=logo_white, size=(40, 45))
            self.logo_label = ctk.CTkLabel(header_f, text=" CRAFTING PRO", image=self.my_logo, compound="left", font=ctk.CTkFont(size=20, weight="bold"), text_color=("black", "white"))
            self.logo_label.pack(anchor="w")
        except:
            self.logo_label = ctk.CTkLabel(header_f, text="CRAFTING PRO", font=ctk.CTkFont(size=22, weight="bold"), text_color=("black", "white"))
            self.logo_label.pack(anchor="w")
            
        control_f = ctk.CTkFrame(self.sidebar_wrapper, fg_color="transparent")
        control_f.pack(fill="x", padx=25, pady=5)
        
        self.theme_var = ctk.BooleanVar(value=self.is_dark)
        self.theme_switch = ctk.CTkSwitch(control_f, text="Dark Mode", variable=self.theme_var, command=self.toggle_theme, progress_color="#3b82f6")
        self.theme_switch.pack(side="left")

        self.mode_toggle_var = ctk.BooleanVar(value=False)
        self.mode_switch = ctk.CTkSwitch(control_f, text="Mode Salvage", variable=self.mode_toggle_var, command=self.toggle_app_mode, progress_color="#9b59b6")
        self.mode_switch.pack(side="right")
        
        btn_frame = ctk.CTkFrame(self.sidebar_wrapper, fg_color="transparent")
        btn_frame.pack(side="bottom", fill="x", padx=20, pady=(0, 20))
        
        self.btn_main_action = ctk.CTkButton(btn_frame, text="Calculate Crafting", command=self.add_to_list, height=45, fg_color="#3b82f6", hover_color="#2563eb", font=ctk.CTkFont(weight="bold"))
        self.btn_main_action.pack(fill="x", pady=(0, 10))
        
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
        
        # FIX LIGHT MODE TAB KIRI
        try: self.tabview._segmented_button.configure(font=ctk.CTkFont(size=13, weight="bold"), text_color=("black", "white"))
        except: pass
        
        self.tab_prod = self.tabview.add("Batch")
        self.tab_rec = self.tabview.add("Recipe")
        self.tab_strat = self.tabview.add("Strategy")
        
        self.create_section_label(self.tab_prod, "MARKET STATUS")
        
        # FIX LIGHT MODE TAB MARKET
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
            text_color=("black", "white"),
            corner_radius=8
        )
        self.method_seg.pack(pady=(5, 10), padx=15, fill="x")
        
        self.premium_var = ctk.BooleanVar(value=self.saved_data.get("premium", True))
        ctk.CTkSwitch(self.tab_prod, text="Premium Status", variable=self.premium_var, progress_color="#f1c40f").pack(pady=5, padx=15, anchor="w")
        
        self.create_section_label(self.tab_prod, "PRODUCTION TARGET")
        
        f_n = ctk.CTkFrame(self.tab_prod, fg_color="transparent"); f_n.pack(fill="x", padx=15, pady=(2, 4))
        self.create_field_label(f_n, "Target Item")
        
        f_n_inner = ctk.CTkFrame(f_n, fg_color="transparent"); f_n_inner.pack(fill="x")
        self.ent_name = ctk.CTkEntry(f_n_inner, height=35, corner_radius=6, border_width=0, fg_color=("#e4e4e4", "#2d3135"), text_color=("#1d4ed8", "#60a5fa"), font=ctk.CTkFont(weight="bold"))
        self.ent_name.insert(0, self.saved_data.get("name", ""))
        self.ent_name.pack(side="left", fill="x", expand=True)
        
        btn_search_target = ctk.CTkButton(f_n_inner, text="Search", width=70, height=35, corner_radius=6, fg_color="#3b82f6", font=ctk.CTkFont(weight="bold"), command=self.open_search_modal)
        btn_search_target.pack(side="right", padx=(5, 0))
        
        self.ent_target, self.ent_out_qty, self.lbl_target_craft, self.lbl_out_qty = self.create_2col_input(self.tab_prod, "Target Craft", "target", "", "Output / Recipe", "out_qty", "")
        
        self.create_section_label(self.tab_prod, "MARKET & FEES")
        self.ent_sell, self.ent_item_val, _, _ = self.create_2col_input(self.tab_prod, "Item Price (Sell/Buy)", "sell_price", "", "Item Value", "item_val", "")

        self.create_section_label(self.tab_rec, "MATERIAL LIST (MANUAL)")
        
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
        
        f_b = ctk.CTkFrame(f_rrr1, fg_color="transparent"); f_b.pack(side="left", fill="x", expand=True, padx=(0, 5)); self.create_field_label(f_b, "Basic"); 
        self.ent_basic = ctk.CTkEntry(f_b, textvariable=self.var_basic, height=35, corner_radius=6, fg_color=("#e4e4e4", "#2d3135"), border_width=0)
        self.ent_basic.pack(fill="x")
        
        f_l = ctk.CTkFrame(f_rrr1, fg_color="transparent"); f_l.pack(side="right", fill="x", expand=True, padx=(5, 0)); self.create_field_label(f_l, "Local"); 
        self.ent_local = ctk.CTkEntry(f_l, textvariable=self.var_local, height=35, corner_radius=6, fg_color=("#e4e4e4", "#2d3135"), border_width=0)
        self.ent_local.pack(fill="x")

        self.f_rrr_row_2 = ctk.CTkFrame(self.tab_strat, fg_color="transparent"); self.f_rrr_row_2.pack(fill="x", padx=15, pady=(2, 4))
        
        f_d = ctk.CTkFrame(self.f_rrr_row_2, fg_color="transparent"); f_d.pack(side="left", fill="x", expand=True, padx=(0, 5)); self.create_field_label(f_d, "Daily"); 
        self.ent_daily = ctk.CTkEntry(f_d, textvariable=self.var_daily, height=35, corner_radius=6, fg_color=("#e4e4e4", "#2d3135"), border_width=0)
        self.ent_daily.pack(fill="x")
        
        self.f_focb = ctk.CTkFrame(self.f_rrr_row_2, fg_color="transparent"); self.create_field_label(self.f_focb, "Focus yield"); 
        self.ent_fb = ctk.CTkEntry(self.f_focb, height=35, corner_radius=6, fg_color=("#cbd4db", "#34495e"), border_width=0)
        self.ent_fb.insert(0, "59"); self.ent_fb.configure(state="readonly"); self.ent_fb.pack(fill="x")

        self.create_section_label(self.tab_strat, "FOCUS & STATION FEE")
        f_st1 = ctk.CTkFrame(self.tab_strat, fg_color="transparent"); f_st1.pack(fill="x", padx=15, pady=(2, 4))
        
        f_fee = ctk.CTkFrame(f_st1, fg_color="transparent"); f_fee.pack(side="left", fill="x", expand=True, padx=(0, 5)); self.create_field_label(f_fee, "Station Fee"); 
        self.ent_fee = ctk.CTkEntry(f_fee, height=35, corner_radius=6, fg_color=("#e4e4e4", "#2d3135"), border_width=0)
        self.ent_fee.insert(0, self.saved_data.get("fee", "")); self.ent_fee.pack(fill="x")
        
        f_rs = ctk.CTkFrame(f_st1, fg_color="transparent"); f_rs.pack(side="right", fill="x", expand=True, padx=(5, 0)); self.create_field_label(f_rs, "Total RRR (%)"); 
        self.ent_rrr = ctk.CTkEntry(f_rs, height=35, corner_radius=6, fg_color=("#e4e4e4", "#2d3135"), text_color=("#1d4ed8", "#60a5fa"), border_width=0, font=ctk.CTkFont(weight="bold"))
        self.ent_rrr.pack(fill="x")
        
        self.frame_focus_toggle = ctk.CTkFrame(self.tab_strat, fg_color="transparent"); self.frame_focus_toggle.pack(fill="x", padx=15, pady=(15, 5))
        self.focus_toggle_var = ctk.BooleanVar(value=self.saved_data.get("focus_toggle", False))
        
        self.switch_focus = ctk.CTkSwitch(self.frame_focus_toggle, text="Craft Pakai Focus?", variable=self.focus_toggle_var, command=self.toggle_focus_mode, progress_color="#9b59b6")
        self.switch_focus.pack(side="left")

        self.frame_focus_inputs = ctk.CTkFrame(self.tab_strat, fg_color="transparent")
        
        f_fcl = ctk.CTkFrame(self.frame_focus_inputs, fg_color="transparent"); f_fcl.pack(side="left", fill="x", expand=True, padx=(0, 5)); self.create_field_label(f_fcl, "Focus Cost / Craft"); 
        self.ent_focus_cost = ctk.CTkEntry(f_fcl, height=35, corner_radius=6, fg_color=("#e4e4e4", "#2d3135"), border_width=0)
        self.ent_focus_cost.insert(0, self.saved_data.get("focus_cost", "")); self.ent_focus_cost.pack(fill="x")
        
        f_fcr = ctk.CTkFrame(self.frame_focus_inputs, fg_color="transparent"); f_fcr.pack(side="right", fill="x", expand=True, padx=(5, 0)); self.create_field_label(f_fcr, "Focus Bank"); 
        self.ent_focus_pool = ctk.CTkEntry(f_fcr, height=35, corner_radius=6, fg_color=("#e4e4e4", "#2d3135"), border_width=0)
        self.ent_focus_pool.insert(0, self.saved_data.get("focus_pool", "")); self.ent_focus_pool.pack(fill="x")
        self.toggle_focus_mode()

        # ===============================================
        # UI KANAN (TABVIEW RESULT BARU)
        # ===============================================
        self.main_container = ctk.CTkFrame(self, fg_color=("#ffffff", "#121416"), corner_radius=0)
        self.main_container.pack(side="right", fill="both", expand=True)
        
        self.result_tabview = ctk.CTkTabview(
            self.main_container, 
            segmented_button_selected_color="#3b82f6", 
            segmented_button_selected_hover_color="#2563eb",
            segmented_button_unselected_color=("#e4e4e4", "#24282c"),
            segmented_button_fg_color=("#e4e4e4", "#24282c"),
            fg_color="transparent", 
            bg_color="transparent",
            corner_radius=10
        )
        self.result_tabview.pack(side="top", fill="both", expand=True, padx=20, pady=10)
        
        # FIX LIGHT MODE TAB KANAN
        try: 
            self.result_tabview._segmented_button.configure(font=ctk.CTkFont(size=14, weight="bold"), text_color=("black", "white"))
        except: pass
        
        self.tab_craft_res = self.result_tabview.add("Crafting Results")
        self.tab_salvage_res = self.result_tabview.add("Salvage Results")
        
        self.crafting_list = ctk.CTkScrollableFrame(self.tab_craft_res, fg_color="transparent")
        self.crafting_list.pack(fill="both", expand=True)
        
        self.salvage_list = ctk.CTkScrollableFrame(self.tab_salvage_res, fg_color="transparent")
        self.salvage_list.pack(fill="both", expand=True)
        
        self.bind_global_scroll(self.main_container, self._scroll_main)
        self.toggle_app_mode()
        self.overlay_frame = ctk.CTkFrame(self, fg_color=("gray60", "#080808"), corner_radius=0)

    def open_search_modal(self):
        self.overlay_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        for child in self.overlay_frame.winfo_children(): child.destroy()
        
        self.search_modal = ItemSearchModal(
            self.overlay_frame, 
            self.universal_db, 
            self.on_target_selected, 
            self.close_search_modal
        )
        self.search_modal.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.7, relheight=0.8)

    def close_search_modal(self):
        self.overlay_frame.place_forget()
        
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
            
            target_name = self.ent_name.get().strip() or "Item"
            item_buy_price = float(self.ent_sell.get() or 0)
            item_value = float(self.ent_item_val.get() or 0)
            
            qty_to_salvage = float(self.ent_target.get() or 1)
            
            if not mats_data:
                silver_from_npc_per_item = item_value * 0.25
                total_silver_from_npc = silver_from_npc_per_item * qty_to_salvage
                total_buy_cost = item_buy_price * qty_to_salvage
                
                profit = total_silver_from_npc - total_buy_cost
                margin = (profit / total_buy_cost) * 100 if total_buy_cost > 0 else 0
                
                res = {
                    'name': f"{target_name} ({qty_to_salvage:.0f}x)",
                    'buy_price': total_buy_cost,
                    'silver_from_npc': total_silver_from_npc,
                    'total_revenue': total_silver_from_npc,
                    'profit': profit,
                    'margin': margin,
                    'is_profitable': profit > 0,
                    'materials_salvaged': [] 
                }
            else:
                res = calculate_salvage_flip(target_name, item_buy_price, item_value, mats_data, self.premium_var.get())
                
                if res and "error" not in res:
                    res['name'] = f"{target_name} ({qty_to_salvage:.0f}x)"
                    res['buy_price'] = res.get('buy_price', 0) * qty_to_salvage
                    res['silver_from_npc'] = res.get('silver_from_npc', 0) * qty_to_salvage
                    res['total_revenue'] = res.get('total_revenue', 0) * qty_to_salvage
                    res['profit'] = res.get('profit', 0) * qty_to_salvage
                    
                    for mat in res.get('materials_salvaged', []):
                        mat['qty_returned'] = mat.get('qty_returned', 0) * qty_to_salvage
                        mat['net_value'] = mat.get('net_value', 0) * qty_to_salvage
            
            if "error" in res:
                print(res["error"])
                return
                
            res['type'] = 'salvage'
            
            self.history.append(res)
            create_salvage_card(self, self.salvage_list, res)
            self.save_current_state() 
            
        except Exception as e:
            print(f"Error Salvage Test: {e}")

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

            res['type'] = 'crafting'

            self.history.append(res)
            create_crafting_card(self, self.crafting_list, res)
            self.save_current_state()
        except Exception as e: 
            print(f"Error di add_to_list: {e}")
    
    def clear_list(self):
        for child in self.crafting_list.winfo_children(): child.destroy()
        for child in self.salvage_list.winfo_children(): child.destroy()
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