import os
import pandas as pd
from upstox_helper import UpstoxHelper

helper = UpstoxHelper()
df = helper.get_instruments()
if df is not None:
    # Filter for NIFTY FO
    nifty_fo = df[(df['name'] == 'NIFTY') & (df['exchange'] == 'NSE_FO')].copy()
    nifty_fo['expiry'] = pd.to_datetime(nifty_fo['expiry'])

    # Expiry for 2026-04-09 or later
    valid = nifty_fo[nifty_fo['expiry'] >= '2026-04-09'].sort_values('expiry')
    if not valid.empty:
        expiry = valid['expiry'].iloc[0]
        print(f"Nearest Expiry: {expiry}")
        subset = valid[valid['expiry'] == expiry]
        # Show a few
        print(subset.head(20)[['instrument_key', 'tradingsymbol', 'strike', 'option_type']])
    else:
        print("No valid expiries found.")
else:
    print("Could not fetch instruments.")
