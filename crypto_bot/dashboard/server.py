# dashboard/server.py

import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from flask import Flask, render_template_string
from trading.paper_executor import simulated_balances
from trading.position_manager import position
from config.settings import TRADING_PAIRS
from data.binance_data import get_klines

app = Flask(__name__)

TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Trading Bot Dashboard</title>
    <meta http-equiv="refresh" content="5" />
    <style>
        body { font-family: Arial; margin: 20px; background-color: #f4f4f4; }
        h1 { color: #333; }
        table { border-collapse: collapse; width: 60%; }
        th, td { padding: 8px 12px; border: 1px solid #aaa; text-align: center; }
    </style>
</head>
<body>
    <h1>🚀 Trading Bot Dashboard</h1>
    <table>
        <tr><th>Par</th><th>Preço Atual</th><th>Posição</th><th>Entrada</th><th>Ação</th></tr>
        {% for pair, status in positions.items() %}
        <tr>
            <td>{{ pair }}</td>
            <td>{{ status.last_price }}</td>
            <td>{{ status.is_open }}</td>
            <td>{{ status.entry_price or '-' }}</td>
            <td>{{ status.action or '-' }}</td>
        </tr>
        {% endfor %}
    </table>

    <h2>💼 Paper Trading - Saldo Simulado</h2>
    <ul>
        {% for asset, amount in balances.items() %}
        <li>{{ asset }}: {{ "%.4f"|format(amount) }}</li>
        {% endfor %}
    </ul>
</body>
</html>
"""

@app.route("/")
def index():
    positions = {}
    for pair in TRADING_PAIRS:
        candles = get_klines(pair=pair, limit=1)
        last_price = candles[-1]["close"] if candles else 0

        pos = position.get(pair, {})
        positions[pair] = {
            "last_price": round(last_price, 4),
            "is_open": pos.get("is_open", False),
            "entry_price": pos.get("entry_price", None),
            "action": pos.get("action", None)
        }

    return render_template_string(TEMPLATE, positions=positions, balances=simulated_balances)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
