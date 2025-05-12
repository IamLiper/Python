# strategies.py (Com sugestões de logs para depuração)
import math
from abc import ABC, abstractmethod
import pandas as pd
import numpy as np # Importado para tratar inf/nan em alguns casos

# ==============================================================================
# FUNÇÕES AUXILIARES PARA CÁLCULO DE INDICADORES TÉCNICOS USANDO PANDAS
# ==============================================================================

def _calculate_ema_pd(series: pd.Series, period: int) -> pd.Series:
    """Calcula a Média Móvel Exponencial (EMA) usando Pandas."""
    if period <= 0: return pd.Series(dtype=float, index=series.index, name=f"EMA_{period}")
    # min_periods=1 permite que o cálculo comece antes, resultando em NaNs no início se len(series) < period
    return series.ewm(span=period, adjust=False, min_periods=1).mean().rename(f"EMA_{period}")

def _calculate_rsi_pd(closes: pd.Series, period: int) -> pd.Series:
    """Calcula o Índice de Força Relativa (RSI) usando Pandas."""
    if period <= 0: return pd.Series(dtype=float, index=closes.index, name=f"RSI_{period}")
    delta = closes.diff()
    gain = delta.where(delta > 0, 0.0).fillna(0.0)
    loss = (-delta).where(delta < 0, 0.0).fillna(0.0)

    # Usar min_periods=1 para começar a calcular médias mesmo com poucos dados
    avg_gain = gain.ewm(com=period - 1, adjust=False, min_periods=1).mean()
    avg_loss = loss.ewm(com=period - 1, adjust=False, min_periods=1).mean()

    # Calcular RS, tratando divisão por zero
    rs = avg_gain / avg_loss
    # Substituir infinito (ocorre quando avg_loss é 0 e avg_gain > 0) por um número grande para levar RSI a 100
    rs.replace([np.inf, -np.inf], np.nan, inplace=True) # Primeiro trata inf
    rs.ffill(inplace=True) # Tenta preencher NaNs (pode ocorrer no início ou se avg_loss e avg_gain são 0)

    rsi = 100.0 - (100.0 / (1.0 + rs))

    # Correções finais: Se avg_loss é 0, RSI -> 100. Se avg_gain é 0 (e avg_loss > 0), RSI -> 0.
    # Estas condições são geralmente cobertas pelo cálculo de rs, mas é uma segurança.
    rsi.loc[avg_loss == 0] = 100.0
    rsi.loc[(avg_gain == 0) & (avg_loss != 0)] = 0.0

    # Preenche quaisquer NaNs restantes (geralmente no início) com 50
    rsi.fillna(50.0, inplace=True)
    # Garante que o RSI esteja entre 0 e 100
    rsi = rsi.clip(0, 100)

    return rsi.rename(f"RSI_{period}")


def _calculate_adx_di_pd(high: pd.Series, low: pd.Series, close: pd.Series, period: int):
    """Calcula ADX, +DI, e -DI usando Pandas, com Wilder's Smoothing (RMA)."""
    if period <= 0:
        nan_series = pd.Series(dtype=float, index=high.index)
        return nan_series.rename(f"ADX_{period}"), nan_series.rename(f"PLUS_DI_{period}"), nan_series.rename(f"MINUS_DI_{period}")

    # True Range (TR)
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr_series = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1, skipna=False).fillna(0.0)

    # Average True Range (ATR) usando RMA (Wilder's Smoothing)
    atr = tr_series.ewm(alpha=1/period, adjust=False, min_periods=1).mean()

    # Directional Movement (+DM, -DM)
    move_up = high.diff().fillna(0.0)
    move_down = -low.diff().fillna(0.0)
    plus_dm = pd.Series(0.0, index=high.index)
    minus_dm = pd.Series(0.0, index=high.index)
    cond_plus = (move_up > move_down) & (move_up > 0)
    plus_dm[cond_plus] = move_up[cond_plus]
    cond_minus = (move_down > move_up) & (move_down > 0)
    minus_dm[cond_minus] = move_down[cond_minus]

    # Smoothed Directional Movement (+SDM, -SDM) usando RMA
    plus_dm_smoothed = plus_dm.ewm(alpha=1/period, adjust=False, min_periods=1).mean()
    minus_dm_smoothed = minus_dm.ewm(alpha=1/period, adjust=False, min_periods=1).mean()

    # Directional Indicators (+DI, -DI)
    safe_atr = atr.replace(0, np.nan) # Usar NaN para evitar divisão por zero
    plus_di = (100.0 * (plus_dm_smoothed / safe_atr)).fillna(0.0).clip(0, 100)
    minus_di = (100.0 * (minus_dm_smoothed / safe_atr)).fillna(0.0).clip(0, 100)

    # Directional Movement Index (DX)
    di_sum = (plus_di + minus_di).replace(0, np.nan) # Usar NaN para evitar divisão por zero
    dx = (100.0 * (abs(plus_di - minus_di) / di_sum)).fillna(0.0).clip(0, 100)

    # Average Directional Index (ADX) usando RMA
    # O ADX requer 'period' valores de DX para começar a suavização de forma significativa
    adx = dx.ewm(alpha=1/period, adjust=False, min_periods=period).mean().fillna(0.0).clip(0, 100)

    return adx.rename(f"ADX_{period}"), plus_di.rename(f"PLUS_DI_{period}"), minus_di.rename(f"MINUS_DI_{period}")

