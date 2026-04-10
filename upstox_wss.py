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
            print("Failed to authorize market data feed:", auth_response)
            return

        authorized_url = auth_response['data']['authorized_redirect_uri']

        async with websockets.connect(authorized_url) as websocket:
            self.websocket = websocket
            print("Connected to Upstox WSS")

            # Subscribe to any keys that were requested before connection
            if self.pending_subscriptions:
                keys_to_sub = list(self.pending_subscriptions)
                print(f"Subscribing to pending keys: {keys_to_sub}")
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
                    print("WSS connection closed")
                    break
                except Exception as e:
                    print(f"Error in WSS loop: {e}")

    def handle_message(self, message):
        feed_response = pb.FeedResponse()
        feed_response.ParseFromString(message)
        # Handle both casings just in case
        data = MessageToDict(feed_response, preserving_proto_field_name=True)

        if 'feeds' in data:
            for instrument_key, feed in data['feeds'].items():
                ltp = 0
                cum_volume = 0
                bid = 0
                ask = 0

                # Robust extraction handling multiple possible Protobuf-to-Dict mappings
                ff = feed.get('fullFeed') or feed.get('full_feed') or {}
                iff = ff.get('indexFF') or ff.get('index_ff') or feed.get('indexFF') or feed.get('index_ff') or {}
                mff = ff.get('marketFF') or ff.get('market_ff') or feed.get('marketFF') or feed.get('market_ff') or {}

                if iff:
                    ltpc = iff.get('ltpc', {})
                    ltp = ltpc.get('ltp', 0)
                elif mff:
                    ltpc = mff.get('ltpc', {})
                    ltp = ltpc.get('ltp', 0)
                    cum_volume = ltpc.get('v', 0)

                    ml = mff.get('marketLevel') or mff.get('market_level') or {}
                    baq = ml.get('bidAskQuote') or ml.get('bid_ask_quote') or []
                    if baq:
                        bid = baq[0].get('bidP') or baq[0].get('bid_p') or 0
                        ask = baq[0].get('askP') or baq[0].get('ask_p') or 0

                # Final fallback to top-level ltpc
                if ltp == 0 and 'ltpc' in feed:
                    ltpc = feed['ltpc']
                    ltp = ltpc.get('ltp', 0)
                    cum_volume = ltpc.get('v', 0)

                if ltp > 0:
                    last_v = self.last_volumes.get(instrument_key, cum_volume)
                    incremental_volume = cum_volume - last_v
                    if incremental_volume < 0: incremental_volume = 0
                    self.last_volumes[instrument_key] = cum_volume

                    is_buy = True
                    if ask > bid > 0:
                        is_buy = abs(ltp - ask) <= abs(ltp - bid)

                    # REQUIRED LOGS FOR THE USER
                    print(f"WSS TICK: {instrument_key} LTP={ltp} Vol={incremental_volume} Buy={is_buy}")
                    self.callback(instrument_key, ltp, incremental_volume, is_buy)

    async def _subscribe(self, instrument_keys):
        if self.websocket:
            print(f"Subscribing to: {instrument_keys}")
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
            print(f"WSS Thread Error: {e}")

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
