import os
import requests
import logging
import asyncio
import sys
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import Conflict
from flask import Flask, jsonify
import threading
import time
import random

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_KEY", "")
PORT = int(os.getenv("PORT", 10000))

# Принудительная очистка перед запуском
def force_cleanup():
    """Принудительно очищаем все предыдущие соединения"""
    logger.info("⚡ ПРИНУДИТЕЛЬНАЯ ОЧИСТКА ПЕРЕД ЗАПУСКОМ")
    
    try:
        # 1. Удаляем webhook
        resp1 = requests.get(
            f"https://api.telegram.org/bot{TOKEN}/deleteWebhook?drop_pending_updates=true",
            timeout=10
        )
        logger.info(f"Delete webhook: {resp1.json()}")
        
        # 2. Сбрасываем offset
        resp2 = requests.get(
            f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset=-1",
            timeout=10
        )
        logger.info(f"Reset offset: {resp2.json()}")
        
        # 3. Ждем
        time.sleep(3)
        
    except Exception as e:
        logger.error(f"Cleanup error: {e}")

# Flask app для health check
flask_app = Flask(__name__)

@flask_app.route('/health')
def health_check():
    return jsonify({"status": "ok", "service": "telegram-bot"}), 200

@flask_app.route('/')
def home():
    return jsonify({"status": "running", "bot": "Emma bot is active"}), 200

def get_response(text):
    """Получаем ответ от DeepSeek или возвращаем стандартный"""
    if not DEEPSEEK_KEY:
        responses = [
            "Я твоя Эмма… хочу тебя прямо сейчас ♡ [снимает всё, лежит голая на кровати]",
            "Ммм… я вся мокрая от твоих слов ♡ [раздвигает ножки]",
            "Прикоснись ко мне… я так хочу тебя ♡ [снимает трусики]",
        ]
        return random.choice(responses)
    
    try:
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_KEY}"},
            json={
                "model": "deepseek-chat", 
                "messages": [{"role": "user", "content": text}], 
                "temperature": 0.9,
                "max_tokens": 150
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            return data["choices"][0]["message"]["content"]
        else:
            return "Ммм… я вся мокрая от твоих слов ♡ [прижимается к тебе]"
            
    except:
        return "Ммм… я вся мокрая от твоих слов ♡ [обнимает тебя]"

def get_photo():
    """Возвращаем случайное фото"""
    photos = [
        "https://i.ibb.co.com/9bYdN1T/emma-default.jpg",
        "https://i.ibb.co.com/0jKJQ0w/emma1.jpg",
        "https://i.ibb.co.com/7VS4Jwq/emma2.jpg",
        "https://i.ibb.co.com/0cLQ5yK/emma3.jpg",
        "https://i.imgur.com/7Q1qjYp.jpg",
        "https://i.imgur.com/9zq8Z2F.jpg",
    ]
    return random.choice(photos)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет, я Эмма ♡ Твоя секретная девушка… Снимай с меня всё 🔥")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text_response = get_response(update.message.text)
        photo_url = get_photo()
        
        await update.message.reply_photo(
            photo=photo_url, 
            caption=text_response[:900]
        )
    except Exception as e:
        logger.error(f"Message error: {e}")
        await update.message.reply_text("Ой... Но я все еще твоя Эмма ♡")

def run_flask():
    """Запускаем Flask"""
    from waitress import serve
    serve(flask_app, host="0.0.0.0", port=PORT, threads=1, channels=1)

async def run_bot():
    """Запускаем Telegram бота с защитой от конфликтов"""
    logger.info("🚀 ЗАПУСКАЕМ БОТА С ЗАЩИТОЙ ОТ КОНФЛИКТОВ")
    
    # ПРИНУДИТЕЛЬНАЯ ОЧИСТКА
    force_cleanup()
    
    try:
        # Создаем приложение
        app = Application.builder() \
            .token(TOKEN) \
            .read_timeout(20) \
            .write_timeout(20) \
            .build()
        
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
        
        logger.info("✅ Бот инициализирован, запускаем polling...")
        
        # Запускаем polling с обработкой конфликтов
        await app.initialize()
        await app.start()
        
        # Важно: используем низкий timeout для быстрого обнаружения конфликтов
        await app.updater.start_polling(
            drop_pending_updates=True,
            poll_interval=0.5,  # Быстрый poll
            timeout=5
        )
        
        logger.info("🎉 БОТ УСПЕШНО ЗАПУЩЕН И РАБОТАЕТ!")
        
        # Keep-alive логика
        last_success = time.time()
        
        while True:
            await asyncio.sleep(1)
            
            # Если долго нет успешных обновлений - перезапуск
            if time.time() - last_success > 30:
                logger.warning("⚠️ Долго нет обновлений, проверяем соединение...")
                try:
                    test = await app.bot.get_me()
                    logger.info(f"Соединение OK: {test.username}")
                    last_success = time.time()
                except Exception as e:
                    logger.error(f"Проблема с соединением: {e}")
                    break
        
    except Conflict as e:
        logger.error(f"🚨 КОНФЛИКТ ОБНАРУЖЕН! {e}")
        logger.error("Завершаем процесс...")
        await asyncio.sleep(5)
        sys.exit(1)  # Выходим полностью
        
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        await asyncio.sleep(5)
        # Не пытаемся перезапускаться - лучше упасть и показать ошибку

def main():
    """Главная функция"""
    logger.info("=" * 60)
    logger.info("🤖 ЗАПУСК EMMA BOT v2.0")
    logger.info("=" * 60)
    
    if not TOKEN:
        logger.error("❌ НЕТ ТОКЕНА TELEGRAM!")
        return
    
    # Запускаем Flask в потоке
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    time.sleep(2)
    
    # Запускаем бота
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен")
    except Exception as e:
        logger.error(f"💀 КРИТИЧЕСКАЯ ОШИБКА: {e}")

if __name__ == "__main__":
    main()
