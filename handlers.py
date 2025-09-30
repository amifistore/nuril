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
from datetime import datetime, timezone

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
bot_messages = {}
login_counter = {}
bot_start_time = datetime.now()


# ==============================================================================
# == SEMUA FUNGSI DARI FILE ASLI ANDA TELAH DISALIN DAN DISESUAIKAN DI SINI ==
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


async def run_automatic_purchase_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data_entry = user_data["registered_users"].get(str(user_id), {})

    current_phone = context.user_data.get('automatic_purchase_phone')
    access_token = context.user_data.get('automatic_purchase_token')
    payment_method_for_xc = context.user_data.get('automatic_purchase_payment_method')

    if not current_phone or not access_token:
        await context.bot.send_message(user_id, "Sesi pembelian otomatis tidak valid atau kedaluwarsa. Silakan mulai ulang.")
        await send_main_menu(update, context)
        return

    user_data_entry.setdefault('accounts', {}).setdefault(current_phone, {})
    automatic_flow_state = user_data_entry['accounts'][current_phone].setdefault('automatic_flow_state', {
        'xuts_completed': False,
        'xc_completed': False,
        'xuts_retry_count': 0,
        'current_step': 'xuts',
        'last_xuts_attempt_time': None,
        'status_message_id': None,
        'qris_countdown_message_id': None
    })

    status_message_id = automatic_flow_state['status_message_id']

    if not status_message_id:
        msg = await context.bot.send_message(user_id, f"Memulai alur pembelian otomatis untuk *{current_phone}*...", parse_mode="Markdown")
        automatic_flow_state['status_message_id'] = msg.message_id
        status_message_id = msg.message_id
    else:
        try:
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_message_id,
                text=f"Melanjutkan alur pembelian otomatis untuk *{current_phone}*...",
                parse_mode="Markdown"
            )
        except Exception as e:
            logging.warning(f"Gagal mengedit pesan status awal untuk {current_phone}: {e}. Mengirim pesan baru.")
            msg = await context.bot.send_message(user_id, f"Melanjutkan alur pembelian otomatis untuk *{current_phone}*...", parse_mode="Markdown")
            automatic_flow_state['status_message_id'] = msg.message_id
            status_message_id = msg.message_id
    simpan_data_ke_db(user_data)

    if automatic_flow_state['current_step'] == 'xuts' and not automatic_flow_state['xuts_completed']:
        if automatic_flow_state['xuts_retry_count'] >= 5:
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_message_id,
                text=f"❌ Gagal membeli XUTS untuk *{current_phone}* setelah {automatic_flow_state['xuts_retry_count']} percobaan. Melanjutkan ke pembelian XC 1+1GB.",
                parse_mode="Markdown"
            )
            logging.info(f"User {user_id} - {current_phone}: XUTS gagal setelah {automatic_flow_state['xuts_retry_count']} percobaan. Lanjut ke XC.")
            automatic_flow_state['xuts_completed'] = True
            automatic_flow_state['current_step'] = 'xc'
            simpan_data_ke_db(user_data)
            asyncio.create_task(run_automatic_purchase_flow(update, context))
            return

        xuts_price = data_packages.CUSTOM_PACKAGE_PRICES.get(data_packages.XUTS_PACKAGE_CODE, {}).get('price_bot', 0)
        if xuts_price <= 0:
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_message_id,
                text=f"❌ Harga paket XUTS tidak ditemukan atau tidak valid. Menghentikan alur otomatis untuk *{current_phone}*.",
                parse_mode="Markdown"
            )
            logging.error(f"User {user_id} - {current_phone}: Harga XUTS tidak valid ({xuts_price}). Menghentikan alur.")
            if 'automatic_flow_state' in user_data_entry['accounts'][current_phone]:
                del user_data_entry['accounts'][current_phone]['automatic_flow_state']
            simpan_data_ke_db(user_data)
            await send_main_menu(update, context)
            return

        user_current_balance = user_data_entry.get("balance", 0)
        if user_current_balance < xuts_price:
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_message_id,
                text=f"❌ Saldo Anda tidak cukup untuk membeli paket XUTS (harga bot: Rp{xuts_price:,}). Saldo Anda saat ini: Rp{user_current_balance:,}. Menghentikan alur otomatis untuk *{current_phone}*.",
                parse_mode="Markdown"
            )
            logging.info(f"User {user_id} - {current_phone}: Saldo tidak cukup untuk XUTS. Menghentikan alur.")
            if 'automatic_flow_state' in user_data_entry['accounts'][current_phone]:
                del user_data_entry['accounts'][current_phone]['automatic_flow_state']
            simpan_data_ke_db(user_data)
            await send_main_menu(update, context)
            return

        automatic_flow_state['xuts_retry_count'] += 1
        await context.bot.edit_message_text(
            chat_id=user_id,
            message_id=status_message_id,
            text=f"Mencoba membeli XUTS untuk *{current_phone}*... (Percobaan ke-{automatic_flow_state['xuts_retry_count']})",
            parse_mode="Markdown"
        )
        simpan_data_ke_db(user_data)

        xuts_purchase_result = await api_clients.execute_automatic_xuts_purchase(
            update, context, user_id, data_packages.XUTS_PACKAGE_CODE, current_phone, access_token, "PULSA", xuts_price, automatic_flow_state['xuts_retry_count']
        )

        if xuts_purchase_result['success']:
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_message_id,
                text=f"✅ Pembelian XUTS berhasil untuk *{current_phone}*! Melanjutkan ke pembelian XC 1+1GB.",
                parse_mode="Markdown"
            )
            logging.info(f"User {user_id} - {current_phone}: XUTS berhasil. Lanjut ke XC.")
            automatic_flow_state['xuts_completed'] = True
            automatic_flow_state['current_step'] = 'xc'
            simpan_data_ke_db(user_data)
            asyncio.create_task(run_automatic_purchase_flow(update, context))
        elif xuts_purchase_result.get('specific_action') == 'countdown_retry':
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_message_id,
                text=f"⚠️ XUTS pending untuk *{current_phone}*. Bot akan mencoba kembali dalam 10 menit. Mohon tunggu...",
                parse_mode="Markdown"
            )
            logging.info(f"User {user_id} - {current_phone}: XUTS pending (MyXL message). Memulai countdown 10 menit.")

            countdown_message_text = f"⏳ Menunggu 10 menit sebelum mencoba XUTS lagi untuk *{current_phone}* (percobaan ke-{automatic_flow_state['xuts_retry_count']}).\nSisa waktu: *10 menit*."
            countdown_msg = await context.bot.send_message(user_id, countdown_message_text, parse_mode="Markdown")
            automatic_flow_state['qris_countdown_message_id'] = countdown_msg.message_id
            simpan_data_ke_db(user_data)

            for i in range(9, -1, -1):
                await asyncio.sleep(60)
                if i > 0:
                    try:
                        await context.bot.edit_message_text(
                            chat_id=user_id,
                            message_id=automatic_flow_state['qris_countdown_message_id'],
                            text=f"⏳ Menunggu 10 menit sebelum mencoba XUTS lagi untuk *{current_phone}* (percobaan ke-{automatic_flow_state['xuts_retry_count']}).\nSisa waktu: *{i} menit*.",
                            parse_mode="Markdown"
                        )
                    except Exception as e:
                        if "message is not modified" not in str(e) and "message to edit not found" not in str(e):
                            logging.warning(f"Gagal mengupdate countdown XUTS untuk user {user_id} - {current_phone}: {e}")
                        break
                else:
                    try:
                        await context.bot.edit_message_text(
                            chat_id=user_id,
                            message_id=automatic_flow_state['qris_countdown_message_id'],
                            text="✅ Waktu jeda XUTS selesai. Mencoba kembali...",
                            parse_mode="Markdown"
                        )
                    except Exception as e:
                        logging.warning(f"Gagal mengedit pesan countdown XUTS selesai untuk {current_phone}: {e}")

            if 'qris_countdown_message_id' in automatic_flow_state:
                try:
                    await context.bot.delete_message(chat_id=user_id, message_id=automatic_flow_state['qris_countdown_message_id'])
                    del automatic_flow_state['qris_countdown_message_id']
                    simpan_data_ke_db(user_data)
                except Exception as e:
                    logging.warning(f"Gagal menghapus pesan countdown XUTS untuk user {user_id} - {current_phone}: {e}")

            asyncio.create_task(run_automatic_purchase_flow(update, context))
        else:
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_message_id,
                text=f"❌ Pembelian XUTS untuk *{current_phone}* gagal: {xuts_purchase_result['error_message']}. Mencoba lagi...",
                parse_mode="Markdown"
            )
            logging.info(f"User {user_id} - {current_phone}: XUTS gagal. Mencoba lagi.")
            asyncio.create_task(run_automatic_purchase_flow(update, context))
        return

    if automatic_flow_state['current_step'] == 'xc' and not automatic_flow_state['xc_completed']:
                                                                                            
        xc_package_code = ""
        xc_price_key = ""
        xc_package_name_display = ""

        if payment_method_for_xc == "DANA":
            xc_package_code = data_packages.XC1PLUS1GB_DANA_CODE
            xc_price_key = data_packages.XC1PLUS1GB_DANA_CODE
            xc_package_name_display = data_packages.CUSTOM_PACKAGE_PRICES.get(xc_price_key, {}).get('display_name', 'XC 1+1GB DANA')
        elif payment_method_for_xc == "BALANCE":
            xc_package_code = data_packages.XC1PLUS1GB_PULSA_CODE
            xc_price_key = data_packages.XC1PLUS1GB_PULSA_CODE
            xc_package_name_display = data_packages.CUSTOM_PACKAGE_PRICES.get(xc_price_key, {}).get('display_name', 'XC 1+1GB PULSA')
        elif payment_method_for_xc == "QRIS":
            xc_package_code = data_packages.XC1PLUS1GB_DANA_CODE                                   
            xc_price_key = data_packages.XC1PLUS1GB_QRIS_CODE                                     
            xc_package_name_display = data_packages.CUSTOM_PACKAGE_PRICES.get(xc_price_key, {}).get('display_name', 'XC 1+1GB QRIS')
        else:
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_message_id,
                text=f"❌ Metode pembayaran tidak valid untuk XC 1+1GB. Menghentikan alur otomatis untuk *{current_phone}*.",
                parse_mode="Markdown"
            )
            logging.error(f"User {user_id} - {current_phone}: Metode pembayaran XC 1+1GB tidak valid ({payment_method_for_xc}). Menghentikan alur.")
            if 'automatic_flow_state' in user_data_entry['accounts'][current_phone]:
                del user_data_entry['accounts'][current_phone]['automatic_flow_state']
            simpan_data_ke_db(user_data)
            await send_main_menu(update, context)
            return
        
        xc_price = data_packages.CUSTOM_PACKAGE_PRICES.get(xc_price_key, {}).get('price_bot', 0)
        
        if xc_price <= 0:
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_message_id,
                text=f"❌ Harga paket {xc_package_name_display} tidak ditemukan atau tidak valid. Menghentikan alur otomatis untuk *{current_phone}*.",
                parse_mode="Markdown"
            )
            logging.error(f"User {user_id} - {current_phone}: Harga XC 1+1GB tidak valid ({xc_price}). Menghentikan alur.")
            if 'automatic_flow_state' in user_data_entry['accounts'][current_phone]:
                del user_data_entry['accounts'][current_phone]['automatic_flow_state']
            simpan_data_ke_db(user_data)
            await send_main_menu(update, context)
            return

        user_current_balance = user_data_entry.get("balance", 0)
        if user_current_balance < xc_price:
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_message_id,
                text=f"❌ Saldo Anda tidak cukup untuk membeli paket {xc_package_name_display} (harga bot: Rp{xc_price:,}). Saldo Anda saat ini: Rp{user_current_balance:,}. Menghentikan alur otomatis untuk *{current_phone}*.",
                parse_mode="Markdown"
            )
            logging.info(f"User {user_id} - {current_phone}: Saldo tidak cukup untuk XC 1+1GB. Menghentikan alur.")
            if 'automatic_flow_state' in user_data_entry['accounts'][current_phone]:
                del user_data_entry['accounts'][current_phone]['automatic_flow_state']
            simpan_data_ke_db(user_data)
            await send_main_menu(update, context)
            return

        user_data["registered_users"][str(user_id)]["balance"] -= xc_price
        simpan_data_ke_db(user_data)
        await context.bot.send_message(user_id, f"Saldo Anda terpotong: *Rp{xc_price:,}* untuk pembelian {xc_package_name_display}. Saldo tersisa: *Rp{user_data['registered_users'][str(user_id)]['balance']:,}*.", parse_mode="Markdown")
        logging.info(f"User {user_id} - {current_phone}: saldo dipotong Rp{xc_price} untuk XC 1+1GB.")

        await context.bot.edit_message_text(
            chat_id=user_id,
            message_id=status_message_id,
            text=f"Mencoba membeli {xc_package_name_display} untuk *{current_phone}*...",
            parse_mode="Markdown"
        )
        simpan_data_ke_db(user_data)

        xc_purchase_result = await api_clients.execute_automatic_xc_purchase(
            update, context, user_id, xc_package_code, xc_package_name_display, current_phone, access_token, payment_method_for_xc, xc_price                                  
        )

        if xc_purchase_result['success']:
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_message_id,
                text=f"✅ Pembelian {xc_package_name_display} untuk *{current_phone}* berhasil! Alur otomatis selesai.",
                parse_mode="Markdown"
            )
            logging.info(f"User {user_id} - {current_phone}: XC 1+1GB berhasil. Alur selesai.")
            automatic_flow_state['xc_completed'] = True
            automatic_flow_state['current_step'] = 'finished'
            if 'automatic_flow_state' in user_data_entry['accounts'][current_phone]:
                del user_data_entry['accounts'][current_phone]['automatic_flow_state']
            simpan_data_ke_db(user_data)
            await send_main_menu(update, context)
        else:
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_message_id,
                text=f"❌ Pembelian {xc_package_name_display} untuk *{current_phone}* gagal: {xc_purchase_result['error_message']}. Alur otomatis dihentikan.",
                parse_mode="Markdown"
            )
            logging.info(f"User {user_id} - {current_phone}: XC 1+1GB gagal. Alur dihentikan.")
            if 'automatic_flow_state' in user_data_entry['accounts'][current_phone]:
                del user_data_entry['accounts'][current_phone]['automatic_flow_state']
            simpan_data_ke_db(user_data)
            await send_main_menu(update, context)
        return

    if automatic_flow_state['current_step'] == 'finished':
        logging.info(f"User {user_id} - {current_phone}: Automatic flow completed (final cleanup).")
        if 'automatic_flow_state' in user_data_entry['accounts'][current_phone]:
            del user_data_entry['accounts'][current_phone]['automatic_flow_state']
        simpan_data_ke_db(user_data)
        await send_main_menu(update, context)
        return

