# strategies.py
import math
from abc import ABC, abstractmethod

# A classe TradingStrategy permanece a mesma (base abstrata)
class TradingStrategy(ABC):
    """Classe base abstrata para estratégias de trading."""

    @abstractmethod
    def decide_action(self, symbol, klines, is_holding):
        """
        Determina a ação de trading ('BUY', 'SELL', 'HOLD') com base SOMENTE nos dados do gráfico
        e estado interno da estratégia.
        O bot principal gerencia saldos, alocações e a frequência de checagem.

        Args:
            symbol (str): O par de trading (ex: 'BTCUSDT').
            klines (list): Lista de dados de klines brutos [ [ts, open, high, low, close, volume, ...], ... ]
                           A estratégia deve extrair as informações que precisa (close, high, low, volume).
            is_holding (bool): Indica se o bot (virtualmente) está segurando uma posição neste par.

        Returns:
            str: 'BUY', 'SELL', ou 'HOLD'.
        """
        pass

    def _calculate_ema(self, prices, period):
        """Calcula a Média Móvel Exponencial (EMA) para um período."""
        if period <= 0:
            return None
        if len(prices) < period:
            return None # Não há dados suficientes para a SMA inicial

        alpha = 2 / (period + 1)

        # Calcula a primeira EMA (usando SMA dos primeiros 'period' preços)
        # Certifica-se de usar os preços dos últimos 'period' klines para a SMA inicial correta
        initial_prices = prices[-period:]
        ema = sum(initial_prices) / period

        # Calcula os EMAs subsequentes (não há, já calculamos no último ponto)
        # O loop abaixo é apenas para calcular o EMA DO ÚLTIMO ponto
        # if len(prices) > period:
        #     # Calcula EMA para o último ponto usando o penúltimo EMA calculado
        #     # (Este método requer EMAs anteriores, o que não é o caso aqui)
        #     # Para calcular o EMA do último ponto, precisamos do EMA do ponto anterior.
        #     # Uma forma mais simples e self-contained é calcular a série de EMAs
        #     # e pegar o último valor.

        # Re-implementando para calcular a série de EMAs e pegar o último
        emas = []
        # Calcula a primeira EMA (SMA)
        if len(prices) >= period:
             sma = sum(prices[:period]) / period
             emas.append(sma)
             # Calcula EMAs subsequentes
             for price in prices[period:]:
                 ema = (price * alpha) + (emas[-1] * (1 - alpha))
                 emas.append(ema)
        # Retorna o último EMA calculado (correspondente ao último preço)
        return emas[-1] if emas else None

    def _calculate_rsi(self, prices, period):
        """Calcula o Índice de Força Relativa (RSI) para um período."""
        if period <= 1:
            return None
        if len(prices) < period + 1: # Precisa de pelo menos period+1 preços para um período de mudanças
            return None

        gains = []
        losses = []
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))

        if len(gains) < period: # Ainda precisa de 'period' ganhos/perdas para a primeira média
             return None

        # Calcula a primeira média de ganho e perda (SMA) sobre os primeiros 'period' períodos de mudança
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        # Calcula a primeira RS
        rs = avg_gain / avg_loss if avg_loss != 0 else (float('inf') if avg_gain > 0 else 0)

        # Calcula o primeiro RSI
        rsi = 100 - (100 / (1 + rs)) if rs != float('inf') else 100

        # Calcula as médias e RSI para os períodos subsequentes (usando EMA)
        # Pega os ganhos/perdas dos períodos APÓS o primeiro cálculo (indexando a partir de 'period')
        for i in range(period, len(gains)):
            current_gain = gains[i]
            current_loss = losses[i]

            # Calcula a média exponencial
            avg_gain = ((avg_gain * (period - 1)) + current_gain) / period
            avg_loss = ((avg_loss * (period - 1)) + current_loss) / period

            rs = avg_gain / avg_loss if avg_loss != 0 else (float('inf') if avg_gain > 0 else 0)
            rsi = 100 - (100 / (1 + rs)) if rs != float('inf') else 100

        # Retorna o último RSI calculado
        return rsi

    def _calculate_tr(self, klines_data):
        """Calcula o True Range (TR) para cada barra nos dados klines."""
        # klines_data é a lista de listas [ [ts, open, high, low, close, volume, ...], ... ]
        high_prices = [float(k[2]) for k in klines_data]
        low_prices = [float(k[3]) for k in klines_data]
        close_prices = [float(k[4]) for k in klines_data]

        trs = []
        for i in range(1, len(klines_data)):
            # TR = max(High - Low, abs(High - Previous Close), abs(Low - Previous Close))
            tr = max(high_prices[i] - low_prices[i],
                     abs(high_prices[i] - close_prices[i-1]),
                     abs(low_prices[i] - close_prices[i-1]))
            trs.append(tr)
        return trs


    def _calculate_dm(self, klines_data):
        """Calcula Directional Movement (+DM and -DM)."""
        high_prices = [float(k[2]) for k in klines_data]
        low_prices = [float(k[3]) for k in klines_data]

        plus_dms = []
        minus_dms = []

        # O primeiro DM é 0
        plus_dms.append(0)
        minus_dms.append(0)

        for i in range(1, len(klines_data)):
            move_up = high_prices[i] - high_prices[i-1]
            move_down = low_prices[i-1] - low_prices[i]

            plus_dm = 0
            minus_dm = 0

            if move_up > move_down and move_up > 0:
                plus_dm = move_up
            elif move_down > move_up and move_down > 0:
                minus_dm = move_down

            plus_dms.append(plus_dm)
            minus_dms.append(minus_dm)

        return plus_dms, minus_dms

    def _calculate_smoothed_average(self, data, period):
        """Calcula uma média suavizada (como a Wilder's Smoothing) para ADX/ATR."""
        # A primeira média é uma SMA
        if len(data) < period:
            return None

        smoothed_avg = sum(data[:period]) / period
        smoothed_values = [smoothed_avg]

        for i in range(period, len(data)):
            smoothed_avg = ((smoothed_avg * (period - 1)) + data[i]) / period
            smoothed_values.append(smoothed_avg)

        # Retorna a série suavizada, o último valor corresponde ao último ponto dos dados originais
        return smoothed_values


    def _calculate_adx(self, klines_data, period):
        """Calcula o Average Directional Index (ADX)."""
        # Requer pelo menos period + period para os cálculos suavizados
        if len(klines_data) < period * 2 + 1: # Aproximadamente o mínimo necessário
            return None

        # 1. Calcular True Range (TR)
        # TRs são calculados para len(klines_data)-1 períodos (a partir do 2º kline)
        trs = self._calculate_tr(klines_data)

        # 2. Calcular +DM e -DM
        # +DMs e -DMs são calculados para len(klines_data) períodos (o primeiro é 0)
        plus_dms_raw, minus_dms_raw = self._calculate_dm(klines_data)

        # Precisamos apenas dos DMs a partir do 2º kline para corresponder aos TRs
        plus_dms = plus_dms_raw[1:]
        minus_dms = minus_dms_raw[1:]

        # Verifica se temos dados suficientes após calcular TRs e DMs
        if len(trs) < period:
             return None # Não temos dados suficientes para suavizar TR, +DM, -DM

        # 3. Calcular ATR (Average True Range) - Smoothed TR
        # Usa os primeiros 'period' TRs para a primeira média suavizada
        smoothed_trs = self._calculate_smoothed_average(trs, period)
        if not smoothed_trs: return None # Falha no cálculo suavizado

        # 4. Calcular Smoothed +DM e Smoothed -DM
        # Usa os primeiros 'period' +DMs e -DMs para as primeiras médias suavizadas
        # Atenção: As médias suavizadas de DM e TR devem ser baseadas no MESMO número de barras.
        # Como TRs e DMs (a partir do 2º kline) têm o mesmo comprimento, podemos usar a função.
        smoothed_plus_dms = self._calculate_smoothed_average(plus_dms, period)
        smoothed_minus_dms = self._calculate_smoothed_average(minus_dms, period)
        if not smoothed_plus_dms or not smoothed_minus_dms: return None

        # 5. Calcular +DI e -DI
        # +DI = (Smoothed +DM / ATR) * 100
        # -DI = (Smoothed -DM / ATR) * 100
        # Calculamos DI para cada ponto que temos smoothed_trs, smoothed_plus_dms, smoothed_minus_dms
        plus_dis = []
        minus_dis = []
        for i in range(len(smoothed_trs)): # Eles devem ter o mesmo comprimento
            atr_val = smoothed_trs[i]
            plus_dm_val = smoothed_plus_dms[i]
            minus_dm_val = smoothed_minus_dms[i]

            plus_di = (plus_dm_val / atr_val) * 100 if atr_val != 0 else 0
            minus_di = (minus_dm_val / atr_val) * 100 if atr_val != 0 else 0

            plus_dis.append(plus_di)
            minus_dis.append(minus_di)

        if len(plus_dis) < period:
             return None # Não temos DI's suficientes para calcular DX

        # 6. Calcular DX (Directional Movement Index)
        # DX = (abs(+DI - -DI) / (+DI + -DI)) * 100
        dxs = []
        for i in range(len(plus_dis)):
             sum_di = plus_dis[i] + minus_dis[i]
             dx = (abs(plus_dis[i] - minus_dis[i]) / sum_di) * 100 if sum_di != 0 else 0
             dxs.append(dx)

        if len(dxs) < period:
             return None # Não temos DX's suficientes para calcular ADX

        # 7. Calcular ADX (Average Directional Index) - Smoothed DX
        # Usa os primeiros 'period' DXs para a primeira média suavizada
        # Atenção: A suavização do ADX também usa a Wilder's Smoothing, mas a primeira média é a SMA dos 'period' primeiros DXs.
        smoothed_dxs = self._calculate_smoothed_average(dxs, period)

        # Retorna o último ADX calculado
        return smoothed_dxs[-1] if smoothed_dxs else None


    def _analyze_volume(self, volumes, length_short, length_long, threshold):
        """
        Analisa o volume comparando a média curta com a média longa.
        Retorna True se a média curta for threshold * média longa.
        """
        if len(volumes) < max(length_short, length_long):
            return False # Não há volumes suficientes para as médias

        # Pega os volumes mais recentes para as médias
        recent_volumes_short = volumes[-length_short:]
        recent_volumes_long = volumes[-length_long:]

        if not recent_volumes_short or not recent_volumes_long:
            return False # Falha ao pegar volumes

        avg_volume_short = sum(recent_volumes_short) / len(recent_volumes_short)
        avg_volume_long = sum(recent_volumes_long) / len(recent_volumes_long)

        # Verifica se o volume recente (curto) está acima de um threshold * volume médio (longo)
        return avg_volume_short > (avg_volume_long * threshold)


