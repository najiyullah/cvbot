
import os
import re
from telegram import Update, InputFile, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)

ASK_FILE, ASK_FN, ASK_FILENAME, ASK_SPLIT = range(4)
SESSION = {}

# ========== /to_vcf ==========
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
                f.write(f"TEL:{number}\r\n")
                f.write("END:VCARD\r\n\r\n")
                counter += 1
        file_paths.append(path)
    return file_paths

# ========== /to_txt ==========
def convert_vcf_to_txt(vcf_path, txt_path):
    invisible = ['‪', '‬', '‎', '‏', '⁦']
    def clean_number(line):
        line = line.strip().replace("TEL:", "").strip()
        for char in invisible:
            line = line.replace(char, '')
        return ''.join(c for c in line if c.isdigit() or c == '+')
    with open(vcf_path, 'r', encoding='utf-8') as vcf_file, open(txt_path, 'w', encoding='utf-8') as txt_file:
        for line in vcf_file:
            if line.strip().startswith("TEL:"):
                cleaned = clean_number(line)
                if cleaned:
                    txt_file.write(cleaned + "\n")

# ========== /clean_txt ==========
def clean_txt_file(input_path, output_path):
    invisible_chars = ['‪', '‬', '‎', '‏', '⁦']
    with open(input_path, 'r', encoding='utf-8') as infile, open(output_path, 'w', encoding='utf-8') as outfile:
        for line in infile:
            for char in invisible_chars:
                line = line.replace(char, '')
            line = line.strip()
            if line:
                outfile.write(line + '\n')

# ========== Handlers ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Gunakan /to_vcf, /to_txt, atau /clean_txt")

async def to_vcf(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

async def to_txt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Silakan kirim file .vcf yang ingin dikonversi ke .txt.")

async def handle_vcf_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc or not doc.file_name.lower().endswith(".vcf"):
        return
    file = await doc.get_file()
    input_path = f"/tmp/{doc.file_id}.vcf"
    output_path = input_path + ".txt"
    await file.download_to_drive(input_path)
    convert_vcf_to_txt(input_path, output_path)
    await update.message.reply_document(InputFile(output_path, filename="converted.txt"))
    os.remove(input_path)
    os.remove(output_path)

async def clean_txt_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Silakan kirim file .txt yang ingin dibersihkan dari karakter tersembunyi.")

async def handle_txt_cleaning(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc or not doc.file_name.endswith(".txt"):
        await update.message.reply_text("Kirim file .txt saja.")
        return
    file = await doc.get_file()
    input_path = f"/tmp/{doc.file_id}.txt"
    output_path = f"/tmp/{doc.file_id}_cleaned.txt"
    await file.download_to_drive(input_path)
    clean_txt_file(input_path, output_path)
    await update.message.reply_document(InputFile(output_path, filename="cleaned.txt"))
    os.remove(input_path)
    os.remove(output_path)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Proses dibatalkan.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def main():
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        raise Exception("Env var TELEGRAM_BOT_TOKEN tidak ditemukan!")
    app = ApplicationBuilder().token(TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("to_vcf", to_vcf)],
        states={
            ASK_FILE: [MessageHandler(filters.Document.ALL, receive_file)],
            ASK_FN: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_fn)],
            ASK_FILENAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_filename)],
            ASK_SPLIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_split)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)
    app.add_handler(CommandHandler("to_txt", to_txt))
    app.add_handler(MessageHandler(filters.Document.ALL & filters.Document.FILE_NAME(lambda name: name.endswith('.vcf')), handle_vcf_file))
    app.add_handler(CommandHandler("clean_txt", clean_txt_command))
    app.add_handler(MessageHandler(filters.Document.ALL & filters.Document.FILE_NAME(lambda name: name.endswith('.txt')), handle_txt_cleaning))
    print("Bot aktif...")
    app.run_polling()

if __name__ == "__main__":
    main()
