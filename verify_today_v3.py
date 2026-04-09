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

            # Select NIFTY 24500 PE (2026-04-13) or similar
            # From find_valid_keys.py, NSE_FO|54702 is NIFTY2641322500PE.
            # Let's try to search by strike 24500 PE

            dropdowns = await page.query_selector_all(".dash-dropdown")
            if len(dropdowns) >= 2:
                await dropdowns[1].click()
                await page.keyboard.type("NIFTY 24500 PE")
                await asyncio.sleep(2)
                await page.keyboard.press("Enter")

            await page.click("label:has-text('Rel. Strength')")
            await page.click("button:has-text('Connect & Start')")

            print("Waiting for bootstrap and bootstrap data to render...")
            await asyncio.sleep(20)

            screenshot_path = "/home/jules/verification/today_real_data.png"
            os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
            await page.screenshot(path=screenshot_path)
            print(f"Screenshot saved to {screenshot_path}")

        except Exception as e:
            print(f"Error: {e}")
            await page.screenshot(path="/home/jules/verification/error_real_data.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(verify())
