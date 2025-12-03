import os
import requests
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import Conflict

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_KEY", "")

def get_response(text):
    if not DEEPSEEK_KEY:
        return "Я твоя Эмма… хочу тебя прямо сейчас ♡ [снимает всё, лежит голая на кровати]"
    
    try:
        r = requests.post("https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_KEY}"},
            json={"model": "deepseek-chat", "messages": [{"role": "user", "content": text}], "temperature": 0.9},
            timeout=20)
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"DeepSeek API error: {e}")
        return "Ммм… я вся мокрая от твоих слов ♡ [раздвигает ножки]"

def get_photo(prompt):
    try:
        r = requests.post("https://black-forest-labs-flux-1-schnell.hf.space/run", 
                         json={"data": [prompt]}, 
                         timeout=40)
        url = r.json()["data"][0]
        if isinstance(url, dict): 
            url = url.get("url", "https://i.ibb.co.com/9bYdN1T/emma-default.jpg")
        return url if url.startswith("http") else "https://i.ibb.co.com/9bYdN1T/emma-default.jpg"
    except Exception as e:
        logger.error(f"Photo API error: {e}")
        return "https://i.ibb.co.com/9bYdN1T/emma-default.jpg"

async def start(update: Update, context):
    await update.message.reply_text("Привет, я Эмма ♡ Твоя секретная девушка… Снимай с меня всё 🔥")

async def message(update: Update, context):
    text = get_response(update.message.text)
    photo = get_photo(f"beautiful naked 22yo girl Emma, {text.split('[')[-1].split(']')[0] if '[' in text else 'fully naked, seductive'}")
    await update.message.reply_photo(photo, caption=text)

async def cleanup_webhook():
    """Очищаем предыдущие webhook/polling соединения"""
    try:
        # Используем прямой запрос к Telegram API для очистки
        response = requests.get(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook?drop_pending_updates=true")
        logger.info(f"Webhook cleanup: {response.json()}")
        
        # Даем время на очистку
        await asyncio.sleep(2)
    except Exception as e:
        logger.error(f"Cleanup error: {e}")

def main():
    if not TOKEN:
        logger.error("Токен бота не найден! Установите переменную окружения TELEGRAM_TOKEN")
        return
    
    try:
        # Создаем приложение с настройками таймаутов
        app = Application.builder() \
            .token(TOKEN) \
            .read_timeout(30) \
            .write_timeout(30) \
            .get_updates_read_timeout(30) \
            .get_updates_write_timeout(30) \
            .get_updates_pool_timeout(30) \
            .build()
        
        # Очищаем предыдущие соединения перед запуском
        asyncio.run(cleanup_webhook())
        
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message))
        
        logger.info("Бот запускается...")
        
        # Запускаем polling с обработкой конфликтов
        app.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES,
            close_loop=False
        )
        
    except Conflict as e:
        logger.error(f"КОНФЛИКТ: Уже запущен другой экземпляр бота!")
        logger.error("Пожалуйста, остановите все другие процессы бота и подождите 30 секунд")
        # Ждем и пытаемся перезапуститься
        import time
        time.sleep(30)
        main()  # Рекурсивный перезапуск
        
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")

if __name__ == "__main__":
    main()
