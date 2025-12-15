import asyncio
from playwright.async_api import async_playwright
import os
import threading
import http.server
import socketserver
import time

# --- Helper to start a local server for the content ---
PORT = 8000
SERVER_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../")) 
# We serve from project root so we can access content_pool/business_01

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

def start_server():
    os.chdir(SERVER_ROOT)
    with socketserver.TCPServer(("", PORT), QuietHandler) as httpd:
        print(f"Serving at port {PORT}")
        httpd.serve_forever()

def run_server_in_thread():
    t = threading.Thread(target=start_server)
    t.daemon = True
    t.start()
    return t

# --- Recorder Logic ---

async def record_url(file_path: str, duration: float, output_path: str):
    """
    Records a webpage interaction via localhost:
    1. Launches browser (Mobile Emulation)
    2. Navigates to localhost URL
    3. Scrolls smoothly via MOUSE WHEEL for 'duration' seconds
    4. Saves video
    """
    # 1. Start Server if not already likely running (simplistic check)
    # Ideally main.py manages this, but for simplicity let's assume this script might be standalone.
    # We will just rely on relative paths conversion to localhost URL.
    # Logic: file_path is like ".../content_pool/business_01/index.html"
    # We want "http://localhost:8000/content_pool/business_01/index.html"
    
    # Calculate relative path from SERVER_ROOT
    rel_path = os.path.relpath(file_path, SERVER_ROOT)
    url = f"http://localhost:{PORT}/{rel_path.replace(os.sep, '/')}"
    
    print(f"Recording URL: {url} | Duration: {duration}s")

    async with async_playwright() as p:
        # Use new headless mode for better rendering compliance
        browser = await p.chromium.launch(
            headless=True,
            args=['--enable-features=OverlayScrollbar', '--no-sandbox', '--disable-setuid-sandbox']
        )
        
        # Mobile Emulation setup
        # 360x640 @ 3x = 1080x1920 physical pixels.
        context = await browser.new_context(
            viewport={"width": 360, "height": 640},
            device_scale_factor=3.0,
            is_mobile=True,
            has_touch=True,
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            record_video_dir=os.path.dirname(output_path),
            record_video_size={"width": 1080, "height": 1920}
        )
        
        page = await context.new_page()
        
        try:
            await page.goto(url, wait_until="networkidle")
        except:
             await page.goto(url)

        # Force GSAP refresh and ensure body covers viewport
        await page.evaluate("""
            if(window.ScrollTrigger) window.ScrollTrigger.refresh();
            document.body.style.minHeight = '100vh';
            document.body.style.width = '100%';
        """)
        await page.wait_for_timeout(1000)
        
        # --- HUMAN SCROLL LOGIC ---
        # Instead of linear constant speed, we use a curve.
        # Start slow (reading), speed up (scanning), slow down (ending).
        
        total_height = await page.evaluate("document.body.scrollHeight")
        viewport_height = 640
        scroll_dist = total_height - viewport_height
        
        if scroll_dist > 0:
            import math
            import random
            
            # FPS for scroll updates
            fps = 60 
            total_frames = int(duration * fps)
            
            current_y = 0
            
            for frame in range(total_frames):
                # Progress (0.0 to 1.0)
                t = frame / total_frames
                
                # Easing function: EaseInOutCubic (Starts slow, speeds up, slows down)
                # This mimics a human checking the top, scrolling fast through content, then slowing at footer.
                # Formula: t < .5 ? 4 * t * t * t : 1 - pow(-2 * t + 2, 3) / 2
                
                if t < 0.5:
                    ease = 4 * t * t * t
                else:
                    ease = 1 - pow(-2 * t + 2, 3) / 2
                
                target_y = scroll_dist * ease
                
                # Calculate delta for this frame
                delta = target_y - current_y
                
                # Add tiny random jitter to look human (imperfection)
                jitter = random.uniform(-0.5, 0.5)
                
                if delta > 0:
                    await page.mouse.wheel(0, delta + jitter)
                    current_y += delta
                
                await page.wait_for_timeout(1000/fps)
                
        else:
             await page.wait_for_timeout(duration * 1000)
             
        await context.close()
        await browser.close()
        
        saved_video_path = await page.video.path()
        if saved_video_path:
             if os.path.exists(output_path):
                 os.remove(output_path)
             os.rename(saved_video_path, output_path)
             print(f"Video saved to {output_path}")

if __name__ == "__main__":
    # Test execution
    # Start server for testing
    run_server_in_thread()
    time.sleep(1) # wait for server
    
    test_html = os.path.abspath(os.path.join(os.path.dirname(__file__), "../content_pool/business_01/index.html"))
    asyncio.run(record_url(test_html, 30, "test_output.mp4"))
