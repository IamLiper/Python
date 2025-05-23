import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from strategies.rsi_strategy import RSIStrategy
from strategies.moving_average import MovingAverageStrategy
from strategies.macd_strategy import MACDStrategy
from strategies.bollinger_strategy import BollingerStrategy
from utils.trend_filter import is_market_bullish


class StrategySelector:
    def __init__(self, candles):
        self.candles = candles
        self.strategies = [
            RSIStrategy(candles),
            MovingAverageStrategy(candles),
            MACDStrategy(candles),
            BollingerStrategy(candles)
        ]

    def select_action(self):
        market_is_bullish = is_market_bullish(self.candles)

        for s in self.strategies:
            if s.should_buy() and market_is_bullish:
                return "buy", s.name()
            if s.should_sell() and not market_is_bullish:
                return "sell", s.name()

        return "hold", None

