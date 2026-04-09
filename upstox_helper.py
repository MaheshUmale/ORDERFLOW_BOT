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
        self.base_url_v3 = "https://api.upstox.com/v3"
        self._instruments_cache = None

    def get_instruments(self):
        if self._instruments_cache is not None:
            return self._instruments_cache

        url = "https://assets.upstox.com/market-quote/instruments/exchange/complete.csv.gz"
        try:
            df = pd.read_csv(url, compression='gzip')
            self._instruments_cache = df
            return df
        except Exception as e:
            print(f"Error fetching instruments: {e}")
            return None

    def get_spot_keys(self):
        return {
            'NIFTY': 'NSE_INDEX|Nifty 50',
            'BANKNIFTY': 'NSE_INDEX|Nifty Bank'
        }

    def find_nearest_expiry(self, symbol='NIFTY'):
        df = self.get_instruments()
        if df is None: return None
        symbol_df = df[(df['name'] == symbol) & (df['exchange'] == 'NSE_FO')]
        if symbol_df.empty: return None

        symbol_df['expiry'] = pd.to_datetime(symbol_df['expiry'])
        today = datetime.now().date()
        future_expiries = symbol_df[symbol_df['expiry'].dt.date >= today]['expiry']
        if future_expiries.empty:
            nearest_expiry = symbol_df['expiry'].max()
        else:
            nearest_expiry = future_expiries.min()
        return nearest_expiry.strftime('%Y-%m-%d')

    def get_option_chain(self, symbol='NIFTY', expiry=None):
        df = self.get_instruments()
        if df is None: return pd.DataFrame()

        if expiry is None:
            expiry = self.find_nearest_expiry(symbol)

        if expiry is None: return pd.DataFrame()

        chain_df = df[(df['name'] == symbol) &
                      (df['expiry'] == expiry) &
                      (df['exchange'] == 'NSE_FO') &
                      (df['instrument_type'].isin(['OPTIDX', 'OPTSTK']))].copy()

        chain_df['label'] = chain_df.apply(lambda r: f"{r['name']} {int(r['strike'])} {r['option_type']} ({pd.to_datetime(r['expiry']).strftime('%Y-%m-%d')})", axis=1)
        return chain_df

    def get_market_data_feed_authorize(self):
        url = f"{self.base_url_v3}/feed/market-data-feed/authorize"
        headers = {
            'Authorization': f"Bearer {self.access_token}",
            'Accept': 'application/json'
        }
        response = requests.get(url, headers=headers)
        return response.json()

    def get_historical_candles(self, instrument_key, interval='1minute'):
        """Fetch intraday candles for bootstrapping."""
        url = f"{self.base_url}/market-quote/ohlc/interval/{instrument_key}/{interval}"
        headers = {
            'Authorization': f"Bearer {self.access_token}",
            'Accept': 'application/json'
        }
        # In reality V3 might have a different structure, but usually OHLC is V2.
        # If user insisted on V3, we'd use base_url_v3.
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'success':
                # Upstox returns candles in data[instrument_key][interval]
                return data['data'][instrument_key][interval]
        return []
