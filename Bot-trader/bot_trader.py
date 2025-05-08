# bot_trader.py
import os
import time
import requests
import math
import pandas as pd

from dotenv import load_dotenv
from binance.client import Client
from binance.exceptions import BinanceAPIException

from strategies import (
    TradingStrategy,
    EmaThreeLinesCrossoverStrategy,
    EmaThreeLinesCrossoverStrategyETH,
    EmaThreeLinesCrossoverStrategySOL,
    FilteredEmaCrossoverStrategy,
)

load_dotenv()
API_KEY = os.getenv('API_KEY')
API_SECRET = os.getenv('API_SECRET')

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
        pass

client = Client(API_KEY, API_SECRET)

# === Parâmetros Globais ===
INTERVALO_KLINES = Client.KLINE_INTERVAL_2HOUR

ORIGINAL_MOEDAS_A_OPERAR = ['BTC', 'ETH', 'SOL']

BASE_ASSET = 'USDT'

ACTIVE_MOEDAS_STR = os.getenv('ACTIVE_MOEDAS')

MOEDAS_A_OPERAR = []
if ACTIVE_MOEDAS_STR is not None:
    requested_active_moedas = [coin.strip().upper() for coin in ACTIVE_MOEDAS_STR.split(',') if coin.strip()]
    print(f"Requisição de moedas ativas via .env: {requested_active_moedas}")

    if requested_active_moedas:
        for coin in requested_active_moedas:
            if coin in ORIGINAL_MOEDAS_A_OPERAR:
                MOEDAS_A_OPERAR.append(coin)
            else:
                print(f"Aviso: Moeda '{coin}' solicitada em ACTIVE_MOEDAS não está na lista de moedas suportadas ({ORIGINAL_MOEDAS_A_OPERAR}). Ignorando.")
                enviar_telegram(f"⚠️ Bot: Moeda '{coin}' solicitada em ACTIVE_MOEDAS não suportada. Ignorando.")
        if not MOEDAS_A_OPERAR:
            print("Erro: Nenhuma moeda ativa válida foi especificada em ACTIVE_MOEDAS ou as solicitadas não são suportadas. O bot não irá operar nenhum par.")
            enviar_telegram("❌ Bot: Nenhuma moeda ativa válida especificada em ACTIVE_MOEDAS. Encerrando.")
    else:
         print("Variável ACTIVE_MOEDAS definida no .env, mas a lista está vazia. O bot não irá operar nenhum par.")
         enviar_telegram(f"⚠️ Bot: Variável ACTIVE_MOEDAS definida, mas vazia. Nenhum par será operado.")

else:
    print("Variável ACTIVE_MOEDAS não definida no .env. Operando em todas as moedas suportadas.")
    MOEDAS_A_OPERAR = ORIGINAL_MOEDAS_A_OPERAR.copy()

if not MOEDAS_A_OPERAR:
    print("Lista final de MOEDAS_A_OPERAR está vazia. Bot não irá operar.")
    TRADING_PAIRS = []
else:
    BASE_ASSET = 'USDT'
    TRADING_PAIRS = [f'{coin}{BASE_ASSET}' for coin in MOEDAS_A_OPERAR]

# --- Parâmetros de Alocação de Capital (POOL POR MOEDA) ---
# O capital AGORA é alocado inicialmente para cada moeda em initialize_trading_state.
# O valor para cada trade de COMPRA é o saldo NA POOL DAQUELA MOEDA.
# TRADE_AMOUNT_USDT_TARGET = 15.0 # Não é mais o alvo fixo por trade.

# --- Parâmetros de Frequência de Checagem ---
CHECK_INTERVAL_SECONDS = 5 * 60 # Checa a cada 5 minutos
SLEEP_BETWEEN_PAIRS_MS = 500 # Pequeno sleep entre pares

# Mínimos gerais
MIN_USDT_TRADE = 10.0 # Mínimo em USDT para uma ordem de compra (será ajustado pelo MIN_NOTIONAL obtido da Binance)

# --- Estrutura para armazenar o estado de cada par ---
trading_state = {}

# LIMITE_KLINES será ajustado dinamicamente
LIMITE_KLINES = 0

# --- Funções de Utilitários ---

def ajustar_tempo():
    """Ajusta o timestamp do cliente Binance com o servidor."""
    try:
        server_time = client.get_server_time()
        local_time = int(time.time() * 1000)
        time_diff = server_time['serverTime'] - local_time
        client.timestamp_offset = time_diff
        print(f"Ajuste de tempo calculado e aplicado: {time_diff} ms")
        if abs(time_diff) > 1000:
            enviar_telegram(f"⏰ Sincronização de tempo: {time_diff}ms de diferença.")
    except Exception as e:
        print(f"Erro ao ajustar o tempo: {e}")
        enviar_telegram(f"❌ Erro ao ajustar o tempo: {e}")

