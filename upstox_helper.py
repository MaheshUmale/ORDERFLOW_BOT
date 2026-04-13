import os
import requests
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class UpstoxHelper:
    def __init__(self):
        # Access Token is the primary authentication for the provided environment
        self.access_token = os.getenv("UPSTOX_ACCESS_TOKEN", "")
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
        # Correct Upstox V2 Historical Intraday endpoint
        url = f"{self.base_url}/historical-candle/intraday/{instrument_key}/{interval}"
        headers = {
            'Authorization': f"Bearer {self.access_token}",
            'Accept': 'application/json'
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'success':
                # Upstox returns candles in data['candles'] as list of lists
                # [timestamp, open, high, low, close, volume, oi]
                return data['data']['candles']
        else:
            print(f"Historical API Error {response.status_code}: {response.text}")
        return []

    def place_order(self, instrument_key, side, quantity, price=0, order_type='MARKET'):
        """Place an order using Upstox V2 API."""
        url = f"{self.base_url}/order/place"
        headers = {
            'Authorization': f"Bearer {self.access_token}",
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        data = {
            "quantity": quantity,
            "product": "I", # Intraday
            "validity": "DAY",
            "price": price,
            "tag": "OF_BOT",
            "instrument_token": instrument_key,
            "order_type": order_type,
            "transaction_type": "BUY" if side == 'BUY' else "SELL",
            "disclosed_quantity": 0,
            "trigger_price": 0,
            "is_amo": False
        }
        try:
            response = requests.post(url, headers=headers, json=data)
            return response.json()
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_historical_candles_range(self, instrument_key, from_date, to_date, interval='1minute'):
        """Fetch historical candles for a specific range."""
        url = f"{self.base_url}/historical-candle/{instrument_key}/{interval}/{to_date}/{from_date}"
        headers = {
            'Authorization': f"Bearer {self.access_token}",
            'Accept': 'application/json'
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'success':
                return data['data']['candles']
        else:
            print(f"Historical Range API Error {response.status_code}: {response.text}")
        return []
