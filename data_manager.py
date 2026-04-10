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

# Global Storage for Multiple Instruments
MAX_CANDLES = 100

# Dictionaries keyed by instrument_key
candles_storage = {}  # {key: deque(FootprintCandle)}
analysis_storage = {} # {key: deque(analysis_dict)}
current_candles = {}  # {key: FootprintCandle}
engines = {}         # {key: OrderFlowEngine}
aggregated_ohlc = {'idx': {}, 'opt': {}} # Keep this for RS, but might need keying too if multi-index
# For simplicity in RS, we map option_key -> index_key
opt_to_idx_map = {}

helper = UpstoxHelper()
rs_strategy = RelativeStrengthStrategy()

# Active set of keys to subscribe to
subscribed_instruments = set()

def on_tick_received(instrument_key, price, volume, is_buy):
    now = pd.Timestamp.now(tz='Asia/Kolkata').replace(tzinfo=None)
    ts_min = now.floor('1min')

    # LOG FOR THE USER
    print(f"DM TICK: {instrument_key} Price={price} Vol={volume} @ {ts_min}")

    # 1. Footprint Aggregation
    if instrument_key in candles_storage:
        if instrument_key not in current_candles or current_candles[instrument_key] is None or current_candles[instrument_key].start_time != ts_min:
            if instrument_key in current_candles and current_candles[instrument_key] is not None:
                old_candle = current_candles[instrument_key]
                candles_storage[instrument_key].append(old_candle)

                engine = engines.get(instrument_key)
                if engine:
                    engine.cumulative_delta += old_candle.delta
                    analysis_storage[instrument_key].append(engine.analyze_candle(old_candle, engine.cumulative_delta - old_candle.delta))

            current_candles[instrument_key] = FootprintCandle(price, ts_min)

        current_candles[instrument_key].add_tick(price, volume, is_buy)
        update_ohlc('opt', instrument_key, ts_min, price, volume)

    # 2. Index OHLC Aggregation (if it's an index being tracked)
    spot_keys = helper.get_spot_keys().values()
    if instrument_key in spot_keys:
        update_ohlc('idx', instrument_key, ts_min, price, 0)

def update_ohlc(type_key, instrument_key, ts, price, vol, high=None, low=None, close=None):
    if instrument_key not in aggregated_ohlc[type_key]:
        aggregated_ohlc[type_key][instrument_key] = {}

    storage = aggregated_ohlc[type_key][instrument_key]

    if ts not in storage:
        storage[ts] = {'open': price, 'high': price, 'low': price, 'close': price, 'volume': 0}

    d = storage[ts]
    if high is not None:
        d['high'] = high
        d['low'] = low
        d['close'] = close
    else:
        d['high'] = max(d['high'], price)
        d['low'] = min(d['low'], price)
        d['close'] = price
    d['volume'] += vol

    if len(storage) > MAX_CANDLES + 10:
        oldest = min(storage.keys())
        del storage[oldest]

def get_all_opt_candles(instrument_key):
    if instrument_key not in candles_storage: return []
    all_c = list(candles_storage[instrument_key])
    if instrument_key in current_candles and current_candles[instrument_key]:
        all_c.append(current_candles[instrument_key])
    return all_c

def get_synced_df(opt_key):
    idx_key = opt_to_idx_map.get(opt_key)
    if not idx_key: return pd.DataFrame()

    if idx_key not in aggregated_ohlc['idx'] or opt_key not in aggregated_ohlc['opt']:
        return pd.DataFrame()

    idx_df = pd.DataFrame.from_dict(aggregated_ohlc['idx'][idx_key], orient='index').rename(columns=lambda x: f'idx_{x}')
    opt_df = pd.DataFrame.from_dict(aggregated_ohlc['opt'][opt_key], orient='index').rename(columns=lambda x: f'opt_{x}')

    df = idx_df.join(opt_df, how='inner').sort_index()
    return df

upstox_wss = UpstoxWSS(callback=on_tick_received)

def start_live_feed():
    print("STARTING LIVE FEED...")
    upstox_wss.start()

def change_instrument(opt_key, idx_name='NIFTY'):
    global subscribed_instruments
    idx_key = helper.get_spot_keys().get(idx_name)

    if opt_key not in candles_storage:
        candles_storage[opt_key] = deque(maxlen=MAX_CANDLES)
        analysis_storage[opt_key] = deque(maxlen=MAX_CANDLES)
        engines[opt_key] = OrderFlowEngine()
        opt_to_idx_map[opt_key] = idx_key

        # Bootstrap historical
        try:
            hist_opt = helper.get_historical_candles(opt_key)
            hist_idx = helper.get_historical_candles(idx_key)
            hist_opt.reverse()
            hist_idx.reverse()

            for c in hist_idx:
                ts = pd.to_datetime(c[0]).replace(tzinfo=None)
                update_ohlc('idx', idx_key, ts, c[1], c[5], high=c[2], low=c[3], close=c[4])

            engine = engines[opt_key]
            for c in hist_opt:
                ts = pd.to_datetime(c[0]).replace(tzinfo=None)
                update_ohlc('opt', opt_key, ts, c[1], c[5], high=c[2], low=c[3], close=c[4])

                f_candle = FootprintCandle(c[1], ts)
                f_candle.high, f_candle.low, f_candle.close, f_candle.volume = c[2], c[3], c[4], c[5]
                f_candle.delta = (c[4] - c[1]) * (c[5] / (c[2] - c[3] + 0.001))

                candles_storage[opt_key].append(f_candle)
                engine.cumulative_delta += f_candle.delta
                analysis_storage[opt_key].append(engine.analyze_candle(f_candle, engine.cumulative_delta - f_candle.delta))

        except Exception as e:
            print(f"Error bootstrapping {opt_key}: {e}")

    subscribed_instruments.add(opt_key)
    subscribed_instruments.add(idx_key)
    upstox_wss.update_subscriptions(list(subscribed_instruments))

# For compatibility with app.py if it still uses the old engine reference
engine = OrderFlowEngine()
