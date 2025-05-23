from abc import ABC, abstractmethod

class BaseStrategy(ABC):
    def __init__(self, candles: list):
        self.candles = candles

    @abstractmethod
    def should_buy(self) -> bool:
        pass

    @abstractmethod
    def should_sell(self) -> bool:
        pass

    @abstractmethod
    def name(self) -> str:
        pass
