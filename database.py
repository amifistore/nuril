# database.py
import sqlite3
import json
import logging
from config import DB_FILE

def inisialisasi_database():
    """Membuat tabel yang diperlukan jika belum ada."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY, first_name TEXT, username TEXT,
        balance INTEGER DEFAULT 0, accounts TEXT DEFAULT '{}',
        transactions TEXT DEFAULT '[]', selected_hesdapkg_ids TEXT DEFAULT '[]',
        selected_30h_pkg_ids TEXT DEFAULT '[]', is_admin INTEGER DEFAULT 0,
        is_banned INTEGER DEFAULT 0, phone_number TEXT
    )''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS custom_packages (
        code TEXT PRIMARY KEY, name TEXT, price INTEGER, description TEXT,
        payment_methods TEXT, ewallet_fee INTEGER DEFAULT 0
    )''')
    cursor.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS blocked_users (user_id INTEGER PRIMARY KEY)')
    conn.commit()
    conn.close()
    logging.info("Database SQLite berhasil diinisialisasi.")

def simpan_data_ke_db(user_data):
    """Menyimpan data dari memori (variabel user_data) ke database SQLite."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    for user_id_str, details in user_data["registered_users"].items():
        cursor.execute('''
        INSERT OR REPLACE INTO users (id, first_name, username, balance, accounts, transactions, selected_hesdapkg_ids, selected_30h_pkg_ids)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            int(user_id_str),
            details.get('first_name', 'N/A'),
            details.get('username', 'N/A'),
            details.get('balance', 0),
            json.dumps(details.get('accounts', {})),
            json.dumps(details.get('transactions', [])),
            json.dumps(details.get('selected_hesdapkg_ids', [])),
            json.dumps(details.get('selected_30h_pkg_ids', []))
        ))
    
    cursor.execute("DELETE FROM blocked_users")
    if user_data.get("blocked_users"):
        cursor.executemany("INSERT INTO blocked_users (user_id) VALUES (?)", [(uid,) for uid in user_data["blocked_users"]])

    cursor.execute("DELETE FROM custom_packages")
    if user_data.get("custom_packages"):
        package_list = [
            (
                code, 
                details['name'], 
                details['price'], 
                details.get('description', ''), 
                json.dumps(details.get('payment_methods', [])),
                details.get('ewallet_fee', 0)
            ) 
            for code, details in user_data["custom_packages"].items()
        ]
        cursor.executemany("INSERT OR REPLACE INTO custom_packages (code, name, price, description, payment_methods, ewallet_fee) VALUES (?, ?, ?, ?, ?, ?)", package_list)

    conn.commit()
    conn.close()
    logging.info("Data berhasil disimpan ke SQLite.")

def muat_data_dari_db():
    """Memuat data dari database SQLite ke memori (variabel user_data)."""
    user_data = {
        "registered_users": {},
        "blocked_users": [],
        "custom_packages": {}
    }
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("SELECT id, first_name, username, balance, accounts, transactions, selected_hesdapkg_ids, selected_30h_pkg_ids FROM users")
    for row in cursor.fetchall():
        user_id_str = str(row[0])
        user_data["registered_users"][user_id_str] = {
            "first_name": row[1],
            "username": row[2],
            "balance": row[3],
            "accounts": json.loads(row[4] or '{}'),
            "transactions": json.loads(row[5] or '[]'),
            "selected_hesdapkg_ids": json.loads(row[6] or '[]'),
            "selected_30h_pkg_ids": json.loads(row[7] or '[]')
        }

    cursor.execute("SELECT user_id FROM blocked_users")
    user_data["blocked_users"] = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT code, name, price, description, payment_methods, ewallet_fee FROM custom_packages")
    for row in cursor.fetchall():
        user_data["custom_packages"][row[0]] = {
            "name": row[1],
            "price": row[2],
            "description": row[3],
            "payment_methods": json.loads(row[4] or '[]'),
            "ewallet_fee": row[5]
        }
    
    conn.close()
    logging.info(f"📂 Data dari SQLite berhasil dimuat. Total {len(user_data['registered_users'])} user.")
    return user_data
