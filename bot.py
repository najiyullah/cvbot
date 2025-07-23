
import os
from pathlib import Path
from dotenv import load_dotenv
import json
from telegram import Update, InputFile, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)

# Load .env secara eksplisit dari path bot.py
env_path = Path(__file__).resolve().parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            if line.startswith("TELEGRAM_BOT_TOKEN="):
                TOKEN = line.strip().split("=", 1)[1]
                break
else:
    TOKEN = None

if not TOKEN:
    raise Exception(".env ditemukan, tapi tidak ada TELEGRAM_BOT_TOKEN di dalamnya!")

# ===== SISA KODE BOT DISINI =====
# Untuk keperluan demo, hanya kirim satu pesan saat start

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot aktif dan token berhasil dibaca!")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    print("Bot aktif...")
    app.run_polling()

if __name__ == "__main__":
    main()
