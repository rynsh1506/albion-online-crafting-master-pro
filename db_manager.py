import sqlite3
import json
import os

from config_utils import APP_DATA_DIR

DB_PATH = os.path.join(APP_DATA_DIR, "albion_data.db")

def get_connection():
    return sqlite3.connect(DB_PATH)

def initialize_db():
    conn = get_connection()
    cursor = conn.cursor()
    # Bikin tabel items dengan Indexing di kolom name buat speed kenceng
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS items (
            display_name TEXT PRIMARY KEY,
            id TEXT,
            tier INTEGER,
            item_value REAL,
            out_qty INTEGER,
            recipe_json TEXT
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_name ON items(display_name)')
    conn.commit()
    conn.close()

def save_items_to_db(items_dict):
    conn = get_connection()
    cursor = conn.cursor()
    
    # Bersihkan data lama
    cursor.execute("DELETE FROM items")
    
    data_to_insert = []
    for name, info in items_dict.items():
        data_to_insert.append((
            name, 
            info['id'], 
            info.get('tier', 0), 
            info.get('item_value', 0),
            info.get('out_qty', 1),
            json.dumps(info.get('recipe', [])) # Simpan resep sebagai JSON string
        ))
    
    cursor.executemany(
        "INSERT INTO items VALUES (?, ?, ?, ?, ?, ?)", 
        data_to_insert
    )
    conn.commit()
    conn.close()

def search_items_db(query="", tier="All", enchant="All"):
    conn = get_connection()
    cursor = conn.cursor()
    
    sql = "SELECT display_name, id, tier, item_value FROM items WHERE 1=1"
    params = []

    if query:
        sql += " AND display_name LIKE ?"
        params.append(f"%{query}%")
    
    if tier != "All":
        sql += " AND tier = ?"
        params.append(int(tier.replace("T", "")))
        
    if enchant != "All":
        e_num = enchant.replace(".", "")
        if e_num == "0":
            sql += " AND (id NOT LIKE '%@%' AND id NOT LIKE '%_LEVEL%')"
        else:
            sql += " AND (id LIKE ? OR id LIKE ?)"
            params.append(f"%@{e_num}%")
            params.append(f"%_LEVEL{e_num}%")

    sql += " ORDER BY display_name ASC"
    
    cursor.execute(sql, params)
    results = cursor.fetchall()
    conn.close()
    return results

def get_item_detail_db(display_name):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM items WHERE display_name = ?", (display_name,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "display_name": row[0],
            "id": row[1],
            "tier": row[2],
            "item_value": row[3],
            "out_qty": row[4],
            "recipe": json.loads(row[5])
        }
    return None