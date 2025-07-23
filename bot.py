import os
from dotenv import load_dotenv
from pathlib import Path

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

import json
from telegram import Update, InputFile, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)

ASK_FILE, ASK_FN, ASK_FILENAME, ASK_SPLIT = range(4)
MANUAL_NUMBERS, MANUAL_FN, MANUAL_FILENAME = range(4, 7)
RENAME_FILE_WAIT_FILE, RENAME_FILE_WAIT_NAME = range(7, 9)
RENAME_CONTACT_WAIT_FILE, RENAME_CONTACT_WAIT_FN = range(9, 11)
SESSION = {}

# === daftar admin ===
ADMINS = {379525054}  # Ganti dengan user_id admin bot

# === daftar user premium ===
import datetime
PREMIUM_FILE = "premium_users.json"

def load_premium_users():
    if os.path.exists(PREMIUM_FILE):
        with open(PREMIUM_FILE, "r") as f:
            return json.load(f)
    return {}

def save_premium_users():
    with open(PREMIUM_FILE, "w") as f:
        json.dump(PREMIUM_USERS, f)

PREMIUM_USERS = load_premium_users()

def is_premium(user_id: int) -> bool:
    return user_id in PREMIUM_USERS

def is_admin(user_id: int) -> bool:
    return user_id in ADMINS

def split_and_generate_vcf(numbers, fn_base, file_base, split_size, temp_dir):
    chunks = [numbers[i:i + split_size] for i in range(0, len(numbers), split_size)]
    file_paths = []
    counter = 1
    for i, group in enumerate(chunks, 1):
        path = os.path.join(temp_dir, f"{file_base}_{i}.vcf")
        with open(path, 'w', encoding='utf-8') as f:
            for number in group:
                f.write("BEGIN:VCARD\r\n")
                f.write("VERSION:3.0\r\n")
                f.write(f"FN:{fn_base} {counter}\r\n")
                f.write(f"N:{fn_base} {counter};;;\r\n")
                f.write(f"TEL:{number}\r\n")
                f.write("END:VCARD\r\n\r\n")
                counter += 1
        file_paths.append(path)
    return file_paths

def generate_single_vcf(numbers, fn_base, filename, output_path):
    with open(output_path, 'w', encoding='utf-8') as f:
        for i, number in enumerate(numbers, 1):
            f.write("BEGIN:VCARD\r\n")
            f.write("VERSION:3.0\r\n")
            f.write(f"FN:{fn_base} {i}\r\n")
            f.write(f"N:{fn_base} {i};;;\r\n")
            f.write(f"TEL:{number}\r\n")
            f.write("END:VCARD\r\n\r\n")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
    "<b>👋 WELCOME TO JAMAL CV BOT</b>\n"
    "🔐 <i>BOT INI HANYA BISA DIGUNAKAN OLEH PENGGUNA PREMIUM.</i>\n\n"
    "🧾 <b>/to_vcf</b> — Ubah file .txt jadi .vcf dan bagi ke beberapa bagian.\n"
    "✍️ <b>/manual</b> — Buat file .vcf dari daftar nomor secara manual.\n"
    "📝 <b>/rename_file</b> — Ganti nama file .vcf.\n"
    "🔄 <b>/rename_contact</b> — Ganti nama semua kontak dalam file .vcf.\n"
    "💳 <b>/qris</b> — Lihat metode pembayaran untuk akses premium."
, parse_mode="HTML")

# === /to_vcf flow ===
async def to_vcf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not is_premium(user_id):
        await update.message.reply_text("❌ Bot ini hanya untuk pengguna berbayar. Hubungi admin untuk akses.")
        return ConversationHandler.END
    await update.message.reply_text("Silakan kirim file .txt yang berisi daftar nomor.")
    return ASK_FILE

async def receive_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc or not doc.file_name.endswith(".txt"):
        await update.message.reply_text("Kirim file .txt saja.")
        return ASK_FILE
    file = await doc.get_file()
    input_path = f"/tmp/{doc.file_id}.txt"
    await file.download_to_drive(input_path)
    await update.message.reply_text(f"✅ File '{doc.file_name}' berhasil diunggah.")
    with open(input_path, 'r', encoding='utf-8') as f:
        numbers = [line.strip() for line in f if line.strip()]
    if not numbers:
        await update.message.reply_text("❌ File .txt kosong atau tidak valid.")
        return ConversationHandler.END
    user_id = update.message.from_user.id
    SESSION[user_id] = {"numbers": numbers, "txt_path": input_path}
    await update.message.reply_text(f"File diterima ✅ ({len(numbers)} kontak).\nMasukkan FN (misal: TES):")
    return ASK_FN

