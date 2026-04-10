import asyncio
from playwright.async_api import async_playwright
import time
import os

async def verify():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print("Connecting to app at http://localhost:8050")
        try:
            await page.goto("http://localhost:8050", timeout=60000)

            await page.wait_for_selector("div:not([data-dash-is-loading='true'])")
            await page.wait_for_selector(".dash-dropdown")

            dropdowns = await page.query_selector_all(".dash-dropdown")
            if len(dropdowns) >= 2:
                await dropdowns[1].click()
                await page.keyboard.type("NIFTY 23800 PE")
                await asyncio.sleep(2)
                await page.keyboard.press("Enter")

            await page.click("button:has-text('Connect & Start')")

            print("Waiting for candles to appear...")
            # Wait until stat-candles is not "0"
            for _ in range(30):
                candles_text = await page.inner_text("#stat-candles")
                if candles_text != "0":
                    print(f"Candles appeared: {candles_text}")
                    break
                await asyncio.sleep(1)
            else:
                print("Timed out waiting for candles")

            await asyncio.sleep(5) # Let it refresh a few more times

            screenshot_path = "/home/jules/verification/terminal_v3.png"
            os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
            await page.screenshot(path=screenshot_path)
            print(f"Screenshot saved to {screenshot_path}")

        except Exception as e:
            print(f"Error: {e}")
            await page.screenshot(path="/home/jules/verification/error_v3.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(verify())