# ==============================================================================
# CLASSE BASE ABSTRATA PARA ESTRATÉGIAS DE TRADING
# ==============================================================================
class TradingStrategy(ABC):
    """Classe base abstrata para todas as estratégias de trading."""
    required_klines: int = 50 # Valor padrão, cada estratégia deve definir o seu

    @abstractmethod
    def decide_action(self, symbol: str, klines_df: pd.DataFrame, is_holding: bool) -> str:
        """
        Decide a próxima ação com base nos dados de klines e estado atual.

        Args:
            symbol (str): O símbolo do par de trading (ex: 'BTCUSDT').
            klines_df (pd.DataFrame): DataFrame com os dados de klines mais recentes.
                                      Colunas esperadas: 'Open', 'High', 'Low', 'Close', 'Volume'.
            is_holding (bool): True se o bot atualmente possui a moeda base, False caso contrário.

        Returns:
            str: A ação recomendada: 'BUY', 'SELL', ou 'HOLD'.
        """
        pass

    def _prepare_dataframe(self, klines_raw: list) -> pd.DataFrame:
         """Converte a lista raw de klines em um DataFrame pandas formatado."""
         if not klines_raw: return pd.DataFrame()
         df = pd.DataFrame(klines_raw, columns=['Open time', 'Open', 'High', 'Low', 'Close', 'Volume','Close time', 'Quote asset volume', 'Number of trades','Taker buy base asset volume', 'Taker buy quote asset volume', 'Ignore'])
         cols_to_use = ['Open', 'High', 'Low', 'Close', 'Volume']
         for col in cols_to_use:
             df[col] = pd.to_numeric(df[col], errors='coerce')
         # É crucial tratar NaNs ANTES de calcular indicadores
         df.dropna(subset=['Open', 'High', 'Low', 'Close'], inplace=True) # Volume pode ser NaN às vezes? Verificar API.
         # Opcional: preencher NaNs de volume com 0 se necessário para cálculos
         # df['Volume'].fillna(0.0, inplace=True)
         return df

