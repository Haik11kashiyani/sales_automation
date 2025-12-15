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
        # We construct the Presentation UI *around* the iframe.
        # The iframe 'src' is the actual site.
        
        # Constants for Scaling
        MOBILE_W = 390
        MOBILE_H = 844 # iPhone 12/13/14
        SCALE_FACTOR = 2.3 # Fits 390 * 2.3 = ~897px width
        
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
                    background: radial-gradient(circle at center, #1b1b1b, #000);
                    color: white;
                    font-family: 'Arial', sans-serif;
                    overflow: hidden;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                }}
                
                #header-group {{
                    margin-top: 60px;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    z-index: 10;
                }}
                
                #p-header {{
                    font-size: 40px; font-weight: bold; letter-spacing: 3px;
                    color: #666; text-transform: uppercase;
                }}
                
                #p-title {{
                    font-size: 70px; font-weight: 900;
                    background: linear-gradient(90deg, #fff, #aaa);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    margin-top: 10px;
                }}
                
                /* The Phone Wrapper */
                #phone-wrapper {{
                    margin-top: 60px;
                    position: relative;
                    width: {MOBILE_W * SCALE_FACTOR}px;
                    height: 1250px;
                    /* Visual Border */
                    border: 25px solid #222;
                    border-radius: 50px;
                    box-shadow: 0 0 100px rgba(0, 255, 136, 0.1);
                    overflow: hidden;
                    background: #000;
                    flex-shrink: 0;
                }}
                
                /* The Iframe Itself */
                #content-iframe {{
                    width: {MOBILE_W}px;
                    height: 100%; /* Will fill the scaled height? No, must trigger scroll. */
                    height: {int(1250 / SCALE_FACTOR)}px; /* Logical height to fill frame? No, let's just make it 100% and scroll internal? */
                    /* Better: Make iframe full height of the logic, transform it. */
                    
                    /* Actually, we want the iframe to be the 'window' */
                    width: {MOBILE_W}px;
                    height: 100%; 
                    border: none;
                    background: #fff;
                    
                    transform: scale({SCALE_FACTOR});
                    transform-origin: top left;
                    
                    /* Force Width to be exact logic pixels */
                    /* Wait, if we scale the iframe element, its content scales. */
                    /* But the container is large. */
                }}
                
                /* Better Approach: 
                   Wrapper is 900px wide.
                   Iframe is 390px wide.
                   Transform Scale(2.3) makes Iframe 897px wide.
                   We place Iframe inside Wrapper.
                */
                
                #footer-group {{
                    margin-top: auto;
                    margin-bottom: 80px;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 20px;
                    z-index: 10;
                }}
                
                 .cta-button {{
                    background: linear-gradient(135deg, #0cebeb, #20e3b2, #29ffc6);
                    color: #000;
                    padding: 20px 70px;
                    border-radius: 60px;
                    font-weight: 900;
                    font-size: 40px;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                    box-shadow: 0 0 40px rgba(32, 227, 178, 0.5);
                    animation: pulse-glow 2.5s infinite ease-in-out;
                }}
                
                .cta-subtext {{
                    font-size: 24px; color: #888; font-weight: bold;
                    letter-spacing: 3px; text-transform: uppercase;
                }}
                
                @keyframes pulse-glow {{
                    0% {{ transform: scale(1); box-shadow: 0 0 30px rgba(32, 227, 178, 0.4); }}
                    50% {{ transform: scale(1.03); box-shadow: 0 0 70px rgba(32, 227, 178, 0.7); }}
                    100% {{ transform: scale(1); box-shadow: 0 0 30px rgba(32, 227, 178, 0.4); }}
                }}
                
                #ai-cursor {{
                    position: absolute; top: 0; left: 0;
                    width: 40px; height: 40px;
                    background: rgba(0, 255, 136, 0.9);
                    border: 3px solid white; border-radius: 50%;
                    pointer-events: none; z-index: 9999;
                    box-shadow: 0 0 15px rgba(0,255,136,0.6);
                    transition: transform 0.1s;
                }}
            </style>
        </head>
        <body>
            <div id="header-group">
                <div id="p-header">{header_txt}</div>
                <div id="p-title">{title_txt}</div>
            </div>
            
            <div id="phone-wrapper">
                <iframe id="content-iframe" src="{target_url}" scrolling="yes"></iframe>
            </div>
            
            <div id="footer-group">
                <div class="cta-button">{cta_txt}</div>
                <div class="cta-subtext">{sub_txt}</div>
            </div>
            
            <div id="ai-cursor"></div>
            
            <script>
                // Cursor Logic (Visual Only)
                const c = document.getElementById('ai-cursor');
                document.addEventListener('mousemove', e => {{
                    c.style.left = e.clientX + 'px';
                    c.style.top = e.clientY + 'px';
                }});
                document.addEventListener('mousedown', () => c.style.transform = 'scale(0.8)');
                document.addEventListener('mouseup', () => c.style.transform = 'scale(1)');
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
                const rect = document.getElementById('phone-wrapper').getBoundingClientRect();
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
        cx, cy = frame_to_viewport(MOBILE_W / 2, MOBILE_H / 2)
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
            
            # SCROLLING
            # We need to ensure we reach the END of the page within the duration.
            # 1. Check current progress
            scroll_info = await content_frame.evaluate("""() => {
                return {
                    current: window.scrollY,
                    total: document.body.scrollHeight,
                    view: window.innerHeight
                };
            }""")
            
            # 2. Dynamic Scroll Step based on remaining distance and time
            # But simple robust approach: just scroll aggressively if needed.
            
            remaining_dist = scroll_info['total'] - (scroll_info['current'] + scroll_info['view'])
            
            if remaining_dist > 50:
                # Scroll Logic
                step = random.randint(150, 400) # Faster scrolling
                await content_frame.evaluate(f"window.scrollBy(0, {step})")
                await page.wait_for_timeout(random.randint(400, 800))
            else:
                # Reached bottom! Pause then maybe scroll up a tiny bit or end?
                # Just wait out the duration or break if time is up.
                await page.wait_for_timeout(1000)
                
            # Time check
            if time.time() - start_time > duration + 5:
                # Force one last scroll to bottom just in case?
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
