# main.py

import time
import threading
from config.settings import LOOP_INTERVAL, TRADING_PAIRS, API_KEY, API_SECRET
from data.binance_data import get_klines
from strategies.strategy_selector import StrategySelector
from trading.binance_executor import execute_trade
from trading.position_manager import (
    is_position_open,
    check_exit,
    open_position,
    capital_em_uso
)
from utils.telegram import send_telegram_message
from utils.state import shared_state, append_log
from binance.client import Client

client = Client(API_KEY, API_SECRET)

def sincronizar_posicoes():
    for pair in TRADING_PAIRS:
        base = pair.replace("/USDT", "")
        saldo = float(client.get_asset_balance(asset=base)["free"])
        if saldo > 0.00001:
            preco_atual = float(client.get_symbol_ticker(symbol=base + "USDT")["price"])
            open_position(pair, preco_atual, "buy")
            append_log(f"[SYNC] Posição reconstruída: {pair} @ {preco_atual}")

def bot_loop():
    append_log("BOT INICIADO")

    while shared_state["running"]:
        for pair in TRADING_PAIRS:
            try:
                candles = get_klines(pair=pair)
                if not candles or len(candles) < 50:
                    append_log(f"[{pair}] Aguardando mais dados...")
                    continue

                last_close = candles[-1]["close"]

                if is_position_open(pair):
                    exit_action = check_exit(pair, last_close)
                    if exit_action:
                        append_log(f"[{pair}] Condição de saída detectada: {exit_action.upper()}")
                        execute_trade(exit_action, pair)
                    else:
                        append_log(f"[{pair}] Aguardando SL ou TP...")
                else:
                    selector = StrategySelector(candles)
                    action, strategy_name = selector.select_action()

                    if action != "hold":
                        append_log(f"[{pair}] AÇÃO: {action.upper()} via {strategy_name}")

                        # ✅ Verificar saldo disponível
                        if action == "buy":
                            usdt_balance = float(client.get_asset_balance(asset="USDT")["free"])
                            precos = {pair: last_close}
                            capital_usado = capital_em_uso(precos)
                            disponivel = usdt_balance - capital_usado

                            if disponivel < 10:
                                append_log(f"[{pair}] Saldo insuficiente para nova posição. Disp: {disponivel:.2f} USDT")
                                continue

                        success = execute_trade(action, pair)

                        if success and action == "buy":
                            open_position(pair, last_close, action)
                    else:
                        append_log(f"[{pair}] Nenhuma ação tomada (hold)")

            except Exception as e:
                append_log(f"[{pair}] ERRO: {e}")
                send_telegram_message(f"[{pair}] ERRO: {e}")

        time.sleep(LOOP_INTERVAL)

# Início controlado pelo Flask
def start_bot():
    if not shared_state["running"]:
        shared_state["running"] = True
        sincronizar_posicoes()
        thread = threading.Thread(target=bot_loop)
        thread.start()
        return "Bot iniciado."
    return "Bot já está em execução."

def stop_bot():
    shared_state["running"] = False
    append_log("BOT PARADO")
    return "Bot parado."
