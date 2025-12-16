import os
import random
import json
import requests

# Fallback Metadata if AI fails or no key provided
VIRAL_TEMPLATES = {
    "headers": [
        "WEB DESIGN AWARDS", "ILLEGAL DESIGN", "STOP SCROLLING", "DEVELOPER HACK",
        "VISUAL ASMR", "UI/UX MASTERCLASS", "IMPOSSIBLE WEBSITE", "CODING MAGIC"
    ],
    "titles": [
        "THE POWER OF SIMPLICITY", "BETTER THAN APPLE?", "3D WEB EXPLAINED",
        "COPY THIS DESIGN", "CLIENTS PAY $10K FOR THIS", "FUTURE OF WEB"
    ],
    "ctas": [
        "VISIT OUR WEBSITE", "CONTACT US NO", "GET A QUOTE", "START YOUR PROJECT",
        "HIRE US TODAY", "BUILD YOUR VISION"
    ],
    "urgency": [
        "TRANSFORM YOUR BRAND", "DOMINATE YOUR MARKET", "PREMIUM DESIGN", "NEXT LEVEL UI",
        "AWARD WINNING TEAM"
    ]
}

def generate_viral_hooks(script_text: str = ""):
    """
    Generates viral metadata (Header, Title, CTA) for the video.
    Tries to use OpenRouter AI if available, otherwise uses Viral Templates.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    hooks = {
        "overlay_header": "WEB DESIGN AWARDS",
        "overlay_text": "THE POWER OF SIMPLICITY",
        "cta_text": "GET THIS TEMPLATE",
        "cta_subtext": "LIMITED TIME OFFER"
    }

    if api_key:
        try:
            print("✨ connecting to OpenRouter for Creative AI...")
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            # Free model: google/gemini-2.0-flash-exp:free (if available) or similar low cost
            # We'll use a widely available free/cheap one or let user config.
            # actually user said "free openrouter api key".
            # We will try a standard widely supported model.
            
            prompt = f"""
            Analyze this video script and generate 4 SHORT, VIRAL, PUNCHY strings for a YouTube Short overlay.
            Script: "{script_text[:500]}..."
            
            Output strictly valid JSON with keys: overlay_header, overlay_text, cta_text, cta_subtext.
            Rules:
            1. overlay_header: 2-4 words, uppercase, authoritative (e.g. "DESIGN SECRETS").
            2. overlay_text: 3-5 words, intriguing (e.g. "YOU NEED TO SEE THIS").
            3. cta_text: 2-4 words, action oriented (e.g. "GET THE FILE").
            4. cta_subtext: 2-3 words, urgency (e.g. "LINK IN BIO").
            """
            
            payload = {
                "model": "google/gemini-2.0-flash-exp:free", # Using free tier model
                "messages": [{"role": "user", "content": prompt}]
            }
            
            response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                content = data['choices'][0]['message']['content']
                # Clean code blocks if present
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                    
                ai_hooks = json.loads(content.strip())
                hooks.update(ai_hooks)
                print("✅ AI Generated Viral Hooks")
                return hooks
                
        except Exception as e:
            print(f"⚠️ AI Generation failed ({e}), switching to Viral Templates.")

    # Fallback / Random Engine
    hooks["overlay_header"] = random.choice(VIRAL_TEMPLATES["headers"])
    hooks["overlay_text"] = random.choice(VIRAL_TEMPLATES["titles"])
    hooks["cta_text"] = random.choice(VIRAL_TEMPLATES["ctas"])
    hooks["cta_subtext"] = random.choice(VIRAL_TEMPLATES["urgency"])
    
    return hooks

def generate_upload_metadata(script_text: str, hooks: dict):
    """
    Generates YouTube Short Title, Description, and Tags.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    metadata = {
        "title": f"{hooks.get('overlay_header')} - {hooks.get('overlay_text')}",
        "description": f"Check out this amazing design! {hooks.get('cta_text')} in bio.",
        "tags": "#webdesign #uiux #coding"
    }
    
    if api_key:
        try:
            print("✨ Generative Metadata...")
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            prompt = f"""
            Generate YouTube Shorts metadata for this video.
            Context: {script_text[:300]}
            Hooks: {hooks}
            
            Output strictly JSON with keys: title, description, tags.
            Rules:
            1. title: Catchy, under 60 chars. MUST include a short CTA like "Get Code" or "Link in Bio" or "Watch Now". Include 1 emoji.
            2. description: FIRST LINE must be the Call To Action (e.g. "🚀 Get this template: Link in Bio"). Then 2 sentences of value.
            3. tags: String of 15 relevant hashtags including #webdesign.
            """
            
            payload = {
                "model": "google/gemini-2.0-flash-exp:free",
                "messages": [{"role": "user", "content": prompt}]
            }
            
            response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                content = data['choices'][0]['message']['content']
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                
                ai_meta = json.loads(content.strip())
                metadata.update(ai_meta)
                print("✅ Generated Metadata")
                return metadata
                
        except Exception as e:
            print(f"⚠️ Metadata Generation failed: {e}")
            
    return metadata

if __name__ == "__main__":
    print(generate_viral_hooks("Test script"))
