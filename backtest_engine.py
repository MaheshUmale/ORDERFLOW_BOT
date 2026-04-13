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

    def run(self, idx_key='NSE_INDEX|Nifty 50'):
        to_date = datetime.datetime.now().strftime('%Y-%m-%d')
        from_date = (datetime.datetime.now() - datetime.timedelta(days=self.days)).strftime('%Y-%m-%d')

        print(f"Fetching historical data for {self.instrument_key} and {idx_key} from {from_date} to {to_date}...")
        opt_candles = self.helper.get_historical_candles_range(self.instrument_key, from_date, to_date)
        idx_candles = self.helper.get_historical_candles_range(idx_key, from_date, to_date)

        if not opt_candles or not idx_candles:
            print("Missing data for backtest.")
            return

        df_opt = pd.DataFrame(opt_candles, columns=['time', 'open', 'high', 'low', 'close', 'volume', 'oi'])
        df_idx = pd.DataFrame(idx_candles, columns=['time', 'open', 'high', 'low', 'close', 'volume', 'oi'])

        for df in [df_opt, df_idx]:
            df['time'] = pd.to_datetime(df['time']).dt.tz_localize(None)
            df.set_index('time', inplace=True)
            df.sort_index(inplace=True)

        # Merge for RS Strategy
        df_merged = df_idx.join(df_opt, how='inner', lsuffix='_idx', rsuffix='_opt').dropna()

        # Detect RS Signals
        rs_strategy = RelativeStrengthStrategy()

        new_cols = {
            'open_idx': 'idx_open', 'high_idx': 'idx_high', 'low_idx': 'idx_low', 'close_idx': 'idx_close', 'volume_idx': 'idx_volume',
            'open_opt': 'opt_open', 'high_opt': 'opt_high', 'low_opt': 'opt_low', 'close_opt': 'opt_close', 'volume_opt': 'opt_volume'
        }
        df_merged.rename(columns=new_cols, inplace=True)

        df_rs = rs_strategy.detect_signals(df_merged)

        print(f"Running backtest on {len(df_rs)} synchronized candles...")

        cum_delta = 0
        self.engine.imbalance_ratio = 1.2
        for ts, row in df_rs.iterrows():
            f_candle = FootprintCandle(row['opt_open'], ts)
            f_candle.high, f_candle.low, f_candle.close, f_candle.volume = row['opt_high'], row['opt_low'], row['opt_close'], row['opt_volume']

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
            self.tm.update_trades(self.instrument_key, row['opt_low'])
            self.tm.update_trades(self.instrument_key, row['opt_high'])
            self.tm.update_trades(self.instrument_key, row['opt_close'])

            # 1. Order Flow Signals
            if analysis['signal'] and analysis['confidence'] >= 0.6:
                ev = self.tm.get_ev(analysis['confidence'])
                if ev > 0:
                    self.tm.add_trade(self.instrument_key, analysis['signal'], row['opt_close'], analysis['confidence'])

            # 2. RS Signals
            if row.get('rs_bullish_signal'):
                print(f"DEBUG: Found RS BUY at {ts} @ {row['opt_close']}")
                self.tm.add_trade(self.instrument_key, 'BUY', row['opt_close'], 0.8)

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
