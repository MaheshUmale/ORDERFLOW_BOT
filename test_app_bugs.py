import pandas as pd
from data_manager import get_opt_df_with_indicators, get_all_opt_candles, analysis_storage, engines, engine
from order_flow_engine import OrderFlowEngine
from footprint_candle import FootprintCandle
import datetime

def test_app_logic_simulation():
    instrument_key = "TEST_INST"
    # Mock some data
    ts = datetime.datetime.now()
    c = FootprintCandle(100, ts)
    c.add_tick(101, 100, True)
    c.close = 101

    # 1. Prepare Data (simulating what app.py does)
    # We need to manually populate storage since we're not running the full app
    from data_manager import candles_storage
    candles_storage[instrument_key] = [c]
    engines[instrument_key] = OrderFlowEngine()

    df_opt = get_opt_df_with_indicators(instrument_key)
    print(f"df_opt columns: {df_opt.columns}")

    inst_analysis = list(analysis_storage.get(instrument_key, []))
    inst_engine = engines.get(instrument_key, engine)

    all_opt_candles = get_all_opt_candles(instrument_key)
    if not df_opt.empty:
        last_c = all_opt_candles[-1]
        # This is where the reviewer said it would fail
        try:
            prev_cum_delta = inst_analysis[-1]['cum_delta'] if inst_analysis else 0
            print(f"prev_cum_delta: {prev_cum_delta}")
        except KeyError as e:
            print(f"Caught expected KeyError: {e}")
            raise

        current_c_analysis = inst_engine.analyze_candle(last_c, prev_cum_delta)
        print(f"current_c_analysis keys: {current_c_analysis.keys()}")
        display_analysis = inst_analysis + [current_c_analysis]
    else:
        display_analysis = inst_analysis

    analysis_df = pd.DataFrame(display_analysis).drop_duplicates(subset='time', keep='last')
    print(f"analysis_df columns: {analysis_df.columns}")

    # Merge
    df_merged = pd.merge(df_opt, analysis_df, on='time', how='inner', suffixes=('', '_an'))
    print(f"df_merged shape: {df_merged.shape}")
    if not df_merged.empty:
        print(f"df_merged first row: {df_merged.iloc[0].to_dict()}")

if __name__ == "__main__":
    try:
        test_app_logic_simulation()
        print("Test Simulation Passed!")
    except Exception as e:
        print(f"Test Simulation Failed: {e}")
        import traceback
        traceback.print_exc()
