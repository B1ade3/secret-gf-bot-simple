import os
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("TELEGRAM_TOKEN")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_KEY", "")

app = Application.builder().token(TOKEN).build()

def get_response(text):
    if not DEEPSEEK_KEY:
        return "Я твоя Эмма… хочу тебя прямо сейчас ♡ [снимает всё, лежит голая на кровати]"
    
    try:
        r = requests.post("https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_KEY}"},
            json={"model": "deepseek-chat", "messages": [{"role": "user", "content": text}], "temperature": 0.9},
            timeout=20)
        return r.json()["choices"][0]["message"]["content"]
    except:
        return "Ммм… я вся мокрая от твоих слов ♡ [раздвигает ножки]"

def get_photo(prompt):
    try:
        r = requests.post("https://black-forest-labs-flux-1-schnell.hf.space/run", json={"data": [prompt]}, timeout=40)
        url = r.json()["data"][0]
        if isinstance(url, dict): url = url.get("url", "https://i.ibb.co.com/9bYdN1T/emma-default.jpg")
        return url if url.startswith("http") else "https://i.ibb.co.com/9bYdN1T/emma-default.jpg"
    except:
        return "https://i.ibb.co.com/9bYdN1T/emma-default.jpg"

async def start(update: Update, context):
    await update.message.reply_text("Привет, я Эмма ♡ Твоя секретная девушка… Снимай с меня всё 🔥")

async def message(update: Update, context):
    text = get_response(update.message.text)
    photo = get_photo(f"beautiful naked 22yo girl Emma, {text.split('[')[-1].split(']')[0] if '[' in text else 'fully naked, seductive'}")
    await update.message.reply_photo(photo, caption=text)

def main():
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message))
    print("Bot started successfully!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
