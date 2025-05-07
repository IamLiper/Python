# strategies.py
import math
from abc import ABC, abstractmethod
import pandas as pd # Mantém pandas para DataFrames e cálculos rolling/ewm
# Remove import pandas_ta as ta

# Classe base abstrata para estratégias de trading
class TradingStrategy(ABC):
    """Classe base abstrata para estratégias de trading."""

    @abstractmethod
    # Assinatura modificada para refletir que aceita klines brutos e holding state
    def decide_action(self, symbol, klines_raw, is_holding):
        """
        Determina a ação de trading ('BUY', 'SELL', 'HOLD') com base nos dados do gráfico
        e estado interno/externo (holding).

        Args:
            symbol (str): O par de trading (ex: 'BTCUSDT').
            klines_raw (list): Lista de dados de klines brutos da Binance.
            is_holding (bool): Indica se o bot está virtualmente segurando uma posição neste par.

        Returns:
            str: 'BUY', 'SELL', ou 'HOLD'.
                 'BUY' -> Intenção de ir Long (entrar ou sair Short).
                 'SELL' -> Intenção de ir Short (entrar ou sair Long).
                 'HOLD' -> Não fazer nada.
        """
        pass

    # Mantemos uma versão simples da EMA caso alguma estratégia a use diretamente,
    # mas a nova estratégia filtrada usará pandas ewm.
    def _calculate_ema(self, prices, period):
        """Calcula a Média Móvel Exponencial (EMA) para um período."""
        if period <= 0 or len(prices) < period:
            return None

        alpha = 2 / (period + 1)
        # Calcula a primeira EMA (usando SMA dos primeiros 'period' preços)
        # Precisa de 'period' preços para a SMA inicial
        if len(prices) < period:
             return None # Dados insuficientes para a SMA inicial

        ema = sum(prices[:period]) / period

        # Calcula os EMAs subsequentes
        for price in prices[period:]:
            ema = (price * alpha) + (ema * (1 - alpha))

        return ema


# Sua estratégia original baseada apenas em 3 EMAs (mantida)
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

        self.required_klines = max(self.fast_period, self.medium_period, self.slow_period) + 1 # +1 para pegar a barra atual


    def decide_action(self, symbol, klines_raw, is_holding): # Implementa o método abstrato
         # Extrair preços de fechamento (necessário apenas para esta estratégia simples)
         klines = [float(k[4]) for k in klines_raw]

         if not klines or len(klines) < self.required_klines:
             # print(f"[{symbol}] Dados insuficientes ({len(klines)}/{self.required_klines}) para a estratégia 3-EMA simples.")
             return 'HOLD'


         # Calcula as EMAs mais recentes
         current_fast_ema = self._calculate_ema(klines, self.fast_period)
         current_medium_ema = self._calculate_ema(klines, self.medium_period)
         current_slow_ema = self._calculate_ema(klines, self.slow_period)

         if current_fast_ema is None or current_medium_ema is None or current_slow_ema is None:
              print(f"[{symbol}] Erro ao calcular EMAs simples na estratégia. Dados Klines: {len(klines)}")
              return 'HOLD'

         # --- Lógica para detectar cruzamentos (requer valores anteriores) ---
         if self.last_fast_ema is None or self.last_medium_ema is None or self.last_slow_ema is None:
              # Primeira execução com dados suficientes: apenas armazena os valores atuais
              print(f"[{symbol}] Inicializando valores de EMAs anteriores na estratégia simples. Aguardando próximo ciclo.")
              self.last_fast_ema = current_fast_ema
              self.last_medium_ema = current_medium_ema
              self.last_slow_ema = current_slow_ema
              return 'HOLD'


         # === Regras de Decisão ===
         action = 'HOLD'

         # Cruzamentos (comparando 'current_' da barra atual com 'last_' da barra anterior)
         has_crossed_below_slow = current_fast_ema < current_slow_ema and self.last_fast_ema >= self.last_slow_ema
         has_crossed_above_medium = current_fast_ema > current_medium_ema and self.last_fast_ema <= self.last_medium_ema
         has_crossed_below_medium = current_fast_ema < current_medium_ema and self.last_fast_ema >= self.last_medium_ema

         # Zonas
         is_in_potential_uptrend_zone = current_fast_ema >= current_slow_ema
         is_trading_zone_active = current_fast_ema > current_slow_ema and current_medium_ema > current_slow_ema # 7 e 20 acima da 40


         # 1. Sinal de VENDA (Saída de Long ou Entrada Short - Bot decide com base em 'is_holding')
         if has_crossed_below_slow:
              # Venda de Emergência/Reversão de Tendência Principal (7 abaixo da 40)
              # print(f"[{symbol}] 🔽 SINAL (Simples): EMA{self.fast_period} cruzou ABAIXO da EMA{self.slow_period}.")
              action = 'SELL'
         elif is_trading_zone_active and has_crossed_below_medium:
              # Venda Antecipada (7 abaixo da 20) dentro da zona de alta (acima da 40)
              # print(f"[{symbol}] 🔽 SINAL (Simples): EMA{self.fast_period} cruzou ABAIXO da EMA{self.medium_period} (acima da EMA{self.slow_period}).")
              action = 'SELL'

         # 2. Sinal de COMPRA (Saída de Short ou Entrada Long - Bot decide com base em 'is_holding')
         # Só checa compra se não decidiu vender AGORA
         if action == 'HOLD' and is_trading_zone_active and has_crossed_above_medium:
              # Compra (7 acima da 20) dentro da zona de alta (acima da 40)
              # print(f"[{symbol}] 🔼 SINAL (Simples): EMA{self.fast_period} cruzou ACIMA da EMA{self.medium_period} (acima da EMA{self.slow_period}).")
              action = 'BUY'


         # --- Atualiza os valores das EMAs anteriores para a próxima iteração ---
         self.last_fast_ema = current_fast_ema
         self.last_medium_ema = current_medium_ema
         self.last_slow_ema = current_slow_ema


         # Retorna apenas a ação decidida ('BUY', 'SELL', ou 'HOLD')
         return action