# Nova Estratégia Filtrada
class FilteredEmaCrossoverStrategy(TradingStrategy):
    """
    Estratégia baseada no cruzamento de três EMAs com filtros de ADX, RSI e Volume.
    Implementada sem bibliotecas externas como pandas_ta.
    """

    def __init__(self, symbol, fast_period=10, medium_period=25, slow_period=50,
                 adx_period=14, adx_threshold=20,
                 rsi_period=14, rsi_overbought=70, rsi_oversold=30,
                 volume_length_short=20, volume_length_long=60, volume_threshold=1.0,
                 atr_period=14): # ATR period é necessário para o cálculo do ADX

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
        self.atr_period = atr_period # Usado no cálculo do ADX

        # Atributos para armazenar os valores dos indicadores do ÚLTIMO kline processado
        # Estes são específicos para este par/instância da estratégia
        self.last_fast_ema = None
        self.last_medium_ema = None
        self.last_slow_ema = None
        self.last_adx = None
        self.last_rsi = None

        # Requisito mínimo de klines para esta estratégia.
        # Precisa de dados suficientes para calcular todas as EMAs, RSI, e ADX/Volume.
        # O ADX geralmente requer o maior número de barras (em torno de 3 * ADX_period).
        # RSI requer RSI_period + 1. EMAs requerem o maior período. Volume requer o maior length.
        # Vamos pegar o máximo desses requisitos aproximados.
        self.required_klines = max(self.slow_period,
                                   self.rsi_period + 1,
                                   self.adx_period * 3 + 1, # Aproximação para ADX
                                   self.volume_length_long)
        # Adiciona uma margem de segurança
        self.required_klines += 5 # Adiciona 5 klines de buffer

        print(f"[{self.symbol}] Estratégia Filtered EMA: Requisito mínimo de Klines = {self.required_klines}")


    def decide_action(self, symbol, klines_data, is_holding):
        """
        Determina a ação ('BUY', 'SELL', 'HOLD') com base nos cruzamentos de EMA
        filtrados por ADX, RSI e Volume.
        """
        # Extrai dados relevantes dos klines brutos
        close_prices = [float(k[4]) for k in klines_data]
        volumes = [float(k[5]) for k in klines_data] # Coluna 5 é o volume base asset

        # Verifica se tem dados suficientes
        if len(klines_data) < self.required_klines:
            # print(f"[{symbol}] Dados insuficientes ({len(klines_data)}/{self.required_klines}) para a estratégia filtrada. Esperando.")
            return 'HOLD'

        # --- Calcular Indicadores Atuais ---
        current_fast_ema = self._calculate_ema(close_prices, self.fast_period)
        current_medium_ema = self._calculate_ema(close_prices, self.medium_period)
        current_slow_ema = self._calculate_ema(close_prices, self.slow_period)
        current_rsi = self._calculate_rsi(close_prices, self.rsi_period)
        current_adx = self._calculate_adx(klines_data, self.adx_period) # Usa klines_data completo para ADX
        volume_condition_met = self._analyze_volume(volumes, self.volume_length_short, self.volume_length_long, self.volume_threshold)


        # Se algum cálculo falhou, retorna HOLD
        if None in [current_fast_ema, current_medium_ema, current_slow_ema, current_rsi, current_adx]:
             print(f"[{symbol}] Falha no cálculo de um ou mais indicadores. Retornando HOLD.")
             # Tenta atualizar os últimos valores calculados com sucesso (se houver) para não perder o estado
             if current_fast_ema is not None: self.last_fast_ema = current_fast_ema
             if current_medium_ema is not None: self.last_medium_ema = current_medium_ema
             if current_slow_ema is not None: self.last_slow_ema = current_slow_ema
             if current_rsi is not None: self.last_rsi = current_rsi
             if current_adx is not None: self.last_adx = current_adx
             return 'HOLD'


        # --- Inicialização dos últimos valores (na primeira execução com dados suficientes) ---
        if None in [self.last_fast_ema, self.last_medium_ema, self.last_slow_ema, self.last_adx, self.last_rsi]:
            print(f"[{symbol}] Inicializando valores anteriores dos indicadores. Aguardando próximo ciclo.")
            self.last_fast_ema = current_fast_ema
            self.last_medium_ema = current_medium_ema
            self.last_slow_ema = current_slow_ema
            self.last_adx = current_adx
            self.last_rsi = current_rsi
            return 'HOLD'


        # --- Regras de Decisão da Estratégia Filtrada ---
        action = 'HOLD' # Ação padrão

        # Condições Básicas de Cruzamento EMA (Semelhante à 3-EMA simples)
        # Sinal de compra: EMA Rápida cruza acima da EMA Média E ambas estão acima da EMA Lenta
        buy_ema_crossover = (current_fast_ema > current_medium_ema and self.last_fast_ema <= self.last_medium_ema) and \
                            (current_fast_ema > current_slow_ema and current_medium_ema > current_slow_ema)

        # Sinal de venda (saída antecipada): EMA Rápida cruza abaixo da EMA Média
        sell_ema_crossover = (current_fast_ema < current_medium_ema and self.last_fast_ema >= self.last_medium_ema)

        # Sinal de venda de emergência: EMA Rápida cruza abaixo da EMA Lenta
        sell_emergency_crossover = (current_fast_ema < current_slow_ema and self.last_fast_ema >= self.last_slow_ema)


        # --- Filtros ---
        adx_filter_buy = current_adx >= self.adx_threshold # ADX acima do threshold (indica tendência forte)
        rsi_filter_buy = current_rsi < self.rsi_overbought # RSI não sobrecomprado
        rsi_filter_sell = current_rsi > self.rsi_overbought # RSI sobrecomprado (sinal de venda por sobrecompra)
        rsi_filter_oversold_exit = current_rsi > self.rsi_oversold # RSI saiu da zona de sobrevenda (pode ser um sinal para NÃO vender ou ATÉ comprar, dependendo da lógica)
        # Para a VENDA por sobrecompra, também podemos adicionar a condição de que o RSI estava abaixo do overbought no período anterior
        rsi_crossed_overbought = current_rsi > self.rsi_overbought and self.last_rsi <= self.rsi_overbought

        # O filtro de volume já é True/False

        # --- Aplicar Regras e Filtros ---

        # Condição de VENDA (Saída)
        # Vende se:
        # 1. Sinal de VENDA de emergência por EMA (Rápida cruzou abaixo da Lenta)
        # 2. Sinal de VENDA por EMA (Rápida cruzou abaixo da Média) E está segurando a posição
        # 3. RSI cruzou acima da zona de sobrecompra E está segurando a posição
        # 4. ADX caiu significativamente? (Não implementado aqui, mas pode ser um filtro de saída)

        # Prioriza a venda de emergência
        if sell_emergency_crossover:
            print(f"[{symbol}] SINAL DE VENDA DE EMERGÊNCIA: EMA{self.fast_period} cruzou ABAIXO da EMA{self.slow_period}.")
            action = 'SELL'

        # Se não houve venda de emergência AGORA, checa outros sinais de venda SE estiver segurando
        elif is_holding:
            if sell_ema_crossover:
                 print(f"[{symbol}] SINAL DE VENDA: EMA{self.fast_period} cruzou ABAIXO da EMA{self.medium_period}.")
                 action = 'SELL'
            elif rsi_crossed_overbought:
                 print(f"[{symbol}] SINAL DE VENDA por RSI: RSI ({current_rsi:.2f}) cruzou ACIMA da zona de sobrecompra ({self.rsi_overbought}).")
                 action = 'SELL'
            # Adicionar outras condições de saída aqui se necessário (ex: Stop Loss, Take Profit, etc.)


        # Condição de COMPRA (Entrada)
        # Compra SE:
        # 1. Houve o sinal de COMPRA por cruzamento EMA
        # 2. O filtro ADX permite (ADX > threshold)
        # 3. O filtro RSI permite (RSI < overbought)
        # 4. A condição de Volume é atendida
        # 5. O bot NÃO está segurando a posição
        # 6. Ainda não decidiu VENDER nesta iteração
        # Note: O filtro RSI < oversold NÃO é uma condição de compra aqui,
        # é mais uma condição para NÃO vender (se estivesse operando short)
        # ou talvez um sinal de reversão para esperar uma compra.
        # Para LONG, geralmente se evita comprar em sobrevenda, a não ser que a estratégia seja de reversão.
        # A estratégia atual é baseada em tendência (EMAs, ADX), então evitamos sobrecompra (RSI < overbought)
        # e queremos força de tendência (ADX > threshold). Volume confirma o movimento.

        if action == 'HOLD' and not is_holding: # Só considera comprar se não vendeu E não está segurando
            # Verifica todas as condições para a compra
            if buy_ema_crossover and adx_filter_buy and rsi_filter_buy and volume_condition_met:
                print(f"[{symbol}] SINAL DE COMPRA VÁLIDO:")
                print(f" - Cruzamento EMA {self.fast_period}/{self.medium_period} acima de {self.slow_period}: OK")
                print(f" - ADX ({current_adx:.2f}) >= Threshold ({self.adx_threshold}): OK")
                print(f" - RSI ({current_rsi:.2f}) < Overbought ({self.rsi_overbought}): OK")
                print(f" - Condição de Volume ({volume_condition_met}): OK")
                action = 'BUY'
            # else:
                # print(f"[{symbol}] Sinal de compra NÃO VÁLIDO. Motivos:")
                # if not buy_ema_crossover: print(" - Cruzamento EMA NÃO ocorreu ou NÃO está acima da EMA Lenta")
                # if not adx_filter_buy: print(f" - ADX ({current_adx:.2f}) abaixo do Threshold ({self.adx_threshold})")
                # if not rsi_filter_buy: print(f" - RSI ({current_rsi:.2f}) >= Overbought ({self.rsi_overbought})")
                # if not volume_condition_met: print(f" - Condição de Volume NÃO atendida ({volume_condition_met})")


        # --- Atualiza os valores anteriores para a próxima iteração ---
        self.last_fast_ema = current_fast_ema
        self.last_medium_ema = current_medium_ema
        self.last_slow_ema = current_slow_ema
        self.last_adx = current_adx
        self.last_rsi = current_rsi

        # Loga os valores atuais dos indicadores (Opcional, pode ser removido se poluir muito)
        # print(f"[{symbol}] Indicadores Atuais: EMA{self.fast_period}={current_fast_ema:.8f}, EMA{self.medium_period}={current_medium_ema:.8f}, EMA{self.slow_period}={current_slow_ema:.8f}, RSI={current_rsi:.2f}, ADX={current_adx:.2f}, VolumeOK={volume_condition_met}. Decisão: {action}")


        return action