async def receive_fn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    SESSION[user_id]["fn"] = update.message.text.strip()
    await update.message.reply_text("Masukkan nama file hasil (tanpa .vcf):")
    return ASK_FILENAME

async def receive_filename(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    SESSION[user_id]["file_name"] = update.message.text.strip()
    await update.message.reply_text("Berapa jumlah kontak per file? Contoh: 50")
    return ASK_SPLIT

async def receive_split(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    split_str = update.message.text.strip()
    if not split_str.isdigit():
        await update.message.reply_text("Masukkan angka yang valid, contoh: 50")
        return ASK_SPLIT
    split_size = int(split_str)
    data = SESSION[user_id]
    temp_dir = "/tmp/split_output"
    os.makedirs(temp_dir, exist_ok=True)
    file_paths = split_and_generate_vcf(data["numbers"], data["fn"], data["file_name"], split_size, temp_dir)
    for path in file_paths:
        with open(path, "rb") as f:
            await update.message.reply_document(InputFile(f, filename=os.path.basename(path)))
    await update.message.reply_text("✅ Semua file berhasil dikirim.", reply_markup=ReplyKeyboardRemove())
    os.remove(data["txt_path"])
    for path in file_paths:
        os.remove(path)
    SESSION.pop(user_id, None)
    return ConversationHandler.END

# === /manual flow ===
async def manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not is_premium(user_id):
        await update.message.reply_text("❌ Bot ini hanya untuk pengguna berbayar. Hubungi admin untuk akses.")
        return ConversationHandler.END
    await update.message.reply_text("Kirim daftar nomor (satu per baris).")
    return MANUAL_NUMBERS

async def manual_receive_numbers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    numbers = [line.strip() for line in update.message.text.splitlines() if line.strip()]
    if not numbers:
        await update.message.reply_text("Daftar nomor tidak valid. Kirim ulang.")
        return MANUAL_NUMBERS
    SESSION[user_id] = {"manual_numbers": numbers}
    await update.message.reply_text("Masukkan nama kontak (FN):")
    return MANUAL_FN

async def manual_receive_fn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    SESSION[user_id]["manual_fn"] = update.message.text.strip()
    await update.message.reply_text("Masukkan nama file hasil (tanpa .vcf):")
    return MANUAL_FILENAME

async def manual_receive_filename(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    data = SESSION[user_id]
    filename = update.message.text.strip()
    temp_path = f"/tmp/{filename}.vcf"
    generate_single_vcf(data["manual_numbers"], data["manual_fn"], filename, temp_path)
    with open(temp_path, "rb") as doc:
        await update.message.reply_document(document=doc, filename=f"{filename}.vcf")
    os.remove(temp_path)
    SESSION.pop(user_id, None)
    return ConversationHandler.END

# === fitur rename file .vcf ===
async def rename_file_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not is_premium(user_id):
        await update.message.reply_text("❌ Bot ini hanya untuk pengguna berbayar. Hubungi admin untuk akses.")
        return ConversationHandler.END
    await update.message.reply_text("Kirim file .vcf yang ingin diubah namanya.")
    return RENAME_FILE_WAIT_FILE

async def rename_file_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc or not doc.file_name.endswith(".vcf"):
        await update.message.reply_text("Kirim file dengan ekstensi .vcf.")
        return RENAME_FILE_WAIT_FILE
    file = await doc.get_file()
    input_path = f"/tmp/{doc.file_id}.vcf"
    await file.download_to_drive(input_path)
    await update.message.reply_text(f"✅ File '{doc.file_name}' berhasil diunggah.")
    user_id = update.message.from_user.id
    SESSION[user_id] = {"vcf_path": input_path, "original_filename": doc.file_name}
    await update.message.reply_text("Masukkan nama file baru (tanpa .vcf):")
    return RENAME_FILE_WAIT_NAME

async def rename_file_receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    new_name = update.message.text.strip()
    data = SESSION.get(user_id)
    if not data:
        await update.message.reply_text("Terjadi kesalahan. Mulai ulang.")
        return ConversationHandler.END
    new_path = f"/tmp/{new_name}.vcf"
    os.rename(data["vcf_path"], new_path)
    with open(new_path, "rb") as f:
        await update.message.reply_document(InputFile(f, filename=f"{new_name}.vcf"))
    os.remove(new_path)
    SESSION.pop(user_id, None)
    return ConversationHandler.END

# === fitur rename contact di .vcf ===
async def rename_contact_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not is_premium(user_id):
        await update.message.reply_text("❌ Bot ini hanya untuk pengguna berbayar. Hubungi admin untuk akses.")
        return ConversationHandler.END
    await update.message.reply_text("Kirim file .vcf yang ingin diubah nama kontaknya.")
    return RENAME_CONTACT_WAIT_FILE

async def rename_contact_receive_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc or not doc.file_name.endswith(".vcf"):
        await update.message.reply_text("Kirim file dengan ekstensi .vcf.")
        return RENAME_CONTACT_WAIT_FILE
    file = await doc.get_file()
    input_path = f"/tmp/{doc.file_id}.vcf"
    await file.download_to_drive(input_path)
    await update.message.reply_text(f"✅ File '{doc.file_name}' berhasil diunggah.")
    user_id = update.message.from_user.id
    SESSION[user_id] = {"vcf_path": input_path, "original_filename": doc.file_name}
    await update.message.reply_text("Masukkan nama baru untuk semua kontak (FN):")
    return RENAME_CONTACT_WAIT_FN

async def rename_contact_receive_fn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    new_fn = update.message.text.strip()
    data = SESSION.get(user_id)
    if not data:
        await update.message.reply_text("Terjadi kesalahan. Mulai ulang.")
        return ConversationHandler.END

    old_path = data["vcf_path"]
    count = 1
    output_lines = []
    with open(old_path, "r", encoding="utf-8") as f_in:
        for line in f_in:
            if line.startswith("FN:"):
                output_lines.append(f"FN:{new_fn} {count}\r\n")
            elif line.startswith("N:"):
                output_lines.append(f"N:{new_fn} {count};;;\r\n")
                count += 1
            else:
                output_lines.append(line)

    if count == 1:
        await update.message.reply_text("❌ Tidak ditemukan baris FN: atau N: di dalam file. Gagal mengganti kontak.")
        os.remove(old_path)
        SESSION.pop(user_id, None)
        return ConversationHandler.END

    with open(old_path, "w", encoding="utf-8") as f_out:
        f_out.writelines(output_lines)

    with open(old_path, "rb") as f:
        await update.message.reply_document(InputFile(f, filename=data.get("original_filename", os.path.basename(old_path))))

    os.remove(old_path)
    SESSION.pop(user_id, None)
    return ConversationHandler.END

    old_path = data["vcf_path"]
    new_path = old_path  # Overwrite isi file dengan nama yang sama
    with open(old_path, "r", encoding="utf-8") as f_in, open(new_path, "w", encoding="utf-8") as f_out:
        count = 1
        for line in f_in:
            if line.startswith("FN:"):
                f_out.write(f"FN:{new_fn} {count}\r\n")
            elif line.startswith("N:"):
                f_out.write(f"N:{new_fn} {count};;;\r\n")
                count += 1
            else:
                f_out.write(line)

    with open(old_path, "rb") as f:
        await update.message.reply_document(InputFile(f, filename=os.path.basename(old_path)))

    os.remove(old_path)
    SESSION.pop(user_id, None)
    return ConversationHandler.END

# === cancel ===
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Proses dibatalkan.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def qris(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = """<b>💳 Pembayaran Akses Premium</b>

Silakan scan QRIS di atas untuk melakukan pembayaran.

<b>💰 Pricelist:</b>
• 1 Bulan — Rp25.000
• 2 Bulan — Rp50.000
• 5 Bulan — Rp100.000
• Permanent — Rp300.000

📩 Setelah membayar, kirim bukti pembayaran & ID Telegram Anda ke admin:
👉 @jamalcok
"""
    await update.message.reply_photo(
        photo="https://i.imgur.com/GwckH7d.jpg",
        caption=caption,
        parse_mode="HTML"
    )

# === daftar handler tambahan ===
def register_rename_handlers(app):
    conv_rename_file = ConversationHandler(
        entry_points=[CommandHandler("rename_file", rename_file_command)],
        states={
            RENAME_FILE_WAIT_FILE: [MessageHandler(filters.Document.ALL, rename_file_receive)],
            RENAME_FILE_WAIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, rename_file_receive_name)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    conv_rename_contact = ConversationHandler(
        entry_points=[CommandHandler("rename_contact", rename_contact_command)],
        states={
            RENAME_CONTACT_WAIT_FILE: [MessageHandler(filters.Document.ALL, rename_contact_receive_file)],
            RENAME_CONTACT_WAIT_FN: [MessageHandler(filters.TEXT & ~filters.COMMAND, rename_contact_receive_fn)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_rename_file)
    app.add_handler(conv_rename_contact)

async def grant_access(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ Anda tidak memiliki izin untuk perintah ini.")
        return
    if not context.args:
        await update.message.reply_text("Gunakan: /grant <user_id>")
        return
    try:
        target_id = int(context.args[0])
        PREMIUM_USERS[target_id] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        save_premium_users()
        await update.message.reply_text(f"✅ Akses diberikan ke user ID {target_id}.")
    except:
        await update.message.reply_text("❌ Format user_id tidak valid.")

async def revoke_access(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ Anda tidak memiliki izin untuk perintah ini.")
        return
    if not context.args:
        await update.message.reply_text("Gunakan: /revoke <user_id>")
        return
    try:
        target_id = int(context.args[0])
        if target_id in PREMIUM_USERS:
            PREMIUM_USERS.pop(target_id)
            save_premium_users()
            await update.message.reply_text(f"✅ Akses user ID {target_id} dicabut.")
        else:
            await update.message.reply_text("❌ User ID tersebut tidak ada dalam daftar premium.")
    except:
        await update.message.reply_text("❌ Format user_id tidak valid.")

async def premium_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ Anda tidak memiliki izin untuk perintah ini.")
        return
    if not PREMIUM_USERS:
        await update.message.reply_text("Tidak ada pengguna premium.")
        return
    lines = [f"👑 List Premium Users ({len(PREMIUM_USERS)}):"]
    for uid, tgl in PREMIUM_USERS.items():
        lines.append(f"- {uid} (sejak {tgl})")
    await update.message.reply_text("\n".join(lines))

# === error handler ===
async def handle_error(update: object, context: ContextTypes.DEFAULT_TYPE):
    error = context.error
    print(f"⚠️ Terjadi error: {error}")
    if isinstance(update, Update) and update.effective_chat:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Maaf, terjadi kesalahan internal. Silakan coba lagi."
            )
        except:
            pass

# === main ===
def main():
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        raise Exception("Env var TELEGRAM_BOT_TOKEN tidak ditemukan!")
    app = ApplicationBuilder().token(TOKEN).build()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_error_handler(handle_error)

    conv_tovcf = ConversationHandler(
        entry_points=[CommandHandler("to_vcf", to_vcf)],
        states={
            ASK_FILE: [MessageHandler(filters.Document.ALL, receive_file)],
            ASK_FN: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_fn)],
            ASK_FILENAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_filename)],
            ASK_SPLIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_split)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    conv_manual = ConversationHandler(
        entry_points=[CommandHandler("manual", manual)],
        states={
            MANUAL_NUMBERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, manual_receive_numbers)],
            MANUAL_FN: [MessageHandler(filters.TEXT & ~filters.COMMAND, manual_receive_fn)],
            MANUAL_FILENAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, manual_receive_filename)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("qris", qris))
    app.add_handler(CommandHandler("grant", grant_access))
    app.add_handler(CommandHandler("revoke", revoke_access))
    app.add_handler(CommandHandler("premium_list", premium_list))
    app.add_handler(conv_tovcf)
    app.add_handler(conv_manual)
    register_rename_handlers(app)

    print("Bot aktif...")
    app.run_polling()

if __name__ == "__main__":
    main()