def get_symbol_details(symbol):
    """Obtém detalhes de precisão e filtros para um dado par."""
    details = {
        'quantity_step_size': None, 'num_decimal_places': 8,
        'price_tick_size': None, 'price_decimal_places': 8,
        'min_notional': 0.0, 'min_quantity': 0.0,
    }
    try:
        symbol_info = client.get_symbol_info(symbol)
        for f in symbol_info['filters']:
            if f['filterType'] == 'LOT_SIZE':
                details['quantity_step_size'] = float(f['stepSize'])
                details['min_quantity'] = float(f['minQty'])
                step_str = str(details['quantity_step_size'])
                if '.' in step_str:
                    details['num_decimal_places'] = len(step_str.split('.')[1].rstrip('0'))
                else:
                    details['num_decimal_places'] = 0
            elif f['filterType'] == 'PRICE_FILTER':
                details['price_tick_size'] = float(f['tickSize'])
                tick_str = str(details['price_tick_size'])
                if '.' in tick_str:
                    details['price_decimal_places'] = len(tick_str.split('.')[1].rstrip('0'))
                else:
                    details['price_decimal_places'] = 0
            elif f['filterType'] == 'MIN_NOTIONAL':
                details['min_notional'] = float(f['minNotional'])

        global MIN_USDT_TRADE
        if details['min_notional'] > MIN_USDT_TRADE:
             MIN_USDT_TRADE = details['min_notional']

    except Exception as e:
        print(f"Erro ao obter detalhes para o par {symbol}: {e}")
        enviar_telegram(f"❌ Erro ao obter detalhes para {symbol}: {e}")
        details['quantity_step_size'] = 1e-8; details['num_decimal_places'] = 8
        details['price_tick_size'] = 1e-2; details['price_decimal_places'] = 2
        details['min_notional'] = 10.0; details['min_quantity'] = 1e-8
    return details

def floor_to_precision(quantity, step_size, num_decimal_places):
    """Arredonda uma quantidade para baixo na precisão correta."""
    if step_size is None or step_size <= 0:
        print(f"Aviso: step_size inválido ({step_size}). Usando precisão padrão de {num_decimal_places} casas decimais para arredondar {quantity}.")
        factor = 10**num_decimal_places
        return math.floor(quantity * factor) / factor
    num_steps = math.floor(quantity / step_size)
    rounded_quantity = num_steps * step_size
    return float(f'{rounded_quantity:.{num_decimal_places}f}')

# --- Funções de Trading Genéricas ---

