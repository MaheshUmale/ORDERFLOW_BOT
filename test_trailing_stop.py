from trade_manager import TradeManager

def test_trailing_stop():
    tm = TradeManager()
    # Entry 100, SL 95, TP 110
    trade = tm.add_trade("TEST", "BUY", 100, 0.7)
    assert trade.stop_loss == 95

    # Price moves to 103 (Entry + 3)
    tm.update_trades("TEST", 103)
    # potential_new_sl = 103 - 4 = 99
    # 103 > 102, so stop_loss should be max(95, 99) = 99
    print(f"Price: 103, SL: {trade.stop_loss}")
    assert trade.stop_loss == 99

    # Price moves to 105
    tm.update_trades("TEST", 105)
    # potential_new_sl = 105 - 4 = 101
    print(f"Price: 105, SL: {trade.stop_loss}")
    assert trade.stop_loss == 101

    # Price drops to 101
    tm.update_trades("TEST", 101)
    print(f"Price: 101, Status: {trade.status}, Exit Reason: {trade.exit_reason}")
    assert trade.status == 'CLOSED'
    assert trade.exit_reason == 'SL'
    assert trade.exit_price == 101
    assert trade.pnl == 1.0 # 101 - 100

if __name__ == "__main__":
    test_trailing_stop()
    print("Trailing Stop Test Passed!")
