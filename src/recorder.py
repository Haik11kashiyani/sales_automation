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
                    background: #000;
                    color: white;
                    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                    overflow: hidden;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: space-between; /* Header top, Footer bottom */
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
                #presentation-window {{
                    position: relative;
                    width: {CONTAINER_W}px;
                    height: {CONTAINER_H}px;
                    
                    /* Clean Window Styling - No Phone Artifacts */
                    background: #fff;
                    box-shadow: 0 20px 80px rgba(0,0,0,0.5); /* Deep shadow lift */
                    overflow: hidden; /* No cutting -> Containment */
                    
                    /* Optional: Subtle rounded corners for modern "Card" feel? */
                    /* User said "Central Squared fit". Let's keep it sharp or very minimal radius. */
                    border-radius: 12px; 
                    
                    /* Border to define edges against dark bg */
                    border: 1px solid #333;
                }}
                
                #content-iframe {{
                    width: {VIRTUAL_W}px;
                    height: {int(CONTAINER_H / SCALE_FACTOR)}px; /* Logical Height */
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
                    width: 32px; height: 32px;
                    border-radius: 50%;
                    background: rgba(255, 50, 50, 0.8); /* Highly visible interaction point */
                    border: 3px solid white;
                    pointer-events: none; z-index: 9999;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                    transition: transform 0.1s;
                }}
            </style>
        </head>
        <body>
            <div id="header-group">
                <div id="p-header">{header_txt}</div>
                <div id="p-title">{title_txt}</div>
            </div>
            
            <div id="presentation-window">
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
                document.addEventListener('mousemove', e => {{
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
        
        # Move mouse to center initially
        virtual_h = int(CONTAINER_H / SCALE_FACTOR)
        cx, cy = frame_to_viewport(VIRTUAL_W / 2, virtual_h / 2)
        await page.mouse.move(cx, cy)
        
        while True:
            # 1. Find Candidates inside FRAME
            # We look for interactive elements
            # Note: We query the FRAME, not the PAGE.
            
            candidates = await content_frame.evaluate("""() => {
                const els = Array.from(document.querySelectorAll('button, a, input, header, footer, nav, section, h1, h2, .card, .interactive'));
                return els.map(e => {
                    const r = e.getBoundingClientRect();
                    return {
                        x: r.left + r.width/2,
                        y: r.top + r.height/2,
                        role: e.tagName,
                        cls: Array.from(e.classList).join(' ')
                    };
                });
            }""")
            
            # Filter candidates that are currently visible in the Iframe's Viewport
            # The iframe window height is ~1250 / 2.3 = ~543px (Layout Height)
            # Actually, "height: 100%" on iframe in HTML means it takes the height of the parent (1250).
            # But scaled... CSS Transforms on Iframes are tricky.
            # If parent is 1250px high, and iframe is scaled 2.3x...
            # The logical height of the iframe document should be 1250 / 2.3 = 543px.
            # So elements with Y > 543 are "below the fold".
            
            # Use `content_frame.evaluate('window.innerHeight')` to be sure.
            frame_viewport_h = await content_frame.evaluate("window.innerHeight")
            
            visible_candidates = [c for c in candidates if 0 <= c['y'] <= frame_viewport_h]
            
            should_interact = False
            target = None
            if visible_candidates and random.random() < 0.7:
                target = random.choice(visible_candidates)
                should_interact = True
                
            if should_interact and target:
                # Convert to Viewport
                vx, vy = frame_to_viewport(target['x'], target['y'])
                
                # Move
                await page.mouse.move(vx, vy, steps=random.randint(15, 30))
                
                # Interaction
                if target['role'] in ['BUTTON', 'A', 'INPUT'] or 'btn' in target['cls']:
                    await page.mouse.down()
                    await page.wait_for_timeout(random.randint(50, 100))
                    await page.mouse.up()
                else:
                    await page.wait_for_timeout(random.randint(200, 500))
            
            # SCROLLING - BUTTER SMOOTH
            # Instead of jumpy steps, use native smooth scrolling with calculated pauses.
            
            # 1. Check current progress
            scroll_info = await content_frame.evaluate("""() => {
                return {
                    current: window.scrollY,
                    total: document.body.scrollHeight,
                    view: window.innerHeight
                };
            }""")
            
            remaining_dist = scroll_info['total'] - (scroll_info['current'] + scroll_info['view'])
            
            if remaining_dist > 50:
                # Smooth Scroll Logic
                # We scroll a smaller chunk but smoother.
                step = random.randint(250, 450) 
                
                # Execute Smooth Scroll
                await content_frame.evaluate(f"window.scrollBy({{top: {step}, left: 0, behavior: 'smooth'}})")
                
                # Wait for the smooth scroll to complete visually
                # Browser smooth scroll takes time (approx 300-500ms).
                await page.wait_for_timeout(random.randint(800, 1200)) # Pause to let user read content
            else:
                await page.wait_for_timeout(1000)
                
            # Time check
            if time.time() - start_time > duration + 5:
                # Force one last smooth scroll to bottom?
                break
                
        await context.close()
        await browser.close()
        
        # Save Video logic (similar to before, assuming Context recorded it)
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
