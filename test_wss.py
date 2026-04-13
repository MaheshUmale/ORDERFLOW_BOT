import asyncio
import os
from upstox_helper import UpstoxHelper
from upstox_wss import UpstoxWSS

async def main():
    helper = UpstoxHelper()

    # Test Auth
    print("Testing Auth...")
    auth = helper.get_market_data_feed_authorize()
    print(f"Auth Response: {auth}")

    if auth.get('status') != 'success':
        print("Auth Failed! Check token.")
        return

    def callback(key, ltp, vol, buy):
        print(f"RECEIVED: {key} @ {ltp}")

    wss = UpstoxWSS(callback)
    wss.start()

    # Wait for loop to init
    await asyncio.sleep(2)

    # Subscribe to NIFTY Spot
    print("Subscribing to NIFTY Spot...")
    wss.update_subscriptions(['NSE_INDEX|Nifty 50'])

    # Keep alive for 30s
    await asyncio.sleep(30)
    print("Test finished.")

if __name__ == "__main__":
    asyncio.run(main())
