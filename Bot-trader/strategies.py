# strategies.py
import math
from abc import ABC, abstractmethod
import pandas as pd

class TradingStrategy(ABC):
    """Classe base abstrata para estratégias de trading."""

    @abstractmethod
    def decide_action(self, symbol, klines_raw, is_holding):
        """
        Determina a ação de trading ('BUY', 'SELL', 'HOLD') com base nos dados do gráfico
        e estado interno/externo (holding).
        """
        pass

    def _calculate_ema(self, prices, period):
        """Calcula a Média Móvel Exponencial (EMA) para um período (Manual)."""
        if period <= 0 or len(prices) < period:
             return None

        alpha = 2 / (period + 1)
        if len(prices) < period:
             return None

        ema = sum(prices[:period]) / period

        for price in prices[period:]:
            ema = (price * alpha) + (ema * (1 - alpha))

        return ema

class EmaThreeLinesCrossoverStrategy(TradingStrategy):
    """Estratégia baseada no cruzamento de TRÊS EMAs (rápida, média, lenta) - Versão Simples."""

    def __init__(self, symbol, fast_period=7, medium_period=20, slow_period=40):
        self.symbol = symbol
        self.fast_period = fast_period
        self.medium_period = medium_period
        self.slow_period = slow_period
        self.last_fast_ema = None
        self.last_medium_ema = None
        self.last_slow_ema = None
        self.required_klines = max(self.fast_period, self.medium_period, self.slow_period) + 1

    def decide_action(self, symbol, klines_raw, is_holding):
        klines = [float(k[4]) for k in klines_raw]

        if not klines or len(klines) < self.required_klines:
             return 'HOLD'

        current_fast_ema = self._calculate_ema(klines, self.fast_period)
        current_medium_ema = self._calculate_ema(klines, self.medium_period)
        current_slow_ema = self._calculate_ema(klines, self.slow_period)

        if current_fast_ema is None or current_medium_ema is None or current_slow_ema is None:
             print(f"[{symbol}] Erro ao calcular EMAs simples na estratégia. Dados Klines: {len(klines)}")
             return 'HOLD'

        if self.last_fast_ema is None or self.last_medium_ema is None or self.last_slow_ema is None:
             print(f"[{symbol}] Inicializando valores de EMAs anteriores na estratégia simples. Aguardando próximo ciclo.")
             self.last_fast_ema = current_fast_ema
             self.last_medium_ema = current_medium_ema
             self.last_slow_ema = current_slow_ema
             return 'HOLD'

        action = 'HOLD'
        has_crossed_below_slow = current_fast_ema < current_slow_ema and self.last_fast_ema >= self.last_slow_ema
        has_crossed_above_medium = current_fast_ema > current_medium_ema and self.last_fast_ema <= self.last_medium_ema
        has_crossed_below_medium = current_fast_ema < current_medium_ema and self.last_fast_ema >= self.last_medium_ema
        is_trading_zone_active = current_fast_ema > current_slow_ema and current_medium_ema > current_slow_ema

        if has_crossed_below_slow:
             action = 'SELL'
        elif is_trading_zone_active and has_crossed_below_medium:
             action = 'SELL'
        if action == 'HOLD' and is_trading_zone_active and has_crossed_above_medium:
             action = 'BUY'

        self.last_fast_ema = current_fast_ema
        self.last_medium_ema = current_medium_ema
        self.last_slow_ema = current_slow_ema

        return action

class EmaThreeLinesCrossoverStrategyETH(EmaThreeLinesCrossoverStrategy):
    """Estratégia 3-EMA simples para ETHUSDT (Parâmetros Específicos)."""
    def __init__(self, symbol, fast_period=10, medium_period=25, slow_period=50):
         super().__init__(symbol, fast_period, medium_period, slow_period)

class EmaThreeLinesCrossoverStrategySOL(EmaThreeLinesCrossoverStrategy):
    """Estratégia 3-EMA simples para SOLUSDT (Parâmetros Específicos)."""
    def __init__(self, symbol, fast_period=5, medium_period=15, slow_period=30):
         super().__init__(symbol, fast_period, medium_period, slow_period)


