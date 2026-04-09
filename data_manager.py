import pandas as pd
import threading
import time
import random
from collections import deque
from footprint_candle import FootprintCandle
from order_flow_engine import OrderFlowEngine
from strategy_logic import RelativeStrengthStrategy
from upstox_wss import UpstoxWSS
from upstox_helper import UpstoxHelper

# Thread-safe rolling window for Option Footprint
MAX_CANDLES = 100
candles_deque = deque(maxlen=MAX_CANDLES)
analysis_deque = deque(maxlen=MAX_CANDLES)

# RS Strategy data: Simplified OHLC aggregation
# Store { 'idx': {timestamp: {o,h,l,c,v}}, 'opt': {timestamp: {o,h,l,c,v}} }
aggregated_ohlc = {'idx': {}, 'opt': {}}

engine = OrderFlowEngine()
rs_strategy = RelativeStrengthStrategy()
helper = UpstoxHelper()

current_opt_candle = None
candle_duration = 60 # 1 minute

active_opt_key = "NSE_FO|53265" # Example default
active_idx_key = helper.get_spot_keys()['NIFTY']

def on_tick_received(instrument_key, price, volume, is_buy):
    global current_opt_candle, active_opt_key, active_idx_key

    now = pd.Timestamp.now()
    ts_min = now.floor('1min')

    # 1. Footprint Aggregation (Selected Option Only)
    if instrument_key == active_opt_key:
        if current_opt_candle is None or current_opt_candle.start_time != ts_min:
            if current_opt_candle is not None:
                candles_deque.append(current_opt_candle)
                analysis_deque.append(engine.analyze_candle(current_opt_candle))
            current_opt_candle = FootprintCandle(price, ts_min)
        current_opt_candle.add_tick(price, volume, is_buy)

        # Aggregated OHLC for Option
        update_ohlc('opt', ts_min, price, volume)

    # 2. Index OHLC Aggregation
    elif instrument_key == active_idx_key:
        update_ohlc('idx', ts_min, price, 0)

def update_ohlc(key, ts, price, vol):
    if ts not in aggregated_ohlc[key]:
        aggregated_ohlc[key][ts] = {'open': price, 'high': price, 'low': price, 'close': price, 'volume': 0}

    d = aggregated_ohlc[key][ts]
    d['high'] = max(d['high'], price)
    d['low'] = min(d['low'], price)
    d['close'] = price
    d['volume'] += vol

    # Prune old data
    if len(aggregated_ohlc[key]) > MAX_CANDLES + 5:
        oldest = min(aggregated_ohlc[key].keys())
        del aggregated_ohlc[key][oldest]

def get_synced_df():
    """Build a synced dataframe for Index and Option."""
    idx_df = pd.DataFrame.from_dict(aggregated_ohlc['idx'], orient='index').rename(columns=lambda x: f'idx_{x}')
    opt_df = pd.DataFrame.from_dict(aggregated_ohlc['opt'], orient='index').rename(columns=lambda x: f'opt_{x}')

    if idx_df.empty or opt_df.empty: return pd.DataFrame()

    df = idx_df.join(opt_df, how='inner').sort_index()
    return df

# Initialize Upstox WSS
upstox_wss = UpstoxWSS(callback=on_tick_received)

def start_simulation():
    def run():
        price_opt = 200
        price_idx = 22000
        while True:
            on_tick_received(active_opt_key, price_opt + random.uniform(-2, 2), random.randint(1, 10), random.choice([True, False]))
            on_tick_received(active_idx_key, price_idx + random.uniform(-5, 5), 0, True)
            time.sleep(0.1)

    threading.Thread(target=run, daemon=True).start()

def change_instrument(opt_key, idx_name='NIFTY'):
    global active_opt_key, active_idx_key, current_opt_candle
    active_opt_key = opt_key
    active_idx_key = helper.get_spot_keys().get(idx_name, active_idx_key)

    candles_deque.clear()
    analysis_deque.clear()
    aggregated_ohlc['idx'].clear()
    aggregated_ohlc['opt'].clear()
    current_opt_candle = None

    upstox_wss.update_subscriptions([active_opt_key, active_idx_key])
