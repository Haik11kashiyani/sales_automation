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
        
        # --- VIRAL LAYOUT ENGINE (DESKTOP MODE) ---
        # User Feedback: "Proper Website Display", "No Cutting".
        # Solution: Switch from Mobile (430px) to Desktop (1024px).
        # This provides a massive, professional viewport.
        
        VIRTUAL_W = 1024 
        
        # Maximize the container height to fill the Short
        # Header (~150) + Footer (~150) = 300. 1920 - 300 = 1620.
        CONTAINER_H = 1550 
        
        # We need to fit 1024px into the 1080px video (with margins).
        # Target Container Width: 1000px (40px margin total)
        CONTAINER_W = 1000
        
        # Scale: Shrink slightly to fit
        SCALE_FACTOR = CONTAINER_W / VIRTUAL_W # ~0.97
        
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
                    /* VIBRANT Background */
                    background: linear-gradient(-45deg, #1a1a2e, #16213e, #4a1c40, #1a1a2e);
                    background-size: 400% 400%;
                    animation: gradientBG 15s ease infinite;
                    color: white;
                    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                    overflow: hidden;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: space-between; /* Push Footer down */
                    padding-bottom: 40px; /* Small bottom padding */
                }}
                
                @keyframes gradientBG {{
                    0% {{ background-position: 0% 50%; }}
                    50% {{ background-position: 100% 50%; }}
                    100% {{ background-position: 0% 50%; }}
                }}
                
                /* --- HEADER SECTION --- */
                #header-group {{
                    margin-top: 50px; /* Reduced top margin */
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    z-index: 10;
                    height: 140px; /* Compact header */
                    flex-shrink: 0;
                }}
                
                #p-header {{
                    font-size: 30px; font-weight: 700; letter-spacing: 4px;
                    color: #888; text-transform: uppercase;
                }}
                
                #p-title {{
                    font-size: 50px; font-weight: 900;
                    text-align: center;
                    background: linear-gradient(135deg, #fff 0%, #aaa 100%);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    margin-top: 10px;
                    line-height: 1.1;
                    max-width: 900px;
                }}
                
                /* --- PRESENTATION WINDOW (The "Screen") --- */
                #presentation-window {{
                    position: relative;
                    width: {CONTAINER_W}px;
                    height: {CONTAINER_H}px;
                    
                    /* Premium "Pop" Styling */
                    background: #fff;
                    
                    /* Deep, Multi-layered Shadow */
                    box-shadow: 
                        0 0 0 1px rgba(0,0,0, 0.8), 
                        0 30px 80px rgba(0,0,0, 0.7),
                        0 0 150px rgba(0,0,0, 0.9);
                        
                    overflow: hidden; 
                    
                    /* Desktop Radius is usually sharper */
                    border-radius: 12px; 
                    
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

        # --- PROFESSIONAL PRESENTATION SCRIPT (UPDATED FOR NEW PORTFOLIO) ---
        
        async def move_and_hover(selector, hover_duration=1.0):
             """Finds an element in the frame, moves to it smoothly, and hovers."""
             try:
                 box = await content_frame.evaluate(f"""(sel) => {{
                     const el = document.querySelector(sel);
                     if(!el) return null;
                     const r = el.getBoundingClientRect();
                     return {{ x: r.left + r.width/2, y: r.top + r.height/2 }};
                 }}""", selector)
                 
                 if box:
                     vx, vy = frame_to_viewport(box['x'], box['y'])
                     await human_move(current_x, current_y, vx, vy, steps=50)
                     return vx, vy # Update current pos
             except Exception as e:
                 print(f"Prop Move Failed: {e}")
             return current_x, current_y

        # 1. HERO PHASE (0-4s) - Loading & Intro
        print("Phase 1: Hero")
        await asyncio.sleep(3.5) # Wait for Shutter/Loading animation
        # Move to "View All Work" button just to hint action
        current_x, current_y = await move_and_hover(".liquid-btn")
        await asyncio.sleep(1.0) 

        # 2. ABOUT PHASE (4-8s)
        print("Phase 2: About")
        await content_frame.evaluate("window.scrollTo({top: window.innerHeight * 0.9, behavior: 'smooth'})")
        await asyncio.sleep(2.0)
        # Read the text (Slow pan)
        await human_move(current_x, current_y, 800, 500, steps=80)
        
        # 3. PROCESS PHASE (8-14s)
        print("Phase 3: Process")
        await content_frame.evaluate("window.scrollTo({top: window.innerHeight * 1.8, behavior: 'smooth'})")
        await asyncio.sleep(1.5)
        
        # Hover over Process Steps to trigger dots
        steps = [".process-step:nth-child(1)", ".process-step:nth-child(3)", ".process-step:nth-child(5)"]
        for step in steps:
            await move_and_hover(step, hover_duration=0.5)
            await asyncio.sleep(0.5)

        # 4. TECH ARSENAL (14-17s)
        print("Phase 4: Tech Arsenal")
        await content_frame.evaluate("document.getElementById('tech').scrollIntoView({behavior: 'smooth'})")
        await asyncio.sleep(1.5)
        # Move mouse rapidly across columns to affect the speed (if interactive)
        await human_move(200, 500, 800, 500, steps=20)
        await asyncio.sleep(1.0)
        
        # 5. PROJECTS SLIDER (17-25s)
        print("Phase 5: Projects ( pinned )")
        await content_frame.evaluate("document.getElementById('projects').scrollIntoView({behavior: 'smooth'})")
        await asyncio.sleep(1.0)
        
        # Scroll DEEP to animate the pinned slider
        # We need to scroll approx 3-4 viewports worth
        for _ in range(5):
             await content_frame.evaluate("window.scrollBy({top: window.innerHeight * 0.8, left: 0, behavior: 'smooth'})")
             await asyncio.sleep(1.2) # Wait for slide transition
        
        # 6. STATS / AUTHORITY (25-28s)
        print("Phase 6: Authority")
        await content_frame.evaluate("document.getElementById('authority').scrollIntoView({behavior: 'smooth'})")
        await asyncio.sleep(1.5)
        
        # Trigger Spotlight Effect
        box = await move_and_hover(".stat-box:nth-child(2)") # Projects Shipped
        # Wiggle to show spotlight
        for _ in range(15):
             await page.mouse.move(current_x + random.randint(-50,50), current_y + random.randint(-50,50))
             await asyncio.sleep(0.02)
             
        # 7. CONTACT (28-30s)
        print("Phase 7: Contact")
        await content_frame.evaluate("document.getElementById('contact-form-section').scrollIntoView({behavior: 'smooth'})")
        await asyncio.sleep(1.0)
        
        # Hover Submit
        await move_and_hover(".submit-btn")
        await asyncio.sleep(1.0)
        
        # End of Script
                
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
