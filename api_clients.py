# api_clients.py

import requests
import logging
import json
import asyncio
import traceback
import base64
from datetime import datetime
from telegram.helpers import escape_markdown

import config
from database import simpan_data_ke_db
from utils import get_hesda_auth_headers

# Variabel ini akan diisi oleh main.py
user_data = {}

async def get_kmsp_balance():
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

    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP Error saat mengambil saldo KMSP: {e}")
        return "API tidak dapat diakses (HTTP Error)"
    except requests.exceptions.RequestException as e:
        logging.error(f"Error jaringan saat mengambil saldo KMSP: {e}")
        return "Gagal terhubung ke server API"
    except json.JSONDecodeError:
        logging.error(f"Gagal memecah JSON dari API saldo KMSP.")
        return "Respons API tidak valid (Bukan JSON)"
    except Exception as e:
        logging.error(f"Kesalahan tak terduga saat mengambil saldo KMSP: {e}", exc_info=True)
        return "Kesalahan tak terduga terjadi"

async def jalankan_cek_kuota_baru(update, context):
    user_id = update.effective_user.id
    nomor_input = update.message.text.strip()

    if not re.match(r'^(08|62)\d{8,12}$', nomor_input):
        await update.message.reply_text(
            '❌ Format nomor tidak valid. Masukkan nomor dalam format `08xxxx` atau `62xxxx`.',
            parse_mode="Markdown"
        )
        context.user_data['next'] = 'handle_cek_kuota_baru_input'
        return

    if nomor_input.startswith('08'):
        nomor = '62' + nomor_input[1:]
    else:
        nomor = nomor_input
        
    status_msg = await update.message.reply_text("🔍 Sedang mengecek kuota, harap tunggu...", parse_mode="Markdown")

    try:
        url = f"https://apigw.kmsp-store.com/sidompul/v4/cek_kuota?msisdn={nomor}&isJSON=true"
        headers = {
            "Authorization": "Basic c2lkb21wdWxhcGk6YXBpZ3drbXNw",
            "X-API-Key": "60ef29aa-a648-4668-90ae-20951ef90c55",
            "X-App-Version": "4.0.0"
        }
        
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status() 
        
        response_json = response.json()
        
        await status_msg.delete()

        if response_json.get('status'):
            hasil_kotor = response_json.get("data", {}).get("hasil", "Tidak ada data.")
            hasil_bersih = html.unescape(hasil_kotor).replace('<br>', '\n').replace('MSISDN', 'NOMOR')
            
            final_text = f"✅ *Hasil Pengecekan Kuota untuk {nomor}*\n\n```{hasil_bersih}```"
            
            keyboard = [[InlineKeyboardButton("🔙 Kembali ke Menu Utama", callback_data='back_to_menu')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(user_id, final_text, parse_mode="Markdown", reply_markup=reply_markup)
        else:
            error_text = response_json.get("message", "Gagal mengambil data kuota.")
            await context.bot.send_message(user_id, f"❌ Terjadi kesalahan: `{error_text}`", parse_mode="Markdown")
            
    except Exception as e:
        logging.error(f"Error di jalankan_cek_kuota_baru: {e}", exc_info=True)
        await status_msg.delete()
        await context.bot.send_message(user_id, "❌ Terjadi kesalahan tak terduga. Silakan hubungi admin.")


async def get_api_package_details(package_code: str):
    try:
        url = f"https://golang-openapi-packagelist-xltembakservice.kmsp-store.com/v1?api_key={config.KMSP_API_KEY}"
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        all_packages = response.json().get("data", [])
        
        for package in all_packages:
            if package.get("package_code") == package_code:
                return package                                           
        return None                                       
    except requests.RequestException as e:
        logging.error(f"Gagal mengambil list paket dari API: {e}")
        return None
    except json.JSONDecodeError:
        logging.error("Gagal memecah JSON dari API list paket.")
        return None

async def execute_automatic_xuts_purchase(update, context, user_id, package_code, phone, access_token, payment_method, deducted_balance, attempt):
    # ... (Salin isi lengkap fungsi execute_automatic_xuts_purchase dari file asli Anda ke sini)
    pass

async def execute_automatic_xc_purchase(update, context, user_id, package_code, package_name_display, phone, access_token, payment_method, deducted_balance):
    # ... (Salin isi lengkap fungsi execute_automatic_xc_purchase dari file asli Anda ke sini)
    pass
    
async def execute_single_purchase(update, context, user_id, package_code, phone, access_token, payment_method, deducted_balance, return_menu_callback_data, provider="kmsp", attempt=1, package_name_for_display=None):
    # ... (Salin isi lengkap fungsi execute_single_purchase dari file asli Anda ke sini)
    pass

async def execute_single_purchase_hesda(update, context, user_id, package_id, package_name, phone, access_token, payment_method, deducted_balance, return_menu_callback_data, attempt=1):
    # ... (Salin isi lengkap fungsi execute_single_purchase_hesda dari file asli Anda ke sini)
    pass
    
async def execute_single_purchase_30h(update, context, user_id, package_code, package_name_display, phone, access_token, payment_method, deducted_balance, return_menu_callback_data, attempt=1):
    # ... (Salin isi lengkap fungsi execute_single_purchase_30h dari file asli Anda ke sini)
    pass
    
async def execute_custom_package_purchase(update, context, user_id, package_code, package_name, package_price, phone, access_token, payment_method, provider="kmsp"):
    # ... (Salin isi lengkap fungsi execute_custom_package_purchase dari file asli Anda ke sini)
    pass
    
async def execute_unreg_package(update, context, user_id, current_phone, access_token, encrypted_package_code):
    # ... (Salin isi lengkap fungsi execute_unreg_package dari file asli Anda ke sini)
    pass
    
async def request_otp_and_prompt_kmsp(update, context, phone):
    # ... (Salin isi lengkap fungsi request_otp_and_prompt_kmsp dari file asli Anda ke sini)
    pass
    
async def request_otp_and_prompt_hesda(update, context, phone):
    # ... (Salin isi lengkap fungsi request_otp_and_prompt_hesda dari file asli Anda ke sini)
    pass
