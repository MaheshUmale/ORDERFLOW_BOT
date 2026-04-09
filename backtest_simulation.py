import pandas as pd
from footprint_candle import FootprintCandle
from order_flow_engine import OrderFlowEngine
from pivot_algorithm import AutoTrendSupportResistance

def test_order_flow_signals():
    print("Testing Order Flow Signals...")
    engine = OrderFlowEngine(imbalance_ratio=3.0)

    # Create a candle with a clear imbalance
    candle = FootprintCandle(100, pd.Timestamp.now())
    # Diagonal imbalance: Ask at 101 vs Bid at 100
    candle.add_tick(100, 10, False) # 10 Bid at 100
    candle.add_tick(101, 35, True)  # 35 Ask at 101 (Ratio 3.5 > 3.0)

    analysis = engine.analyze_candle(candle)
    assert any(imb['type'] == 'Buy' and imb['price'] == 101 for imb in analysis['imbalances']), "Buy imbalance not detected"
    print("✓ Imbalance detection passed")

    # Test Absorption (The Wall)
    candle2 = FootprintCandle(100, pd.Timestamp.now())
    candle2.add_tick(100, 50, True) # 50 volume at 100
    candle2.add_tick(101, 10, True) # 10 volume at 101
    candle2.add_tick(102, 10, True) # 10 volume at 102
    # Total volume = 70. Level 100 has 50/70 = 71% > 40%
    analysis2 = engine.analyze_candle(candle2)
    assert 100 in analysis2['absorption_zones'], "Absorption zone at 100 not detected"
    print("✓ Absorption detection passed")

def test_pivot_logic():
    print("Testing Pivot Logic...")
    indicator = AutoTrendSupportResistance(required_ticks_for_broken=4, tick_size=1)

    # Create a sequence of bars to form a high pivot
    # Bar 0: Low=90, High=100, Open=90, Close=100
    indicator.update(0, 90, 100, 90, 100) # Initial pivot (Low)

    # Bar 1: Open=100, High=110, Low=100, Close=110
    indicator.update(1, 100, 110, 100, 110)

    # Bar 2: Open=110, High=105, Low=100, Close=100 (Lower High)
    indicator.update(2, 110, 105, 100, 100)

    assert any(p.is_high and p.price == 110 for p in indicator.pivots), "High pivot at 110 not found"
    print("✓ Pivot creation passed")

    # Test level testing/broken
    # High pivot at 110. Threshold = 4 * 1 = 4. Broken if > 114. Tested if 110-114.
    pivot = next(p for p in indicator.pivots if p.is_high and p.price == 110)

    # Test level tested
    indicator.update(3, 100, 112, 100, 105)
    assert pivot.is_level_tested, "Level should be tested at 112"
    print("✓ Level tested logic passed")

    # Test level broken
    indicator.update(4, 105, 115, 105, 110)
    assert pivot.is_level_broken, "Level should be broken at 115"
    assert not pivot.display_level, "Broken level should not be displayed"
    print("✓ Level broken logic passed")

if __name__ == "__main__":
    try:
        test_order_flow_signals()
        test_pivot_logic()
        print("\nALL TESTS PASSED!")
    except AssertionError as e:
        print(f"\nTEST FAILED: {e}")
        exit(1)
    except Exception as e:
        print(f"\nAN ERROR OCCURRED: {e}")
        exit(1)
