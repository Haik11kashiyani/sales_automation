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
        # STRATEGY CHANGE: Native 1080x1920 Viewport with CSS Zoom.
        # This guarantees the video fills the frame 100% without scaling artifacts.
        context = await browser.new_context(
            viewport={"width": 1080, "height": 1920},
            device_scale_factor=1.0,
            is_mobile=False, # We strictly control layout via CSS/Meta
            has_touch=True,
            record_video_dir=os.path.dirname(output_path),
            record_video_size={"width": 1080, "height": 1920}
        )
        
        page = await context.new_page()
        
        try:
            await page.goto(url, wait_until="networkidle")
        except:
             await page.goto(url)

        # --- FIX RENDERING & INJECT CURSOR ---
        # 1. Force Mobile Layout via Zoom implies width ~360px (1080 / 3 = 360)
        # 2. Add Cursor
        await page.add_style_tag(content="""
            html {
                zoom: 300%; /* Force Mobile View on 1080p screen */
                overflow-x: hidden;
            }
            body { 
                margin: 0; 
                padding: 0; 
                background-color: #0a0a0a; /* Ensure no white bars */
            }
            ::-webkit-scrollbar { display: none; }
            
            #ai-cursor {
                position: fixed;
                width: 15px; /* Smaller because of zoom */
                height: 15px;
                background: rgba(0, 255, 136, 0.9);
                border: 1px solid white;
                border-radius: 50%;
                pointer-events: none;
                z-index: 999999;
                transition: transform 0.1s;
                mix-blend-mode: normal;
                box-shadow: 0 0 10px rgba(0,255,136,0.5);
            }
        """)
        
        # Inject cursor div
        await page.evaluate("""
            const c = document.createElement('div');
            c.id = 'ai-cursor';
            document.body.appendChild(c);
            
            // Sync cursor with mouse events
            // visual cursor needs to counteract zoom for smooth look? 
            // actually playright mouse events are logical, zoom handles the rest.
            document.addEventListener('mousemove', e => {
                c.style.left = e.clientX + 'px';
                c.style.top = e.clientY + 'px';
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
                    classList: Array.from(t.classList).join(' '),
                    centerX: r.left + r.width/2,
                    centerY: r.top + r.height/2
                };
            }).sort((a, b) => a.y - b.y);
        }""")
        
        total_height = await page.evaluate("document.body.scrollHeight")
        # Logical height will be lower due to zoom? No, scrollHeight reports Scaled pixels usually.
        # Let's verify: 1080x1920 zoom 300% -> Viewport effectively 360x640 logical.
        # We need to scroll based on logical pixels.
        
        viewport_height = 640 # logic viewport (1920 / 3)
        current_scroll = 0
        start_time = time.time()
        
        # Cursor Start
        await page.mouse.move(180, 320) # Center of logical 360x640
        
        while current_scroll < (total_height - viewport_height):
            # Identify POIs
            look_ahead = current_scroll + 200
            visible_pois = [p for p in pois if p['y'] > current_scroll and p['y'] < (current_scroll + viewport_height - 50)]
            
            should_interact = False
            if len(visible_pois) > 0 and random.random() < 0.75:
                 should_interact = True
            
            if should_interact:
                target = random.choice(visible_pois)
                mouse_y_target = target['centerY'] - current_scroll
                
                # Bounds check (Logical Viewport)
                if 50 < mouse_y_target < 590:
                    # Move Cursor (Human Curve)
                    await page.mouse.move(target['centerX'], mouse_y_target, steps=random.randint(8, 15))
                    
                    # --- DISTINCT INTERACTIONS ---
                    tag = target['type']
                    cls = target['classList']
                    
                    if tag == 'CANVAS':
                         # 3D ROTATE (Drag)
                         await page.mouse.down()
                         await page.mouse.move(target['centerX'] + 50, mouse_y_target, steps=10)
                         await page.mouse.up()
                         await page.mouse.move(target['centerX'], mouse_y_target, steps=10) # Return
                         
                    elif tag == 'BUTTON' or 'btn' in cls:
                         # CLICK HOVER (Bounce)
                         await page.wait_for_timeout(100)
                         await page.mouse.down() # Click
                         await page.wait_for_timeout(100)
                         await page.mouse.up()
                         await page.wait_for_timeout(400) # Admire result
                         
                    elif 'card' in cls or tag == 'DIV':
                         # READ/FOCUS (Slow Pan)
                         # Pan across the card
                         start_x = target['centerX'] - 20
                         end_x = target['centerX'] + 20
                         await page.mouse.move(start_x, mouse_y_target, steps=20)
                         await page.mouse.move(end_x, mouse_y_target, steps=20)
                    
                    else:
                         # GENERIC HOVER
                         await page.wait_for_timeout(random.randint(300, 600))
                
                # Resume Scroll (Slow)
                step = random.randint(20, 60)
                await page.mouse.wheel(0, step)
                current_scroll += step
                await page.wait_for_timeout(random.randint(50, 150))
                
            else:
                # FAST SKIM (Flick)
                flick_power = random.randint(200, 500)
                remaining = flick_power
                while remaining > 10:
                    chunk = int(remaining * 0.25)
                    await page.mouse.wheel(0, chunk)
                    current_scroll += chunk
                    remaining -= chunk
                    await page.wait_for_timeout(16)
                
                await page.wait_for_timeout(random.randint(30, 80))

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
