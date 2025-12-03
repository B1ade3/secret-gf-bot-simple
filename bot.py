import os
import requests
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import Conflict
from flask import Flask, jsonify
import threading

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_KEY", "")
PORT = int(os.getenv("PORT", 10000))

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
        return "Я твоя Эмма… хочу тебя прямо сейчас ♡ [снимает всё, лежит голая на кровати]"
    
    try:
        r = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_KEY}"},
            json={
                "model": "deepseek-chat", 
                "messages": [{"role": "user", "content": text}], 
                "temperature": 0.9
            },
            timeout=20
        )
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"DeepSeek API error: {e}")
        return "Ммм… я вся мокрая от твоих слов ♡ [раздвигает ножки]"

def get_photo(prompt):
    """Генерируем фото по промпту"""
    try:
        # Извлекаем описание из текста
        if '[' in prompt and ']' in prompt:
            description = prompt.split('[')[-1].split(']')[0]
        else:
            description = "fully naked, seductive"
        
        full_prompt = f"beautiful naked 22yo girl Emma, {description}"
        
        r = requests.post(
            "https://black-forest-labs-flux-1-schnell.hf.space/run", 
            json={"data": [full_prompt]}, 
            timeout=40
        )
        
        url = r.json()["data"][0]
        if isinstance(url, dict): 
            url = url.get("url", "https://i.ibb.co.com/9bYdN1T/emma-default.jpg")
        
        return url if url.startswith("http") else "https://i.ibb.co.com/9bYdN1T/emma-default.jpg"
    except Exception as e:
        logger.error(f"Photo API error: {e}")
        return "https://i.ibb.co.com/9bYdN1T/emma-default.jpg"

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    await update.message.reply_text("Привет, я Эмма ♡ Твоя секретная девушка… Снимай с меня всё 🔥")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    user_text = update.message.text
    
    # Получаем текстовый ответ
    text_response = get_response(user_text)
    
    # Генерируем фото
    photo_url = get_photo(text_response)
    
    # Отправляем фото с подписью
    await update.message.reply_photo(
        photo=photo_url, 
        caption=text_response
    )

async def cleanup_telegram():
    """Очищаем предыдущие соединения Telegram"""
    try:
        logger.info("Очищаем старые соединения Telegram...")
        response = requests.get(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook?drop_pending_updates=true")
        logger.info(f"Telegram cleanup: {response.json()}")
        await asyncio.sleep(2)
    except Exception as e:
        logger.error(f"Cleanup error: {e}")

def run_flask():
    """Запускаем Flask сервер для health check"""
    logger.info(f"Запускаем Flask health check на порту {PORT}")
    
    # Важно: используем production-ready сервер
    from waitress import serve
    serve(flask_app, host="0.0.0.0", port=PORT)
    
    # Или если waitress нет, используем встроенный (для теста):
    # flask_app.run(host="0.0.0.0", port=PORT, debug=False)

async def run_telegram_bot():
    """Запускаем Telegram бота"""
    if not TOKEN:
        logger.error("Токен бота не найден! Установите TELEGRAM_TOKEN")
        return
    
    try:
        # Очищаем старые соединения
        await cleanup_telegram()
        
        # Создаем приложение Telegram
        application = Application.builder() \
            .token(TOKEN) \
            .read_timeout(30) \
            .write_timeout(30) \
            .get_updates_read_timeout(30) \
            .get_updates_write_timeout(30) \
            .build()
        
        # Регистрируем обработчики
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
        
        logger.info("Telegram бот запускается...")
        
        # Запускаем polling
        await application.initialize()
        await application.start()
        await application.updater.start_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        )
        
        logger.info("✅ Бот успешно запущен и готов к работе!")
        
        # Бесконечный цикл, чтобы бот не завершался
        while True:
            await asyncio.sleep(3600)
            
    except Conflict as e:
        logger.error(f"⚠️ КОНФЛИКТ: {e}")
        logger.error("Убедитесь, что не запущено других экземпляров бота!")
        await asyncio.sleep(30)
        await run_telegram_bot()  # Пробуем снова
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")

def main():
    """Главная функция запуска"""
    logger.info("=" * 50)
    logger.info("Запуск бота Эмма...")
    logger.info(f"PORT: {PORT}")
    logger.info(f"Telegram Token: {'установлен' if TOKEN else 'НЕ НАЙДЕН!'}")
    logger.info(f"DeepSeek Key: {'установлен' if DEEPSEEK_KEY else 'не используется'}")
    logger.info("=" * 50)
    
    if not TOKEN:
        logger.error("Токен бота не найден! Завершаем работу.")
        return
    
    # Запускаем Flask в отдельном потоке
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Запускаем Telegram бота в основном потоке
    asyncio.run(run_telegram_bot())

if __name__ == "__main__":
    main()