def execute_buy_order(symbol, usdt_amount_to_spend, symbol_details, current_price):
    """Executa uma ordem de compra a mercado usando um montante específico de USDT."""
    try:
        if usdt_amount_to_spend < symbol_details['min_notional']:
             print(f"[{symbol}] Aviso interno: Montante USDT para compra ({usdt_amount_to_spend:.2f}) menor que o mínimo nocional ({symbol_details['min_notional']:.2f}) recebido pela função. Isso deveria ter sido tratado antes.")
             enviar_telegram(f"⚠️ [{symbol}] Aviso interno: Compra cancelada na execução: Montante ({usdt_amount_to_spend:.2f} {BASE_ASSET}) < mín. nocional ({symbol_details['min_notional']:.2f}).")
             return None, None

        quantidade_desejada = usdt_amount_to_spend / current_price
        quantidade_calculada = floor_to_precision(quantidade_desejada, symbol_details['quantity_step_size'], symbol_details['num_decimal_places'])
        if quantidade_calculada < symbol_details['min_quantity']:
             print(f"[{symbol}] Quantidade calculada ({quantidade_calculada:.{symbol_details['num_decimal_places']}f}) menor que o mínimo do par ({symbol_details['min_quantity']:.{symbol_details['min_quantity']}f}). Cancelando.")
             enviar_telegram(f"⚠️ [{symbol}] Compra cancelada: Qtd ({quantidade_calculada:.{symbol_details['num_decimal_places']}f}) < mín. do par ({symbol_details['min_quantity']:.{symbol_details['min_quantity']}f}).")
             return None, None
        quantity_str = f"{quantidade_calculada:.{symbol_details['num_decimal_places']}f}".rstrip('0').rstrip('.')

        print(f"[{symbol}] Tentando COMPRAR {quantity_str} com ~{usdt_amount_to_spend:.2f} USDT...")
        enviar_telegram(f"⏳ [{symbol}] Tentando COMPRAR {quantity_str} com ~{usdt_amount_to_spend:.2f} {BASE_ASSET}...")

        ordem = client.order_market_buy(symbol=symbol, quantity=quantity_str)
        print(f"[{symbol}] Ordem de compra enviada. ID: {ordem.get('orderId')}, Status: {ordem.get('status')}")

        filled_quantity = 0.0; total_fill_price = 0.0
        fills = ordem.get('fills', [])
        if fills:
            for fill in fills:
                qty = float(fill['qty']); price = float(fill['price'])
                filled_quantity += qty; total_fill_price += qty * price

            avg_price = total_fill_price / filled_quantity if filled_quantity > 0 else current_price
            print(f"[{symbol}] Ordem preenchida. Qtd: {filled_quantity:.{symbol_details['num_decimal_places']}f}, Preço Médio: {avg_price:.{symbol_details['price_decimal_places']}f}")
            print(f"[{symbol}] ✅ COMPRA Executada (Entrada Long).")
            enviar_telegram(f"✅ COMPRA Executada [{symbol}]: {filled_quantity:.{symbol_details['num_decimal_places']}f} @ {avg_price:.{symbol_details['price_decimal_places']}f} (Gasto: {filled_quantity * avg_price:.2f} {BASE_ASSET}).")
            return filled_quantity, avg_price
        else:
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
        quantity_calculated = floor_to_precision(quantity_to_sell, symbol_details['quantity_step_size'], symbol_details['num_decimal_places'])
        if quantity_calculated < symbol_details['min_quantity']:
             print(f"[{symbol}] Quantidade para venda ({quantity_calculated:.{symbol_details['num_decimal_places']}f}) menor que o mínimo do par ({symbol_details['min_quantity']:.{symbol_details['min_quantity']}f}). Cancelando.")
             enviar_telegram(f"⚠️ [{symbol}] Venda cancelada: Qtd ({quantity_calculated:.{symbol_details['num_decimal_places']}f}) < mín. do par ({symbol_details['min_quantity']:.{symbol_details['min_quantity']}f}).")
             return None, None, None
        estimated_notional = quantity_calculated * current_price
        if estimated_notional < symbol_details['min_notional']:
             print(f"[{symbol}] Venda estimada ({estimated_notional:.2f} USDT) menor que o mínimo nocional ({symbol_details['min_notional']:.2f}). Cancelando.")
             enviar_telegram(f"⚠️ [{symbol}] Venda cancelada: Estimativa ({estimated_notional:.2f} {BASE_ASSET}) < mín. nocional ({symbol_details['min_notional']:.2f}).")
             return None, None, None

        quantity_str = f"{quantity_calculated:.{symbol_details['num_decimal_places']}f}".rstrip('0').rstrip('.')

        print(f"[{symbol}] Tentando VENDER {quantity_str} {symbol}...")
        enviar_telegram(f"⏳ [{symbol}] Tentando VENDER {quantity_str} {symbol}...")

        ordem = client.order_market_sell(symbol=symbol, quantity=quantity_str)
        print(f"[{symbol}] Ordem de venda enviada. ID: {ordem.get('orderId')}, Status: {ordem.get('status')}")

        filled_quantity = 0.0; total_revenue = 0.0
        fills = ordem.get('fills', [])
        if fills:
            for fill in fills:
                qty = float(fill['qty']); price = float(fill['price'])
                filled_quantity += qty; total_revenue += qty * price

            avg_price = total_revenue / filled_quantity if filled_quantity > 0 else current_price
            print(f"[{symbol}] Ordem preenchida. Qtd: {filled_quantity:.{symbol_details['num_decimal_places']}f}, Preço Médio: {avg_price:.{symbol_details['price_decimal_places']}f}, Receita: {total_revenue:.2f} USDT")
            print(f"[{symbol}] ✅ VENDA Executada (Saída de Long). Pool Receita atualizada: {total_revenue:.2f}.")
            enviar_telegram(f"✅ VENDA Executada [{symbol}]: {filled_quantity:.{symbol_details['num_decimal_places']}f} @ {avg_price:.{symbol_details['price_decimal_places']}f} (Receita: {total_revenue:.2f} {BASE_ASSET}).")
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
        account_info = client.get_account()
        for balance in account_info['balances']:
            asset = balance['asset']
            if asset == BASE_ASSET or asset in MOEDAS_A_OPERAR:
                 balances[asset] = float(balance['free'])
        return balances
    except Exception as e:
        print(f"Erro ao obter todos os saldos: {e}")
        enviar_telegram(f"❌ Erro ao obter todos os saldos: {e}")
        fallback_balances = {BASE_ASSET: 0.0}
        for coin in MOEDAS_A_OPERAR:
             fallback_balances[coin] = 0.0
        return fallback_balances

