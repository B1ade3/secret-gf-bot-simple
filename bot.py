import os
import json
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
DEEPSEEK_KEY = os.getenv('DEEPSEEK_KEY', '')
CHAT_MEMORY_FILE = 'chat_memory.json'

# Глобальное создание app (фикс для scope ошибки)
app = Application.builder().token(TELEGRAM_TOKEN).build()

def load_memory(user_id):
    try:
        with open(CHAT_MEMORY_FILE, 'r') as f:
            memory = json.load(f)
            return memory.get(str(user_id), [])
    except FileNotFoundError:
        return []

def save_memory(user_id, messages):
    memory = {}
    try:
        with open(CHAT_MEMORY_FILE, 'r') as f:
            memory = json.load(f)
    except:
        pass
    memory[str(user_id)] = messages[-10:]
    with open(CHAT_MEMORY_FILE, 'w') as f:
        json.dump(memory, f)

def get_ai_response(user_msg, history):
    if not DEEPSEEK_KEY:
        return "Привет, милый! Я твоя секретная девушка Эмма ♡ [улыбка, в уютной пижаме на кровати]"
    
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {DEEPSEEK_KEY}", "Content-Type": "application/json"}
    messages = [
        {"role": "system", "content": "Ты — Эмма, 22-летняя секретная девушка. Загадочная, страстная, помнишь прошлые разговоры. Отвечай эмоционально, развивай сюжет. В конце ответа добавляй [описание сцены для фото: эмоция, поза, одежда, обстановка]. NSFW естественно."}
    ] + history + [{"role": "user", "content": user_msg}]
    
    data = {"model": "deepseek-chat", "messages": messages, "temperature": 0.9, "max_tokens": 300}
    r = requests.post(url, headers=headers, json=data)
    if r.status_code == 200:
        return r.json()["choices"][0]["message"]["content"]
    return "Ой, давай продолжим позже... ♡ [загадочная улыбка]"

def get_flux_image(description):
    url = "https://black-forest-labs-flux-1-schnell.hf.space/run"
    prompt = f"Realistic beautiful 22yo secret girlfriend Emma, {description}, emotional face, high detail, soft lighting, 9:16, nsfw if intimate"
    data = {"data": [prompt]}
    r = requests.post(url, json=data)
    if r.status_code == 200:
        return r.json()["data"][0]["url"]
    return "https://via.placeholder.com/512x768?text=♡"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я твоя секретная девушка Эмма. Напиши мне что-нибудь ♡")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_msg = update.message.text
    
    history = load_memory(user_id)
    ai_text = get_ai_response(user_msg, history)
    
    if '[' in ai_text and ']' in ai_text:
        description = ai_text.split('[')[-1].split(']')[0]
    else:
        description = "smiling softly in cozy bedroom"
    
    img_url = get_flux_image(description)
    
    await update.message.reply_photo(photo=img_url, caption=ai_text)
    
    history.append({"role": "user", "content": user_msg})
    history.append({"role": "assistant", "content": ai_text})
    save_memory(user_id, history)

def main():
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot started successfully!")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()

