# backtest/run.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backtest.backtester import run_backtest

# Testar uma estratégia isoladamente
run_backtest("BTC/USDT", strategy_only=True)

# Backtest completo
run_backtest("BTC/USDT")
run_backtest("ETH/USDT")
run_backtest("SOL/USDT")