# --- Exemplo de como adicionar outras estratégias (mesma estrutura, nomes diferentes) ---
# Mantenha estas classes se você as mapeou em bot_trader.py, mesmo que usem a mesma lógica da base 3-EMA simples
# Ou remova-as e use FilteredEmaCrossoverStrategy diretamente para todos os pares, ajustando os parâmetros em bot_trader.py

class EmaThreeLinesCrossoverStrategy(TradingStrategy):
    """Estratégia baseada no cruzamento de TRÊS EMAs (rápida, média, lenta). Versão original."""
    # Removemos o argumento wait_interval_seconds
    def __init__(self, symbol, fast_period=7, medium_period=20, slow_period=40):
        """Inicializa a estratégia com o par e os períodos das três EMAs."""
        self.symbol = symbol # Armazena o par para identificação
        self.fast_period = fast_period
        self.medium_period = medium_period
        self.slow_period = slow_period

        # Atributos para armazenar os valores das EMAs do ÚLTIMO kline processado
        self.last_fast_ema = None
        self.last_medium_ema = None
        self.last_slow_ema = None

        # Requisito mínimo de klines para esta estratégia
        self.required_klines = max(self.fast_period, self.medium_period, self.slow_period) + 1 # Precisa de pelo menos 1 kline a mais para comparar com o anterior


    # Retorno simplificado: apenas a ação
    def decide_action(self, symbol, klines_data, is_holding):
        """
        Determina a ação com base no cruzamento das três EMAs (versão simples).
        Retorna apenas a ação ('BUY', 'SELL', 'HOLD').
        """
        # Extrai apenas os preços de fechamento
        close_prices = [float(k[4]) for k in klines_data]

        # Verifica se tem dados suficientes
        if len(close_prices) < self.required_klines:
            # print(f"[{symbol}] Dados insuficientes ({len(close_prices)}/{self.required_klines}) para a estratégia 3-EMA simples. Esperando.")
            return 'HOLD'

        # Calcula as EMAs mais recentes
        current_fast_ema = self._calculate_ema(close_prices, self.fast_period)
        current_medium_ema = self._calculate_ema(close_prices, self.medium_period)
        current_slow_ema = self._calculate_ema(close_prices, self.slow_period)

        # Se por algum motivo o cálculo falhou
        if None in [current_fast_ema, current_medium_ema, current_slow_ema]:
             print(f"[{symbol}] Erro ao calcular EMAs na estratégia 3-EMA simples. Dados Klines: {len(close_prices)}")
             return 'HOLD'

        # --- Lógica para detectar cruzamentos (requer valores anteriores) ---
        if None in [self.last_fast_ema, self.last_medium_ema, self.last_slow_ema]:
            # Primeira execução com dados suficientes: apenas armazena os valores atuais
            print(f"[{symbol}] Inicializando valores de EMAs anteriores (3-EMA simples). Aguardando próximo ciclo.")
            self.last_fast_ema = current_fast_ema
            self.last_medium_ema = current_medium_ema
            self.last_slow_ema = current_slow_ema
            return 'HOLD' # Retorna HOLD


        # === Regras de Decisão (3-EMA simples) ===
        action = 'HOLD' # Ação padrão

        # Condição de Venda de Emergência: EMA 7 cruza ABAIXO da EMA 40
        has_crossed_below_slow = current_fast_ema < current_slow_ema and self.last_fast_ema >= self.last_slow_ema

        if has_crossed_below_slow:
             print(f"[{symbol}] SINAL DE EMERGÊNCIA (3-EMA simples): EMA{self.fast_period} cruzou ABAIXO da EMA{self.slow_period}!")
             action = 'SELL' # Sinal de venda total

        # Condição de Compra: EMA 7 cruza ACIMA da EMA 20 E ambas estão acima da EMA 40
        # Só considera compra se NÃO houve sinal de venda de emergência AGORA E NÃO está segurando a posição
        elif not is_holding:
             has_crossed_above_medium = current_fast_ema > current_medium_ema and self.last_fast_ema <= self.last_medium_ema
             if has_crossed_above_medium and current_fast_ema > current_slow_ema and current_medium_ema > current_slow_ema:
                  print(f"[{symbol}] SINAL DE COMPRA (3-EMA simples): EMA{self.fast_period} cruzou ACIMA da EMA{self.medium_period} (acima da EMA{self.slow_period}).")
                  action = 'BUY'


        # Condição de Venda (Saída): EMA 7 cruza ABAIXO da EMA 20 E está segurando a posição
        # Só considera venda (saída) se NÃO houve sinal de venda de emergência AGORA E ESTÁ segurando a posição
        elif is_holding:
             has_crossed_below_medium = current_fast_ema < current_medium_ema and self.last_fast_ema >= self.last_medium_ema
             if has_crossed_below_medium: # Epcifamente, se EMA 7 está abaixo da EMA 20 (e cruzou)
                  print(f"[{symbol}] SINAL DE VENDA (Saída 3-EMA simples): EMA{self.fast_period} cruzou ABAIXO da EMA{self.medium_period}.")
                  action = 'SELL'


        # --- Atualiza os valores das EMAs anteriores para a próxima iteração ---
        self.last_fast_ema = current_fast_ema
        self.last_medium_ema = current_medium_ema
        self.last_slow_ema = current_slow_ema


        # Retorna apenas a ação decidida
        return action

# Classes específicas para ETH e SOL usando a estratégia 3-EMA simples (mantenha se você as usa em bot_trader.py)
class EmaThreeLinesCrossoverStrategyETH(EmaThreeLinesCrossoverStrategy):
    """Estratégia 3-EMA para ETHUSDT."""
    pass # Usa os parâmetros padrão da classe base 3-EMA simples

class EmaThreeLinesCrossoverStrategySOL(EmaThreeLinesCrossoverStrategy):
    """Estratégia 3-EMA para SOLUSDT."""
    pass # Usa os parâmetros padrão da classe base 3-EMA simples
