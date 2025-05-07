# bot_trader.py
import os
import time
import requests
import math
import pandas as pd # Necessário para a nova estratégia filtrada (usada em strategies.py)
# Removemos a necessidade direta de pandas_ta aqui, mas pandas é usado na estratégia

from dotenv import load_dotenv
from binance.client import Client
from binance.exceptions import BinanceAPIException

# Importar as estratégias
from strategies import (
    TradingStrategy, # Importa a classe base (boa prática)
    EmaThreeLinesCrossoverStrategy, # Sua estratégia original simples
    EmaThreeLinesCrossoverStrategyETH, # Estratégia simples para ETH (pode ser mudada)
    EmaThreeLinesCrossoverStrategySOL, # Estratégia simples para SOL (pode ser mudada)
    FilteredEmaCrossoverStrategy, # Importe a NOVA estratégia filtrada sem pandas_ta
)

# === Carrega variáveis de ambiente (.env) ===
load_dotenv()
API_KEY = os.getenv('API_KEY')
API_SECRET = os.getenv('API_SECRET')

# === Chaves do Telegram ===
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def enviar_telegram(mensagem):
    """Envia uma mensagem para o Telegram usando o bot configurado."""
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensagem}
        try:
            requests.post(url, json=payload)
        except Exception as e:
            print(f"Erro ao enviar mensagem para o Telegram: {e}")
    else:
        # print("Telegram não configurado. Mensagem não enviada.") # Comentado para não poluir o log se não usar Telegram
        pass # Não faz nada se não configurado

client = Client(API_KEY, API_SECRET)

# === Parâmetros Globais do Bot Multi-Moeda ===
# Intervalo dos Klines para a ESTRATÉGIA (aplicado a todos os pares)
INTERVALO_KLINES = Client.KLINE_INTERVAL_4HOUR # Renomeado para clareza

# Lista de moedas base que o bot irá operar (sempre contra USDT)
MOEDAS_A_OPERAR = ['BTC', 'ETH', 'SOL'] # Ou outras moedas que você quer operar
BASE_ASSET = 'USDT' # A moeda base para todas as negociações (dólar) # <--- CORRIGIDO: MOVIDO PARA CIMA
TRADING_PAIRS = [f'{coin}{BASE_ASSET}' for coin in MOEDAS_A_OPERAR]

# --- Parâmetros de Alocação de Capital (NOVA LÓGICA) ---
# O bot tentará gastar este montante em USDT POR TRADE de compra, se o saldo total livre permitir e >= MIN_NOTIONAL
TRADE_AMOUNT_USDT_TARGET = 15.0 # Alvo de ~15 USDT por trade de compra (ajuste conforme seu risco/capital)
# Este valor DEVE ser maior que o MIN_NOTIONAL de qualquer par que você opere.


# --- Parâmetro de Frequência de Checagem ---
# Define com que frequência o bot irá verificar TODOS os pares
# Importante: Este CHECK_INTERVAL_SECONDS DEVE ser um múltiplo do intervalo dos klines.
# Ex: Se klines é 4H (240 min), CHECK_INTERVAL_SECONDS pode ser 5min, 10min, 240min, 480min, etc.
# O bot decide APENAS com base na ÚLTIMA barra FECHADA.
# Se CHECK_INTERVAL_SECONDS for menor que o intervalo dos klines, o bot checará a mesma barra fechada várias vezes.
# Se for igual ou múltiplo, checará em intervalos alinhados com o fechamento das barras.
CHECK_INTERVAL_SECONDS = 5 * 60 # Checa a cada 5 minutos (ajuste conforme sua preferência)

# Pequeno sleep entre a checagem de um par e outro para não sobrecarregar a API (em milissegundos)
SLEEP_BETWEEN_PAIRS_MS = 500

# Mínimos gerais (serão ajustados pela precisão da Binance por par)
MIN_USDT_TRADE = 10.0 # Mínimo em USDT para uma ordem de compra (será ajustado pelo MIN_NOTIONAL obtido da Binance)


# --- Estrutura para armazenar o estado de cada par ---
trading_state = {}

# LIMITE_KLINES será ajustado dinamicamente com base no maior requisito das estratégias
LIMITE_KLINES = 0


# --- Funções de Utilitários ---

def ajustar_tempo():
    """Ajusta o timestamp do cliente Binance com o servidor."""
    try:
        # Usando get_server_time() que já é uma função do client
        server_time = client.get_server_time()
        local_time = int(time.time() * 1000)
        time_diff = server_time['serverTime'] - local_time
        client.timestamp_offset = time_diff # Aplica o offset ao client
        print(f"Ajuste de tempo calculado e aplicado: {time_diff} ms")
        # Opcional: enviar para o Telegram se a diferença for grande
        if abs(time_diff) > 1000: # > 1 segundo
            enviar_telegram(f"⏰ Sincronização de tempo: {time_diff}ms de diferença.")

    except Exception as e:
        print(f"Erro ao ajustar o tempo: {e}")
        enviar_telegram(f"❌ Erro ao ajustar o tempo: {e}")


