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
        # Switching to "Phablet" Logical Resolution to fix "Cornered/Narrow" look.
        # Logical: 540x960
        # Scale: 2.0
        # Output: 1080x1920
        context = await browser.new_context(
            viewport={"width": 540, "height": 960},
            device_scale_factor=2.0,
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

        # --- FIX RENDERING & INJECT CURSOR ---
        # 1. Force full width
        # 2. Add a FAKE CURSOR so the user can see the "Human" interaction! 
        #    (Playwright mouse is invisible, adding a visual dot helps sell the effect)
        await page.add_style_tag(content="""
            html, body { width: 100%; margin: 0; padding: 0; overflow-x: hidden; }
            ::-webkit-scrollbar { display: none; }
            
            #ai-cursor {
                position: fixed;
                width: 20px;
                height: 20px;
                background: rgba(0, 255, 136, 0.7);
                border: 2px solid white;
                border-radius: 50%;
                pointer-events: none;
                z-index: 999999;
                transition: transform 0.1s;
                mix-blend-mode: difference;
            }
        """)
        
        # Inject cursor div
        await page.evaluate("""
            const c = document.createElement('div');
            c.id = 'ai-cursor';
            document.body.appendChild(c);
            
            // Sync cursor with mouse events
            document.addEventListener('mousemove', e => {
                c.style.left = (e.clientX - 10) + 'px';
                c.style.top = (e.clientY - 10) + 'px';
            });
            document.addEventListener('mousedown', () => c.style.transform = 'scale(0.8)');
            document.addEventListener('mouseup', () => c.style.transform = 'scale(1)');
        """)

        # Force GSAP refresh
        await page.evaluate("if(window.ScrollTrigger) window.ScrollTrigger.refresh()")
        await page.wait_for_timeout(1000)
        
        # --- PEAK HUMAN SURFING LOGIC (State Machine) ---
        
        pois = await page.evaluate("""() => {
            const targets = Array.from(document.querySelectorAll('button, a, input, canvas, .card, .interactive, h1, h2, video'));
            return targets.map(t => {
                const r = t.getBoundingClientRect();
                return {
                    y: r.top + window.scrollY,
                    height: r.height,
                    type: t.tagName,
                    centerX: r.left + r.width/2,
                    centerY: r.top + r.height/2
                };
            }).sort((a, b) => a.y - b.y);
        }""")
        
        total_height = await page.evaluate("document.body.scrollHeight")
        viewport_height = 960
        current_scroll = 0
        start_time = time.time()
        
        # Initial "Look around"
        await page.mouse.move(270, 480, steps=20) 
        
        while current_scroll < (total_height - viewport_height):
            # Dynamic Speed: Fast Flick vs Slow Read
            
            # Check interaction zone
            visible_pois = [p for p in pois if p['y'] > current_scroll and p['y'] < (current_scroll + viewport_height - 100)]
            
            should_interact = False
            if len(visible_pois) > 0 and random.random() < 0.7:
                 should_interact = True
            
            if should_interact:
                # --- INTERACTION MODE ---
                # Scroll a tiny bit, then play with element
                target = random.choice(visible_pois)
                mouse_y_target = target['centerY'] - current_scroll
                
                # Check bounds
                if 100 < mouse_y_target < 860:
                    # 1. Scroll check (Micro scroll to align?)
                    # 2. Move Mouse Fast (Human Flick)
                    await page.mouse.move(target['centerX'], mouse_y_target, steps=random.randint(5, 12))
                    
                    # 3. Hover / Wiggle
                    if target['type'] == 'CANVAS':
                         # 3D Rotate
                         start_x = target['centerX']
                         for _ in range(10):
                             await page.mouse.move(start_x + random.randint(-40, 40), mouse_y_target + random.randint(-40, 40), steps=2)
                    else:
                         # Button Hover
                         await page.wait_for_timeout(random.randint(400, 900))
                    
                    # 4. Resume
                
                # Slow Scroll (Reading/Viewing)
                step = random.randint(30, 80)
                await page.mouse.wheel(0, step)
                current_scroll += step
                await page.wait_for_timeout(random.randint(50, 150))
                
            else:
                # --- FAST SKIM MODE (Sloopy Fix) ---
                # User complaining about "Sloopy" (Slow/Sloppy). They want "Fast & Fluid".
                # We do a 'Flick' (large scroll) + Glide
                flick_power = random.randint(300, 600)
                
                # Execute Flick (Exponential Decceleration)
                remaining = flick_power
                while remaining > 10:
                    chunk = int(remaining * 0.3) # Move 30% of remaining distance
                    await page.mouse.wheel(0, chunk)
                    current_scroll += chunk
                    remaining -= chunk
                    await page.wait_for_timeout(16) # 60fps
                
                await page.wait_for_timeout(random.randint(50, 100))

            if time.time() - start_time > duration + 5:
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
