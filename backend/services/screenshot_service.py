"""
Screenshot Service - Server-side screenshot capture using Playwright
Bypasses CORS restrictions by capturing screenshots on the server
"""

import base64
import asyncio
from typing import Optional
from playwright.async_api import async_playwright, Browser, Page

# Global browser instance (reused for performance)
_browser: Optional[Browser] = None


async def get_browser() -> Browser:
    """Get or create a browser instance with stealth settings"""
    global _browser
    if _browser is None or not _browser.is_connected():
        playwright = await async_playwright().start()
        # Launch with stealth settings to avoid bot detection
        _browser = await playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process'
            ]
        )
    return _browser


async def capture_youtube_frame(video_id: str, timestamp: float = 0) -> Optional[str]:
    """
    Capture a frame from a YouTube video at the specified timestamp.

    Args:
        video_id: YouTube video ID
        timestamp: Timestamp in seconds to capture from

    Returns:
        Base64 encoded JPEG image, or None if capture fails
    """
    try:
        print(f"📸 Capturing screenshot: {video_id} at {timestamp}s")

        browser = await get_browser()

        # Create page with stealth settings
        page = await browser.new_page(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

        # Set viewport size
        await page.set_viewport_size({"width": 1280, "height": 720})

        # Add stealth JavaScript
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        # Navigate to YouTube embed with autoplay
        youtube_url = f"https://www.youtube.com/embed/{video_id}?autoplay=1&start={int(timestamp)}&mute=1"
        print(f"  🌐 Loading: {youtube_url}")

        await page.goto(youtube_url, wait_until="networkidle")

        # Wait for player to be ready
        await asyncio.sleep(3)

        # Check if there's an error message
        try:
            error_element = await page.query_selector('.ytp-error')
            if error_element:
                print("  ⚠️ YouTube player error detected")
        except:
            pass

        # Try to interact with player to ensure it's playing
        try:
            # Click on the player area to ensure focus
            await page.click('iframe, video, .html5-video-player', timeout=2000)
            print("  🖱️ Clicked player area")
        except:
            pass

        # Wait longer for video to buffer and start
        await asyncio.sleep(4)

        # Execute JavaScript to check video state
        try:
            video_playing = await page.evaluate("""
                () => {
                    const video = document.querySelector('video');
                    return video && !video.paused && !video.ended && video.readyState > 2;
                }
            """)
            if video_playing:
                print("  ✅ Video is playing")
            else:
                print("  ⚠️ Video may not be playing yet")
        except:
            pass

        # Take screenshot of the full page (includes video player)
        screenshot_bytes = await page.screenshot(
            type='jpeg',
            quality=80,
            full_page=False
        )

        # Debug: Save screenshot to file for inspection
        debug_path = f"/tmp/screenshot_{video_id}_{int(timestamp)}.jpg"
        with open(debug_path, 'wb') as f:
            f.write(screenshot_bytes)
        print(f"  💾 Debug screenshot saved: {debug_path}")

        # Convert to base64
        screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')

        await page.close()

        print(f"✅ Screenshot captured: {len(screenshot_base64)} chars")
        return screenshot_base64

    except Exception as e:
        print(f"❌ Screenshot capture failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def close_browser():
    """Close the browser instance"""
    global _browser
    if _browser:
        await _browser.close()
        _browser = None
