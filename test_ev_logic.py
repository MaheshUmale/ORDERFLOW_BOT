import pandas as pd
from trade_manager import TradeManager
from order_flow_engine import OrderFlowEngine
from footprint_candle import FootprintCandle
import datetime

def test_ev_and_trades():
    tm = TradeManager()
    ofe = OrderFlowEngine()

    # 1. Simulate a series of ticks that form an imbalance BUY signal
    # We'll create a candle and add ticks to it.
    ts = datetime.datetime.now()
    candle = FootprintCandle(100, ts)

    # Add ticks to create Buy Imbalances
    # Levels: 100, 101, 102
    candle.add_tick(100, 100, False) # Bid vol at 100
    candle.add_tick(101, 400, True)  # Ask vol at 101 (4x Bid at 100 -> Imbalance)
    candle.add_tick(101, 100, False) # Bid vol at 101
    candle.add_tick(102, 400, True)  # Ask vol at 102 (4x Bid at 101 -> Imbalance)

    candle.close = 102
    candle.delta = 600 # (400+400) - (100+100)

    analysis = ofe.analyze_candle(candle)
    print(f"Analysis Signal: {analysis['signal']}, Confidence: {analysis['confidence']}")

    assert analysis['signal'] == 'BUY'
    assert analysis['confidence'] > 0.5

    ev = tm.get_ev(analysis['confidence'])
    print(f"Calculated EV: {ev}")
    assert ev > 0

    # 2. Add trade
    trade = tm.add_trade("TEST", analysis['signal'], candle.close, analysis['confidence'])
    print(f"Trade Added: Side={trade.side}, Entry={trade.entry_price}, SL={trade.stop_loss}, TP={trade.take_profit}")

    assert trade.status == 'OPEN'

    # 3. Simulate price movement to hit TP
    tm.update_trades("TEST", 105)
    tm.update_trades("TEST", 110)
    tm.update_trades("TEST", 115) # Should hit TP (102 + 10)

    print(f"Trade Status: {trade.status}, Exit Reason: {trade.exit_reason}, PnL: {trade.pnl}")
    assert trade.status == 'CLOSED'
    assert trade.exit_reason == 'TP'
    assert trade.pnl == 10.0

    print(f"Final Stats: {tm.stats}")
    assert tm.stats['wins'] == 1
    assert tm.stats['realized_pnl'] == 10.0

if __name__ == "__main__":
    test_ev_and_trades()
    print("Test passed!")
