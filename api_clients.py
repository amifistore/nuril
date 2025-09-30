# api_clients.py
import requests
import logging
import json
import asyncio
import traceback
import base64
from datetime import datetime
from telegram.helpers import escape_markdown

# Impor dari modul lokal
import config
from database import simpan_data_ke_db
from utils import get_hesda_auth_headers

# Variabel global untuk data user (akan diinisialisasi di main.py)
user_data = {}

# Salin semua fungsi yang berhubungan dengan API ke sini, contoh:
# - get_kmsp_balance
# - jalankan_cek_kuota_baru
# - get_api_package_details
# - request_otp_and_prompt_kmsp
# - request_otp_and_prompt_hesda
# - execute_single_purchase
# - execute_single_purchase_hesda
# - execute_custom_package_purchase
# - execute_automatic_xuts_purchase
# - execute_automatic_xc_purchase
# - execute_single_purchase_30h
# - execute_unreg_package

# Catatan: Karena keterbatasan panjang, saya hanya akan menyertakan satu contoh
# fungsi yang telah diadaptasi. Anda perlu memindahkan SEMUA fungsi API Anda
# ke file ini dan menyesuaikannya jika perlu.

async def get_kmsp_balance():
    """Mengambil saldo dari API KMSP."""
    try:
        url = f"https://golang-openapi-panelaccountbalance-xltembakservice.kmsp-store.com/v1?api_key={config.KMSP_API_KEY}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        api_response = response.json()
        logging.info(f"KMSP balance API response: {api_response}")

        if isinstance(api_response, dict) and 'data' in api_response and isinstance(api_response.get('data'), dict):
            balance_value = api_response['data'].get('balance')
            if balance_value is not None:
                try:
                    formatted_balance = f"Rp{int(float(balance_value)):,}"
                    return formatted_balance
                except (ValueError, TypeError):
                    logging.error(f"Gagal mengonversi nilai saldo '{balance_value}' menjadi angka.")
                    return "Format saldo tidak valid"

        message = api_response.get('message', 'Respons API tidak dikenali.')
        logging.warning(f"Struktur respons API KMSP tidak seperti yang diharapkan. Pesan: {message}")
        return f"Info dari API: {message}"

    except requests.exceptions.RequestException as e:
        logging.error(f"Error jaringan saat mengambil saldo KMSP: {e}")
        return "Gagal terhubung ke server API"
    except Exception as e:
        logging.error(f"Kesalahan tak terduga saat mengambil saldo KMSP: {e}", exc_info=True)
        return "Kesalahan tak terduga"

# ==============================================================================
# == PENTING: Salin semua fungsi API lainnya dari file asli Anda ke sini ==
# == Pastikan untuk mengganti `user_data` dengan `api_clients.user_data` jika  ==
# == Anda mengaksesnya dari file lain, atau teruskan `user_data` sebagai   ==
# == argumen fungsi.                                                        ==
# ==============================================================================
# Contoh:
# async def execute_single_purchase(update, context, user_id, ...):
#     ...
#     user_data["registered_users"][str(user_id)]["balance"] -= deducted_balance
#     simpan_data_ke_db(user_data)
#     ...