def get_symbol_details(symbol):
    """Obtém detalhes de precisão e filtros para um dado par."""
    details = {
        'quantity_step_size': None,
        'num_decimal_places': 8, # Default para quote asset
        'price_tick_size': None,
        'price_decimal_places': 8, # Default para preço
        'min_notional': 0.0,
        'min_quantity': 0.0, # Calculado a partir do stepSize
    }
    try:
        symbol_info = client.get_symbol_info(symbol)
        for f in symbol_info['filters']:
            if f['filterType'] == 'LOT_SIZE':
                details['quantity_step_size'] = float(f['stepSize'])
                details['min_quantity'] = float(f['minQty']) # Mínimo do LOT_SIZE
                # Calcula casas decimais a partir do stepSize
                step_str = str(details['quantity_step_size'])
                if '.' in step_str:
                    details['num_decimal_places'] = len(step_str.split('.')[1].rstrip('0')) # Remove zeros à direita antes de contar
                else:
                    details['num_decimal_places'] = 0

            elif f['filterType'] == 'PRICE_FILTER':
                details['price_tick_size'] = float(f['tickSize'])
                # Calcula casas decimais a partir do tickSize
                tick_str = str(details['price_tick_size'])
                if '.' in tick_str:
                    details['price_decimal_places'] = len(tick_str.split('.')[1].rstrip('0')) # Remove zeros à direita antes de contar
                else:
                    details['price_decimal_places'] = 0

            elif f['filterType'] == 'MIN_NOTIONAL':
                details['min_notional'] = float(f['minNotional'])

        # Atualiza o MIN_USDT_TRADE global se o mínimo nocional do par for maior
        global MIN_USDT_TRADE
        if details['min_notional'] > MIN_USDT_TRADE:
             MIN_USDT_TRADE = details['min_notional']

    except Exception as e:
        print(f"Erro ao obter detalhes para o par {symbol}: {e}")
        enviar_telegram(f"❌ Erro ao obter detalhes para {symbol}: {e}")
        # Fallback values (valores seguros, mas podem não ser precisos para o par)
        details['quantity_step_size'] = 1e-8
        details['num_decimal_places'] = 8
        details['price_tick_size'] = 1e-2
        details['price_decimal_places'] = 2
        details['min_notional'] = 10.0
        details['min_quantity'] = 1e-8

    # print(f"[{symbol}] Details: {details}") # Opcional: descomentar para ver detalhes
    return details


def floor_to_precision(quantity, step_size, num_decimal_places):
    """Arredonda uma quantidade para baixo na precisão correta."""
    # print(f"Arredondando {quantity} com step {step_size} e {num_decimal_places} casas.") # Debug
    if step_size is None or step_size <= 0:
        print(f"Aviso: step_size inválido ({step_size}). Usando precisão padrão de {num_decimal_places} casas decimais para arredondar {quantity}.")
        # Fallback para arredondamento decimal direto
        factor = 10**num_decimal_places
        return math.floor(quantity * factor) / factor

    # Arredonda para o step_size mais próximo abaixo
    num_steps = math.floor(quantity / step_size)
    rounded_quantity = num_steps * step_size

    # Garante que o resultado tem o número correto de casas decimais para evitar notação científica em string
    # Use float() para garantir que seja tratado como float para o f-string
    # Use round() para garantir a precisão, pois a multiplicação de floats pode ser imprecisa
    return float(f'{rounded_quantity:.{num_decimal_places}f}')


# --- Funções de Trading Genéricas ---

