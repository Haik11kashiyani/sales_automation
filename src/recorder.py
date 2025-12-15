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

async def record_url(file_path: str, duration: float, output_path: str, overlay_text: str = "", overlay_header: str = ""):
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
        # --- PRESENTATION MODE: MOCKUP WRAPPER ---
        # Instead of scaling the body, we Wrap the existing content in a Phone Mockup.
        
        # 1. Inject Styles for the Wrapper
        await page.add_style_tag(content="""
            /* Hide the original body scrollbar first, we will scroll the inner frame */
            html, body {
                width: 100%;
                height: 100%;
                margin: 0;
                padding: 0;
                overflow: hidden; /* No window scroll */
                background: #000;
            }
            
            /* The Container that fills the 1080x1920 video */
            #presentation-container {
                position: fixed;
                top: 0; 
                left: 0;
                width: 1080px;
                height: 1920px;
                background: radial-gradient(circle at center, #1a1a1a 0%, #000 70%);
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                z-index: 99990; /* Below cursor, above content? No, we wrap content. */
                font-family: 'Arial', sans-serif;
                color: #fff;
            }
            
            /* Header Text */
            #presentation-header {
                font-size: 40px;
                font-weight: bold;
                letter-spacing: 2px;
                margin-bottom: 40px;
                text-transform: uppercase;
                color: #888;
            }
            
            #presentation-title {
                 font-size: 60px;
                 font-weight: 800;
                 margin-bottom: 60px;
                 text-align: center;
                 background: linear-gradient(90deg, #fff, #888);
                 -webkit-background-clip: text;
                 -webkit-text-fill-color: transparent;
            }
            
            /* The Phone Mockup Frame */
            #mockup-frame {
                width: 700px;  /* 360 * 2ish? Fits widely */
                height: 1100px; /* 16:9ish */
                background: #000;
                border: 20px solid #222;
                border-radius: 40px;
                box-shadow: 0 0 100px rgba(0, 255, 136, 0.2);
                overflow: hidden; /* Clip content */
                position: relative;
            }
            
            /* The Content Wrapper inside the phone */
            /* We will move the original BODY content into this div */
            #mockup-content {
                width: 100%;
                height: 100%;
                overflow-y: scroll; /* Scrollable inside */
                overflow-x: hidden;
                background: #0a0a0a;
            }
            
            /* Hide scrollbars in mockup */
            #mockup-content::-webkit-scrollbar { display: none; }
            
            /* Footer */
            #presentation-footer {
                margin-top: 60px;
                background: #fff;
                color: #000;
                padding: 15px 40px;
                border-radius: 50px;
                font-weight: bold;
                font-size: 30px;
            }

            /* AI Cursor */
            #ai-cursor {
                position: fixed;
                top: 0; left: 0;
                width: 40px;
                height: 40px;
                background: rgba(0, 255, 136, 0.9);
                border: 3px solid white;
                border-radius: 50%;
                pointer-events: none;
                z-index: 999999;
                transition: transform 0.1s;
                box-shadow: 0 0 20px rgba(0,255,136,0.6);
            }
        """)
        
        # 2. Re-structure the DOM
        # We need to take all children of body and move them into #mockup-content
        # Then put #mockup-content inside #mockup-frame inside #presentation-container
        
        js_injection = f"""
            // Create the wrapper structure
            const container = document.createElement('div');
            container.id = 'presentation-container';
            
            const header = document.createElement('div');
            header.id = 'presentation-header';
            header.innerText = "{overlay_header if overlay_header else 'WEB DESIGN AWARDS'}";
            
            const title = document.createElement('div');
            title.id = 'presentation-title';
            title.innerText = "{overlay_text if overlay_text else 'THE POWER OF SIMPLICITY'}";
            
            const frame = document.createElement('div');
            frame.id = 'mockup-frame';
            
            const innerContent = document.createElement('div');
            innerContent.id = 'mockup-content';
            
            const footer = document.createElement('div');
            footer.id = 'presentation-footer';
            footer.innerText = 'DAILY INSPIRATION';
            
            // Assemble
            frame.appendChild(innerContent);
            
            container.appendChild(header);
            container.appendChild(title);
            container.appendChild(frame);
            container.appendChild(footer);
            
            // Move existing body content
            while (document.body.firstChild) {{
                innerContent.appendChild(document.body.firstChild);
            }}
            
            document.body.appendChild(container);
            
            // Add Cursor
            const c = document.createElement('div');
            c.id = 'ai-cursor';
            document.body.appendChild(c);
            
            // Cursor Sync
            document.addEventListener('mousemove', e => {{
                c.style.left = e.clientX + 'px';
                c.style.top = e.clientY + 'px';
            }});
            document.addEventListener('mousedown', () => c.style.transform = 'scale(0.8)');
            document.addEventListener('mouseup', () => c.style.transform = 'scale(1)');
            
            // Force Font Scale on Inner Content to look like mobile
            // Since frame is 700px wide, and mobile is usually 360-ish.
            // 700 / 360 = ~2x. 
            innerContent.style.fontSize = '200%'; 
        """
        
        await page.evaluate(js_injection)
        
        # Helper function for text overlay logic.
        pass

        # Force GSAP refresh
        await page.evaluate("""
            if(window.ScrollTrigger) {
                // ScrollTrigger usually listens to window. 
                // We need to tell it to listen to #mockup-content
                ScrollTrigger.defaults({ scroller: "#mockup-content" });
                ScrollTrigger.refresh();
            }
        """)
        await page.wait_for_timeout(1000)
        
        # --- LOGIC UPDATE: Target the MOCKUP CONTENT ---
        
        pois = await page.evaluate("""() => {
            // We search inside the mockup content
            const container = document.getElementById('mockup-content');
            const targets = Array.from(container.querySelectorAll('button, a, input, canvas, .card, .interactive, h1, h2, video'));
            
            return targets.map(t => {
                const r = t.getBoundingClientRect();
                // r is relative to Viewport (Window).
                // Since container is fixed, this works for targeting!
                // But specifically for sorting default order...
                return {
                    y: r.top + container.scrollTop, // Position relative to content top
                    height: r.height,
                    type: t.tagName,
                    classList: Array.from(t.classList).join(' '),
                    centerX: r.left + r.width/2,
                    centerY: r.top + r.height/2
                };
            }).sort((a, b) => a.y - b.y);
        }""")
        
        total_height = await page.evaluate("document.getElementById('mockup-content').scrollHeight") 
        viewport_height = 1100 # Height of #mockup-frame
        
        current_scroll = 0
        start_time = time.time()
        
        # Initial Mouse Move to Mockup Center
        await page.mouse.move(540, 960) 
        
        loop_count = 0
        while True:
            # 1. Get current scroll of the container
            current_scroll_pos = await page.evaluate("document.getElementById('mockup-content').scrollTop")
            
            # 2. Identify POIs visible within the frame
            # The frame is roughly at Top: 250px (est), Height: 1100px.
            # We can use getBoundingClientRect() to check visibility.
            
            visible_targets = await page.evaluate("""() => {
                const targets = Array.from(document.querySelectorAll('#mockup-content button, #mockup-content a, #mockup-content .card, #mockup-content .interactive, #mockup-content canvas'));
                const frameRect = document.getElementById('mockup-frame').getBoundingClientRect();
                
                return targets.map(t => {
                     const r = t.getBoundingClientRect();
                     // Check if inside frame bounds
                     if (r.top > frameRect.top && r.bottom < frameRect.bottom) {
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
            
            should_interact = False
            if len(visible_targets) > 0 and random.random() < 0.65:
                 should_interact = True

            if should_interact:
                target = random.choice(visible_targets)
                # Move Mouse
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
            
            # SCROLL STEP - WE MUST SCROLL THE ELEMENT via JS because wheel scrolls window usually (unless focused)
            # Actually page.mouse.wheel usually scrolls the element under cursor.
            # Let's ensure cursor is over frame.
            await page.mouse.move(540, 960) # Center
            
            step = random.randint(50, 150)
            await page.mouse.wheel(0, step)
            await page.wait_for_timeout(random.randint(30, 80))
            
            loop_count += 1
            if time.time() - start_time > duration + 5:
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
