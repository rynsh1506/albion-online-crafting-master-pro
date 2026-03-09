import math

def calculate_refining_logic(
    item_name,
    materials_list, 
    target_actual_craft, 
    output_qty_per_craft, 
    sell_price, 
    item_value, 
    station_fee, 
    rrr_percentage, 
    is_premium=True,
    use_focus=False,
    focus_cost=0,
    focus_pool=30000,
    sell_method="direct" 
):
    try:
        # --- KONVERSI DATA ---
        target_actual_craft = int(target_actual_craft)
        output_qty_per_craft = int(output_qty_per_craft)
        sell_price = float(sell_price)
        item_value = float(item_value)
        station_fee = float(station_fee)
        rrr = float(rrr_percentage) / 100.0
        
        if use_focus and float(focus_cost or 0) > 0:
            max_focus_craft = int(float(focus_pool) / float(focus_cost))
            target_actual_craft = min(target_actual_craft, max_focus_craft)

        if target_actual_craft <= 0:
            return {"error": "Target craft 0"}

        nutrition_factor = 0.1125 
        tax_per_craft = item_value * nutrition_factor * (station_fee / 100.0)

        buy_list = []
        total_material_cost = 0.0
        inventory = {}

        # --- 1. RUMUS EXCEL: HITUNG MATERIAL AWAL YANG HARUS DIBELI ---
        for mat in materials_list:
            q_per_craft = float(mat["qty"])
            price = float(mat["price"])
            is_ret = mat.get("is_return", True)
            stock = float(mat.get("qty_from_stock", 0.0))

            if is_ret:
                # Target awal dipotong RRR untuk menghemat modal
                total_needed = target_actual_craft * q_per_craft * (1 - rrr)
            else:
                total_needed = target_actual_craft * q_per_craft
                
            qty_to_prepare = math.ceil(total_needed)
            qty_to_buy = max(0, qty_to_prepare - stock)
            cash_out = qty_to_buy * price
            
            total_material_cost += cash_out
            inventory[mat["name"]] = qty_to_prepare
            
            buy_list.append({
                "name": mat["name"],
                "qty_to_buy": qty_to_buy,
                "qty_from_stock": stock,
                "price": price,
                "cash_out": cash_out,
                "is_return": is_ret,
                "qty_per_craft": q_per_craft
            })

        # --- 2. SIMULASI GULUNG BAHAN (Seperti Kolom Iterasi Excel) ---
        actual_total_crafts = 0
        total_tax_cost = 0
        
        iteration_safe_guard = 0
        while True:
            iteration_safe_guard += 1
            if iteration_safe_guard > 1000: break # Mencegah loop rusak
            
            # Cari batas craft berdasarkan inventory saat ini
            crafts_possible = []
            for mat in buy_list:
                possible = math.floor(inventory[mat["name"]] / mat["qty_per_craft"])
                crafts_possible.append(possible)
            
            current_crafts = min(crafts_possible) if crafts_possible else 0
            if current_crafts <= 0: break
                
            actual_total_crafts += current_crafts
            total_tax_cost += current_crafts * tax_per_craft # Pajak iterasi
            
            # Pengurangan bahan & Pengembalian RRR
            for mat in buy_list:
                used = current_crafts * mat["qty_per_craft"]
                inventory[mat["name"]] -= used
                
                if mat["is_return"]:
                    returned = math.floor(used * rrr)
                    inventory[mat["name"]] += returned
                    
        # Simpan sisa material riil setelah selesai digulung
        for mat in buy_list:
            mat["leftover"] = inventory[mat["name"]]

        # --- 3. PENDAPATAN & PAJAK MARKET ---
        total_items_produced = actual_total_crafts * output_qty_per_craft
        gross_revenue = total_items_produced * sell_price
        
        market_tax_rate = 0.04 if is_premium else 0.08
        setup_fee_rate = 0.025 if sell_method == "order" else 0.0
        total_fee_rate = market_tax_rate + setup_fee_rate
        
        market_fee_deduction = gross_revenue * total_fee_rate
        net_revenue = gross_revenue - market_fee_deduction

        # --- 4. HASIL AKHIR (COST & PROFIT / ITEM) ---
        net_production_cost = total_material_cost + total_tax_cost
        real_profit = net_revenue - net_production_cost
        margin = (real_profit / net_production_cost * 100) if net_production_cost > 0 else 0.0
        
        # Hitungan per item persis seperti Excel
        profit_per_item = (real_profit / total_items_produced) if total_items_produced > 0 else 0.0
        cost_per_item = (net_production_cost / total_items_produced) if total_items_produced > 0 else 0.0

        def get_suggested(target_m):
            needed_net = net_production_cost * (1 + target_m)
            price_needed = (needed_net / (1 - total_fee_rate)) / total_items_produced if total_items_produced > 0 else 0
            return math.ceil(price_needed)

        return {
            "name": item_name,
            "actual_craft": actual_total_crafts, 
            "total_produced": total_items_produced,
            "buy_list": buy_list,
            "total_material_cost": total_material_cost,
            "tax_used": station_fee,
            "total_tax_cost": total_tax_cost,
            "net_production_cost": net_production_cost,
            "cost_per_item": cost_per_item,
            "gross_revenue": gross_revenue,
            "market_fee_deduction": market_fee_deduction,
            "total_revenue": net_revenue,
            "real_profit": real_profit,
            "profit_per_item": profit_per_item,
            "margin": margin,
            "is_profitable": real_profit > 0,
            "suggested": {
                "m5": get_suggested(0.05),
                "m10": get_suggested(0.10),
                "m20": get_suggested(0.20)
            }
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": f"Logic Engine Error: {str(e)}"}