# main.py
import customtkinter as ctk
import tkinter as tk
from PIL import Image 
import sys # <-- TAMBAHAN 1: Import sys untuk deteksi OS
import os

# Mengambil fungsi dari file terpisah
from logic_engine import calculate_refining_logic
from data_manager import save_to_json, load_from_json

# <-- TAMBAHAN 2: Fungsi Sakti PyInstaller Asset Bundling -->
def get_resource_path(relative_path):
    """ Dapatkan path absolut ke resource, berfungsi baik untuk dev maupun PyInstaller """
    try:
        # PyInstaller membuat folder temp dan menyimpan path-nya di _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Jika bukan dari exe (sedang di-run dari terminal biasa)
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class AlbionApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.saved_data = load_from_json()
        
        # Theme Setup (Default Dark)
        self.is_dark = self.saved_data.get("dark_mode", True)
        ctk.set_appearance_mode("dark" if self.is_dark else "light")
        ctk.set_default_color_theme("blue")

        self.title("Crafting Master Pro")
        self.minsize(1280, 720) 
        
        # <-- TAMBAHAN 3: Multi-Platform Maximized Window -->
        try:
            if sys.platform == "win32":
                self.state('zoomed') # Native Maximize Windows
            else:
                self.attributes('-zoomed', True) # Native Maximize Linux/Mac
        except Exception:
            # Fallback jika OS tidak support
            self.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")
            
        # <-- TAMBAHAN 4: Gunakan get_resource_path untuk logo -->
        try:
            app_icon = tk.PhotoImage(file=get_resource_path("logo2.png"))
            self.iconphoto(False, app_icon)
        except Exception as e:
            print(f"Gagal memuat ikon aplikasi: {e}")

        self.material_entries = []
        self.history = self.saved_data.get("history", []) 
        
        self.setup_ui()
        self.load_saved_materials()
    
        for res in self.history:
            self.render_expandable_card(res)
            
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
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
        widget.bind("<MouseWheel>", scroll_func); widget.bind("<Button-4>", scroll_func); widget.bind("<Button-5>", scroll_func)
        for child in widget.winfo_children(): self.bind_global_scroll(child, scroll_func)

    def _scroll_sidebar(self, event): self._scroll_handler(event, self.sidebar._parent_canvas)
    def _scroll_main(self, event): self._scroll_handler(event, self.scrollable_list._parent_canvas)

    def create_section_label(self, parent, text):
        ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(size=12, weight="bold"), text_color=("#4a56c4", "#5e6ad2")).pack(pady=(12, 2), padx=25, anchor="w")

    def create_field_label(self, parent, text):
        lbl = ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(size=10), text_color=("#6c757d", "#8e949a")); lbl.pack(anchor="w")

    def create_2col_input(self, parent, label1, key1, def1, label2, key2, def2):
        frame = ctk.CTkFrame(parent, fg_color="transparent"); frame.pack(fill="x", padx=25, pady=(2, 4))
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
            self.frame_focus_inputs.pack(fill="x", padx=25, pady=(2, 4), after=self.frame_focus_toggle)
        else:
            self.f_focb.pack_forget(); self.frame_focus_inputs.pack_forget()
            self.ent_focus_cost.delete(0, tk.END); self.ent_focus_cost.insert(0, "0")
        self.auto_calculate_rrr()

    def setup_ui(self):
        self.sidebar_wrapper = ctk.CTkFrame(self, width=400, fg_color=("#f4f5f7", "#1a1c1e"), corner_radius=0); self.sidebar_wrapper.pack(side="left", fill="y"); self.sidebar_wrapper.pack_propagate(False)
        
        try:
            # <-- TAMBAHAN 5: Gunakan get_resource_path untuk logo -->
            logo_black = Image.open(get_resource_path("logo1.png")) 
            logo_white = Image.open(get_resource_path("logo2.png"))
            
            self.my_logo = ctk.CTkImage(
                light_image=logo_black, 
                dark_image=logo_white, 
                size=(50, 55)
            )
            self.logo_label = ctk.CTkLabel(
                self.sidebar_wrapper, 
                text=" CRAFTING MASTER PRO", 
                image=self.my_logo,
                compound="left",
                font=ctk.CTkFont(size=20, weight="bold"),
                text_color=("black", "white")
            )
            self.logo_label.pack(pady=(20, 5), padx=25, anchor="w")
            
        except Exception as e:
            print(f"Logo error: {e}")
            self.logo_label = ctk.CTkLabel(
                self.sidebar_wrapper, 
                text="CRAFTING MASTER PRO", 
                font=ctk.CTkFont(size=22, weight="bold"), 
                text_color=("black", "white")
            )
            self.logo_label.pack(pady=(20, 5), padx=25, anchor="w")
            
        ctk.CTkFrame(self.sidebar_wrapper, height=2, fg_color=("#d4d4d4", "#2d3135")).pack(fill="x", padx=25, pady=(10, 5))

        self.theme_var = ctk.BooleanVar(value=self.is_dark)
        self.theme_switch = ctk.CTkSwitch(self.sidebar_wrapper, text="Dark Mode", variable=self.theme_var, command=self.toggle_theme, progress_color="#5e6ad2", text_color=("black", "white"))
        self.theme_switch.pack(pady=5, padx=25, anchor="w")

        ctk.CTkFrame(self.sidebar_wrapper, height=2, fg_color=("#d4d4d4", "#2d3135")).pack(fill="x", padx=25, pady=(5, 10))

        self.sidebar = ctk.CTkScrollableFrame(self.sidebar_wrapper, fg_color="transparent", corner_radius=0); self.sidebar.pack(fill="both", expand=True)

        self.premium_var = ctk.BooleanVar(value=self.saved_data.get("premium", True))
        ctk.CTkSwitch(self.sidebar, text="Premium Status (Tax 4%)", variable=self.premium_var, progress_color="#f1c40f", text_color=("black", "white")).pack(pady=(5, 10), padx=25, anchor="w")

        self.create_section_label(self.sidebar, "PRODUCTION BATCH")
        f_n = ctk.CTkFrame(self.sidebar, fg_color="transparent"); f_n.pack(fill="x", padx=25, pady=(2, 4))
        self.create_field_label(f_n, "Item Name"); self.ent_name = ctk.CTkEntry(f_n, height=35, corner_radius=6, fg_color=("#e4e4e4", "#2d3135"), border_width=0); self.ent_name.insert(0, self.saved_data.get("name", "Energy Potion T4")); self.ent_name.pack(fill="x")
        self.ent_target, self.ent_out_qty = self.create_2col_input(self.sidebar, "Target Craft", "target", "999", "Output / Recipe", "out_qty", "1")
        self.create_section_label(self.sidebar, "MARKET & FEES")
        self.ent_sell, self.ent_item_val = self.create_2col_input(self.sidebar, "Sell Price", "sell_price", "1850", "Item Value", "item_val", "64")

        self.create_section_label(self.sidebar, "RECIPE (MAX 5 MATS)")
        h_f = ctk.CTkFrame(self.sidebar, fg_color="transparent"); h_f.pack(fill="x", padx=(25, 27), pady=(0, 2)) 
        ctk.CTkLabel(h_f, text="Material", font=ctk.CTkFont(size=10, weight="bold"), text_color=("#6c757d", "#8e949a"), width=120, anchor="w").pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkLabel(h_f, text="Price", font=ctk.CTkFont(size=10, weight="bold"), text_color=("#6c757d", "#8e949a"), width=65, anchor="w").pack(side="left", padx=(0, 6))
        ctk.CTkLabel(h_f, text="Qty", font=ctk.CTkFont(size=10, weight="bold"), text_color=("#6c757d", "#8e949a"), width=40, anchor="w").pack(side="left", padx=(0, 6))
        ctk.CTkLabel(h_f, text="Ret", font=ctk.CTkFont(size=10, weight="bold"), text_color=("#6c757d", "#8e949a"), width=30, anchor="w").pack(side="left", padx=(0, 2))
        
        self.mats_container = ctk.CTkFrame(self.sidebar, fg_color="transparent"); self.mats_container.pack(fill="x", padx=25, pady=0)

        self.create_section_label(self.sidebar, "RRR CALCULATOR (BONUS YIELD)")
        self.var_basic = tk.StringVar(value=self.saved_data.get("basic", "18")); self.var_local = tk.StringVar(value=self.saved_data.get("local", "40")); self.var_daily = tk.StringVar(value=self.saved_data.get("daily", "0"))
        for v in [self.var_basic, self.var_local, self.var_daily]: v.trace_add("write", self.auto_calculate_rrr)

        f_rrr1 = ctk.CTkFrame(self.sidebar, fg_color="transparent"); f_rrr1.pack(fill="x", padx=25, pady=(2, 4))
        f_b = ctk.CTkFrame(f_rrr1, fg_color="transparent"); f_b.pack(side="left", fill="x", expand=True, padx=(0, 5)); self.create_field_label(f_b, "Basic"); ctk.CTkEntry(f_b, textvariable=self.var_basic, height=35, corner_radius=6, fg_color=("#e4e4e4", "#2d3135"), border_width=0).pack(fill="x")
        f_l = ctk.CTkFrame(f_rrr1, fg_color="transparent"); f_l.pack(side="right", fill="x", expand=True, padx=(5, 0)); self.create_field_label(f_l, "Local"); ctk.CTkEntry(f_l, textvariable=self.var_local, height=35, corner_radius=6, fg_color=("#e4e4e4", "#2d3135"), border_width=0).pack(fill="x")

        self.f_rrr_row_2 = ctk.CTkFrame(self.sidebar, fg_color="transparent"); self.f_rrr_row_2.pack(fill="x", padx=25, pady=(2, 4))
        f_d = ctk.CTkFrame(self.f_rrr_row_2, fg_color="transparent"); f_d.pack(side="left", fill="x", expand=True, padx=(0, 5)); self.create_field_label(f_d, "Daily"); ctk.CTkEntry(f_d, textvariable=self.var_daily, height=35, corner_radius=6, fg_color=("#e4e4e4", "#2d3135"), border_width=0).pack(fill="x")
        self.f_focb = ctk.CTkFrame(self.f_rrr_row_2, fg_color="transparent"); self.create_field_label(self.f_focb, "Focus yield (Auto)"); ent_fb = ctk.CTkEntry(self.f_focb, height=35, corner_radius=6, fg_color=("#cbd4db", "#34495e"), border_width=0); ent_fb.insert(0, "59"); ent_fb.configure(state="readonly"); ent_fb.pack(fill="x")

        self.create_section_label(self.sidebar, "STRATEGY & RESULT")
        f_st1 = ctk.CTkFrame(self.sidebar, fg_color="transparent"); f_st1.pack(fill="x", padx=25, pady=(2, 4))
        f_fee = ctk.CTkFrame(f_st1, fg_color="transparent"); f_fee.pack(side="left", fill="x", expand=True, padx=(0, 5)); self.create_field_label(f_fee, "Station Fee"); self.ent_fee = ctk.CTkEntry(f_fee, height=35, corner_radius=6, fg_color=("#e4e4e4", "#2d3135"), border_width=0); self.ent_fee.insert(0, self.saved_data.get("fee", "320")); self.ent_fee.pack(fill="x")
        f_rs = ctk.CTkFrame(f_st1, fg_color="transparent"); f_rs.pack(side="right", fill="x", expand=True, padx=(5, 0)); self.create_field_label(f_rs, "Result RRR (%) [LOCKED]"); self.ent_rrr = ctk.CTkEntry(f_rs, height=35, corner_radius=6, fg_color=("#5fa0e3", "#1f538d"), text_color="white", border_width=0); self.ent_rrr.pack(fill="x")
        
        self.frame_focus_toggle = ctk.CTkFrame(self.sidebar, fg_color="transparent"); self.frame_focus_toggle.pack(fill="x", padx=25, pady=(15, 5))
        self.focus_toggle_var = ctk.BooleanVar(value=self.saved_data.get("focus_toggle", False))
        ctk.CTkSwitch(self.frame_focus_toggle, text="Craft Pakai Focus?", variable=self.focus_toggle_var, command=self.toggle_focus_mode, progress_color="#9b59b6", text_color=("black", "white")).pack(side="left")

        self.frame_focus_inputs = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        f_fcl = ctk.CTkFrame(self.frame_focus_inputs, fg_color="transparent"); f_fcl.pack(side="left", fill="x", expand=True, padx=(0, 5)); self.create_field_label(f_fcl, "Focus Cost / Craft"); self.ent_focus_cost = ctk.CTkEntry(f_fcl, height=35, corner_radius=6, fg_color=("#e4e4e4", "#2d3135"), border_width=0); self.ent_focus_cost.insert(0, self.saved_data.get("focus_cost", "6602")); self.ent_focus_cost.pack(fill="x")
        f_fcr = ctk.CTkFrame(self.frame_focus_inputs, fg_color="transparent"); f_fcr.pack(side="right", fill="x", expand=True, padx=(5, 0)); self.create_field_label(f_fcr, "Focus Poin Anda (Max 30k)"); self.ent_focus_pool = ctk.CTkEntry(f_fcr, height=35, corner_radius=6, fg_color=("#e4e4e4", "#2d3135"), border_width=0); self.ent_focus_pool.insert(0, self.saved_data.get("focus_pool", "30000")); self.ent_focus_pool.pack(fill="x")

        self.toggle_focus_mode()
        ctk.CTkButton(self.sidebar, text="Calculate & Add", command=self.add_to_list, height=40, fg_color="#5e6ad2", font=ctk.CTkFont(weight="bold")).pack(pady=(20, 5), padx=25, fill="x")
        ctk.CTkButton(self.sidebar, text="Clear List", fg_color="transparent", text_color=("#6c757d", "#8e949a"), command=self.clear_list).pack(pady=(0, 10), padx=25, fill="x")

        self.main_container = ctk.CTkFrame(self, fg_color=("#ffffff", "#121416"), corner_radius=0); self.main_container.pack(side="right", fill="both", expand=True)
        
        self.h_res = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.h_res.pack(side="top", fill="x", padx=30, pady=(20, 5))
        ctk.CTkLabel(self.h_res, text="Market Analysis Result", font=ctk.CTkFont(size=24, weight="bold"), text_color=("black", "white")).pack(side="left")
        
        self.scrollable_list = ctk.CTkScrollableFrame(self.main_container, fg_color="transparent")
        self.scrollable_list.pack(side="top", fill="both", expand=True, padx=25, pady=0)
        
        self.bind_global_scroll(self.sidebar_wrapper, self._scroll_sidebar)
        self.bind_global_scroll(self.main_container, self._scroll_main)

    def add_static_material_row(self, name_val="", price_val="", qty_val="", is_ret=True):
        row = ctk.CTkFrame(self.mats_container, fg_color="transparent"); row.pack(fill="x", padx=0, pady=2)
        ent_n = ctk.CTkEntry(row, height=35, corner_radius=4, fg_color=("#e4e4e4", "#2d3135"), border_width=0); ent_n.pack(side="left", fill="x", expand=True, padx=(0, 6)); ent_n.insert(0, name_val)
        ent_p = ctk.CTkEntry(row, height=35, width=65, corner_radius=4, fg_color=("#e4e4e4", "#2d3135"), border_width=0); ent_p.pack(side="left", padx=(0, 6)); ent_p.insert(0, price_val)
        ent_q = ctk.CTkEntry(row, height=35, width=40, corner_radius=4, fg_color=("#e4e4e4", "#2d3135"), border_width=0); ent_q.pack(side="left", padx=(0, 6)); ent_q.insert(0, qty_val)
        
        ret_var = ctk.BooleanVar(value=is_ret)
        chk = ctk.CTkCheckBox(row, text="", variable=ret_var, width=20, checkbox_width=20, checkbox_height=20, fg_color="#5e6ad2", hover_color="#4854b5")
        chk.pack(side="left", padx=(5, 0))
        
        self.material_entries.append({"name": ent_n, "price": ent_p, "qty": ent_q, "is_ret": ret_var})
        self.bind_global_scroll(row, self._scroll_sidebar)

    def load_saved_materials(self):
        saved_mats = self.saved_data.get("materials", [])
        for i in range(5):
            if i < len(saved_mats):
                m = saved_mats[i]
                self.add_static_material_row(m.get("name", ""), m.get("price", ""), m.get("qty", ""), m.get("is_ret", True))
            else:
                self.add_static_material_row("", "", "", True)

    def add_to_list(self):
        try:
            mats_data = []
            for mat in self.material_entries:
                p_str = mat['price'].get().strip()
                q_str = mat['qty'].get().strip()
                if p_str and q_str:
                    try:
                        p_val = float(p_str)
                        q_val = float(q_str)
                        if p_val > 0 and q_val > 0:
                            mats_data.append({"name": mat['name'].get().strip() or f"Mat {len(mats_data)+1}", "price": p_val, "qty": q_val, "is_return": mat['is_ret'].get()})
                    except ValueError: pass
                        
            if not mats_data: return 
            res = calculate_refining_logic(self.ent_name.get(), mats_data, float(self.ent_target.get()), float(self.ent_out_qty.get()), float(self.ent_sell.get()), float(self.ent_item_val.get()), float(self.ent_fee.get()), float(self.ent_rrr.get()), self.premium_var.get(), self.focus_toggle_var.get(), float(self.ent_focus_cost.get() or 0), float(self.ent_focus_pool.get() or 30000))
            
            self.history.append(res) 
            self.render_expandable_card(res)
            self.save_current_state()
        except Exception as e: print(e)

    def render_expandable_card(self, res):
        card = ctk.CTkFrame(self.scrollable_list, corner_radius=8, fg_color=("#f4f5f7", "#1a1c1e"))
        card.pack(pady=5, padx=10, fill="x") 

        status_color = "#2ecc71" if res['is_profitable'] else "#e74c3c"
        ctk.CTkFrame(card, width=4, height=0, corner_radius=2, fg_color=status_color).pack(side="left", fill="y", padx=(10, 0), pady=10)
        
        c_w = ctk.CTkFrame(card, fg_color="transparent")
        c_w.pack(side="left", fill="x", expand=True, padx=20, pady=12) 
        
        h_f = ctk.CTkFrame(c_w, fg_color="transparent") 
        h_f.pack(fill="x")
        
        i_l = ctk.CTkFrame(h_f, fg_color="transparent")
        i_l.pack(side="left")
        
        tax_info = "(Premium Tax)" if res['is_premium'] else "(Normal Tax)"
        title_text = f"{res['name'].upper()} ➔ CRAFTABLE ITEM: {res['actual_craft']:,}  {tax_info}"
        
        ctk.CTkLabel(i_l, text=title_text, font=ctk.CTkFont(size=15, weight="bold"), text_color=("black", "white")).pack(anchor="w")
        ctk.CTkLabel(i_l, text=f"Total Profit: Rp {res['total_profit']:+,.0f}  |  Margin: {res['margin']:.2f}%", font=ctk.CTkFont(size=12), text_color=status_color).pack(anchor="w", pady=(2, 0))
        
        def remove_card():
            if res in self.history:
                self.history.remove(res)
                self.save_current_state()
            card.destroy()
            
        ctk.CTkButton(h_f, text="✕", font=ctk.CTkFont(size=14, weight="bold"), width=30, height=30, corner_radius=6, fg_color="transparent", text_color=("#888888", "#5a5e63"), hover_color="#ff4d4d", command=remove_card).pack(side="right", padx=(5, 0))
        
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

        btn_t = ctk.CTkButton(h_f, text="Detail ▼", width=60, height=28, font=ctk.CTkFont(size=11), fg_color=("#e4e4e4", "#2d3135"), hover_color=("#c0c0c0", "#3e4348"), text_color=("black", "white"), command=toggle)
        btn_t.pack(side="right")
        
        t_dash = ctk.CTkFrame(det_f, fg_color="transparent")
        t_dash.pack(fill="x", pady=(5, 10))
        
        header_f = ctk.CTkFrame(t_dash, fg_color="transparent")
        header_f.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(header_f, text="Parameter Info", font=ctk.CTkFont(weight="bold", size=12), width=130, anchor="w", text_color=("#6c757d", "#8e949a")).pack(side="left")
        
        for i in range(5):
            if i < len(res['buy_list']) and res['buy_list'][i]['req_q'] > 0:
                ret_status = "RETURN" if res['buy_list'][i]['is_ret'] else "NON-RET"
                col_color = "#3498db" if res['buy_list'][i]['is_ret'] else "#e74c3c"
                ctk.CTkLabel(header_f, text=f"Mat {i+1} ({ret_status})", font=ctk.CTkFont(weight="bold", size=11), width=100, text_color=col_color, anchor="w").pack(side="left", padx=8)
            else:
                ctk.CTkLabel(header_f, text=f"Material {i+1}", font=ctk.CTkFont(weight="bold", size=11), width=100, text_color=("#adb5bd", "#5a5e63"), anchor="w").pack(side="left", padx=8)
            
        ctk.CTkFrame(t_dash, height=2, fg_color=("#d4d4d4", "#2d3135")).pack(fill="x", pady=(0, 8)) 

        def create_card_dash_row(label_text, value_key, is_money=False, highlight=False):
            row_f = ctk.CTkFrame(t_dash, fg_color="transparent")
            row_f.pack(fill="x", pady=4) 
            lbl_color = ("black", "white") if highlight else ("#495057", "#bdc3c7")
            ctk.CTkLabel(row_f, text=label_text, font=ctk.CTkFont(size=12, weight="bold" if highlight else "normal"), width=130, anchor="w", text_color=lbl_color).pack(side="left")
            
            for i in range(5):
                val = 0
                if i < len(res['buy_list']) and res['buy_list'][i]['req_q'] > 0:
                    mat = res['buy_list'][i]
                    if value_key == 'buy': val = mat['qty']
                    elif value_key == 'need': val = mat['req_q']
                    elif value_key == 'price': val = mat['price']
                    elif value_key == 'eff': val = mat['eff_stock']
                    elif value_key == 'craft': val = mat['craftable_m']
                    elif value_key == 'return': val = mat['sisa']
                
                txt_val = f"Rp {val:,.0f}" if is_money else f"{val:,.0f}"
                if val == 0 and not is_money: txt_val = "0"
                val_color = "#f1c40f" if highlight and val != 0 else ("#adb5bd", "#5a5e63") if val == 0 else ("black", "white")
                ctk.CTkLabel(row_f, text=txt_val, font=ctk.CTkFont(size=12, weight="bold" if highlight else "normal"), width=100, anchor="w", text_color=val_color).pack(side="left", padx=8)

        create_card_dash_row("Material To Buy", "buy", highlight=True)
        create_card_dash_row("Material Needed", "need")
        create_card_dash_row("Material Price", "price", is_money=True)
        create_card_dash_row("Effective Stock", "eff")
        create_card_dash_row("Craftable Item", "craft")
        create_card_dash_row("Sisa Material", "return")
        
        ctk.CTkFrame(det_f, height=2, fg_color=("#b8b8b8", "#3e4348")).pack(fill="x", pady=(15, 15)) 

        b_c = ctk.CTkFrame(det_f, fg_color="transparent")
        b_c.pack(fill="x", padx=5) 
        
        l_c = ctk.CTkFrame(b_c, fg_color="transparent")
        l_c.pack(side="left", fill="both", expand=True, padx=(0, 20)) 
    
        costs = [("Fee / Recipe", f"Rp {res['fee_per_recipe']:,.0f}", ("#6c757d", "#8e949a")), ("Gross Mat Cost", f"Rp {res['total_mats_cost']:,.0f}", ("#495057", "#bdc3c7")), ("Mat Return (Sisa)", f"- Rp {res['material_return_val']:,.0f}", "#2ecc71"), ("Net Mat Cost Total", f"Rp {res['net_mat_cost']:,.0f}", "#e67e22"), ("Craft Fee Total", f"Rp {res['total_fee']:,.0f}", ("#495057", "#bdc3c7")), ("Total Prod. Cost", f"Rp {res['total_cost']:,.0f}", ("black", "white")), ("Cost per Item", f"Rp {res['cost_per_item']:,.0f}", "#3498db")]
        for l, v, c in costs:
            rf = ctk.CTkFrame(l_c, fg_color="transparent"); rf.pack(fill="x", pady=4) 
            ctk.CTkLabel(rf, text=l, font=ctk.CTkFont(size=12), text_color=("#6c757d", "#8e949a")).pack(side="left")
            ctk.CTkLabel(rf, text=v, font=ctk.CTkFont(size=12, weight="bold"), text_color=c).pack(side="right")
            
        if res.get('total_focus', 0) > 0:
            ctk.CTkFrame(l_c, height=2, fg_color=("#d4d4d4", "#2d3135")).pack(fill="x", pady=(8, 8))
            f_costs = [("Total Focus Dipakai", f"{res['total_focus']:,.0f}", "#9b59b6"), ("Sisa Focus di Bank", f"{res['foc_sisa_point']:,.0f}", "#9b59b6"), ("Maks. Craft Pakai Focus", f"{res['foc_can_craft']:,.0f}x Klik", "#9b59b6"), ("Hasil Jadi (Focus Mode)", f"{res['foc_item_yield']:,.0f} Item", "#9b59b6")]
            for l, v, c in f_costs:
                rf = ctk.CTkFrame(l_c, fg_color="transparent"); rf.pack(fill="x", pady=3)
                ctk.CTkLabel(rf, text=l, font=ctk.CTkFont(size=12), text_color=("#6c757d", "#8e949a")).pack(side="left")
                ctk.CTkLabel(rf, text=v, font=ctk.CTkFont(size=12, weight="bold"), text_color=c).pack(side="right")

        ctk.CTkFrame(b_c, width=2, fg_color=("#b8b8b8", "#3e4348")).pack(side="left", fill="y", pady=10) 
        r_c = ctk.CTkFrame(b_c, fg_color="transparent") 
        r_c.pack(side="left", fill="both", expand=True, padx=(20, 0)) 
        ctk.CTkLabel(r_c, text="SRP & Profit Tiers", font=ctk.CTkFont(size=13, weight="bold"), text_color=("#4a56c4", "#5e6ad2")).pack(anchor="center", pady=(0, 15)) 
        th = ctk.CTkFrame(r_c, fg_color="transparent"); th.pack(fill="x", padx=5)
        ctk.CTkLabel(th, text="Margin", width=60, font=ctk.CTkFont(size=11, weight="bold"), text_color=("#6c757d", "#8e949a"), anchor="w").pack(side="left")
        ctk.CTkLabel(th, text="Jual di Harga", width=100, font=ctk.CTkFont(size=11, weight="bold"), text_color=("#6c757d", "#8e949a"), anchor="w").pack(side="left")
        ctk.CTkLabel(th, text="Total Profit", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#6c757d", "#8e949a"), anchor="e").pack(side="right")
        ctk.CTkFrame(r_c, height=2, fg_color=("#b8b8b8", "#3e4348")).pack(fill="x", pady=(6, 6)) 
        for m in ["5", "10", "15", "20"]:
            tr = ctk.CTkFrame(r_c, fg_color="transparent"); tr.pack(fill="x", pady=6, padx=5) 
            ctk.CTkLabel(tr, text=f"{m}%", width=60, font=ctk.CTkFont(size=12), text_color=("#6c757d", "#8e949a"), anchor="w").pack(side="left")
            ctk.CTkLabel(tr, text=f"Rp {res['srp'][m]:,.0f}", width=100, font=ctk.CTkFont(size=12, weight="bold"), text_color="#e67e22", anchor="w").pack(side="left")
            ctk.CTkLabel(tr, text=f"Rp {res['profit_tiers'][m]:,.0f}", font=ctk.CTkFont(size=12, weight="bold"), text_color="#2ecc71", anchor="e").pack(side="right")
        ctk.CTkFrame(r_c, height=2, fg_color=("#b8b8b8", "#3e4348")).pack(fill="x", pady=(12, 8)) 
        af = ctk.CTkFrame(r_c, fg_color="transparent"); af.pack(fill="x", padx=5, pady=4)
        ctk.CTkLabel(af, text="Harga Market", font=ctk.CTkFont(size=12), text_color=("#6c757d", "#8e949a")).pack(side="left")
        ctk.CTkLabel(af, text=f"Rp {res['sell_price']:,.0f}", font=ctk.CTkFont(size=12, weight="bold"), text_color=("black", "white")).pack(side="right")
        af2 = ctk.CTkFrame(r_c, fg_color="transparent"); af2.pack(fill="x", padx=5, pady=(4, 15)) 
        ctk.CTkLabel(af2, text="Profit / Item", font=ctk.CTkFont(size=12), text_color=("#6c757d", "#8e949a")).pack(side="left")
        ctk.CTkLabel(af2, text=f"Rp {res['profit_per_pc']:+,.0f}", font=ctk.CTkFont(size=13, weight="bold"), text_color=status_color).pack(side="right")

        self.bind_global_scroll(card, self._scroll_main)

    def clear_list(self):
        for child in self.scrollable_list.winfo_children(): child.destroy()
        self.history.clear()
        self.save_current_state()

    def save_current_state(self):
        saved_mats = []
        for mat in self.material_entries:
            p, q = mat['price'].get().strip(), mat['qty'].get().strip()
            if p and q: saved_mats.append({"name": mat['name'].get().strip(), "price": p, "qty": q, "is_ret": mat['is_ret'].get()})
        save_to_json({"name": self.ent_name.get(), "target": self.ent_target.get(), "out_qty": self.ent_out_qty.get(), "premium": self.premium_var.get(), "sell_price": self.ent_sell.get(), "item_val": self.ent_item_val.get(), "fee": self.ent_fee.get(), "rrr_manual": self.ent_rrr.get(), "focus_cost": self.ent_focus_cost.get(), "focus_pool": self.ent_focus_pool.get(), "focus_toggle": self.focus_toggle_var.get(), "basic": self.var_basic.get(), "local": self.var_local.get(), "daily": self.var_daily.get(), "dark_mode": self.theme_var.get(), "materials": saved_mats, "history": self.history})

        
if __name__ == "__main__":
    app = AlbionApp(); app.mainloop()