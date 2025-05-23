import logging
from datetime import datetime

def setup_logger():
    logger = logging.getLogger("TradingBot")
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler(f"logs/{datetime.now().strftime('%Y-%m-%d')}.log")
    formatter = logging.Formatter('%(asctime)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    return logger
