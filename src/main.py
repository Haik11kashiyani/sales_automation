import os
import json
import asyncio
from recorder import record_url
from audio import generate_voiceover
from editor import assemble_video
import argparse

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT_POOL = os.path.join(BASE_DIR, "content_pool")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

def get_content_folders():
    return [f for f in os.listdir(CONTENT_POOL) if os.path.isdir(os.path.join(CONTENT_POOL, f))]

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    folders = get_content_folders()
    print(f"Found content folders: {folders}")

    for folder in folders:
        folder_path = os.path.join(CONTENT_POOL, folder)
        index_html = os.path.join(folder_path, "index.html")
        script_json = os.path.join(folder_path, "script.json")
        
        # Output filenames
        raw_video = os.path.join(OUTPUT_DIR, f"raw_{folder}.mp4")
        voiceover = os.path.join(OUTPUT_DIR, f"voice_{folder}.mp3")
        final_video = os.path.join(OUTPUT_DIR, f"final_{folder}.mp4")
        
        # Check if already processed (simple check: if final video exists)
        if os.path.exists(final_video):
            print(f"Skipping {folder}, already processed.")
            continue
            
        print(f"Processing {folder}...")
        
        # 1. Generate Audio
        duration = 0
        if os.path.exists(script_json):
            duration = generate_voiceover(script_json, voiceover)
        else:
            print(f"No script.json found for {folder}, skipping.")
            continue
            
        if duration <= 0:
            print("Audio generation failed or returned 0 duration.")
            # Fallback or exit? Let's fallback to manual duration if in json
            with open(script_json, 'r') as f:
                d = json.load(f)
                duration = d.get("video_duration_override", 30)
                print(f"Using fallback duration: {duration}s")

        # 2. Record Video
        if os.path.exists(index_html):
            # We run the async recorder
            asyncio.run(record_url(index_html, duration, raw_video))
        else:
             print(f"No index.html found for {folder}")
             continue

        # 3. Assemble
        if os.path.exists(raw_video) and os.path.exists(voiceover):
            assemble_video(raw_video, voiceover, final_video)
        else:
            print("Missing raw video or voiceover, cannot assemble.")

if __name__ == "__main__":
    main()
