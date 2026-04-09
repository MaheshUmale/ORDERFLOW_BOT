import pandas as pd
import numpy as np

class RelativeStrengthStrategy:
    def __init__(self, swing_window=3):
        self.swing_window = swing_window

    def find_swings(self, df, prefix):
        """Identify Swing Highs and Lows."""
        window_size = 2 * self.swing_window + 1
        low_col = f'{prefix}_low'
        high_col = f'{prefix}_high'

        # Local extrema
        is_min = df[low_col].rolling(window=window_size, center=True).apply(
            lambda x: 1 if x.iloc[self.swing_window] == x.min() else 0, raw=False
        )
        is_max = df[high_col].rolling(window=window_size, center=True).apply(
            lambda x: 1 if x.iloc[self.swing_window] == x.max() else 0, raw=False
        )

        # Shift to avoid lookahead
        df[f'{prefix}_is_sl'] = is_min.shift(self.swing_window)
        df[f'{prefix}_is_sh'] = is_max.shift(self.swing_window)

        # Track last swing level
        df[f'{prefix}_last_sl'] = df[low_col].shift(self.swing_window).where(df[f'{prefix}_is_sl'] == 1).ffill()
        df[f'{prefix}_last_sh'] = df[high_col].shift(self.swing_window).where(df[f'{prefix}_is_sh'] == 1).ffill()

        return df

    def detect_signals(self, df):
        """
        Detect RS Signals based on divergence:
        Bullish: Index breaks Major SL, but CE holds its Major SL.
        Bearish: Index breaks Major SH, but PE holds its Major SH (Inverse of relative strength).
        """
        # We need data for 'idx' (Spot Index) and 'opt' (Selected Option)
        for p in ['idx', 'opt']:
            df = self.find_swings(df, p)

        # RS Setup: Index breaches previous SL, but Option holds its previous SL
        # Note: Strategy description says premiums refuse to fall despite Index making new lows.
        idx_new_low = df['idx_low'] < df['idx_last_sl']
        opt_holds_low = df['opt_low'] >= df['opt_last_sl']

        # Trigger: Aggression (Volume spike + Price uptick)
        # Volume > 1.5 * SMA(20)
        vol_sma = df['opt_volume'].rolling(window=20).mean()
        vol_trigger = df['opt_volume'] > (1.5 * vol_sma)
        # Price uptick: Close > High of the swing low formation candle
        # For simplicity, we'll check if Close > previous High
        price_trigger = df['opt_close'] > df['opt_high'].shift(1)

        df['rs_bullish_signal'] = idx_new_low & opt_holds_low & vol_trigger & price_trigger

        return df
