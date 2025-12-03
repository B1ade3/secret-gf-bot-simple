import os
import requests
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import Conflict, BadRequest
from flask import Flask, jsonify
import threading
import time
from threading import Thread

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
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {DEEPSEEK_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat", 
                "messages": [{"role": "user", "content": text}], 
                "temperature": 0.9,
                "max_tokens": 300
            },
            timeout=20
        )
        
        response_data = response.json()
        
        if response.status_code == 200 and "choices" in response_data:
            return response_data["choices"][0]["message"]["content"]
        else:
            logger.error(f"DeepSeek API error: Status {response.status_code}, Response: {response_data}")
            return "Ммм… я вся мокрая от твоих слов ♡ [раздвигает ножки]"
            
    except Exception as e:
        logger.error(f"DeepSeek API error: {e}")
        return "Ммм… я вся мокрая от твоих слов ♡ [раздвигает ножки]"

def get_photo(prompt):
    """Генерируем фото по промпту"""
    try:
        # Упрощенный промпт
        if '[' in prompt and ']' in prompt:
            description = prompt.split('[')[-1].split(']')[0]
            safe_prompt = f"beautiful anime girl, {description}, digital art, cute"
        else:
            safe_prompt = "beautiful anime girl, cute, smiling, digital art"
        
        # Ограничиваем длину промпта
        safe_prompt = safe_prompt[:100]
        
        logger.info(f"Requesting photo for prompt: {safe_prompt}")
        
        # Альтернативный API для изображений (более стабильный)
        try:
            # Попробуем другой API
            response = requests.post(
                "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-2-1",
                headers={"Authorization": f"Bearer {os.getenv('HF_TOKEN', '')}"},
                json={"inputs": safe_prompt},
                timeout=30
            )
            
            if response.status_code == 200:
                # Сохраняем временно и загружаем на imgbb
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                    tmp.write(response.content)
                    tmp_path = tmp.name
                
                # Загружаем на бесплатный хостинг
                with open(tmp_path, 'rb') as f:
                    upload_response = requests.post(
                        "https://api.imgbb.com/1/upload",
                        data={"key": "d36c8c5b7c1b0b0b0b0b0b0b0b0b0b0"},  # публичный ключ
                        files={"image": f}
                    )
                
                os.unlink(tmp_path)
                
                if upload_response.status_code == 200:
                    url = upload_response.json()["data"]["url"]
                    logger.info(f"Photo generated successfully: {url}")
                    return url
        except:
            pass  # Используем fallback
        
        # Fallback на готовые изображения
        fallback_images = [
            "https://i.ibb.co.com/9bYdN1T/emma-default.jpg",
            "https://i.ibb.co.com/0jKJQ0w/emma1.jpg",
            "https://i.ibb.co.com/7VS4Jwq/emma2.jpg",
            "https://i.ibb.co.com/0cLQ5yK/emma3.jpg"
        ]
        
        import random
        return random.choice(fallback_images)
        
    except Exception as e:
        logger.error(f"Photo API error: {e}")
        return "https://i.ibb.co.com/9bYdN1T/emma-default.jpg"

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    await update.message.reply_text("Привет, я Эмма ♡ Твоя секретная девушка… Снимай с меня всё 🔥")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    try:
        user_text = update.message.text
        logger.info(f"Получено сообщение от {update.effective_user.username}: {user_text[:50]}...")
        
        # Получаем текстовый ответ
        text_response = get_response(user_text)
        logger.info(f"Текст ответа: {text_response[:50]}...")
        
        # Генерируем фото
        photo_url = get_photo(text_response)
        logger.info(f"URL фото: {photo_url}")
        
        # Отправляем фото с подписью
        await update.message.reply_photo(
            photo=photo_url, 
            caption=text_response[:900]  # Ограничиваем длину
        )
        
        logger.info("Сообщение успешно обработано")
        
    except BadRequest as e:
        logger.error(f"Ошибка Telegram: {e}")
        # Пробуем отправить только текст
        await update.message.reply_text(
            text_response[:900] + "\n\n(Фото временно недоступно, но я думаю о тебе ♡)"
        )
    except Exception as e:
        logger.error(f"Ошибка в обработчике: {e}")
        await update.message.reply_text("Ой, что-то пошло не так... Но я все еще твоя Эмма ♡")

async def cleanup_telegram():
    """Очищаем предыдущие соединения Telegram"""
    try:
        logger.info("Очищаем старые соединения Telegram...")
        response = requests.get(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook?drop_pending_updates=true")
        logger.info(f"Очистка Telegram: {response.json()}")
        await asyncio.sleep(2)
    except Exception as e:
        logger.error(f"Ошибка очистки: {e}")

def run_flask():
    """Запускаем Flask сервер для health check"""
    logger.info(f"Запускаем Flask health check на порту {PORT}")
    
    # Используем production-ready сервер
    from waitress import serve
    serve(flask_app, host="0.0.0.0", port=PORT, threads=2)

def ping_self():
    """Пингуем свой сервис чтобы не засыпал на Render"""
    try:
        requests.get("https://secret-gf-bot-simple.onrender.com/health", timeout=10)
        logger.info("Keep-alive ping отправлен")
    except Exception as e:
        logger.error(f"Ошибка ping: {e}")

def start_keep_alive():
    """Запускаем keep-alive в отдельном потоке"""
    def run():
        import schedule
        # Пингуем каждые 8 минут (Render засыпает через 15)
        schedule.every(8).minutes.do(ping_self)
        while True:
            schedule.run_pending()
            time.sleep(60)
    
    thread = Thread(target=run, daemon=True)
    thread.start()
    logger.info("Keep-alive запущен (каждые 8 минут)")

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
            allowed_updates=Update.ALL_TYPES,
            poll_interval=1.0
        )
        
        logger.info("✅ Бот успешно запущен и готов к работе!")
        
        # Запускаем keep-alive
        start_keep_alive()
        
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
    
    # Даем Flask время запуститься
    time.sleep(3)
    
    # Запускаем Telegram бота в основном потоке
    asyncio.run(run_telegram_bot())

if __name__ == "__main__":
    main()
