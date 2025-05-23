import requests
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config.settings import TRADING_PAIRS, TIMEFRAME, VERBOSE

def format_pair(symbol: str) -> str:
    return symbol.replace("/", "")

def get_klines(pair=TRADING_PAIRS, interval=TIMEFRAME, limit=500):  # AUMENTADO PARA 500
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": format_pair(pair), "interval": interval, "limit": limit}
    try:
        res = requests.get(url, params=params)
        res.raise_for_status()
        data = res.json()
        candles = [{
            "timestamp": c[0],
            "open": float(c[1]),
            "high": float(c[2]),
            "low": float(c[3]),
            "close": float(c[4]),
            "volume": float(c[5])
        } for c in data]
        if VERBOSE:
            print(f"[DATA] Obtidos {len(candles)} candles para {pair}")
        return candles
    except Exception as e:
        print(f"[ERRO] Falha ao buscar candles: {e}")
        return []
