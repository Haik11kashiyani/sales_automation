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
SERVER_PORT = 0 # Will be assigned dynamically
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
        # Use Port 0 to let OS assign a free port
        with ReusableTCPServer(("", 0), QuietHandler) as httpd:
            SERVER_PORT = httpd.server_address[1]
            print(f"Serving at port {SERVER_PORT}")
            SERVER_READY.set()
            httpd.serve_forever()
    except Exception as e:
        print(f"Server Error: {e}")
        SERVER_READY.set() # Unblock main thread even on error

def run_server_in_thread():
    t = threading.Thread(target=start_server)
    t.daemon = True
    t.start()
    return t

# --- HUMAN ATTENTION ENGINE ---

class AttentionInput:
    """
    Simulates a human eye-hand coordination system with attention 'gravity'.
    """
    def __init__(self, page, frame, wrapper_offset, scale_factor):
        self.page = page
        self.frame = frame
        self.wrapper_offset = wrapper_offset
        self.scale_factor = scale_factor
        
        self.mouse_x = 540
        self.mouse_y = 960
        self.scroll_y = 0
        self.scroll_velocity = 0
        
        self.FPS = 30
        self.DT = 1.0 / self.FPS
        
        self.targets = []
        self.current_focus = None
        self.focus_start_time = 0

    def frame_to_viewport(self, fx, fy):
        vx = self.wrapper_offset['x'] + (fx * self.scale_factor)
        vy = self.wrapper_offset['y'] + (fy * self.scale_factor)
        return vx, vy

    async def update_physics(self):
        self.scroll_y += self.scroll_velocity
        await self.frame.evaluate(f"window.scrollTo(0, {self.scroll_y})")
        
        attention_pull = (0, 0)
        drag_factor = 1.0
        
        best_target = None
        min_dist = 9999
        
        for t in self.targets:
            tfy = t['y'] - self.scroll_y
            tfx = t['x']
            tvx, tvy = self.frame_to_viewport(tfx, tfy)
            if 100 < tvy < 1400: # Visible zone
                dist = math.hypot(tvx - self.mouse_x, tvy - self.mouse_y)
                if dist < min_dist:
                    min_dist = dist
                    best_target = (tvx, tvy, t)

        if best_target:
            tvx, tvy, t_data = best_target
            if min_dist < 400 and random.random() < 0.1:
                if self.current_focus != t_data:
                    self.current_focus = t_data
                    self.focus_start_time = time.time()
        
        if self.current_focus:
            focus_duration = time.time() - self.focus_start_time
            tvx, tvy = self.frame_to_viewport(self.current_focus['x'], self.current_focus['y'] - self.scroll_y)
            
            if focus_duration < 0.6:
                dx = tvx - self.mouse_x
                dy = tvy - self.mouse_y
                self.mouse_x += dx * 0.1 
                self.mouse_y += dy * 0.1
                drag_factor = 0.90 
            elif focus_duration < 1.5:
                self.mouse_x = tvx + math.sin(focus_duration * 10) * 5
                self.mouse_y = tvy + math.cos(focus_duration * 8) * 5
                drag_factor = 0.5
            else:
                self.current_focus = None
        else:
            self.mouse_x += random.uniform(-1, 1)
            self.mouse_y += math.sin(time.time()) * 0.5

        self.scroll_velocity *= drag_factor
        await self.page.mouse.move(self.mouse_x, self.mouse_y)


    async def fluid_glide(self, start_y, end_y, max_duration):
        self.scroll_y = start_y
        start_time = time.time()
        dist = end_y - start_y
        base_velocity = dist / (max_duration * 30)
        self.scroll_velocity = base_velocity
        
        while True:
            elapsed = time.time() - start_time
            if elapsed > max_duration: break
            if self.scroll_y >= end_y - 10: break
            
            if self.current_focus is None:
                if self.scroll_velocity < base_velocity:
                    self.scroll_velocity += 0.5
                elif self.scroll_velocity > base_velocity:
                    self.scroll_velocity -= 0.1
            
            await self.update_physics()
            await asyncio.sleep(self.DT)
        
        await self.frame.evaluate(f"window.scrollTo(0, {end_y})")


async def choreography_script(page, frame, input_sys):
    print(">> AI Director: Human Attention Scan...")
    
    targets = await frame.evaluate("""() => {
        const candidates = document.querySelectorAll('button, a.btn, .card, .project-item, img, h2');
        const results = [];
        candidates.forEach(el => {
            const r = el.getBoundingClientRect();
            if(r.height < 50 || r.width < 50) return; 
            results.push({
                tag: el.tagName,
                x: r.left + r.width/2,
                y: r.top + window.scrollY + r.height/2 // Abs Y
            });
        });
        return results.sort((a,b) => a.y - b.y);
    }""")
    
    filtered = []
    last_y = -999
    for t in targets:
        if t['y'] - last_y > 400: 
            filtered.append(t)
            last_y = t['y']
            
    input_sys.targets = filtered
    print(f">> Identified {len(filtered)} Attention Magnets.")
    
    total_height = await frame.evaluate("document.body.scrollHeight")
    viewport_h = await frame.evaluate("window.innerHeight")
    max_scroll = total_height - viewport_h
    
    print(">> Act 1: Hero")
    input_sys.scroll_y = 0
    await input_sys.page.mouse.move(540, 500)
    for i in range(60): 
        await input_sys.update_physics()
        await asyncio.sleep(input_sys.DT)
        
    print(">> Act 2: Fluid Glide")
    await input_sys.fluid_glide(0, max_scroll, max_duration=45.0)

    print(">> Act 3: Footer Check")
    for i in range(90): 
        await input_sys.update_physics()
        await asyncio.sleep(input_sys.DT)


async def record_url(file_path: str, duration: float, output_path: str, overlay_text: str = "", overlay_header: str = "", cta_text: str = "", cta_subtext: str = ""):
    rel_path = os.path.relpath(file_path, SERVER_ROOT)
    # Use Global SERVER_PORT
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
        
        inputs = AttentionInput(page, content_frame, wrapper_offset, SCALE_FACTOR)
        await page.mouse.move(540, 960)
        
        try:
            await asyncio.wait_for(choreography_script(page, content_frame, inputs), timeout=65.0)
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

if __name__ == "__main__":
    t = run_server_in_thread()
    # Wait for server to be ready with port
    if SERVER_READY.wait(timeout=5):
        time.sleep(1) # Extra buffer
        test_html = os.path.abspath(os.path.join(os.path.dirname(__file__), "../content_pool/business_01/index.html"))
        asyncio.run(record_url(test_html, 55, "test_output.mp4"))
    else:
        print("Server Failed to start!")
