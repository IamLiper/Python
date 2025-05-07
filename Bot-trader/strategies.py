# strategies.py
import math
from abc import ABC, abstractmethod
# import time # Não precisa mais de time aqui

# Removidos os tipos de atraso, a estratégia só retorna a ação

class TradingStrategy(ABC):
    """Classe base abstrata para estratégias de trading."""

    @abstractmethod
    # Retorno simplificado: apenas a ação
    # Removemos os argumentos de intervalo
    def decide_action(self, symbol, klines):
        """
        Determina a ação de trading ('BUY', 'SELL', 'HOLD') com base SOMENTE nos dados do gráfico
        e estado interno da estratégia.
        O bot principal gerencia saldos, alocações e a frequência de checagem.

        Args:
            symbol (str): O par de trading (ex: 'BTCUSDT').
            klines (list): Lista de preços de fechamento (floats).

        Returns:
            str: 'BUY', 'SELL', ou 'HOLD'.
        """
        pass

    def _calculate_ema(self, prices, period):
        """Calcula a Média Móvel Exponencial (EMA) para um período."""
        if period <= 0:
            return None
        # Para calcular o EMA no último ponto, precisamos de pelo menos 'period' + 1 pontos
        # Ajuste para garantir que temos dados suficientes para calcular a SMA inicial
        if len(prices) < period:
             return None

        alpha = 2 / (period + 1)

        # Calcula a primeira EMA (usando SMA dos primeiros 'period' preços)
        ema = sum(prices[:period]) / period

        # Calcula os EMAs subsequentes até o final da lista
        for price in prices[period:]:
            ema = (price * alpha) + (ema * (1 - alpha))

        return ema