def execute_buy_order(symbol, usdt_amount_to_spend, symbol_details, current_price):
    """Executa uma ordem de compra a mercado usando um montante específico de USDT."""
    try:
        # Verifica se o montante atende ao mínimo nocional
        if usdt_amount_to_spend < symbol_details['min_notional']:
            print(f"[{symbol}] Montante USDT para compra ({usdt_amount_to_spend:.2f}) menor que o mínimo nocional ({symbol_details['min_notional']:.2f}). Cancelando.")
            enviar_telegram(f"⚠️ [{symbol}] Compra cancelada: Montante ({usdt_amount_to_spend:.2f} {BASE_ASSET}) < mín. nocional ({symbol_details['min_notional']:.2f}).")
            return None, None # Não executa ordem

        # Calcula a quantidade desejada e arredonda para a precisão do par
        quantidade_desejada = usdt_amount_to_spend / current_price
        quantidade_calculada = floor_to_precision(quantidade_desejada, symbol_details['quantity_step_size'], symbol_details['num_decimal_places'])

        # Verifica se a quantidade arredondada atende ao mínimo de quantidade
        if quantidade_calculada < symbol_details['min_quantity']:
             print(f"[{symbol}] Quantidade calculada ({quantidade_calculada:.{symbol_details['num_decimal_places']}f}) menor que o mínimo do par ({symbol_details['min_quantity']:.{symbol_details['min_quantity']}f}). Cancelando.")
             enviar_telegram(f"⚠️ [{symbol}] Compra cancelada: Qtd ({quantidade_calculada:.{symbol_details['num_decimal_places']}f}) < mín. do par ({symbol_details['min_quantity']:.{symbol_details['min_quantity']}f}).")
             return None, None # Não executa ordem

        # Formata a quantidade para a string correta com a precisão necessária
        quantity_str = f"{quantidade_calculada:.{symbol_details['num_decimal_places']}f}".rstrip('0').rstrip('.') # Remove zeros no final e ponto se inteiro

        print(f"[{symbol}] Tentando COMPRAR {quantity_str} com ~{usdt_amount_to_spend:.2f} USDT...")
        enviar_telegram(f"⏳ [{symbol}] Tentando COMPRAR {quantity_str} com ~{usdt_amount_to_spend:.2f} {BASE_ASSET}...")

        ordem = client.order_market_buy(symbol=symbol, quantity=quantity_str)
        print(f"[{symbol}] Ordem de compra enviada. ID: {ordem.get('orderId')}, Status: {ordem.get('status')}")

        # Tenta obter os detalhes de preenchimento se a ordem for executada imediatamente
        filled_quantity = 0.0
        total_fill_price = 0.0
        fills = ordem.get('fills', [])
        if fills:
            for fill in fills:
                qty = float(fill['qty'])
                price = float(fill['price'])
                # comission = float(fill['commission']) # Se precisar rastrear comissão por fill
                filled_quantity += qty
                total_fill_price += qty * price # Soma o valor total (qty * price)

            avg_price = total_fill_price / filled_quantity if filled_quantity > 0 else current_price
            print(f"[{symbol}] Ordem preenchida. Qtd: {filled_quantity:.{symbol_details['num_decimal_places']}f}, Preço Médio: {avg_price:.{symbol_details['price_decimal_places']}f}")
            # Note: Binance Market orders usually fill immediately or are cancelled.
            # If status is FILLED, fills list should not be empty.

            return filled_quantity, avg_price

        else:
            # Se não houver 'fills', a ordem pode estar PENDING, EXPIRED, CANCELED, etc.
            # Para ordens MARKET, 'fills' vazio geralmente significa que não foi preenchida,
            # o que não deveria acontecer com sucesso (a menos que seja um erro ou problema de rede).
            # Consideramos que a ordem não foi executada com sucesso se não houver fills.
            print(f"[{symbol}] Aviso: Ordem de compra enviada (ID: {ordem.get('orderId')}), mas sem fills na resposta. Status: {ordem.get('status')}. Assumindo falha na execução.")
            enviar_telegram(f"⚠️ [{symbol}] Ordem de compra enviada, mas sem fills. Status: {ordem.get('status')}.")
            return None, None

    except BinanceAPIException as e:
        print(f"[{symbol}] Erro da API ao comprar: {e.code}: {e.message}")
        enviar_telegram(f"❌ Falha na compra ({symbol}):\n{e.code}: {e.message}")
        return None, None
    except Exception as e:
        print(f"[{symbol}] Erro inesperado ao comprar: {e}")
        enviar_telegram(f"❌ Erro inesperado na compra ({symbol}):\n{e}")
        return None, None


def execute_sell_order(symbol, quantity_to_sell, symbol_details, current_price):
    """Executa uma ordem de venda a mercado usando uma quantidade específica da moeda."""
    try:
        # Arredonda a quantidade para a precisão do par
        quantity_calculated = floor_to_precision(quantity_to_sell, symbol_details['quantity_step_size'], symbol_details['num_decimal_places'])

        # Verifica se a quantidade arredondada atende ao mínimo de quantidade
        if quantity_calculated < symbol_details['min_quantity']:
             print(f"[{symbol}] Quantidade para venda ({quantity_calculated:.{symbol_details['num_decimal_places']}f}) menor que o mínimo do par ({symbol_details['min_quantity']:.{symbol_details['min_quantity']}f}). Cancelando.")
             enviar_telegram(f"⚠️ [{symbol}] Venda cancelada: Qtd ({quantity_calculated:.{symbol_details['num_decimal_places']}f}) < mín. do par ({symbol_details['min_quantity']:.{symbol_details['min_quantity']}f}).")
             return None, None, None # Não executa ordem

        # Verifica se a venda estimada atende ao mínimo nocional
        estimated_notional = quantity_calculated * current_price
        if estimated_notional < symbol_details['min_notional']:
             print(f"[{symbol}] Venda estimada ({estimated_notional:.2f} USDT) menor que o mínimo nocional ({symbol_details['min_notional']:.2f}). Cancelando.")
             enviar_telegram(f"⚠️ [{symbol}] Venda cancelada: Estimativa ({estimated_notional:.2f} {BASE_ASSET}) < mín. nocional ({symbol_details['min_notional']:.2f}).")
             return None, None, None # Não executa ordem


        # Formata a quantidade para a string correta com a precisão necessária
        quantity_str = f"{quantity_calculated:.{symbol_details['num_decimal_places']}f}".rstrip('0').rstrip('.') # Remove zeros no final e ponto se inteiro

        print(f"[{symbol}] Tentando VENDER {quantity_str} {symbol}...")
        enviar_telegram(f"⏳ [{symbol}] Tentando VENDER {quantity_str} {symbol}...")

        ordem = client.order_market_sell(symbol=symbol, quantity=quantity_str)
        print(f"[{symbol}] Ordem de venda enviada. ID: {ordem.get('orderId')}, Status: {ordem.get('status')}")


        # Tenta obter os detalhes de preenchimento
        filled_quantity = 0.0
        total_revenue = 0.0 # Total de USDT recebido
        fills = ordem.get('fills', [])
        if fills:
            for fill in fills:
                qty = float(fill['qty'])
                price = float(fill['price'])
                # comission = float(fill['commission']) # Se precisar rastrear comissão por fill
                filled_quantity += qty
                total_revenue += qty * price # Soma o valor total (qty * price)

            avg_price = total_revenue / filled_quantity if filled_quantity > 0 else current_price
            print(f"[{symbol}] Ordem preenchida. Qtd: {filled_quantity:.{symbol_details['num_decimal_places']}f}, Preço Médio: {avg_price:.{symbol_details['price_decimal_places']}f}, Receita: {total_revenue:.2f} USDT")
            # Note: Similarmente às compras, market sells devem preencher imediatamente.

            return filled_quantity, avg_price, total_revenue

        else:
            print(f"[{symbol}] Aviso: Ordem de venda enviada (ID: {ordem.get('orderId')}), mas sem fills na resposta. Status: {ordem.get('status')}. Assumindo falha na execução.")
            enviar_telegram(f"⚠️ [{symbol}] Ordem de venda enviada, mas sem fills. Status: {ordem.get('status')}.")
            return None, None, None


    except BinanceAPIException as e:
        print(f"[{symbol}] Erro da API ao vender: {e.code}: {e.message}")
        enviar_telegram(f"❌ Falha na venda ({symbol}):\n{e.code}: {e.message}")
        return None, None, None
    except Exception as e:
        print(f"[{symbol}] Erro inesperado ao vender: {e}")
        enviar_telegram(f"❌ Erro inesperado na venda ({symbol}):\n{e}")
        return None, None, None


