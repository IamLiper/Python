# utils/trend_filter.py

from utils.indicators import calculate_sma

def is_market_bullish(candles, period=200):
    closes = [c["close"] for c in candles]
    ma = calculate_sma(closes, period)

    if not ma or ma[-1] is None:
        return False  # Sem dados suficientes

    return closes[-1] > ma[-1]  # Preço acima da média = alta
