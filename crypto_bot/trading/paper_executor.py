# trading/paper_executor.py

from utils.telegram import send_telegram_message

# Simulação de saldo fictício
simulated_balances = {
    "USDT": 1000.0,
    "BTC": 0.0,
    "ETH": 0.0,
    "SOL": 0.0
}

def execute_paper_trade(action, trading_pair):
    base = trading_pair.replace("/USDT", "")
    price = 100.0  # Preço fictício. Ideal: passar real depois.

    if action == "buy":
        usdt = simulated_balances["USDT"]
        amount = usdt * 0.05 / price
        simulated_balances[base] += amount
        simulated_balances["USDT"] -= usdt * 0.05
        msg = f"[PAPER] COMPROU {amount:.6f} {base}"
    elif action == "sell":
        amount = simulated_balances[base]
        simulated_balances["USDT"] += amount * price
        simulated_balances[base] = 0
        msg = f"[PAPER] VENDEU {amount:.6f} {base}"
    else:
        msg = "[PAPER] Ação inválida"

    print(msg)
    send_telegram_message(msg)
