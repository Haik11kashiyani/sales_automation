import os
import json
import asyncio
from recorder import record_url
from audio import generate_voiceover
from editor import assemble_video
import argparse

from recorder import record_url, run_server_in_thread
import shutil
from creative import generate_viral_hooks, generate_upload_metadata
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
    BATCH_SIZE = 3
    
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    previous_history = []
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
    
    # Get all folders
    folders = get_content_folders()
    folders.sort()
    
    # Filter pending
    pending_folders = [f for f in folders if f not in previous_history]
    
    if not pending_folders:
        print("No new content to process! All folders in history.")
        return

    # Select Batch
    batch = pending_folders[:BATCH_SIZE]
    print(f"🚀 Starting Batch Run: {len(batch)} videos ({batch})")
    
    for folder in batch:
        print(f"\n🎥 Processing: {folder}")
        folder_path = os.path.join(CONTENT_POOL, folder)
        index_html = os.path.join(folder_path, "index.html")
        script_json = os.path.join(folder_path, "script.json")
        
        # Output paths
        raw_video = os.path.join(OUTPUT_DIR, f"raw_{folder}.mp4")
        voiceover = os.path.join(OUTPUT_DIR, f"voice_{folder}.mp3")
        final_video = os.path.join(OUTPUT_DIR, f"final_{folder}.mp4")
        meta_file = os.path.join(OUTPUT_DIR, f"metadata_{folder}.json")

        if not os.path.exists(index_html):
            print(f"Skipping {folder}: No index.html")
            continue

        # 1. Script & Audio Strategy
        script_data = {}
        duration = 30 # Default
        has_audio = False
        
        if os.path.exists(script_json):
            with open(script_json, 'r') as f:
                script_data = json.load(f)
            
            narration = script_data.get("narration", "")
            if narration and len(narration.strip()) > 5:
                # Narrated Mode
                try:
                    duration = generate_voiceover(script_json, voiceover)
                    if duration > 0: has_audio = True
                except Exception as e:
                    print(f"Audio failed, defaulting to Silent Mode: {e}")
            else:
                # Silent / Trending Music Mode
                print("Silent Mode Active (Trend Music Strategy)")
                duration = script_data.get("video_duration_override", 30)

        # 2. Viral Hooks & Metadata
        hooks = generate_viral_hooks(script_data.get("narration", ""))
        
        # Merge hooks with script defaults
        overlay_text = script_data.get("overlay_text") or hooks.get("overlay_text")
        overlay_header = script_data.get("overlay_header") or hooks.get("overlay_header")
        cta_text = script_data.get("cta_text") or hooks.get("cta_text")
        cta_subtext = script_data.get("cta_subtext") or hooks.get("cta_subtext")
        
        # Generate & Save YouTube Metadata (Title/Tags)
        yt_meta = generate_upload_metadata(script_data.get("narration", ""), hooks)
        with open(meta_file, 'w') as f:
            json.dump(yt_meta, f, indent=2)
        print(f"✅ Metadata saved to {meta_file}")

        # 3. Record Video
        print(f"Recording {folder} for {duration}s...")
        asyncio.run(record_url(index_html, duration, raw_video, 
                               overlay_text=overlay_text, 
                               overlay_header=overlay_header, 
                               cta_text=cta_text, 
                               cta_subtext=cta_subtext))

        # 4. Finalize
        if os.path.exists(raw_video):
            if has_audio and os.path.exists(voiceover):
                assemble_video(raw_video, voiceover, final_video)
            else:
                # Silent Finalization
                shutil.copy(raw_video, final_video)
                print(f"Silent video ready: {final_video}")
            
            # Update History
            previous_history.append(folder)
            with open(history_file, 'w') as f:
                json.dump(previous_history, f)
        else:
            print("Recording failed, skipping assembly.")
            
    print("\n✅ Batch Run Complete.")

if __name__ == "__main__":
    main()
