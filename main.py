# main.py

import logging
import sys
import signal
from datetime import datetime

from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes, 
    CallbackQueryHandler, MessageHandler, filters
)

import config
import database
import handlers
import api_clients
import utils

def shutdown_handler(sig, frame):
    logging.info("🔌 Menerima sinyal shutdown...")
    database.simpan_data_ke_db(handlers.user_data)
    logging.info("✅ Data berhasil disimpan. Bot dimatikan.")
    sys.exit(0)

def main():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO,
        handlers=[logging.FileHandler(config.LOG_FILE), logging.StreamHandler()]
    )
    logging.info("🚀 Bot mulai dijalankan...")

    database.inisialisasi_database()
    
    # Memuat data dan membagikannya ke modul lain
    loaded_data = database.muat_data_dari_db()
    handlers.user_data = loaded_data
    api_clients.user_data = loaded_data
    
    # Inisialisasi variabel global di modul lain
    utils.bot_start_time = datetime.now()
    handlers.bot_messages = utils.bot_messages

    if not config.BOT_TOKEN:
        logging.critical("BOT_TOKEN tidak ditemukan!")
        sys.exit(1)
    
    app = ApplicationBuilder().token(config.BOT_TOKEN).build()

    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        logging.error(msg="Exception while handling an update:", exc_info=context.error)
    
    app.add_error_handler(error_handler)

    # Mendaftarkan handler dari modul `handlers`
    app.add_handler(CommandHandler("start", handlers.start))
    app.add_handler(CommandHandler("menu", handlers.start))
    app.add_handler(CommandHandler("admin", handlers.admin_menu))
    app.add_handler(CommandHandler("akun_saya", handlers.akun_saya_command_handler))
    
    app.add_handler(CallbackQueryHandler(handlers.button))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handlers.handle_text))

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    logging.info("✅ Bot berhasil dijalankan dan siap menerima perintah.")
    
    try:
        app.run_polling()
    except Exception as e:
        logging.critical(f"Terjadi kesalahan fatal saat polling: {e}", exc_info=True)
        shutdown_handler(None, None)
        sys.exit(1)

if __name__ == '__main__':
    main()