def obter_klines(symbol, interval, limit):
    """Obtém os dados de klines (velas) brutos para um par, intervalo e limite definidos."""
    try:
        klines_data = client.get_klines(symbol=symbol, interval=interval, limit=limit)
        if not klines_data:
            print(f"[{symbol}] Aviso: get_klines retornou dados vazios para {interval}.")
            enviar_telegram(f"⚠️ [{symbol}] Aviso: dados klines vazios para {interval}.")
            return []
        return klines_data
    except BinanceAPIException as e:
        print(f"[{symbol}] Erro da API ao obter klines ({interval}): {e}")
        enviar_telegram(f"❌ Erro ao obter klines para {symbol} ({interval}): {e.code}: {e.message}")
        return []
    except Exception as e:
        print(f"[{symbol}] Erro inesperado ao obter klines: {e}")
        enviar_telegram(f"❌ Erro inesperado ao obter klines: {e}")
        return []


def initialize_trading_state():
    print("Inicializando estado de trading para pares ativos...")
    # print("DEBUG: Dentro de initialize_trading_state.") # REMOVIDO DEBUG

    # print("DEBUG: Antes de obter saldos iniciais.") # REMOVIDO DEBUG
    initial_balances = get_all_balances()
    # print("DEBUG: Após obter saldos iniciais.") # REMOVIDO DEBUG
    total_initial_usdt = initial_balances.get(BASE_ASSET, 0.0)

    num_active_pairs_to_configure = len(TRADING_PAIRS)
    if num_active_pairs_to_configure > 0:
        initial_usdt_per_pair = total_initial_usdt / num_active_pairs_to_configure
        print(f"Capital inicial total na Exchange: {total_initial_usdt:.2f} {BASE_ASSET}. Dividindo conceitualmente entre {num_active_pairs_to_configure} par(es) ativo(s).")
        print(f"Capital inicial conceitual alocado POR PAR: {initial_usdt_per_pair:.2f} {BASE_ASSET}.")
        enviar_telegram(f"Bot: Saldo {BASE_ASSET} Livre Inicial Exchange: {total_initial_usdt:.2f}.\nAlocação inicial conceitual POR PAR: {initial_usdt_per_pair:.2f} {BASE_ASSET} para {num_active_pairs_to_configure} par(es) ativo(s): {TRADING_PAIRS}.")
    else:
        initial_usdt_per_pair = 0.0
        enviar_telegram(f"Bot: Saldo {BASE_ASSET} Livre Inicial Exchange: {total_initial_usdt:.2f}.\nNenhum par ativo configurado para alocar capital.")


    pair_strategy_map = {
        'BTCUSDT': FilteredEmaCrossoverStrategy,
        'ETHUSDT': FilteredEmaCrossoverStrategy,
        'SOLUSDT': FilteredEmaCrossoverStrategy,
    }

    filtered_strategy_params = {
        'BTCUSDT': {'fast_period': 7, 'medium_period': 20, 'slow_period': 40, 'rsi_period': 14, 'rsi_overbought': 70, 'rsi_oversold': 30, 'volume_length_short': 14, 'volume_length_long': 50, 'volume_threshold': 1.0},
        'ETHUSDT': {'fast_period': 10, 'medium_period': 25, 'slow_period': 50, 'rsi_period': 14, 'rsi_overbought': 70, 'rsi_oversold': 30, 'volume_length_short': 14, 'volume_length_long': 50, 'volume_threshold': 1.0},
        'SOLUSDT': {'fast_period': 5, 'medium_period': 15, 'slow_period': 30, 'rsi_period': 14, 'rsi_overbought': 70, 'rsi_oversold': 30, 'volume_length_short': 14, 'volume_length_long': 50, 'volume_threshold': 1.0},
    }
    simple_strategy_params = {
        'ETHUSDT': {'fast_period': 10, 'medium_period': 25, 'slow_period': 50},
        'SOLUSDT': {'fast_period': 5, 'medium_period': 15, 'slow_period': 30},
    }

    # print("DEBUG: Antes de loop de configuração de pares.") # REMOVIDO DEBUG
    global LIMITE_KLINES
    LIMITE_KLINES = 0

    for pair in TRADING_PAIRS:
        # print(f"DEBUG: Configurando par: {pair}") # REMOVIDO DEBUG
        coin = pair.replace(BASE_ASSET, '')

        if pair not in pair_strategy_map:
             print(f"Aviso: Nenhuma estratégia definida explicitamente para o par ativo {pair}. Pulando na inicialização.")
             enviar_telegram(f"⚠️ Bot: Nenhuma estratégia definida para o par ativo {pair}. Pulando na inicialização.")
             continue

        trading_state[pair] = {
            'strategy': None,
            'usdt_pool_revenue': initial_usdt_per_pair if num_active_pairs_to_configure > 0 else 0.0,
            'holding': False,
            'quote_asset': coin,
            'symbol_details': get_symbol_details(pair),
            'buy_price': 0.0,
        }

        StrategyClass = pair_strategy_map[pair]
        if StrategyClass == FilteredEmaCrossoverStrategy:
             params = filtered_strategy_params.get(pair, {})
        elif StrategyClass == EmaThreeLinesCrossoverStrategy or issubclass(StrategyClass, EmaThreeLinesCrossoverStrategy):
             params = simple_strategy_params.get(pair, {})
        else:
             params = {}

        # print(f"DEBUG: Instanciando estratégia para {pair} com params: {params}") # REMOVIDO DEBUG
        try:
            trading_state[pair]['strategy'] = StrategyClass(symbol=pair, **params)
            # print(f"DEBUG: Estratégia instanciada com sucesso para {pair}") # REMOVIDO DEBUG
        except Exception as e:
            # print(f"DEBUG: Erro durante instanciação da estratégia para {pair}: {e}") # REMOVIDO DEBUG
            print(f"Erro ao instanciar estratégia para o par ativo {pair}: {e}. Removendo dos pares ativos.")
            enviar_telegram(f"❌ Bot: Erro ao instanciar estratégia para o par ativo {pair}: {e}. Removendo.")
            del trading_state[pair]
            print(f"[{pair}] Capital alocado conceitualmente a este par ({initial_usdt_per_pair:.2f} {BASE_ASSET}) não será operado devido à falha na estratégia.")
            enviar_telegram(f"⚠️ [{pair}] Capital alocado ({initial_usdt_per_pair:.2f} {BASE_ASSET}) não será operado devido à falha na estratégia.")


        if pair in trading_state and trading_state[pair]['strategy'] is not None:
             required = getattr(trading_state[pair]['strategy'], 'required_klines', 0)
             if required > LIMITE_KLINES:
                  LIMITE_KLINES = required

    # print("DEBUG: Após loop de configuração de pares.") # REMOVIDO DEBUG
    pairs_to_check = list(trading_state.keys())

    print("Verificando posições existentes para pares ativos configurados...")
    # print("DEBUG: Antes do loop de verificação de posições existentes.") # REMOVIDO DEBUG

    for pair in pairs_to_check:
        # print(f"DEBUG: Verificando posição para: {pair}") # REMOVIDO DEBUG
        state = trading_state[pair]
        quote_asset = state['quote_asset']
        symbol_details = state['symbol_details']

        current_holding_balance = initial_balances.get(quote_asset, 0.0)

        is_significant_holding = (current_holding_balance > symbol_details['min_quantity'] * 2)

        if is_significant_holding:
            # print(f"DEBUG: Posição significativa encontrada para {pair}.") # REMOVIDO DEBUG
            try:
                 # print(f"DEBUG: Obtendo ticker para estimar posição existente para {pair}") # REMOVIDO DEBUG
                 ticker = client.get_symbol_ticker(symbol=pair)
                 current_price_at_init = float(ticker['price'])
                 estimated_position_value = current_holding_balance * current_price_at_init
                 state['usdt_pool_revenue'] = estimated_position_value
                 print(f"[{pair}] 💼 Posição existente detectada ({current_holding_balance:.{symbol_details['num_decimal_places']}f} {quote_asset}). Estimativa de valor: {estimated_position_value:.2f} {BASE_ASSET}. Pool inicializada com este valor.")
                 enviar_telegram(f"⚠️ [{pair}] Posição existente detectada ({current_holding_balance:.{symbol_details['num_decimal_places']}f} {quote_asset}). Pool inicializada com ~{estimated_position_value:.2f} {BASE_ASSET} (estimado).")

            except Exception as e:
                 # print(f"DEBUG: Erro ao estimar posição existente para {pair}: {e}") # REMOVIDO DEBUG
                 print(f"[{pair}] ⚠️ Erro ao estimar valor de posição existente ({current_holding_balance:.{symbol_details['num_decimal_places']}f} {quote_asset}) para inicializar a pool: {e}. Mantendo alocação inicial calculada ({state['usdt_pool_revenue']:.2f}).")
                 enviar_telegram(f"⚠️ [{pair}] Erro ao estimar valor de posição existente. Mantendo alocação inicial calculada ({state['usdt_pool_revenue']:.2f}).")

            state['holding'] = True
            state['buy_price'] = 0.0


        else:
            # print(f"DEBUG: Nenhuma posição significativa encontrada para {pair}. Pool mantém alocação inicial ou zero.") # REMOVIDO DEBUG
            state['holding'] = False
            state['buy_price'] = 0.0

    # print("DEBUG: Após loop de verificação de posições existentes.") # REMOVIDO DEBUG
    if not trading_state:
         LIMITE_KLINES = 50
         print("Aviso: Nenhum par ativo com estratégia válida após a inicialização.")

    print(f"\n✅ Inicialização completa.")
    print(f"Pares ATIVOS CONFIGURADOS ({len(trading_state)}): {list(trading_state.keys()) if trading_state else 'Nenhum'}")
    print(f"Configurado para obter {LIMITE_KLINES} klines brutos para o intervalo {INTERVALO_KLINES}.")
    print(f"Bot checará TODOS os pares ATIVOS CONFIGURADOS a cada {CHECK_INTERVAL_SECONDS} segundos.")


