import asyncio
import websockets
from upstox_client.feeder.proto import MarketDataFeedV3_pb2 as pb
from google.protobuf.json_format import MessageToDict
import threading
import json
from upstox_helper import UpstoxHelper

class UpstoxWSS:
    def __init__(self, callback):
        self.callback = callback
        self.helper = UpstoxHelper()
        self.websocket = None
        self.loop = None
        self.subscribed_keys = set()
        self._thread = None

    async def connect(self):
        auth_response = self.helper.get_market_data_feed_authorize()
        if 'data' not in auth_response:
            print("Failed to authorize market data feed:", auth_response)
            return

        authorized_url = auth_response['data']['authorized_redirect_uri']

        async with websockets.connect(authorized_url) as websocket:
            self.websocket = websocket
            print("Connected to Upstox WSS")

            if self.subscribed_keys:
                await self._subscribe(list(self.subscribed_keys))

            while True:
                try:
                    message = await websocket.recv()
                    self.handle_message(message)
                except websockets.ConnectionClosed:
                    print("WSS connection closed")
                    break
                except Exception as e:
                    print(f"Error in WSS loop: {e}")

    def handle_message(self, message):
        feed_response = pb.FeedResponse()
        feed_response.ParseFromString(message)
        data = MessageToDict(feed_response)

        if 'feeds' in data:
            for instrument_key, feed in data['feeds'].items():
                ltp = 0
                volume = 0
                bid = 0
                ask = 0

                # Extract data from MarketFullFeed or MarketLTPC
                if 'ff' in feed and 'marketFF' in feed['ff']:
                    mff = feed['ff']['marketFF']
                    ltp = mff.get('ltpc', {}).get('ltp', 0)
                    volume = mff.get('ltpc', {}).get('v', 0)
                    # Get top level bid/ask for trade side detection
                    market_levels = mff.get('marketLevels', {})
                    bid_levels = market_levels.get('bidBuyDiff', [])
                    ask_levels = market_levels.get('askSellDiff', [])
                    if bid_levels: bid = bid_levels[0].get('price', 0)
                    if ask_levels: ask = ask_levels[0].get('price', 0)
                elif 'ltpc' in feed:
                    ltp = feed.get('ltpc', {}).get('ltp', 0)
                    volume = feed.get('ltpc', {}).get('v', 0)

                if ltp > 0:
                    # Side detection: LTP closer to Ask -> Buy, closer to Bid -> Sell
                    is_buy = True
                    if ask > bid > 0:
                        is_buy = abs(ltp - ask) <= abs(ltp - bid)

                    self.callback(instrument_key, ltp, volume, is_buy)

    async def _subscribe(self, instrument_keys):
        if self.websocket:
            data = {
                "guid": "someguid",
                "method": "sub",
                "data": {
                    "mode": "full",
                    "instrumentKeys": instrument_keys
                }
            }
            await self.websocket.send(json.dumps(data).encode('utf-8'))
            self.subscribed_keys.update(instrument_keys)

    async def _unsubscribe(self, instrument_keys):
        if self.websocket:
            data = {
                "guid": "someguid",
                "method": "unsub",
                "data": {
                    "instrumentKeys": instrument_keys
                }
            }
            await self.websocket.send(json.dumps(data).encode('utf-8'))
            for key in instrument_keys:
                self.subscribed_keys.discard(key)

    def start(self):
        if self._thread and self._thread.is_alive(): return
        self.loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self._thread.start()

    def _run_event_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.connect())

    def update_subscriptions(self, instrument_keys):
        """Update the active list of subscribed instruments."""
        if not self.loop: return

        to_remove = list(self.subscribed_keys - set(instrument_keys))
        to_add = list(set(instrument_keys) - self.subscribed_keys)

        if to_remove:
            asyncio.run_coroutine_threadsafe(self._unsubscribe(to_remove), self.loop)
        if to_add:
            asyncio.run_coroutine_threadsafe(self._subscribe(to_add), self.loop)
