# scheduler/daily_report.py

from binance.client import Client
from config.settings import API_KEY, API_SECRET, TRADING_PAIRS
from trading.position_manager import position
from utils.telegram import send_telegram_message
from utils.chart import gerar_grafico_lucro
from datetime import datetime
import json
import os

client = Client(API_KEY, API_SECRET)
EARNINGS_FILE = "scheduler/earnings.json"

def send_daily_report():
    now = datetime.now().strftime("%d/%m/%Y")
    today_key = datetime.now().strftime("%Y-%m-%d")
    message = f"📊 Relatório Diário – {now}\n\n"

    # Obter saldo USDT atual
    usdt_now = float(client.get_asset_balance(asset="USDT")["free"])
    saldo_msg = f"💰 Saldo atual: {usdt_now:.2f} USDT\n"

    # Calcular lucro líquido
    if os.path.exists(EARNINGS_FILE):
        with open(EARNINGS_FILE, "r") as f:
            dados = json.load(f)
    else:
        dados = {}

    saldo_ontem = list(dados.values())[-1] if dados else usdt_now
    lucro = round(usdt_now - saldo_ontem, 2)
    dados[today_key] = usdt_now

    with open(EARNINGS_FILE, "w") as f:
        json.dump(dados, f, indent=2)

    lucro_msg = f"{'📈 Lucro' if lucro >= 0 else '📉 Prejuízo'} do dia: {lucro:+.2f} USDT\n\n"

    # Saldo de ativos
    message += saldo_msg + lucro_msg
    for pair in TRADING_PAIRS:
        base = pair.replace("/USDT", "")
        balance = float(client.get_asset_balance(asset=base)["free"])
        message += f"• {base}: {balance:.6f}\n"

    # Posições
    abertas = [
        f"{p} @ {data['entry_price']} ({data['action']})"
        for p, data in position.items() if data["is_open"]
    ]
    if abertas:
        message += "\n📍 Posições abertas:\n" + "\n".join(abertas)
    else:
        message += "\n✅ Nenhuma posição aberta."

    send_telegram_message(message)

    # Enviar gráfico se disponível
    path_img = gerar_grafico_lucro()
    if path_img:
        enviar_imagem_telegram(path_img)

def enviar_imagem_telegram(path):
    from config.settings import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
    import requests

    with open(path, "rb") as img:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        files = {"photo": img}
        data = {"chat_id": TELEGRAM_CHAT_ID}
        requests.post(url, data=data, files=files)