class FilteredEmaCrossoverStrategy(TradingStrategy):
    """Estratégia Filtrada: 3 EMAs + RSI + Volume Filter (Calculado via Pandas)."""

    def __init__(self, symbol, fast_period=7, medium_period=20, slow_period=40,
                 rsi_period=14, rsi_overbought=70, rsi_oversold=30,
                 volume_length_short=14, volume_length_long=50, volume_threshold=1.0):

        self.symbol = symbol
        self.fast_period = fast_period
        self.medium_period = medium_period
        self.slow_period = slow_period
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.volume_length_short = volume_length_short
        self.volume_length_long = volume_length_long
        self.volume_threshold = volume_threshold

        self.last_ema7 = None
        self.last_ema20 = None
        self.last_ema40 = None
        self.last_rsi = None
        self.last_volume_ratio = None
        self.last_bearish_price_confirmation = False

        self.waitingForSecondaryBuy = False

        max_period = max(fast_period, medium_period, slow_period, rsi_period, volume_length_short, volume_length_long)
        self.required_klines = max_period + 25

        print(f"[{self.symbol}] Estratégia Filtered EMA (No ADX): Requisito mínimo de Klines = {self.required_klines}")

    def _calculate_ema_pd(self, series, period):
        """Calcula EMA usando pandas ewm."""
        if period <= 0 or len(series) < period:
            return pd.Series([None] * len(series))
        return series.ewm(span=period, adjust=False, min_periods=period).mean()

    def _calculate_rsi_pd(self, closes, period):
        """Calcula RSI usando pandas."""
        if period <= 0 or len(closes) < period:
            return pd.Series([None] * len(closes))

        delta = closes.diff()
        gains = delta.mask(delta < 0, 0)
        losses = delta.mask(delta > 0, 0).abs()

        avg_gains = gains.ewm(span=period, adjust=False, min_periods=period).mean()
        avg_losses = losses.ewm(span=period, adjust=False, min_periods=period).mean()

        rs = avg_gains / avg_losses.replace(0, pd.NA)
        rsi = 100 - (100 / (1 + rs))
        return rsi


    def decide_action(self, symbol, klines_raw, is_holding):
        """
        Determina a ação com base na lógica da estratégia filtrada (SEM ADX).
        """
        if not klines_raw or len(klines_raw) < self.required_klines:
             return 'HOLD'

        df = pd.DataFrame(klines_raw, columns=[
             'Open time', 'Open', 'High', 'Low', 'Close', 'Volume',
             'Close time', 'Quote asset volume', 'Number of trades',
             'Taker buy base asset volume', 'Taker buy quote asset volume', 'Ignore'
        ])
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
             df[col] = pd.to_numeric(df[col], errors='coerce')
        df['Close'] = df['Close'].astype(float)
        df['High'] = df['High'].astype(float)
        df['Low'] = df['Low'].astype(float)
        df['Volume'] = df['Volume'].astype(float)

        df.dropna(subset=['Close'], inplace=True)

        if len(df) < self.required_klines:
             return 'HOLD'

        # --- Calcula Indicadores usando Pandas ---

        ema7 = self._calculate_ema_pd(df['Close'], self.fast_period)
        ema20 = self._calculate_ema_pd(df['Close'], self.medium_period)
        ema40 = self._calculate_ema_pd(df['Close'], self.slow_period)

        current_rsi = self._calculate_rsi_pd(df['Close'], self.rsi_period)

        volume_sma_short = df['Volume'].rolling(window=self.volume_length_short, min_periods=1).mean()
        volume_sma_long = df['Volume'].rolling(window=self.volume_length_long, min_periods=1).mean()
        volume_ratio = volume_sma_short / volume_sma_long.replace(0, pd.NA)

        # --- Obtém os valores mais recentes dos indicadores ---
        indicators_needed = [ema7, ema20, ema40, current_rsi, volume_ratio]
        if any(pd.isna(series.iloc[-1]) for series in indicators_needed):
             return 'HOLD'

        current_ema7 = ema7.iloc[-1]
        current_ema20 = ema20.iloc[-1]
        current_ema40 = ema40.iloc[-1]
        current_rsi = current_rsi.iloc[-1]
        current_volume_ratio = volume_ratio.iloc[-1]

        current_bearish_price_confirmation = False
        if len(df) >= 3:
             current_bearish_price_confirmation = df['Close'].iloc[-1] < df['Close'].iloc[-2] and df['Close'].iloc[-2] < df['Close'].iloc[-3]

        # --- Inicializa valores 'last_' ---
        if self.last_ema7 is None or self.last_ema20 is None or self.last_ema40 is None or self.last_rsi is None or self.last_volume_ratio is None or self.last_bearish_price_confirmation is False:
             print(f"[{symbol}] Inicializando valores 'last_' na estratégia filtrada (No ADX). Aguardando próximo ciclo.")
             self.last_ema7 = current_ema7
             self.last_ema20 = current_ema20
             self.last_ema40 = current_ema40
             self.last_rsi = current_rsi
             self.last_volume_ratio = current_volume_ratio
             self.last_bearish_price_confirmation = current_bearish_price_confirmation
             self.waitingForSecondaryBuy = False
             return 'HOLD'

        # --- Obtém os valores 'last_' armazenados ---
        last_ema7 = self.last_ema7
        last_ema20 = self.last_ema20
        last_ema40 = self.last_ema40
        last_rsi = self.last_rsi
        last_volume_ratio = self.last_volume_ratio
        last_bearish_price_confirmation = self.last_bearish_price_confirmation


        # --- Traduz as Condições (SEM ADX) ---

        bullishCross7_40 = current_ema7 > current_ema40 and last_ema7 <= last_ema40
        bearishCross7_40 = current_ema7 < current_ema40 and last_ema40 >= last_ema40
        bullishCross7_20 = current_ema7 > current_ema20 and last_ema7 <= last_ema20
        bearishCross7_20 = current_ema7 < current_ema20 and last_ema7 >= last_ema20
        bearishCross20_40 = current_ema20 < current_ema40 and last_ema20 >= last_ema40

        aboveEma40 = current_ema7 > current_ema40 and current_ema20 > current_ema40
        rsiFilterBuy = current_rsi < self.rsi_overbought
        rsiFilterShort = current_rsi > self.rsi_oversold
        volumeFilter = current_volume_ratio > self.volume_threshold

        # --- Lógica dos Sinais (SEM ADX) ---

        buyPrimaryCondition = bullishCross7_40 and rsiFilterBuy and volumeFilter
        if buyPrimaryCondition: print(f"[{symbol}] Condição: Compra Primária True (No ADX)")

        buySecondaryCondition_this_candle = self.waitingForSecondaryBuy and bullishCross7_20 and aboveEma40 and rsiFilterBuy and volumeFilter
        if buySecondaryCondition_this_candle: print(f"[{symbol}] Condição: Compra Secundária True (No ADX)")

        buySignal = buyPrimaryCondition or buySecondaryCondition_this_candle

        sellLongSignal = bearishCross20_40
        if sellLongSignal: print(f"[{symbol}] Condição: Saída Long (EMA 20<40) True")

        sellShortSignal = bearishCross7_40 and rsiFilterShort and volumeFilter and current_bearish_price_confirmation
        if sellShortSignal: print(f"[{symbol}] Condição: Entrada Short True (No ADX)")


        # --- Determina a Ação Final ---
        action = 'HOLD'

        if sellLongSignal:
             action = 'SELL'
        elif sellShortSignal:
             action = 'SELL'

        if action == 'HOLD' and buySignal:
             action = 'BUY'

        # --- Atualiza Variáveis de Estado PERSISTENTES para a PRÓXIMA execução ---
        self.last_ema7 = current_ema7
        self.last_ema20 = current_ema20
        self.last_ema40 = current_ema40
        self.last_rsi = current_rsi
        self.last_volume_ratio = current_volume_ratio
        self.last_bearish_price_confirmation = current_bearish_price_confirmation

        # Lógica CORRIGIDA para atualizar o estado 'waitingForSecondaryBuy' para a PRÓXIMA execução
        # Baseado na lógica Pine Script: var := if cond1 then val1 else if cond2 then val2 else var[1]
        waitingForSecondaryBuy_at_start_of_candle = self.waitingForSecondaryBuy # Pega o valor DESTE estado antes de ser potencialmente alterado nesta barra (valor do fim da barra anterior)

        if buySecondaryCondition_this_candle: # Se a condição secundária foi atendida NESTA barra
            self.waitingForSecondaryBuy = False # O NOVO estado de espera para a próxima barra é False
        elif bearishCross7_20 and aboveEma40 and not buySecondaryCondition_this_candle: # Senão, se o TRIGGER para esperar a secundária ocorreu NESTA barra E a condição secundária NÃO FOI atendida NESTA barra:
             self.waitingForSecondaryBuy = True # O NOVO estado de espera para a próxima barra é True
        else: # Senão (nenhuma das condições acima foi atendida NESTA barra)
             self.waitingForSecondaryBuy = waitingForSecondaryBuy_at_start_of_candle # O NOVO estado de espera para a próxima barra é o mesmo que era no início desta barra (final da anterior)


        return action

class EmaThreeLinesCrossoverStrategyETH(EmaThreeLinesCrossoverStrategy):
    """Estratégia 3-EMA simples para ETHUSDT (Parâmetros Específicos)."""
    def __init__(self, symbol, fast_period=10, medium_period=25, slow_period=50):
         super().__init__(symbol, fast_period, medium_period, slow_period)

class EmaThreeLinesCrossoverStrategySOL(EmaThreeLinesCrossoverStrategy):
    """Estratégia 3-EMA simples para SOLUSDT (Parâmetros Específicos)."""
    def __init__(self, symbol, fast_period=5, medium_period=15, slow_period=30):
         super().__init__(symbol, fast_period, medium_period, slow_period)
