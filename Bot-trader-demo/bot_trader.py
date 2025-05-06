# bot_trader.py
import os
import time
import requests
import math
from dotenv import load_dotenv
from binance.client import Client
from binance.exceptions import BinanceAPIException

# Importar as estratégias
from strategies import (
    EmaThreeLinesCrossoverStrategy,
    EmaThreeLinesCrossoverStrategyETH, # Importe as estratégias para cada moeda
    EmaThreeLinesCrossoverStrategySOL, # Embora usem a mesma base agora, podem ser customizadas
    # Não precisamos mais dos tipos de atraso na importação principal
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
        print("Telegram não configurado. Mensagem não enviada.")

client = Client(API_KEY, API_SECRET)

# === Parâmetros Globais do Bot Multi-Moeda ===
# Intervalo dos Klines para a ESTRATÉGIA (aplicado a todos os pares)
INTERVALO_KLINES = Client.KLINE_INTERVAL_4HOUR # Renomeado para clareza


# Lista de moedas base que o bot irá operar (sempre contra USDT)
MOEDAS_A_OPERAR = ['BTC', 'ETH', 'SOL']
TRADING_PAIRS = [f'{coin}USDT' for coin in MOEDAS_A_OPERAR]
BASE_ASSET = 'USDT' # A moeda base para todas as negociações (dólar)


# --- Parâmetro de Frequência de Checagem ---
# Define com que frequência o bot irá verificar TODOS os pares
CHECK_INTERVAL_SECONDS = 5 * 60 # Checa a cada 5 minutos (ajuste conforme sua preferência)

# Pequeno sleep entre a checagem de um par e outro para não sobrecarregar a API (em milissegundos)
SLEEP_BETWEEN_PAIRS_MS = 500

# Mínimos gerais (serão ajustados pela precisão da Binance por par)
MIN_USDT_TRADE = 10.0 # Mínimo em USDT para uma ordem de compra (será ajustado pelo MIN_NOTIONAL)


# --- Estrutura para armazenar o estado de cada par ---
# ... (trading_state dictionary definition remains the same)
trading_state = {}

# LIMITE_KLINES será ajustado dinamicamente com base no maior requisito das estratégias
LIMITE_KLINES = 0


# --- Funções de Utilitários ---

# >>>>>>>>>> MOVA A DEFINIÇÃO DE ajustar_tempo PARA AQUI, FORA DE executar_bot <<<<<<<<<<
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

# >>>>>>>>>> FIM DA MOVIMENTAÇÃO <<<<<<<<<<


def get_symbol_details(symbol):
    # ... (função get_symbol_details permanece a mesma)
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
                if '.' in f['stepSize']:
                    details['num_decimal_places'] = len(f['stepSize'].split('.')[1])
                else:
                    details['num_decimal_places'] = 0
            elif f['filterType'] == 'PRICE_FILTER':
                details['price_tick_size'] = float(f['tickSize'])
                if '.' in f['tickSize']:
                    details['price_decimal_places'] = len(f['tickSize'].split('.')[1])
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
        details['quantity_step_size'] = 1e-8 # Fallback
        details['num_decimal_places'] = 8
        details['price_tick_size'] = 1e-2 # Fallback
        details['price_decimal_places'] = 2
        details['min_notional'] = 10.0 # Fallback
        details['min_quantity'] = 1e-8 # Fallback

    return details


def floor_to_precision(quantity, step_size, num_decimal_places):
    # ... (função floor_to_precision permanece a mesma)
    """Arredonda uma quantidade para baixo na precisão correta."""
    if step_size is None or step_size <= 0:
        print(f"Aviso: step_size inválido ({step_size}). Usando precisão padrão de {num_decimal_places} casas decimais.")
        factor = 10**num_decimal_places
        return math.floor(quantity * factor) / factor

    num_steps = math.floor(quantity / step_size)
    return num_steps * step_size


# --- Funções de Trading Genéricas ---

def execute_buy_order(symbol, usdt_amount_to_spend, symbol_details, current_price):
    # ... (função execute_buy_order permanece a mesma)
     """Executa uma ordem de compra a mercado usando um montante específico de USDT."""
     try:
         if usdt_amount_to_spend < symbol_details['min_notional']:
             print(f"[{symbol}] Montante USDT para compra ({usdt_amount_to_spend:.2f}) menor que o mínimo nocional ({symbol_details['min_notional']:.2f}). Cancelando.")
             return None, None # Não executa ordem

         quantidade_desejada = usdt_amount_to_spend / current_price
         quantidade_calculada = floor_to_precision(quantidade_desejada, symbol_details['quantity_step_size'], symbol_details['num_decimal_places'])

         if quantidade_calculada < symbol_details['min_quantity']:
              print(f"[{symbol}] Quantidade calculada ({quantidade_calculada:.{symbol_details['num_decimal_places']}f}) menor que o mínimo do par ({symbol_details['min_quantity']:.{symbol_details['num_decimal_places']}f}). Cancelando.")
              return None, None # Não executa ordem

         quantity_str = f"{quantidade_calculada:.{symbol_details['num_decimal_places']}f}"
         print(f"[{symbol}] Tentando comprar {quantity_str} com ~{usdt_amount_to_spend:.2f} USDT...")
         ordem = client.order_market_buy(symbol=symbol, quantity=quantity_str)
         print(f"[{symbol}] Ordem de compra enviada. ID: {ordem.get('orderId')}")

         filled_quantity = 0.0
         total_fill_price = 0.0
         fills = ordem.get('fills', [])
         if fills:
             for fill in fills:
                 qty = float(fill['qty'])
                 price = float(fill['price'])
                 filled_quantity += qty
                 total_fill_price += qty * price

             avg_price = total_fill_price / filled_quantity if filled_quantity > 0 else current_price
             print(f"[{symbol}] Ordem preenchida. Qtd: {filled_quantity:.{symbol_details['num_decimal_places']}f}, Preço Médio: {avg_price:.{symbol_details['price_decimal_places']}f}")
             return filled_quantity, avg_price

         else:
             print(f"[{symbol}] Aviso: Ordem de compra enviada, mas sem fills imediatos. Status: {ordem.get('status')}")
             return None, None

     except BinanceAPIException as e:
         print(f"[{symbol}] Erro ao comprar: {e.code}: {e.message}")
         enviar_telegram(f"❌ Falha na compra ({symbol}):\n{e.code}: {e.message}")
         return None, None
     except Exception as e:
         print(f"[{symbol}] Erro inesperado ao comprar: {e}")
         enviar_telegram(f"❌ Erro inesperado na compra ({symbol}):\n{e}")
         return None, None


def execute_sell_order(symbol, quantity_to_sell, symbol_details, current_price):
    # ... (função execute_sell_order permanece a mesma)
    """Executa uma ordem de venda a mercado usando uma quantidade específica da moeda."""
    try:
        quantity_calculated = floor_to_precision(quantity_to_sell, symbol_details['quantity_step_size'], symbol_details['num_decimal_places'])

        if quantity_calculated < symbol_details['min_quantity']:
             print(f"[{symbol}] Quantidade para venda ({quantity_calculated:.{symbol_details['num_decimal_places']}f}) menor que o mínimo do par ({symbol_details['min_quantity']:.{symbol_details['num_decimal_places']}f}). Cancelando.")
             return None, None, None

        estimated_notional = quantity_calculated * current_price
        if estimated_notional < symbol_details['min_notional']:
             print(f"[{symbol}] Venda estimada ({estimated_notional:.2f} USDT) menor que o mínimo nocional ({symbol_details['min_notional']:.2f}). Cancelando.")
             return None, None, None

        quantity_str = f"{quantity_calculated:.{symbol_details['num_decimal_places']}f}"
        print(f"[{symbol}] Tentando vender {quantity_str} {symbol}...")
        ordem = client.order_market_sell(symbol=symbol, quantity=quantity_str)
        print(f"[{symbol}] Ordem de venda enviada. ID: {ordem.get('orderId')}")

        filled_quantity = 0.0
        total_revenue = 0.0
        fills = ordem.get('fills', [])
        if fills:
            for fill in fills:
                qty = float(fill['qty'])
                price = float(fill['price'])
                filled_quantity += qty
                total_revenue += qty * price

            avg_price = total_revenue / filled_quantity if filled_quantity > 0 else current_price
            print(f"[{symbol}] Ordem preenchida. Qtd: {filled_quantity:.{symbol_details['num_decimal_places']}f}, Preço Médio: {avg_price:.{symbol_details['price_decimal_places']}f}, Receita: {total_revenue:.2f} USDT")
            return filled_quantity, avg_price, total_revenue

        else:
            print(f"[{symbol}] Aviso: Ordem de venda enviada, mas sem fills imediatos. Status: {ordem.get('status')}")
            return None, None, None

    except BinanceAPIException as e:
        print(f"[{symbol}] Erro ao vender: {e.code}: {e.message}")
        enviar_telegram(f"❌ Falha na venda ({symbol}):\n{e.code}: {e.message}")
        return None, None, None
    except Exception as e:
        print(f"[{symbol}] Erro inesperado ao vender: {e}")
        enviar_telegram(f"❌ Erro inesperado na venda ({symbol}):\n{e}")
        return None, None, None


def get_all_balances():
    # ... (função get_all_balances permanece a mesma)
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
         return balances # Retorna saldos iniciais (zero) em caso de erro


def initialize_trading_state():
    # ... (função initialize_trading_state permanece a mesma)
    """Inicializa a estrutura de estado para todos os pares de trading."""
    print("Inicializando estado de trading...")

    initial_balances = get_all_balances()
    total_initial_usdt = initial_balances.get(BASE_ASSET, 0.0)
    print(f"Saldo inicial total em {BASE_ASSET}: {total_initial_usdt:.2f}")

    pairs_to_process = []
    for coin in MOEDAS_A_OPERAR:
        pair = f'{coin}{BASE_ASSET}'
        pairs_to_process.append(pair)
        trading_state[pair] = {
            'strategy': None,
            'usdt_pool': 0.0,
            'holding': False,
            'quote_asset': coin,
            'symbol_details': get_symbol_details(pair),
            'buy_price': 0.0
        }

        if coin == 'BTC':
            trading_state[pair]['strategy'] = EmaThreeLinesCrossoverStrategy(pair, fast_period=7, medium_period=20, slow_period=40)
        elif coin == 'ETH':
             trading_state[pair]['strategy'] = EmaThreeLinesCrossoverStrategyETH(pair, fast_period=10, medium_period=25, slow_period=50)
        elif coin == 'SOL':
             trading_state[pair]['strategy'] = EmaThreeLinesCrossoverStrategySOL(pair, fast_period=5, medium_period=15, slow_period=30)
        else:
             print(f"Aviso: Nenhuma estratégia definida para a moeda {coin} ({pair}). Pulando.")
             del trading_state[pair]
             pairs_to_process.remove(pair)
             continue

        global LIMITE_KLINES
        required = getattr(trading_state[pair]['strategy'], 'required_klines', 0)
        if required > LIMITE_KLINES:
             LIMITE_KLINES = required + 10


    pairs_eligible_for_allocation = [p for p in pairs_to_process]
    num_eligible_pairs = len(pairs_eligible_for_allocation)
    initial_usdt_per_pool = total_initial_usdt / num_eligible_pairs if num_eligible_pairs > 0 else 0.0

    print("Verificando posições existentes e definindo alocação inicial nos pools...")
    for pair in pairs_eligible_for_allocation:
        quote_asset = trading_state[pair]['quote_asset']
        current_holding = initial_balances.get(quote_asset, 0.0)
        symbol_details = trading_state[pair]['symbol_details']

        is_significant_holding = (current_holding > symbol_details['min_quantity'] * 2)

        if is_significant_holding:
            trading_state[pair]['holding'] = True
            trading_state[pair]['usdt_pool'] = 0.0
            print(f"[{pair}] Posição existente detectada ({current_holding:.{symbol_details['num_decimal_places']}f} {quote_asset}). USDT pool inicial zero.")
            enviar_telegram(f"⚠️ [{pair}] Posição existente detectada ({current_holding:.{symbol_details['num_decimal_places']}f} {quote_asset}).")
            trading_state[pair]['buy_price'] = 0.0

        else:
            trading_state[pair]['holding'] = False
            allocated_usdt = max(initial_usdt_per_pool, symbol_details['min_notional'])
            trading_state[pair]['usdt_pool'] = min(allocated_usdt, total_initial_usdt)
            print(f"[{pair}] Sem posição existente. USDT pool inicial: {trading_state[pair]['usdt_pool']:.2f}.")


    print(f"Estado inicial de trading configurado para {len(trading_state)} pares.")
    print(f"Configurado para obter {LIMITE_KLINES} klines para o intervalo {INTERVALO_KLINES}.")
    print(f"Bot checará TODOS os pares a cada {CHECK_INTERVAL_SECONDS} segundos.")
    print(f"Pares a serem operados: {list(trading_state.keys())}")
    enviar_telegram(f"Bot configurado.\nPares: {list(trading_state.keys())}\nIntervalo Klines: {INTERVALO_KLINES}\nChecagem: {CHECK_INTERVAL_SECONDS}s.")


# --- Modificar a função obter_klines para aceitar symbol e interval ---
def obter_klines(symbol, interval, limit):
    # ... (função obter_klines permanece a mesma)
    """Obtém os dados de klines (velas) para um par, intervalo e limite definidos."""
    try:
        klines_data = client.get_klines(symbol=symbol, interval=interval, limit=limit)
        if not klines_data:
             print(f"[{symbol}] Aviso: get_klines retornou dados vazios para {interval}.")
             return []
        closing_prices = [float(k[4]) for k in klines_data]
        return closing_prices
    except BinanceAPIException as e:
        print(f"[{symbol}] Erro ao obter klines ({interval}): {e}")
        enviar_telegram(f"❌ Erro ao obter klines para {symbol} ({interval}): {e}")
        return []
    except Exception as e:
        print(f"[{symbol}] Erro inesperado ao obter klines: {e}")
        enviar_telegram(f"❌ Erro inesperado ao obter klines: {e}")
        return []


# >>>>>>>>>> A FUNÇÃO executar_bot COMEÇA AQUI <<<<<<<<<<
def executar_bot():
    print("Bot Multi-Moeda iniciado.")
    enviar_telegram("🤖 Bot Multi-Moeda iniciado.")

    # >>>>>>>>>> CHAMADA CORRETA PARA ajustar_tempo (AGORA DEFINIDA GLOBALMENTE) <<<<<<<<<<
    ajustar_tempo() # Ajusta o tempo do servidor Binance

    # Inicializa o estado de trading para todos os pares (inclui detalhes e estratégias)
    initialize_trading_state()


    iteration_count = 0

    # O bot checará todos os pares a cada CHECK_INTERVAL_SECONDS
    # A variável sleep_duration_seconds não é mais determinada pela estratégia,
    # ela é apenas o tempo de espera FIXO do loop principal.
    sleep_duration_seconds = CHECK_INTERVAL_SECONDS

    try:
        while True:
            iteration_count += 1
            current_time_str = time.strftime('%Y-%m-%d %H:%M:%S')
            print(f"\n--- Iteração {iteration_count} ({current_time_str}) ---")

            # --- Obter todos os saldos no início de cada iteração ---
            # Precisamos dos saldos atualizados para todas as moedas
            all_balances = get_all_balances()
            total_usdt_free = all_balances.get(BASE_ASSET, 0.0)
            print(f"Saldo USDT Livre Total: {total_usdt_free:.2f}")


            # --- Loop através de cada par de trading configurado ---
            processed_count = 0 # Conta quantos pares foram processados nesta iteração
            for pair in list(trading_state.keys()): # Iterar sobre uma cópia das chaves caso algum par seja removido
                state = trading_state[pair]
                symbol = pair
                quote_asset = state['quote_asset']
                symbol_details = state['symbol_details']


                processed_count += 1
                print(f"\n[{current_time_str}] Checando par: {symbol}")

                # Obter saldos específicos para este par da lista completa
                usdt_balance_available = all_balances.get(BASE_ASSET, 0.0) # Saldo USDT total disponível (poderia ser usado para um pool global opcional)
                quote_asset_balance = all_balances.get(quote_asset, 0.0) # Saldo da moeda específica (BTC, ETH, SOL)

                # A pool de USDT específica para este par é gerenciada na estrutura de estado
                usdt_pool_for_this_pair = state['usdt_pool']


                # 1. Obter dados (klines e preço atual) para ESTE par
                klines = obter_klines(symbol, INTERVALO_KLINES, LIMITE_KLINES)

                # Verifica se obteve klines suficientes para a estratégia deste par
                required_klines = getattr(state['strategy'], 'required_klines', 0)
                # Se não tem dados suficientes, não executa a estratégia para este par
                if not klines or len(klines) < required_klines:
                     print(f"[{symbol}] Dados de klines insuficientes ({len(klines)}/{required_klines}). Pulando decisão para este par nesta iteração.")
                     # Não atualiza o estado de EMA anteriores aqui, pois a estratégia não foi executada com dados completos.
                     # A estratégia retornaria HOLD de qualquer forma, mas pulamos para economizar recursos.
                     # Continue para o próximo par na mesma iteração do loop principal.
                     if len(trading_state) > 1 and processed_count < len(trading_state): # Pequeno sleep se houver mais pares a processar
                         time.sleep(SLEEP_BETWEEN_PAIRS_MS / 1000.0)
                     continue # Pula o restante da lógica para este par


                # Obtém o preço atual
                try:
                     ticker = client.get_symbol_ticker(symbol=symbol)
                     current_price = float(ticker['price'])
                except Exception as e:
                     print(f"[{symbol}] Erro ao obter ticker: {e}. Pulando decisão para este par.")
                     enviar_telegram(f"⚠️ [{symbol}] Erro ao obter ticker: {e}. Pulando decisão.")
                     if len(trading_state) > 1 and processed_count < len(trading_state): # Pequeno sleep se houver mais pares a processar
                         time.sleep(SLEEP_BETWEEN_PAIRS_MS / 1000.0)
                     continue # Pula o restante da lógica para este par


                print(f"[{symbol}] Preço: {current_price:.{symbol_details['price_decimal_places']}f} | Saldo {quote_asset}: {quote_asset_balance:.{symbol_details['num_decimal_places']}f} | Pool {BASE_ASSET}: {usdt_pool_for_this_pair:.2f} | Holding: {state['holding']}")


                # 2. Chamar a estratégia *deste par* para decidir a ação
                # Passamos apenas os dados do gráfico para a estratégia
                action = state['strategy'].decide_action(symbol, klines)


                # 3. Executar a Ação e Atualizar o Estado do Par (USANDO OS POOLS DEDICADOS)
                trade_executed = False # Flag para saber se uma ordem foi enviada
                executed_quantity = None
                executed_price = None
                executed_revenue = None

                # Para BUY, verificamos se NÃO está segurando E se a pool de USDT tem o mínimo
                if action == 'BUY':
                    # O saldo real de USDT não é relevante aqui, só a pool dedicada
                    if not state['holding'] and state['usdt_pool'] >= symbol_details['min_notional']:
                         print(f"[{symbol}] 🔼 Estratégia recomendou COMPRA.")
                         # Executa a compra usando TODO o USDT da pool DESTE PAR
                         qty, price = execute_buy_order(symbol, state['usdt_pool'], symbol_details, current_price)
                         if qty is not None and price is not None:
                             trade_executed = True
                             executed_quantity = qty
                             executed_price = price
                             state['holding'] = True # Agora está segurando
                             state['usdt_pool'] = 0.0 # A pool de USDT está vazia após a compra
                             state['buy_price'] = price # Registra o preço de compra para cálculo futuro
                             enviar_telegram(f"🎉 COMPRA Executada [{symbol}]: {executed_quantity:.{symbol_details['num_decimal_places']}f} @ {executed_price:.{symbol_details['price_decimal_places']}f}. Pool {state['usdt_pool']:.2f}.") # Mostra a pool zerada


                    # else:
                         # print(f"[{symbol}] Sinal de compra, mas já está segurando ({state['holding']}) ou USDT pool insuficiente ({state['usdt_pool']:.2f} < {symbol_details['min_notional']:.2f}).")


                # Para SELL, verificamos se ESTÁ segurando (virtualmente) E se o saldo REAL da moeda é maior que o mínimo do par
                elif action == 'SELL':
                    # Só vendemos se estivermos "virtualmente" segurando (state['holding']) E tivermos saldo real > mínimo do par.
                    # O saldo real é o que está na exchange.
                    if state['holding'] and quote_asset_balance >= symbol_details['min_quantity']:
                         print(f"[{symbol}] 🔽 Estratégia recomendou VENDA.")
                         # Executa a venda da quantidade TOTAL REAL disponível para este par (desde que > mínimo)
                         qty, price, revenue = execute_sell_order(symbol, quote_asset_balance, symbol_details, current_price)

                         if qty is not None and price is not None and revenue is not None:
                             trade_executed = True
                             executed_quantity = qty
                             executed_price = price
                             executed_revenue = revenue # Receita total da venda
                             state['holding'] = False # Não está mais segurando virtualmente
                             # A receita da venda (lucro ou prejuízo) retorna para a pool DESTE PAR
                             state['usdt_pool'] += revenue
                             # Opcional: calcular e logar lucro explícito da última posição fechada
                             if state['buy_price'] > 0: # Verifica se tínhamos um preço de compra registrado da última compra
                                 estimated_bought_value = executed_quantity * state['buy_price']
                                 profit_loss = revenue - estimated_bought_value
                                 print(f"[{symbol}] Lucro/Prejuízo na posição fechada: {profit_loss:.2f} USDT.")
                                 enviar_telegram(f"📊 P/L Fechado [{symbol}]: {profit_loss:.2f} USDT. Pool {state['usdt_pool']:.2f}.")

                             state['buy_price'] = 0.0 # Reseta preço de compra
                             enviar_telegram(f"📉 VENDA Executada [{symbol}]: {executed_quantity:.{symbol_details['num_decimal_places']}f} @ {executed_price:.{symbol_details['price_decimal_places']}f}. Pool {state['usdt_pool']:.2f} USDT.")

                    # else:
                         # print(f"[{symbol}] Sinal de venda, mas não está segurando virtualmente ({state['holding']}) ou saldo real insuficiente ({quote_asset_balance:.{symbol_details['num_decimal_places']}f} < {symbol_details['min_quantity']:.{symbol_details['num_decimal_places']}f}).")


                elif action == 'HOLD':
                     # A estratégia recomendou HOLD. Não faz nada de trading para este par.
                     pass


                else:
                     print(f"[{symbol}] ⚠️ Aviso: Estratégia retornou ação inválida: {action}")
                     enviar_telegram(f"[{symbol}] ⚠️ Aviso: Estratégia para {symbol} retornou ação inválida: {action}")


                # Pequeno sleep entre processar um par e o próximo para não martelar a API
                if len(trading_state) > 1 and processed_count < len(trading_state): # Não dorme se for o último par ou só tiver 1
                     time.sleep(SLEEP_BETWEEN_PAIRS_MS / 1000.0)


            # --- Fim do loop por pares ---

            # Espera o tempo definido em CHECK_INTERVAL_SECONDS antes da próxima iteração principal
            # onde todos os pares serão checados novamente.
            print(f"\n--- Fim da Iteração {iteration_count}. Aguardando {CHECK_INTERVAL_SECONDS} segundos para a próxima checagem completa. ---")
            time.sleep(CHECK_INTERVAL_SECONDS)


    except KeyboardInterrupt:
        print("Bot encerrado pelo usuário.")
        enviar_telegram(f"🛑 Bot Multi-Moeda encerrado pelo usuário.")
    except Exception as e:
        print(f"Erro inesperado no loop principal: {e}")
        enviar_telegram(f"⚠️ Erro inesperado no bot Multi-Moeda: {e}")


# --- Modificar a função obter_klines para aceitar symbol e interval ---
# Já estava assim na versão anterior.
def obter_klines(symbol, interval, limit):
    """Obtém os dados de klines (velas) para um par, intervalo e limite definidos."""
    try:
        klines_data = client.get_klines(symbol=symbol, interval=interval, limit=limit)
        if not klines_data:
             print(f"[{symbol}] Aviso: get_klines retornou dados vazios para {interval}.")
             return []
        closing_prices = [float(k[4]) for k in klines_data]
        return closing_prices
    except BinanceAPIException as e:
        print(f"[{symbol}] Erro ao obter klines ({interval}): {e}")
        enviar_telegram(f"❌ Erro ao obter klines para {symbol} ({interval}): {e}")
        return []
    except Exception as e:
        print(f"[{symbol}] Erro inesperado ao obter klines: {e}")
        enviar_telegram(f"❌ Erro inesperado ao obter klines: {e}")
        return []


if __name__ == "__main__":
    # A estratégia é instanciada DENTRO de initialize_trading_state para cada par
    # Os intervalos de checagem são definidos globalmente.

    executar_bot() # Começa a execução do bot multi-moeda