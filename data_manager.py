import pandas as pd
import threading
import time
import random
from collections import deque
from footprint_candle import FootprintCandle
from order_flow_engine import OrderFlowEngine
from strategy_logic import RelativeStrengthStrategy
from indicators import Indicators
from trade_manager import TradeManager
from upstox_wss import UpstoxWSS
from upstox_helper import UpstoxHelper

last_wss_tick_time = 0

# Global Storage for Multiple Instruments
MAX_CANDLES = 100

# Dictionaries keyed by (instrument_key, timeframe)
candles_storage = {}  # {(key, tf): deque(FootprintCandle)}
analysis_storage = {} # {(key, tf): deque(analysis_dict)}
current_candles = {}  # {(key, tf): FootprintCandle}
engines = {}         # {(key, tf): OrderFlowEngine}
aggregated_ohlc = {'idx': {}, 'opt': {}} # Keep this for RS, but might need keying too if multi-index

data_lock = threading.RLock()
# For simplicity in RS, we map option_key -> index_key
opt_to_idx_map = {}

helper = UpstoxHelper()
rs_strategy = RelativeStrengthStrategy()
trade_manager = TradeManager(helper=helper)

# Active set of keys to subscribe to
subscribed_instruments = set()

def on_tick_received(instrument_key, price, volume, is_buy):
    global last_wss_tick_time
    last_wss_tick_time = time.time()
    now = pd.Timestamp.now(tz='Asia/Kolkata').replace(tzinfo=None)

    # Fast path
    if instrument_key not in subscribed_instruments:
        return

    with data_lock:
        trade_manager.update_trades(instrument_key, price)

        # Process multiple timeframes: 1m, 5m, 15m
        for tf in ['1min', '5min', '15min']:
            ts_floor = now.floor(tf)
            storage_key = (instrument_key, tf)
            curr_key = (instrument_key, tf)

            if storage_key in candles_storage:
                if curr_key not in current_candles or current_candles[curr_key] is None or current_candles[curr_key].start_time != ts_floor:
                    if curr_key in current_candles and current_candles[curr_key] is not None:
                        old_candle = current_candles[curr_key]
                        candles_storage[storage_key].append(old_candle)

                        engine = engines.get(curr_key)
                        if engine:
                            engine.cumulative_delta += old_candle.delta
                            analysis = engine.analyze_candle(old_candle, engine.cumulative_delta - old_candle.delta)
                            analysis_storage[storage_key].append(analysis)

                            # Only execute trades from 1m TF to avoid duplicates
                            if tf == '1min' and analysis.get('signal') and analysis.get('confidence', 0) > 0.6:
                                ev = trade_manager.get_ev(analysis['confidence'])
                                if ev > 0:
                                    print(f"AUTO-TRADE: {analysis['signal']} on {instrument_key} @ {old_candle.close} (EV: {ev:.1f})", flush=True)
                                    trade_manager.add_trade(instrument_key, analysis['signal'], old_candle.close, analysis['confidence'])

                    if candles_storage[storage_key] and candles_storage[storage_key][-1].start_time == ts_floor:
                        candles_storage[storage_key].pop()

                    current_candles[curr_key] = FootprintCandle(price, ts_floor)

                current_candles[curr_key].add_tick(price, volume, is_buy)

        # Update synced OHLC (1m base)
        ts_1m = now.floor('1min')
        update_ohlc('opt', instrument_key, ts_1m, price, volume)
        spot_keys = helper.get_spot_keys().values()
        if instrument_key in spot_keys:
            update_ohlc('idx', instrument_key, ts_1m, price, 0)

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

def get_all_opt_candles(instrument_key, tf='1min'):
    with data_lock:
        key = (instrument_key, tf)
        if key not in candles_storage: return []
        all_c = list(candles_storage[key])
        if key in current_candles and current_candles[key]:
            # Ensure no double timestamp
            if not all_c or all_c[-1].start_time != current_candles[key].start_time:
                all_c.append(current_candles[key])
        return all_c

def get_opt_df_with_indicators(instrument_key, tf='1min'):
    candles = get_all_opt_candles(instrument_key, tf)
    if not candles: return pd.DataFrame()

    df = pd.DataFrame([{
        'time': c.start_time, 'open': c.open, 'high': c.high, 'low': c.low, 'close': c.close, 'volume': c.volume, 'delta': c.delta
    } for c in candles]).drop_duplicates(subset='time', keep='last')

    df = Indicators.calculate_vwap(df)
    return df

