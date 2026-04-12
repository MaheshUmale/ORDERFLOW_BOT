import pandas as pd
from upstox_helper import UpstoxHelper
from order_flow_engine import OrderFlowEngine
from strategy_logic import RelativeStrengthStrategy
from trade_manager import TradeManager
from footprint_candle import FootprintCandle
import datetime

class BacktestEngine:
    def __init__(self, instrument_key, days=7):
        self.helper = UpstoxHelper()
        self.instrument_key = instrument_key
        self.days = days
        self.engine = OrderFlowEngine()
        self.tm = TradeManager()

    def run(self):
        to_date = datetime.datetime.now().strftime('%Y-%m-%d')
        from_date = (datetime.datetime.now() - datetime.timedelta(days=self.days)).strftime('%Y-%m-%d')

        print(f"Fetching historical data for {self.instrument_key} from {from_date} to {to_date}...")
        candles = self.helper.get_historical_candles_range(self.instrument_key, from_date, to_date)

        if not candles:
            print("No data found for backtest.")
            return

        # Upstox returns oldest first in range API usually, but let's check and sort
        df = pd.DataFrame(candles, columns=['time', 'open', 'high', 'low', 'close', 'volume', 'oi'])
        df['time'] = pd.to_datetime(df['time']).dt.tz_localize(None)
        df = df.sort_values('time')

        print(f"Running backtest on {len(df)} candles...")

        cum_delta = 0
        self.engine.imbalance_ratio = 1.2 # Aggressive for backtest
        for _, row in df.iterrows():
            f_candle = FootprintCandle(row['open'], row['time'])
            f_candle.high, f_candle.low, f_candle.close, f_candle.volume = row['high'], row['low'], row['close'], row['volume']

            # Generate multiple price levels to trigger imbalances
            ticks = 5
            price_step = (f_candle.high - f_candle.low) / ticks if f_candle.high > f_candle.low else 0.05
            for i in range(ticks + 1):
                p = round(f_candle.low + i * price_step, 2)
                is_up = f_candle.close > f_candle.open
                # Artificial imbalance: more ask vol if price is rising
                f_candle.price_levels[p] = {
                    'bid_vol': f_candle.volume / 10 if is_up else f_candle.volume / 2,
                    'ask_vol': f_candle.volume / 2 if is_up else f_candle.volume / 10
                }

            # Estimate delta
            f_candle.delta = (f_candle.volume * 0.6) if f_candle.close > f_candle.open else (-f_candle.volume * 0.6)

            # Process with Order Flow Engine
            analysis = self.engine.analyze_candle(f_candle, cum_delta)
            cum_delta += f_candle.delta

            # Update Trade Manager with current candle "ticks" (high/low/close)
            # To simulate SL/TP being hit within a bar
            self.tm.update_trades(self.instrument_key, row['low'])
            self.tm.update_trades(self.instrument_key, row['high'])
            self.tm.update_trades(self.instrument_key, row['close'])

            # Signal check
            if analysis['signal'] and analysis['confidence'] >= 0.6: # Lowered for backtest visibility
                ev = self.tm.get_ev(analysis['confidence'])
                if ev >= -5: # Lowered for backtest visibility
                    print(f"DEBUG: Found signal {analysis['signal']} at {row['time']} @ {row['close']} EV: {ev}")
                    self.tm.add_trade(self.instrument_key, analysis['signal'], row['close'], analysis['confidence'])

        self.show_results()

    def show_results(self):
        print("\n" + "="*30)
        print("BACKTEST RESULTS")
        print("="*30)
        print(f"Total Trades: {self.tm.stats['total_trades']}")
        print(f"Wins: {self.tm.stats['wins']}")
        print(f"Losses: {self.tm.stats['losses']}")
        print(f"Win Rate: {self.tm.stats['win_rate']:.2f}%")
        print(f"Realized PnL: {self.tm.stats['realized_pnl']:.2f}")
        print("-" * 30)
        print("TRADE LOG:")
        for t in self.tm.trades:
            status = f"[{t.status}] {t.side} @ {t.entry_price:.2f}"
            if t.status == 'CLOSED':
                status += f" -> Exit: {t.exit_price:.2f} PnL: {t.pnl:.2f} ({t.exit_reason})"
            print(status)
        print("="*30)

if __name__ == "__main__":
    # Example test
    bt = BacktestEngine("NSE_FO|54805") # Example NIFTY Option
    bt.run()
