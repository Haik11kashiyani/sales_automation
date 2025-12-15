from elevenlabs import generate, save, set_api_key
import os
import json
from dotenv import load_dotenv

load_dotenv()

def get_api_key():
    """
    Rotates through available API keys.
    For simplicity, we check a list of keys provided in env.
    Env var format: ELEVENLABS_API_KEYS=key1,key2,key3
    """
    keys_str = os.getenv("ELEVENLABS_API_KEYS", "")
    if not keys_str:
        print("No ElevenLabs API keys found in .env")
        return None
    
    keys = keys_str.split(",")
    # In a real scenario, you'd track usage or catch 402/429 errors 
    # and switch to the next key.
    # For now, we return the first one, but the structure allows expansion.
    return keys[0]

def generate_voiceover(script_path: str, output_path: str):
    """
    Reads the script.json, generates audio using ElevenLabs, 
    and returns duration.
    """
    with open(script_path, 'r') as f:
        data = json.load(f)
    
    text = data.get("narration", "")
    if not text:
        raise ValueError("No narration text found in script.json")

    api_key = get_api_key()
    if api_key:
        set_api_key(api_key)
    
    print(f"Generating voiceover for: {text[:30]}...")
    
    try:
        audio = generate(
            text=text,
            voice="Bella", # Or any other high quality voice
            model="eleven_monolingual_v1"
        )
        
        save(audio, output_path)
        
        # Determine duration using MoviePy (since we have it as dependency)
        # or just simple estimation if we want to avoid loading heavy libs here.
        # But we need exact duration for the video recorder to know how long to scroll.
        # Let's use a lightweight method or just return metadata if ElevenLabs provided it.
        # ElevenLabs doesn't return duration directly in 'generate'.
        # We will use pydub or just let the main controller handle duration check
        # using the file size or a library.
        # For this snippet, we will rely on src/editor.py or similar to check length,
        # OR we import moviepy here just for duration check.
        
        from moviepy.editor import AudioFileClip
        clip = AudioFileClip(output_path)
        duration = clip.duration
        clip.close()
        
        print(f"Audio generated: {duration}s")
        return duration
        
    except Exception as e:
        print(f"Error generating audio: {e}")
        # Here we would implement the key rotation retry logic:
        # if "quota_exceeded" in str(e): try_next_key()
        return 0

if __name__ == "__main__":
    # Test
    # generate_voiceover("../content_pool/business_01/script.json", "test_audio.mp3")
    pass
