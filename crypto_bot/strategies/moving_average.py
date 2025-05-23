from strategies.base_strategies import BaseStrategy
from utils.indicators import calculate_sma

class MovingAverageStrategy(BaseStrategy):
    def __init__(self, candles, short=9, long=21):
        super().__init__(candles)
        closes = [c["close"] for c in candles]
        self.short_ma = calculate_sma(closes, short)
        self.long_ma = calculate_sma(closes, long)

    def should_buy(self) -> bool:
        return self.short_ma[-2] < self.long_ma[-2] and self.short_ma[-1] > self.long_ma[-1]

    def should_sell(self) -> bool:
        return self.short_ma[-2] > self.long_ma[-2] and self.short_ma[-1] < self.long_ma[-1]

    def name(self) -> str:
        return "MA Crossover"
