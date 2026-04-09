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

# RS Strategy data: OHLC aggregation
aggregated_ohlc = {'idx': {}, 'opt': {}}

engine = OrderFlowEngine()
rs_strategy = RelativeStrengthStrategy()
helper = UpstoxHelper()

current_opt_candle = None
active_opt_key = None
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
                engine.cumulative_delta += current_opt_candle.delta
                analysis_deque.append(engine.analyze_candle(current_opt_candle, engine.cumulative_delta - current_opt_candle.delta))
            current_opt_candle = FootprintCandle(price, ts_min)
        current_opt_candle.add_tick(price, volume, is_buy)

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

    if len(aggregated_ohlc[key]) > MAX_CANDLES + 10:
        oldest = min(aggregated_ohlc[key].keys())
        del aggregated_ohlc[key][oldest]

def get_all_opt_candles():
    all_c = list(candles_deque)
    if current_opt_candle:
        all_c.append(current_opt_candle)
    return all_c

def get_synced_df():
    idx_df = pd.DataFrame.from_dict(aggregated_ohlc['idx'], orient='index').rename(columns=lambda x: f'idx_{x}')
    opt_df = pd.DataFrame.from_dict(aggregated_ohlc['opt'], orient='index').rename(columns=lambda x: f'opt_{x}')

    if idx_df.empty or opt_df.empty: return pd.DataFrame()

    df = idx_df.join(opt_df, how='inner').sort_index()
    return df

upstox_wss = UpstoxWSS(callback=on_tick_received)
_simulation_active = False

def start_simulation():
    global _simulation_active
    if _simulation_active: return
    _simulation_active = True
    def run():
        price_opt = 200
        price_idx = 22000
        while _simulation_active:
            try:
                if active_opt_key:
                    # Simulate ticks every 0.5s
                    on_tick_received(active_opt_key, price_opt + random.uniform(-2, 2), random.randint(1, 10), random.choice([True, False]))
                    on_tick_received(active_idx_key, price_idx + random.uniform(-5, 5), 0, True)
                    # Drift prices slightly
                    price_opt += random.uniform(-0.5, 0.5)
                    price_idx += random.uniform(-1, 1)
            except Exception as e:
                print(f"Simulation error: {e}")
            time.sleep(0.5)

    threading.Thread(target=run, daemon=True).start()

def stop_simulation():
    global _simulation_active
    _simulation_active = False

def start_live_feed():
    """Starts the real-time Upstox WebSocket feed."""
    stop_simulation()
    upstox_wss.start()

def change_instrument(opt_key, idx_name='NIFTY'):
    global active_opt_key, active_idx_key, current_opt_candle
    active_opt_key = opt_key
    active_idx_key = helper.get_spot_keys().get(idx_name, active_idx_key)

    candles_deque.clear()
    analysis_deque.clear()
    aggregated_ohlc['idx'].clear()
    aggregated_ohlc['opt'].clear()
    current_opt_candle = None
    engine.cumulative_delta = 0

    # Bootstrap historical candles
    if active_opt_key == "SIMULATED_INSTRUMENT": return

    try:
        hist_opt = helper.get_historical_candles(active_opt_key)
        hist_idx = helper.get_historical_candles(active_idx_key)

        # Upstox returns newest first; reverse for chronological order
        hist_opt.reverse()
        hist_idx.reverse()

        # Populate aggregated_ohlc
        for c in hist_idx:
            ts = pd.to_datetime(c[0]).tz_localize(None)
            aggregated_ohlc['idx'][ts] = {'open': c[1], 'high': c[2], 'low': c[3], 'close': c[4], 'volume': c[5]}

        for c in hist_opt:
            ts = pd.to_datetime(c[0]).tz_localize(None)
            aggregated_ohlc['opt'][ts] = {'open': c[1], 'high': c[2], 'low': c[3], 'close': c[4], 'volume': c[5]}

            # Create FootprintCandles from OHLC (approximate since we don't have ticks for history)
            f_candle = FootprintCandle(c[1], ts)
            f_candle.high = c[2]
            f_candle.low = c[3]
            f_candle.close = c[4]
            f_candle.volume = c[5]
            # Heuristic delta
            f_candle.delta = (c[4] - c[1]) * (c[5] / (c[2] - c[3] + 0.001))

            candles_deque.append(f_candle)
            engine.cumulative_delta += f_candle.delta
            analysis_deque.append(engine.analyze_candle(f_candle, engine.cumulative_delta - f_candle.delta))

    except Exception as e:
        print(f"Error bootstrapping: {e}")

    upstox_wss.update_subscriptions([active_opt_key, active_idx_key])
