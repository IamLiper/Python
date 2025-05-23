# dashboard/app.py
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from flask import Flask, render_template, request, redirect, url_for, session
from trading.position_manager import position
from data.binance_data import get_klines
from config.settings import TRADING_PAIRS
from utils.state import shared_state
from main import start_bot, stop_bot
from binance.client import Client
from config.settings import API_KEY, API_SECRET
from apscheduler.schedulers.background import BackgroundScheduler
from scheduler.daily_report import send_daily_report

app = Flask(__name__)
app.secret_key = os.urandom(24)

client = Client(API_KEY, API_SECRET)

USERNAME = "Blake"
PASSWORD = "1820"

@app.route("/", methods=["GET"])
def index():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

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

    balances = {
        "USDT": float(client.get_asset_balance(asset="USDT")["free"])
    }

    for pair in TRADING_PAIRS:
        base = pair.replace("/USDT", "")
        balances[base] = float(client.get_asset_balance(asset=base)["free"])

    return render_template("index.html",
        running=shared_state["running"],
        positions=positions,
        balances=balances,
        log=shared_state["log"]
    )

@app.route("/start", methods=["POST"])
def start():
    start_bot()
    return redirect(url_for("index"))

@app.route("/stop", methods=["POST"])
def stop():
    stop_bot()
    return redirect(url_for("index"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["username"] == USERNAME and request.form["password"] == PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("index"))
        return "Login inválido"
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/log")
def get_log():
    return {"log": list(shared_state["log"])}

scheduler = BackgroundScheduler()
scheduler.add_job(send_daily_report, "cron", hour=0, minute=0)
scheduler.start()

if __name__ == "__main__":
    app.run(port=5000, debug=True)

@app.route("/status")
def get_status():
    from trading.position_manager import position
    from data.binance_data import get_klines

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

    balances = {
        "USDT": float(client.get_asset_balance(asset="USDT")["free"])
    }

    for pair in TRADING_PAIRS:
        base = pair.replace("/USDT", "")
        balances[base] = float(client.get_asset_balance(asset=base)["free"])

    return {
        "positions": positions,
        "balances": balances,
        "log": list(shared_state["log"]),
        "running": shared_state["running"]
    }