# As estratégias específicas para ETH e SOL podem herdar da base ou da nova estratégia filtrada
# dependendo se você quer que elas tenham os filtros ou não, ou se terão parâmetros/lógica diferentes.
# Mantidas como herança da simples original.
class EmaThreeLinesCrossoverStrategyETH(EmaThreeLinesCrossoverStrategy):
    """Estratégia 3-EMA simples para ETHUSDT."""
    def __init__(self, symbol, fast_period=10, medium_period=25, slow_period=50):
         super().__init__(symbol, fast_period, medium_period, slow_period)

class EmaThreeLinesCrossoverStrategySOL(EmaThreeLinesCrossoverStrategy):
    """Estratégia 3-EMA simples para SOLUSDT."""
    def __init__(self, symbol, fast_period=5, medium_period=15, slow_period=30):
         super().__init__(symbol, fast_period, medium_period, slow_period)


# --- NOVA ESTRATÉGIA: Baseada na Lógica Filtrada do Pine Script (Sem pandas_ta) ---
class FilteredEmaCrossoverStrategy(TradingStrategy):
    """Estratégia baseada no Pine Script: 3 EMAs + ADX + RSI + Volume Filter (Calculado via Pandas)."""

    def __init__(self, symbol, fast_period=7, medium_period=20, slow_period=40,
                 adx_period=14, adx_threshold=20,
                 rsi_period=14, rsi_overbought=70, rsi_oversold=30,
                 volume_length_short=14, volume_length_long=50, volume_threshold=1.0,
                 atr_period=14): # Incluído ATR period, embora não usado para SL/TP no bot

        self.symbol = symbol
        self.fast_period = fast_period
        self.medium_period = medium_period
        self.slow_period = slow_period
        self.adx_period = adx_period
        self.adx_threshold = adx_threshold
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.volume_length_short = volume_length_short
        self.volume_length_long = volume_length_long
        self.volume_threshold = volume_threshold
        self.atr_period = atr_period # Armazenado, mas não usado na lógica de sinal BUY/SELL aqui

        # Variáveis de estado para detectar cruzamentos e manter estados como no Pine Script
        self.last_ema7 = None
        self.last_ema20 = None
        self.last_ema40 = None
        self.last_adx = None
        self.last_rsi = None
        self.last_volume_ratio = None
        self.last_bearish_price_confirmation = False # Estado do filtro de preço na barra anterior

        # Estados "waiting" da lógica Pine Script (persistem entre as chamadas decide_action)
        self.waitingForSecondaryBuy = False
        # self.waitingForBuyAfterSell # Omitido por enquanto, pois depende do estado de trade do bot


        # O número mínimo de klines necessários para TODOS os indicadores calcularem pelo menos 1 valor válido na última barra
        # O cálculo manual pode exigir um pouco mais de dados iniciais para "aquecer" as médias
        # Max dos períodos de todos os indicadores + um buffer para garantir dados suficientes
        max_period = max(fast_period, medium_period, slow_period, adx_period, rsi_period, volume_length_short, volume_length_long, atr_period)
        self.required_klines = max_period + 25 # Buffer aumentado para ADX e RSI manuais

    # --- Métodos para Calcular Indicadores Manuais (Adaptado do Pine Script) ---
    # Usa funcionalidades do Pandas onde possível

    def _calculate_ema_pd(self, series, period):
        """Calcula EMA usando pandas ewm."""
        if period <= 0 or len(series) < period:
            return pd.Series([None] * len(series)) # Retorna série de None se dados insuficientes
        # pandas ewm min_periods=0 usa o preço atual para a primeira barra se não houver períodos suficientes,
        # min_periods=period espera a SMA inicial. Usamos min_periods=period para replicar o cálculo usual de EMA.
        return series.ewm(span=period, adjust=False, min_periods=period).mean()


    def _calculate_rsi_pd(self, closes, period):
        """Calcula RSI usando pandas."""
        if period <= 0 or len(closes) < period:
            return pd.Series([None] * len(closes))

        delta = closes.diff()
        # Calcula ganhos e perdas
        gains = delta.mask(delta < 0, 0)
        losses = delta.mask(delta > 0, 0).abs()

        # Calcula a média exponencial (RMA like) de ganhos e perdas
        # pandas ewm adjust=False e min_periods=period replica o comportamento da RMA do TradingView na primeira barra
        avg_gains = gains.ewm(span=period, adjust=False, min_periods=period).mean()
        avg_losses = losses.ewm(span=period, adjust=False, min_periods=period).mean()

        # Calcula Relative Strength (RS)
        # Evita divisão por zero
        rs = avg_gains / avg_losses.replace(0, pd.NA) # Usa pd.NA para resultado em NaN onde avg_losses é 0

        # Calcula RSI
        rsi = 100 - (100 / (1 + rs))

        # O RSI na primeira barra calculável é baseado na SMA, não na EWM/RMA.
        # Para replicar TradingView/Pine Script de perto, precisaríamos do primeiro avg_gains/losses como SMA.
        # Para simplicidade inicial, usaremos EWM desde o início, que é comum em muitas libs.
        # O importante é que a lógica de cruzamento/threshold use os valores consistentes.
        # Retorna a série completa, a lógica decide_action pegará o último valor.
        return rsi


    def _calculate_adx_pd(self, high, low, close, period):
        """Calcula ADX usando pandas (adaptado da lógica manual do Pine Script)."""
        if period <= 0 or len(high) < period or len(low) < period or len(close) < period:
             return pd.Series([None] * len(high)) # Retorna série de None se dados insuficientes

        # Calcula movimentos direcionais
        up = high.diff()
        down = low.diff() * -1 # low[1] - low se torna low.diff() * -1

        # Calcula +DM e -DM
        plusDM = pd.Series(0.0, index=high.index)
        minusDM = pd.Series(0.0, index=high.index)

        # Quando up > down E up > 0, +DM = up
        plusDM[(up > down) & (up > 0)] = up[(up > down) & (up > 0)]
        # Quando down > up E down > 0, -DM = down
        minusDM[(down > up) & (down > 0)] = down[(down > up) & (down > 0)]


        # Calcula True Range (TR)
        tr = pd.concat([high - low, abs(high - close.shift(1)), abs(low - close.shift(1))], axis=1).max(axis=1)

        # Calcula +DI e -DI suavizados com RMA (usando pandas ewm)
        # Equivalente ao ta.rma no Pine Script com adjust=False
        plusDI = 100 * plusDM.ewm(span=period, adjust=False, min_periods=period).mean() / tr.ewm(span=period, adjust=False, min_periods=period).mean().replace(0, pd.NA)
        minusDI = 100 * minusDM.ewm(span=period, adjust=False, min_periods=period).mean() / tr.ewm(span=period, adjust=False, min_periods=period).mean().replace(0, pd.NA)

        # Calcula DX
        sumDI = plusDI + minusDI
        dx = 100 * (abs(plusDI - minusDI) / sumDI.replace(0, pd.NA))
        # Substitui NaN onde sumDI era 0
        dx = dx.replace([float('inf'), float('-inf')], pd.NA) # Garante que +/- Inf de divisão por zero também se tornam NA

        # Calcula ADX (RMA do DX)
        adx = dx.ewm(span=period, adjust=False, min_periods=period).mean()

        return adx


    def decide_action(self, symbol, klines_raw, is_holding): # Implementa o método abstrato
        """
        Determina a ação com base na lógica da estratégia Pine Script filtrada (calculado via Pandas).
        """
        # Converte klines brutos para DataFrame do pandas
        if not klines_raw or len(klines_raw) < self.required_klines:
            # print(f"[{symbol}] Dados insuficientes ({len(klines_raw)}/{self.required_klines}) para a estratégia filtrada.")
            return 'HOLD'

        df = pd.DataFrame(klines_raw, columns=[
            'Open time', 'Open', 'High', 'Low', 'Close', 'Volume',
            'Close time', 'Quote asset volume', 'Number of trades',
            'Taker buy base asset volume', 'Taker buy quote asset volume', 'Ignore'
        ])
        # Converte colunas relevantes para numérico
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
             # errors='coerce' transforma valores não numéricos em NaN
             df[col] = pd.to_numeric(df[col], errors='coerce')
        # Converte colunas de preço para float (essencial para cálculos)
        df['Close'] = df['Close'].astype(float)
        df['High'] = df['High'].astype(float)
        df['Low'] = df['Low'].astype(float)
        df['Volume'] = df['Volume'].astype(float)


        # Remove linhas com dados incompletos após conversão (improvável com get_klines, mas seguro)
        # Usamos a coluna 'Close' para verificar, mas High/Low/Volume também deveriam ser válidos.
        df.dropna(subset=['Close'], inplace=True)

        # Re-verifica se ainda temos dados suficientes após a limpeza
        if len(df) < self.required_klines:
             # print(f"[{symbol}] Dados insuficientes após limpeza ({len(df)}/{self.required_klines}) para a estratégia filtrada.")
             return 'HOLD'

        # --- Calcula Indicadores usando Pandas/Implementação Manual ---

        # EMAs usando pandas ewm
        ema7 = self._calculate_ema_pd(df['Close'], self.fast_period)
        ema20 = self._calculate_ema_pd(df['Close'], self.medium_period)
        ema40 = self._calculate_ema_pd(df['Close'], self.slow_period)

        # ADX usando implementação manual adaptada do Pine Script
        adx = self._calculate_adx_pd(df['High'], df['Low'], df['Close'], self.adx_period)

        # RSI usando implementação manual/pandas
        rsi = self._calculate_rsi_pd(df['Close'], self.rsi_period)

        # Volume SMAs manualmente
        volume_sma_short = df['Volume'].rolling(window=self.volume_length_short, min_periods=1).mean() # min_periods para ter valor nas primeiras barras
        volume_sma_long = df['Volume'].rolling(window=self.volume_length_long, min_periods=1).mean() # min_periods para ter valor nas primeiras barras
        # Evita divisão por zero no Volume Ratio
        volume_ratio = volume_sma_short / volume_sma_long.replace(0, pd.NA) # Use pd.NA para evitar Inf/NaN


        # --- Obtém os valores mais recentes dos indicadores ---
        # Estes representam a última barra COMPLETA
        last_row_index = df.index[-1]

        # Verifica se os indicadores necessários têm valores válidos na última barra
        # Indicadores calculados com min_periods terão NaN nas primeiras barras se não houver dados suficientes para o período
        # Precisamos que o required_klines seja grande o suficiente para que estes valores não sejam NaN na última barra
        indicators_needed = [ema7, ema20, ema40, adx, rsi, volume_ratio]
        # Verifica se o último valor de CADA série calculada NÃO é NaN
        if any(pd.isna(series.iloc[-1]) for series in indicators_needed):
             # Isso pode acontecer se o required_klines ainda for muito baixo para TODOS os indicadores terem warmup
             # print(f"[{symbol}] Valores de indicadores NaN na última barra. Dados Klines: {len(df)}. Requer ~{self.required_klines}. Pulando.")
             return 'HOLD' # Não decide sem indicadores válidos na última barra

        current_ema7 = ema7.iloc[-1]
        current_ema20 = ema20.iloc[-1]
        current_ema40 = ema40.iloc[-1]
        current_adx = adx.iloc[-1]
        current_rsi = rsi.iloc[-1]
        current_volume_ratio = volume_ratio.iloc[-1]

        # Confirmação de preço bearish (fechamento decrescente por 3 barras)
        current_bearish_price_confirmation = False
        if len(df) >= 3:
             current_bearish_price_confirmation = df['Close'].iloc[-1] < df['Close'].iloc[-2] and df['Close'].iloc[-2] < df['Close'].iloc[-3]


        # --- Inicializa valores 'last_' na primeira execução com dados suficientes ---
        if self.last_ema7 is None:
             print(f"[{symbol}] Inicializando valores 'last_' na estratégia filtrada. Aguardando próximo ciclo.")
             # Armazena os valores 'current_' desta primeira barra válida como 'last_' para a próxima execução
             self.last_ema7 = current_ema7
             self.last_ema20 = current_ema20
             self.last_ema40 = current_ema40
             self.last_adx = current_adx
             self.last_rsi = current_rsi
             self.last_volume_ratio = current_volume_ratio
             self.last_bearish_price_confirmation = current_bearish_price_confirmation
             self.waitingForSecondaryBuy = False # Inicializa o estado
             # self.waitingForBuyAfterSell = False # Inicializa o estado (se usado)
             return 'HOLD'


        # --- Obtém os valores 'last_' armazenados da execução ANTERIOR ---
        last_ema7 = self.last_ema7
        last_ema20 = self.last_ema20
        last_ema40 = self.last_ema40
        last_adx = self.last_adx
        last_rsi = self.last_rsi
        last_volume_ratio = self.last_volume_ratio
        last_bearish_price_confirmation = self.last_bearish_price_confirmation


        # --- Traduz as Condições do Pine Script ---

        # Cruzamentos (comparando 'current_' da barra atual com 'last_' da barra anterior)
        bullishCross7_40 = current_ema7 > current_ema40 and last_ema7 <= last_ema40
        bearishCross7_20 = current_ema7 < current_ema20 and last_ema7 >= last_ema20
        bullishCross7_20 = current_ema7 > current_ema20 and last_ema7 <= last_ema20
        bearishCross20_40 = current_ema20 < current_ema40 and last_ema20 >= last_ema40
        bearishCross7_40 = current_ema7 < current_ema40 and last_ema7 >= last_ema40

        # Filtros (baseados nos valores 'current_' da barra atual)
        aboveEma40 = current_ema7 > current_ema40 and current_ema20 > current_ema40
        rsiFilterBuy = current_rsi < self.rsi_overbought
        rsiFilterShort = current_rsi > self.rsi_oversold # Usando input_rsiOversold
        volumeFilter = current_volume_ratio > self.volume_threshold

        # --- Condições de Compra (Traduzidas do Pine Script) ---

        # Condição de Compra Primária
        buyPrimaryCondition = bullishCross7_40 and current_adx > self.adx_threshold and rsiFilterBuy and volumeFilter
        if buyPrimaryCondition: print(f"[{symbol}] Condição: Compra Primária True")

        # Lógica para a Condição de Compra Secundária (Gerenciando o estado 'waiting')
        # Check the 'waitingForSecondaryBuy' state from the *start* of this decide_action call (its value from the previous candle)
        waitingForSecondaryBuy_last_candle = self.waitingForSecondaryBuy

        # Calculate buySecondaryCondition based on state from last candle and conditions THIS candle
        buySecondaryCondition_this_candle = waitingForSecondaryBuy_last_candle and bullishCross7_20 and aboveEma40 and current_adx > self.adx_threshold and rsiFilterBuy and volumeFilter
        if buySecondaryCondition_this_candle: print(f"[{symbol}] Condição: Compra Secundária True")

        # Condição de Compra Após Venda (Omitida por enquanto na estratégia Python)
        # buyAfterSellCondition = ... # Requer informação do bot principal se uma posição acabou de ser fechada.
        # if buyAfterSellCondition: print(f"[{symbol}] Condição: Compra Após Venda True")


        # Condição Final de Compra (Combina as condições que são implementadas aqui)
        # is_holding é passado para decidir se um sinal BUY significa entrada ou saída de short
        buySignal = buyPrimaryCondition or buySecondaryCondition_this_candle # Omitido buyAfterSellCondition


        # --- Condições de Venda/Saída (Traduzidas do Pine Script) ---

        # Sinal de Venda (Saída de Long baseada em EMA 20 < 40)
        sellLongSignal = bearishCross20_40
        if sellLongSignal: print(f"[{symbol}] Condição: Saída Long (EMA 20<40) True")


        # Sinal de Venda Curta (Entrada Short)
        sellShortSignal = bearishCross7_40 and current_adx > self.adx_threshold and rsiFilterShort and volumeFilter and current_bearish_price_confirmation
        if sellShortSignal: print(f"[{symbol}] Condição: Entrada Short True")

        # --- Determina a Ação Final ('BUY', 'SELL', 'HOLD') ---
        # Baseado nos sinais, mas o bot principal usará 'is_holding' para decidir se é entrada ou saída.
        # A estratégia retorna a INTENÇÃO: 'BUY' para ir Long, 'SELL' para ir Short/sair Long.

        action = 'HOLD' # Ação padrão

        # Prioriza Saída de Long se houver sinal
        if sellLongSignal:
             action = 'SELL' # Indica intenção de sair de Long (bot executará venda se estiver holding)

        # Prioriza Entrada Short sobre Compra se ambos ocorrerem (seguindo a ordem no Pine Script original de entry)
        # Se o sinal for para Short E não decidiu sair de Long AGORA:
        elif sellShortSignal:
             action = 'SELL' # Indica intenção de ir Short (bot executará venda se não estiver holding, ou saída de Long se estiver segurando - isso precisa ser claro no bot)
             # Nota: No bot atual (sem shorting), 'SELL' enquanto not holding é ignorado.


        # Sinal de Compra (Potencial Entrada Long ou Saída Short)
        # Só sinaliza BUY se NÃO sinalizou SELL (Long Exit ou Short Entry)
        if action == 'HOLD' and buySignal:
             action = 'BUY' # Indica intenção de ir Long (bot executará compra se não estiver holding, ou saída de short se estiver segurando - bot atual não faz short)


        # Se action ainda é HOLD, significa que nenhuma das condições de BUY/SELL foi atendida NESTA barra.
        # O bot manterá a posição atual (se houver) ou permanecerá fora.


        # --- Atualiza Variáveis de Estado PERSISTENTES para a PRÓXIMA execução ---

        # Atualiza os valores 'last_' com os valores 'current_' desta barra completa
        self.last_ema7 = current_ema7
        self.last_ema20 = current_ema20
        self.last_ema40 = current_ema40
        self.last_adx = current_adx
        self.last_rsi = current_rsi
        self.last_volume_ratio = current_volume_ratio
        self.last_bearish_price_confirmation = current_bearish_price_confirmation

        # Atualiza o estado 'waitingForSecondaryBuy' para a PRÓXIMA barra (seguindo a lógica Pine Script)
        # Se a condição de compra secundária foi atendida NESTA barra, reseta o waiting para False na próxima.
        if buySecondaryCondition_this_candle: # Se a condição secundária foi true NESTA barra
             self.waitingForSecondaryBuy = False # O waiting reseta
        # Senão, se o TRIGGER para esperar a secundária ocorreu NESTA barra E o waiting NÃO FOI resetado NESTA barra:
        elif bearishCross7_20 and aboveEma40 and not buySecondaryCondition_this_candle:
             self.waitingForSecondaryBuy = True
        # Senão, mantém o valor que já tinha (do início desta função).


        # print(f"[{symbol}] Decisão: {action}")
        return action


# As estratégias específicas para ETH e SOL podem herdar da base ou da nova estratégia filtrada
# dependendo se você quer que elas tenham os filtros ou não, ou se terão parâmetros/lógica diferentes.
# Mantidas como herança da simples original. Se quiser que usem a nova, mude a herança.
class EmaThreeLinesCrossoverStrategyETH(EmaThreeLinesCrossoverStrategy):
    """Estratégia 3-EMA simples para ETHUSDT."""
    def __init__(self, symbol, fast_period=10, medium_period=25, slow_period=50):
         super().__init__(symbol, fast_period, medium_period, slow_period)

class EmaThreeLinesCrossoverStrategySOL(EmaThreeLinesCrossoverStrategy):
    """Estratégia 3-EMA simples para SOLUSDT."""
    def __init__(self, symbol, fast_period=5, medium_period=15, slow_period=30):
         super().__init__(symbol, fast_period, medium_period, slow_period)