# ==============================================================================
# ESTRATÉGIA 1: AdvancedEmaRsiAdxStrategy
# ==============================================================================
class AdvancedEmaRsiAdxStrategy(TradingStrategy):
    """Estratégia avançada usando 3 EMAs, RSI e ADX/+DI/-DI para sinais."""
    def __init__(self, symbol: str,
                 fast_ema_period: int = 10, medium_ema_period: int = 21, slow_ema_period: int = 50,
                 rsi_period: int = 14, rsi_overbought: int = 70, rsi_oversold: int = 30,
                 adx_period: int = 14, adx_trend_threshold: int = 23):
        self.symbol = symbol
        self.fast_ema_period = fast_ema_period
        self.medium_ema_period = medium_ema_period
        self.slow_ema_period = slow_ema_period
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.adx_period = adx_period
        self.adx_trend_threshold = adx_trend_threshold

        # Estimativa segura para lookback
        max_lookback = max(fast_ema_period, medium_ema_period, slow_ema_period, rsi_period + 1, adx_period * 2 + 1)
        self.required_klines = max_lookback + 20 # Aumentar margem

        self.prev_ema_fast = None
        self.prev_ema_medium = None

        print(f"[{self.symbol}] Estratégia AdvancedEmaRsiAdxStrategy INICIALIZADA (Params: EMA({fast_ema_period},{medium_ema_period},{slow_ema_period}), RSI({rsi_period},{rsi_oversold},{rsi_overbought}), ADX({adx_period},{adx_trend_threshold}); Klines Req: {self.required_klines})")

    def decide_action(self, symbol: str, klines_df: pd.DataFrame, is_holding: bool) -> str:
        if klines_df.empty or len(klines_df) < self.required_klines:
            # print(f"DEBUG [{self.symbol}] Klines insuficientes: {len(klines_df)}/{self.required_klines}")
            return 'HOLD'

        # Calcula indicadores
        ema_fast_series = _calculate_ema_pd(klines_df['Close'], self.fast_ema_period)
        ema_medium_series = _calculate_ema_pd(klines_df['Close'], self.medium_ema_period)
        ema_slow_series = _calculate_ema_pd(klines_df['Close'], self.slow_ema_period)
        rsi_series = _calculate_rsi_pd(klines_df['Close'], self.rsi_period)
        adx_series, plus_di_series, minus_di_series = _calculate_adx_di_pd(klines_df['High'], klines_df['Low'], klines_df['Close'], self.adx_period)

        # Pega os valores atuais (último candle) e anteriores (penúltimo)
        try:
            current_ema_fast = ema_fast_series.iloc[-1]
            current_ema_medium = ema_medium_series.iloc[-1]
            current_ema_slow = ema_slow_series.iloc[-1]
            current_rsi = rsi_series.iloc[-1]
            current_adx = adx_series.iloc[-1]
            current_plus_di = plus_di_series.iloc[-1]
            current_minus_di = minus_di_series.iloc[-1]

            prev_ema_fast_val = ema_fast_series.iloc[-2]
            prev_ema_medium_val = ema_medium_series.iloc[-2]
            prev_close = klines_df['Close'].iloc[-2]
            prev_fast_ema_s = ema_fast_series.iloc[-2] # Para condição de venda 3

        except IndexError:
            # print(f"DEBUG [{self.symbol}] IndexError ao acessar indicadores/preços anteriores. Klines={len(klines_df)}")
            return 'HOLD' # Não há dados suficientes para comparar com o anterior

        # Verifica se temos valores válidos no último candle
        indicators_current = [current_ema_fast, current_ema_medium, current_ema_slow, current_rsi, current_adx, current_plus_di, current_minus_di]
        if any(pd.isna(v) for v in indicators_current):
             # print(f"DEBUG [{self.symbol}] Indicadores NaN no último candle.")
             # for i, v in enumerate(indicators_current):
             #      if pd.isna(v): print(f"DEBUG [{self.symbol}] Indicador NaN: index {i}")
             return 'HOLD'

        # Inicializa estado interno para cruzamentos (usa valor do penúltimo candle)
        if self.prev_ema_fast is None or self.prev_ema_medium is None:
            self.prev_ema_fast = prev_ema_fast_val
            self.prev_ema_medium = prev_ema_medium_val
            # print(f"DEBUG [{self.symbol}] Inicializando prev_ema com valores de kline[-2].")
            return 'HOLD' # Não toma ação na primeira vez

        # ---- Lógica de Decisão ----
        action = 'HOLD'
        buy_condition_met = False
        sell_condition_met = False
        sell_reason = ""

        # Condições booleanas
        is_uptrend_ema_alignment = current_ema_fast > current_ema_medium and current_ema_medium > current_ema_slow
        is_downtrend_ema_alignment = current_ema_fast < current_ema_medium and current_ema_medium < current_ema_slow
        is_strong_trend_adx = current_adx > self.adx_trend_threshold
        is_di_dominant_bullish = current_plus_di > current_minus_di
        is_di_dominant_bearish = current_minus_di > current_plus_di
        rsi_in_buy_zone = current_rsi < (self.rsi_overbought - 5) and current_rsi > (self.rsi_oversold + 10)

        # Cruzamentos (usando estado prévio da CLASSE vs valor atual)
        bullish_cross_now = (self.prev_ema_fast <= self.prev_ema_medium) and (current_ema_fast > current_ema_medium)
        bearish_cross_now = (self.prev_ema_fast >= self.prev_ema_medium) and (current_ema_fast < current_ema_medium)

        # --- Lógica de Compra ---
        if bullish_cross_now and (current_ema_medium > current_ema_slow) and is_strong_trend_adx and is_di_dominant_bullish and rsi_in_buy_zone:
             buy_condition_met = True
             action = 'BUY'
             # ----- LOG EXEMPLO -----
             # print(f"DEBUG [{self.symbol}] BUY Condition Met (Cross): cross={bullish_cross_now}, "
             #       f"med>slow={(current_ema_medium > current_ema_slow)}, adx>th={is_strong_trend_adx}, "
             #       f"+DI>-DI={is_di_dominant_bullish}, rsi_zone={rsi_in_buy_zone}")
             # print(f"DEBUG [{self.symbol}] Values: EMA_F={current_ema_fast:.2f}, EMA_M={current_ema_medium:.2f}, EMA_S={current_ema_slow:.2f}, "
             #       f"RSI={current_rsi:.2f}, ADX={current_adx:.2f}, +DI={current_plus_di:.2f}, -DI={current_minus_di:.2f}")
             # ----- FIM LOG EXEMPLO -----

        # --- Lógica de Venda (somente se estiver em posição) ---
        if is_holding:
            current_close = klines_df['Close'].iloc[-1] # Preço de fechamento atual
            # 1. Venda no cruzamento bearish principal, confirmado por ADX e DI
            if bearish_cross_now and is_strong_trend_adx and is_di_dominant_bearish:
                sell_condition_met = True; sell_reason = f"Cruz. EMA {self.fast_ema_period}/{self.medium_ema_period} Bearish c/ ADX/DI"
            # 2. Venda alternativa: Cruzamento bearish E preço caindo abaixo da EMA Lenta
            elif bearish_cross_now and current_ema_fast < current_ema_slow:
                 sell_condition_met = True; sell_reason = f"Cruz. EMA {self.fast_ema_period}/{self.medium_ema_period} Bearish & EMA Rápida < EMA Lenta"
            # 3. Venda por fraqueza: Preço fecha abaixo da EMA rápida + RSI fraco ou ADX fraco (alerta rápido)
            #   Verifica se o preço fechou abaixo da EMA rápida NESTA vela, mas estava acima ou igual na anterior
            elif current_close < current_ema_fast and prev_close >= prev_fast_ema_s and \
                 (current_rsi < 45 or not is_strong_trend_adx): # Condição de fraqueza
                     sell_condition_met = True; sell_reason = f"Preço < EMA{self.fast_ema_period} c/ RSI<45 ou ADX<{self.adx_trend_threshold}"
            # 4. Venda se a tendência reverter completamente (EMAs desalinhadas para baixo)
            elif is_downtrend_ema_alignment:
                 sell_condition_met = True; sell_reason = f"EMAs Alinhadas p/ Baixo ({self.fast_ema_period}<{self.medium_ema_period}<{self.slow_ema_period})"

            if sell_condition_met:
                action = 'SELL'
                # ----- LOG EXEMPLO PARA VENDA -----
                # print(f"DEBUG [{self.symbol}] SELL Condition Met: Reason='{sell_reason}'")
                # print(f"DEBUG [{self.symbol}] Values: EMA_F={current_ema_fast:.2f}, EMA_M={current_ema_medium:.2f}, EMA_S={current_ema_slow:.2f}, "
                #       f"RSI={current_rsi:.2f}, ADX={current_adx:.2f}, +DI={current_plus_di:.2f}, -DI={current_minus_di:.2f}, "
                #       f"Close={current_close:.2f}, BearCross={bearish_cross_now}")
                # ----- FIM LOG EXEMPLO -----

        # Atualiza estado interno da classe para a próxima iteração ANTES de retornar
        self.prev_ema_fast = current_ema_fast
        self.prev_ema_medium = current_ema_medium

        return action


