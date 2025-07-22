
import os
from telegram import Update, InputFile
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)

def convert_txt_to_vcf(txt_path, vcf_path):
    with open(txt_path, 'r') as txt_file, open(vcf_path, 'w') as vcf_file:
        for i, line in enumerate(txt_file):
            number = line.strip()
            if not number:
                continue
            vcf_file.write("BEGIN:VCARD\n")
            vcf_file.write("VERSION:3.0\n")
            vcf_file.write(f"FN:Contact {i+1}\n")
            vcf_file.write(f"TEL:{number}\n")
            vcf_file.write("END:VCARD\n\n")

def convert_vcf_to_txt(vcf_path, txt_path):
    with open(vcf_path, 'r') as vcf_file, open(txt_path, 'w') as txt_file:
        for line in vcf_file:
            if line.startswith("TEL"):
                txt_file.write(line.replace("TEL:", "").strip() + "\n")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Halo! Bot siap. Gunakan /to_vcf atau /to_txt.")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc:
        await update.message.reply_text("Kirim file .txt atau .vcf setelah perintah ini.")
        return

    file = await doc.get_file()
    filename = doc.file_name.lower()
    input_path = f"/tmp/{doc.file_id}_{filename}"
    output_path = input_path + (".vcf" if filename.endswith(".txt") else ".txt")

    await file.download_to_drive(input_path)

    if filename.endswith(".txt"):
        convert_txt_to_vcf(input_path, output_path)
        await update.message.reply_document(document=InputFile(output_path), filename="converted.vcf")
    elif filename.endswith(".vcf"):
        convert_vcf_to_txt(input_path, output_path)
        await update.message.reply_document(document=InputFile(output_path), filename="converted.txt")
    else:
        await update.message.reply_text("Format file tidak didukung. Kirim .txt atau .vcf saja.")
        return

    os.remove(input_path)
    os.remove(output_path)

def main():
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        raise Exception("Env var TELEGRAM_BOT_TOKEN tidak ditemukan!")

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("to_vcf", handle_document))
    app.add_handler(CommandHandler("to_txt", handle_document))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    print("Bot berjalan...")
    app.run_polling()

if __name__ == "__main__":
    main()
