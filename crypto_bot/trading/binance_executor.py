from binance.client import Client
from config.settings import API_KEY, API_SECRET, TRADE_PERCENT_PER_PAIR, MIN_NOTIONAL_PER_PAIR
from utils.telegram import send_telegram_message

client = Client(API_KEY, API_SECRET)

def execute_trade(action, trading_pair):
    symbol = trading_pair.replace("/", "")
    base = symbol.replace("USDT", "")

    try:
        usdt_balance = float(client.get_asset_balance(asset="USDT")["free"])
        trade_pct = TRADE_PERCENT_PER_PAIR.get(trading_pair, 0.01)
        min_notional = MIN_NOTIONAL_PER_PAIR.get(trading_pair, 10.0)
        amount = max(round(usdt_balance * trade_pct, 2), min_notional)

        if amount > usdt_balance:
            print(f"[{symbol}] Saldo insuficiente para comprar {amount} USDT.")
            return False

        if action == "buy":
            print(f"[{symbol}] COMPRANDO {amount} USDT")
            order = client.order_market_buy(
                symbol=symbol,
                quoteOrderQty=amount
            )

        elif action == "sell":
            balance = float(client.get_asset_balance(asset=base)["free"])
            min_qty = 0.0001
            if balance < min_qty:
                print(f"[{symbol}] Saldo {base} insuficiente.")
                return False

            print(f"[{symbol}] VENDENDO {balance} {base}")
            order = client.order_market_sell(
                symbol=symbol,
                quantity=round(balance, 6)
            )

        else:
            print(f"[{symbol}] Ação inválida.")
            return False

        send_telegram_message(f"✅ [{symbol}] Ordem {action.upper()} executada")
        return True

    except Exception as e:
        send_telegram_message(f"❌ [{symbol}] Erro na ordem: {e}")
        print(f"[{symbol}] ERRO: {e}")
        return False

