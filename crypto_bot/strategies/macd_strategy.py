from strategies.base_strategies import BaseStrategy
from utils.indicators import calculate_macd

class MACDStrategy(BaseStrategy):
    def __init__(self, candles):
        super().__init__(candles)
        closes = [c["close"] for c in candles]
        self.macd, self.signal = calculate_macd(closes)

    def should_buy(self) -> bool:
        return self.macd[-2] < self.signal[-2] and self.macd[-1] > self.signal[-1]

    def should_sell(self) -> bool:
        return self.macd[-2] > self.signal[-2] and self.macd[-1] < self.signal[-1]

    def name(self) -> str:
        return "MACD"
