import asyncio
from playwright.async_api import async_playwright
import os

async def record_url(url: str, duration: float, output_path: str):
    """
    Records a webpage interaction:
    1. Launches browser (1080x1920)
    2. Navigates to URL
    3. Waits for load
    4. Scrolls smoothly for 'duration' seconds
    5. Saves video
    """
    print(f"Starting recording for {url} with duration {duration}s")
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(
            headless=False,
            args=['--enable-features=OverlayScrollbar'] # Optional: hide scrollbars overlay style
        )
        
        # Create context with MOBILE Emulation
        # We want 1080x1920 output.
        # CSS Viewport: 360x640 (Standard Mobile)
        # Scale Factor: 3.0
        # Result: 360*3 = 1080, 640*3 = 1920.
        context = await browser.new_context(
            viewport={"width": 360, "height": 640},
            device_scale_factor=3.0,
            is_mobile=True,
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            record_video_dir=os.path.dirname(output_path),
            record_video_size={"width": 1080, "height": 1920}
        )
        
        page = await context.new_page()
        
        # Open the local file or URL
        # If it's a file path, convert to file:// URI
        if os.path.exists(url):
            url = f"file://{os.path.abspath(url)}"
            
        await page.goto(url)
        
        # Wait for initial load animations
        await page.wait_for_timeout(1000)
        
        # Smooth scroll logic
        # We scroll from top to bottom over 'duration' seconds
        # Calculate total height
        total_height = await page.evaluate("() => document.body.scrollHeight")
        viewport_height = 1920
        scrollable_distance = total_height - viewport_height
        
        if scrollable_distance > 0:
            steps = int(duration * 60) # 60 fps assumed for smoothness steps
            step_time = (duration * 1000) / steps
            step_distance = scrollable_distance / steps
            
            for i in range(steps):
                await page.evaluate(f"window.scrollBy(0, {step_distance})")
                await page.wait_for_timeout(step_time)
        else:
             # Just wait if no scroll
            await page.wait_for_timeout(duration * 1000)
            
        await context.close()
        await browser.close()
        
        # Playwright saves video with random name, we need to rename it
        # The video file is likely the only .webm/.mp4 in the dir if we clean up, 
        # but context.record_video_dir was set.
        # Actually, page.video.path() gives the path.
        saved_video_path = await page.video.path()
        if saved_video_path:
             if os.path.exists(output_path):
                 os.remove(output_path)
             os.rename(saved_video_path, output_path)
             print(f"Video saved to {output_path}")

if __name__ == "__main__":
    # Test execution
    test_html = os.path.abspath(os.path.join(os.path.dirname(__file__), "../content_pool/business_01/index.html"))
    asyncio.run(record_url(test_html, 30, "test_output.mp4"))