def get_all_balances():
    """Obtém o saldo livre de USDT e todas as moedas em MOEDAS_A_OPERAR."""
    balances = {BASE_ASSET: 0.0}
    for coin in MOEDAS_A_OPERAR:
        balances[coin] = 0.0

    try:
        # print("Obtendo saldos da conta...") # Debug
        account_info = client.get_account()
        for balance in account_info['balances']:
            asset = balance['asset']
            # Inclui o BASE_ASSET e as moedas de trading
            if asset == BASE_ASSET or asset in MOEDAS_A_OPERAR:
                # print(f" Saldo {asset}: Free={balance['free']}, Locked={balance['locked']}") # Debug
                balances[asset] = float(balance['free']) # Pega apenas o saldo LIVRE
        # print(f"Saldos obtidos: {balances}") # Debug
        return balances
    except Exception as e:
        print(f"Erro ao obter todos os saldos: {e}")
        enviar_telegram(f"❌ Erro ao obter todos os saldos: {e}")
        # Retorna saldos iniciais (zero para as moedas de trading e USDT) em caso de erro
        # Isso pode prevenir trades indesejados se não souber o saldo real
        fallback_balances = {BASE_ASSET: 0.0}
        for coin in MOEDAS_A_OPERAR:
             fallback_balances[coin] = 0.0
        return fallback_balances


