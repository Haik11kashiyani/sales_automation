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
SERVER_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../")) 
SERVER_PORT = 0
SERVER_READY = threading.Event()

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

def start_server():
    global SERVER_PORT
    try:
        os.chdir(SERVER_ROOT)
        with ReusableTCPServer(("", 0), QuietHandler) as httpd:
            SERVER_PORT = httpd.server_address[1]
            print(f"Serving at port {SERVER_PORT}")
            SERVER_READY.set()
            httpd.serve_forever()
    except Exception as e:
        print(f"Server Error: {e}")
        SERVER_READY.set()

def run_server_in_thread():
    t = threading.Thread(target=start_server)
    t.daemon = True
    t.start()
    return t

# --- REFINED HUMAN SCROLLING ENGINE ---

def ease_in_out_cubic(t):
    """Gentler easing curve for slower, more natural scrolling."""
    if t < 0.5:
        return 4 * t * t * t
    return 1 - pow(-2 * t + 2, 3) / 2

class HumanScroller:
    """
    Simulates natural, human-like scrolling with organic mouse movements.
    Key improvements:
    - Uses easing curves instead of linear velocity
    - Implements continuous flow with subtle speed variations
    - Never truly "stops" - always has micro-movement
    """
    def __init__(self, page, frame, wrapper_offset, scale_factor):
        self.page = page
        self.frame = frame
        self.wrapper_offset = wrapper_offset
        self.scale_factor = scale_factor
        
        # State
        self.mouse_x = 540
        self.mouse_y = 800
        self.scroll_y = 0
        
        # Timing
        self.FPS = 30
        self.DT = 1.0 / self.FPS
        
        # Organic variation seeds
        self.time_offset = random.random() * 1000

    def frame_to_viewport(self, fx, fy):
        vx = self.wrapper_offset['x'] + (fx * self.scale_factor)
        vy = self.wrapper_offset['y'] + (fy * self.scale_factor)
        return vx, vy

    async def organic_mouse_update(self, elapsed):
        """
        Creates natural, flowing mouse movement.
        Uses layered sine waves for organic sway.
        """
        # Primary sway
        sway_x = math.sin(elapsed * 0.3 + self.time_offset) * 15
        sway_y = math.sin(elapsed * 0.5 + self.time_offset * 0.7) * 10
        
        # Secondary micro-jitter (subtle)
        jitter_x = random.gauss(0, 0.5)
        jitter_y = random.gauss(0, 0.5)
        
        # Apply
        self.mouse_x = 540 + sway_x + jitter_x
        self.mouse_y = 800 + sway_y + jitter_y
        
        await self.page.mouse.move(self.mouse_x, self.mouse_y)

    async def smooth_scroll_to(self, target_y, duration):
        """
        Scrolls to target_y over 'duration' seconds with ease-in-out.
        Never truly stops - maintains a flowing, natural rhythm.
        """
        start_y = self.scroll_y
        start_time = time.time()
        distance = target_y - start_y
        
        while True:
            elapsed = time.time() - start_time
            if elapsed >= duration:
                break
            
            # Eased progress
            t = elapsed / duration
            eased_t = ease_in_out_cubic(t)
            
            # Current scroll position
            self.scroll_y = start_y + distance * eased_t
            
            # Apply scroll
            await self.frame.evaluate(f"window.scrollTo(0, {self.scroll_y})")
            
            # Organic mouse movement
            await self.organic_mouse_update(elapsed)
            
            await asyncio.sleep(self.DT)
        
        # Final snap
        self.scroll_y = target_y
        await self.frame.evaluate(f"window.scrollTo(0, {target_y})")

    async def glide_with_pauses(self, max_scroll, total_duration, pause_points=[]):
        """
        Main scrolling choreography:
        - Smoothly scrolls from 0 to max_scroll
        - Pauses briefly at specified Y coordinates (pause_points)
        - Each pause includes natural "reading" behavior
        """
        start_time = time.time()
        current_y = 0
        
        # Sort and filter pause points
        pause_points = sorted([p for p in pause_points if 0 < p < max_scroll])
        pause_points.append(max_scroll) # Always end at bottom
        
        # Calculate time per segment
        num_segments = len(pause_points)
        scroll_time_per_segment = (total_duration * 0.85) / num_segments # 85% scrolling (slower)
        pause_time_per_point = (total_duration * 0.15) / max(1, num_segments - 1) # 15% pausing
        
        for i, target_y in enumerate(pause_points):
            print(f"   > Scrolling to Y={int(target_y)}...")
            
            # Scroll to target
            await self.smooth_scroll_to(target_y, scroll_time_per_segment)
            
            # Pause and "read" (except at the very end)
            if i < len(pause_points) - 1 and pause_time_per_point > 0.5:
                print(f"   > Reading at Y={int(target_y)}...")
                await self.reading_behavior(pause_time_per_point)
            
            current_y = target_y
    
    async def reading_behavior(self, duration):
        """
        Simulates a human pausing to read/look at content.
        - Finds interactive elements in viewport and hovers over them
        - Triggers micro-interactions (hover effects)
        """
        start_time = time.time()
        
        # Find interactive elements currently visible in viewport
        visible_elements = await self.frame.evaluate("""() => {
            const elements = document.querySelectorAll('button, a, .card, .project-item, img, h2, h3');
            const results = [];
            elements.forEach(el => {
                const r = el.getBoundingClientRect();
                // Check if in viewport (visible area)
                if(r.top > 50 && r.top < 800 && r.width > 50 && r.height > 30) {
                    results.push({
                        x: r.left + r.width/2,
                        y: r.top + r.height/2,
                        tag: el.tagName
                    });
                }
            });
            return results.slice(0, 3); // Max 3 elements
        }""")
        
        # Hover over each element briefly
        for el in visible_elements:
            if time.time() - start_time >= duration:
                break
                
            # Move to element
            vx, vy = self.frame_to_viewport(el['x'], el['y'])
            
            # Smooth approach
            steps = 15
            start_x, start_y = self.mouse_x, self.mouse_y
            for i in range(steps):
                t = (i + 1) / steps
                eased_t = ease_in_out_cubic(t)
                self.mouse_x = start_x + (vx - start_x) * eased_t
                self.mouse_y = start_y + (vy - start_y) * eased_t
                await self.page.mouse.move(self.mouse_x, self.mouse_y)
                await asyncio.sleep(self.DT)
            
            # Hover wiggle (triggers micro-interaction)
            for _ in range(8):
                wiggle_x = vx + random.uniform(-5, 5)
                wiggle_y = vy + random.uniform(-3, 3)
                await self.page.mouse.move(wiggle_x, wiggle_y)
                await asyncio.sleep(0.05)
            
            # Brief pause to let animation play
            await asyncio.sleep(0.3)
        
        # Fill remaining time with gentle drift
        while time.time() - start_time < duration:
            elapsed = time.time() - start_time
            drift_x = math.sin(elapsed * 0.8) * 30
            drift_y = math.sin(elapsed * 0.5) * 20
            await self.page.mouse.move(540 + drift_x, 800 + drift_y)
            await asyncio.sleep(self.DT)


