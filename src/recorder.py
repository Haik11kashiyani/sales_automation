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

async def record_url(file_path: str, duration: float, output_path: str, overlay_text: str = "", overlay_header: str = "", cta_text: str = "", cta_subtext: str = ""):
    """
    Records a webpage interaction via localhost using an IFRAME isolation strategy.
    The Host Page is 1080x1920 (Presentation).
    The Content is an Iframe (375x100%) scaled up.
    """
    rel_path = os.path.relpath(file_path, SERVER_ROOT)
    target_url = f"http://localhost:{PORT}/{rel_path.replace(os.sep, '/')}"
    
    print(f"Recording URL: {target_url} | Duration: {duration}s")

    async with async_playwright() as p:
        # Launch with flags to bypass CORS and X-Frame-Options for universal Iframe support
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--enable-features=OverlayScrollbar', 
                '--no-sandbox', 
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process'
            ]
        )
        
        context = await browser.new_context(
            viewport={"width": 1080, "height": 1920},
            device_scale_factor=1.0,
            has_touch=True,
            record_video_dir=os.path.dirname(output_path),
            record_video_size={"width": 1080, "height": 1920}
        )
        
        page = await context.new_page()
        
        # --- IFRAME HOST PAGE GENERATION ---
        # "Universal Clean Layout" Strategy
        # 1. Background: Dynamic/Dark.
        # 2. Container: "Presentation Window" - A clean, sharp, maximized container.
        # 3. Content: 100% Fit Iframe. No cutting.
        
        # Dimensions for the "Virtual Browser"
        # We want a modern mobile/tablet feel. 
        # Width: 430px (iPhone Pro Max width) -> Scaled up to fill 1080p
        # 1080px total. Margins 40px? -> 1000px targets.
        # Scale: 1000 / 430 = 2.32
        
        VIRTUAL_W = 430 
        SCALE_FACTOR = 2.3
        CONTAINER_W = int(VIRTUAL_W * SCALE_FACTOR) # ~989px
        
        # Height: fill available space between Header and Footer
        # Header ~200px. Footer ~250px. Total 1920.
        # Available ~1400px.
        CONTAINER_H = 1350 
        
        # Header/Footer Text Defaults
        header_txt = overlay_header if overlay_header else "WEB DESIGN AWARDS"
        title_txt = overlay_text if overlay_text else "FUTURE OF WEB"
        cta_txt = cta_text if cta_text else "VISIT WEBSITE"
        sub_txt = cta_subtext if cta_subtext else "LINK IN BIO"

        host_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    margin: 0; padding: 0;
                    width: 1080px; height: 1920px;
                    /* VIBRANT Background - Distinctly NOT Black */
                    background: linear-gradient(-45deg, #1a1a2e, #16213e, #4a1c40, #1a1a2e);
                    background-size: 400% 400%;
                    animation: gradientBG 15s ease infinite;
                    color: white;
                    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                    overflow: hidden;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: space-between;
                }}
                
                @keyframes gradientBG {{
                    0% {{ background-position: 0% 50%; }}
                    50% {{ background-position: 100% 50%; }}
                    100% {{ background-position: 0% 50%; }}
                }}
                
                /* --- HEADER SECTION --- */
                #header-group {{
                    margin-top: 80px;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    z-index: 10;
                    height: 200px;
                }}
                
                #p-header {{
                    font-size: 35px; font-weight: 700; letter-spacing: 4px;
                    color: #888; text-transform: uppercase;
                }}
                
                #p-title {{
                    font-size: 60px; font-weight: 900;
                    text-align: center;
                    background: linear-gradient(135deg, #fff 0%, #aaa 100%);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    margin-top: 15px;
                    line-height: 1.1;
                }}
                
                /* --- PRESENTATION WINDOW (The "Screen") --- */
                /* --- PRESENTATION WINDOW (The "Screen") --- */
                #presentation-window {{
                    position: relative;
                    width: {CONTAINER_W}px;
                    height: {CONTAINER_H}px;
                    
                    /* Premium "Pop" Styling */
                    background: #fff;
                    
                    /* Deep, Multi-layered Shadow for Maximum Separation */
                    box-shadow: 
                        0 0 0 1px rgba(0,0,0, 0.8), /* Crisp black line */
                        0 30px 80px rgba(0,0,0, 0.7), /* Deep Ambient */
                        0 0 150px rgba(0,0,0, 0.9); /* Void Separation */
                        
                    overflow: hidden; 
                    
                    /* Subtle "High-End" Border Radius */
                    border-radius: 16px; 
                    
                    /* Glass-like Edge Definition */
                    border: 4px solid rgba(255, 255, 255, 0.1);
                    display: flex; flex-direction: column;
                }}
                
                /* Browser Mockup Header */
                #browser-header {{
                    height: 40px;
                    background: #f0f0f0;
                    border-bottom: 1px solid #ddd;
                    display: flex; align-items: center;
                    padding: 0 15px; gap: 10px;
                    flex-shrink: 0; /* Prevent header from shrinking */
                }}
                .browser-dot {{ width: 12px; height: 12px; border-radius: 50%; }}
                .dot-red {{ background: #ff5f56; }}
                .dot-yellow {{ background: #ffbd2e; }}
                .dot-green {{ background: #27c93f; }}
                .browser-bar {{
                    flex-grow: 1; height: 24px; background: #fff; border-radius: 4px;
                    margin-left: 10px; border: 1px solid #e0e0e0;
                }}
                
                #content-iframe {{
                    width: {VIRTUAL_W}px;
                    /* Subtract Header Height (40px) to fit perfectly */
                    height: {int((CONTAINER_H - 40) / SCALE_FACTOR)}px; 
                    border: none;
                    background: #fff;
                    
                    transform: scale({SCALE_FACTOR});
                    transform-origin: top left;
                    
                    /* Ensure full rendering */
                    display: block;
                }}
                
                /* --- FOOTER SECTION --- */
                #footer-group {{
                    margin-bottom: 90px;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 15px;
                    z-index: 10;
                    height: 200px;
                    justify-content: flex-end;
                }}
                
                 .cta-button {{
                    background: #fff; /* High contrast */
                    color: #000;
                    padding: 25px 80px;
                    border-radius: 4px; /* Sharp professional look */
                    font-weight: 900;
                    font-size: 45px;
                    text-transform: uppercase;
                    letter-spacing: 2px;
                    box-shadow: 0 10px 40px rgba(255, 255, 255, 0.2);
                    animation: pulse-glow 3s infinite ease-in-out;
                }}
                
                .cta-subtext {{
                    font-size: 26px; color: #666; font-weight: 600;
                    letter-spacing: 2px; text-transform: uppercase;
                }}
                
                @keyframes pulse-glow {{
                    0% {{ transform: scale(1); }}
                    50% {{ transform: scale(1.02); box-shadow: 0 10px 60px rgba(255, 255, 255, 0.4); }}
                    100% {{ transform: scale(1); }}
                }}
                
                #ai-cursor {{
                    position: absolute; top: 0; left: 0;
                    width: 30px; height: 30px;
                    /* High Visibility Touch Indicator - Solid White */
                    background: #ffffff;
                    border: 2px solid rgba(0, 0, 0, 0.1);
                    border-radius: 50%;
                    pointer-events: none; z-index: 9999;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
                    transition: transform 0.1s, background 0.2s, opacity 0.3s;
                    opacity: 0; /* Hidden by default to prevent 0,0 glitch */
                }}
            </style>
        </head>
        <body>
            <div id="header-group">
                <div id="p-header">{header_txt}</div>
                <div id="p-title">{title_txt}</div>
            </div>
            
            <div id="presentation-window">
                <div id="browser-header">
                    <div class="browser-dot dot-red"></div>
                    <div class="browser-dot dot-yellow"></div>
                    <div class="browser-dot dot-green"></div>
                    <div class="browser-bar"></div>
                </div>
                <iframe id="content-iframe" src="{target_url}" scrolling="yes"></iframe>
            </div>
            
            <div id="footer-group">
                <div class="cta-button">{cta_txt}</div>
                <div class="cta-subtext">{sub_txt}</div>
            </div>
            
            <div id="ai-cursor"></div>
            
            <script>
                // Cursor Logic
                const c = document.getElementById('ai-cursor');
                let isVisible = false;
                
                document.addEventListener('mousemove', e => {{
                    if (!isVisible) {{
                        c.style.opacity = '1';
                        isVisible = true;
                    }}
                    c.style.left = e.clientX + 'px';
                    c.style.top = e.clientY + 'px';
                }});
                document.addEventListener('mousedown', () => {{
                    c.style.transform = 'scale(0.8)';
                    c.style.background = 'white';
                }});
                document.addEventListener('mouseup', () => {{
                    c.style.transform = 'scale(1)';
                    c.style.background = 'rgba(255, 50, 50, 0.8)';
                }});
            </script>
        </body>
        </html>
        """
        
        # Load the Host Page
        await page.set_content(host_html)
        
        # Helper: Wait for Iframe to Load
        # In Playwright, we can get the frame by name or URL? 
        # Since it's dynamically loaded, we wait for the element then get content frame.
        iframe_element = await page.query_selector('#content-iframe')
        content_frame = await iframe_element.content_frame()
        
        if not content_frame:
            # Wait a bit if not ready
            await page.wait_for_timeout(2000)
            content_frame = await iframe_element.content_frame()
            
        if not content_frame:
            print("Error: Could not access content iframe.")
            return

        # Wait for site to load inside iframe
        try:
            await content_frame.wait_for_load_state("networkidle")
        except:
            await page.wait_for_timeout(2000)
            
        print("Iframe Loaded. Starting Interaction Loop.")
        
        # --- COORDINATE TRANSLATION SYSTEM ---
        # We need to map [Frame X, Y] -> [Viewport X, Y] to move the mouse.
        #
        # Math:
        # Wrapper is centered horizontally?
        # Host: 1080w. Wrapper: (390 * 2.3) = 897w.
        # Wrapper Left = (1080 - 897) / 2 = 91.5px.
        # Wrapper Top = Computed by Flex (Margin 60 + Header ~100) = ~160px.
        #
        # BUT relying on static math is risky. Let's ask the page!
        
        async def get_wrapper_offset():
            return await page.evaluate("""() => {
                const rect = document.getElementById('presentation-window').getBoundingClientRect();
                return { x: rect.left, y: rect.top };
            }""")
            
        wrapper_offset = await get_wrapper_offset()
        # Scale Factor is known: 2.3
        
        def frame_to_viewport(fx, fy):
            # The iframe content is scaled by SCALE_FACTOR.
            # So 1px in Frame = 2.3px in Viewport.
            vx = wrapper_offset['x'] + (fx * SCALE_FACTOR)
            vy = wrapper_offset['y'] + (fy * SCALE_FACTOR)
            return vx, vy

        # --- INTERACTION LOOP (Targeting the FRAME) ---
        
        # 1. Hide Scrollbars inside Iframe (Inject CSS into Frame)
        await content_frame.add_style_tag(content="""
            ::-webkit-scrollbar { display: none; }
            body { -ms-overflow-style: none; scrollbar-width: none; }
        """)

        start_time = time.time()
        
        # --- VIRAL CHOREOGRAPHY ENGINE ---
        
        async def human_move(start_x, start_y, end_x, end_y, steps=60):
            """Moves mouse in a human-like quadratic bezier curve."""
            # Random control point deviation
            offset = random.randint(-200, 200)
            ctrl_x = (start_x + end_x) / 2 + offset
            ctrl_y = (start_y + end_y) / 2 + (offset / 2)
            
            for i in range(steps + 1):
                t = i / steps
                # Quadratic Bezier Formula
                nt = 1 - t
                x = (nt**2 * start_x) + (2 * nt * t * ctrl_x) + (t**2 * end_x)
                y = (nt**2 * start_y) + (2 * nt * t * ctrl_y) + (t**2 * end_y)
                
                # Add tiny jitter
                x += random.uniform(-2, 2)
                y += random.uniform(-2, 2)
                
                await page.mouse.move(x, y)
                # Variable sleep for acceleration/deceleration
                # Fast in middle, slow at ends
                await asyncio.sleep(0.005 + 0.01 * (4 * (t - 0.5)**2))

        # Initial Center
        current_x = 540 # Middle of 1080
        current_y = 960 # Middle of 1920
        await page.mouse.move(current_x, current_y)

        while True:
            # 1. Analyze Visible Elements (The "Eye")
            # Priority: H1/H2 > Cards > Buttons > Images
            candidates = await content_frame.evaluate("""() => {
                const els = Array.from(document.querySelectorAll('h1, h2, h3, .card, button, a.btn, img, section'));
                return els.map(e => {
                    const r = e.getBoundingClientRect();
                    // Basic scoring
                    let score = 1;
                    if (e.tagName.startsWith('H')) score = 3;
                    if (e.classList.contains('card')) score = 2;
                    if (e.tagName === 'BUTTON') score = 2;
                    
                    return {
                        x: r.left + r.width/2,
                        y: r.top + r.height/2,
                        width: r.width,
                        height: r.height,
                        role: e.tagName,
                        cls: Array.from(e.classList).join(' '),
                        score: score
                    };
                });
            }""")
            
            frame_h = await content_frame.evaluate("window.innerHeight")
            visible_targets = [c for c in candidates if 100 < c['y'] < frame_h - 100]
            
            # Sort by "Viral Score" (Focus on content first)
            visible_targets.sort(key=lambda x: x['score'], reverse=True)
            
            # Action Decision
            action_happened = False
            
            if visible_targets and random.random() < 0.8:
                # Pick a high-value target
                # Introduce randomness but bias towards top scored
                target = random.choice(visible_targets[:3]) 
                
                # Convert to Viewport
                vx, vy = frame_to_viewport(target['x'], target['y'])
                
                # Check bounds
                if 0 <= vx <= 1080 and 0 <= vy <= 1920:
                    # Move to it organically
                    await human_move(current_x, current_y, vx, vy, steps=random.randint(40, 80))
                    current_x, current_y = vx, vy
                    
                    # "The Presenter Point" (Wiggle)
                    # Small circle/wiggle to indicate "Look at this"
                    for _ in range(20):
                        wx = vx + random.uniform(-10, 10)
                        wy = vy + random.uniform(-10, 10)
                        await page.mouse.move(wx, wy)
                        await asyncio.sleep(0.01)
                        
                    # Hover effect wait
                    await page.wait_for_timeout(random.randint(500, 1500))
                    
                    # Click if interaction
                    if target['role'] == 'BUTTON' or 'btn' in target['cls'] or target['role'] == 'A':
                        if random.random() < 0.5:
                            await page.mouse.down()
                            await page.wait_for_timeout(100)
                            await page.mouse.up()
                            await page.wait_for_timeout(1000)
                    
                    action_happened = True

            if not action_happened:
                 # Idle / Read
                 await page.wait_for_timeout(random.randint(500, 1000))

            # 2. SCROLLING (The "Feed" Rhythm)
            # Scroll > Pause to Read > Scroll
            
            scroll_info = await content_frame.evaluate("""() => {
                 return { y: window.scrollY, total: document.body.scrollHeight, h: window.innerHeight };
            }""")
            
            if scroll_info['y'] + scroll_info['h'] < scroll_info['total'] - 50:
                # Scroll
                step = random.randint(400, 700) # Big chunks like a swipe
                await content_frame.evaluate(f"window.scrollBy({{top: {step}, left: 0, behavior: 'smooth'}})")
                
                # Follow the scroll with mouse (physically move mouse up slightly as if dragging)
                # await human_move(current_x, current_y, current_x, current_y - 100, steps=20)
                # current_y -= 100
                
                # CRITICAL: Pause after scroll to let viewer digest content
                await page.wait_for_timeout(random.randint(1500, 2500))
            else:
                 await page.wait_for_timeout(1000)

            # Time check
            if time.time() - start_time > duration + 3:
                break
                
        # Save Video Logic - Correct Sequence
        video = page.video
        await context.close() # Writes video to disk
        
        saved_video_path = None
        if video:
            saved_video_path = await video.path()
            
        await browser.close()
        
        if saved_video_path:
             if os.path.exists(output_path):
                 os.remove(output_path)
             # Use shutil for cross-filesystem safety
             import shutil
             shutil.move(saved_video_path, output_path)
             print(f"Video saved to {output_path}")
        else:
            print("Error: No video recorded.")

if __name__ == "__main__":
    # Test execution
    # Start server for testing
    run_server_in_thread()
    time.sleep(1) # wait for server
    
    test_html = os.path.abspath(os.path.join(os.path.dirname(__file__), "../content_pool/business_01/index.html"))
    asyncio.run(record_url(test_html, 30, "test_output.mp4"))
