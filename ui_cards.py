import customtkinter as ctk
import tkinter as tk

def create_salvage_card(app, parent_frame, res):
    card = ctk.CTkFrame(parent_frame, corner_radius=8, fg_color=("#f4f5f7", "#1a1c1e"))
    card.pack(pady=5, padx=10, fill="x") 
    
    status_color = "#2ecc71" if res.get('is_profitable', False) else "#e74c3c"
    
    ctk.CTkFrame(card, width=4, height=0, corner_radius=2, fg_color=status_color).pack(side="left", fill="y", padx=(10, 0), pady=10)
    
    c_w = ctk.CTkFrame(card, fg_color="transparent")
    c_w.pack(side="left", fill="x", expand=True, padx=20, pady=12) 
    
    h_f = ctk.CTkFrame(c_w, fg_color="transparent")
    h_f.pack(fill="x")
    
    i_l = ctk.CTkFrame(h_f, fg_color="transparent")
    # FIX: Biar judul ngembang dan nggak kepotong
    i_l.pack(side="left", fill="x", expand=True) 
    
    # FIX: Tambahin wraplength biar kalau judul kepanjangan dia turun ke bawah, ga nembus layar
    ctk.CTkLabel(i_l, text=f"🛠️ SALVAGE: {res.get('name', 'Item').upper()}", font=ctk.CTkFont(size=14, weight="bold"), wraplength=450, justify="left").pack(anchor="w")
    
    profit_val = res.get('profit', 0)
    ctk.CTkLabel(i_l, text=f"Salvage Profit: Rp {profit_val:+,.0f}  |  Margin: {res.get('margin', 0):.1f}%", font=ctk.CTkFont(size=12, weight="bold"), text_color=status_color).pack(anchor="w", pady=(2, 0))
    
    btn_frame = ctk.CTkFrame(h_f, fg_color="transparent")
    btn_frame.pack(side="right", padx=(10, 0))
    
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
            app.bind_global_scroll(det_f, app._scroll_main)
            
    btn_t = ctk.CTkButton(btn_frame, text="Detail ▼", width=60, height=28, font=ctk.CTkFont(size=11), fg_color=("#e4e4e4", "#2d3135"), hover_color=("#c0c0c0", "#3e4348"), text_color=("black", "white"), command=toggle)
    btn_t.pack(side="left", padx=(0, 5))
    
    def remove_card():
        if res in app.history: 
            app.history.remove(res)
            app.save_current_state()
        card.destroy()
        
    ctk.CTkButton(btn_frame, text="✕", font=ctk.CTkFont(size=14, weight="bold"), width=30, height=30, corner_radius=6, fg_color="transparent", text_color=("#888888", "#5a5e63"), hover_color="#ff4d4d", command=remove_card).pack(side="left")

    ctk.CTkFrame(det_f, height=2, fg_color=("#d4d4d4", "#2d3135")).pack(fill="x", pady=(10, 10))

    total_mats_revenue = 0
    if res.get('materials_salvaged'):
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
            
        for row_idx, mat in enumerate(res.get('materials_salvaged', []), start=1):
            # FIX: Nama material ga disunat lagi
            mat_name = mat['name']
            
            # FIX: Pake wraplength biar teks ga nabrak kalau nama item panjang banget
            ctk.CTkLabel(table_f, text=mat_name, font=ctk.CTkFont(size=11, weight="bold"), text_color="#3498db", anchor="w", justify="left", wraplength=200).grid(row=row_idx, column=0, sticky="ew", padx=5, pady=4)
            ctk.CTkLabel(table_f, text=f"{mat['qty_returned']:,.0f}", font=ctk.CTkFont(size=12, weight="bold"), anchor="e").grid(row=row_idx, column=1, sticky="ew", padx=5)
            ctk.CTkLabel(table_f, text=f"Rp {mat.get('unit_price', 0):,.0f}", font=ctk.CTkFont(size=11), text_color=("#adb5bd", "#5a5e63"), anchor="e").grid(row=row_idx, column=2, sticky="ew", padx=5)
            ctk.CTkLabel(table_f, text=f"Rp {mat['net_value']:,.0f}", font=ctk.CTkFont(size=12, weight="bold"), text_color="#f1c40f", anchor="e").grid(row=row_idx, column=3, sticky="ew", padx=5)
            
            total_mats_revenue += mat['net_value']

        ctk.CTkFrame(det_f, height=2, fg_color=("#d4d4d4", "#2d3135")).pack(fill="x", pady=(10, 15))

    b_c = ctk.CTkFrame(det_f, fg_color="transparent")
    b_c.pack(fill="x", padx=5)
    
    l_c = ctk.CTkFrame(b_c, fg_color="transparent")
    l_c.pack(side="left", fill="both", expand=True, padx=(0, 10))
    
    # FIX: Ganti sistem dari Pack() jadi Grid() biar angka ga kedorong keluar batas
    def add_fin_row(parent, label, val, is_bold=False, color=None):
        rf = ctk.CTkFrame(parent, fg_color="transparent")
        rf.pack(fill="x", pady=4)
        rf.grid_columnconfigure(0, weight=1)
        rf.grid_columnconfigure(1, weight=0)
        
        fnt = ctk.CTkFont(size=12, weight="bold" if is_bold else "normal")
        c = color if color else ("black", "white")
        lbl_c = ("#6c757d", "#8e949a") if not is_bold else ("black", "white")
        
        ctk.CTkLabel(rf, text=label, font=ctk.CTkFont(size=12), text_color=lbl_c).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(rf, text=val, font=fnt, text_color=c).grid(row=0, column=1, sticky="e")

    add_fin_row(l_c, "Harga Beli Rongsok", f"Rp {res.get('buy_price', 0):,.0f}", True, "#e74c3c")
    add_fin_row(l_c, "Silver Refund NPC", f"Rp {res.get('silver_from_npc', 0):,.0f}", False, "#3498db")
    if res.get('materials_salvaged'):
        add_fin_row(l_c, "Jual Material ke Market", f"Rp {total_mats_revenue:,.0f}", False, "#3498db")
    
    r_c = ctk.CTkFrame(b_c, fg_color="transparent")
    r_c.pack(side="right", fill="both", expand=True, padx=(10, 0))
    
    add_fin_row(r_c, "Total Uang Kembali", f"Rp {res.get('total_revenue', 0):,.0f}", True, "#3498db")
    add_fin_row(r_c, "Salvage Profit", f"Rp {res.get('profit', 0):,.0f}", True, status_color)

    app.bind_global_scroll(card, app._scroll_main)


