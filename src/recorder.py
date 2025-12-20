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
        # Faster Duration for Shorts
        duration = 0.3 + (dist / 4000.0) 
        if speed == "fast": duration *= 0.5
        
        await self._bezier_curve(self.mouse_x, self.mouse_y, vx, vy, duration)
        self.mouse_x, self.mouse_y = vx, vy

    async def _bezier_curve(self, sx, sy, ex, ey, duration):
        # PERFORMANCE FIX: Reduce FPS from 60 to 12
        # Reduce IPC overhead
        fps = 12
        steps = int(duration * fps)
        if steps < 1: steps = 1

        offset_strength = random.randint(-50, 50)
        cx = (sx + ex) / 2 + random.randint(-20, 20)
        cy = (sy + ey) / 2 + offset_strength
        
        for i in range(steps + 1):
            t = i / steps
            nt = 1 - t
            bx = (nt**2 * sx) + (2 * nt * t * cx) + (t**2 * ex)
            by = (nt**2 * sy) + (2 * nt * t * cy) + (t**2 * ey)
            await self.page.mouse.move(bx, by)
            # Sleep longer between frames -> less CPU burn
            await asyncio.sleep(duration / steps)

    async def smooth_glide(self, start_y, end_y, duration):
        """
        Smooth linear scroll to cover ground.
        """
        # PERFORMANCE FIX: 10 FPS for Scrolling
        fps = 10 
        steps = int(duration * fps)
        if steps == 0: return

        dist = end_y - start_y
        step_size = dist / steps
        
        current_y = start_y
        
        for i in range(steps):
             current_y += step_size
             await self.frame.evaluate(f"window.scrollTo(0, {current_y})")
             
             # Gentle mouse sway
             # Only update mouse every 2nd frame to save calls
             if i % 2 == 0:
                 sway = math.sin(i * 0.1) * 20
                 await self.page.mouse.move(self.mouse_x + sway, self.mouse_y)
             
             await asyncio.sleep(duration / steps)
        
        await self.frame.evaluate(f"window.scrollTo(0, {end_y})")


async def choreography_script(page, frame, input_sys):
    print(">> AI Director: 30s Full Page Scan...")
    
    # 1. GET KEY METRICS
    total_height = await frame.evaluate("document.body.scrollHeight")
    viewport_h = await frame.evaluate("window.innerHeight")
    max_scroll = total_height - viewport_h
    
    # --- ACT 1: HERO (4s) ---
    print(">> Act 1: Hero")
    
    # Find Hero element
    hero_center = await frame.evaluate("""() => {
        const h = document.querySelector('section, header');
        const r = h.getBoundingClientRect();
        return {x: r.left + r.width/2, y: r.top + r.height/2};
    }""")
    
    # Move to center
    await input_sys.human_move(hero_center['x'], hero_center['y'], speed="slow")
    await asyncio.sleep(0.5)
    
    # Interaction: Circle?
    cx, cy = input_sys.mouse_x, input_sys.mouse_y
    # Reduced circle steps
    for i in range(10):
        a = i * 0.6
        r = 30
        await page.mouse.move(cx + math.cos(a)*r, cy + math.sin(a)*r)
        await asyncio.sleep(0.05) # 50ms wait
        
    await asyncio.sleep(0.5)
    
    # --- ACT 2: THE GLIDE (20s) ---
    print(">> Act 2: Full Page Glide")
    
    start_y = 0
    # Find 'Projects' Y
    projects_y = await frame.evaluate("""() => {
        const el = document.getElementById('projects') || document.querySelector('.projects');
        return el ? el.offsetTop : null;
    }""")
    
    if projects_y:
        # Split Glide: Hero -> Projects -> End
        dist1 = projects_y - start_y
        time1 = 6.0 
        
        await input_sys.smooth_glide(start_y, projects_y, duration=time1)
        start_y = projects_y
        
        # Pause at Projects (1.5s)
        print("   > Pausing at Projects")
        await input_sys.human_move(500, 800, speed="fast")
        await asyncio.sleep(1.0)
        
        # Segment 2: Projects -> End
        dist2 = max_scroll - projects_y
        time2 = 12.0 
        await input_sys.smooth_glide(start_y, max_scroll, duration=time2)
        
    else:
        # No specific middle target, just Glide all way (18s)
        await input_sys.smooth_glide(0, max_scroll, duration=18.0)
    
    # --- ACT 3: FOOTER (End) ---
    print(">> Act 3: Footer/Contact")
    
    # Ensure we are fully at bottom
    await frame.evaluate(f"window.scrollTo(0, {total_height})")
    
    # Find CTA Button
    cta_pos = await frame.evaluate("""() => {
        const b = document.querySelector('.submit-btn, button[type="submit"], .footer-link');
        if(!b) return null;
        const r = b.getBoundingClientRect();
        return {x: r.left + r.width/2, y: r.top + r.height/2};
    }""")
    
    if cta_pos:
        # Move to CTA
        await input_sys.human_move(cta_pos['x'], cta_pos['y'], speed="normal")
        # Hover/Wiggle
        await asyncio.sleep(0.5)
        
    await asyncio.sleep(2.0) # Final freeze frame


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
        
        # Hide Scrollbars
        await content_frame.add_style_tag(content="::-webkit-scrollbar { display: none; } body { -ms-overflow-style: none; scrollbar-width: none; }")

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
        # PERFORMANCE FIX: GLOBAL TIMEOUT
        # We enforce a hard 32s limit on the choreography.
        # This prevents loop lag from dragging it to 3 minutes.
        try:
            await asyncio.wait_for(choreography_script(page, content_frame, inputs), timeout=32.0)
        except asyncio.TimeoutError:
            print("(!) TIMEOUT: Forced video end at 32s safety limit.")
                
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
