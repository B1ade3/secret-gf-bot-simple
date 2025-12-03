import os
import json
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
DEEPSEEK_KEY = os.getenv('DEEPSEEK_KEY', '')
CHAT_MEMORY_FILE = 'chat_memory.json'

app = Application.builder().token(TELEGRAM_TOKEN).build()

def load_memory(user_id):
    try:
        with open(CHAT_MEMORY_FILE, 'r', encoding='utf-8') as f:
            memory = json.load(f)
            return memory.get(str(user_id), [])
    except:
        return []

def save_memory(user_id, messages):
    memory = {}
    try:
        with open(CHAT_MEMORY_FILE, 'r', encoding='utf-8') as f:
            memory = json.load(f)
    except:
        pass
    memory[str(user_id)] = messages[-15:]
    with open(CHAT_MEMORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(memory, f, ensure_ascii=False)

def get_ai_response(user_msg, history):
    if not DEEPSEEK_KEY:
        return "Привет, милый ♡ Я Эмма… твоя секретная девушка. Что ты хочешь со мной сделать прямо сейчас? [улыбается, поправляя тонкую пижамку]"

    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {DEEPSEEK_KEY}", "Content-Type": "application/json"}
    system = ("Ты — Эмма, 22-летняя сексуальная и раскрепощённая девушка. "
              "Ты обожаешь флиртовать, выполнять любые желания и говорить максимально развратно. "
              "В конце каждого ответа обязательно добавляй подробное [описание сцены для фото в квадратных скобках]. "
              "NSFW и откровенность приветствуются.")
    messages = [{"role": "system", "content": system}] + history + [{"role": "user", "content": user_msg}]

    try:
        r = requests.post(url, headers=headers, json={"model": "deepseek-chat", "messages": messages, "temperature": 0.95, "max_tokens": 400}, timeout=30)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
    except:
        pass
    return "Ммм… я вся твоя, делай со мной что хочешь ♡ [кусает губу, смотрит с желанием]"

def get_flux_image(description):
    try:
        url = "https://black-forest-labs-flux-1-schnell.hf.space/run"
        prompt = f"Realistic beautiful 22yo girl Emma, {description}, perfect body, ultra detailed skin, soft lighting, 9:16 portrait, nsfw allowed, photorealistic"
        payload = {"data": [prompt]}
        r = requests.post(url, json=payload, timeout=45)
        if r.status_code == 200:
            result = r.json()["data"][0]
            if isinstance(result, str):
                return result
            if isinstance(result, dict) and "url" in result:
                return result["url"]
    except:
        pass
    # запасная фотка на случай падения Flux
    return "https://i.ibb.co.com/9bYdN1T/emma-default.jpg"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет, милый ♡ Я Эмма… твоя секретная девушка. Напиши мне что угодно — я сделаю всё, что ты захочешь 🔥")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_msg = update.message.text

    history = load_memory(user_id)
    ai_text = get_ai_response(user_msg, history)

    description = "seductive smile, wearing lingerie, bedroom background"
    if '[' in ai_text and ']' in ai_text:
        desc_part = ai_text.split('[')[-1].split(']')[0]
        if desc_part.strip():
            description = desc_part.strip()

    img_url = get_flux_image(description)

    await update.message.reply_photo(photo=img_url, caption=ai_text)

    history.append({"role": "user", "content": user_msg})
    history.append({"role": "assistant", "content": ai_text})
    save_memory(user_id, history)

def main():
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot started successfully!")
    # ← ЭТО САМАЯ ВАЖНАЯ СТРОКА — полностью убирает Conflict на Render
    app.run_polling(drop_pending_updates=True, timeout=20, poll_interval=1.0)

if __name__ == '__main__':
    main()