async def run_automatic_xutp_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data_entry = user_data["registered_users"].get(str(user_id), {})

    current_phone = context.user_data.get('xutp_purchase_phone')
    access_token = context.user_data.get('xutp_purchase_token')
    payment_method_for_xcp_8gb = context.user_data.get('xutp_purchase_payment_method')

    if not current_phone or not access_token:
        await context.bot.send_message(user_id, "Sesi pembelian XUTP otomatis tidak valid atau kedaluwarsa. Silakan mulai ulang.")
        await send_main_menu(update, context)
        return

                                                               
    user_data_entry.setdefault('accounts', {}).setdefault(current_phone, {})
    xutp_flow_state = user_data_entry['accounts'][current_phone].setdefault('xutp_flow_state', {
        'initial_package_completed': False,                                   
        'xcp_8gb_completed': False,                
        'initial_package_retry_count': 0,
        'current_step': 'initial_package',                                           
        'last_initial_package_attempt_time': None,                           
        'status_message_id': None,                        
        'qris_countdown_message_id': None                  
    })

    status_message_id = xutp_flow_state['status_message_id']

                                              
    if not status_message_id:
        msg = await context.bot.send_message(user_id, f"Memulai alur pembelian XUTP otomatis untuk *{current_phone}*...", parse_mode="Markdown")
        xutp_flow_state['status_message_id'] = msg.message_id
        status_message_id = msg.message_id
    else:
        try:
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_message_id,
                text=f"Melanjutkan alur pembelian XUTP otomatis untuk *{current_phone}*...",
                parse_mode="Markdown"
            )
        except Exception as e:
            logging.warning(f"Gagal mengedit pesan status awal XUTP untuk {current_phone}: {e}. Mengirim pesan baru.")
            msg = await context.bot.send_message(user_id, f"Melanjutkan alur pembelian XUTP otomatis untuk *{current_phone}*...", parse_mode="Markdown")
            xutp_flow_state['status_message_id'] = msg.message_id
            status_message_id = msg.message_id
    simpan_data_ke_db(user_data)

                                                                      
    if xutp_flow_state['current_step'] == 'initial_package' and not xutp_flow_state['initial_package_completed']:
        initial_package_code = data_packages.XUTP_INITIAL_PACKAGE_CODE
        initial_package_name_display = data_packages.CUSTOM_PACKAGE_PRICES.get(initial_package_code, {}).get('display_name', 'ADD ON PREMIUM')
        initial_package_price = data_packages.CUSTOM_PACKAGE_PRICES.get(initial_package_code, {}).get('price_bot', 0)

        if xutp_flow_state['initial_package_retry_count'] >= 5:                                   
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_message_id,
                text=f"❌ Gagal membeli {initial_package_name_display} untuk *{current_phone}* setelah {xutp_flow_state['initial_package_retry_count']} percobaan. Melanjutkan ke pembelian XCP 8GB.",
                parse_mode="Markdown"
            )
            logging.info(f"User {user_id} - {current_phone}: {initial_package_name_display} gagal setelah {xutp_flow_state['initial_package_retry_count']} percobaan. Lanjut ke XCP 8GB.")
            xutp_flow_state['initial_package_completed'] = True
            xutp_flow_state['current_step'] = 'xcp_8gb'
            simpan_data_ke_db(user_data)
            asyncio.create_task(run_automatic_xutp_flow(update, context))
            return

        if initial_package_price <= 0:
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_message_id,
                text=f"❌ Harga paket {initial_package_name_display} tidak ditemukan atau tidak valid. Menghentikan alur XUTP otomatis untuk *{current_phone}*.",
                parse_mode="Markdown"
            )
            logging.error(f"User {user_id} - {current_phone}: Harga {initial_package_name_display} tidak valid ({initial_package_price}). Menghentikan alur.")
            if 'xutp_flow_state' in user_data_entry['accounts'][current_phone]:
                del user_data_entry['accounts'][current_phone]['xutp_flow_state']
            simpan_data_ke_db(user_data)
            await send_main_menu(update, context)
            return

        user_current_balance = user_data_entry.get("balance", 0)
        if user_current_balance < initial_package_price:
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_message_id,
                text=f"❌ Saldo Anda tidak cukup untuk membeli paket {initial_package_name_display} (harga bot: Rp{initial_package_price:,}). Saldo Anda saat ini: Rp{user_current_balance:,}. Menghentikan alur XUTP otomatis untuk *{current_phone}*.",
                parse_mode="Markdown"
            )
            logging.info(f"User {user_id} - {current_phone}: Saldo tidak cukup untuk {initial_package_name_display}. Menghentikan alur.")
            if 'xutp_flow_state' in user_data_entry['accounts'][current_phone]:
                del user_data_entry['accounts'][current_phone]['xutp_flow_state']
            simpan_data_ke_db(user_data)
            await send_main_menu(update, context)
            return

        user_data["registered_users"][str(user_id)]["balance"] -= initial_package_price
        simpan_data_ke_db(user_data)
        await context.bot.send_message(user_id, f"Saldo Anda terpotong: *Rp{initial_package_price:,}* untuk percobaan pembelian {initial_package_name_display}. Saldo tersisa: *Rp{user_data['registered_users'][str(user_id)]['balance']:,}*.", parse_mode="Markdown")
        logging.info(f"User {user_id} - {current_phone}: saldo dipotong Rp{initial_package_price} untuk {initial_package_name_display}.")

        xutp_flow_state['initial_package_retry_count'] += 1
        await context.bot.edit_message_text(
            chat_id=user_id,
            message_id=status_message_id,
            text=f"Mencoba membeli {initial_package_name_display} untuk *{current_phone}*... (Percobaan ke-{xutp_flow_state['initial_package_retry_count']})",
            parse_mode="Markdown"
        )
        simpan_data_ke_db(user_data)

                                                                                            
        initial_purchase_result = await api_clients.execute_single_purchase_30h(
            update, context, user_id, initial_package_code, initial_package_name_display, current_phone, access_token, "BALANCE", initial_package_price, "xutp_method_selection_menu", xutp_flow_state['initial_package_retry_count']
        )

        if initial_purchase_result['success']:
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_message_id,
                text=f"✅ Pembelian {initial_package_name_display} berhasil untuk *{current_phone}*! Melanjutkan ke pembelian XCP 8GB.",
                parse_mode="Markdown"
            )
            logging.info(f"User {user_id} - {current_phone}: {initial_package_name_display} berhasil. Lanjut ke XCP 8GB.")
            xutp_flow_state['initial_package_completed'] = True
            xutp_flow_state['current_step'] = 'xcp_8gb'
            simpan_data_ke_db(user_data)
            asyncio.create_task(run_automatic_xutp_flow(update, context))
        elif initial_purchase_result.get('specific_action') == 'countdown_retry':
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_message_id,
                text=f"⚠️ {initial_package_name_display} pending untuk *{current_phone}*. Bot akan mencoba kembali dalam 10 menit. Mohon tunggu...",
                parse_mode="Markdown"
            )
            logging.info(f"User {user_id} - {current_phone}: {initial_package_name_display} pending (MyXL message). Memulai countdown 10 menit.")

            countdown_message_text = f"⏳ Menunggu 10 menit sebelum mencoba {initial_package_name_display} lagi untuk *{current_phone}* (percobaan ke-{xutp_flow_state['initial_package_retry_count']}).\nSisa waktu: *10 menit*."
            countdown_msg = await context.bot.send_message(user_id, countdown_message_text, parse_mode="Markdown")
            xutp_flow_state['qris_countdown_message_id'] = countdown_msg.message_id
            simpan_data_ke_db(user_data)

            for i in range(9, -1, -1):
                await asyncio.sleep(60)
                if i > 0:
                    try:
                        await context.bot.edit_message_text(
                            chat_id=user_id,
                            message_id=xutp_flow_state['qris_countdown_message_id'],
                            text=f"⏳ Menunggu 10 menit sebelum mencoba {initial_package_name_display} lagi untuk *{current_phone}* (percobaan ke-{xutp_flow_state['initial_package_retry_count']}).\nSisa waktu: *{i} menit*.",
                            parse_mode="Markdown"
                        )
                    except Exception as e:
                        if "message is not modified" not in str(e) and "message to edit not found" not in str(e):
                            logging.warning(f"Gagal mengupdate countdown XUTP initial package untuk user {user_id} - {current_phone}: {e}")
                        break
                else:
                    try:
                        await context.bot.edit_message_text(
                            chat_id=user_id,
                            message_id=xutp_flow_state['qris_countdown_message_id'],
                            text="✅ Waktu jeda XUTP initial package selesai. Mencoba kembali...",
                            parse_mode="Markdown"
                        )
                    except Exception as e:
                        logging.warning(f"Gagal mengedit pesan countdown XUTP initial package selesai untuk {current_phone}: {e}")

            if 'qris_countdown_message_id' in xutp_flow_state:
                try:
                    await context.bot.delete_message(chat_id=user_id, message_id=xutp_flow_state['qris_countdown_message_id'])
                    del xutp_flow_state['qris_countdown_message_id']
                    simpan_data_ke_db(user_data)
                except Exception as e:
                    logging.warning(f"Gagal menghapus pesan countdown XUTP initial package untuk user {user_id} - {current_phone}: {e}")

            asyncio.create_task(run_automatic_xutp_flow(update, context))
        else:
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_message_id,
                text=f"❌ Pembelian {initial_package_name_display} untuk *{current_phone}* gagal: {initial_purchase_result['error_message']}. Mencoba lagi...",
                parse_mode="Markdown"
            )
            logging.info(f"User {user_id} - {current_phone}: {initial_package_name_display} gagal. Mencoba lagi.")
            asyncio.create_task(run_automatic_xutp_flow(update, context))
        return

                                      
    if xutp_flow_state['current_step'] == 'xcp_8gb' and not xutp_flow_state['xcp_8gb_completed']:
        xcp_8gb_package_code = None
        xcp_8gb_price_key = None
        
        if payment_method_for_xcp_8gb == "DANA":
            xcp_8gb_package_code = data_packages.XCP_8GB_DANA_CODE_FOR_XUTP
            xcp_8gb_price_key = data_packages.XCP_8GB_DANA_CODE_FOR_XUTP
        elif payment_method_for_xcp_8gb == "PULSA":
            xcp_8gb_package_code = data_packages.XCP_8GB_PULSA_CODE_FOR_XUTP
            xcp_8gb_price_key = data_packages.XCP_8GB_PULSA_CODE_FOR_XUTP
        elif payment_method_for_xcp_8gb == "QRIS":
            xcp_8gb_package_code = data_packages.XCP_8GB_DANA_CODE_FOR_XUTP                                             
            xcp_8gb_price_key = data_packages.XCP_8GB_QRIS_CODE_FOR_XUTP                                 
        
        xcp_8gb_name = data_packages.CUSTOM_PACKAGE_PRICES.get(xcp_8gb_price_key, {}).get('display_name', 'XCP 8GB')

        if xcp_8gb_price_key is None or xcp_8gb_package_code is None:
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_message_id,
                text=f"❌ Konfigurasi paket XCP 8GB untuk XUTP tidak valid. Menghentikan alur otomatis untuk *{current_phone}*.",
                parse_mode="Markdown"
            )
            logging.error(f"User {user_id} - {current_phone}: Konfigurasi XCP 8GB untuk XUTP tidak valid.")
            if 'xutp_flow_state' in user_data_entry['accounts'][current_phone]:
                del user_data_entry['accounts'][current_phone]['xutp_flow_state']
            simpan_data_ke_db(user_data)
            await send_main_menu(update, context)
            return

        xcp_8gb_price = data_packages.CUSTOM_PACKAGE_PRICES.get(xcp_8gb_price_key, {}).get('price_bot', 0)
        
        if xcp_8gb_price <= 0:
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_message_id,
                text=f"❌ Harga paket {xcp_8gb_name} tidak ditemukan atau tidak valid. Menghentikan alur XUTP otomatis untuk *{current_phone}*.",
                parse_mode="Markdown"
            )
            logging.error(f"User {user_id} - {current_phone}: Harga XCP 8GB tidak valid ({xcp_8gb_price}). Menghentikan alur.")
            if 'xutp_flow_state' in user_data_entry['accounts'][current_phone]:
                del user_data_entry['accounts'][current_phone]['xutp_flow_state']
            simpan_data_ke_db(user_data)
            await send_main_menu(update, context)
            return

        user_current_balance = user_data_entry.get("balance", 0)
        if user_current_balance < xcp_8gb_price:
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_message_id,
                text=f"❌ Saldo Anda tidak cukup untuk membeli paket {xcp_8gb_name} (harga bot: Rp{xcp_8gb_price:,}). Saldo Anda saat ini: Rp{user_current_balance:,}. Menghentikan alur XUTP otomatis untuk *{current_phone}*.",
                parse_mode="Markdown"
            )
            logging.info(f"User {user_id} - {current_phone}: Saldo tidak cukup untuk XCP 8GB. Menghentikan alur.")
            if 'xutp_flow_state' in user_data_entry['accounts'][current_phone]:
                del user_data_entry['accounts'][current_phone]['xutp_flow_state']
            simpan_data_ke_db(user_data)
            await send_main_menu(update, context)
            return
        
        user_data["registered_users"][str(user_id)]["balance"] -= xcp_8gb_price
        simpan_data_ke_db(user_data)
        await context.bot.send_message(user_id, f"Saldo Anda terpotong: *Rp{xcp_8gb_price:,}* untuk pembelian {xcp_8gb_name}. Saldo tersisa: *Rp{user_data['registered_users'][str(user_id)]['balance']:,}*.", parse_mode="Markdown")
        logging.info(f"User {user_id} - {current_phone}: saldo dipotong Rp{xcp_8gb_price} untuk XCP 8GB.")

        await context.bot.edit_message_text(
            chat_id=user_id,
            message_id=status_message_id,
            text=f"Mencoba membeli {xcp_8gb_name} untuk *{current_phone}*...",
            parse_mode="Markdown"
        )
        simpan_data_ke_db(user_data)

        xcp_8gb_purchase_result = await api_clients.execute_automatic_xc_purchase(
            update, context, user_id, xcp_8gb_package_code, xcp_8gb_name, current_phone, access_token, payment_method_for_xcp_8gb, xcp_8gb_price
        )

        if xcp_8gb_purchase_result['success']:
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_message_id,
                text=f"✅ Pembelian {xcp_8gb_name} untuk *{current_phone}* berhasil! Alur XUTP otomatis selesai.",
                parse_mode="Markdown"
            )
            logging.info(f"User {user_id} - {current_phone}: XCP 8GB berhasil. Alur XUTP selesai.")
            xutp_flow_state['xcp_8gb_completed'] = True
            if 'xutp_flow_state' in user_data_entry['accounts'][current_phone]:
                del user_data_entry['accounts'][current_phone]['xutp_flow_state']
            simpan_data_ke_db(user_data)
            await send_main_menu(update, context)
        else:
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_message_id,
                text=f"❌ Pembelian {xcp_8gb_name} untuk *{current_phone}* gagal: {xcp_8gb_purchase_result['error_message']}. Alur XUTP otomatis dihentikan.",
                parse_mode="Markdown"
            )
            logging.info(f"User {user_id} - {current_phone}: XCP 8GB gagal. Alur XUTP dihentikan.")
            if 'xutp_flow_state' in user_data_entry['accounts'][current_phone]:
                del user_data_entry['accounts'][current_phone]['xutp_flow_state']
            simpan_data_ke_db(user_data)
            await send_main_menu(update, context)
        return

                                                     
    if xutp_flow_state['current_step'] == 'finished':
        logging.info(f"User {user_id} - {current_phone}: XUTP Automatic flow completed (final cleanup).")
        if 'xutp_flow_state' in user_data_entry['accounts'][current_phone]:
            del user_data_entry['accounts'][current_phone]['xutp_flow_state']
        simpan_data_ke_db(user_data)
        await send_main_menu(update, context)
        return


#
# ... (DAN SETERUSNYA)
#
# Di sini Anda harus menyalin SEMUA FUNGSI LAINNYA dari file asli, seperti:
# - send_uts_menu
# - send_manual_uts_selection_menu
# - send_xutp_method_selection_menu
# - send_bypass_menu
# - button
# - handle_text
# - Semua fungsi `admin_*`
# - Semua fungsi `execute_*`
# - Semua fungsi `request_otp_*`
# - dll.
#
# Pastikan tidak ada satupun fungsi yang tertinggal.
#
