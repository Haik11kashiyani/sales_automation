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

# --- ULTRAMODERN CHOREOGRAPHY ENGINE ---

class VelocityInput:
    """
    Simulates physical input devices with momentum, friction, and biological tremors.
    """
    def __init__(self, page, frame, wrapper_offset, scale_factor):
        self.page = page
        self.frame = frame
        self.wrapper_offset = wrapper_offset
        self.scale_factor = scale_factor
        self.mouse_x = 540
        self.mouse_y = 960

    def frame_to_viewport(self, fx, fy):
        vx = self.wrapper_offset['x'] + (fx * self.scale_factor)
        vy = self.wrapper_offset['y'] + (fy * self.scale_factor)
        return vx, vy

    async def human_move(self, target_fx, target_fy, speed="normal", overshoot=True):
        """
        Moves mouse to a Frame Coordinate (fx, fy) using:
        1. Fitts's Law approximation (speed proportional to distance).
        2. Biological sub-movements (initial impulse + correction).
        3. Motor variations (jitter).
        """
        vx, vy = self.frame_to_viewport(target_fx, target_fy)
        
        start_x, start_y = self.mouse_x, self.mouse_y
        dist = math.hypot(vx - start_x, vy - start_y)
        
        # Duration based on distance (Fitts Law-ish)
        # Closer = faster relative to distance, Farther = slower
        base_time = 0.5 if speed == "fast" else 0.8
        duration = base_time + (dist / 2000.0) 
        
        if overshoot and dist > 100:
            # Main ballistic movement
            overshoot_dist = min(dist * 0.1, 50)
            angle = math.atan2(vy - start_y, vx - start_x)
            ov_x = vx + math.cos(angle) * overshoot_dist
            ov_y = vy + math.sin(angle) * overshoot_dist
            
            await self._bezier_curve(start_x, start_y, ov_x, ov_y, duration * 0.8)
            await asyncio.sleep(random.uniform(0.05, 0.15)) # Reaction time
            await self._bezier_curve(ov_x, ov_y, vx, vy, duration * 0.3) # Correction
        else:
            await self._bezier_curve(start_x, start_y, vx, vy, duration)
            
        self.mouse_x, self.mouse_y = vx, vy

    async def _bezier_curve(self, sx, sy, ex, ey, duration):
        steps = int(duration * 60) # 60fps
        if steps < 1: steps = 1

        # Control points for arc
        offset_strength = random.randint(-100, 100)
        cx = (sx + ex) / 2 + random.randint(-50, 50)
        cy = (sy + ey) / 2 + offset_strength
        
        for i in range(steps + 1):
            t = i / steps
            
            # Bezier Path
            nt = 1 - t
            bx = (nt**2 * sx) + (2 * nt * t * cx) + (t**2 * ex)
            by = (nt**2 * sy) + (2 * nt * t * cy) + (t**2 * ey)
            
            # Micro-tremors (Bio-noise)
            # Increases when moving slow (fine motor control struggles)
            noise = random.uniform(-1, 1)
            
            await self.page.mouse.move(bx + noise, by + noise)
            
            # Timing: Constant delta for smoothness
            dt = duration / steps
            await asyncio.sleep(dt)

    async def kinetic_scroll_to(self, target_y):
        """
        Simulates "Flick" scrolling with inertial decay.
        """
        current_y = await self.frame.evaluate("window.scrollY")
        if abs(target_y - current_y) < 10: return

        distance = target_y - current_y
        
        # 1. ACCELERATE (The Flick)
        # We ramp up velocity quickly
        velocity = 0
        direction = 1 if distance > 0 else -1
        
        # SHORTS OPTIMIZATION: Faster flicks
        # Peak velocity depends on distance, but capped higher
        peak_velocity = min(abs(distance) / 8, 120) * direction
        
        # Simulation Loop
        pos = current_y
        velocity = peak_velocity # Instant flick start for responsiveness
        
        # Physics Params
        friction = 0.92 # Slightly more friction for "snappy" feel
        
        while abs(pos - target_y) > 10 and abs(velocity) > 0.5:
            # Apply Friction
            velocity *= friction
            
            # Update Position
            pos += velocity
            
            # Boundary Check
            if (direction > 0 and pos > target_y) or (direction < 0 and pos < target_y):
                # We overshot or arrived
                pos = target_y
                break
                
            await self.frame.evaluate(f"window.scrollTo(0, {pos})")
            
            # While scrolling, eyes (mouse) drift slightly
            drift_x = self.mouse_x + random.randint(-2, 2)
            drift_y = self.mouse_y + random.randint(-5, 5) 
            await self.page.mouse.move(drift_x, drift_y)
            
            await asyncio.sleep(0.016) # ~60fps
            
        # Final snap
        await self.frame.evaluate(f"window.scrollTo(0, {target_y})")