class EmaThreeLinesCrossoverStrategy(TradingStrategy):
    """Estratégia baseada no cruzamento de TRÊS EMAs (rápida, média, lenta)."""

    # Removemos o argumento wait_interval_seconds
    def __init__(self, symbol, fast_period=7, medium_period=20, slow_period=40):
        """Inicializa a estratégia com o par e os períodos das três EMAs."""
        self.symbol = symbol # Armazena o par para identificação
        self.fast_period = fast_period
        self.medium_period = medium_period
        self.slow_period = slow_period

        # Atributos para armazenar os valores das EMAs do ÚLTIMO kline processado
        # Estes são específicos para este par/instância da estratégia
        self.last_fast_ema = None
        self.last_medium_ema = None
        self.last_slow_ema = None

        # Requisito mínimo de klines para esta estratégia
        self.required_klines = max(self.fast_period, self.medium_period, self.slow_period)


    # Retorno simplificado: apenas a ação
    # Removemos os argumentos de intervalo e saldos
    def decide_action(self, symbol, klines):
        """
        Determina a ação com base no cruzamento das três EMAs.
        Retorna apenas a ação ('BUY', 'SELL', 'HOLD').
        """
        # Verifica se tem dados suficientes
        # O bot principal também checa isso, mas é bom ter a validação na estratégia
        if len(klines) < self.required_klines:
            # print(f"[{symbol}] Dados insuficientes ({len(klines)}/{self.required_klines}) para a estratégia 3-EMA. Esperando.")
            # A estratégia não decide ação de BUY/SELL sem dados, retorna HOLD
            # O bot principal que gerencia o tempo de espera inicial/por falta de dados
            return 'HOLD'


        # Calcula as EMAs mais recentes
        current_fast_ema = self._calculate_ema(klines, self.fast_period)
        current_medium_ema = self._calculate_ema(klines, self.medium_period)
        current_slow_ema = self._calculate_ema(klines, self.slow_period)

        # Se por algum motivo o cálculo falhou
        if current_fast_ema is None or current_medium_ema is None or current_slow_ema is None:
             print(f"[{symbol}] Erro ao calcular EMAs na estratégia. Dados Klines: {len(klines)}")
             return 'HOLD'


        # --- Lógica para detectar cruzamentos (requer valores anteriores) ---
        if self.last_fast_ema is None or self.last_medium_ema is None or self.last_slow_ema is None:
            # Primeira execução com dados suficientes: apenas armazena os valores atuais
            # Não decide ação na primeira execução com dados completos
            print(f"[{symbol}] Inicializando valores de EMAs anteriores. Aguardando próximo ciclo.")
            self.last_fast_ema = current_fast_ema
            self.last_medium_ema = current_medium_ema
            self.last_slow_ema = current_slow_ema
            return 'HOLD' # Retorna HOLD


        # === Regras de Decisão ===
        action = 'HOLD' # Ação padrão

        # 1. Condição de Venda de Emergência: EMA 7 cruza ABAIXO da EMA 40
        has_crossed_below_slow = current_fast_ema < current_slow_ema and self.last_fast_ema >= self.last_slow_ema

        if has_crossed_below_slow:
             print(f"[{symbol}] SINAL DE EMERGÊNCIA: EMA{self.fast_period} cruzou ABAIXO da EMA{self.slow_period}!")
             action = 'SELL' # Sinal de venda total

        # 2. Condição para operar a estratégia principal: EMA 7 e EMA 20 ACIMA ou cruzando ACIMA da EMA 40
        # Só verificamos os cruzamentos 7/20 se NÃO houve o sinal de emergência AGORA
        # E se a EMA 7 está ACIMA ou IGUAL da EMA 40 (zona de interesse para alta)
        is_in_potential_uptrend_zone = current_fast_ema >= current_slow_ema

        if action == 'HOLD' and is_in_potential_uptrend_zone: # Só checa 7/20 se ainda não decidiu VENDER emergencialmente E 7 >= 40

            # Verificar se ambas 7 e 20 estão AGORA acima da 40 para os sinais normais
            is_trading_zone_active = current_fast_ema > current_slow_ema and current_medium_ema > current_slow_ema

            if is_trading_zone_active:
                # Estamos na "zona de compra/venda rápida" acima da EMA 40

                # Verificar cruzamentos entre EMA 7 e EMA 20
                has_crossed_above_medium = current_fast_ema > current_medium_ema and self.last_fast_ema <= self.last_medium_ema
                has_crossed_below_medium = current_fast_ema < current_medium_ema and self.last_fast_ema >= self.last_medium_ema

                if has_crossed_above_medium:
                     print(f"[{symbol}] Sinal: EMA{self.fast_period} cruzou ACIMA da EMA{self.medium_period} (acima da EMA{self.slow_period}).")
                     action = 'BUY' # Sinal de compra

                elif has_crossed_below_medium:
                     print(f"[{symbol}] Sinal: EMA{self.fast_period} cruzou ABAIXO da EMA{self.medium_period} (acima da EMA{self.slow_period}).")
                     action = 'SELL' # Sinal de venda (saída antecipada)

                # Se nenhuma das regras acima acionou uma compra/venda, a ação continua sendo HOLD

            else:
                 # Se 7 e 20 NÃO estão ambas acima da 40, mas 7 está ACIMA ou IGUAL da 40
                 # Espera a EMA 20 passar para cima da 40 ou o 7 cruzar a 20 (se já acima da 40)
                 pass # action é HOLD

        # 3. Condição para MANTER FORA: EMA 7 está ABAIXO da EMA 40 (e não foi o cruzamento agora)
        # Se a ação ainda é HOLD (nenhuma regra de BUY/SELL foi acionada AGORA)
        # E a EMA 7 está claramente abaixo da EMA 40.
        # Usamos '<' estrito para diferenciar do cruzamento que foi tratado na regra 1.
        # Neste caso, a estratégia retorna HOLD, e o bot principal saberá que está na "zona de espera longa".
        if action == 'HOLD' and current_fast_ema < current_slow_ema:
             # print(f"[{symbol}] EMA{self.fast_period} está abaixo da EMA{self.slow_period}. Modo de espera longa.")
             action = 'HOLD' # Confirma HOLD

        # --- Atualiza os valores das EMAs anteriores para a próxima iteração ---
        self.last_fast_ema = current_fast_ema
        self.last_medium_ema = current_medium_ema
        self.last_slow_ema = current_slow_ema


        # Retorna apenas a ação decidida
        return action

# --- Exemplo de como adicionar outras estratégias (mesma estrutura, nomes diferentes) ---
class EmaThreeLinesCrossoverStrategyETH(EmaThreeLinesCrossoverStrategy):
    """Estratégia 3-EMA para ETHUSDT (pode ter parâmetros diferentes no futuro)."""
    def __init__(self, symbol, fast_period=7, medium_period=20, slow_period=40):
         super().__init__(symbol, fast_period, medium_period, slow_period)

class EmaThreeLinesCrossoverStrategySOL(EmaThreeLinesCrossoverStrategy):
    """Estratégia 3-EMA para SOLUSDT (pode ter parâmetros diferentes no futuro)."""
    def __init__(self, symbol, fast_period=7, medium_period=20, slow_period=40):
         super().__init__(symbol, fast_period, medium_period, slow_period)

# --- Exemplo de como você adicionaria uma estratégia DIFERENTE ---
# class RsiStrategy(TradingStrategy):
#     def __init__(self, symbol, rsi_period=14):
#          self.symbol = symbol
#          self.rsi_period = rsi_period
#          self.required_klines = rsi_period + 1
#          # ... state variables for RSI calculation ...

#     def decide_action(self, symbol, klines):
#          if len(klines) < self.required_klines:
#               return 'HOLD'
#          # ... calculate RSI ...
#          # ... implement RSI logic ...
#          # return 'BUY' or 'SELL' or 'HOLD'