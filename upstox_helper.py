import os
import requests
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class UpstoxHelper:
    def __init__(self):
        self.api_key = os.getenv('UPSTOX_API_KEY')
        self.access_token = os.getenv('UPSTOX_ACCESS_TOKEN')
        self.base_url = "https://api.upstox.com/v2"
        self._instruments_cache = None

    def get_instruments(self, segment='NSE_FO'):
        if self._instruments_cache is not None:
            return self._instruments_cache

        url = f"https://upstream.upstox.com/market-quote/instruments/{segment}"
        response = requests.get(url)
        if response.status_code == 200:
            import gzip
            from io import StringIO
            content = gzip.decompress(response.content).decode('utf-8')
            df = pd.read_csv(StringIO(content))
            self._instruments_cache = df
            return df
        return None

    def get_spot_keys(self):
        """Get instrument keys for NIFTY and BANKNIFTY spot indices."""
        return {
            'NIFTY': 'NSE_INDEX|Nifty 50',
            'BANKNIFTY': 'NSE_INDEX|Nifty Bank'
        }

    def find_nearest_expiry(self, symbol='NIFTY'):
        df = self.get_instruments()
        if df is None: return None
        symbol_df = df[(df['underlying_symbol'] == symbol) & (df['instrument_type'].isin(['CE', 'PE']))]
        if symbol_df.empty: return None
        symbol_df['expiry'] = pd.to_datetime(symbol_df['expiry'])
        nearest_expiry = symbol_df[symbol_df['expiry'] >= datetime.now()]['expiry'].min()
        if pd.isna(nearest_expiry): return None
        return nearest_expiry.strftime('%Y-%m-%d')

    def get_option_chain(self, symbol='NIFTY', expiry=None):
        df = self.get_instruments()
        if df is None: return []
        if expiry is None:
            expiry = self.find_nearest_expiry(symbol)

        chain_df = df[(df['underlying_symbol'] == symbol) &
                      (df['expiry'] == expiry) &
                      (df['instrument_type'].isin(['CE', 'PE']))]
        return chain_df

    def get_market_data_feed_authorize(self):
        url = f"{self.base_url}/feed/market-data-feed/authorize"
        headers = {
            'Authorization': f"Bearer {self.access_token}",
            'Accept': 'application/json'
        }
        response = requests.get(url, headers=headers)
        return response.json()
