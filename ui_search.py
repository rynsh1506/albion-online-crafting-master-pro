import customtkinter as ctk
import tkinter as tk
from config_utils import get_item_image
import db_manager

# ==========================================
# FUNGSI UTILITAS
# ==========================================
def clean_name(text):
    if not text: return "Item"
    prefixes = [
        "Beginner's ", "Novice's ", "Journeyman's ", 
        "Adept's ", "Expert's ", "Master's ", 
        "Grandmaster's ", "Elder's "
    ]
    for p in prefixes:
        if text.startswith(p):
            return text.replace(p, "", 1)
    return text

# ==========================================
# KOMPONEN MODAL SEARCH
# ==========================================
class ItemSearchModal(ctk.CTkFrame):
    def __init__(self, parent, universal_db, on_select_callback, close_callback):
        super().__init__(parent, fg_color=("#ffffff", "#1a1c1e"), corner_radius=20, border_width=2, border_color=("#e0e0e0", "#2d3135"))
        
        self.universal_db = universal_db
        self.on_select_callback = on_select_callback
        self.close_callback = close_callback
        
        self.ITEMS_PER_PAGE = 8 
        self.current_page = 1
        self.filtered_data = []
        self.search_timer = None 

        self.setup_ui()
        self.apply_filters()

        self.after(100, self._bind_mousewheel)

    # --- SCROLL HANDLERS ---
    def _bind_mousewheel(self):
        try:
            root = self.winfo_toplevel()
            root.bind_all("<MouseWheel>", self._on_mousewheel)
            root.bind_all("<Button-4>", self._on_mousewheel) 
            root.bind_all("<Button-5>", self._on_mousewheel) 
        except: pass

    def _on_mousewheel(self, event):
        if not self.winfo_exists(): return
        try:
            if event.num == 4 or (hasattr(event, 'delta') and event.delta > 0):
                self.list_bg._parent_canvas.yview_scroll(-1, "units")
            elif event.num == 5 or (hasattr(event, 'delta') and event.delta < 0):
                self.list_bg._parent_canvas.yview_scroll(1, "units")
        except: pass

    # --- UI SETUP ---
    def setup_ui(self):
        # Header Section
        header_f = ctk.CTkFrame(self, fg_color="transparent")
        header_f.pack(fill="x", padx=25, pady=(25, 10))
        
        ctk.CTkLabel(header_f, text="Marketplace Search", font=ctk.CTkFont(size=24, weight="bold"), 
                     text_color=("#1d4ed8", "#60a5fa")).pack(side="left")
        
        self.btn_close = ctk.CTkButton(header_f, text="✕", width=35, height=35, fg_color="transparent", 
                                      text_color=("#888888", "#5a5e63"), hover_color="#e74c3c", 
                                      font=ctk.CTkFont(size=20, weight="bold"), command=self.close_and_unbind)
        self.btn_close.pack(side="right")
        
        # Filter Control Section
        filter_f = ctk.CTkFrame(self, fg_color="transparent")
        filter_f.pack(fill="x", padx=20, pady=5)

        self.search_var = tk.StringVar()
        # DEBOUNCE IS BACK! 
        self.search_var.trace_add("write", self.debounce_filter)
        
        # FIX LIGHT MODE ENTRY: Tambah text_color & placeholder_text_color
        self.search_entry = ctk.CTkEntry(filter_f, textvariable=self.search_var, placeholder_text="Search items (Sword, Map, Fiber...)", 
                                        height=45, border_width=1, border_color=("#c1c5cb", "#33373b"), fg_color=("#ffffff", "#121416"), 
                                        text_color=("black", "white"), placeholder_text_color=("gray40", "gray60"), corner_radius=12)
        self.search_entry.pack(fill="x", padx=5, pady=(0, 15))

        control_row = ctk.CTkFrame(filter_f, fg_color="transparent")
        control_row.pack(fill="x")

        seg_style = {
            "height": 36,
            "corner_radius": 8,
            "font": ctk.CTkFont(weight="bold", size=12),
            "text_color": ("black", "white"),
            "fg_color": ("#e5e7eb", "#16181a"),           # Warna Latar Track
            "unselected_color": ("#e5e7eb", "#16181a"),   # SAMA dengan Track biar menyatu
            "selected_color": "#3b82f6",                  # Biru solid pas dipilih
            "selected_hover_color": "#2563eb",
            "unselected_hover_color": ("#d1d5db", "#2d3135") # Efek hover tipis
        }

        self.tier_var = ctk.StringVar(value="All")
        self.seg_tier = ctk.CTkSegmentedButton(
            control_row, 
            values=["All", "T2", "T3", "T4", "T5", "T6", "T7", "T8"],
            variable=self.tier_var, 
            command=self.debounce_filter, 
            **seg_style # Langsung inject style di sini
        )
        self.seg_tier.pack(side="left", padx=5)

        self.ench_var = ctk.StringVar(value="All")
        self.seg_ench = ctk.CTkSegmentedButton(
            control_row, 
            values=["All", ".0", ".1", ".2", ".3", ".4"],
            variable=self.ench_var, 
            command=self.debounce_filter, 
            **seg_style # Inject style yang sama
        )
        self.seg_ench.pack(side="left", padx=5)

        # Tombol Reset disesuaiin warnanya biar seirama
        ctk.CTkButton(control_row, text="↺ Reset", width=80, height=36, corner_radius=8, 
                     fg_color=("#e5e7eb", "#16181a"), text_color=("black", "white"), 
                     hover_color=("#d1d5db", "#e74c3c"), font=ctk.CTkFont(weight="bold"),
                     command=self.reset_all_filters).pack(side="right", padx=5)


        # List Area Section
        self.list_bg = ctk.CTkScrollableFrame(self, fg_color=("#f3f4f6", "#0d0d0d"), corner_radius=15, border_width=0)
        self.list_bg.pack(fill="both", expand=True, padx=20, pady=15)
        
        # Pagination Section
        page_frame = ctk.CTkFrame(self, fg_color="transparent")
        page_frame.pack(fill="x", padx=25, pady=(0, 25))

        self.btn_prev = ctk.CTkButton(page_frame, text="◀ Previous", command=self.prev_page, width=100, height=35, corner_radius=8,
                                     fg_color=("#e4e4e4", "#2d3135"), text_color=("black", "white"), hover_color="#3b82f6")
        self.btn_prev.pack(side="left")

        self.lbl_page = ctk.CTkLabel(page_frame, text="Page 1", font=ctk.CTkFont(weight="bold", size=14), text_color=("black", "white"))
        self.lbl_page.pack(side="left", expand=True)

        self.btn_next = ctk.CTkButton(page_frame, text="Next ▶", command=self.next_page, width=100, height=35, corner_radius=8,
                                     fg_color=("#e4e4e4", "#2d3135"), text_color=("black", "white"), hover_color="#3b82f6")
        self.btn_next.pack(side="right")
        
        self.search_entry.focus()

    # --- FILTER LOGIC ---
    def debounce_filter(self, *args):
        if self.search_timer: 
            self.after_cancel(self.search_timer)
        self.search_timer = self.after(250, self.apply_filters)

    def reset_all_filters(self):
        self.search_var.set("")
        self.tier_var.set("All")
        self.ench_var.set("All")
        self.apply_filters()

    def apply_filters(self):
        self.current_page = 1
        query = self.search_var.get().strip()
        tier_f = self.tier_var.get()
        ench_f = self.ench_var.get()

        results = db_manager.search_items_db(query, tier_f, ench_f)
        self.filtered_data = results 
        self.render_page()

    # --- RENDERING DATA ---
    def render_page(self):
        for widget in self.list_bg.winfo_children(): widget.destroy()
        
        total_items = len(self.filtered_data)
        total_pages = max(1, (total_items + self.ITEMS_PER_PAGE - 1) // self.ITEMS_PER_PAGE)
        
        start_idx = (self.current_page - 1) * self.ITEMS_PER_PAGE
        page_items = self.filtered_data[start_idx : start_idx + self.ITEMS_PER_PAGE]

        if not page_items:
            ctk.CTkLabel(self.list_bg, text="No items found. Try different filters!", text_color="#8e949a").pack(pady=50)
        else:
            for row in page_items:
                raw_name, item_id, item_tier, item_val = row
                display_name = clean_name(raw_name)
                
                card = ctk.CTkFrame(self.list_bg, fg_color=("#ffffff", "#16181a"), corner_radius=12, border_width=1, border_color=("#e5e7eb", "#2d3135"))
                card.pack(fill="x", pady=5, padx=10)
                
                img = get_item_image(item_id, size=45)
                ctk.CTkLabel(card, text="", image=img, width=50).pack(side="left", padx=15, pady=10)
                
                info = ctk.CTkFrame(card, fg_color="transparent")
                info.pack(side="left", fill="both", expand=True)
                # FIX LIGHT MODE TEXT DI CARD
                ctk.CTkLabel(info, text=display_name, font=ctk.CTkFont(size=15, weight="bold"), text_color=("black", "white"), anchor="w").pack(fill="x", pady=(10,0))
                
                try: iv_formatted = f"{float(item_val):,.0f}"
                except: iv_formatted = "0"
                
                ctk.CTkLabel(info, text=f"Tier {item_tier}  |  Item Value: {iv_formatted}", 
                             font=ctk.CTkFont(size=12), text_color="#8e949a", anchor="w").pack(fill="x", pady=(0,10))
                
                ctk.CTkButton(card, text="Pilih", width=85, height=35, corner_radius=8, font=ctk.CTkFont(weight="bold"),
                              text_color="white", command=lambda n=raw_name: self.select_item(n)).pack(side="right", padx=20)

        self.lbl_page.configure(text=f"Page {self.current_page} of {total_pages}")
        self.btn_prev.configure(state="normal" if self.current_page > 1 else "disabled")
        self.btn_next.configure(state="normal" if self.current_page < total_pages else "disabled")

    # --- NAVIGATION & CLEANUP ---
    def prev_page(self):
        if self.current_page > 1: self.current_page -= 1; self.render_page()

    def next_page(self):
        if self.current_page < (len(self.filtered_data) + self.ITEMS_PER_PAGE - 1) // self.ITEMS_PER_PAGE:
            self.current_page += 1; self.render_page()

    def select_item(self, item_name):
        self.on_select_callback(item_name)
        self.close_and_unbind()

    def close_and_unbind(self):
        try:
            root = self.winfo_toplevel()
            root.unbind_all("<MouseWheel>")
            root.unbind_all("<Button-4>")
            root.unbind_all("<Button-5>")
        except: pass
        self.close_callback()