from strategies.base_strategies import BaseStrategy
from utils.indicators import calculate_bollinger_bands

class BollingerStrategy(BaseStrategy):
    def __init__(self, candles, period=20, deviation=2):
        super().__init__(candles)
        closes = [c["close"] for c in candles]
        self.lower, self.middle, self.upper = calculate_bollinger_bands(closes, period, deviation)
        self.closes = closes

    def should_buy(self) -> bool:
        return self.closes[-1] < self.lower[-1]

    def should_sell(self) -> bool:
        return self.closes[-1] > self.upper[-1]

    def name(self) -> str:
        return "Bollinger Bands"