async def choreography_script(page, frame, scroller):
    print(">> Refined Human Scrolling...")
    
    # Get page dimensions
    total_height = await frame.evaluate("document.body.scrollHeight")
    viewport_h = await frame.evaluate("window.innerHeight")
    max_scroll = max(0, total_height - viewport_h)
    
    # Find interesting pause points (sections, headings)
    pause_points = await frame.evaluate("""() => {
        const points = [];
        const sections = document.querySelectorAll('section, .section, h2, .project-item');
        sections.forEach(el => {
            const rect = el.getBoundingClientRect();
            const absY = rect.top + window.scrollY;
            if(absY > 500) points.push(absY - 200); // Stop 200px before so it's visible
        });
        return points;
    }""")
    
    # Limit pause points to 3-4 max for good pacing
    if len(pause_points) > 4:
        step = len(pause_points) // 4
        pause_points = [pause_points[i] for i in range(0, len(pause_points), step)][:4]
    
    print(f">> Found {len(pause_points)} sections to highlight.")
    
    # --- ACT 1: HERO (Initial view, 5s) ---
    print(">> Act 1: Hero")
    await scroller.reading_behavior(4.0)
    
    # --- ACT 2: MAIN GLIDE (45s) ---
    print(">> Act 2: Glide")
    await scroller.glide_with_pauses(max_scroll, total_duration=42.0, pause_points=pause_points)
    
    # --- ACT 3: FOOTER (5s) ---
    print(">> Act 3: Footer")
    await scroller.reading_behavior(4.0)


