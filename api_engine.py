import requests
import traceback
import db_manager

def clean_albion_name(text):
    if not isinstance(text, str): return str(text)
    prefixes = ["Beginner's ", "Novice's ", "Journeyman's ", "Adept's ", "Adept", "Expert's ", "Master's ", "Grandmaster's ", "Elder's "]
    for p in prefixes:
        if text.startswith(p):
            return text.replace(p, "", 1)
    return text

def download_and_build_db():
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

        # ==================================================
        # PERUBAHAN BESAR: NO-FILTER, AMBIL SEMUA ITEM!
        # ==================================================
        raw_items_list = []
        def find_items(obj):
            if isinstance(obj, dict):
                uid = obj.get("@uniquename")
                if uid:
                    # GAK ADA IF CRAFTING LAGI. ASAL PUNYA UID, SIKAT!
                    raw_items_list.append(obj)
                    
                    # Tetep masukin varian Enchantment (.1, .2, .3, .4) kalau ada
                    if "enchantments" in obj:
                        enchs = obj["enchantments"].get("enchantment", [])
                        if isinstance(enchs, dict): enchs = [enchs]
                        for e in enchs:
                            if isinstance(e, dict):
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
            
            # Kalau nggak punya nama EN-US dari API (kayak raw resource), pake UniqueName-nya
            if not base_name:
                base_name = uid
                
            # Filter minimal: Cuma buang sampah sistem (Token, Journal) biar UI nggak kotor
            if "Token" in base_name or "Journal" in base_name or "Trash" in base_name: continue
            
            base_name = clean_albion_name(base_name)
            
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
            
            # Kalau ada resep, ekstrak bahannya. Kalau nggak ada, yaudah list resepnya kosong aja (mats = [])
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
                        r_raw_name = clean_albion_name(r_raw_name)
                        
                        r_display_name = f"{r_raw_name} [{r_tier}.{r_ench}]"
                            
                        is_returnable = True
                        if res.get("@maxreturnamount") == "0": is_returnable = False
                        uid_upper = r_uid.upper()
                        if any(keyword in uid_upper for keyword in ["_RUNE", "_SOUL", "_RELIC", "_SHARD", "ARTIFACT_", "_MOUNT_", "FARM_"]):
                            is_returnable = False
                            
                        mats.append({
                            "id": r_uid, "name": r_display_name, "qty": r_qty, "is_returnable": is_returnable
                        })

            try: item_val = float(item.get("@itemvalue", 0))
            except: item_val = 0
            
            if item_val == 0:
                item_val = dynamic_item_value
                
            t = 4
            try: t = int(item.get("@tier", current_tier))
            except: pass
            
            db[display_name] = {"id": uid, "tier": t, "out_qty": out_qty_val, "item_value": item_val, "recipe": mats}
        
        # Simpan puluhan ribu data itu langsung ke SQLite
        db_manager.save_items_to_db(db)
        return db
        
    except Exception as e:
        traceback.print_exc()
        return None