def get_volume_profile(instrument_key, tf='1min'):
    candles = get_all_opt_candles(instrument_key, tf)
    if not candles: return {}

    profile = {}
    # Aggregate volume across last 50 candles for the profile
    recent_candles = candles[-50:]
    for c in recent_candles:
        for price, data in c.price_levels.items():
            profile[price] = profile.get(price, 0) + data['bid_vol'] + data['ask_vol']

    return profile

def get_synced_df(opt_key):
    with data_lock:
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
    import os
    if os.getenv("MOCK_DATA") == "TRUE":
        threading.Thread(target=run_mock_feed, daemon=True).start()
    else:
        upstox_wss.start()

def run_mock_feed():
    print("STARTING MOCK FEED...", flush=True)
    while True:
        with data_lock:
            active_keys = list(subscribed_instruments)
        if not active_keys:
            time.sleep(1)
            continue

        for key in active_keys:
            # Generate a random tick
            price = 100 + random.random() * 10
            vol = random.randint(1, 500)
            is_buy = random.random() > 0.5
            on_tick_received(key, price, vol, is_buy)
        time.sleep(0.5)

def change_instrument(opt_key, idx_name='NIFTY'):
    global subscribed_instruments
    idx_key = helper.get_spot_keys().get(idx_name)

    with data_lock:
        # Bootstrap all timeframes
        for tf in ['1min', '5min', '15min']:
            key = (opt_key, tf)
            if key not in candles_storage:
                candles_storage[key] = deque(maxlen=MAX_CANDLES)
                analysis_storage[key] = deque(maxlen=MAX_CANDLES)
            if key not in engines:
                engines[key] = OrderFlowEngine()

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

            engine_1m = engines[(opt_key, '1min')]
            for c in hist_opt:
                ts = pd.to_datetime(c[0]).replace(tzinfo=None)
                update_ohlc('opt', opt_key, ts, c[1], c[5], high=c[2], low=c[3], close=c[4])

                f_candle = FootprintCandle(c[1], ts)
                f_candle.high, f_candle.low, f_candle.close, f_candle.volume = c[2], c[3], c[4], c[5]
                # Estimate delta
                f_candle.delta = (c[4] - c[1]) * (c[5] / (max(0.1, c[2] - c[3])))

                candles_storage[(opt_key, '1min')].append(f_candle)
                engine_1m.cumulative_delta += f_candle.delta
                analysis_storage[(opt_key, '1min')].append(engine_1m.analyze_candle(f_candle, engine_1m.cumulative_delta - f_candle.delta))

            # Aggregate MTF bootstrapping
            df_hist = pd.DataFrame(hist_opt, columns=['time', 'open', 'high', 'low', 'close', 'volume', 'oi'])
            df_hist['time'] = pd.to_datetime(df_hist['time']).dt.tz_localize(None)
            for tf in ['5min', '15min']:
                df_resampled = df_hist.set_index('time').resample(tf).agg({
                    'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
                }).dropna()
                engine_tf = engines[(opt_key, tf)]
                for ts, r in df_resampled.iterrows():
                    mtf_candle = FootprintCandle(r['open'], ts)
                    mtf_candle.high, mtf_candle.low, mtf_candle.close, mtf_candle.volume = r['high'], r['low'], r['close'], r['volume']
                    mtf_candle.delta = (r['close'] - r['open']) * (r['volume'] / (max(0.1, r['high'] - r['low'])))
                    candles_storage[(opt_key, tf)].append(mtf_candle)

                    engine_tf.cumulative_delta += mtf_candle.delta
                    analysis_storage[(opt_key, tf)].append(engine_tf.analyze_candle(mtf_candle, engine_tf.cumulative_delta - mtf_candle.delta))

        except Exception as e:
            print(f"Error bootstrapping {opt_key}: {e}", flush=True)

    subscribed_instruments.add(opt_key)
    subscribed_instruments.add(idx_key)
    upstox_wss.update_subscriptions(list(subscribed_instruments))

# For compatibility with app.py if it still uses the old engine reference
engine = OrderFlowEngine()
