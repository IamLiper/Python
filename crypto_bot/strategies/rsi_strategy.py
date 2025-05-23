from strategies.base_strategies import BaseStrategy
from utils.indicators import calculate_rsi
from utils.state import append_log



class RSIStrategy(BaseStrategy):
    def __init__(self, candles, period=14):
        super().__init__(candles)
        self.closes = [c["close"] for c in candles]
        self.rsi = calculate_rsi(self.closes, period)

    def should_buy(self) -> bool:
        value = self.rsi[-1] if self.rsi else None
        if value:
            append_log(f"[RSI] Último RSI: {value:.2f}")
        return value is not None and value < 30

    def should_sell(self) -> bool:
        value = self.rsi[-1] if self.rsi else None
        return value is not None and value > 70

    def name(self) -> str:
        return "RSI"
