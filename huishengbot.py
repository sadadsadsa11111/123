from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import os

TOKEN = os.getenv("TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("你好，我是回声机器人！你说啥我就回啥。")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_received = update.message.text
    await update.message.reply_text(text_received)

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), echo))

    app.run_polling()

if __name__ == '__main__':
    main()