def initialize_trading_state():
    """Inicializa a estrutura de estado para todos os pares de trading e configura estratégias."""
    print("Inicializando estado de trading...")

    initial_balances = get_all_balances()
    total_initial_usdt = initial_balances.get(BASE_ASSET, 0.0)
    print(f"Saldo {BASE_ASSET} Livre Inicial Detectado na Conta: {total_initial_usdt:.2f}")
    enviar_telegram(f"Bot: Saldo {BASE_ASSET} Livre Inicial Detectado: {total_initial_usdt:.2f}.")


    pairs_to_process = []
    # Definir qual estratégia usar para cada par
    pair_strategy_map = {
        'BTCUSDT': FilteredEmaCrossoverStrategy, # Usar a nova estratégia filtrada para BTC
        'ETHUSDT': FilteredEmaCrossoverStrategy, # Usar a nova estratégia filtrada para ETH (pode mudar parâmetros)
        'SOLUSDT': FilteredEmaCrossoverStrategy, # Usar a nova estratégia filtrada para SOL (pode mudar parâmetros)
        # 'OUTROUSDT': EmaThreeLinesCrossoverStrategy, # Exemplo: usar a estratégia simples para outro par
    }

    # Parâmetros específicos para a estratégia filtrada por par (opcional)
    # Se um par não estiver neste dicionário, usará os parâmetros padrão da classe
    filtered_strategy_params = {
        'BTCUSDT': {'fast_period': 7, 'medium_period': 20, 'slow_period': 40, 'adx_period': 14, 'adx_threshold': 20, 'rsi_period': 14, 'rsi_overbought': 70, 'rsi_oversold': 30, 'volume_length_short': 14, 'volume_length_long': 50, 'volume_threshold': 1.0, 'atr_period': 14},
        'ETHUSDT': {'fast_period': 10, 'medium_period': 25, 'slow_period': 50, 'adx_period': 14, 'adx_threshold': 25, 'rsi_period': 14, 'rsi_overbought': 75, 'rsi_oversold': 35, 'volume_length_short': 14, 'volume_length_long': 50, 'volume_threshold': 1.2, 'atr_period': 14}, # Exemplo: parâmetros diferentes
        'SOLUSDT': {'fast_period': 5, 'medium_period': 15, 'slow_period': 30, 'adx_period': 14, 'adx_threshold': 15, 'rsi_period': 14, 'rsi_overbought': 65, 'rsi_oversold': 25, 'volume_length_short': 14, 'volume_length_long': 50, 'volume_threshold': 0.8, 'atr_period': 14}, # Exemplo: parâmetros diferentes
    }


    global LIMITE_KLINES
    LIMITE_KLINES = 0 # Reseta para recalcular com base nos requisitos das estratégias escolhidas

    for coin in MOEDAS_A_OPERAR:
        pair = f'{coin}{BASE_ASSET}'
        if pair not in pair_strategy_map:
            print(f"Aviso: Nenhuma estratégia definida explicitamente para a moeda {coin} ({pair}). Pulando este par.")
            enviar_telegram(f"⚠️ Bot: Nenhuma estratégia definida para {pair}. Pulando.")
            continue # Pula este par se nenhuma estratégia for mapeada

        pairs_to_process.append(pair)
        trading_state[pair] = {
            'strategy': None,
            'usdt_pool_revenue': 0.0, # Pool para acumular receita das vendas DESTE par
            'holding': False, # Estado inicial: não segurando (virtualmente)
            'quote_asset': coin, # Ex: 'BTC' em 'BTCUSDT'
            'symbol_details': get_symbol_details(pair), # Detalhes de precisão da Binance
            'buy_price': 0.0, # Preço da última compra para cálculo de P/L
        }

        # Instancia a estratégia correta para o par
        StrategyClass = pair_strategy_map[pair]
        params = filtered_strategy_params.get(pair, {}) # Pega parâmetros específicos ou um dicionário vazio
        try:
            # Passa o símbolo e os parâmetros (se houver) ao inicializar a estratégia
            trading_state[pair]['strategy'] = StrategyClass(symbol=pair, **params)
        except Exception as e:
            print(f"Erro ao instanciar estratégia para o par {pair}: {e}. Pulando.")
            enviar_telegram(f"❌ Bot: Erro ao instanciar estratégia para {pair}: {e}. Pulando.")
            del trading_state[pair] # Remove o par do estado se a estratégia falhar
            pairs_to_process.remove(pair)
            continue


        # Atualiza o LIMITE_KLINES global com o maior requisito entre todas as estratégias instanciadas com sucesso
        required = getattr(trading_state[pair]['strategy'], 'required_klines', 0)
        if required > LIMITE_KLINES:
            LIMITE_KLINES = required


    # Após instanciar todas as estratégias, verifica posições existentes
    pairs_to_check = list(trading_state.keys()) # Pares que tiveram a estratégia instanciada com sucesso

    print("Verificando posições existentes...")

    for pair in pairs_to_check:
        state = trading_state[pair]
        quote_asset = state['quote_asset']
        symbol_details = state['symbol_details']

        # Obter saldo real da moeda específica para verificar posição existente
        current_holding_balance = initial_balances.get(quote_asset, 0.0)

        # Verifica se há uma posição existente significativa na exchange
        # O critério 'min_quantity * 2' é um heuristic para evitar considerar poeira como posição
        is_significant_holding = (current_holding_balance > symbol_details['min_quantity'] * 2)


        if is_significant_holding:
            # Se há posição existente, o estado 'holding' é True.
            state['holding'] = True
            state['usdt_pool_revenue'] = 0.0 # Pool de receita começa zerada, pois capital está 'preso'
            # TODO: Opcional - tentar obter o preço médio de compra da posição existente da API Binance?
            # Isso é complexo, pode-se iniciar 'buy_price' como 0.0 ou tentar estimar.
            state['buy_price'] = 0.0 # Marca como desconhecido ou 0.0

            print(f"[{pair}] 💼 Posição existente detectada ({current_holding_balance:.{symbol_details['num_decimal_places']}f} {quote_asset}). Estado 'holding' = True.")
            enviar_telegram(f"⚠️ [{pair}] Posição existente detectada ({current_holding_balance:.{symbol_details['num_decimal_places']}f} {quote_asset}).")

        else:
            # Se não há posição existente, o estado 'holding' é False.
            state['holding'] = False
            state['usdt_pool_revenue'] = 0.0 # Pool de receita começa zerada
            state['buy_price'] = 0.0 # Sem posição, sem preço de compra


    # Se não há pares elegíveis, define LIMITE_KLINES para um valor mínimo seguro
    if not trading_state:
         LIMITE_KLINES = 50 # Um valor base se não houver estratégias válidas

    print(f"\n✅ Inicialização completa.")
    # Note: A alocação inicial para COMPRAS agora vem do saldo USDT LIVRE TOTAL na conta em cada iteração do loop principal.
    print(f"Configurado para obter {LIMITE_KLINES} klines brutos para o intervalo {INTERVALO_KLINES}.")
    print(f"Bot checará TODOS os pares a cada {CHECK_INTERVAL_SECONDS} segundos.")
    print(f"Pares a serem operados ({len(trading_state)}): {list(trading_state.keys())}")
    print(f"Montante ALVO por trade de compra: {TRADE_AMOUNT_USDT_TARGET:.2f} {BASE_ASSET} (limitado pelo saldo livre total e MIN_NOTIONAL).")

    enviar_telegram(f"🚀 Bot configurado.\nPares: {list(trading_state.keys())}\nIntervalo Klines: {INTERVALO_KLINES}\nChecagem: {CHECK_INTERVAL_SECONDS}s.\nKlines por checagem: {LIMITE_KLINES}.\nAlvo por compra: {TRADE_AMOUNT_USDT_TARGET:.2f} {BASE_ASSET}.")


