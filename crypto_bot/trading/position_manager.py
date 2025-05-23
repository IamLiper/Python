# trading/position_manager.py

position = {}

def open_position(pair, entry_price, action):
    position[pair] = {
        "is_open": True,
        "entry_price": entry_price,
        "action": action
    }

def close_position(pair):
    if pair in position:
        position[pair]["is_open"] = False

def is_position_open(pair):
    return position.get(pair, {}).get("is_open", False)

def check_exit(pair, current_price):
    pos = position.get(pair)
    if not pos or not pos["is_open"]:
        return None

    entry = pos["entry_price"]
    stop = entry * 0.98
    target = entry * 1.05

    if current_price <= stop:
        close_position(pair)
        return "sell"
    elif current_price >= target:
        close_position(pair)
        return "sell"
    return None

def capital_em_uso(usdt_preco_map):
    total = 0
    for pair, pos in position.items():
        if pos["is_open"]:
            entry = pos["entry_price"]
            base = pair.replace("/USDT", "")
            qty = get_quantity_in_binance(base)
            total += qty * usdt_preco_map.get(pair, entry)
    return total

def get_quantity_in_binance(asset):
    from binance.client import Client
    from config.settings import API_KEY, API_SECRET
    client = Client(API_KEY, API_SECRET)
    try:
        bal = float(client.get_asset_balance(asset=asset)["free"])
        return bal
    except:
        return 0.0
