# handlers.py

# Impor library standar
import logging
import re
import asyncio
import math
import html
import base64
import traceback 
import uuid 
import random
import sqlite3
from datetime import datetime, timedelta, timezone

# Impor library Telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown

# Impor dari modul-modul lokal yang telah kita buat
import config
import data_packages
from database import simpan_data_ke_db
import api_clients
import utils

# Variabel global untuk data user, akan diisi oleh main.py saat bot dimulai
user_data = {}

# ==============================================================================
# == SEMUA FUNGSI DARI FILE ASLI ANDA TELAH DISALIN KE BAWAH INI ==
# ==============================================================================

async def run_automatic_xcs_addon_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    automatic_xcs_flow_state = context.user_data.get('automatic_xcs_flow_state')

    if not automatic_xcs_flow_state:
        if context.user_data.get('overall_status_message_id'):
            try:
                await context.bot.delete_message(chat_id=user_id, message_id=context.user_data['overall_status_message_id'])
            except Exception as e:
                logging.warning(f"Gagal menghapus pesan status lama: {e}")
            del context.user_data['overall_status_message_id']
        await context.bot.send_message(user_id, "Sesi pembelian otomatis XCS ADD ON tidak valid atau kedaluwarsa. Silakan mulai ulang.")
        await send_main_menu(update, context)
        return

                                
    phone = automatic_xcs_flow_state['phone']
    access_token = automatic_xcs_flow_state['access_token']
    payment_method_xcp_8gb = automatic_xcs_flow_state['payment_method_xcp_8gb']
    
    automatic_xcs_flow_state.setdefault('addons_to_process', [])
    automatic_xcs_flow_state.setdefault('current_addon_index', 0)
    automatic_xcs_flow_state.setdefault('addon_pending_retry_count', 0)
    automatic_xcs_flow_state.setdefault('addon_results', {})
    
                                                               
    automatic_xcs_flow_state.setdefault('failed_attempts_for_reprocess', {})
    automatic_xcs_flow_state.setdefault('current_reprocess_id_index', 0)
    automatic_xcs_flow_state.setdefault('reprocess_attempts_counter', {})
    automatic_xcs_flow_state.setdefault('flow_has_waited', False)
    automatic_xcs_flow_state.setdefault('reprocessing_countdown_initiated', False)
    automatic_xcs_flow_state.setdefault('reprocessing_pass_count', 1)
    automatic_xcs_flow_state.setdefault('xcp_8gb_completed', False)
    
                                                                                
    automatic_xcs_flow_state.setdefault('reprocessing_queue', [])

                       
    MAX_REPROCESSING_PASSES = 2                                
    
                         
    addons_to_process = automatic_xcs_flow_state['addons_to_process']
    current_addon_index = automatic_xcs_flow_state['current_addon_index']
    addon_pending_retry_count = automatic_xcs_flow_state['addon_pending_retry_count']
    addon_results = automatic_xcs_flow_state['addon_results']
    failed_attempts_for_reprocess = automatic_xcs_flow_state['failed_attempts_for_reprocess']
    current_reprocess_id_index = automatic_xcs_flow_state['current_reprocess_id_index']
    reprocess_attempts_counter = automatic_xcs_flow_state['reprocess_attempts_counter']
    status_message_id = automatic_xcs_flow_state.setdefault('overall_status_message_id', None)
    
                                                              
    reprocessing_queue = automatic_xcs_flow_state['reprocessing_queue']

                                    
    current_status_text = ""
    
    if current_addon_index < len(addons_to_process):
                                      
        addon_info_current = next((pkg for pkg in data_packages.ADD_ON_SEQUENCE if pkg['code'] == addons_to_process[current_addon_index]), None)
        current_addon_name_for_display = addon_info_current['name'] if addon_info_current else "Paket Tidak Dikenal"
        current_status_text = (
            f"Melanjutkan alur XCS ADD ON otomatis untuk *{phone}*...\n"
            f"📦 Memproses paket awal: *{current_addon_name_for_display}* "
            f"({current_addon_index + 1} dari {len(addons_to_process)})"
        )
                                                                                             
    elif reprocessing_queue and current_reprocess_id_index < len(reprocessing_queue):
                                                                
        unique_failure_id_to_retry = reprocessing_queue[current_reprocess_id_index]
        failure_details = failed_attempts_for_reprocess.get(unique_failure_id_to_retry)                                
        
        if failure_details:
            current_addon_name_for_display = failure_details['package_name']
            current_reprocess_attempt_count = reprocess_attempts_counter.get(unique_failure_id_to_retry, 0)
            MAX_REPROCESS_ATTEMPTS = 3
            current_pass = automatic_xcs_flow_state.get('reprocessing_pass_count', 1)
            current_status_text = (
                f"✅ Selesai memproses semua paket awal.\n"
                f"🔁 Mencoba ulang paket gagal (Putaran {current_pass}/{MAX_REPROCESSING_PASSES}):\n"
                f"   Paket: *{current_addon_name_for_display}* ({current_reprocess_id_index + 1} dari {len(reprocessing_queue)})\n"                   
                f"   (Percobaan ke-{current_reprocess_attempt_count + 1} / Maks {MAX_REPROCESS_ATTEMPTS})"
            )
        else:
                                                                                         
            current_status_text = f"Melewatkan item yang tidak valid di antrean..."
            automatic_xcs_flow_state['current_reprocess_id_index'] += 1
            asyncio.create_task(run_automatic_xcs_addon_flow(update, context))
            return
            
    else:
                                             
        current_status_text = "✅ Semua paket berhasil diproses. Mempersiapkan pembelian paket utama..."

                                     
    if not status_message_id:
        msg = await context.bot.send_message(user_id, current_status_text, parse_mode="Markdown")
        automatic_xcs_flow_state['overall_status_message_id'] = msg.message_id
        status_message_id = msg.message_id
    else:
        try:
            await context.bot.edit_message_text(chat_id=user_id, message_id=status_message_id, text=current_status_text, parse_mode="Markdown")
        except Exception as e:
            if "message is not modified" not in str(e):
                logging.warning(f"Gagal mengedit pesan status XCS {status_message_id}: {e}.")

                                                                         
                                                                            
                                                                         
    if current_addon_index < len(addons_to_process):
        addon_code = addons_to_process[current_addon_index]
        addon_info = next((pkg for pkg in data_packages.ADD_ON_SEQUENCE if pkg['code'] == addon_code), None)
        
        if not addon_info:
            logging.error(f"Paket ADD ON tidak dikenal ({addon_code}). Melewatkan.")
            addon_results[addon_code] = {"success": False, "error_message": "Paket tidak dikenal"}
            automatic_xcs_flow_state['current_addon_index'] += 1
            asyncio.create_task(run_automatic_xcs_addon_flow(update, context))
            return

        addon_name = addon_info['name']
        addon_price = data_packages.CUSTOM_PACKAGE_PRICES.get(addon_code, {}).get('price_bot', 0)

        addon_purchase_result = await api_clients.execute_single_purchase_30h(
            update, context, user_id, addon_code, addon_name, phone, access_token, "BALANCE", addon_price,
            "automatic_xcs_addon_flow",
            automatic_xcs_flow_state['addon_pending_retry_count'] + 1
        )
        addon_results[addon_code] = addon_purchase_result

                                                                           
        if addon_purchase_result.get('fatal_error'):
            logging.critical(f"FATAL ERROR (Token Expired) pada alur XCS otomatis untuk user {user_id}. Menghentikan semua proses dan merefund sisa saldo.")
            
                                                           
            total_price_to_refund = context.user_data.pop('total_automatic_xcs_price', 0)
            
                                                                                      
            already_refunded = addon_purchase_result.get('refunded_amount', 0)
            
                                             
            remaining_refund = total_price_to_refund - already_refunded

                                   
            if remaining_refund > 0:
                user_data["registered_users"][str(user_id)]["balance"] += remaining_refund
                simpan_data_ke_db(user_data)

                                              
            user_facing_error = (
                "⚠️ *TOKEN LOGIN ANDA KADALUARSA* ⚠️\n"
                "Semua proses pembelian otomatis telah dihentikan.\n\n"
                f"Total saldo sebesar *Rp{total_price_to_refund:,}* telah dikembalikan ke akun Anda.\n"
                "Silakan login ulang dan coba lagi."
            )
            
            status_message_id = automatic_xcs_flow_state.get('overall_status_message_id')
            if status_message_id:
                try:
                    await context.bot.edit_message_text(chat_id=user_id, message_id=status_message_id, text=user_facing_error, parse_mode="Markdown")
                except Exception:
                    await context.bot.send_message(user_id, user_facing_error, parse_mode="Markdown")
            else:
                await context.bot.send_message(user_id, user_facing_error, parse_mode="Markdown")

                                             
            del context.user_data['automatic_xcs_flow_state']
            await send_main_menu(update, context)
            return
                                 

        if addon_purchase_result['success']:
            await context.bot.edit_message_text(chat_id=user_id, message_id=status_message_id, text=f"✅ Pembelian *{addon_name}* berhasil! Melanjutkan...", parse_mode="Markdown")
            automatic_xcs_flow_state['addon_pending_retry_count'] = 0
            automatic_xcs_flow_state['current_addon_index'] += 1
            await asyncio.sleep(10)
            asyncio.create_task(run_automatic_xcs_addon_flow(update, context))

        elif addon_purchase_result.get('specific_action') == 'countdown_retry':
            if automatic_xcs_flow_state['flow_has_waited']:
                logging.warning(f"User {user_id} - {phone}: ADD ON {addon_name} pending, tetapi bot sudah pernah menunggu. Dianggap GAGAL.")
                unique_failure_id = str(uuid.uuid4())
                failed_attempts_for_reprocess[unique_failure_id] = {
                    "package_code": addon_code, "package_name": addon_name, "price_bot": addon_price, "error_message": "Pending kedua kali, dianggap gagal."
                }
                await context.bot.edit_message_text(chat_id=user_id, message_id=status_message_id, text=f"⚠️ Pembelian *{addon_name}* pending lagi. Ini dianggap kegagalan dan akan dicoba ulang nanti. Melanjutkan...", parse_mode="Markdown")
                automatic_xcs_flow_state['addon_pending_retry_count'] = 0
                automatic_xcs_flow_state['current_addon_index'] += 1
                await asyncio.sleep(10)
            else:
                automatic_xcs_flow_state['flow_has_waited'] = True
                logging.info(f"User {user_id} - {phone}: ADD ON {addon_name} pending. Memulai countdown 10 menit.")
                countdown_msg = await context.bot.send_message(user_id, f"⏳ Pembelian *{addon_name}* pending. Menunggu 10 menit sebelum mencoba lagi...", parse_mode="Markdown")
                await asyncio.sleep(600)
                await countdown_msg.delete()
            asyncio.create_task(run_automatic_xcs_addon_flow(update, context))
        else:
            automatic_xcs_flow_state['addon_pending_retry_count'] += 1
            if automatic_xcs_flow_state['addon_pending_retry_count'] >= config.MAX_ADDON_PURCHASE_RETRIES:
                logging.error(f"User {user_id} - {phone}: ADD ON {addon_name} gagal setelah {config.MAX_ADDON_PURCHASE_RETRIES} percobaan.")
                unique_failure_id = str(uuid.uuid4())
                failed_attempts_for_reprocess[unique_failure_id] = {
                    "package_code": addon_code, "package_name": addon_name, "price_bot": addon_price, "error_message": addon_purchase_result.get('error_message', 'Gagal')
                }
                await context.bot.edit_message_text(chat_id=user_id, message_id=status_message_id, text=f"❌ Pembelian *{addon_name}* gagal total dan dicatat untuk dicoba ulang nanti. Melanjutkan...", parse_mode="Markdown")
                automatic_xcs_flow_state['addon_pending_retry_count'] = 0
                automatic_xcs_flow_state['current_addon_index'] += 1
                await asyncio.sleep(10)
            else:
                logging.info(f"User {user_id} - {phone}: ADD ON {addon_name} gagal. Mencoba lagi.")
                await context.bot.edit_message_text(chat_id=user_id, message_id=status_message_id, text=f"❌ Pembelian *{addon_name}* gagal. Mencoba lagi...", parse_mode="Markdown")
                await asyncio.sleep(10)
            asyncio.create_task(run_automatic_xcs_addon_flow(update, context))
        return

                                                                         
                                   
                                                                         
    if current_addon_index >= len(addons_to_process) and failed_attempts_for_reprocess and not automatic_xcs_flow_state.get('reprocessing_countdown_initiated', False):
        automatic_xcs_flow_state['reprocessing_countdown_initiated'] = True
        
                                                                                      
        automatic_xcs_flow_state['reprocessing_queue'] = list(failed_attempts_for_reprocess.keys())
        
        logging.info(f"User {user_id} - {phone}: Fase 1 selesai, ditemukan {len(failed_attempts_for_reprocess)} kegagalan. Memulai jeda 4 menit.")
        await context.bot.edit_message_text(
            chat_id=user_id, message_id=status_message_id, 
            text="✅ Pemrosesan awal selesai. Ditemukan beberapa paket yang gagal. Akan dicoba lagi setelah jeda.",
            parse_mode="Markdown"
        )
        countdown_seconds = 240
        countdown_msg = await context.bot.send_message(user_id, f"⏳ Jeda 4 menit 0 detik sebelum mencoba ulang...", parse_mode="Markdown")
        for i in range(countdown_seconds, 0, -1):
            if i % 15 == 0 or i <= 10:
                minutes = i // 60
                seconds = i % 60
                try:
                    await context.bot.edit_message_text(
                        chat_id=user_id, message_id=countdown_msg.message_id,
                        text=f"⏳ Jeda sebelum mencoba ulang: *{minutes} menit {seconds} detik*"
                    )
                except Exception as e:
                    if "message is not modified" not in str(e): logging.warning(f"Gagal update countdown: {e}")
            await asyncio.sleep(1)
        try: await countdown_msg.delete()
        except Exception: pass
        asyncio.create_task(run_automatic_xcs_addon_flow(update, context))
        return

                                                                         
                                           
                                                                         
                                                                            
    if reprocessing_queue and current_reprocess_id_index < len(reprocessing_queue):
        unique_failure_id_to_retry = reprocessing_queue[current_reprocess_id_index]
        failure_details = failed_attempts_for_reprocess[unique_failure_id_to_retry]
        addon_code_to_retry = failure_details['package_code']
        addon_name_to_retry = failure_details['package_name']
        addon_price_to_retry = failure_details['price_bot']
        MAX_REPROCESS_ATTEMPTS = 3
        current_reprocess_attempt = reprocess_attempts_counter.setdefault(unique_failure_id_to_retry, 0)
        
        if current_reprocess_attempt >= MAX_REPROCESS_ATTEMPTS:
            logging.error(f"User {user_id} - {phone}: Percobaan ulang {addon_name_to_retry} gagal permanen setelah {MAX_REPROCESS_ATTEMPTS} kali.")
            automatic_xcs_flow_state['current_reprocess_id_index'] += 1
            asyncio.create_task(run_automatic_xcs_addon_flow(update, context))
            return

        user_data["registered_users"][str(user_id)]["balance"] -= addon_price_to_retry
        simpan_data_ke_db(user_data)
        logging.info(f"User {user_id} saldo dipotong Rp{addon_price_to_retry} untuk percobaan ulang ADD ON {addon_name_to_retry}.")
        
        reprocess_result = await api_clients.execute_single_purchase_30h(
            update, context, user_id, addon_code_to_retry, addon_name_to_retry, phone, access_token, "BALANCE", addon_price_to_retry,
            "automatic_xcs_addon_flow", current_reprocess_attempt + 1
        )
        reprocess_attempts_counter[unique_failure_id_to_retry] += 1

        if reprocess_result['success']:
            logging.info(f"User {user_id} - {phone}: Percobaan ulang ADD ON {addon_name_to_retry} berhasil.")
            await context.bot.edit_message_text(chat_id=user_id, message_id=status_message_id, text=f"✅ Percobaan ulang *{addon_name_to_retry}* berhasil!", parse_mode="Markdown")
                                                                                                   
            del failed_attempts_for_reprocess[unique_failure_id_to_retry]
        else:
            logging.warning(f"User {user_id} - {phone}: Percobaan ulang ADD ON {addon_name_to_retry} masih gagal.")
            await context.bot.edit_message_text(chat_id=user_id, message_id=status_message_id, text=f"❌ Percobaan ulang *{addon_name_to_retry}* masih gagal. Melanjutkan...", parse_mode="Markdown")

        automatic_xcs_flow_state['current_reprocess_id_index'] += 1
        await asyncio.sleep(10)
        asyncio.create_task(run_automatic_xcs_addon_flow(update, context))
        return

                                                                         
                                        
                                                                         
                                                                                                      
    if current_addon_index >= len(addons_to_process) and failed_attempts_for_reprocess and current_reprocess_id_index >= len(reprocessing_queue) and automatic_xcs_flow_state.get('reprocessing_pass_count', 1) < MAX_REPROCESSING_PASSES:
        automatic_xcs_flow_state['reprocessing_pass_count'] += 1
        automatic_xcs_flow_state['current_reprocess_id_index'] = 0                                  
        automatic_xcs_flow_state['reprocess_attempts_counter'] = {}                             
        
                                                                               
        automatic_xcs_flow_state['reprocessing_queue'] = list(failed_attempts_for_reprocess.keys())
        
        logging.info(f"User {user_id}: Memulai putaran proses ulang ke-{automatic_xcs_flow_state['reprocessing_pass_count']}.")
        
        await context.bot.edit_message_text(
            chat_id=user_id,
            message_id=status_message_id,
            text=f"⚠️ Beberapa paket masih gagal. Menunggu 1 menit sebelum melakukan upaya terakhir...",
            parse_mode="Markdown"
        )
        await asyncio.sleep(60)
        
        asyncio.create_task(run_automatic_xcs_addon_flow(update, context))
        return

                                                                         
                                                                                  
                                                                         
    if not automatic_xcs_flow_state['xcp_8gb_completed']:
        if failed_attempts_for_reprocess:
            final_error_text = f"❌ *Alur Otomatis Dihentikan* ❌\n\nBeberapa paket gagal permanen setelah {MAX_REPROCESSING_PASSES} putaran percobaan ulang. Pembelian *XCP 8GB* dibatalkan.\n\n*Paket yang Gagal Permanen:*\n"
            for fail_id, fail_details in failed_attempts_for_reprocess.items():
                final_error_text += f"- *{fail_details['package_name']}*: `{fail_details['error_message']}`\n"
            
            final_error_text += f"\nSaldo Anda saat ini: *Rp{user_data['registered_users'][str(user_id)]['balance']:,}*."
            await context.bot.edit_message_text(chat_id=user_id, message_id=status_message_id, text=final_error_text, parse_mode="Markdown")
            
            del context.user_data['automatic_xcs_flow_state']
            simpan_data_ke_db(user_data)
            await send_main_menu(update, context)
            return

        xcp_8gb_price_key = f"c03be70fb3523ac2ac440966d3a5920e_{payment_method_xcp_8gb}"
        if payment_method_xcp_8gb == "PULSA":
            xcp_8gb_price_key = "bdb392a7aa12b21851960b7e7d54af2c"
        
        xcp_8gb_code = "c03be70fb3523ac2ac440966d3a5920e"
        if payment_method_xcp_8gb == "PULSA":
            xcp_8gb_code = "bdb392a7aa12b21851960b7e7d54af2c"
            
        xcp_8gb_name = data_packages.CUSTOM_PACKAGE_PRICES.get(xcp_8gb_price_key, {}).get('display_name', 'XCP 8GB')
        xcp_8gb_price = data_packages.CUSTOM_PACKAGE_PRICES.get(xcp_8gb_price_key, {}).get('price_bot', 0)
        
        await context.bot.edit_message_text(chat_id=user_id, message_id=status_message_id, text=f"Mencoba membeli paket utama *{xcp_8gb_name}* untuk *{phone}*...", parse_mode="Markdown")
        
        xcp_8gb_purchase_result = await api_clients.execute_automatic_xc_purchase(
            update, context, user_id, xcp_8gb_code, xcp_8gb_name, phone, access_token, payment_method_xcp_8gb, xcp_8gb_price
        )

        if xcp_8gb_purchase_result['success']:
            final_summary_text = (
                f"🎉 *Alur pembelian XCS ADD ON otomatis untuk *{phone}* telah selesai!*\n\n"
                f"Semua paket Add-On dan paket utama *{xcp_8gb_name}* berhasil dibeli."
            )
            await context.bot.edit_message_text(chat_id=user_id, message_id=status_message_id, text=final_summary_text, parse_mode="Markdown")
            automatic_xcs_flow_state['xcp_8gb_completed'] = True
        else:
            await context.bot.edit_message_text(chat_id=user_id, message_id=status_message_id, text=f"❌ Pembelian paket utama *{xcp_8gb_name}* gagal: {xcp_8gb_purchase_result['error_message']}. Alur dihentikan.", parse_mode="Markdown")

        del context.user_data['automatic_xcs_flow_state']
        simpan_data_ke_db(user_data)
        await send_main_menu(update, context)

