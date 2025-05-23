# utils/state.py

from collections import deque

# Controle central de estado
shared_state = {
    "running": False,
    "log": deque(maxlen=100)
}

def append_log(message: str):
    print(message)
    shared_state["log"].appendleft(message)