def executar_bot():
    # NOVO: Envia mensagem de bot iniciado via Telegram logo no início
    enviar_telegram("🤖 Bot Multi-Moeda iniciado.") # Adicionado Telegram de início simples
    print("Bot Multi-Moeda iniciado.") # Loga no console

    # print("DEBUG: Antes de ajustar tempo.") # REMOVIDO DEBUG
    ajustar_tempo()
    # print("DEBUG: Após ajustar tempo.") # REMOVIDO DEBUG
    # print("DEBUG: Antes de chamar initialize_trading_state().") # REMOVIDO DEBUG
    initialize_trading_state()
    # print("DEBUG: Após chamar initialize_trading_state().") # REMOVIDO DEBUG

    if not trading_state:
        print("Nenhum par de trading ATIVO configurado ou inicializado com sucesso. Encerrando o bot.")
        solicitadas = os.getenv('ACTIVE_MOEDAS')
        msg_solicitadas = solicitadas if solicitadas is not None else 'Todas (ACTIVE_MOEDAS não definido)'
        pares_ativos_solicitados = TRADING_PAIRS if 'TRADING_PAIRS' in globals() and TRADING_PAIRS else 'Nenhum par ativo na lista inicial'
        enviar_telegram(f"❌ Bot encerrado: Nenhum par de trading ATIVO configurado ou inicializado com sucesso.\nSolicitadas via .env: {msg_solicitadas}\nSuportadas pelo código (ORIGINAL_MOEDAS_A_OPERAR): {ORIGINAL_MOEDAS_A_OPERAR}\nPares Ativos SOLICITADOS: {pares_ativos_solicitados}.\nPares ATIVOS CONFIGURADOS com Sucesso: {list(trading_state.keys())}.")
        return


    iteration_count = 0
    # sleep_duration_seconds = CHECK_INTERVAL_SECONDS # Já definido globalmente

    # print("DEBUG: Entrando no loop principal.") # REMOVIDO DEBUG
    try:
        while True:
            iteration_count += 1
            current_time_str = time.strftime('%Y-%m-%d %H:%M:%S')
            print(f"\n--- Iteração {iteration_count} ({current_time_str}) ---")
            # print("DEBUG: Início da iteração do loop principal.") # REMOVIDO DEBUG

            # print("DEBUG: Obtendo saldos atuais.") # REMOVIDO DEBUG
            all_balances = get_all_balances()
            # print("DEBUG: Saldos atuais obtidos.") # REMOVIDO DEBUG
            current_total_usdt_free_on_exchange = all_balances.get(BASE_ASSET, 0.0)
            print(f"Saldo {BASE_ASSET} Livre Total na Exchange: {current_total_usdt_free_on_exchange:.2f}")

            # O saldo na pool de cada moeda (state['usdt_pool_revenue']) é o capital CONCEITUAL ALOCADO/DISPONÍVEL PARA COMPRAR AQUELA moeda.

            processed_count = 0
            buy_executed_in_this_iteration = False

            # print("DEBUG: Antes do loop de checagem de pares ativos.") # REMOVIDO DEBUG
            for pair in list(trading_state.keys()):
                 # print(f"DEBUG: Checando par ativo configurado: {pair}") # REMOVIDO DEBUG
                 state = trading_state[pair]
                 symbol = pair
                 quote_asset = state['quote_asset']
                 symbol_details = state['symbol_details']
                 strategy_instance = state['strategy']

                 processed_count += 1
                 print(f"\n[{current_time_str}] Checando par ativo configurado: {symbol}")

                 quote_asset_balance_on_exchange = all_balances.get(quote_asset, 0.0)
                 usdt_pool_available_for_buy = state.get('usdt_pool_revenue', 0.0)

                 # print(f"DEBUG: Obtendo klines para {symbol}") # REMOVIDO DEBUG
                 klines_raw = obter_klines(symbol, INTERVALO_KLINES, LIMITE_KLINES)
                 # print(f"DEBUG: Klines obtidos ({len(klines_raw)}) para {symbol}") # REMOVIDO DEBUG


                 required_klines = getattr(strategy_instance, 'required_klines', 0)
                 if not klines_raw or len(klines_raw) < required_klines:
                     print(f"[{symbol}] Dados de klines insuficientes ({len(klines_raw)}/{required_klines}). Pulando decisão para este par ATIVO nesta iteração.")
                     if len(trading_state) > 1 and processed_count < len(trading_state):
                          time.sleep(SLEEP_BETWEEN_PAIRS_MS / 1000.0) # Corrigido typo SLEEP_BETWEEN_PAIRS_MS
                     continue

                 # print(f"DEBUG: Obtendo ticker para {symbol}") # REMOVIDO DEBUG
                 try:
                     ticker = client.get_symbol_ticker(symbol=symbol)
                     current_price = float(ticker['price'])
                     # print(f"DEBUG: Ticker obtido para {symbol}") # REMOVIDO DEBUG
                 except Exception as e:
                     # print(f"DEBUG: Erro ao obter ticker para {symbol}: {e}") # REMOVIDO DEBUG
                     print(f"[{symbol}] Erro ao obter ticker: {e}. Pulando decisão para este par ATIVO.")
                     enviar_telegram(f"⚠️ [{symbol}] Erro ao obter ticker: {e}. Pulando decisão.")
                     if len(trading_state) > 1 and processed_count < len(trading_state):
                          time.sleep(SLEEP_BETWEEN_PAIRS_MS / 1000.0)
                     continue

                 print(f"[{symbol}] Preço Atual: {current_price:.{symbol_details['price_decimal_places']}f} | Saldo REAL {quote_asset}: {quote_asset_balance_on_exchange:.{symbol_details['num_decimal_places']}f} | {BASE_ASSET} Pool Alocada: {usdt_pool_available_for_buy:.2f} | Holding (Bot State): {state['holding']}")

                 # print(f"DEBUG: Chamando decide_action para {symbol}") # REMOVIDO DEBUG
                 action = strategy_instance.decide_action(symbol, klines_raw, state['holding'])
                 # print(f"DEBUG: decide_action retornou {action} para {symbol}") # REMOVIDO DEBUG


                 trade_executed = False

                 if action == 'BUY':
                     if not state['holding']:
                         amount_to_spend_from_pool = usdt_pool_available_for_buy

                         if amount_to_spend_from_pool > 0:
                              if amount_to_spend_from_pool >= symbol_details['min_notional']:
                                   print(f"[{symbol}] 🔼 Estratégia recomendou COMPRA (Entrada Long). Capital disponível na pool: {amount_to_spend_from_pool:.2f} {BASE_ASSET}. Tentando executar...")
                                   # print(f"DEBUG: Chamando execute_buy_order para {symbol}") # REMOVIDO DEBUG
                                   qty, price = execute_buy_order(symbol, amount_to_spend_from_pool, symbol_details, current_price)
                                   # print(f"DEBUG: execute_buy_order retornou {qty}, {price} para {symbol}") # REMOVIDO DEBUG

                                   if qty is not None and price is not None:
                                       trade_executed = True
                                       buy_executed_in_this_iteration = True
                                       state['holding'] = True
                                       state['buy_price'] = price
                                       state['usdt_pool_revenue'] = 0.0
                                   else:
                                       pass

                              else:
                                  print(f"[{symbol}] Sinal de compra, mas pool alocada ({amount_to_spend_from_pool:.2f} {BASE_ASSET}) é menor que o mínimo nocional ({symbol_details['min_notional']:.2f}). Não tentando comprar.")
                                  enviar_telegram(f"⚠️ [{symbol}] Sinal de compra, mas pool alocada ({amount_to_spend_from_pool:.2f} {BASE_ASSET}) < mín. nocional ({symbol_details['min_notional']:.2f}). Não tentando comprar.")
                         else:
                             print(f"[{symbol}] Sinal de compra, mas pool alocada para esta moeda ({amount_to_spend_from_pool:.2f} {BASE_ASSET}) é zero ou negativa. Não tentando comprar.")


                 elif action == 'SELL':
                     if state['holding']:
                         quantity_to_sell = quote_asset_balance_on_exchange

                         try:
                             ticker_pre_sell = client.get_symbol_ticker(symbol=symbol)
                             current_price_pre_sell = float(ticker_pre_sell['price'])
                             # print(f"DEBUG: Ticker pré-venda obtido para {symbol}") # REMOVIDO DEBUG
                         except Exception as e:
                             # print(f"DEBUG: Erro ao obter ticker pré-venda para {symbol}: {e}") # REMOVIDO DEBUG
                             print(f"[{symbol}] ⚠️ Erro ao obter ticker pré-venda: {e}. Pulando tentativa de venda.")
                             enviar_telegram(f"⚠️ [{symbol}] Erro ao obter ticker pré-venda: {e}. Pulando tentativa de venda.")
                             continue

                         estimated_notional_pre_sell = quantity_to_sell * current_price_pre_sell

                         if quantity_to_sell >= symbol_details['min_quantity'] and estimated_notional_pre_sell >= symbol_details['min_notional']:

                             print(f"[{symbol}] 🔽 Estratégia recomendou VENDA (Saída de Long). Saldo REAL disponível: {quantity_to_sell:.{symbol_details['num_decimal_places']}f} {quote_asset}. Tentando executar...")
                             # print(f"DEBUG: Chamando execute_sell_order para {symbol}") # REMOVIDO DEBUG
                             qty_sold, price_sold, revenue = execute_sell_order(symbol, quantity_to_sell, symbol_details, current_price_pre_sell)
                             # print(f"DEBUG: execute_sell_order retornou {qty_sold}, {price_sold}, {revenue} para {symbol}") # REMOVIDO DEBUG

                             if qty_sold is not None and price_sold is not None and revenue is not None:
                                 trade_executed = True
                                 state['holding'] = False
                                 state['usdt_pool_revenue'] = revenue
                                 if state['buy_price'] > 0:
                                     estimated_bought_cost_of_sold_qty = qty_sold * state['buy_price']
                                     profit_loss = revenue - estimated_bought_cost_of_sold_qty
                                     print(f"[{symbol}] 📊 Lucro/Prejuízo na posição fechada: {profit_loss:.2f} USDT.")
                                     enviar_telegram(f"📊 P/L Fechado [{symbol}]: {profit_loss:.2f} {BASE_ASSET}. Capital na pool agora: {state['usdt_pool_revenue']:.2f}.")
                                 else:
                                     print(f"[{symbol}] Posição fechada. Receita total: {revenue:.2f} USDT. Capital na pool agora: {state['usdt_pool_revenue']:.2f}. Preço de compra desconhecido.")
                                     enviar_telegram(f"✅ VENDA Executada [{symbol}]. Capital na pool agora: {state['usdt_pool_revenue']:.2f} {BASE_ASSET}. Preço de compra desconhecido.")

                                 state['buy_price'] = 0.0
                             else:
                                 pass

                         else:
                             if quantity_to_sell < symbol_details['min_quantity']:
                                 print(f"[{symbol}] Sinal de venda, mas saldo REAL insuficiente ({quantity_to_sell:.{symbol_details['num_decimal_places']}f} {quote_asset}) ou abaixo do mínimo do par ({symbol_details['min_quantity']:.{symbol_details['min_decimal_places']}f}). Não tentando vender.")
                                 enviar_telegram(f"⚠️ [{symbol}] Sinal de venda, mas saldo REAL ({quantity_to_sell:.{symbol_details['num_decimal_places']}f}) < mín. do par ({symbol_details['min_quantity']:.{symbol_details['min_decimal_places']}f}). Não tentando vender.")
                             elif estimated_notional_pre_sell < symbol_details['min_notional']:
                                  print(f"[{symbol}] Sinal de venda, mas valor nocional estimado ATUAL do saldo REAL ({estimated_notional_pre_sell:.2f} USDT) é menor que o mínimo nocional ({symbol_details['min_notional']:.2f}). Não tentando vender.")
                                  enviar_telegram(f"⚠️ [{symbol}] Sinal de venda, mas valor nocional estimado ATUAL ({estimated_notional_pre_sell:.2f} {BASE_ASSET}) < mín. nocional ({symbol_details['min_notional']:.2f}). Não tentando vender.")

                 elif action == 'HOLD':
                     pass

                 else:
                     print(f"[{symbol}] ⚠️ Aviso: Estratégia para {symbol} retornou ação inválida: {action}. Esperado 'BUY', 'SELL', ou 'HOLD'.")
                     enviar_telegram(f"[{symbol}] ⚠️ Aviso: Estratégia para {symbol} retornou ação inválida: {action}.")

                 if len(trading_state) > 1 and processed_count < len(trading_state):
                      time.sleep(SLEEP_BETWEEN_PAIRS_MS / 1000.0) # Corrigido typo SLEEP_BETWEEN_PAIRS_MS

            # print("DEBUG: Fim do loop de checagem de pares ativos.") # REMOVIDO DEBUG

            print(f"\n--- Fim da Iteração {iteration_count}. Aguardando {CHECK_INTERVAL_SECONDS} segundos para a próxima checagem completa. ---")
            time.sleep(CHECK_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print("\nBot encerrado pelo usuário.")
        enviar_telegram(f"🛑 Bot Multi-Moeda encerrado pelo usuário.")
    except Exception as e:
        print(f"\nErro inesperado no loop principal: {e}")
        enviar_telegram(f"⚠️ Erro inesperado no bot Multi-Moeda: {e}")


if __name__ == "__main__":
    executar_bot()
