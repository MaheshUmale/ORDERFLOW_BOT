import asyncio
from upstox_helper import UpstoxHelper
from upstox_wss import UpstoxWSS

async def main():
    helper = UpstoxHelper()

    def callback(key, ltp, vol, buy):
        print(f"WSS FEED -> {key} @ {ltp}")

    wss = UpstoxWSS(callback)
    wss.start()

    await asyncio.sleep(3)

    # Sub to NIFTY Spot and one Option
    keys = ['NSE_INDEX|Nifty 50', 'NSE_FO|54711']
    print(f"Requesting SUB for {keys}")
    wss.update_subscriptions(keys)

    await asyncio.sleep(30)
    print("Done.")

if __name__ == "__main__":
    asyncio.run(main())
