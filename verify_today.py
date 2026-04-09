import asyncio
from playwright.async_api import async_playwright
import time
import os

async def verify():
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Go to the app
        # Note: app.py must be running. I'll start it in the bash session.
        print("Connecting to app at http://localhost:8050")
        try:
            await page.goto("http://localhost:8050", timeout=60000)

            # 1. Select the instrument
            # Wait for the dropdown to be available
            await page.wait_for_selector(".dash-dropdown")

            # Select Option Instrument (NIFTY 23800 PE 2026-04-13)
            # The dropdown has id 'opt-dropdown'
            await page.click("#opt-dropdown")
            # Type to filter if many options, or just click if it's there.
            # Since it's a dynamic dropdown from Upstox, I'll search for the specific text
            await page.type("#opt-dropdown input", "NIFTY 23800 PE (2026-04-13)")
            await page.press("#opt-dropdown input", "Enter")

            # 2. Change Mode to Rel. Strength
            await page.click("label:has-text('Rel. Strength')")

            # 3. Connect & Start
            await page.click("#connect-btn")

            # 4. Wait for data to load and render
            print("Waiting for data to render...")
            await asyncio.sleep(10) # Give it time to bootstrap and draw

            # 5. Take Screenshot
            screenshot_path = "/home/jules/verification/terminal_view.png"
            os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
            await page.screenshot(path=screenshot_path)
            print(f"Screenshot saved to {screenshot_path}")

        except Exception as e:
            print(f"Error during verification: {e}")
            # Take a screenshot of the error state if possible
            await page.screenshot(path="/home/jules/verification/error_state.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(verify())
