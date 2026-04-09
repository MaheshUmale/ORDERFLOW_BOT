import pandas as pd
import threading
import time
import random
from collections import deque
from footprint_candle import FootprintCandle
from order_flow_engine import OrderFlowEngine

# Thread-safe rolling window for the UI to consume
MAX_CANDLES = 100
candles_deque = deque(maxlen=MAX_CANDLES)
analysis_deque = deque(maxlen=MAX_CANDLES)
engine = OrderFlowEngine()

def simulate_wss_feed():
    """
    Replace this simulator with your actual WSS client (e.g., Upstox WSS).
    It should append footprint candle data to the deques.
    """
    price = 22000 # Example base price for Nifty
    while True:
        candle = FootprintCandle(price, pd.Timestamp.now())
        # Simulate ~50 ticks per candle
        for _ in range(50):
            tick_price = price + random.choice([-1, 0, 1])
            tick_vol = random.randint(10, 100)
            is_buy = random.choice([True, False])
            candle.add_tick(tick_price, tick_vol, is_buy)
            price = tick_price
            time.sleep(0.02) # Fast tick simulation

        candles_deque.append(candle)
        analysis_deque.append(engine.analyze_candle(candle))

def start_simulation():
    # Start WSS feed in background
    wss_thread = threading.Thread(target=simulate_wss_feed, daemon=True)
    wss_thread.start()
    return wss_thread