def create_crafting_card(app, parent_frame, res):
    card = ctk.CTkFrame(parent_frame, corner_radius=8, fg_color=("#f4f5f7", "#1a1c1e"))
    card.pack(pady=5, padx=10, fill="x") 
    
    status_color = "#2ecc71" if res.get('is_profitable', False) else "#e74c3c"
    
    ctk.CTkFrame(card, width=4, height=0, corner_radius=2, fg_color=status_color).pack(side="left", fill="y", padx=(10, 0), pady=10)
    
    c_w = ctk.CTkFrame(card, fg_color="transparent")
    c_w.pack(side="left", fill="x", expand=True, padx=20, pady=12) 
    
    h_f = ctk.CTkFrame(c_w, fg_color="transparent")
    h_f.pack(fill="x")
    
    i_l = ctk.CTkFrame(h_f, fg_color="transparent")
    i_l.pack(side="left", fill="x", expand=True) # Dikasih expand biar lega
    
    title_text = f"{res.get('name', 'Item').upper()}  |  TOTAL OUTPUT: {res.get('total_produced', 0):,} ITEM"
    ctk.CTkLabel(i_l, text=title_text, font=ctk.CTkFont(size=14, weight="bold"), wraplength=450, justify="left").pack(anchor="w")
    
    profit_val = res.get('real_profit', 0)
    ctk.CTkLabel(i_l, text=f"Total Profit: Rp {profit_val:+,.0f}  |  Margin: {res.get('margin', 0):.1f}%", 
                 font=ctk.CTkFont(size=12, weight="bold"), text_color=status_color).pack(anchor="w", pady=(2, 0))
    
    btn_frame = ctk.CTkFrame(h_f, fg_color="transparent")
    btn_frame.pack(side="right", padx=(10, 0))
    
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
            app.bind_global_scroll(det_f, app._scroll_main)
            
    btn_t = ctk.CTkButton(btn_frame, text="Detail ▼", width=60, height=28, font=ctk.CTkFont(size=11), 
                         fg_color=("#e4e4e4", "#2d3135"), hover_color=("#c0c0c0", "#3e4348"), 
                         text_color=("black", "white"), command=toggle)
    btn_t.pack(side="left", padx=(0, 5))
    
    def remove_card():
        if res in app.history: 
            app.history.remove(res)
            app.save_current_state()
        card.destroy()
        
    ctk.CTkButton(btn_frame, text="✕", font=ctk.CTkFont(size=14, weight="bold"), width=30, height=30, 
                 corner_radius=6, fg_color="transparent", text_color=("#888888", "#5a5e63"), 
                 hover_color="#ff4d4d", command=remove_card).pack(side="left")
    
    try: target_input = int(app.ent_target.get() or 0)
    except: target_input = 0
    
    if res.get('actual_craft', 0) < target_input and app.focus_toggle_var.get():
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
        
        mat_name = mat['name'] # FIX: Jangan disunat
        name_text = f"{mat_name}\nRet: {ret_symbol}"
        
        ctk.CTkLabel(table_f, text=name_text, font=ctk.CTkFont(size=11, weight="bold"), text_color=base_color, anchor="w", justify="left", wraplength=180).grid(row=row_idx, column=0, sticky="ew", padx=5, pady=4)
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
    
    # FIX: Ganti ke GRID persis kayak Salvage
    def add_fin_row(parent, label, val, is_bold=False, color=None):
        rf = ctk.CTkFrame(parent, fg_color="transparent")
        rf.pack(fill="x", pady=4)
        rf.grid_columnconfigure(0, weight=1)
        rf.grid_columnconfigure(1, weight=0)
        
        fnt = ctk.CTkFont(size=12, weight="bold" if is_bold else "normal")
        c = color if color else ("black", "white")
        lbl_c = ("#6c757d", "#8e949a") if not is_bold else ("black", "white")
        
        ctk.CTkLabel(rf, text=label, font=ctk.CTkFont(size=12), text_color=lbl_c).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(rf, text=val, font=fnt, text_color=c).grid(row=0, column=1, sticky="e")

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

    app.bind_global_scroll(card, app._scroll_main)