async def analyze_and_choreograph(page, frame, input_sys):
    """
    Scans the page for semantic meaning and creates a improv performance.
    """
    print(">> AI Director: Scanning Scene...")
    
    # 1. DISCOVER SECTIONS
    # We look for Semantic Tags or IDs
    sections = await frame.evaluate("""() => {
        const candidates = document.querySelectorAll('section, header, footer, .hero, .panel, div[id]');
        const results = [];
        let runningY = 0;
        
        candidates.forEach((el, index) => {
            const rect = el.getBoundingClientRect();
            // Filter invisible or tiny
            if (rect.height < 100) return;
            // Filter nested? No, keeps it simple.
            
            // Get 'Interest Points' inside
            const headers = Array.from(el.querySelectorAll('h1, h2, h3'))
                                .map(h => {
                                    const r = h.getBoundingClientRect();
                                    return { 
                                        text: h.innerText, 
                                        x: r.left + r.width/2,
                                        y: r.top + r.height/2
                                    };
                                });
                                
            const buttons = Array.from(el.querySelectorAll('button, a[class*="btn"], .cta, [role="button"]'))
                                .map(b => {
                                    const r = b.getBoundingClientRect();
                                    return {
                                        selector: b.className,
                                        x: r.left + r.width/2,
                                        y: r.top + r.height/2
                                    };
                                });
            
            results.push({
                index: index,
                id: el.id || el.className || 'section-'+index,
                top: rect.top + window.scrollY, // Absolute Y
                height: rect.height,
                headers: headers,
                buttons: buttons
            });
        });
        
        // Remove duplicates (by Y)
        const unique = [];
        const seenY = new Set();
        results.forEach(r => {
            const y = Math.floor(r.top / 100) * 100; // Fuzzy
            if(!seenY.has(y)) {
                seenY.add(y);
                unique.push(r);
            }
        });
        
        return unique.sort((a,b) => a.top - b.top);
    }""")
    
    print(f">> AI Director: Found {len(sections)} Scenes.")
    
    # 2. PERFORM
    
    for i, section in enumerate(sections):
        print(f"   Action: Scene {i} ('{section['id']}')")
        
        # A. SCROLL TO SCENE (Physics)
        # We target slightly above the section top for context (padding)
        target_y = max(0, section['top'] - 50)
        
        # Dont scroll if we are already close (first section)
        current_y = await frame.evaluate("window.scrollY")
        if abs(target_y - current_y) > 100:
            await input_sys.kinetic_scroll_to(target_y)
        
        # SHORTS OPTIMIZATION: Less hesitation
        await asyncio.sleep(0.2) 
        
        # B. READ HEADLINES or INTERACT
        # Only if there are headers
        if section['headers']:
            # SHORTS OPTIMIZATION: Only read 40% of the time, keep it moving
            if random.random() < 0.4:
                # Let's do a "Visual Re-Scan" of the current viewport
                await input_sys.page.wait_for_timeout(100) # tiny wait
                
                visible_points = await frame.evaluate("""() => {
                    const nodes = document.querySelectorAll('h1, h2, h3, p, li, button, a');
                    const points = [];
                    const vh = window.innerHeight;
                    nodes.forEach(n => {
                        const r = n.getBoundingClientRect();
                        if (r.top > 100 && r.bottom < vh - 100) {
                            points.push({
                                x: r.left + r.width / 2,
                                y: r.top + r.height / 2
                            });
                        }
                    });
                    return points;
                }""")
                
                if visible_points:
                    # Trace just 1 item quickly
                    p = random.choice(visible_points)
                    await input_sys.human_move(p['x'], p['y'], speed="fast", overshoot=False)
                    await asyncio.sleep(random.uniform(0.3, 0.6))
        
        # C. DYNAMIC DURATION
        # SHORTS OPTIMIZATION: Much faster reading
        # Height / 1000 means 1000px height = 1s dwell. (Previously /500 = 2s)
        wait_time = min(section['height'] / 1000, 1.2) 
        await asyncio.sleep(wait_time)


