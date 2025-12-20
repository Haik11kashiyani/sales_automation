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
    Simulates physical input devices with momentum.
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
        vx, vy = self.frame_to_viewport(target_fx, target_fy)
        dist = math.hypot(vx - self.mouse_x, vy - self.mouse_y)
        duration = 0.5 + (dist / 3000.0) 
        if speed == "fast": duration *= 0.6
        
        await self._bezier_curve(self.mouse_x, self.mouse_y, vx, vy, duration)
        self.mouse_x, self.mouse_y = vx, vy

    async def _bezier_curve(self, sx, sy, ex, ey, duration):
        start_time = time.time()
        
        offset_strength = random.randint(-40, 40)
        cx = (sx + ex) / 2 + random.randint(-15, 15)
        cy = (sy + ey) / 2 + offset_strength
        
        while True:
            elapsed = time.time() - start_time
            if elapsed >= duration: break
            
            t = elapsed / duration
            nt = 1 - t
            bx = (nt**2 * sx) + (2 * nt * t * cx) + (t**2 * ex)
            by = (nt**2 * sy) + (2 * nt * t * cy) + (t**2 * ey)
            
            await self.page.mouse.move(bx, by)
            # SMOOTH 30 FPS
            await asyncio.sleep(0.033) 

    async def interactive_glide(self, start_y, end_y, nominal_duration, interactables=[]):
        """
        Scrolls from start_y to end_y.
        If an 'interactable' comes into view, we PAUSE scroll, interact, then RESUME.
        The 'nominal_duration' is the time spent scrolling (excluding pauses).
        """
        start_time = time.time()
        paused_duration = 0
        
        # Sort targets by Y position
        pending_targets = sorted(interactables, key=lambda i: i['y'])
        
        # To avoid getting stuck, we remove targets effectively passed
        
        while True:
            now = time.time()
            # Net elapsed time spent actually scrolling
            scroll_elapsed = (now - start_time) - paused_duration
            
            if scroll_elapsed >= nominal_duration:
                break
            
            progress = scroll_elapsed / nominal_duration
            current_y = start_y + (end_y - start_y) * progress
            
            await self.frame.evaluate(f"window.scrollTo(0, {current_y})")
            
            # --- INTERACTION CHECK ---
            # Check if any target is roughly in the "Golden Zone" (middle of screen)
            # Viewport center in Doc coords = current_y + 960/2 (approx 480) ?? 
            # Viewport height is ~900 in frame units? Let's check window innerHeight
            
            # Simple heuristic: If we are close to target Y - 500
            
            if pending_targets:
                next_t = pending_targets[0]
                # Target Y is absolute document Y.
                # If target is within [current_y + 200, current_y + 600] (visible area)
                
                # We trigger interaction when it's comfortably in view
                trigger_y = next_t['y'] - 500 
                
                if current_y > trigger_y:
                    # TIME TO INTERACT!
                    print(f"   > Spotted Interest: {next_t['tag']}")
                    
                    # 1. Pause Clock
                    pause_start = time.time()
                    
                    # 2. Move & Hover
                    # Convert absolute doc Y to local frame relative Y for mouse
                    # Frame Y = Doc Y - current_y
                    frame_target_y = next_t['y'] - current_y
                    frame_target_x = next_t['x']
                    
                    # Only move if it's actually on screen
                    if 0 < frame_target_y < 1500: # Safety bounds
                        await self.human_move(frame_target_x, frame_target_y, speed="normal")
                        
                        # HOVER EFFECT (Wiggle)
                        await asyncio.sleep(0.2)
                        await self.human_move(frame_target_x + 20, frame_target_y + 10, speed="slow", overshoot=False)
                        await asyncio.sleep(0.4)
                        
                        # Move away slightly to un-hover? Or just leave it.
                        
                    # 3. Resume
                    paused_duration += (time.time() - pause_start)
                    pending_targets.pop(0) # Done with this one
            
            # --- END INTERACTION CHECK ---
            
            # Mouse Sway
            if random.random() < 0.2:
                 sway = math.sin(scroll_elapsed * 1.5) * 15
                 await self.page.mouse.move(self.mouse_x + sway, self.mouse_y)
            
            await asyncio.sleep(0.033)
        
        await self.frame.evaluate(f"window.scrollTo(0, {end_y})")


