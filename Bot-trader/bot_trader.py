# bot_trader.py (Com Stop-Loss, Seleção de Estratégia Flexível e Correção Multi-Coin)
import os
import time
import requests
import math
import pandas as pd
import traceback
import threading
import asyncio
import numpy as np # Para tratar NaN/Inf se necessário
from dotenv import load_dotenv

# --- Carregamento Inicial ---
script_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(script_dir, '.env')
if os.path.exists(dotenv_path):
    print(f"INFO: Carregando variáveis de ambiente de: {dotenv_path}")
    load_dotenv(dotenv_path)
else:
    print(f"ALERTA: Arquivo .env não encontrado em {dotenv_path}.")

# --- Imports de Bibliotecas Externas ---
try:
    from binance.client import Client
    from binance.exceptions import BinanceAPIException
    from telegram import Update
    from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters as tg_filters
except ImportError as e:
    print(f"ERRO CRÍTICO: Dependência não encontrada: {e}. Verifique a instalação.")
    print("Execute: pip install python-binance python-dotenv requests pandas python-telegram-bot>=20.0")
    exit(1)

# --- Imports Locais (do seu projeto) ---
try:
    # Certifique-se que o arquivo strategies.py está acessível
    from strategies import (
        TradingStrategy, AdvancedEmaRsiAdxStrategy, FilteredEmaCrossoverStrategy,
        PureEmaStrategy, CombinedEmaRsiVolumeStrategy # Adicione outras classes de estratégia aqui
    )
except ImportError as e:
    print(f"ERRO CRÍTICO: Não foi possível importar de strategies.py: {e}")
    print("Verifique se o arquivo strategies.py está no mesmo diretório e não contém erros de sintaxe.")
    exit(1)

# === Variáveis de Ambiente Carregadas ===
API_KEY = os.getenv('API_KEY')
API_SECRET = os.getenv('API_SECRET')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID_FALLBACK = os.getenv('TELEGRAM_CHAT_ID_FALLBACK')

if not API_KEY or not API_SECRET:
    print("ERRO CRÍTICO: API_KEY ou API_SECRET não encontradas. Verifique o arquivo .env ou as variáveis de ambiente.")
    exit(1)

# === Parâmetros Globais e Configurações ===
# --- AJUSTE ESTES PARÂMETROS ---
INTERVALO_KLINES = Client.KLINE_INTERVAL_2HOUR # Ex: 15m, 1h, 4h, etc. **AJUSTE!**
BASE_ASSET = 'USDT' # Moeda base para cotação e saldo
CHECK_INTERVAL_SECONDS = 60 # Intervalo (segundos) entre checagens completas
SLEEP_BETWEEN_PAIRS_MS = 300 # Pausa (ms) entre processar pares diferentes (evita rate limit)
MIN_USDT_TRADE_FALLBACK = 10.0 # Valor mínimo nocional (USDT) - verificar regras atuais da Binance
MOEDAS_SUPORTADAS = ['BTC', 'ETH', 'SOL'] # Moedas que o bot *pode* operar - **AJUSTE!**
PERCENTUAL_STOP_LOSS = 0.05 # Stop loss: 0.05 = 5%, 0.1 = 10%. **Use 0 para desativar**. **AJUSTE!**
DEFAULT_STRATEGY_CLASS = CombinedEmaRsiVolumeStrategy # Estratégia padrão se não especificada abaixo

# --- Configure a ESTRATÉGIA e PARÂMETROS para cada PAR ---
# Use a CLASSE da estratégia importada de strategies.py
STRATEGY_CONFIG = {
    "BTCUSDT": AdvancedEmaRsiAdxStrategy,
    "ETHUSDT": CombinedEmaRsiVolumeStrategy,
    "SOLUSDT": FilteredEmaCrossoverStrategy,
    # "ADAUSDT": PureEmaStrategy, # Exemplo
    # Adicione outros pares... Se não listado, usará DEFAULT_STRATEGY_CLASS
}

# PARÂMETROS para cada CLASSE de estratégia. Chave é o NOME DA CLASSE.
# Certifique-se que os parâmetros correspondem aos esperados pelo __init__ da classe.
STRATEGY_PARAMS_CONFIG = {
    "AdvancedEmaRsiAdxStrategy": {
        'fast_ema_period': 10, 'medium_ema_period': 21, 'slow_ema_period': 50,
        'rsi_period': 14, 'rsi_overbought': 70, 'rsi_oversold': 30, # Ajustado exemplo
        'adx_period': 14, 'adx_trend_threshold': 23 # Ajustado exemplo
    },
    "FilteredEmaCrossoverStrategy": {
        'fast_period': 7, 'medium_period': 20, 'slow_period': 40,
        'rsi_period': 14, 'rsi_overbought': 75, 'rsi_oversold': 25,
        'volume_length_short': 10, 'volume_length_long': 30, 'volume_threshold': 1.2 # Ajustado exemplo
    },
    "PureEmaStrategy": {
        'fast_period': 9, 'medium_period': 21, 'slow_period': 55 # Ajustado exemplo
    },
    "CombinedEmaRsiVolumeStrategy": { # Para a estratégia padrão ou se usada explicitamente
        'fast_period': 12, 'medium_period': 26, 'slow_period': 50, # Ajustado exemplo
        'rsi_period': 14, 'rsi_overbought': 70,
        'volume_length_short': 14, 'volume_length_long': 50, 'volume_threshold': 1.0
    }
    # Adicione outras classes e seus parâmetros...
}
# --- FIM DOS AJUSTES ---

# Variáveis de estado internas (não precisam ser alteradas manualmente)
MOEDAS_A_OPERAR = []
TRADING_PAIRS = []
trading_state = {}
LIMITE_KLINES = 0
OPERATING_MODE = "manual_allocation" # Será definido pelo usuário
discovered_chat_id = None
CHAT_ID_FILE = os.path.join(script_dir, "telegram_chat_id.txt")
telegram_application_instance = None # Para referência se necessário parar

# --- Conexão Inicial com Binance ---
try:
    client = Client(API_KEY, API_SECRET)
    client.ping()
    print("INFO: Conexão com a API Binance OK.")
except BinanceAPIException as e:
    print(f"ERRO CRÍTICO Conexão Binance: {e.code} - {e.message}")
    exit(1)
except Exception as e:
    print(f"ERRO CRÍTICO Conexão Binance (Geral): {e}")
    exit(1)

# --- Funções Telegram (mantidas como antes, com pequenos ajustes) ---
def carregar_chat_id_salvo():
    global discovered_chat_id
    if os.path.exists(CHAT_ID_FILE):
        try:
            with open(CHAT_ID_FILE, "r") as f:
                stored_id = f.read().strip()
                if stored_id:
                    discovered_chat_id = int(stored_id)
                    print(f"INFO: Chat ID {discovered_chat_id} carregado de {CHAT_ID_FILE}")
        except Exception as e:
            print(f"WARN: Não foi possível carregar chat_id do arquivo: {e}")

