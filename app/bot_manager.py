import threading
import logging
import atexit
from app.services.telegram_bot import SimpleTelegramBot

logger = logging.getLogger(__name__)

bot_thread = None
bot_instance = None
bot_lock = threading.Lock()

def start_bot_thread(token):
    """Start bot thread if not already running"""
    global bot_thread, bot_instance

    with bot_lock:
        if bot_thread is not None and bot_thread.is_alive():
            logger.info("Bot thread already running")
            return

        logger.info("Starting bot thread...")
        bot_instance = SimpleTelegramBot(token)
        bot_thread = threading.Thread(
            target=bot_instance.run,
            name="telegram-bot-polling",
            daemon=True
        )
        bot_thread.start()
        logger.info("Bot thread started")

def stop_bot_thread():
    """Stop bot thread"""
    global bot_thread, bot_instance

    with bot_lock:
        if bot_instance is not None:
            logger.info("Stopping bot thread...")
            bot_instance.stop()

        if bot_thread is not None and bot_thread.is_alive():
            bot_thread.join(timeout=40)

        bot_thread = None
        bot_instance = None
        logger.info("Bot thread stopped")


atexit.register(stop_bot_thread)