async def choreography_script(page, frame, input_sys):
    print(">> AI Director: 55s Interactive Exploration...")
    
    # 1. SCAN FOR INTERACTABLES
    # We look for "Juicy" elements: Buttons, Cards, Images
    interactables = await frame.evaluate("""() => {
        const candidates = document.querySelectorAll('button, a.btn, .card, .project-item, img, h2');
        const results = [];
        candidates.forEach(el => {
            const r = el.getBoundingClientRect();
            if(r.height < 50 || r.width < 50) return; // Skip tiny icons
            
            results.push({
                tag: el.tagName,
                x: r.left + r.width/2,
                y: r.top + window.scrollY + r.height/2 // Abs Y
            });
        });
        // Sort by Y
        return results.sort((a,b) => a.y - b.y);
    }""")
    
    # Filter: Limit to max 4 interactions to avoid stopping every 2 seconds
    # We pick them spaced out
    final_interactables = []
    if interactables:
        step = max(1, len(interactables) // 4)
        for i in range(0, len(interactables), step):
            if len(final_interactables) < 4:
                final_interactables.append(interactables[i])
    
    print(f">> Identified {len(final_interactables)} Interactive Targets.")
    
    total_height = await frame.evaluate("document.body.scrollHeight")
    viewport_h = await frame.evaluate("window.innerHeight")
    max_scroll = total_height - viewport_h
    
    # --- ACT 1: HERO (5s) ---
    print(">> Act 1: Hero")
    hero_center = await frame.evaluate("""() => {
        const h = document.querySelector('section, header');
        const r = h.getBoundingClientRect();
        return {x: r.left + r.width/2, y: r.top + r.height/2};
    }""")
    await input_sys.human_move(hero_center['x'], hero_center['y'], speed="slow")
    await asyncio.sleep(1.0)
    
    cx, cy = input_sys.mouse_x, input_sys.mouse_y
    for i in range(20):
        a = i * 0.4
        r = 30
        await page.mouse.move(cx + math.cos(a)*r, cy + math.sin(a)*r)
        await asyncio.sleep(0.033)
    await asyncio.sleep(0.5)
    
    # --- ACT 2: INTERACTIVE GLIDE (45s base) ---
    print(">> Act 2: Interactive Glide")
    
    # The glide will take ~35s-40s of SCROLL time, plus pauses.
    # We use 'interactive_glide' to handle the pauses.
    
    await input_sys.interactive_glide(0, max_scroll, nominal_duration=40.0, interactables=final_interactables)

    # --- ACT 3: FOOTER (5s) ---
    print(">> Act 3: Footer/Contact")
    await frame.evaluate(f"window.scrollTo(0, {total_height})")
    
    cta_pos = await frame.evaluate("""() => {
        const b = document.querySelector('.submit-btn, button[type="submit"], .footer-link');
        if(!b) return null;
        const r = b.getBoundingClientRect();
        return {x: r.left + r.width/2, y: r.top + r.height/2};
    }""")
    
    if cta_pos:
        await input_sys.human_move(cta_pos['x'], cta_pos['y'], speed="normal")
        await asyncio.sleep(1.0)
        
    await asyncio.sleep(3.0) 


async def record_url(file_path: str, duration: float, output_path: str, overlay_text: str = "", overlay_header: str = "", cta_text: str = "", cta_subtext: str = ""):
    """
    Records a webpage interaction via localhost.
    """
    rel_path = os.path.relpath(file_path, SERVER_ROOT)
    target_url = f"http://localhost:{PORT}/{rel_path.replace(os.sep, '/')}"
    
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
        
        # --- UI CONSTANTS ---
        VIRTUAL_W = 1024 
        CONTAINER_H = 1550 
        CONTAINER_W = 1000
        SCALE_FACTOR = CONTAINER_W / VIRTUAL_W

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
                @keyframes gradientBG {{ 0% {{ background-position: 0% 50%; }} 50% {{ background-position: 100% 50%; }} 100% {{ background-position: 0% 50%; }} }}
                #header-group {{ margin-top: 50px; display: flex; flex-direction: column; align-items: center; z-index: 10; height: 140px; flex-shrink: 0; }}
                #p-header {{ font-size: 30px; font-weight: 700; letter-spacing: 4px; color: #888; text-transform: uppercase; }}
                #p-title {{ font-size: 50px; font-weight: 900; text-align: center; background: linear-gradient(135deg, #fff 0%, #aaa 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-top: 10px; line-height: 1.1; max-width: 900px; }}
                #presentation-window {{ position: relative; width: {CONTAINER_W}px; height: {CONTAINER_H}px; background: #fff; box-shadow: 0 0 0 1px rgba(0,0,0, 0.8), 0 30px 80px rgba(0,0,0, 0.7), 0 0 150px rgba(0,0,0, 0.9); overflow: hidden; border-radius: 12px; border: 4px solid rgba(255, 255, 255, 0.1); display: flex; flex-direction: column; }}
                #browser-header {{ height: 40px; background: #f0f0f0; border-bottom: 1px solid #ddd; display: flex; align-items: center; padding: 0 15px; gap: 10px; flex-shrink: 0; }}
                .browser-dot {{ width: 12px; height: 12px; border-radius: 50%; }}
                .dot-red {{ background: #ff5f56; }} .dot-yellow {{ background: #ffbd2e; }} .dot-green {{ background: #27c93f; }}
                .browser-bar {{ flex-grow: 1; height: 24px; background: #fff; border-radius: 4px; margin-left: 10px; border: 1px solid #e0e0e0; }}
                #content-iframe {{ width: {VIRTUAL_W}px; height: {int((CONTAINER_H - 40) / SCALE_FACTOR)}px; border: none; background: #fff; transform: scale({SCALE_FACTOR}); transform-origin: top left; display: block; }}
                #footer-group {{ margin-bottom: 90px; display: flex; flex-direction: column; align-items: center; gap: 15px; z-index: 10; height: 200px; justify-content: flex-end; }}
                .cta-button {{ background: #fff; color: #000; padding: 25px 80px; border-radius: 4px; font-weight: 900; font-size: 45px; text-transform: uppercase; letter-spacing: 2px; box-shadow: 0 10px 40px rgba(255, 255, 255, 0.2); animation: pulse-glow 3s infinite ease-in-out; }}
                .cta-subtext {{ font-size: 26px; color: #666; font-weight: 600; letter-spacing: 2px; text-transform: uppercase; }}
                @keyframes pulse-glow {{ 0% {{ transform: scale(1); }} 50% {{ transform: scale(1.02); box-shadow: 0 10px 60px rgba(255, 255, 255, 0.4); }} 100% {{ transform: scale(1); }} }}
                #ai-cursor {{ position: absolute; top: 0; left: 0; width: 30px; height: 30px; background: #ffffff; border: 2px solid rgba(0, 0, 0, 0.1); border-radius: 50%; pointer-events: none; z-index: 9999; box-shadow: 0 4px 20px rgba(0,0,0,0.4); transition: transform 0.1s, background 0.2s, opacity 0.3s; opacity: 0; }}
            </style>
        </head>
        <body>
            <div id="header-group"><div id="p-header">{header_txt}</div><div id="p-title">{title_txt}</div></div>
            <div id="presentation-window"><div id="browser-header"><div class="browser-dot dot-red"></div><div class="browser-dot dot-yellow"></div><div class="browser-dot dot-green"></div><div class="browser-bar"></div></div><iframe id="content-iframe" src="{target_url}" scrolling="yes"></iframe></div>
            <div id="footer-group"><div class="cta-button">{cta_txt}</div><div class="cta-subtext">{sub_txt}</div></div>
            <div id="ai-cursor"></div>
            <script>
                const c = document.getElementById('ai-cursor'); let isVisible = false;
                document.addEventListener('mousemove', e => {{ if(!isVisible){{c.style.opacity='1';isVisible=true;}} c.style.left=e.clientX+'px'; c.style.top=e.clientY+'px'; }});
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
            
        if not content_frame: return

        try:
            await content_frame.wait_for_load_state("networkidle")
        except:
            await page.wait_for_timeout(2000)
            
        print("Iframe Loaded. Starting Action.")
        
        await content_frame.add_style_tag(content="::-webkit-scrollbar { display: none; } body { -ms-overflow-style: none; scrollbar-width: none; }")

        wrapper_offset = await page.evaluate("""() => {
            const rect = document.getElementById('presentation-window').getBoundingClientRect();
            return { x: rect.left, y: rect.top };
        }""")
        
        inputs = VelocityInput(page, content_frame, wrapper_offset, SCALE_FACTOR)
        await page.mouse.move(540, 960)
        
        # --- CHOREOGRAPHY ---
        # TIMEOUT: 70s Hard Limit (Buffer for 55s logic)
        try:
            await asyncio.wait_for(choreography_script(page, content_frame, inputs), timeout=70.0)
        except asyncio.TimeoutError:
            print("(!) TIMEOUT: Safety limit hit.")
                
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
    run_server_in_thread()
    time.sleep(1)
    test_html = os.path.abspath(os.path.join(os.path.dirname(__file__), "../content_pool/business_01/index.html"))
    asyncio.run(record_url(test_html, 55, "test_output.mp4"))
