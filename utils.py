# utils.py
import logging
import re
import html
import base64
from datetime import datetime

# Impor dari modul lokal
import config

bot_start_time = datetime.now()
bot_messages = {} # Dikelola di sini atau di main.py

def extract_package_display_name(package_full_name: str) -> str:
    """Membersihkan nama paket dari API untuk ditampilkan ke user."""
    # Salin fungsi extract_package_display_name dari file asli Anda ke sini
    match1 = re.search(r'\]\s*(.*?)(?:\s*\(|$)', package_full_name)
    if match1:
        extracted = match1.group(1).strip()
        if extracted:
            return extracted
    
    cleaned_name = re.sub(r'\[.*?\]|\(.*?\)', '', package_full_name).strip()
    return cleaned_name if cleaned_name else package_full_name

async def delete_last_message(user_id, context):
    """Menghapus pesan terakhir yang dikirim oleh bot ke user."""
    messages = bot_messages.get(user_id, [])
    if messages:
        for msg_id in messages:
            try:
                await context.bot.delete_message(chat_id=user_id, message_id=msg_id)
            except Exception as e:
                if "message to delete not found" not in str(e):
                    logging.warning(f"Gagal hapus pesan {msg_id} untuk user {user_id}: {e}")
        bot_messages[user_id] = []

async def qris_expiration_job(context):
    """Pekerjaan yang dijalankan saat QRIS kedaluwarsa."""
    # Salin fungsi qris_expiration_job dari file asli Anda ke sini
    job = context.job
    user_id = job.data['user_id']
    qris_message_id = job.data['qris_message_id']
    qris_photo_id = job.data.get('qris_photo_id') # Use .get for safety

    try:
        if qris_photo_id:
            await context.bot.delete_message(chat_id=user_id, message_id=qris_photo_id)
    except Exception as e:
        logging.warning(f"Gagal menghapus foto QRIS {qris_photo_id} untuk user {user_id}: {e}")

    try:
        await context.bot.edit_message_text(
            chat_id=user_id,
            message_id=qris_message_id,
            text="⚠️ QRIS telah kedaluwarsa. Silakan buat permintaan baru jika ingin melanjutkan.",
            reply_markup=None
        )
    except Exception as e:
        logging.warning(f"Gagal mengedit pesan teks QRIS {qris_message_id} untuk user {user_id}: {e}")


def get_hesda_auth_headers():
    """Membuat header otentikasi untuk API Hesda."""
    if not config.HESDA_USERNAME or not config.HESDA_PASSWORD:
        logging.error("HESDA_USERNAME atau HESDA_PASSWORD tidak diatur.")
        return None
    auth_string = f"{config.HESDA_USERNAME}:{config.HESDA_PASSWORD}"
    encoded_auth = base64.b64encode(auth_string.encode()).decode()
    return {"Authorization": f"Basic {encoded_auth}"}

def calculate_total_successful_transactions(user_data):
    """Menghitung total transaksi yang berhasil dari semua pengguna."""
    count = 0
    all_users = user_data.get("registered_users", {})
    for user_id, details in all_users.items():
        transactions = details.get("transactions", [])
        for tx in transactions:
            if tx.get("status") == "Berhasil":
                count += 1
    return count
