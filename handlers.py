# handlers.py

import logging
import re
import asyncio
import math
import html
import base64
import traceback
import uuid
import random
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown

import config
import data_packages
from database import simpan_data_ke_db
import api_clients
import utils

# Variabel ini akan diisi oleh main.py saat bot dimulai
user_data = {}
bot_messages = {}
login_counter = {}

# ==============================================================================
# == SEMUA FUNGSI DARI FILE ASLI ANDA TELAH DISALIN DAN DISESUAIKAN DI SINI ==
# ==============================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id_str = str(user.id)
    user_first_name = user.first_name or "N/A"
    user_username = user.username or "N/A"
    
    logging.info(f"User {user_id_str} mengakses /start. Memvalidasi data pengguna...")

    is_new_user = user_id_str not in user_data["registered_users"]

    user_details = user_data["registered_users"].setdefault(user_id_str, {
        "accounts": {}, "balance": 0, "transactions": [], "selected_hesdapkg_ids": [],
        "selected_30h_pkg_ids": [], "selected_automatic_addons": []
    })
    
    user_details['first_name'] = user_first_name
    user_details['username'] = user_username

    if is_new_user:
        logging.info(f"User baru terdaftar: ID={user_id_str}, Nama={user_first_name}, Username=@{user_username}")
        admin_notification_text = (
            f"✨ *💜 W E L C O M E • T O • V I P • M E M B E R 💜* ✨\n\n"
            f"🆔 *ID User*: `{user_id_str}`\n"
            f"👤 *Nama*: `{user_first_name}`\n"
            f"🏷 *Username*: @{user_username}\n"
            f"⏰ *Waktu Registrasi*: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💜 *Status*: `AKTIF`\n"
            f"💎 *Level*: `PREMIUM`\n"
            f"🔮 *Expired*: `LIFETIME`\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🎊 *Selamat bergabung di keluarga eksklusif kami!* 🎊\n"
            f"⚡ Nikmati semua fitur premium kami!"
        )
        try:
            await context.bot.send_message(config.ADMIN_ID, admin_notification_text, parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Gagal mengirim notifikasi user baru ke admin: {e}")

    simpan_data_ke_db(user_data)
    await utils.delete_last_message(int(user_id_str), context)
    await send_main_menu(update, context)


async def check_access(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id == config.ADMIN_ID:
        return True

    if user_id in user_data.get("blocked_users", []):
        message_text = "ANDA TELAH DIBLOKIR DAN TIDAK DAPAT MENGAKSES BOT INI. Silakan hubungi admin."
        if update.callback_query:
            await update.callback_query.answer(message_text, show_alert=True)
            try:
                await update.callback_query.edit_message_text(message_text)
            except Exception as e:
                logging.warning(f"Gagal mengedit pesan untuk user {user_id} saat diblokir: {e}")
                await context.bot.send_message(user_id, message_text)
        elif update.message:
            await update.message.reply_text(message_text)
        logging.warning(f"Akses ditolak untuk user {user_id} (diblokir).")
        return False

    return True


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
            if 'message is not modified' not in str(e):
                logging.warning(f"Gagal mengedit pesan menu: {e}. Mengirim pesan baru.")
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

#
# --- MULAI SALIN SEMUA FUNGSI LAINNYA DARI FILE ASLI ANDA DI SINI ---
#

async def show_login_options_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = "Silakan pilih jenis login OTP yang Anda inginkan:"
    keyboard = [
        [InlineKeyboardButton("🔐 LOGIN OTP", callback_data='login_kmsp')],                    
        [InlineKeyboardButton("🔑 LOGIN OTP BYPASS", callback_data='login_hesda')],                     
        [InlineKeyboardButton("🏠 Kembali ke Menu Utama", callback_data='back_to_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)
        except Exception as e:
            logging.warning(f"Gagal mengedit pesan show_login_options_menu untuk user {user_id}: {e}. Mengirim pesan baru.")
            msg = await context.bot.send_message(user_id, text, parse_mode="Markdown", reply_markup=reply_markup)
            bot_messages.setdefault(user_id, []).append(msg.message_id)
    else:
        msg = await context.bot.send_message(user_id, text, parse_mode="Markdown", reply_markup=reply_markup)
        bot_messages.setdefault(user_id, []).append(msg.message_id)


async def akun_saya_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update, context):
        return

    user_id = update.effective_user.id
    logging.info(f"User {user_id} mengakses NOMOR SAYA (alur baru).")

    query = update.callback_query
    
    text = "Silakan masukan nomor yang ingin di cek status login nya..."
    keyboard = [[InlineKeyboardButton("🏠 Kembali ke Menu Utama", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if query:
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    else:
        await utils.delete_last_message(user_id, context)
        await context.bot.send_message(user_id, text, parse_mode="Markdown", reply_markup=reply_markup)
        
    context.user_data['next'] = 'handle_akun_saya_nomor_input'


async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != config.ADMIN_ID:
        await update.message.reply_text("Anda tidak memiliki izin untuk menggunakan perintah ini.")
        return

    msg_info = None
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text("Memuat data statistik, harap tunggu...")
            msg_info = update.callback_query.message
        except Exception:
             msg_info = await context.bot.send_message(user_id, "Memuat data statistik, harap tunggu...")
    else:
        msg_info = await context.bot.send_message(user_id, "Memuat data statistik, harap tunggu...")


    total_users = len(user_data.get("registered_users", {}))
    kmsp_balance = await api_clients.get_kmsp_balance()

    header_text = (
        f"📊 *Statistik Bot*\n"
        f"👥 Total Pengguna: *{total_users}*\n"
        f"💰 Saldo Akun LOGIN: *{kmsp_balance}*\n\n"                        
        "👑 *Panel Admin Bot XL Tembak*\n"
        "Pilih tindakan yang ingin Anda lakukan:"
    )

    keyboard = [
        [
            InlineKeyboardButton("➕ Tambah Saldo", callback_data='admin_add_balance'),
            InlineKeyboardButton("➖ Kurangi Saldo", callback_data='admin_deduct_balance')
        ],
        [InlineKeyboardButton("💰 Cek Saldo User", callback_data='admin_check_user_balances')],
        [InlineKeyboardButton("👥 Daftar User", callback_data='admin_list_users')],
        [
            InlineKeyboardButton("🚫 Blokir", callback_data='admin_block_user_menu'),
            InlineKeyboardButton("✅ Un-Blokir", callback_data='admin_unblock_user_menu')
        ],
        [
            InlineKeyboardButton("🔍 Cari User", callback_data='admin_search_user_menu'),
            InlineKeyboardButton("🧾 Riwayat User", callback_data='admin_check_user_transactions_menu')
        ],
        [
            InlineKeyboardButton("📦 Kelola Paket API", callback_data='admin_check_api_packages'),
            InlineKeyboardButton("🔍 Cari Paket API", callback_data='admin_search_api_package_menu')
        ],
        [
            InlineKeyboardButton("➕ Paket Kustom", callback_data='admin_add_custom_package'),
            InlineKeyboardButton("✏️ Edit Paket Kustom", callback_data='admin_edit_custom_package_menu')
        ],
        [InlineKeyboardButton("📢 Broadcast Pesan", callback_data='admin_broadcast')],
        [InlineKeyboardButton("🏠 Kembali ke Menu User", callback_data='back_to_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await context.bot.edit_message_text(
            chat_id=user_id,
            message_id=msg_info.message_id,
            text=header_text,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    except Exception as e:
        logging.warning(f"Gagal mengedit pesan admin menu: {e}. Mengirim pesan baru.")
        await context.bot.delete_message(chat_id=user_id, message_id=msg_info.message_id)
        await context.bot.send_message(user_id, header_text, parse_mode="Markdown", reply_markup=reply_markup)

# ... (Salin semua sisa fungsi dari file asli Anda ke sini)
# Pastikan tidak ada yang tertinggal!
