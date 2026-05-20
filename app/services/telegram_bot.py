import logging
import requests
import time
import threading

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class SimpleTelegramBot:
    """Simplified Telegram Bot - menggunakan Long Polling via requests"""
    
    def __init__(self, token):
        self.bot_token = token
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found!")
        
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.update_id = 0
        self.stop_event = threading.Event()
        logger.info(f"Bot initialized: {self.bot_token[:20]}...")

    def stop(self):
        """Signal polling loop to stop."""
        self.stop_event.set()
    
    def send_message(self, chat_id, text):
        """Send message to user"""
        try:
            url = f"{self.api_url}/sendMessage"
            payload = {
                'chat_id': chat_id,
                'text': text,
                'parse_mode': 'HTML'
            }
            response = requests.post(url, json=payload, timeout=10)
            return response.json()
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return None
    
    def get_updates(self):
        """Get updates from Telegram"""
        try:
            url = f"{self.api_url}/getUpdates"
            payload = {'offset': self.update_id, 'timeout': 30}
            response = requests.post(url, json=payload, timeout=35)
            return response.json()
        except Exception as e:
            logger.error(f"Error getting updates: {e}")
            return {'ok': False, 'result': []}
    
    def handle_command(self, chat_id, text, first_name):
        """Handle command from user"""
        command = text.split()[0].lower()
        
        if command == '/start':
            message = f"""
Halo {first_name}!

Selamat datang di <b>Jadwal Kerja Bot</b>

Perintah yang bisa digunakan:
/start - Mulai
/help - Bantuan
/myid - Lihat ID Telegram Anda
/test - Test message

Atau buka aplikasi scheduling untuk link Telegram.
            """
            logger.info(f"Command /start to {chat_id}")
        
        elif command == '/help':
            message = """
<b>Bantuan Bot Jadwal Kerja</b>

Bot ini digunakan untuk menerima notifikasi jadwal kerja.

<b>Perintah:</b>
/start - Mulai
/help - Bantuan ini
/myid - Lihat Telegram ID Anda
/test - Test message

<b>Cara Link Telegram:</b>
1. Buka aplikasi scheduling
2. Ke menu Profile
3. Klik 'Pengaturan Telegram'
4. Klik 'Hubungkan Telegram'
5. Dapatkan kode verifikasi
6. Kirim kode ini ke bot (copy-paste saja)
7. Selesai! Telegram sudah terhubung
            """
            logger.info(f"Command /help to {chat_id}")
        
        elif command == '/myid':
            message = f"""
<b>Info Anda</b>

<b>ID Telegram:</b> <code>{chat_id}</code>
<b>Nama:</b> {first_name}

ID ini bisa digunakan untuk berbagai keperluan.
            """
            logger.info(f"Command /myid to {chat_id}")
        
        elif command == '/test':
            message = f"Test message - Bot berjalan dengan baik!\n\nTelegram ID Anda: {chat_id}"
            logger.info(f"Command /test to {chat_id}")
        
        else:
            message = f"Command tidak dikenal: {command}\n\nKetik /help untuk bantuan"
            logger.info(f"Unknown command: {command}")
        
        return message
    
    def send_verification_to_backend(self, chat_id, username):
        """Send verification data to backend API"""
        try:
            # This will be called when user sends verification code
            # Backend will verify and link account
            logger.info(f"Verification data ready: telegram_id={chat_id}, username={username}")
            return True
        except Exception as e:
            logger.error(f"Error sending to backend: {e}")
            return False
    
    def verify_code_with_backend(self, chat_id, username, code):
        """Send verification code to backend for verification
        Backend akan lookup user_id dari code di session
        """
        try:
            import os
            bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
            
            if not bot_token:
                logger.error("TELEGRAM_BOT_TOKEN not found")
                return False
            
            # Call backend API. Keep the default local URL, but allow .env to
            # override it when Flask runs on a different host/port.
            backend_base_url = os.getenv('APP_BASE_URL')
            if not backend_base_url:
                backend_host = os.getenv('FLASK_HOST', '127.0.0.1')
                backend_port = os.getenv('FLASK_PORT', '5000')
                backend_base_url = f"http://{backend_host}:{backend_port}"

            backend_url = f"{backend_base_url.rstrip('/')}/user/telegram-verify-from-bot"
            
            payload = {
                'code': code.strip(),
                'telegram_id': str(chat_id),
                'username': username or '',
                'bot_token': bot_token
            }
            
            logger.info(f"Sending verification to backend: {payload['telegram_id']}, code: {code}")
            
            response = requests.post(backend_url, json=payload, timeout=10)
            result = response.json()
            
            if result.get('success'):
                logger.info(f"Verification successful for {chat_id}")
                return True
            else:
                logger.warning(f"Verification failed: {result.get('error')}")
                return False
        
        except Exception as e:
            logger.error(f"Error verifying code with backend: {e}")
            return False
    
    def run(self):
        """Start bot polling"""
        try:
            logger.info("="*60)
            logger.info("TELEGRAM BOT STARTED")
            logger.info("="*60)
            logger.info("Bot is listening for messages...")
            logger.info("Open Telegram and send /start to your bot")
            logger.info("Press Ctrl+C to stop")
            logger.info("="*60)
            
            while not self.stop_event.is_set():
                try:
                    # Get updates
                    response = self.get_updates()
                    
                    if not response.get('ok'):
                        logger.error(f"API Error: {response}")
                        self.stop_event.wait(5)
                        continue
                    
                    updates = response.get('result', [])
                    
                    for update in updates:
                        self.update_id = update['update_id'] + 1
                        
                        # Handle message
                        if 'message' in update:
                            message_data = update['message']
                            chat_id = message_data['chat']['id']
                            text = message_data.get('text', '')
                            first_name = message_data['chat'].get('first_name', 'User')
                            username = message_data['chat'].get('username', '')
                            
                            logger.info(f"New message from {first_name} ({chat_id}): {text}")
                            
                            # Check if command
                            if text.startswith('/'):
                                response_text = self.handle_command(chat_id, text, first_name)
                            else:
                                # Treat as verification code
                                # Send to backend for verification
                                is_verified = self.verify_code_with_backend(chat_id, username, text)
                                
                                if is_verified:
                                    response_text = "Sukses! Telegram Anda sudah terhubung dengan aplikasi.\n\nAnda akan menerima notifikasi jadwal kerja."
                                else:
                                    response_text = "Kode tidak valid atau sudah kadaluarsa.\n\nCoba buka aplikasi lagi dan dapatkan kode baru."
                            
                            # Send response
                            result = self.send_message(chat_id, response_text)
                            
                            if result and result.get('ok'):
                                logger.info(f"Response sent to {chat_id}")
                            else:
                                logger.error(f"Failed to send response: {result}")
                    
                    # Small delay to avoid CPU spinning
                    if not updates:
                        self.stop_event.wait(1)
                
                except Exception as e:
                    logger.error(f"Error in polling loop: {e}")
                    self.stop_event.wait(5)
        
        except KeyboardInterrupt:
            logger.info("\nBot stopped by user")
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            raise
        finally:
            logger.info("Telegram bot polling stopped")


def start_bot(token):
    """Entry point untuk jalankan bot"""
    try:
        bot = SimpleTelegramBot(token)
        bot.run()
    except Exception as e:
        print(f"Fatal error: {e}")
        exit(1)
