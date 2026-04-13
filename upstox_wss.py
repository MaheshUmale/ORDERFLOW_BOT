import asyncio
import websockets
from upstox_client.feeder.proto import MarketDataFeedV3_pb2 as pb
from google.protobuf.json_format import MessageToDict
import threading
import json
import time
from upstox_helper import UpstoxHelper

class UpstoxWSS:
    def __init__(self, callback):
        self.callback = callback
        self.helper = UpstoxHelper()
        self.websocket = None
        self.loop = None
        self.pending_subscriptions = set()
        self.subscribed_keys = set()
        self._thread = None

    async def connect(self):
        while True:
            try:
                auth_response = self.helper.get_market_data_feed_authorize()
                if 'status' not in auth_response or auth_response['status'] != 'success':
                    print(f"FAILED WSS AUTH: {auth_response}. Retrying in 5s...", flush=True)
                    await asyncio.sleep(5)
                    continue

                authorized_url = auth_response['data']['authorized_redirect_uri']
                print(f"Connecting to WSS...", flush=True)

                async with websockets.connect(authorized_url) as websocket:
                    self.websocket = websocket
                    print("WSS CONNECTED SUCCESS", flush=True)

                    # Re-subscribe to existing keys or handle pending ones
                    keys_to_sub = list(self.pending_subscriptions | self.subscribed_keys)
                    if keys_to_sub:
                        print(f"Resubscribing to: {keys_to_sub}", flush=True)
                        await self._subscribe(keys_to_sub)
                        self.pending_subscriptions.clear()

                    while True:
                        try:
                            message = await websocket.recv()
                            self.handle_message(message)
                        except websockets.ConnectionClosed:
                            print("WSS CONNECTION CLOSED. Reconnecting...", flush=True)
                            self.websocket = None
                            break
                        except Exception as e:
                            print(f"WSS RECV ERROR: {e}", flush=True)
                            await asyncio.sleep(0.1)

            except Exception as e:
                print(f"WSS CONNECT ERROR: {e}. Retrying in 5s...", flush=True)
                self.websocket = None
                await asyncio.sleep(5)

    def handle_message(self, message):
        try:
            feed_response = pb.FeedResponse()
            feed_response.ParseFromString(message)
            # Try both with and without preserving field names
            data = MessageToDict(feed_response)
        except Exception as e:
            print(f"PROTO DECODE ERROR: {e}", flush=True)
            return

        # DEBUG RAW
        # print(f"WSS RAW KEYS: {data.keys()}", flush=True)

        if 'feeds' in data:
            for instrument_key, feed in data['feeds'].items():
                ltp = 0
                tick_volume = 0
                bid = 0
                ask = 0

                # Navigation robust to both formats
                ff = feed.get('fullFeed') or feed.get('full_feed', {})
                iff = ff.get('indexFF') or ff.get('index_ff') or feed.get('indexFF') or feed.get('index_ff', {})
                mff = ff.get('marketFF') or ff.get('market_ff') or feed.get('marketFF') or feed.get('market_ff', {})

                if iff:
                    ltpc = iff.get('ltpc', {})
                    ltp = ltpc.get('ltp', 0)
                elif mff:
                    ltpc = mff.get('ltpc', {})
                    ltp = ltpc.get('ltp', 0)
                    tick_volume = int(ltpc.get('ltq', 0))

                    ml = mff.get('marketLevel') or mff.get('market_level', {})
                    baq = ml.get('bidAskQuote') or ml.get('bid_ask_quote', [])
                    if baq:
                        bid = baq[0].get('bidP') or baq[0].get('bid_p', 0)
                        ask = baq[0].get('askP') or baq[0].get('ask_p', 0)

                # Fallback
                if ltp == 0:
                    ltpc = feed.get('ltpc', {})
                    ltp = ltpc.get('ltp', 0)
                    tick_volume = int(ltpc.get('ltq', 0))

                if ltp > 0:
                    is_buy = True
                    if ask > bid > 0:
                        is_buy = abs(ltp - ask) <= abs(ltp - bid)

                    print(f"WSS TICK: {instrument_key} LTP={ltp} Vol={tick_volume} Buy={is_buy}", flush=True)
                    self.callback(instrument_key, ltp, tick_volume, is_buy)

    async def _subscribe(self, instrument_keys):
        if self.websocket:
            print(f"WSS SUB: {instrument_keys}", flush=True)
            data = {
                "guid": "of_bot",
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
                "guid": "of_bot",
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
            print(f"WSS LOOP ERROR: {e}", flush=True)

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
