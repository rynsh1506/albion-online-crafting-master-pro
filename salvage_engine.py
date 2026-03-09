import math

def calculate_salvage_flip(item_name, item_buy_price, item_value, materials_data, is_premium=True):
    """
    Menghitung untung rugi menghancurkan item di Repair Station.
    - item_buy_price: Harga kita beli item rongsoknya di Market.
    - item_value: Buat ngitung Silver murni dari NPC (25% dari Item Value).
    - materials_data: Bahan yang keluar (25% dari resep, dibulatkan ke bawah).
    """
    try:
        item_buy_price = float(item_buy_price)
        item_value = float(item_value)
        
        # 1. Silver murni dari NPC (25% dari Item Value)
        silver_gained = math.floor(item_value * 0.25)
        
        # Pajak jika material hasil salvage kita jual lagi (Sell Order 2.5% + Tax Market)
        market_tax = 0.065 if is_premium else 0.105
        
        salvaged_mats_value = 0
        mats_result = []
        
        # 2. Hitung jumlah bahan yang muntah dari mesin Salvage
        for mat in materials_data:
            # Aturan Albion: Salvage mengembalikan 25% material (selalu round down)
            returned_qty = math.floor(mat["qty_in_recipe"] * 0.25)
            
            if returned_qty > 0:
                gross_revenue = returned_qty * mat["market_sell_price"]
                # Potong pajak karena kita mau jual bahan ini ke market
                net_revenue = math.floor(gross_revenue * (1 - market_tax))
                
                salvaged_mats_value += net_revenue
                
                mats_result.append({
                    "name": mat["name"],
                    "qty_returned": returned_qty,
                    "net_value": net_revenue,
                    "unit_price": mat["market_sell_price"]
                })
                
        # 3. Hitungan Final Profit
        total_revenue = silver_gained + salvaged_mats_value
        profit = total_revenue - item_buy_price
        margin = (profit / item_buy_price * 100) if item_buy_price > 0 else 0
        
        return {
            "name": item_name,
            "buy_price": item_buy_price,
            "silver_from_npc": silver_gained,
            "materials_salvaged": mats_result,
            "total_revenue": total_revenue,
            "profit": profit,
            "margin": margin,
            "is_profitable": profit > 0
        }
    except Exception as e:
        print(f"Error Salvage: {e}")
        return {"error": str(e)}