async def start_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global discovered_chat_id
    user = update.effective_user # Usar effective_user é mais robusto
    chat_id = update.effective_chat.id
    user_name = user.first_name if user else "Usuário"

    # Lock para evitar condição de corrida se múltiplos /start chegarem quase juntos
    # (Implementação simples, pode precisar de lock mais robusto em cenários complexos)
    lock_file = CHAT_ID_FILE + ".lock"
    if os.path.exists(lock_file):
         print(f"INFO: /start recebido enquanto outro está sendo processado. Ignorando chat {chat_id}.")
         await update.message.reply_text("🔄 Processando um comando anterior, tente novamente em alguns segundos.")
         return

    try:
        # Cria o lock
        with open(lock_file, 'w') as lf: lf.write(str(os.getpid()))

        # Recarrega o chat_id salvo DENTRO do lock para garantir valor mais recente
        carregar_chat_id_salvo()
        current_chat_id_in_memory = discovered_chat_id

        if current_chat_id_in_memory is None:
            discovered_chat_id = chat_id
            print(f"INFO: Primeiro /start de {user_name} (ID: {user.id if user else 'N/A'}, Chat: {chat_id}). Notificações configuradas.")
            try:
                with open(CHAT_ID_FILE, "w") as f: f.write(str(chat_id))
                print(f"INFO: Chat ID {chat_id} salvo em {CHAT_ID_FILE}")
                await update.message.reply_text(f"Olá {user_name}! 👍 Notificações ATIVADAS para este chat (ID: {chat_id}).")
            except Exception as e:
                print(f"WARN: Não foi possível salvar chat_id: {e}")
                await update.message.reply_text(f"Olá {user_name}! 👍 Notificações ATIVADAS (ID: {chat_id}), mas não salvei p/ próxima vez.")
        elif current_chat_id_in_memory == chat_id:
            print(f"INFO: /start do chat já configurado: {user_name} (Chat: {chat_id}).")
            await update.message.reply_text(f"Olá {user_name}! Notificações já estão ativas para este chat (ID: {chat_id}).")
        else:
            other_info = f"{user_name} (ID: {user.id if user else 'N/A'}, Chat: {chat_id})"
            print(f"WARN: /start de outro chat ({other_info}) quando já config p/ {current_chat_id_in_memory}. Ignorado.")
            await update.message.reply_text(f"⚠️ Bot já configurado para enviar notificações apenas para o chat ID {current_chat_id_in_memory}.")
            if TELEGRAM_TOKEN: enviar_telegram(f"⚠️ Tentativa de /start bloqueada do chat {chat_id}. Notificações continuam para {current_chat_id_in_memory}.")

    finally:
         # Remove o lock
         if os.path.exists(lock_file): os.remove(lock_file)


