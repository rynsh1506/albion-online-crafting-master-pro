# logic_engine.py
import math

def calculate_refining_logic(name, materials, target_craft, output_qty, sell_price, item_value, station_fee, rrr_rate, is_premium, is_focus_on, focus_per_craft, max_focus_pool):
    market_tax = 0.04 if is_premium else 0.08
    setup_fee = 0.025
    total_tax_rate = market_tax + setup_fee
    decimal_rrr = rrr_rate / 100 
    
    # 1. Tentukan target resep awal
    requested_recipes = math.ceil(target_craft / output_qty) if output_qty > 0 else 0
    is_capped = False
    
    # 2. CEK FOCUS
    foc_limit_info = math.floor(max_focus_pool / focus_per_craft) if focus_per_craft > 0 else 0
    if is_focus_on and focus_per_craft > 0:
        if requested_recipes > foc_limit_info:
            requested_recipes = foc_limit_info
            is_capped = True

    total_mats_cost_gross = 0
    buy_list = []
    
    # 3. HITUNG MODAL BELI PER MATERIAL
    for mat in materials:
        mat_rrr = decimal_rrr if mat.get('is_return', True) else 0.0
        
        buy_q = math.ceil(requested_recipes * mat['qty'] * (1 - mat_rrr))
        
        eff_stock = math.floor(buy_q / (1 - mat_rrr)) if (1 - mat_rrr) > 0 else buy_q
        craftable_m = math.floor(eff_stock / mat['qty']) if mat['qty'] > 0 else 0
        
        buy_list.append({
            "name": mat['name'], "qty": buy_q, "price": mat['price'], "req_q": mat['qty'], 
            "is_ret": mat.get('is_return', True), "eff_stock": eff_stock, "craftable_m": craftable_m,
            "mat_rrr": mat_rrr
        })
        total_mats_cost_gross += (buy_q * mat['price'])
        
    # 4. SIMULASI ACTUAL CRAFTABLE
    inventory = [m['qty'] for m in buy_list]
    actual_recipes_run = 0
    
    while True:
        valid_mats = [inv // m['req_q'] for inv, m in zip(inventory, buy_list) if m['req_q'] > 0]
        possible = min(valid_mats) if valid_mats else 0
        if possible <= 0: break
        
        actual_recipes_run += possible
        for i, m in enumerate(buy_list):
            if m['req_q'] > 0:
                used = possible * m['req_q']
                inventory[i] -= used
                if m['is_ret']:
                    inventory[i] += math.floor((used * decimal_rrr) + 0.5)

    actual_crafted_items = actual_recipes_run * output_qty

    # 5. HITUNG SISA MATERIAL DAN BIAYA
    for i, m in enumerate(buy_list):
        m['sisa'] = inventory[i]

    material_return_value = sum([m['sisa'] * m['price'] for m in buy_list])
    net_mat_cost = total_mats_cost_gross - material_return_value
    
    fee_per_recipe = item_value * 0.1125 * (station_fee / 100)
    total_fee = actual_recipes_run * fee_per_recipe
    total_production_cost = net_mat_cost + total_fee
    
    cost_per_item = total_production_cost / actual_crafted_items if actual_crafted_items > 0 else 0
    net_sell_price = sell_price * (1 - total_tax_rate)
    profit_per_item = net_sell_price - cost_per_item
    total_profit = profit_per_item * actual_crafted_items
    
    margin = (profit_per_item / cost_per_item) * 100 if cost_per_item > 0 else 0
    sisa_focus = max_focus_pool - (foc_limit_info * focus_per_craft) if is_focus_on else max_focus_pool
    srp_divisor = actual_crafted_items * (1 - total_tax_rate) if actual_crafted_items > 0 else 1
    
    leftover_texts = [f"{m['sisa']} {m['name']}" for m in buy_list if m['sisa'] > 0]
    leftover_str = " | ".join(leftover_texts) if leftover_texts else "Habis (0)"

    return {
        "name": name, "target_craft": int(target_craft), "actual_craft": int(actual_crafted_items),
        "is_focus_capped": is_capped, "buy_list": buy_list, "fee_per_recipe": fee_per_recipe,
        "total_mats_cost": total_mats_cost_gross, "material_return_val": material_return_value,
        "net_mat_cost": net_mat_cost, "total_fee": total_fee, "cost_per_item": cost_per_item,
        "sell_price": sell_price, "profit_per_pc": profit_per_item, "total_profit": total_profit, 
        "total_cost": total_production_cost, "margin": margin, "is_premium": is_premium,
        "is_profitable": total_profit > 0, "total_focus": foc_limit_info * focus_per_craft if is_focus_on else 0,
        "foc_can_craft": foc_limit_info, "foc_sisa_point": sisa_focus, "foc_item_yield": foc_limit_info * output_qty,
        "leftover_text": leftover_str, "requested_recipes": requested_recipes, "decimal_rrr": decimal_rrr,
        "srp": { "5": (total_production_cost * 1.05) / srp_divisor if srp_divisor > 0 else 0, "10": (total_production_cost * 1.10) / srp_divisor if srp_divisor > 0 else 0, "15": (total_production_cost * 1.15) / srp_divisor if srp_divisor > 0 else 0, "20": (total_production_cost * 1.20) / srp_divisor if srp_divisor > 0 else 0 },
        "profit_tiers": { "5": total_production_cost * 0.05, "10": total_production_cost * 0.10, "15": total_production_cost * 0.15, "20": total_production_cost * 0.20 }
    }