# --- Modificar a função obter_klines para retornar dados brutos ---
def obter_klines(symbol, interval, limit):
    """Obtém os dados de klines (velas) brutos para um par, intervalo e limite definidos."""
    try:
        # print(f"[{symbol}] Obtendo {limit} klines para {interval}...") # Debug
        klines_data = client.get_klines(symbol=symbol, interval=interval, limit=limit)
        if not klines_data:
            print(f"[{symbol}] Aviso: get_klines retornou dados vazios para {interval}.")
            enviar_telegram(f"⚠️ [{symbol}] Aviso: dados klines vazios para {interval}.")
            return [] # Retorna lista vazia
        # Retorna a lista bruta de klines [ [ts, open, high, low, close, volume, ...], ... ]
        # print(f"[{symbol}] Klines obtidos: {len(klines_data)}") # Debug
        return klines_data
    except BinanceAPIException as e:
        print(f"[{symbol}] Erro da API ao obter klines ({interval}): {e}")
        enviar_telegram(f"❌ Erro ao obter klines para {symbol} ({interval}): {e.code}: {e.message}")
        return []
    except Exception as e:
        print(f"[{symbol}] Erro inesperado ao obter klines: {e}")
        enviar_telegram(f"❌ Erro inesperado ao obter klines: {e}")
        return []


