import pandas as pd
import numpy as np
from footprint_candle import FootprintCandle
from order_flow_engine import OrderFlowEngine
from pivot_algorithm import AutoTrendSupportResistance
from strategy_logic import RelativeStrengthStrategy

def test_order_flow_signals():
    print("Testing Order Flow Signals...")
    engine = OrderFlowEngine(imbalance_ratio=3.0)

    candle = FootprintCandle(100, pd.Timestamp.now())
    candle.add_tick(100, 10, False)
    candle.add_tick(101, 35, True)

    analysis = engine.analyze_candle(candle)
    assert any(imb['type'] == 'Buy' and imb['price'] == 101 for imb in analysis['imbalances']), "Buy imbalance not detected"
    print("✓ Imbalance detection passed")

    candle2 = FootprintCandle(100, pd.Timestamp.now())
    candle2.add_tick(100, 50, True)
    candle2.add_tick(101, 10, True)
    candle2.add_tick(102, 10, True)
    analysis2 = engine.analyze_candle(candle2)
    assert 100 in analysis2['absorption_zones'], "Absorption zone at 100 not detected"
    print("✓ Absorption detection passed")

def test_rs_logic():
    print("Testing RS Logic...")
    rs = RelativeStrengthStrategy(swing_window=1)

    # Create mock synced data
    # Timestamps for 5 minutes
    ts = pd.date_range("2026-04-10 10:00:00", periods=10, freq="min")
    data = {
        'idx_open':  [100, 101, 102, 100, 98,  97,  96,  95,  94,  93],
        'idx_high':  [101, 102, 103, 101, 99,  98,  97,  96,  95,  94],
        'idx_low':   [ 99, 100, 101,  99, 97,  96,  95,  94,  93,  92],
        'idx_close': [100, 101, 102, 100, 98,  97,  96,  95,  94,  93],
        'opt_open':  [10,  11,  12,  11,  10,  10,  10,  11,  12,  13],
        'opt_high':  [11,  12,  13,  12,  11,  11,  11,  12,  13,  14],
        'opt_low':   [ 9,  10,  11,  10,   9,   9,   9,  10,  11,  12],
        'opt_close': [10,  11,  12,  11,  10,  10,  10,  11,  12,  13],
        'opt_volume':[10,  10,  10,  10,  10,  10,  10,  50,  50,  50]
    }
    df = pd.DataFrame(data, index=ts)

    df = rs.detect_signals(df)

    # In this data:
    # idx makes new low at end
    # opt holds low at 9 and then moves up with volume

    assert 'rs_bullish_signal' in df.columns
    print("✓ RS signal detection logic executed")

if __name__ == "__main__":
    try:
        test_order_flow_signals()
        test_rs_logic()
        print("\nALL TESTS PASSED!")
    except AssertionError as e:
        print(f"\nTEST FAILED: {e}")
        exit(1)
    except Exception as e:
        print(f"\nAN ERROR OCCURRED: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