async def error_handler_telegram(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log de erros do Telegram."""
    print(f"--- ERRO TELEGRAM (async) ---")
    print(f"Update: {update}")
    # Erros comuns como TimedOut ou NetworkError podem ser tratados de forma mais leve
    if isinstance(context.error, (requests.exceptions.Timeout, requests.exceptions.ConnectionError)):
         print(f"Erro de Rede/Timeout Telegram: {context.error}")
    else:
         print(f"Erro: {context.error}")
         traceback.print_exception(type(context.error), context.error, context.error.__traceback__)
    print(f"--- FIM ERRO TELEGRAM ---")
    # Considerar enviar uma notificação sobre erros persistentes

def enviar_telegram(mensagem: str):
    """Envia mensagem para o chat_id configurado."""
    global discovered_chat_id
    chat_id_to_use = discovered_chat_id or TELEGRAM_CHAT_ID_FALLBACK
    if TELEGRAM_TOKEN and chat_id_to_use:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        # Limita tamanho da mensagem (Telegram tem limite por volta de 4096)
        max_len = 4000
        mensagem_trunc = (mensagem[:max_len] + '...') if len(mensagem) > max_len else mensagem
        payload = {"chat_id": str(chat_id_to_use), "text": f"[BOT] {mensagem_trunc}"}
        try:
             response = requests.post(url, json=payload, timeout=10) # Timeout um pouco maior
             if response.status_code >= 400: # Erros do cliente ou servidor
                 print(f"WARN: Erro ao enviar Telegram HTTP {response.status_code} para {chat_id_to_use}: {response.text}")
                 # Erros comuns: 400 (bad request, chat_id errado?), 403 (bot bloqueado?), 429 (too many requests)
                 if response.status_code == 403: print("WARN: Bot pode ter sido bloqueado pelo usuário no Telegram.")
                 if response.status_code == 429: print("WARN: Rate limit do Telegram atingido. Diminuir frequência de mensagens.")
        except requests.exceptions.Timeout:
            print(f"WARN: Timeout ao enviar para Telegram ({chat_id_to_use}). Mensagem perdida.")
        except requests.exceptions.RequestException as e:
            print(f"WARN: Erro de rede ao enviar para Telegram ({chat_id_to_use}): {e}")
        except Exception as e:
            print(f"WARN: Erro inesperado ao enviar para Telegram ({chat_id_to_use}): {e}")
    elif not TELEGRAM_TOKEN: pass
    elif not chat_id_to_use:
        print("WARN: Telegram não enviado. Chat ID não definido (use /start ou configure TELEGRAM_CHAT_ID_FALLBACK).")

# --- Funções Utilitárias Binance e Lógica ---
def ajustar_tempo():
    """Sincroniza o tempo com o servidor da Binance."""
    try:
        server_time = client.get_server_time()['serverTime']
        local_time = int(time.time() * 1000)
        client.timestamp_offset = server_time - local_time
        offset_abs = abs(client.timestamp_offset)
        print(f"INFO: Ajuste de tempo com servidor Binance: {client.timestamp_offset} ms")
        if offset_abs > 5000: # 5 segundos de dessincronia
            msg = f"⏰ ALERTA CRÍTICO: Relógio dessincronizado por {client.timestamp_offset}ms! SINCRONIZE O RELÓGIO DO SISTEMA URGENTE!"
            print(msg); enviar_telegram(msg)
        elif offset_abs > 1000: # 1 segundo
            msg = f"⏰ ALERTA: Relógio dessincronizado por {client.timestamp_offset}ms. Considere sincronizar."
            print(msg); enviar_telegram(msg)
    except BinanceAPIException as e:
        print(f"ERRO API ao ajustar tempo: {e.code} - {e.message}"); enviar_telegram(f"❌ Erro API ajustar tempo: {e.code}")
    except Exception as e:
        print(f"ERRO ao ajustar tempo: {e}"); enviar_telegram(f"❌ Erro ajustar tempo: {e}")

# Substitua a função inteira no bot_trader.py
def get_symbol_details(symbol: str) -> dict:
    """Busca detalhes atualizados do símbolo da Binance."""
    defaults = {'quantity_step_size': 1e-8, 'num_decimal_places': 8, 'price_tick_size': 1e-8, 'price_decimal_places': 8, 'min_notional': MIN_USDT_TRADE_FALLBACK, 'min_quantity': 1e-8 }
    try:
        info = client.get_symbol_info(symbol)
        if not info: print(f"WARN: Sem info da API para {symbol}. Usando defaults."); return defaults
        details = defaults.copy()
        details['min_notional'] = MIN_USDT_TRADE_FALLBACK
        for f in info.get('filters', []):
            ft = f.get('filterType')
            try:
                if ft == 'LOT_SIZE':
                    step_size_str = f['stepSize']
                    details['quantity_step_size'] = float(step_size_str)
                    details['min_quantity'] = float(f['minQty'])
                    # Calcula decimais direto da string step_size
                    if '.' in step_size_str:
                         details['num_decimal_places'] = len(step_size_str.split('.')[-1].rstrip('0'))
                    else:
                         details['num_decimal_places'] = 0 # Inteiro
                elif ft == 'PRICE_FILTER':
                    tick_size_str = f['tickSize']
                    details['price_tick_size'] = float(tick_size_str)
                    # Calcula decimais direto da string tick_size
                    if '.' in tick_size_str:
                        details['price_decimal_places'] = len(tick_size_str.split('.')[-1].rstrip('0'))
                    else:
                        details['price_decimal_places'] = 0 # Inteiro
                elif ft in ['NOTIONAL', 'MIN_NOTIONAL']:
                    details['min_notional'] = max(details['min_notional'], float(f.get('minNotional', details['min_notional'])))
            except (KeyError, ValueError, TypeError) as e: print(f"WARN [{symbol}] Erro processar filtro {ft}: {e}")
        if details['min_notional'] <= 0: details['min_notional'] = 1.0 # Segurança
        return details
    except BinanceAPIException as e: print(f"ERRO API detalhes {symbol}: {e.code}-{e.message}"); return defaults
    except Exception as e: print(f"ERRO obter detalhes {symbol}: {e}"); return defaults

def floor_to_precision(quantity: float, step_size: float, num_decimal_places: int) -> float:
    """Ajusta a quantidade para baixo de acordo com o step_size e formata."""
    if step_size <= 0: factor = 10 ** max(0, num_decimal_places); return math.floor(quantity * factor) / factor
    adjusted_quantity = math.floor(quantity / step_size) * step_size
    try: return float(f'{adjusted_quantity:.{max(0, num_decimal_places)}f}')
    except ValueError: print(f"WARN: Erro formatar floor_to_precision qty={quantity}"); return adjusted_quantity

def obter_klines(symbol: str, interval: str, limit: int) -> list:
    """Obtém klines da Binance com retentativas."""
    max_retries, initial_delay = 3, 5
    for attempt in range(max_retries):
        try:
            api_limit = min(limit, 1000)
            data = client.get_klines(symbol=symbol, interval=interval, limit=api_limit)
            # print(f"DEBUG [{symbol}] Klines obtidos: {len(data)} velas.")
            return data if data else []
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as net_err:
            print(f"WARN [{symbol}] Timeout/Conexão Kline (Tentativa {attempt + 1}/{max_retries}): {net_err}")
            if attempt < max_retries - 1: time.sleep(initial_delay * (2 ** attempt))
            else: print(f"ERRO [{symbol}] Falha klines rede."); enviar_telegram(f"❌ [{symbol}] Falha klines (Rede)."); return []
        except BinanceAPIException as api_err:
            print(f"ERRO API [{symbol}] klines: {api_err.code}-{api_err.message}"); enviar_telegram(f"❌ [{symbol}] Erro API Klines: {api_err.code}-{api_err.message}"); return []
        except Exception as general_err:
            print(f"ERRO [{symbol}] klines (Geral): {general_err}")
            if attempt < max_retries - 1: time.sleep(initial_delay * (2 ** attempt))
            else: print(f"ERRO [{symbol}] Falha klines geral."); enviar_telegram(f"❌ [{symbol}] Falha klines (Geral)."); return []
    return []

def execute_buy_order(symbol: str, usdt_amount: float, details: dict, current_price_estimate: float):
    """Executa uma ordem de compra a mercado, retornando (filled_qty, avg_price) ou (None, None)."""
    try:
        min_not, min_qty, step, dec_q, dec_p = details['min_notional'], details['min_quantity'], details['quantity_step_size'], details['num_decimal_places'], details['price_decimal_places']
        if usdt_amount < min_not * 0.99: print(f"INFO [{symbol}] Compra Ignorada: Valor ({usdt_amount:.2f}) < MinNot ({min_not:.2f})."); return None, None
        if current_price_estimate <= 0: print(f"ERRO [{symbol}] Compra Falhou: Preço inválido ({current_price_estimate})."); return None, None

        desired_qty = usdt_amount / current_price_estimate
        calc_qty = floor_to_precision(desired_qty, step, dec_q)

        if calc_qty < min_qty: print(f"INFO [{symbol}] Compra Ignorada: Qtd ({calc_qty:.{dec_q}f}) < MinQty ({min_qty:.{dec_q}f})."); return None, None
        final_not = calc_qty * current_price_estimate
        if final_not < min_not * 0.99: print(f"INFO [{symbol}] Compra Ignorada: Nocional Final ({final_not:.2f}) < MinNot ({min_not:.2f})."); return None, None

        qty_str = f"{calc_qty:.{dec_q}f}"
        print(f"EXEC [{symbol}] Enviando COMPRA Market: {qty_str} por ~{usdt_amount:.2f} {BASE_ASSET}..."); enviar_telegram(f"⏳ [{symbol}] Enviando COMPRA: {qty_str} (~{usdt_amount:.2f} {BASE_ASSET})...")
        order = client.order_market_buy(symbol=symbol, quantity=qty_str)

        fill_q, cost_tot, fills = 0.0, 0.0, order.get('fills', [])
        if fills:
            for f in fills: fill_q += float(f['qty']); cost_tot += float(f['qty']) * float(f['price'])
            if fill_q > 0:
                avg_p = cost_tot / fill_q
                msg = f"COMPRA Executada: {fill_q:.{dec_q}f} @ {avg_p:.{dec_p}f}. Custo: {cost_tot:.2f} {BASE_ASSET}"
                print(f"SUCCESS [{symbol}] {msg}"); enviar_telegram(f"✅ [{symbol}] {msg}")
                return fill_q, avg_p
        # Se não houve fills ou fill_q == 0
        stat, oid = order.get('status', 'N/A'), order.get('orderId', 'N/A')
        msg = f"Compra enviada (ID:{oid}), sem fills válidos. Status:{stat}. Verifique Binance."
        print(f"WARN [{symbol}] {msg}"); enviar_telegram(f"⚠️ [{symbol}] {msg}"); return None, None
    except BinanceAPIException as e: print(f"ERRO API [{symbol}] Compra: {e.code}-{e.message}"); enviar_telegram(f"❌ Falha COMPRA {symbol}: {e.code}-{e.message}"); return None, None
    except Exception as e: print(f"ERRO [{symbol}] Compra: {e}"); enviar_telegram(f"❌ Erro COMPRA {symbol}: {e}"); traceback.print_exc(); return None, None

def execute_sell_order(symbol: str, quantity_to_sell: float, details: dict, current_price_estimate: float):
    """Executa uma ordem de venda a mercado, retornando (filled_qty, avg_price, revenue) ou (None, None, None)."""
    try:
        min_not, min_qty, step, dec_q, dec_p = details['min_notional'], details['min_quantity'], details['quantity_step_size'], details['num_decimal_places'], details['price_decimal_places']
        calc_qty = floor_to_precision(quantity_to_sell, step, dec_q)

        if calc_qty < min_qty: print(f"INFO [{symbol}] Venda Ignorada: Qtd ({calc_qty:.{dec_q}f}) < MinQty ({min_qty:.{dec_q}f})."); return None, None, None
        if current_price_estimate <= 0: print(f"ERRO [{symbol}] Venda Falhou: Preço inválido ({current_price_estimate})."); return None, None, None
        est_not = calc_qty * current_price_estimate
        if est_not < min_not * 0.99: print(f"INFO [{symbol}] Venda Ignorada: Nocional Est. ({est_not:.2f}) < MinNot ({min_not:.2f})."); return None, None, None

        qty_str = f"{calc_qty:.{dec_q}f}"; coin_nm = symbol.replace(BASE_ASSET, '')
        print(f"EXEC [{symbol}] Enviando VENDA Market: {qty_str} {coin_nm}..."); enviar_telegram(f"⏳ [{symbol}] Enviando VENDA: {qty_str} {coin_nm}...")
        order = client.order_market_sell(symbol=symbol, quantity=qty_str)

        fill_q, rev_tot, fills = 0.0, 0.0, order.get('fills', [])
        if fills:
            for f in fills: fill_q += float(f['qty']); rev_tot += float(f['qty']) * float(f['price'])
            if fill_q > 0:
                avg_p = rev_tot / fill_q
                msg = f"VENDA Executada: {fill_q:.{dec_q}f} @ {avg_p:.{dec_p}f}. Receita: {rev_tot:.2f} {BASE_ASSET}"
                print(f"SUCCESS [{symbol}] {msg}"); enviar_telegram(f"✅ [{symbol}] {msg}")
                return fill_q, avg_p, rev_tot
        # Se não houve fills ou fill_q == 0
        stat, oid = order.get('status', 'N/A'), order.get('orderId', 'N/A')
        msg = f"Venda enviada (ID:{oid}), sem fills válidos. Status:{stat}. Verifique Binance."
        print(f"WARN [{symbol}] {msg}"); enviar_telegram(f"⚠️ [{symbol}] {msg}"); return None, None, None
    except BinanceAPIException as e: print(f"ERRO API [{symbol}] Venda: {e.code}-{e.message}"); enviar_telegram(f"❌ Falha VENDA {symbol}: {e.code}-{e.message}"); return None, None, None
    except Exception as e: print(f"ERRO [{symbol}] Venda: {e}"); enviar_telegram(f"❌ Erro VENDA {symbol}: {e}"); traceback.print_exc(); return None, None, None

def get_all_balances() -> dict:
    """Obtém os saldos 'free' das moedas relevantes."""
    balances = {BASE_ASSET: 0.0}
    coins_to_check = MOEDAS_A_OPERAR if MOEDAS_A_OPERAR else MOEDAS_SUPORTADAS
    for coin in coins_to_check: balances[coin] = 0.0
    try:
        acc_info = client.get_account()
        if not acc_info or 'balances' not in acc_info: print("ERRO: Resposta inválida saldos API."); return {k: 0.0 for k in balances}
        for acc_b in acc_info['balances']:
            asset = acc_b.get('asset')
            if asset == BASE_ASSET or asset in coins_to_check:
                try: balances[asset] = float(acc_b['free'])
                except (KeyError, ValueError, TypeError): print(f"WARN: Valor inválido saldo {asset}."); balances[asset] = 0.0
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as er: print(f"ERRO Rede/Timeout saldos: {er}"); enviar_telegram(f"❌ Erro Rede/Timeout saldos."); return {k: 0.0 for k in balances}
    except BinanceAPIException as ea: print(f"ERRO API saldos: {ea.code}-{ea.message}"); enviar_telegram(f"❌ Erro API Saldos: {ea.code}."); return {k: 0.0 for k in balances}
    except Exception as e: print(f"ERRO obter saldos: {e}"); enviar_telegram(f"❌ Erro obter saldos."); traceback.print_exc(); return {k: 0.0 for k in balances}
    return balances

def prompt_user_config_v2():
    """Solicita configuração inicial do usuário (moedas, modo)."""
    global OPERATING_MODE, MOEDAS_A_OPERAR, TRADING_PAIRS
    print("\n--- Configuração Inicial ---"); print(f"Moedas Suportadas: {', '.join(MOEDAS_SUPORTADAS)}")
    while True:
        raw_in = input(f"Moedas (ex:BTC,ETH) ou Enter p/ ({', '.join(MOEDAS_SUPORTADAS)}): ").strip(); sel_coins = []
        if not raw_in: sel_coins = list(MOEDAS_SUPORTADAS); print(f"INFO: Operando com TODAS: {', '.join(sel_coins)}"); break
        else:
            pot_coins = raw_in.split(','); valid_found = False
            for cn in pot_coins:
                cp = cn.strip().upper()
                if cp in MOEDAS_SUPORTADAS:
                    if cp not in sel_coins: sel_coins.append(cp); valid_found = True
                elif cp: print(f"WARN: Moeda '{cn}' ignorada (não suportada ou inválida).")
            if valid_found: print(f"INFO: Moedas selecionadas: {', '.join(sel_coins)}"); break
            else: print("ERRO: Nenhuma moeda válida selecionada. Tente novamente.")
    if not sel_coins: print("ERRO CRÍTICO: Nenhuma moeda selecionada."); return False, {}
    MOEDAS_A_OPERAR = sel_coins; TRADING_PAIRS = [f'{c}{BASE_ASSET}' for c in MOEDAS_A_OPERAR]

    while True:
        u_choice = input(f"Modo: [s] Alocar {BASE_ASSET} por moeda | [n] Dividir {BASE_ASSET} entre sinais BUY? (s/n): ").strip().lower()
        if u_choice == 's': OPERATING_MODE = "manual_allocation"; print(f"\nINFO: Modo: Alocação Manual."); enviar_telegram(f"ℹ️ Config: Modo Alocação Manual."); break
        elif u_choice == 'n': OPERATING_MODE = "multi_coin"; print(f"\nINFO: Modo: Multi Moeda Dinâmico."); enviar_telegram(f"ℹ️ Config: Modo Multi Moeda."); return True, {}; break
        else: print("Opção inválida.")

    alloc_targets = {c: 0.0 for c in MOEDAS_A_OPERAR}; bals = get_all_balances(); usdt_b = bals.get(BASE_ASSET, 0.0); print(f"INFO: Saldo {BASE_ASSET}: {usdt_b:.2f}")
    tot_alloc = 0.0
    for coin in MOEDAS_A_OPERAR:
        p = f"{coin}{BASE_ASSET}"; dets = get_symbol_details(p); min_n = dets.get('min_notional', MIN_USDT_TRADE_FALLBACK); print(f"--- {coin} (MinNot: {min_n:.2f} {BASE_ASSET}) ---")
        while True:
            try:
                a_str = input(f"Alocar {BASE_ASSET} p/ {coin}? (0=ñ op): ").strip(); t = float(a_str)
                if t < 0: print("Inválido (negativo).")
                elif 0 < t < min_n: print(f"WARN: {t:.2f} < MinNot ({min_n:.2f}). Compra inicial pode falhar."); alloc_targets[coin] = t; tot_alloc += t; break
                elif t >= min_n: alloc_targets[coin] = t; tot_alloc += t; break
                else: alloc_targets[coin] = 0.0; print(f"INFO: {coin} não operado."); break
            except ValueError: print("Inválido (número).")
    print(f"\n--- Resumo Alocação ---"); [print(f"- {c}: {a:.2f} {BASE_ASSET}") for c, a in alloc_targets.items()]; print(f"TOTAL ALOCADO: {tot_alloc:.2f} {BASE_ASSET}")
    if tot_alloc > usdt_b * 1.01: msg_al = f"⚠️ Alocado ({tot_alloc:.2f}) > Saldo ({usdt_b:.2f}). Pode faltar {BASE_ASSET}."; print(msg_al); enviar_telegram(msg_al)
    elif tot_alloc == 0: msg_al0 = f"⚠️ Nenhuma alocação feita. Nenhuma compra será realizada."; print(msg_al0); enviar_telegram(msg_al0)
    return True, alloc_targets

def initialize_trading_state_v2(alloc_map):
    """Inicializa o dicionário 'trading_state' para cada par."""
    global LIMITE_KLINES, trading_state
    print("\nINFO: Inicializando estado de trading..."); init_bals = get_all_balances(); usdt_init = init_bals.get(BASE_ASSET, 0.0); print(f"INFO: Saldo inicial {BASE_ASSET}: {usdt_init:.2f}")
    LIMITE_KLINES = 0; trading_state = {}; act_pairs_log = []

    for coin_i in MOEDAS_A_OPERAR:
        pair_i = f'{coin_i}{BASE_ASSET}'
        if OPERATING_MODE == "manual_allocation" and alloc_map.get(coin_i, 0.0) <= 0: print(f"INFO: Pulando {pair_i} (Alocação 0)."); continue

        StratCls = STRATEGY_CONFIG.get(pair_i, DEFAULT_STRATEGY_CLASS)
        if not StratCls or not issubclass(StratCls, TradingStrategy): print(f"WARN: Estratégia inválida/não encontrada p/ {pair_i}. Pulando."); continue
        strat_cls_nm = StratCls.__name__; strat_prms = STRATEGY_PARAMS_CONFIG.get(strat_cls_nm, {})
        dets_i = get_symbol_details(pair_i)

        trading_state[pair_i] = {'strategy_instance': None, 'strategy_class_name': strat_cls_nm, 'usdt_pool_revenue': 0.0, 'holding': False, 'quote_asset': coin_i, 'symbol_details': dets_i, 'buy_price_avg': 0.0, 'stop_loss_price': 0.0, 'trade_amount_target_usdt': alloc_map.get(coin_i, 0.0) if OPERATING_MODE == "manual_allocation" else 0.0, 'total_quantity_held': 0.0, 'total_invested_usdt': 0.0, 'last_action_log': 'Init'}

        try:
            instance = StratCls(symbol=pair_i, **strat_prms)
            trading_state[pair_i]['strategy_instance'] = instance
            LIMITE_KLINES = max(LIMITE_KLINES, getattr(instance, 'required_klines', 50))
            print(f"INFO: [{pair_i}] Instanciada {strat_cls_nm} (Klines Req: {getattr(instance, 'required_klines', 'N/A')})")
        except Exception as e_inst: print(f"ERRO CRÍTICO instanciar {strat_cls_nm} p/ {pair_i}: {e_inst}. Par desativado."); enviar_telegram(f"❌ Erro CRÍTICO instanciar {strat_cls_nm} p/ {pair_i}. Par desativado."); del trading_state[pair_i]; continue

        log_e = f"[{pair_i}] Strat:{strat_cls_nm}, MinNoc:{dets_i['min_notional']:.2f}";
        if OPERATING_MODE=="manual_allocation": log_e+=f", AlvoOp:{trading_state[pair_i]['trade_amount_target_usdt']:.2f}"
        act_pairs_log.append(log_e)

    print("\nINFO: Verificando saldos para posições existentes..."); pairs_to_remove = []
    for pair_c, st_c in trading_state.items():
        asset_c = st_c['quote_asset']; dets_c = st_c['symbol_details']; bal_asset = init_bals.get(asset_c)
        if bal_asset is None: print(f"WARN [{pair_c}] Saldo {asset_c} não encontrado. Desativando."); pairs_to_remove.append(pair_c); enviar_telegram(f"⚠️ [{pair_c}] Saldo {asset_c} não encontrado. Par desativado."); continue
        min_q = dets_c.get('min_quantity', 1e-8) * 1.01
        if bal_asset >= min_q:
            st_c['holding'] = True; st_c['total_quantity_held'] = bal_asset; st_c['buy_price_avg'] = 0.0; st_c['stop_loss_price'] = 0.0; st_c['total_invested_usdt'] = 0.0
            qty_f = f"{bal_asset:.{dets_c['num_decimal_places']}f}"; msg_p = f"[{pair_c}] 💼 Posição Existente: {qty_f} {asset_c}. PM e Stop NÃO definidos."; print(f"INFO: {msg_p}"); enviar_telegram(f"⚠️ {msg_p}"); st_c['last_action_log'] = 'Pos. Existente'
        else: st_c['holding'] = False

    for pair_rem in pairs_to_remove:
        if pair_rem in trading_state: del trading_state[pair_rem]
        act_pairs_log = [log for log in act_pairs_log if not log.startswith(f"[{pair_rem}]")] # Tenta remover do log

    if not trading_state: LIMITE_KLINES = 50; print("ERRO CRÍTICO: Nenhum par ativo."); enviar_telegram("❌ ERRO: Nenhum par ativo configurado/inicializado."); return # Retorna para indicar falha
    else:
        print(f"\nINFO: Init OK. {len(trading_state)} par(es) ativo(s). Klines: {LIMITE_KLINES}.")
        msg_set = (f"🚀 Bot Pronto!\nModo: {OPERATING_MODE}, Stop: {PERCENTUAL_STOP_LOSS*100:.1f}%"
                  f"\nInt:{INTERVALO_KLINES}, Chk:{CHECK_INTERVAL_SECONDS}s, Klines:{LIMITE_KLINES}"
                  f"\nPares Ativos:\n- "+"\n- ".join(act_pairs_log))
        enviar_telegram(msg_set)
    return True # Indica sucesso


def executar_bot():
    """Função principal que executa o loop do bot."""
    global discovered_chat_id, trading_state
    carregar_chat_id_salvo(); session_id = int(time.time()); start_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(session_id)); print(f"\n{'='*60}\n Bot Trader - {start_time_str} (Sessão: {session_id})\n{'='*60}"); ajustar_tempo()
    config_success, user_allocs = prompt_user_config_v2()
    if not config_success: enviar_telegram("❌ Bot Encerrado: Falha config. usuário."); print("ERRO: Falha config. usuário."); return
    init_success = initialize_trading_state_v2(user_allocs)
    if not init_success or not trading_state: print("ERRO CRÍTICO: Falha inicialização estado/pares. Encerrando."); enviar_telegram("❌ Bot Encerrado: Falha inicialização estado/pares."); return

    iter_loop, last_summary_time, SUMMARY_INTERVAL = 0, 0, 3600
    try:
        while True:
            iter_loop += 1; ts_start = time.time(); time_str = time.strftime('%H:%M:%S'); print(f"\n{'='*15} Iteração {iter_loop} ({time_str}) {'='*15}")
            bals = get_all_balances(); usdt_bal_start = max(0.0, bals.get(BASE_ASSET, 0.0)); print(f"INFO: Saldo {BASE_ASSET}: {usdt_bal_start:.2f}. Modo: {OPERATING_MODE}")
            processed_actions = {}

            # --- B. Processamento por Par ---
            for pair, state in list(trading_state.items()):
                if not state or not state.get('strategy_instance'): continue
                strat_inst, dets, coin, is_holding = state['strategy_instance'], state['symbol_details'], state['quote_asset'], state['holding']
                action, stop_triggered = 'HOLD', False

                # B.1: Sync Holding
                min_q_chk = dets.get('min_quantity', 1e-8) * 1.01; real_bal = bals.get(coin, 0.0); has_real = (real_bal >= min_q_chk)
                if is_holding != has_real: print(f"WARN [{pair}] Corrigindo Holding ({is_holding}->{has_real})."); state['holding'] = has_real; is_holding = has_real;
                if not has_real: state['buy_price_avg']=0.0; state['stop_loss_price']=0.0; state['total_quantity_held']=0.0; state['total_invested_usdt']=0.0

                # B.2: Obter Klines e Preço
                klines_raw = obter_klines(pair, INTERVALO_KLINES, LIMITE_KLINES); req_k = getattr(strat_inst, 'required_klines', 50)
                if not klines_raw or len(klines_raw) < req_k: print(f"INFO [{pair}] Klines insuf. ({len(klines_raw)}/{req_k})."); processed_actions[pair] = {'action': 'HOLD', 'price': 0, 'stop_triggered': False}; time.sleep(SLEEP_BETWEEN_PAIRS_MS/1000.0); continue
                klines_df = strat_inst._prepare_dataframe(klines_raw)
                if klines_df.empty or len(klines_df) < req_k: print(f"INFO [{pair}] Klines DF vazio/insuf."); processed_actions[pair] = {'action': 'HOLD', 'price': 0, 'stop_triggered': False}; time.sleep(SLEEP_BETWEEN_PAIRS_MS/1000.0); continue

                price_curr = 0.0
                try: price_curr = float(client.get_symbol_ticker(symbol=pair)['price']);
                except Exception as e_pr: print(f"ERRO [{pair}] obter preço: {e_pr}."); processed_actions[pair] = {'action': 'HOLD', 'price': 0, 'stop_triggered': False}; time.sleep(SLEEP_BETWEEN_PAIRS_MS/1000.0); continue

                # B.3: Check Stop-Loss
                if is_holding and state['buy_price_avg'] > 0 and PERCENTUAL_STOP_LOSS > 0:
                    state['stop_loss_price'] = state['buy_price_avg'] * (1 - PERCENTUAL_STOP_LOSS) # Recalcula sempre
                    if price_curr < state['stop_loss_price']: action, stop_triggered = 'SELL', True; print(f"WARN [{pair}] 🛑 STOP LOSS! Preço:{price_curr:.{dets['price_decimal_places']}f} < Stop:{state['stop_loss_price']:.{dets['price_decimal_places']}f}")
                
                # B.4: Decisão da Estratégia
                if not stop_triggered:
                    try: action = strat_inst.decide_action(pair, klines_df, is_holding)
                    except Exception as e_str: print(f"ERRO [{pair}] estratégia decide_action: {e_str}"); action = 'HOLD'

                # B.5: Log e Armazenamento da Ação
                log_pm = f"{state['buy_price_avg']:.{dets['price_decimal_places']}f}" if state['buy_price_avg'] > 0 else "N/A"; log_sl = f"{state['stop_loss_price']:.{dets['price_decimal_places']}f}" if state['stop_loss_price'] > 0 else "N/A"
                print(f"INFO [{pair}] P:{price_curr:.{dets['price_decimal_places']}f}, H:{is_holding}, PM:{log_pm}, SL:{log_sl} -> Ação: {action}{' (STOP)' if stop_triggered else ''}")
                processed_actions[pair] = {'action': action, 'price': price_curr, 'stop_triggered': stop_triggered}
                time.sleep(SLEEP_BETWEEN_PAIRS_MS / 1000.0)

            # --- C. Fase de Execução ---
            print("\nINFO: Fase de Execução..."); usdt_exec = usdt_bal_start
            # C.1: Vendas
            sold_pairs = []
            for pair_ex, act_info in processed_actions.items():
                if act_info['action'] == 'SELL':
                    state_ex = trading_state.get(pair_ex);
                    if not state_ex or not state_ex['holding']: continue
                    dets_ex, coin_ex, price_ex = state_ex['symbol_details'], state_ex['quote_asset'], act_info['price']
                    qty_sell = state_ex['total_quantity_held']
                    if qty_sell >= dets_ex.get('min_quantity', 1e-8) * 0.99:
                        reason = "STOP" if act_info['stop_triggered'] else "STRAT"
                        print(f"EXEC [{pair_ex}] 🔽 Iniciando VENDA ({reason})..."); qty_s, price_s, rev_s = execute_sell_order(pair_ex, qty_sell, dets_ex, price_ex)
                        if qty_s and price_s and rev_s is not None:
                            usdt_exec += rev_s; state_ex['holding']=False; state_ex['buy_price_avg']=0.0; state_ex['stop_loss_price']=0.0; state_ex['total_quantity_held']=0.0; state_ex['total_invested_usdt']=0.0; state_ex['usdt_pool_revenue']+=rev_s; state_ex['last_action_log']=f"Sell OK ({reason})"; sold_pairs.append(pair_ex); print(f"SUCCESS [{pair_ex}] Venda OK. USDT p/ exec:{usdt_exec:.2f}")
                        else: state_ex['last_action_log']=f"Falha Sell ({reason})"
                    else: print(f"INFO [{pair_ex}] Sell ignorado (Qtd Insuf.)"); state_ex['last_action_log']=f"Sell Ign.(Qtd)"
            # C.2: Compras
            buy_todo = [p for p, i in processed_actions.items() if i['action']=='BUY' and trading_state.get(p) and not trading_state[p]['holding']]
            if buy_todo: print(f"\nINFO: Sinais COMPRA: {buy_todo}. Saldo {BASE_ASSET} p/ exec: {usdt_exec:.2f}")
            if OPERATING_MODE == "manual_allocation":
                for pair_b in buy_todo:
                    st_b, dets_b, price_b = trading_state[pair_b], trading_state[pair_b]['symbol_details'], processed_actions[pair_b]['price']
                    tgt_usdt = st_b['trade_amount_target_usdt']; min_not = dets_b.get('min_notional', MIN_USDT_TRADE_FALLBACK)*0.99
                    if tgt_usdt >= min_not and usdt_exec >= tgt_usdt * 0.99:
                        print(f"EXEC [{pair_b}] 🔼 Iniciando COMPRA Manual ({tgt_usdt:.2f} {BASE_ASSET})..."); qty_b, price_bf = execute_buy_order(pair_b, tgt_usdt, dets_b, price_b)
                        if qty_b and price_bf:
                            inv = qty_b*price_bf; st_b['total_quantity_held']=qty_b; st_b['total_invested_usdt']=inv; st_b['buy_price_avg']=price_bf; st_b['stop_loss_price']=st_b['buy_price_avg']*(1-PERCENTUAL_STOP_LOSS); st_b['holding']=True; usdt_exec-=inv; st_b['last_action_log']=f"Buy OK (Man)"; print(f"SUCCESS [{pair_b}] Compra Manual OK. PM:{price_bf:.{dets_b['price_decimal_places']}f}, SL:{st_b['stop_loss_price']:.{dets_b['price_decimal_places']}f}. USDT Rest:{usdt_exec:.2f}")
                        else: st_b['last_action_log']=f"Falha Buy (Man)"
                    elif usdt_exec < tgt_usdt * 0.99: print(f"INFO [{pair_b}] Buy Manual ignorado (Saldo {BASE_ASSET} {usdt_exec:.2f} < Alvo {tgt_usdt:.2f})."); st_b['last_action_log']=f"Buy Ign.(Saldo)"
                    else: print(f"INFO [{pair_b}] Buy Manual ignorado (Alvo {tgt_usdt:.2f} < MinNot {min_not:.2f})."); st_b['last_action_log']=f"Buy Ign.(MinNot)"
            elif OPERATING_MODE == "multi_coin":
                 num_buys = len(buy_todo);
                 if num_buys > 0 and usdt_exec > MIN_USDT_TRADE_FALLBACK:
                      usdt_per_buy = usdt_exec / num_buys; print(f"INFO [Multi]: Dividindo {usdt_exec:.2f} {BASE_ASSET} / {num_buys} compras = {usdt_per_buy:.2f} por compra.")
                      for pair_b in buy_todo:
                           st_b, dets_b, price_b = trading_state[pair_b], trading_state[pair_b]['symbol_details'], processed_actions[pair_b]['price']
                           min_not = dets_b.get('min_notional', MIN_USDT_TRADE_FALLBACK)*0.99
                           amt_spend = min(usdt_per_buy, usdt_exec) # Garante não gastar mais q o disponível
                           if amt_spend >= min_not:
                               print(f"EXEC [{pair_b}] 🔼 Iniciando COMPRA Multi ({amt_spend:.2f} {BASE_ASSET})..."); qty_b, price_bf = execute_buy_order(pair_b, amt_spend, dets_b, price_b)
                               if qty_b and price_bf:
                                    inv = qty_b*price_bf; st_b['total_quantity_held']=qty_b; st_b['total_invested_usdt']=inv; st_b['buy_price_avg']=price_bf; st_b['stop_loss_price']=st_b['buy_price_avg']*(1-PERCENTUAL_STOP_LOSS); st_b['holding']=True; usdt_exec-=inv; st_b['last_action_log']=f"Buy OK (Multi)"; print(f"SUCCESS [{pair_b}] Compra Multi OK. PM:{price_bf:.{dets_b['price_decimal_places']}f}, SL:{st_b['stop_loss_price']:.{dets_b['price_decimal_places']}f}. USDT Rest:{usdt_exec:.2f}")
                               else: st_b['last_action_log']=f"Falha Buy (Multi)"
                           else: print(f"INFO [{pair_b}] Compra Multi ignorada (Valor por compra {amt_spend:.2f} < MinNot {min_not:.2f} ou Saldo insuficiente)."); st_b['last_action_log']=f"Buy Ign.(MinNot/Saldo)"
                           if usdt_exec < MIN_USDT_TRADE_FALLBACK: print("INFO [Multi]: Saldo USDT baixo. Parando compras neste ciclo."); break
                 elif num_buys > 0: print(f"INFO [Multi]: Saldo USDT ({usdt_exec:.2f}) insuficiente para novas compras.")
            # --- D. Resumo Periódico ---
            now = time.time()
            if now - last_summary_time >= SUMMARY_INTERVAL:
                try:
                    summary = [f"== Resumo Bot ({time.strftime('%H:%M:%S')}) =="]; summary.append(f"Modo: {OPERATING_MODE}, Saldo {BASE_ASSET}: {usdt_exec:.2f} (pós-exec)")
                    pos_found = False
                    for pair_s, state_s in trading_state.items():
                        if state_s.get('holding') and state_s.get('total_quantity_held',0)>0:
                            pos_found=True; dets_s=state_s['symbol_details']; pm=f"{state_s['buy_price_avg']:.{dets_s['price_decimal_places']}f}" if state_s['buy_price_avg']>0 else "N/A"; sl=f"{state_s['stop_loss_price']:.{dets_s['price_decimal_places']}f}" if state_s['stop_loss_price']>0 else "N/A"; qt=f"{state_s['total_quantity_held']:.{dets_s['num_decimal_places']}f}"
                            summary.append(f"- {pair_s}: Qtd={qt}, PM={pm}, SL={sl}")
                    if not pos_found: summary.append("- Nenhuma posição aberta.")
                    enviar_telegram("\n".join(summary)); last_summary_time = now
                except Exception as e_sum: print(f"ERRO gerar resumo: {e_sum}")
            # --- E. Finalização da Iteração ---
            iter_dur = time.time() - ts_start; print(f"\n{'='*15} Fim Iteração {iter_loop} (Duração: {iter_dur:.2f}s) {'='*15}"); sleep_t = max(0.5, CHECK_INTERVAL_SECONDS - iter_dur); time.sleep(sleep_t)
    except KeyboardInterrupt: print("\n👋 Bot interrompido manualmente."); enviar_telegram("🔌 Bot interrompido manualmente.")
    except BinanceAPIException as e_fapi: print(f"\n💥 ERRO FATAL API: {e_fapi.code}-{e_fapi.message}"); enviar_telegram(f"🚨 ERRO FATAL API: {e_fapi.code}-{e_fapi.message}. Encerrando."); traceback.print_exc()
    except Exception as e_fmain: print(f"\n💥 ERRO FATAL INESPERADO: {e_fmain}"); enviar_telegram(f"🚨 ERRO FATAL INESPERADO: {e_fmain}. Encerrando."); traceback.print_exc()
    finally: print("Bot finalizado."); enviar_telegram("💤 Bot finalizado.")


def run_telegram_listener():
    """Executa o listener do Telegram em uma thread separada."""
    global telegram_application_instance
    if TELEGRAM_TOKEN:
        print("INFO: Iniciando listener do Bot Telegram (para /start)...")
        loop = None
        try:
            # Configura um novo loop de eventos asyncio para esta thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Cria e configura a aplicação Telegram
            application = Application.builder().token(TELEGRAM_TOKEN).build()
            application.add_handler(CommandHandler("start", start_command_handler))
            application.add_error_handler(error_handler_telegram)
            telegram_application_instance = application # Guarda referência global

            print("INFO: Listener Telegram pronto e escutando em background.")
            # Inicia o polling (bloqueia esta thread até parar)
            application.run_polling(poll_interval=1, timeout=30, drop_pending_updates=True)
            print("INFO: Listener Telegram (run_polling) encerrou.") # Só chega aqui se parar

        except RuntimeError as e_rt:
            # Erros comuns ao fechar/interromper threads com asyncio
            if "cannot schedule new futures after shutdown" in str(e_rt).lower() or \
               "no current event loop" in str(e_rt).lower() or \
               "Event loop is closed" in str(e_rt):
                print(f"INFO: Listener Telegram encontrou erro esperado de loop/shutdown: {e_rt}")
            else:
                print(f"ERRO CRÍTICO no listener Telegram (RuntimeError): {e_rt}")
                traceback.print_exc(); enviar_telegram(f"❌ ERRO CRÍTICO RT listener Telegram: {e_rt}")
        except Exception as e:
            print(f"ERRO CRÍTICO no listener Telegram (Exceção Geral): {e}")
            traceback.print_exc(); enviar_telegram(f"❌ ERRO CRÍTICO Exceção listener Telegram: {e}")
        finally:
             # Tenta limpar o loop se ele foi criado
             # A limpeza em threads daemon é complexa e pode não ser necessária,
             # mas tentamos parar de forma limpa se possível.
             if loop and telegram_application_instance:
                   if loop.is_running():
                        print("INFO: Tentando parar o loop de eventos do Telegram...")
                        loop.call_soon_threadsafe(telegram_application_instance.stop) # Pede para parar
                   # Não fechar o loop aqui, pode causar problemas se ainda estiver sendo usado
                   # if not loop.is_closed(): loop.close()
             print("INFO: Thread do listener Telegram finalizada.")
    else:
        print("INFO: Token do Telegram não fornecido. Listener /start desativado.")


# === Ponto de Entrada Principal ===
if __name__ == "__main__":
    print("INFO: Verificando dependências...")
    # Bloco de verificação movido para o início do script após imports

    if not os.path.exists(dotenv_path):
        print(f"ALERTA: Arquivo .env não encontrado em {dotenv_path}.")
        try:
            with open(dotenv_path, 'w') as f:
                 f.write("# Cole suas chaves da API Binance aqui\n")
                 f.write("API_KEY='SUA_API_KEY_BINANCE'\n")
                 f.write("API_SECRET='SEU_API_SECRET_BINANCE'\n\n")
                 f.write("# Token do seu Bot do Telegram (obtido via @BotFather)\n")
                 f.write("TELEGRAM_TOKEN='SEU_TOKEN_TELEGRAM'\n\n")
                 f.write("# (Opcional) Chat ID padrão para enviar notificações se o /start não for usado\n")
                 f.write("# TELEGRAM_CHAT_ID_FALLBACK='SEU_CHAT_ID_TELEGRAM'\n")
            print(f"INFO: Arquivo .env de exemplo criado em {dotenv_path}. Edite-o com suas chaves.")
        except Exception as e_env: print(f"ERRO ao tentar criar .env exemplo: {e_env}")
        exit("Arquivo .env não presente ou não configurado. Edite o .env criado e rode novamente.")

    if not API_KEY or not API_SECRET:
         print("ERRO CRÍTICO: API_KEY ou API_SECRET não carregadas. Verifique o .env.")
         exit(1)

    # Carrega o chat_id antes de iniciar a thread do Telegram
    carregar_chat_id_salvo()

    telegram_thread = None
    if TELEGRAM_TOKEN:
        # Inicia o listener do Telegram em uma thread separada
        # 'daemon=True' significa que a thread não impedirá o programa principal de sair
        telegram_thread = threading.Thread(target=run_telegram_listener, name="TelegramListenerThread", daemon=True)
        telegram_thread.start()
        print("INFO: Thread do listener Telegram iniciada em background.")
    else:
        print("INFO: Token do Telegram não configurado no .env. O comando /start não funcionará.")

    # Executa a lógica principal do bot na thread principal
    executar_bot()

    # O programa principal termina aqui. A thread do Telegram (se daemon=True) será encerrada automaticamente.
    # Se precisar esperar a thread do Telegram (raro para daemon), pode usar telegram_thread.join()
    print("\nPrograma principal encerrado.")
