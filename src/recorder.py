import asyncio
from playwright.async_api import async_playwright
import os
import threading
import http.server
import socketserver
import time
import random
import math

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
        # iPhone 14 Pro Max-ish aspect ratio but scaled to 1080w
        # Logic: 430px width * 2.5 scale = ~1075px (Close to 1080)
        # Let's stick to the proven 360 * 3 = 1080.
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

        # --- FIX RENDERING ISSUES ---
        # Inject CSS to force the body to fill the viewport and remove margins
        # This fixes the "small box in gray void" issue seen in user screenshot
        await page.add_style_tag(content="""
            html, body {
                width: 100%;
                margin: 0;
                padding: 0;
                overflow-x: hidden;
            }
            /* Hide scrollbars visually but keep functionality */
            ::-webkit-scrollbar {
                display: none;
            }
        """)

        # Force GSAP refresh
        await page.evaluate("if(window.ScrollTrigger) window.ScrollTrigger.refresh()")
        await page.wait_for_timeout(1000)
        
        # --- SMART HUMAN SURFING LOGIC ---
        # 1. Analyze Page: Find "Points of Interest" (POIs)
        # 2. Logic:
        #    - If current viewport has POIs -> Scroll Slow, Hover, Interact.
        #    - If empty -> Scroll Fast (Skim).
        
        # Get all POIs positions
        pois = await page.evaluate("""() => {
            const targets = Array.from(document.querySelectorAll('button, a, input, canvas, .card, .interactive, h1, h2, video'));
            return targets.map(t => {
                const r = t.getBoundingClientRect();
                return {
                    y: r.top + window.scrollY, // Absolute Y position
                    height: r.height,
                    type: t.tagName,
                    centerX: r.left + r.width/2,
                    centerY: r.top + r.height/2
                };
            }).sort((a, b) => a.y - b.y);
        }""")
        
        total_height = await page.evaluate("document.body.scrollHeight")
        viewport_height = 640
        current_scroll = 0
        
        start_time = time.time()
        
        while current_scroll < (total_height - viewport_height):
            # Check elapsed time to ensure we respect roughly the duration (optional, but good for shorts)
            # If we are "skimming" too fast, we might end early. If interacting too much, we might cut off.
            # For now, priority is 'Human Feel' over exact second count.
            
            # Identify POIs in the NEXT viewport slice (what we are scrolling into)
            # Look ahead ~300px
            look_ahead = current_scroll + 300
            
            visible_pois = [p for p in pois if p['y'] > current_scroll and p['y'] < (current_scroll + viewport_height)]
            
            if len(visible_pois) > 0:
                # INTERESTING ZONE: Scroll Slow + Interact
                step = random.randint(20, 50) # Slow scroll
                
                # Chance to interact with a POI
                if random.random() < 0.6: # 60% chance to interact if POI exists
                    target = random.choice(visible_pois)
                    # Mouse Move to it (relative to viewport)
                    mouse_y = target['centerY'] - current_scroll
                    # Ensure it's on screen
                    if 0 < mouse_y < 640:
                         await page.mouse.move(target['centerX'], mouse_y, steps=15)
                         
                         if target['type'] == 'CANVAS':
                             # 3D WIGGLE
                             for i in range(5):
                                 await page.mouse.move(target['centerX'] + random.randint(-20, 20), mouse_y + random.randint(-20, 20), steps=5)
                         else:
                             # HOVER/FOCUS
                             await page.wait_for_timeout(random.randint(300, 800)) # Look at it
            else:
                # BORING ZONE: Scroll Fast (Skim)
                step = random.randint(100, 200) # Fast scroll
            
            # Perform the scroll
            await page.mouse.wheel(0, step)
            current_scroll += step
            
            # Random micropause (human thinking/reading)
            if random.random() < 0.1:
                await page.wait_for_timeout(random.randint(200, 500))
                
            await page.wait_for_timeout(random.randint(16, 32)) # ~30-60fps variance
            
            # Ensure we don't loop forever
            if time.time() - start_time > (duration + 10): # Timeout hardstop
                break
             
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
