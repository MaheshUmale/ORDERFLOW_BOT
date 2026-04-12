import pandas as pd
import numpy as np

class Indicators:
    @staticmethod
    def calculate_vwap(df):
        """
        Calculate Anchored VWAP and Standard Deviation Bands.
        Expects df with 'close', 'volume', and 'high', 'low' if bands are needed.
        """
        if df.empty:
            return df

        # Cumulative Typical Price * Volume
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        v_tp = typical_price * df['volume']

        df['cum_v_tp'] = v_tp.cumsum()
        df['cum_vol'] = df['volume'].cumsum()

        df['vwap'] = df['cum_v_tp'] / df['cum_vol']

        # Standard Deviation Bands (based on price variance from VWAP)
        # Using a rolling window for variance to make it dynamic, or cumulative for anchored
        variance = ((typical_price - df['vwap'])**2 * df['volume']).cumsum() / df['cum_vol']
        df['vwap_std'] = np.sqrt(variance)

        df['vwap_upper1'] = df['vwap'] + df['vwap_std']
        df['vwap_lower1'] = df['vwap'] - df['vwap_std']
        df['vwap_upper2'] = df['vwap'] + (2 * df['vwap_std'])
        df['vwap_lower2'] = df['vwap'] - (2 * df['vwap_std'])

        return df
