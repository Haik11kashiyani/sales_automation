import os
import json
import asyncio
from recorder import record_url
from audio import generate_voiceover
from editor import assemble_video
import argparse

from recorder import record_url, run_server_in_thread
import time

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT_POOL = os.path.join(BASE_DIR, "content_pool")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# Start Local Server (Daemon)
try:
    run_server_in_thread()
    time.sleep(2) # Warmup
except Exception as e:
    print(f"Server start warning: {e}")

def get_content_folders():
    return [f for f in os.listdir(CONTENT_POOL) if os.path.isdir(os.path.join(CONTENT_POOL, f))]

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    previous_history = []
    # Persistent history file in 'data' folder (must be committed)
    data_dir = os.path.join(BASE_DIR, "data")
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    history_file = os.path.join(data_dir, "history.json")
    
    if os.path.exists(history_file):
        with open(history_file, 'r') as f:
            try:
                previous_history = json.load(f)
            except:
                previous_history = []
    
    # Get list of folders
    folders = get_content_folders()
    
    # Sort folders to ensure deterministic order (optional)
    folders.sort()
    
    # Scheduling Logic: Pick ONE folder that hasn't been done
    target_folder = None
    for folder in folders:
        if folder not in previous_history:
            target_folder = folder
            break
            
    if not target_folder:
        print("No new content to process! All folders in history.")
        return

    print(f"Selected for this run: {target_folder}")
    
    folder = target_folder
    folder_path = os.path.join(CONTENT_POOL, folder)
    index_html = os.path.join(folder_path, "index.html")
    script_json = os.path.join(folder_path, "script.json")
    
    # Output filenames
    raw_video = os.path.join(OUTPUT_DIR, f"raw_{folder}.mp4")
    voiceover = os.path.join(OUTPUT_DIR, f"voice_{folder}.mp3")
    final_video = os.path.join(OUTPUT_DIR, f"final_{folder}.mp4")
    
    # 1. Read Script Data
    script_data = {}
    if os.path.exists(script_json):
        with open(script_json, 'r') as f:
            script_data = json.load(f)
        duration = generate_voiceover(script_json, voiceover)
    else:
        print(f"No script.json found for {folder}, skipping.")
        return

    # Extract Metadata
    overlay_text = script_data.get("overlay_text", "")
    overlay_header = script_data.get("overlay_header", "")
    
    if duration <= 0:
        print("Audio generation failed or returned 0 duration.")
        # Fallback
        duration = script_data.get("video_duration_override", 30)
        print(f"Using fallback duration: {duration}s")

    # 2. Record Video
    if os.path.exists(index_html):
        # We run the async recorder
        asyncio.run(record_url(index_html, duration, raw_video, overlay_text=overlay_text, overlay_header=overlay_header))
    else:
            print(f"No index.html found for {folder}")
            return

    # 3. Assemble
    if os.path.exists(raw_video) and os.path.exists(voiceover):
        assemble_video(raw_video, voiceover, final_video)
        
        # 4. Update History
        previous_history.append(folder)
        with open(history_file, 'w') as f:
            json.dump(previous_history, f)
            print(f"Updated history: {folder} marked as done.")
    else:
        print("Missing raw video or voiceover, cannot assemble.")


if __name__ == "__main__":
    main()
