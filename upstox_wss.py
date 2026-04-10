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
        self.last_volumes = {} # Store last cumulative volume per instrument
        self.loop = None
        self.pending_subscriptions = set()
        self.subscribed_keys = set()
        self._thread = None

    async def connect(self):
        auth_response = self.helper.get_market_data_feed_authorize()
        if 'status' not in auth_response or auth_response['status'] != 'success':
            print("Failed to authorize market data feed:", auth_response, flush=True)
            return

        authorized_url = auth_response['data']['authorized_redirect_uri']

        async with websockets.connect(authorized_url) as websocket:
            self.websocket = websocket
            print("Connected to Upstox WSS", flush=True)

            # Subscribe to any keys that were requested before connection
            if self.pending_subscriptions:
                keys_to_sub = list(self.pending_subscriptions)
                print(f"Subscribing to pending keys: {keys_to_sub}", flush=True)
                await self._subscribe(keys_to_sub)
                self.pending_subscriptions.clear()

            # Also re-subscribe to already tracked keys if reconnecting
            elif self.subscribed_keys:
                await self._subscribe(list(self.subscribed_keys))

            while True:
                try:
                    message = await websocket.recv()
                    self.handle_message(message)
                except websockets.ConnectionClosed:
                    print("WSS connection closed", flush=True)
                    break
                except Exception as e:
                    print(f"Error in WSS loop: {e}", flush=True)

    def handle_message(self, message):
        feed_response = pb.FeedResponse()
        feed_response.ParseFromString(message)
        # Using default CamelCase to match user provided format
        data = MessageToDict(feed_response)

        if 'feeds' in data:
            for instrument_key, feed in data['feeds'].items():
                ltp = 0
                tick_volume = 0
                bid = 0
                ask = 0

                # Robust extraction handling CamelCase keys
                ff = feed.get('fullFeed', {})
                iff = ff.get('indexFF') or feed.get('indexFF', {})
                mff = ff.get('marketFF') or feed.get('marketFF', {})

                if iff:
                    ltpc = iff.get('ltpc', {})
                    ltp = ltpc.get('ltp', 0)
                elif mff:
                    ltpc = mff.get('ltpc', {})
                    ltp = ltpc.get('ltp', 0)

                    # ltq is the last traded quantity for THIS tick (TS)
                    ltq = ltpc.get('ltq', 0)
                    try:
                        tick_volume = int(ltq)
                    except:
                        tick_volume = 0

                    ml = mff.get('marketLevel', {})
                    baq = ml.get('bidAskQuote', [])
                    if baq:
                        bid = baq[0].get('bidP', 0)
                        ask = baq[0].get('askP', 0)

                # Final fallback to top-level ltpc
                if ltp == 0 and 'ltpc' in feed:
                    ltpc = feed['ltpc']
                    ltp = ltpc.get('ltp', 0)
                    ltq = ltpc.get('ltq', 0)
                    try:
                        tick_volume = int(ltq)
                    except:
                        pass

                if ltp > 0:
                    is_buy = True
                    if ask > bid > 0:
                        is_buy = abs(ltp - ask) <= abs(ltp - bid)

                    # REQUIRED LOGS FOR THE USER
                    print(f"WSS TICK: {instrument_key} LTP={ltp} Vol={tick_volume} Buy={is_buy}", flush=True)
                    self.callback(instrument_key, ltp, tick_volume, is_buy)

    async def _subscribe(self, instrument_keys):
        if self.websocket:
            print(f"Subscribing to: {instrument_keys}", flush=True)
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
        try:
            self.loop.run_until_complete(self.connect())
        except Exception as e:
            print(f"WSS Thread Error: {e}", flush=True)

    def update_subscriptions(self, instrument_keys):
        if not self.loop:
            self.pending_subscriptions.update(instrument_keys)
            return

        to_remove = list(self.subscribed_keys - set(instrument_keys))
        to_add = list(set(instrument_keys) - self.subscribed_keys)

        if to_remove:
            asyncio.run_coroutine_threadsafe(self._unsubscribe(to_remove), self.loop)
        if to_add:
            asyncio.run_coroutine_threadsafe(self._subscribe(to_add), self.loop)
