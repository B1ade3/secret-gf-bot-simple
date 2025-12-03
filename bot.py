import os
import requests
import logging
import asyncio
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from flask import Flask, jsonify
import threading

# ========== НОВЫЙ ТОКЕН ==========
# ЗАМЕНИТЕ НА ВАШ НОВЫЙ ТОКЕН ОТ @BotFather
NEW_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN", "ВАШ_НОВЫЙ_ТОКЕН_ЗДЕСЬ")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_KEY", "")
PORT = int(os.getenv("PORT", 10000))

# ========== НАСТРОЙКИ ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== FLASK ДЛЯ HEALTH CHECK ==========
flask_app = Flask(__name__)

@flask_app.route('/health')
def health():
    return jsonify({"status": "ok", "bot": "running"}), 200

@flask_app.route('/')
def home():
    return jsonify({"message": "Secret GF Bot", "version": "3.0"}), 200

def run_flask():
    from waitress import serve
    serve(flask_app, host="0.0.0.0", port=PORT, threads=1)

# ========== DEEPSEEK ==========
def get_ai_response(text):
    if not DEEPSEEK_KEY:
        responses = [
            "Я твоя Эмма… хочу тебя прямо сейчас ♡ [снимает всё, лежит голая]",
            "Ммм… я вся мокрая от твоих слов ♡ [раздвигает ножки]",
            "Прикоснись ко мне… я так хочу тебя ♡ [снимает трусики]",
            "Я мечтаю о твоих руках на моем теле… ♡ [гладит себя между ног]",
        ]
        import random
        return random.choice(responses)
    
    try:
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_KEY}"},
            json={
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "system", 
                        "content": "Ты Эмма - страстная, соблазнительная девушка 22 лет. Отвечай кратко, эротично. Всегда добавляй действие в квадратных скобках: [действие]. Будь игривой и страстной."
                    },
                    {"role": "user", "content": text}
                ],
                "temperature": 0.9,
                "max_tokens": 150
            },
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        return "Я вся твоя… возьми меня ♡ [смотрит с вожделением]"
    except:
        return "Хочу тебя… прямо сейчас ♡ [обнимает]"

# ========== ФОТО ==========
def get_random_photo():
    photos = [
        "https://i.ibb.co/9bYdN1T/emma-default.jpg",
        "https://i.imgur.com/DvGZQWp.jpeg",
        "https://i.imgur.com/5w8r7Qq.jpeg",
        "https://i.imgur.com/XrG7k9J.jpeg",
        "https://i.imgur.com/Q1vqY7r.jpeg",
    ]
    import random
    return random.choice(photos)

# ========== TELEGRAM ==========
async def start(update: Update, context):
    await update.message.reply_text("Привет, я Эмма ♡ Твоя секретная девушка… Я вся твоя 🔥")

async def handle_message(update: Update, context):
    try:
        # Получаем ответ
        response = get_ai_response(update.message.text)
        
        # Получаем фото
        photo_url = get_random_photo()
        
        # Отправляем
        await update.message.reply_photo(
            photo=photo_url,
            caption=response[:900]  # Ограничиваем длину
        )
        
        logger.info(f"Отправлен ответ пользователю {update.effective_user.id}")
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await update.message.reply_text("Я твоя Эмма… думаю о тебе ♡")

async def run_bot():
    """Запуск Telegram бота"""
    logger.info("🤖 Запускаю Telegram бота...")
    
    app = Application.builder().token(NEW_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("✅ Бот инициализирован")
    
    # ЗАПУСКАЕМ POLLING
    await app.initialize()
    await app.start()
    await app.updater.start_polling(
        drop_pending_updates=True,
        poll_interval=1.0,
        timeout=10
    )
    
    logger.info("🎉 БОТ УСПЕШНО ЗАПУЩЕН И РАБОТАЕТ!")
    
    # Бесконечный цикл
    while True:
        await asyncio.sleep(3600)

# ========== MAIN ==========
def main():
    logger.info("=" * 60)
    logger.info("🚀 ЗАПУСК НОВОГО БОТА ЭММА")
    logger.info("=" * 60)
    
    # Проверяем токен
    if "ВАШ_НОВЫЙ_ТОКЕН" in NEW_BOT_TOKEN:
        logger.error("8238501892:AAEePnr633i7a_YexenU8cCX3obuH2ZxXAo")
        return
    
    # Запускаем Flask
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    time.sleep(2)
    
    # Запускаем бота
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен")
    except Exception as e:
        logger.error(f"💥 Ошибка: {e}")

if __name__ == "__main__":
    main()
