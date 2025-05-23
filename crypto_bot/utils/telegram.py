import requests
from config.settings import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID

def send_telegram_message(text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": text}
        )
    except Exception as e:
        print(f"[Telegram] Erro: {e}")
