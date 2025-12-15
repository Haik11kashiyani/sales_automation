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
        # --- PRESENTATION MODE: OVERLAY STRATEGY (Non-Destructive) ---
        # 1. We keep the Body as the "Page". We Scale it to look like mobile.
        # 2. We inject a FIXED Overlay on top that contains the "Phone Frame", Header, and Footer.
        # 3. We use pointer-events: none on the overlay so clicks pass through to the body.
        
        await page.add_style_tag(content="""
            /* 1. Force Mobile Layout on the content */
            html {
                width: 100%;
                overflow-x: hidden;
                background: #000; /* Outer background */
            }
            
            body {
                width: 390px; /* Standard Modern Mobile Width */
                min-height: 100vh;
                margin: 0 auto; /* Center mechanically */
                background: #0a0a0a; /* Site background */
                
                /* THE TRANSFORM: Scale it up to fill the 1080px width */
                /* 1080 / 390 = 2.76 */
                /* Let's aim for a Frame width of ~750px (Visual). */
                /* 750 / 390 = ~1.92. Let's use 2.0 */
                
                transform: scale(2.2); 
                transform-origin: top center;
                
                /* Push it down to start inside the frame 'window' */
                /* Frame starts at roughly 300px from top? */
                /* Since we scale from top, the top edge stays at 0. */
                /* We need to move the body down. */
                position: relative;
                top: 280px; /* Adjust based on frame header height */
                
                overflow-y: visible;
                overflow-x: hidden;
            }
            
            /* Hide scrollbars */
            ::-webkit-scrollbar { display: none; }
            
            /* 2. The Overlay HUD (Heads Up Display) */
            #presentation-overlay {
                position: fixed;
                top: 0; 
                left: 0;
                width: 1080px;
                height: 1920px;
                z-index: 99990; /* High Z-index */
                pointer-events: none; /* CLICK THROUGH to body! */
                
                display: flex;
                flex-direction: column;
                align-items: center;
                
                /* Background: We need the center to be transparent (to see body) */
                /* But the sides/top/bottom to be Black/Gradient. */
                /* Using a giant radial gradient or border hack? */
                /* Let's use a "Masking" approach with borders. */
                /* Or just simpler: Use CSS Grid or Flex to place blockers. */
            }
            
            /* The "Frame" that visually surrounds the content */
            .frame-border {
                position: absolute;
                top: 250px; /* Start of phone screen */
                width: 860px; /* 390 * 2.2 = 858px */
                height: 1300px;
                
                border: 25px solid #222;
                border-radius: 50px;
                box-shadow: 
                    0 0 0 1000px #000, /* The giant blocker for everything else */
                    inset 0 0 40px rgba(0,0,0,0.5), /* Inner shadow */
                    0 0 80px rgba(0, 255, 136, 0.15); /* Outer Glow */
                    
                z-index: 1; /* Behind text, in front of nothing? */
                pointer-events: none;
            }
            
            /* Text Layers (On top of the black blocker) */
            .overlay-content {
                position: absolute;
                width: 100%;
                height: 100%;
                z-index: 2;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: space-between;
                padding: 60px 0;
            }
            
            #presentation-header {
                font-size: 40px;
                font-weight: bold;
                letter-spacing: 2px;
                text-transform: uppercase;
                color: #666;
                margin-top: 20px;
            }
            
            #presentation-title {
                 font-size: 65px;
                 font-weight: 800;
                 text-align: center;
                 background: linear-gradient(90deg, #fff, #999);
                 -webkit-background-clip: text;
                 -webkit-text-fill-color: transparent;
                 margin-top: 10px;
            }
            
            #presentation-footer {
                margin-bottom: 80px;
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 15px;
            }
              
            .cta-button {
                background: linear-gradient(135deg, #0cebeb, #20e3b2, #29ffc6);
                color: #000;
                padding: 20px 70px;
                border-radius: 60px;
                font-weight: 900;
                font-size: 38px;
                text-transform: uppercase;
                letter-spacing: 1px;
                box-shadow: 0 0 40px rgba(32, 227, 178, 0.5);
                animation: pulse-glow 2.5s infinite ease-in-out;
            }
            
            .cta-subtext {
                font-size: 22px;
                color: #888;
                font-weight: bold;
                letter-spacing: 3px;
                text-transform: uppercase;
                animation: fade-in-up 1s ease-out;
            }
            
            @keyframes pulse-glow {
                0% { transform: scale(1); box-shadow: 0 0 30px rgba(32, 227, 178, 0.4); }
                50% { transform: scale(1.03); box-shadow: 0 0 70px rgba(32, 227, 178, 0.7); }
                100% { transform: scale(1); box-shadow: 0 0 30px rgba(32, 227, 178, 0.4); }
            }
            
            /* Cursor - Needs to match the SCALE */
            /* Since body is scaled 2.2x, if we put cursor in body, it scales too. */
            /* 20px cursor * 2.2 = 44px visual. Good. */
            #ai-cursor {
                position: absolute;
                top: 0; left: 0;
                width: 20px;
                height: 20px;
                background: rgba(0, 255, 136, 0.9);
                border: 2px solid white;
                border-radius: 50%;
                pointer-events: none;
                z-index: 999999;
                transition: transform 0.1s;
                box-shadow: 0 0 10px rgba(0,255,136,0.6);
            }
        """)

        js_injection = f"""
            // Create the Overlay HUD
            const overlay = document.createElement('div');
            overlay.id = 'presentation-overlay';
            
            // Frame Border (The Blocker)
            const frame = document.createElement('div');
            frame.className = 'frame-border';
            
            // Content Container
            const content = document.createElement('div');
            content.className = 'overlay-content';
            
            // Header Group
            const headerGroup = document.createElement('div');
            headerGroup.style.display = 'flex';
            headerGroup.style.flexDirection = 'column';
            headerGroup.style.alignItems = 'center';
            
            const header = document.createElement('div');
            header.id = 'presentation-header';
            header.innerText = "{overlay_header if overlay_header else 'WEB DESIGN AWARDS'}";
            
            const title = document.createElement('div');
            title.id = 'presentation-title';
            title.innerText = "{overlay_text if overlay_text else 'THE FUTURE IS HERE'}";
            
            headerGroup.appendChild(header);
            headerGroup.appendChild(title);
            
            // Footer Group
            const footer = document.createElement('div');
            footer.id = 'presentation-footer';
            
            const ctaBtn = document.createElement('div');
            ctaBtn.className = 'cta-button';
            ctaBtn.innerText = "{cta_text if cta_text else 'VISIT WEBSITE'}";
            
            const ctaSub = document.createElement('div');
            ctaSub.className = 'cta-subtext';
            ctaSub.innerText = "{cta_subtext if cta_subtext else 'LINK IN BIO'}";
            
            footer.appendChild(ctaBtn);
            footer.appendChild(ctaSub);
            
            // Assemble content
            content.appendChild(headerGroup);
            // Spacer to push footer to bottom is handled by justify-content: space-between
            content.appendChild(footer);
            
            overlay.appendChild(frame);
            overlay.appendChild(content);
            
            document.body.appendChild(overlay);
            
            // AI Cursor (Inside Body, so it scales with content)
            const c = document.createElement('div');
            c.id = 'ai-cursor';
            document.body.appendChild(c);
            
            // Sync Logic
            // Playwright gives us Viewport coordinates (0-1080).
            // Our body is Scaled (2.2) and Offset (Top 280).
            // We need to inverse map the coordinates.
            
            // VisualX = (LogicalX * Scale) + MarginX
            // LogicalX = (VisualX - MarginX) / Scale
            
            // MarginX is auto (centered).
            // Body Width = 390. Scaled = 858. 
            // Viewport = 1080.
            // MarginX = (1080 - 858) / 2 = 111px.
            
            const SCALE = 2.2;
            const MARGIN_X = (1080 - (390 * SCALE)) / 2;
            const MARGIN_Y = 280; // Top offset
            
            document.addEventListener('mousemove', e => {{
                // e.clientX is Viewport (Visual).
                // We want to set 'left'/ 'top' on the cursor which is in the SCALED body context.
                
                const logicalX = (e.clientX - MARGIN_X) / SCALE;
                const logicalY = (e.clientY - MARGIN_Y) / SCALE;
                
                c.style.left = logicalX + 'px';
                c.style.top = logicalY + 'px';
            }});
            
            document.addEventListener('mousedown', () => c.style.transform = 'scale(0.8)');
            document.addEventListener('mouseup', () => c.style.transform = 'scale(1)');
        """
        
        await page.evaluate(js_injection)
        
        await page.evaluate(js_injection)
        
        # Helper function for text overlay logic.
        pass

        # Force GSAP refresh
        await page.evaluate("if(window.ScrollTrigger) window.ScrollTrigger.refresh()")
        await page.wait_for_timeout(1000)
        
        # --- LOGIC UPDATE: Overlay Mode ---
        # We scroll the WINDOW (since body is the page).
        # We filter targets based on if they are in the "Frame" area visually.
        # But actually, with the `box-shadow` mask, we can just allow everything in viewport to be candidate.
        
        pois = await page.evaluate("""() => {
            const targets = Array.from(document.querySelectorAll('button, a, input, canvas, .card, .interactive, h1, h2, video'));
            return targets.map(t => {
                const r = t.getBoundingClientRect();
                return {
                    y: r.top + window.scrollY,
                    height: r.height,
                    type: t.tagName,
                    classList: Array.from(t.classList).join(' '),
                    centerX: r.left + r.width/2,
                    centerY: r.top + r.height/2
                };
            }).sort((a, b) => a.y - b.y);
        }""")
        
        total_height = await page.evaluate("document.body.scrollHeight") 
        viewport_height = 1920 
        
        current_scroll = 0
        start_time = time.time()
        
        # Initial Mouse Move
        await page.mouse.move(540, 960) 
        
        while True:
            current_idx = await page.evaluate("window.scrollY")
            
            # Identify Next Target
            visible_targets = await page.evaluate("""() => {
                const targets = Array.from(document.querySelectorAll('button, a, .card, .interactive, canvas'));
                // Frame is roughly 250 to 1550 Y visually?
                // Viewport is 0-1920.
                
                return targets.map(t => {
                     const r = t.getBoundingClientRect();
                     // Check if valid target
                     // We prefer targets near center of screen (where the phone is)
                     if (r.top > 250 && r.bottom < 1550) { 
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
            
            # SCROLL STEP - Scroll WINDOW
            # Since body is transformed, does window scroll amount map 1:1?
            # No, if body is scaled 2.2x, 100px scroll might look like 220px? Or 100px?
            # It usually scrolls the viewport logical pixels. 
            step = random.randint(50, 150)
            await page.mouse.wheel(0, step)
            await page.wait_for_timeout(random.randint(30, 80))
            
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
