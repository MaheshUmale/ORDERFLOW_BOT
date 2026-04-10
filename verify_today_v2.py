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

            # Use data-dash-is-loading attribute to wait for app to be ready
            await page.wait_for_selector("div:not([data-dash-is-loading='true'])")

            # The dropdown might not have id="opt-dropdown" directly on the clickable element
            # Dash dcc.Dropdown usually wraps it. Let's find by class or inner text
            # Wait for any dropdown
            await page.wait_for_selector(".dash-dropdown")

            # Let's try to click the second dropdown (Option Instrument)
            dropdowns = await page.query_selector_all(".dash-dropdown")
            if len(dropdowns) >= 2:
                await dropdowns[1].click()
                # Type NIFTY to see if it populates
                await page.keyboard.type("NIFTY 23800 PE")
                await asyncio.sleep(2)
                await page.keyboard.press("Enter")

            await page.click("label:has-text('Rel. Strength')")
            await page.click("button:has-text('Connect & Start')")

            print("Waiting for data to render...")
            await asyncio.sleep(15)

            screenshot_path = "/home/jules/verification/terminal_v2.png"
            os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
            await page.screenshot(path=screenshot_path)
            print(f"Screenshot saved to {screenshot_path}")

        except Exception as e:
            print(f"Error: {e}")
            await page.screenshot(path="/home/jules/verification/error_v2.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(verify())
