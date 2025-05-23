# backtest/backtester.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from strategies.strategy_selector import StrategySelector
from data.binance_data import get_klines
import time

def run_backtest(pair: str, strategy_only=False):
    candles = get_klines(pair=pair, limit=500)
    if not candles or len(candles) < 50:
        print(f"[{pair}] Dados insuficientes para backtest.")
        return

    selector = StrategySelector(candles)
    action, strategy_name = selector.select_action()

    if strategy_only:
        print(f"[BACKTEST] Melhor estratégia atual: {strategy_name}")
        return

    balance = 1000.0  # USDT inicial
    position = None
    entry_price = 0.0

    for i in range(50, len(candles)):
        window = candles[i - 50:i]
        selector = StrategySelector(window)
        action, strategy = selector.select_action()
        price = candles[i]["close"]

        if position == "buy":
            if price >= entry_price * 1.05:
                balance *= 1.05
                position = None
                print(f"[{pair}] TAKE PROFIT @{price:.2f} - saldo: {balance:.2f}")
            elif price <= entry_price * 0.98:
                balance *= 0.98
                position = None
                print(f"[{pair}] STOP LOSS @{price:.2f} - saldo: {balance:.2f}")
        elif action == "buy":
            entry_price = price
            position = "buy"
            print(f"[{pair}] COMPRA @{price:.2f} via {strategy}")

    print(f"\n[RESULTADO] Saldo final em {pair}: {balance:.2f} USDT")