# ==============================================================================
# ESTRATÉGIA 2: FilteredEmaCrossoverStrategy
# ==============================================================================
class FilteredEmaCrossoverStrategy(TradingStrategy):
    """Estratégia de Cruzamento de EMA (7/40 primário, 7/20 secundário) filtrada por RSI e Volume."""
    def __init__(self, symbol, fast_period=7, medium_period=20, slow_period=40,
                 rsi_period=14, rsi_overbought=70, rsi_oversold=30,
                 volume_length_short=14, volume_length_long=50, volume_threshold=1.0):
        self.symbol = symbol
        self.fast_period = fast_period; self.medium_period = medium_period; self.slow_period = slow_period
        self.rsi_period = rsi_period; self.rsi_overbought = rsi_overbought; self.rsi_oversold = rsi_oversold
        self.volume_length_short = volume_length_short; self.volume_length_long = volume_length_long
        self.volume_threshold = volume_threshold

        self.last_ema_fast = None; self.last_ema_medium = None; self.last_ema_slow = None
        self.waiting_for_secondary_buy = False

        max_p = max(fast_period, medium_period, slow_period, rsi_period + 1, volume_length_long)
        self.required_klines = max_p + 10 # Margem
        print(f"[{self.symbol}] Estratégia FilteredEmaCrossoverStrategy INICIALIZADA (Params: EMA({fast_period},{medium_period},{slow_period}), RSI({rsi_period},{rsi_overbought}), VolFilt({volume_threshold}); Klines Req: {self.required_klines})")

    def decide_action(self, symbol, klines_df, is_holding):
        if klines_df.empty or len(klines_df) < self.required_klines:
            # print(f"DEBUG [{self.symbol}] Klines insuficientes: {len(klines_df)}/{self.required_klines}")
            return 'HOLD'

        # Calcula indicadores
        ema_fast_series = _calculate_ema_pd(klines_df['Close'], self.fast_period)
        ema_medium_series = _calculate_ema_pd(klines_df['Close'], self.medium_period)
        ema_slow_series = _calculate_ema_pd(klines_df['Close'], self.slow_period)
        rsi_series = _calculate_rsi_pd(klines_df['Close'], self.rsi_period)

        # Calcula filtro de volume (SMA do Volume)
        if 'Volume' not in klines_df.columns or klines_df['Volume'].isnull().all() or len(klines_df['Volume']) < self.volume_length_long:
             # print(f"DEBUG [{self.symbol}] Volume data insufficient or missing.")
             return 'HOLD'
        volume_sma_short = klines_df['Volume'].rolling(window=self.volume_length_short, min_periods=self.volume_length_short).mean()
        volume_sma_long = klines_df['Volume'].rolling(window=self.volume_length_long, min_periods=self.volume_length_long).mean()
        # Tratar divisão por zero ou SMA longa sendo zero
        volume_sma_long_safe = volume_sma_long.replace(0, np.nan)
        volume_ratio_series = (volume_sma_short / volume_sma_long_safe).fillna(0)

        # Pega valores atuais e anteriores
        try:
            current_ema_fast = ema_fast_series.iloc[-1]
            current_ema_medium = ema_medium_series.iloc[-1]
            current_ema_slow = ema_slow_series.iloc[-1]
            current_rsi = rsi_series.iloc[-1]
            current_volume_ratio = volume_ratio_series.iloc[-1]

            prev_ema_fast_val = ema_fast_series.iloc[-2]
            prev_ema_medium_val = ema_medium_series.iloc[-2]
            prev_ema_slow_val = ema_slow_series.iloc[-2]
        except IndexError:
            # print(f"DEBUG [{self.symbol}] IndexError ao acessar indicadores anteriores (Filtered). Klines={len(klines_df)}")
            return 'HOLD'

        # Verifica NaNs nos valores atuais
        indicators_current = [current_ema_fast, current_ema_medium, current_ema_slow, current_rsi, current_volume_ratio]
        if any(pd.isna(v) for v in indicators_current):
             # print(f"DEBUG [{self.symbol}] Indicadores NaN no último candle (Filtered).")
             return 'HOLD'

        # Inicializa estado interno (com valores do penúltimo candle)
        if self.last_ema_fast is None:
            self.last_ema_fast = prev_ema_fast_val
            self.last_ema_medium = prev_ema_medium_val
            self.last_ema_slow = prev_ema_slow_val
            self.waiting_for_secondary_buy = False
            # print(f"DEBUG [{self.symbol}] Inicializando prev_ema com valores de kline[-2] (Filtered).")
            return 'HOLD'

        # ---- Lógica de Decisão ----
        action = 'HOLD'

        # Define condições booleanas
        bullish_cross_fast_slow = (self.last_ema_fast <= self.last_ema_slow) and (current_ema_fast > current_ema_slow)
        bullish_cross_fast_medium = (self.last_ema_fast <= self.last_ema_medium) and (current_ema_fast > current_ema_medium)
        bearish_cross_fast_medium = (self.last_ema_fast >= self.last_ema_medium) and (current_ema_fast < current_ema_medium)
        bearish_cross_medium_slow = (self.last_ema_medium >= self.last_ema_slow) and (current_ema_medium < current_ema_slow)

        above_slow_ema = current_ema_fast > current_ema_slow and current_ema_medium > current_ema_slow
        rsi_filter_buy_ok = current_rsi < self.rsi_overbought
        volume_filter_ok = current_volume_ratio > self.volume_threshold

        # --- Lógica de Compra ---
        buy_condition_met = False
        buy_primary_condition = bullish_cross_fast_slow and rsi_filter_buy_ok and volume_filter_ok
        buy_secondary_condition = self.waiting_for_secondary_buy and bullish_cross_fast_medium and \
                                  above_slow_ema and rsi_filter_buy_ok and volume_filter_ok

        if buy_primary_condition or buy_secondary_condition:
            buy_condition_met = True
            action = 'BUY'
            reason = "Primária (EMA{}/{} Cross)".format(self.fast_period, self.slow_period) if buy_primary_condition else "Secundária (EMA{}/{} Recross)".format(self.fast_period, self.medium_period)
            # ----- LOG EXEMPLO -----
            # print(f"DEBUG [{self.symbol}] BUY Condition Met ({reason}): primary={buy_primary_condition}, secondary={buy_secondary_condition}, waiting_flag={self.waiting_for_secondary_buy}")
            # print(f"DEBUG [{self.symbol}] Values: EMA_F={current_ema_fast:.2f}, EMA_M={current_ema_medium:.2f}, EMA_S={current_ema_slow:.2f}, RSI={current_rsi:.2f}, VolRatio={current_volume_ratio:.2f}")
            # ----- FIM LOG EXEMPLO -----

        # --- Lógica de Venda (somente se estiver em posição) ---
        if is_holding:
            if bearish_cross_medium_slow:
                action = 'SELL'
                sell_reason = "EMA{}/{} Cross Bearish".format(self.medium_period, self.slow_period)
                # ----- LOG EXEMPLO -----
                # print(f"DEBUG [{self.symbol}] SELL Condition Met: Reason='{sell_reason}', Cross={bearish_cross_medium_slow}")
                # print(f"DEBUG [{self.symbol}] Values: EMA_F={current_ema_fast:.2f}, EMA_M={current_ema_medium:.2f}, EMA_S={current_ema_slow:.2f}")
                # ----- FIM LOG EXEMPLO -----

        # --- Atualiza Estado Interno da Classe ---
        self.last_ema_fast = current_ema_fast
        self.last_ema_medium = current_ema_medium
        self.last_ema_slow = current_ema_slow

        if buy_secondary_condition: self.waiting_for_secondary_buy = False
        elif action == 'SELL': self.waiting_for_secondary_buy = False
        elif not buy_condition_met and bearish_cross_fast_medium and above_slow_ema:
            if not self.waiting_for_secondary_buy: # Ativa apenas uma vez
                 # print(f"DEBUG [{self.symbol}] Flag waiting_for_secondary_buy ATIVADA.")
                 self.waiting_for_secondary_buy = True

        return action