def executar_bot():
    print("Bot Multi-Moeda iniciado.")
    enviar_telegram("🤖 Bot Multi-Moeda iniciado.")

    # Ajusta o tempo do servidor Binance
    ajustar_tempo()

    # Inicializa o estado de trading para todos os pares e configura estratégias
    initialize_trading_state()

    # Verifica se há algum par para operar após a inicialização
    if not trading_state:
         print("Nenhum par de trading válido configurado ou inicializado. Encerrando o bot.")
         enviar_telegram("❌ Bot encerrado: Nenhum par de trading válido configurado ou inicializado.")
         return # Sai da função se não há pares


    iteration_count = 0
    sleep_duration_seconds = CHECK_INTERVAL_SECONDS # O tempo de espera FIXO do loop principal

    try:
        while True:
            iteration_count += 1
            current_time_str = time.strftime('%Y-%m-%d %H:%M:%S')
            print(f"\n--- Iteração {iteration_count} ({current_time_str}) ---")

            # --- Obter todos os saldos no início de cada iteração ---
            # Isso garante que temos os saldos mais recentes antes de checar cada par
            all_balances = get_all_balances()
            current_total_usdt_free = all_balances.get(BASE_ASSET, 0.0) # Saldo USDT LIVRE TOTAL na conta
            print(f"Saldo {BASE_ASSET} Livre Total Atual: {current_total_usdt_free:.2f}")

            # A pool de revenue por par é apenas para rastrear a performance individual
            # O capital para COMPRAS agora vem do 'current_total_usdt_free'
            # total_usdt_in_revenue_pools = sum(state.get('usdt_pool_revenue', 0.0) for state in trading_state.values())
            # print(f"Total em pools de receita: {total_usdt_in_revenue_pools:.2f}") # Opcional: logar total nas pools


            # --- Loop através de cada par de trading configurado ---
            processed_count = 0 # Conta quantos pares foram processados nesta iteração
            buy_executed_in_this_iteration = False # Flag para garantir apenas 1 compra por iteração, se desejar

            # Itera sobre uma cópia das chaves caso algum par precise ser removido durante a execução (ex: erro persistente)
            for pair in list(trading_state.keys()):
                state = trading_state[pair]
                symbol = pair
                quote_asset = state['quote_asset']
                symbol_details = state['symbol_details']
                strategy_instance = state['strategy'] # Pega a instância da estratégia para este par

                processed_count += 1
                print(f"\n[{current_time_str}] Checando par: {symbol}")

                # Obtém saldos específicos para este par da lista completa obtida no início da iteração
                # Necessário para verificar o saldo REAL da moeda para vendas
                quote_asset_balance = all_balances.get(quote_asset, 0.0)

                # A pool de USDT específica para ACUMULAR RECEITA deste par
                usdt_pool_revenue_for_this_pair = state.get('usdt_pool_revenue', 0.0)


                # 1. Obter dados (klines brutos) para ESTE par
                klines_raw = obter_klines(symbol, INTERVALO_KLINES, LIMITE_KLINES)

                # Verifica se obteve klines suficientes para a estratégia deste par
                required_klines = getattr(strategy_instance, 'required_klines', 0)
                # Se não tem dados suficientes, não executa a estratégia para este par nesta iteração.
                # Isso dá tempo para a Binance acumular mais klines, especialmente no início.
                if not klines_raw or len(klines_raw) < required_klines:
                    print(f"[{symbol}] Dados de klines insuficientes ({len(klines_raw)}/{required_klines}). Pulando decisão para este par nesta iteração.")
                    # Continue para o próximo par na mesma iteração do loop principal.
                    if len(trading_state) > 1 and processed_count < len(trading_state): # Pequeno sleep se houver mais pares a processar
                         time.sleep(SLEEP_BETWEEN_PAIRS_MS / 1000.0)
                    continue # Pula o restante da lógica para este par


                # Obtém o preço atual (necessário para cálculo de notional e log)
                try:
                    ticker = client.get_symbol_ticker(symbol=symbol)
                    current_price = float(ticker['price'])
                except Exception as e:
                    print(f"[{symbol}] Erro ao obter ticker: {e}. Pulando decisão para este par.")
                    enviar_telegram(f"⚠️ [{symbol}] Erro ao obter ticker: {e}. Pulando decisão.")
                    if len(trading_state) > 1 and processed_count < len(trading_state):
                         time.sleep(SLEEP_BETWEEN_PAIRS_MS / 1000.0)
                    continue # Pula o restante da lógica para este par


                print(f"[{symbol}] Preço Atual: {current_price:.{symbol_details['price_decimal_places']}f} | Saldo REAL {quote_asset}: {quote_asset_balance:.{symbol_details['num_decimal_places']}f} | {BASE_ASSET} Pool Receita: {usdt_pool_revenue_for_this_pair:.2f} | Holding (Bot State): {state['holding']}")


                # 2. Chamar a estratégia *deste par* para decidir a ação
                # Passamos os klines brutos E o estado 'holding' gerenciado pelo bot
                action = strategy_instance.decide_action(symbol, klines_raw, state['holding'])


                # 3. Executar a Ação com base na decisão da estratégia e no estado do bot
                trade_executed = False # Flag para saber se uma ordem FOI executada por ESTE par nesta checagem


                # --- Lógica de EXECUÇÃO baseada na AÇÃO da Estratégia e no Estado do Bot ---

                # Se a estratégia sinalizou COMPRA ('BUY')
                if action == 'BUY':
                    # Se o bot NÃO está segurando (estado virtual 'holding' = False)
                    # E ainda não executou uma compra nesta iteração (para priorizar o primeiro sinal, opcional)
                    # E há capital USDT livre total suficiente para o mínimo nocional do par
                    # Note: A compra usa o capital USDT livre TOTAL disponível, não uma pool por par.
                    if not state['holding'] and not buy_executed_in_this_iteration and current_total_usdt_free >= symbol_details['min_notional']:
                        print(f"[{symbol}] 🔼 Estratégia recomendou COMPRA (Entrada Long). Tentando executar...")

                        # Define o montante a tentar gastar: alvo fixo ou saldo livre total, o que for menor
                        usdt_amount_to_spend = min(TRADE_AMOUNT_USDT_TARGET, current_total_usdt_free)

                        # Garante que o montante a gastar é pelo menos o mínimo nocional do par
                        # A função execute_buy_order já verifica isso, mas é bom garantir antes de chamar.
                        if usdt_amount_to_spend >= symbol_details['min_notional']:

                             qty, price = execute_buy_order(symbol, usdt_amount_to_spend, symbol_details, current_price)

                             if qty is not None and price is not None: # Se a ordem de compra foi executada com sucesso
                                 trade_executed = True
                                 buy_executed_in_this_iteration = True # Marca que uma compra foi feita NESTA iteração
                                 state['holding'] = True # Atualiza o estado do bot: agora está segurando
                                 # O capital foi gasto do saldo USDT livre TOTAL.
                                 # A pool de receita DESTE par (state['usdt_pool_revenue']) permanece inalterada (0.0 no início).
                                 state['buy_price'] = price # Registra o preço de compra
                                 print(f"[{symbol}] ✅ COMPRA Executada (Entrada Long).")
                                 # O saldo USDT livre total será atualizado na próxima iteração principal.
                                 # Telegram já é enviado dentro de execute_buy_order
                             else:
                                 # Ordem falhou na execução (API error, etc.). Log já feito na função de execução.
                                 pass # Não atualiza estado se a ordem falhou

                        else:
                            print(f"[{symbol}] Sinal de compra, mas saldo USDT livre total ({current_total_usdt_free:.2f}) menor que o mínimo nocional ({symbol_details['min_notional']:.2f}).")
                            enviar_telegram(f"⚠️ [{symbol}] Sinal de compra, mas saldo livre ({current_total_usdt_free:.2f} {BASE_ASSET}) < mín. nocional ({symbol_details['min_notional']:.2f}).")


                    # Se a estratégia sinalizou 'BUY' E o bot JÁ está segurando (holding=True)...
                    # Isso seria um sinal para SAIR de uma posição SHORT (se estivéssemos operando short).
                    # No modelo atual (apenas LONG), este sinal 'BUY' enquanto holding=True é ignorado.
                    pass # Ação 'BUY' enquanto holding Long é ignorada no modelo atual (sem shorting)


                # Se a estratégia sinalizou VENDA ('SELL')
                elif action == 'SELL':
                    # Se o bot ESTÁ segurando (estado virtual 'holding' = True)
                    # E o saldo REAL da moeda específica na conta é suficiente para vender o mínimo do par
                    if state['holding'] and quote_asset_balance >= symbol_details['min_quantity']:
                        print(f"[{symbol}] 🔽 Estratégia recomendou VENDA (Saída de Long). Tentando executar...")
                        # Executa a venda da quantidade TOTAL REAL disponível para este par (desde que > mínimo do par)
                        # A venda deve ser baseada no saldo REAL que você tem na conta para este ativo.
                        qty, price, revenue = execute_sell_order(symbol, quote_asset_balance, symbol_details, current_price)

                        if qty is not None and price is not None and revenue is not None: # Se a ordem de venda foi executada com sucesso
                            trade_executed = True # Marca que este par executou uma venda
                            state['holding'] = False # Atualiza o estado do bot: não está mais segurando
                            # A receita da venda (capital + lucro/prejuízo) retorna para a pool DESTE PAR (revenue pool)
                            state['usdt_pool_revenue'] += revenue
                            # Calcular e logar lucro/prejuízo da posição fechada
                            if state['buy_price'] > 0: # Verifica se tínhamos um preço de compra registrado da última compra
                                estimated_bought_value = qty * state['buy_price'] # Usa a quantidade REALMENTE vendida
                                profit_loss = revenue - estimated_bought_value
                                print(f"[{symbol}] 📊 Lucro/Prejuízo na posição fechada: {profit_loss:.2f} USDT.")
                                enviar_telegram(f"📊 P/L Fechado [{symbol}]: {profit_loss:.2f} {BASE_ASSET}.")
                            else:
                                 # Se o buy_price era 0 (posição existente inicial desconhecida), apenas loga a receita.
                                 print(f"[{symbol}] Posição fechada. Receita total: {revenue:.2f} USDT. Preço de compra desconhecido.")

                            state['buy_price'] = 0.0 # Reseta preço de compra após fechar posição
                            print(f"[{symbol}] ✅ VENDA Executada (Saída de Long). Pool Receita atualizada: {state['usdt_pool_revenue']:.2f}.")
                             # Telegram já é enviado dentro de execute_sell_order
                        else:
                            # Ordem de venda falhou na execução. Log já feito na função de execução.
                            pass # Não atualiza estado se a ordem falhou


                    # Se a estratégia sinalizou 'SELL' E o bot NÃO está segurando (holding=False)...
                    # Isso seria um sinal para ENTRAR SHORT.
                    # No modelo atual (apenas LONG), este sinal 'SELL' enquanto not holding é ignorado.
                    pass # Ação 'SELL' enquanto not holding Long é ignorada no modelo atual (sem shorting)


                elif action == 'HOLD':
                    # A estratégia recomendou HOLD. Não fazemos nada de trading para este par nesta iteração.
                    # O estado 'holding' e 'usdt_pool_revenue' permanecem inalterados por esta ação.
                    # print(f"[{symbol}] Estratégia recomendou HOLD.") # Opcional: logar HOLD
                    pass


                else:
                    print(f"[{symbol}] ⚠️ Aviso: Estratégia para {symbol} retornou ação inválida: {action}. Esperado 'BUY', 'SELL', ou 'HOLD'.")
                    enviar_telegram(f"[{symbol}] ⚠️ Aviso: Estratégia para {symbol} retornou ação inválida: {action}.")

                # Pequeno sleep entre processar um par e o próximo para não martelar a API
                # Só dorme se não foi o último par da lista nesta iteração
                if len(trading_state) > 1 and processed_count < len(trading_state):
                    time.sleep(SLEEP_BETWEEN_PAIRS_MS / 1000.0)


            # --- Fim do loop por pares NESTA iteração ---

            # A flag `buy_executed_in_this_iteration` controla se uma compra ocorreu em QUALQUER par nesta iteração.
            # Isso garante que o primeiro par que sinalizar 'BUY' (na ordem do loop) tem a chance de comprar.
            # Se você quiser permitir várias compras na mesma iteração (uma para cada par que sinalizar, se houver capital),
            # remova a flag `buy_executed_in_this_iteration` e suas verificações.


            # Espera o tempo definido em CHECK_INTERVAL_SECONDS antes da próxima iteração principal
            # onde todos os pares serão checados novamente.
            print(f"\n--- Fim da Iteração {iteration_count}. Aguardando {CHECK_INTERVAL_SECONDS} segundos para a próxima checagem completa. ---")
            time.sleep(CHECK_INTERVAL_SECONDS)


    except KeyboardInterrupt:
        print("\nBot encerrado pelo usuário.")
        enviar_telegram(f"🛑 Bot Multi-Moeda encerrado pelo usuário.")
    except Exception as e:
        print(f"\nErro inesperado no loop principal: {e}")
        enviar_telegram(f"⚠️ Erro inesperado no bot Multi-Moeda: {e}")


# --- A função obter_klines já foi modificada acima ---


if __name__ == "__main__":
    # A estratégia é instanciada DENTRO de initialize_trading_state para cada par
    # Os intervalos de checagem são definidos globalmente.

    executar_bot() # Começa a execução do bot multi-moeda