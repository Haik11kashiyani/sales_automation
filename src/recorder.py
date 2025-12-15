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
        # STRATEGY CHANGE: "CSS Transform Mock"
        # 1. We keep native 1080x1920 canvas.
        # 2. We set body width to 360px (Mobile Standard).
        # 3. We scale the body by 3x.
        # Result: Perfect 360px layout (responsive) projected onto 1080px canvas.
        context = await browser.new_context(
            viewport={"width": 1080, "height": 1920},
            device_scale_factor=1.0,
            is_mobile=False,
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
        await page.add_style_tag(content="""
            html, body {
                width: 360px; /* Force Logical Mobile Width */
                min-height: 100vh;
                margin: 0;
                padding: 0;
                overflow-x: hidden;
            }
            
            /* The Magic: Scale everything up 3x to fill 1080px width */
            body {
                transform: scale(3.0);
                transform-origin: top left;
                overflow-y: visible; /* Let it scroll */
                background-color: #0a0a0a;
            }
            
            /* Fix fixed elements (like background orbs) */
            .floating-orb {
                 /* They usually relate to body, so they scale with it. Good. */
            }
            
            /* Hide scrollbars */
            ::-webkit-scrollbar { display: none; }
            
            /* AI CURSOR IS OUTSIDE THE SCALE TRANSFORM (Fixed to viewport) */
            /* We inject it as a direct child of html or outside body if possible, 
               but simpler to make it inverse-scaled or just big?
               If body is scaled, cursor inside body is scaled.
               Let's put cursor in body and let it be scaled 3x automatically. 
               So 15px cursor -> 45px visual. perfect.
            */
            #ai-cursor {
                position: absolute; /* Absolute relative to doc, not fixed to viewport if we scroll? */
                /* If we scroll page, body moves up. If cursor is fixed, it stays. */
                /* Wait, transform on body might mess up fixed positioning context. */
                top: 0; left: 0;
                width: 15px;
                height: 15px;
                background: rgba(0, 255, 136, 0.9);
                border: 2px solid white;
                border-radius: 50%;
                pointer-events: none;
                z-index: 999999;
                transition: transform 0.1s;
                box-shadow: 0 0 10px rgba(0,255,136,0.6);
            }
        """)
        
        # Inject cursor div
        await page.evaluate("""
            const c = document.createElement('div');
            c.id = 'ai-cursor';
            document.body.appendChild(c);
            
            // Sync cursor with mouse events
            // PROBLEM: Mouse events in Playwright are in Viewport Pixels (0-1080).
            // But Body is 360px wide (Scaled 3x).
            // If we move mouse to 540 (Screen Center), that equates to Body x=180.
            // If the cursor is inside the body, we must set its left/top to logical pixels (0-360).
            
            document.addEventListener('mousemove', e => {
                // e.clientX is Viewport X (0-1080).
                // We need to place #ai-cursor at logical position (0-360).
                // So divide by 3.
                c.style.left = (e.pageX / 3) + 'px'; 
                c.style.top = (e.pageY / 3) + 'px';
            });
            document.addEventListener('mousedown', () => c.style.transform = 'scale(0.8)');
            document.addEventListener('mouseup', () => c.style.transform = 'scale(1)');
        """)

        # Force GSAP refresh
        await page.evaluate("if(window.ScrollTrigger) window.ScrollTrigger.refresh()")
        await page.wait_for_timeout(1000)
        
        # --- LOGIC UPDATE: Use Viewport Pixels (0-1080) for Playwright Mouse ---
        # The page layout is 360px logical. But Playwright controls the "Window" (1080px).
        # When we move mouse to x=540, the browser hits x=180 on the scaled body. Matches perfectly.
        
        # Get POIs. `getBoundingClientRect` on scaled elements returns VIEWPORT coordinates (0-1080).
        # So our logic remains mostly same!
        
        pois = await page.evaluate("""() => {
            const targets = Array.from(document.querySelectorAll('button, a, input, canvas, .card, .interactive, h1, h2, video'));
            return targets.map(t => {
                const r = t.getBoundingClientRect();
                return {
                    y: r.top + window.scrollY, # This might be tricky with transform?
                    # Window scroll Y is usually in viewport pixels? No, logical.
                    # Actually, let's just use absolute page offset.
                    
                    # Safer: getBoundingClientRect().top + window.scrollY
                    # If body is scaled, valid scroll height is HUGE or SMALL?
                    # If 360px wide body is scaled 3x... total scroll height is logical (360 based) or visual?
                    # Usually CSS transform doesn't affect scrollWidth/Height report of documentElement?
                    # Let's assume standard behavior:
                    # We will rely on r.top (Viewport relative) + scrollY (current scroll).
                    
                    y: r.top + window.scrollY,
                    height: r.height,
                    type: t.tagName,
                    classList: Array.from(t.classList).join(' '),
                    centerX: r.left + r.width/2,
                    centerY: r.top + r.height/2
                };
            }).sort((a, b) => a.y - b.y);
        }""")
        
        # We need to scroll the *Viewport*. 
        # Total height of document?
        total_height = await page.evaluate("document.body.scrollHeight") 
        # With scale(3), content is visually huge. scrollHeight might be native (e.g. 2000px).
        # But visually it occupies 6000px.
        # Playwright mouse.wheel(0, 100) scrolls 100 viewport pixels usually.
        
        # Let's adjust viewport_height logic.
        viewport_height = 1920 
        current_scroll = 0
        start_time = time.time()
        
        # Initial Mouse Move
        await page.mouse.move(540, 960) 
        
        # We scroll until we think we reached bottom.
        # Let's trust visual detection.
        while True: # Loop until timeout or max scroll
            current_idx = await page.evaluate("window.scrollY")
            total = await page.evaluate("document.body.scrollHeight") # Logical height?
            # If body is scaled, the browser might report logical height?
            # Actually with transform on body, the WINDOW scroll bar might disappear or change?
            # We set `overflow-y: visible` on body and `overflow` on html... 
            
            # SCROLL STRATEGY:
            # We scroll, then check if scrollY changed. If not, we are at bottom.
            
            # Identify Next Target
            # Filter POIs visible in current Viewport (0 to 1920 relative to scroll)
            # Actually pois.y includes scrollY.
            
            # Re-read positions relative to viewport for interactions
            # This is safer than maintaining state.
            visible_targets = await page.evaluate("""() => {
                const targets = Array.from(document.querySelectorAll('button, a, .card, .interactive, canvas'));
                return targets.map(t => {
                     const r = t.getBoundingClientRect();
                     if (r.top > 100 && r.bottom < 1800) { # Visible in 1080x1920 frame
                         return {
                             x: r.left + r.width/2,
                             y: r.top + r.height/2,
                             type: t.tagName,
                             cls: Array.from(t.classList).join(' ')
                         };
                     }
                     return null;
                }).filter(t => t !== null);
            }""")
            
            # INTERACTION CHANCE
            if len(visible_targets) > 0 and random.random() < 0.6:
                target = random.choice(visible_targets)
                
                # Move Mouse (Human Curve)
                start_pt = await page.evaluate("({x: 540, y: 960})") # Pseudo center? no
                # Just move from current mouse pos (maintained by PW)
                await page.mouse.move(target['x'], target['y'], steps=random.randint(10, 20))
                
                # Action based on type
                if target['type'] == 'CANVAS':
                    await page.mouse.down()
                    await page.mouse.move(target['x'] + 100, target['y'], steps=15)
                    await page.mouse.up()
                elif 'btn' in target['cls'] or target['type'] == 'BUTTON':
                    await page.mouse.down()
                    await page.wait_for_timeout(50)
                    await page.mouse.up()
                else:
                    await page.wait_for_timeout(random.randint(200, 500)) # Hover
                    
            # SCROLL STEP
            step = random.randint(30, 100) # Viewport pixels
            await page.mouse.wheel(0, step)
            await page.wait_for_timeout(random.randint(20, 50))
            
            # Check exit
            new_scroll = await page.evaluate("window.scrollY")
            if new_scroll == current_idx and current_idx > 0:
                 # Stuck = Bottom? or stuck top?
                 # If we tried to scroll 10 times and didn't move...
                 pass # Simple logic: just rely on time or scrollHeight
            
            if time.time() - start_time > duration + 5:
                # Force one last big scroll to ensure footer
                await page.mouse.wheel(0, 1000)
                await page.wait_for_timeout(1000)
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