async def record_url(file_path: str, duration: float, output_path: str, overlay_text: str = "", overlay_header: str = "", cta_text: str = "", cta_subtext: str = ""):
    """
    Records a webpage interaction via localhost using an IFRAME logic.
    """
    rel_path = os.path.relpath(file_path, SERVER_ROOT)
    target_url = f"http://localhost:{PORT}/{rel_path.replace(os.sep, '/')}"
    
    print(f"Recording URL: {target_url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--enable-features=OverlayScrollbar', '--no-sandbox', '--disable-web-security']
        )
        
        # Standard Presentation Viewport
        context = await browser.new_context(
            viewport={"width": 1080, "height": 1920},
            device_scale_factor=1.0,
            record_video_dir=os.path.dirname(output_path),
            record_video_size={"width": 1080, "height": 1920}
        )
        
        page = await context.new_page()
        
        # --- UI CONSTANTS ---
        VIRTUAL_W = 1024 
        # Maximize vertically
        CONTAINER_H = 1550 
        CONTAINER_W = 1000
        SCALE_FACTOR = CONTAINER_W / VIRTUAL_W

        # Header/Footer Text Defaults
        header_txt = overlay_header.upper() if overlay_header else "WEB DESIGN AWARDS"
        title_txt = overlay_text.upper() if overlay_text else "FUTURE OF WEB"
        cta_txt = cta_text.upper() if cta_text else "VISIT WEBSITE"
        sub_txt = cta_subtext.upper() if cta_subtext else "LINK IN BIO"

        host_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    margin: 0; padding: 0;
                    width: 1080px; height: 1920px;
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
                    padding-bottom: 40px;
                }}
                
                @keyframes gradientBG {{
                    0% {{ background-position: 0% 50%; }}
                    50% {{ background-position: 100% 50%; }}
                    100% {{ background-position: 0% 50%; }}
                }}
                
                /* HEADER */
                #header-group {{
                    margin-top: 50px;
                    display: flex; flex-direction: column; align-items: center;
                    z-index: 10; height: 140px; flex-shrink: 0;
                }}
                #p-header {{ font-size: 30px; font-weight: 700; letter-spacing: 4px; color: #888; text-transform: uppercase; }}
                #p-title {{
                    font-size: 50px; font-weight: 900; text-align: center;
                    background: linear-gradient(135deg, #fff 0%, #aaa 100%);
                    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                    margin-top: 10px; line-height: 1.1; max-width: 900px;
                }}
                
                /* PRESENTATION WINDOW */
                #presentation-window {{
                    position: relative;
                    width: {CONTAINER_W}px; height: {CONTAINER_H}px;
                    background: #fff;
                    box-shadow: 0 0 0 1px rgba(0,0,0, 0.8), 0 30px 80px rgba(0,0,0, 0.7), 0 0 150px rgba(0,0,0, 0.9);
                    overflow: hidden; border-radius: 12px;
                    border: 4px solid rgba(255, 255, 255, 0.1);
                    display: flex; flex-direction: column;
                }}
                
                #browser-header {{
                    height: 40px; background: #f0f0f0; border-bottom: 1px solid #ddd;
                    display: flex; align-items: center; padding: 0 15px; gap: 10px; flex-shrink: 0;
                }}
                .browser-dot {{ width: 12px; height: 12px; border-radius: 50%; }}
                .dot-red {{ background: #ff5f56; }}
                .dot-yellow {{ background: #ffbd2e; }}
                .dot-green {{ background: #27c93f; }}
                .browser-bar {{ flex-grow: 1; height: 24px; background: #fff; border-radius: 4px; margin-left: 10px; border: 1px solid #e0e0e0; }}
                
                #content-iframe {{
                    width: {VIRTUAL_W}px;
                    height: {int((CONTAINER_H - 40) / SCALE_FACTOR)}px;
                    border: none; background: #fff;
                    transform: scale({SCALE_FACTOR}); transform-origin: top left; display: block;
                }}
                
                /* FOOTER */
                #footer-group {{
                    margin-bottom: 90px; display: flex; flex-direction: column;
                    align-items: center; gap: 15px; z-index: 10; height: 200px; justify-content: flex-end;
                }}
                 .cta-button {{
                    background: #fff; color: #000; padding: 25px 80px;
                    border-radius: 4px; font-weight: 900; font-size: 45px;
                    text-transform: uppercase; letter-spacing: 2px;
                    box-shadow: 0 10px 40px rgba(255, 255, 255, 0.2);
                    animation: pulse-glow 3s infinite ease-in-out;
                }}
                .cta-subtext {{ font-size: 26px; color: #666; font-weight: 600; letter-spacing: 2px; text-transform: uppercase; }}
                @keyframes pulse-glow {{
                    0% {{ transform: scale(1); }}
                    50% {{ transform: scale(1.02); box-shadow: 0 10px 60px rgba(255, 255, 255, 0.4); }}
                    100% {{ transform: scale(1); }}
                }}
                
                #ai-cursor {{
                    position: absolute; top: 0; left: 0; width: 30px; height: 30px;
                    background: #ffffff; border: 2px solid rgba(0, 0, 0, 0.1);
                    border-radius: 50%; pointer-events: none; z-index: 9999;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
                    transition: transform 0.1s, background 0.2s, opacity 0.3s; opacity: 0;
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
                const c = document.getElementById('ai-cursor');
                let isVisible = false;
                document.addEventListener('mousemove', e => {{
                    if (!isVisible) {{ c.style.opacity = '1'; isVisible = true; }}
                    c.style.left = e.clientX + 'px';
                    c.style.top = e.clientY + 'px';
                }});
            </script>
        </body>
        </html>
        """
        
        await page.set_content(host_html)
        
        iframe_element = await page.query_selector('#content-iframe')
        content_frame = await iframe_element.content_frame()
        
        if not content_frame:
            await page.wait_for_timeout(2000)
            content_frame = await iframe_element.content_frame()
            
        if not content_frame:
            print("Error: Could not access content iframe.")
            return

        try:
            await content_frame.wait_for_load_state("networkidle")
        except:
            await page.wait_for_timeout(2000)
            
        print("Iframe Loaded. Starting Action.")
        
        # Hide Scrollbars
        await content_frame.add_style_tag(content="""
            ::-webkit-scrollbar { display: none; }
            body { -ms-overflow-style: none; scrollbar-width: none; }
        """)

        # Get Wrapper Offset for Mapping
        wrapper_offset = await page.evaluate("""() => {
            const rect = document.getElementById('presentation-window').getBoundingClientRect();
            return { x: rect.left, y: rect.top };
        }""")
        
        # Init Physics
        inputs = VelocityInput(page, content_frame, wrapper_offset, SCALE_FACTOR)
        
        # Start Move
        await page.mouse.move(540, 960)
        
        # --- CHOREOGRAPHY ---
        # Limit total duration to ~45s? We can just run the natural flow now that it's faster.
        await analyze_and_choreograph(page, content_frame, inputs)
                
        # Save
        video = page.video
        await context.close() 
        
        if video:
            saved_video_path = await video.path()
            await browser.close()
            if os.path.exists(output_path):
                 os.remove(output_path)
            import shutil
            shutil.move(saved_video_path, output_path)
            print(f"Video saved to {output_path}")
        else:
            await browser.close()
            print("Error: No video recorded.")

if __name__ == "__main__":
    # Test execution
    run_server_in_thread()
    time.sleep(1)
    
    test_html = os.path.abspath(os.path.join(os.path.dirname(__file__), "../content_pool/business_01/index.html"))
    asyncio.run(record_url(test_html, 30, "test_output.mp4"))
