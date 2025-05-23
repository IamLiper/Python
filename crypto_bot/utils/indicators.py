import numpy as np

def calculate_rsi(closes, period=14):
    if len(closes) < period + 1:
        return []
    closes = np.array(closes)
    deltas = np.diff(closes)
    seed = deltas[:period]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    rs = up / down if down != 0 else 0
    rsi = [100 - (100 / (1 + rs))]
    for i in range(period, len(closes) - 1):
        delta = deltas[i]
        gain = max(delta, 0)
        loss = -min(delta, 0)
        up = (up * (period - 1) + gain) / period
        down = (down * (period - 1) + loss) / period
        rs = up / down if down != 0 else 0
        rsi.append(100 - (100 / (1 + rs)))
    return [None] * period + rsi

def calculate_sma(data, period):
    if len(data) < period:
        return []
    return [None] * (period - 1) + [
        sum(data[i - period + 1:i + 1]) / period for i in range(period - 1, len(data))
    ]

def calculate_macd(closes, short=12, long=26, signal=9):
    def ema(data, period):
        alpha = 2 / (period + 1)
        ema_values = [sum(data[:period]) / period]
        for price in data[period:]:
            ema_values.append(alpha * price + (1 - alpha) * ema_values[-1])
        return [None] * (period - 1) + ema_values
    short_ema = ema(closes, short)
    long_ema = ema(closes, long)
    macd_line = [s - l if s and l else None for s, l in zip(short_ema, long_ema)]
    signal_line = ema([m for m in macd_line if m is not None], signal)
    signal_line = [None] * (len(macd_line) - len(signal_line)) + signal_line
    return macd_line, signal_line

def calculate_bollinger_bands(data, period=20, deviation=2):
    sma = calculate_sma(data, period)
    stddev = [
        np.std(data[i - period + 1:i + 1]) if i >= period - 1 else None
        for i in range(len(data))
    ]
    upper = [s + deviation * d if s and d else None for s, d in zip(sma, stddev)]
    lower = [s - deviation * d if s and d else None for s, d in zip(sma, stddev)]
    return lower, sma, upper

def calculate_ma200(data):
    return calculate_sma(data, 200)
