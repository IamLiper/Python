# config/settings.py

# ===============================
# CONFIGURAÇÕES GERAIS DO BOT
# ===============================

# Chaves da API da Binance
API_KEY = "LkUJ1sn6A72rKYsK7ev1VWfrW4S3TZfdjZ81CGl5gGmG3HqVzKWIcXRIahBWbgCR"       # TODO: Substitua pela sua chave da API
API_SECRET = "8IZ3xVdeew6gfSPpFjzSGYQHqz9yUeqxJEt2ARZiyIcfVmRAZHz68l3OkESzAyQ1" # TODO: Substitua pelo seu segredo da API

TELEGRAM_TOKEN = "7468073016:AAGYkg1iOb6seTGdo4wBXHWSUBczPiGVKd0"
TELEGRAM_CHAT_ID = "6117002707"

TRADING_PAIRS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
TRADE_AMOUNT_USDT = 10.0
STOP_LOSS_PCT = 0.02
TAKE_PROFIT_PCT = 0.05
TIMEFRAME = "1m"
USE_REAL_FUNDS = True
LOOP_INTERVAL = 60
VERBOSE = True

TRADE_PERCENT_PER_PAIR = {
    "BTC/USDT": 0.01,
    "ETH/USDT": 0.01,
    "SOL/USDT": 0.01
}

MIN_NOTIONAL_PER_PAIR = {
    "BTC/USDT": 10.0,
    "ETH/USDT": 10.0,
    "SOL/USDT": 10.0
}

TRADING_MODE_PER_PAIR = {
    "BTC/USDT": "real", # modo simulado
    "ETH/USDT": "real",
    "SOL/USDT": "real"  
}