async def record_url(file_path: str, duration: float, output_path: str, overlay_text: str = "", overlay_header: str = "", cta_text: str = "", cta_subtext: str = ""):
    rel_path = os.path.relpath(file_path, SERVER_ROOT)
    target_url = f"http://localhost:{SERVER_PORT}/{rel_path.replace(os.sep, '/')}"
    print(f"Recording URL: {target_url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--enable-features=OverlayScrollbar', '--no-sandbox', '--disable-web-security']
        )
        context = await browser.new_context(
            viewport={"width": 1080, "height": 1920},
            device_scale_factor=1.0,
            record_video_dir=os.path.dirname(output_path),
            record_video_size={"width": 1080, "height": 1920}
        )
        page = await context.new_page()
        
        VIRTUAL_W, CONTAINER_H, CONTAINER_W = 1024, 1550, 1000
        SCALE_FACTOR = CONTAINER_W / VIRTUAL_W
        header_txt = overlay_header.upper() or "WEB DESIGN AWARDS"
        title_txt = overlay_text.upper() or "FUTURE OF WEB"
        cta_txt = cta_text.upper() or "VISIT WEBSITE"
        sub_txt = cta_subtext.upper() or "LINK IN BIO"

        host_html = f"""
        <!DOCTYPE html><html><head><style>
            body {{ margin:0; width:1080px; height:1920px; background:linear-gradient(-45deg, #1a1a2e, #16213e, #4a1c40, #1a1a2e); background-size:400% 400%; animation:g 15s ease infinite; color:white; font-family:sans-serif; overflow:hidden; display:flex; flex-direction:column; align-items:center; justify-content:space-between; padding-bottom:40px; }}
            @keyframes g {{ 0%{{background-position:0% 50%}} 50%{{background-position:100% 50%}} 100%{{background-position:0% 50%}} }}
            #header-group {{ margin-top:50px; display:flex; flex-direction:column; align-items:center; z-index:10; height:140px; }}
            #p-header {{ font-size:30px; font-weight:700; letter-spacing:4px; color:#888; text-transform:uppercase; }}
            #p-title {{ font-size:50px; font-weight:900; text-align:center; background:linear-gradient(135deg, #fff 0%, #aaa 100%); -webkit-background-clip:text; -webkit-text-fill-color:transparent; margin-top:10px; }}
            #presentation-window {{ position:relative; width:{CONTAINER_W}px; height:{CONTAINER_H}px; background:#fff; border-radius:12px; border:4px solid rgba(255,255,255,0.1); display:flex; flex-direction:column; overflow:hidden; box-shadow:0 30px 80px rgba(0,0,0,0.7); }}
            #browser-header {{ height:40px; background:#f0f0f0; border-bottom:1px solid #ddd; display:flex; align-items:center; padding:0 15px; gap:10px; }}
            .browser-dot {{ width:12px; height:12px; border-radius:50%; }} .dot-red{{background:#ff5f56}} .dot-yellow{{background:#ffbd2e}} .dot-green{{background:#27c93f}}
            .browser-bar {{ flex-grow:1; height:24px; background:#fff; border-radius:4px; margin-left:10px; border:1px solid #e0e0e0; }}
            #content-iframe {{ width:{VIRTUAL_W}px; height:{int((CONTAINER_H-40)/SCALE_FACTOR)}px; border:none; background:#fff; transform:scale({SCALE_FACTOR}); transform-origin:top left; display:block; }}
            #footer-group {{ margin-bottom:90px; display:flex; flex-direction:column; align-items:center; gap:15px; z-index:10; height:200px; justify-content:flex-end; }}
            .cta-button {{ background:#fff; color:#000; padding:25px 80px; border-radius:4px; font-weight:900; font-size:45px; letter-spacing:2px; box-shadow:0 10px 40px rgba(255,255,255,0.2); animation:p 3s infinite ease-in-out; }}
            .cta-subtext {{ font-size:26px; color:#666; font-weight:600; letter-spacing:2px; text-transform:uppercase; }}
            @keyframes p {{ 0%{{transform:scale(1)}} 50%{{transform:scale(1.02);box-shadow:0 10px 60px rgba(255,255,255,0.4)}} 100%{{transform:scale(1)}} }}
            #ai-cursor {{ position:absolute; width:30px; height:30px; background:#fff; border:2px solid rgba(0,0,0,0.1); border-radius:50%; pointer-events:none; z-index:9999; box-shadow:0 4px 20px rgba(0,0,0,0.4); opacity:0; transition:opacity 0.3s; }}
        </style></head>
        <body>
            <div id="header-group"><div id="p-header">{header_txt}</div><div id="p-title">{title_txt}</div></div>
            <div id="presentation-window"><div id="browser-header"><div class="browser-dot dot-red"></div><div class="browser-dot dot-yellow"></div><div class="browser-dot dot-green"></div><div class="browser-bar"></div></div><iframe id="content-iframe" src="{target_url}" scrolling="yes"></iframe></div>
            <div id="footer-group"><div class="cta-button">{cta_txt}</div><div class="cta-subtext">{sub_txt}</div></div>
            <div id="ai-cursor"></div>
            <script>const c=document.getElementById('ai-cursor');let v=false;document.addEventListener('mousemove',e=>{{if(!v){{c.style.opacity='1';v=true}}c.style.left=e.clientX+'px';c.style.top=e.clientY+'px'}})</script>
        </body></html>
        """
        await page.set_content(host_html)
        
        iframe_element = await page.query_selector('#content-iframe')
        content_frame = await iframe_element.content_frame()
        if not content_frame: await page.wait_for_timeout(2000); content_frame = await iframe_element.content_frame()
        if not content_frame: return
        try: await content_frame.wait_for_load_state("networkidle")
        except: await page.wait_for_timeout(2000)
        
        await content_frame.add_style_tag(content="::-webkit-scrollbar { display: none; } body { -ms-overflow-style: none; scrollbar-width: none; }")
        wrapper_offset = await page.evaluate("() => { const r = document.getElementById('presentation-window').getBoundingClientRect(); return {x:r.left, y:r.top}; }")
        
        scroller = HumanScroller(page, content_frame, wrapper_offset, SCALE_FACTOR)
        await page.mouse.move(540, 960)
        
        try:
            await asyncio.wait_for(choreography_script(page, content_frame, scroller), timeout=60.0)
        except asyncio.TimeoutError:
            print("(!) Video Limit Reached.")
            
        video = page.video
        await context.close()
        if video:
            saved = await video.path()
            await browser.close()
            if os.path.exists(output_path): os.remove(output_path)
            import shutil
            shutil.move(saved, output_path)
            print(f"Video saved to {output_path}")

if __name__ == "__main__":
    t = run_server_in_thread()
    if SERVER_READY.wait(timeout=5):
        time.sleep(1)
        test_html = os.path.abspath(os.path.join(os.path.dirname(__file__), "../content_pool/business_01/index.html"))
        asyncio.run(record_url(test_html, 55, "test_output.mp4"))
    else:
        print("Server Failed to start!")
