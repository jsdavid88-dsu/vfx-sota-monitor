# X/Twitter login session setup (Playwright direct)
# Run: .venv\Scripts\python.exe scripts\x_login_setup.py
import asyncio
import os
import re
import sys

os.environ["PYTHONIOENCODING"] = "utf-8"

from pathlib import Path

PROFILE_DIR = Path(__file__).resolve().parent.parent / "data" / "x_browser_profile"
PROFILE_DIR.mkdir(parents=True, exist_ok=True)


async def main():
    from playwright.async_api import async_playwright

    print("=" * 50)
    print("  X/Twitter login setup")
    print("=" * 50)
    print(f"\nProfile: {PROFILE_DIR}")
    print("\nBrowser opens now. Log in to X.")
    print("After login, come back here and press Enter.\n")

    pw = await async_playwright().start()

    browser = await pw.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE_DIR),
        headless=False,
        viewport={"width": 1280, "height": 900},
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
        ],
        ignore_default_args=["--enable-automation"],
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    )

    page = browser.pages[0] if browser.pages else await browser.new_page()
    await page.goto("https://x.com/login", wait_until="domcontentloaded")
    print("Login page opened. Log in now.")

    input("\n>>> Logged in? Press Enter to continue... ")

    # Go to home timeline
    print("\nChecking home timeline...")
    try:
        await page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=30000)
    except Exception:
        pass
    await asyncio.sleep(5)
    content = await page.content()
    print(f"Home page: {len(content)} chars")

    # Go to my profile
    print("\nChecking @leedavid387274...")
    try:
        await page.goto("https://x.com/leedavid387274", wait_until="domcontentloaded", timeout=30000)
    except Exception:
        pass
    await asyncio.sleep(5)

    # Scroll down to load more tweets
    for i in range(3):
        await page.evaluate("window.scrollBy(0, 2000)")
        await asyncio.sleep(2)

    content = await page.content()
    print(f"Profile page: {len(content)} chars")

    # Extract tweet IDs from page
    ids = set(re.findall(r'/status/(\d+)', content))
    print(f"\nTweet IDs found: {len(ids)}")
    for tid in sorted(ids, reverse=True)[:15]:
        print(f"  https://x.com/leedavid387274/status/{tid}")

    # Save IDs to file for feed crawler
    ids_file = PROFILE_DIR.parent / "x_tweet_ids.txt"
    with open(ids_file, "w") as f:
        for tid in sorted(ids, reverse=True):
            f.write(tid + "\n")
    print(f"\nSaved {len(ids)} IDs to {ids_file}")

    input("\n>>> Press Enter to close browser... ")

    await browser.close()
    await pw.stop()
    print("Done! Session saved.")


if __name__ == "__main__":
    asyncio.run(main())