# ==============================================================================
# ESTRATÉGIA 3: PureEmaStrategy
# ==============================================================================
class PureEmaStrategy(TradingStrategy):
    """Estratégia puramente baseada no alinhamento de 3 EMAs."""
    def __init__(self, symbol: str, fast_period: int = 7, medium_period: int = 20, slow_period: int = 40):
        self.symbol = symbol
        self.fast_period = fast_period
        self.medium_period = medium_period
        self.slow_period = slow_period
        self.required_klines = max(fast_period, medium_period, slow_period) + 5
        print(f"[{self.symbol}] Estratégia PureEmaStrategy INICIALIZADA (Params: EMA({fast_period},{medium_period},{slow_period}); Klines Req: {self.required_klines})")

    def decide_action(self, symbol: str, klines_df: pd.DataFrame, is_holding: bool) -> str:
        if klines_df.empty or len(klines_df) < self.required_klines:
            # print(f"DEBUG [{self.symbol}] Klines insuficientes: {len(klines_df)}/{self.required_klines}")
            return 'HOLD'

        ema_fast_series = _calculate_ema_pd(klines_df['Close'], self.fast_period)
        ema_medium_series = _calculate_ema_pd(klines_df['Close'], self.medium_period)
        ema_slow_series = _calculate_ema_pd(klines_df['Close'], self.slow_period)

        try:
            current_ema_fast = ema_fast_series.iloc[-1]
            current_ema_medium = ema_medium_series.iloc[-1]
            current_ema_slow = ema_slow_series.iloc[-1]
        except IndexError:
             # print(f"DEBUG [{self.symbol}] IndexError ao acessar EMAs (Pure). Klines={len(klines_df)}")
             return 'HOLD'

        if any(pd.isna(v) for v in [current_ema_fast, current_ema_medium, current_ema_slow]):
             # print(f"DEBUG [{self.symbol}] EMAs NaN no último candle (Pure).")
             return 'HOLD'

        action = 'HOLD'
        # Condição de Compra: Alinhamento Bullish forte
        is_bullish_alignment = current_ema_fast > current_ema_medium and current_ema_medium > current_ema_slow

        if is_bullish_alignment:
            action = 'BUY'
            # ----- LOG EXEMPLO -----
            # print(f"DEBUG [{self.symbol}] BUY Condition Met (Pure): EMA Align Strong Bullish")
            # print(f"DEBUG [{self.symbol}] Values: EMA_F={current_ema_fast:.2f}, EMA_M={current_ema_medium:.2f}, EMA_S={current_ema_slow:.2f}")
            # ----- FIM LOG EXEMPLO -----

        # Condição de Venda (somente se holding): EMA rápida cruza abaixo da média OU da lenta
        if is_holding:
            is_bearish_signal = current_ema_fast < current_ema_medium or current_ema_fast < current_ema_slow
            if is_bearish_signal:
                action = 'SELL'
                sell_reason = f"EMA{self.fast_period} < EMA{self.medium_period}" if current_ema_fast < current_ema_medium else f"EMA{self.fast_period} < EMA{self.slow_period}"
                # ----- LOG EXEMPLO -----
                # print(f"DEBUG [{self.symbol}] SELL Condition Met (Pure): Reason='{sell_reason}'")
                # print(f"DEBUG [{self.symbol}] Values: EMA_F={current_ema_fast:.2f}, EMA_M={current_ema_medium:.2f}, EMA_S={current_ema_slow:.2f}")
                # ----- FIM LOG EXEMPLO -----
        return action