async def send_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_first_name = update.effective_user.first_name
    
    user_balance = user_data.get("registered_users", {}).get(str(user_id), {}).get("balance", 0)
    total_users = len(user_data.get("registered_users", {}))
    
    uptime_delta = datetime.now() - utils.bot_start_time
    days = uptime_delta.days
    hours, remainder = divmod(uptime_delta.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    uptime_str = f"{days}d:{hours}j:{minutes}m"

    stats_block = (
        "💜 D O R  X L  H O K A G E  L E G E N D  S T O R E 💜\n"
        "╔══════════════════════════════╗\n"
        f"║ 🪪 *Nama* : {user_first_name}\n"
        f"║ 🆔 *ID User* : `{user_id}`\n"
        f"║ 💰 *Saldo Anda* : `Rp{user_balance:,}`\n"
        "╠══════════════════════════════╣\n"
        "║ 📊 *S T A T I S T I K  B O T*\n"
        "╠══════════════════════════════╣\n"
        f"║ 👥 *Total Pengguna* : {total_users} user\n"
        f"║ ⏱️ *Uptime Bot* : {uptime_str}\n"
        "╚══════════════════════════════╝\n\n"
        "🌸 *~ Selamat Berbelanja Di Hokage Legend ~* 🌸\n"
    )

    original_welcome_block = (
        "💜 *💠 D O R  X L  H O K A G E  P R I C E  L I S T 💠* 💜\n"
        "═════════════════════════════════\n"
        "==== DEVELOPER SCRIPT BY : IKS STORE ====\n"
        "═════════════════════════════════\n"
        "╔══════════════════════════════╗\n"
        "║ 🟣 *PAKET BUNDLING SPECIAL* 🟣\n"
        "╠══════════════════════════════╣\n"
        "║ • XUTS: Rp5.200\n"
        "║ • XCS ADDS-ON: Rp7.600 (full add on)\n"
        "║ • XUTP: Rp5.200\n"
        "╠══════════════════════════════╣\n"
        "║ 💜 *HARGA SATUAN* 💜\n"
        "╠══════════════════════════════╣\n"
        "║ • ADD ON: Rp200/add on\n"
        "║ • XC 1+1GB: Rp5000\n"
        "║ • XCP 8GB: Rp5000\n"
        "╠══════════════════════════════╣\n"
        "║ 🟣 *PAKET LAINNYA* 🟣\n"
        "╠══════════════════════════════╣\n"
        "║ • XL VIDIO: Rp5000\n"
        "║ • XL IFLIX: Rp5000\n"
        "║ • *CEK MENU PAKET LAINNYA*\n"
        "╚══════════════════════════════╝\n\n"
        "🟣 *⚠️  P E N T I N G  D I B A C A  ⚠️* 🟣\n"
        "╔══════════════════════════════╗\n"
        "║ ⛔ *Paket Unofficial (Tanpa Garansi)*\n"
        "╠══════════════════════════════╣\n"
        "║ ‼️ *WAJIB CEK TUTORIAL BELI*\n"
        "║ ‼️ *Cek Kuota terlebih dahulu!*\n"
        "║ ‼️ *Hindari semua jenis kuota XTRA COMBO*\n"
        "║ ❌ *Unreg paket ini jika ada* ❌\n"
        "╠══════════════════════════════╣\n"
        "║ - XTRA COMBO ❌\n"
        "║ - XTRA COMBO VIP ❌\n"
        "║ - XTRA COMBO MINI ❌\n"
        "║ - XTRA COMBO VIP PLUS ❌\n"
        "╠══════════════════════════════╣\n"
        "║ 💜 *Pastikan semua langkah dilakukan dengan benar* 💜\n"
        "╚══════════════════════════════╝\n\n"
        "🌸 *~ Silakan pilih menu di bawah ini ~* 🌸"
    )
    text = stats_block + original_welcome_block
    
    keyboard = [
        [InlineKeyboardButton("🔮 LOGIN OTP", callback_data='show_login_options'),
         InlineKeyboardButton("🆔 NOMOR SAYA", callback_data="akun_saya")],
        [InlineKeyboardButton("⚡ Tembak Paket", callback_data='tembak_paket')],
        [InlineKeyboardButton("👾 XL VIDIO", callback_data='vidio_xl_menu'),
         InlineKeyboardButton("🍇 XL IFLIX", callback_data='iflix_xl_menu')],
        [InlineKeyboardButton("📶 Cek Kuota", callback_data='cek_kuota'),
         InlineKeyboardButton("💰 Cek Saldo", callback_data='cek_saldo')],
        [InlineKeyboardButton("📚 Tutorial Beli", callback_data='tutorial_beli'),
         InlineKeyboardButton("💸 Top Up Saldo", callback_data='top_up_saldo')],
        [InlineKeyboardButton("📦 Paket Lainnya", callback_data='show_custom_packages')],
        [InlineKeyboardButton("💜 Kontak Admin", url=f"https://t.me/{config.ADMIN_USERNAME}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(
                text,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
        except Exception as e:
            logging.warning(f"Gagal mengedit pesan menu untuk user {user_id}: {e}. Mengirim pesan baru.")
            await context.bot.send_message(
                user_id,
                text,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
    else:
        await update.message.reply_text(
            text,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

async def check_access(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id == config.ADMIN_ID:
        return True

    if user_id in user_data.get("blocked_users", []):
        message_text = "ANDA TELAH DIBLOKIR DAN TIDAK DAPAT MENGAKSES BOT INI. Silakan hubungi admin."
        if update.callback_query:
            await update.callback_query.answer(message_text, show_alert=True)
        elif update.message:
            await update.message.reply_text(message_text)
        logging.warning(f"Akses ditolak untuk user {user_id} (diblokir).")
        return False

    return True

# ================================================================
# ==  Salin semua fungsi handler Anda yang lain di sini...      ==
# ==  Contoh: `run_automatic_purchase_flow`, `admin_menu`, dll. ==
# ================================================================