# ==============================================================================
# ESTRATÉGIA 4: CombinedEmaRsiVolumeStrategy
# ==============================================================================
class CombinedEmaRsiVolumeStrategy(TradingStrategy):
    """Combina Alinhamento de EMA com filtros de RSI e Volume."""
    def __init__(self, symbol: str, fast_period: int = 7, medium_period: int = 20, slow_period: int = 40,
                 rsi_period: int = 14, rsi_overbought: int = 70,
                 volume_length_short: int = 14, volume_length_long: int = 50, volume_threshold: float = 1.0):
        self.symbol = symbol
        self.fast_period = fast_period; self.medium_period = medium_period; self.slow_period = slow_period
        self.rsi_period = rsi_period; self.rsi_overbought = rsi_overbought
        self.volume_length_short = volume_length_short; self.volume_length_long = volume_length_long
        self.volume_threshold = volume_threshold

        max_lookback_period = max(fast_period, medium_period, slow_period, rsi_period + 1, volume_length_long)
        self.required_klines = max_lookback_period + 10 # Margem
        print(f"[{self.symbol}] Estratégia CombinedEmaRsiVolumeStrategy INICIALIZADA (Params: EMA({fast_period},{medium_period},{slow_period}), RSI({rsi_period},{rsi_overbought}), VolFilt({volume_threshold}); Klines Req: {self.required_klines})")

    def decide_action(self, symbol: str, klines_df: pd.DataFrame, is_holding: bool) -> str:
        if klines_df.empty or len(klines_df) < self.required_klines:
             # print(f"DEBUG [{self.symbol}] Klines insuficientes: {len(klines_df)}/{self.required_klines}")
             return 'HOLD'

        # Cálculos
        ema_fast_series = _calculate_ema_pd(klines_df['Close'], self.fast_period)
        ema_medium_series = _calculate_ema_pd(klines_df['Close'], self.medium_period)
        ema_slow_series = _calculate_ema_pd(klines_df['Close'], self.slow_period)
        rsi_series = _calculate_rsi_pd(klines_df['Close'], self.rsi_period)

        if 'Volume' not in klines_df.columns or klines_df['Volume'].isnull().all() or len(klines_df['Volume']) < self.volume_length_long: return 'HOLD'
        volume_sma_short = klines_df['Volume'].rolling(window=self.volume_length_short, min_periods=self.volume_length_short).mean()
        volume_sma_long = klines_df['Volume'].rolling(window=self.volume_length_long, min_periods=self.volume_length_long).mean()
        volume_sma_long_safe = volume_sma_long.replace(0, np.nan)
        volume_ratio_series = (volume_sma_short / volume_sma_long_safe).fillna(0)

        # Valores atuais
        try:
             current_ema_fast = ema_fast_series.iloc[-1]
             current_ema_medium = ema_medium_series.iloc[-1]
             current_ema_slow = ema_slow_series.iloc[-1]
             current_rsi = rsi_series.iloc[-1]
             current_volume_ratio = volume_ratio_series.iloc[-1]
        except IndexError:
              # print(f"DEBUG [{self.symbol}] IndexError ao acessar indicadores (Combined). Klines={len(klines_df)}")
              return 'HOLD'

        # Verifica NaNs
        if any(pd.isna(v) for v in [current_ema_fast, current_ema_medium, current_ema_slow, current_rsi, current_volume_ratio]):
             # print(f"DEBUG [{self.symbol}] Indicadores NaN no último candle (Combined).")
             return 'HOLD'

        action = 'HOLD'

        # Condições de Compra
        ema_buy_condition = current_ema_fast > current_ema_medium and current_ema_medium > current_ema_slow
        rsi_buy_filter_passed = current_rsi < self.rsi_overbought
        volume_buy_filter_passed = current_volume_ratio > self.volume_threshold

        if ema_buy_condition and rsi_buy_filter_passed and volume_buy_filter_passed:
            action = 'BUY'
            # ----- LOG EXEMPLO -----
            # print(f"DEBUG [{self.symbol}] BUY Condition Met (Combined): EMA Align={ema_buy_condition}, RSI OK={rsi_buy_filter_passed}, Vol OK={volume_buy_filter_passed}")
            # print(f"DEBUG [{self.symbol}] Values: EMA_F={current_ema_fast:.2f}, EMA_M={current_ema_medium:.2f}, EMA_S={current_ema_slow:.2f}, RSI={current_rsi:.2f}, VolRatio={current_volume_ratio:.2f}")
            # ----- FIM LOG EXEMPLO -----

        # Condições de Venda (igual PureEma)
        if is_holding:
            is_bearish_signal = current_ema_fast < current_ema_medium or current_ema_fast < current_ema_slow
            if is_bearish_signal:
                action = 'SELL'
                sell_reason = f"EMA{self.fast_period} < EMA{self.medium_period}" if current_ema_fast < current_ema_medium else f"EMA{self.fast_period} < EMA{self.slow_period}"
                # ----- LOG EXEMPLO -----
                # print(f"DEBUG [{self.symbol}] SELL Condition Met (Combined): Reason='{sell_reason}'")
                # print(f"DEBUG [{self.symbol}] Values: EMA_F={current_ema_fast:.2f}, EMA_M={current_ema_medium:.2f}, EMA_S={current_ema_slow:.2f}")
                # ----- FIM LOG EXEMPLO -----

        return action

# (Manter as classes EmaThreeLines* apenas se realmente for usá-las e adaptá-las para receber DataFrame)

# Fim do arquivo strategies.py
