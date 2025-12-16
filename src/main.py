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
    # pending_folders = [f for f in folders if f not in previous_history]
    
    # DEBUG: Force Run All for Verification
    print(f"DEBUG: All Folders: {folders}")
    print(f"DEBUG: History: {previous_history}")
    print("DEBUG: Forcing run of ALL folders to ensure artifact generation.")
    pending_folders = folders 
    
    if not pending_folders:
        print("No new content to process! All folders in history.")
        return

    # Select Batch
    batch = pending_folders[:BATCH_SIZE]
    print(f"🚀 Starting Batch Run: {len(batch)} videos ({batch})")
    
    # DEBUG: Create a token file to verify Output Write Access & Artifact Upload
    with open(os.path.join(OUTPUT_DIR, 'debug_token.txt'), 'w') as f:
        f.write(f"Run started at {time.time()}\nBatch: {batch}\nExisting Output: {os.listdir(OUTPUT_DIR) if os.path.exists(OUTPUT_DIR) else 'None'}")
    
    for folder in batch:
        print(f"\n🎥 Processing: {folder}")
        folder_path = os.path.join(CONTENT_POOL, folder)
        index_html = os.path.join(folder_path, "index.html")
        script_json = os.path.join(folder_path, "script.json")
        
        # Verify Paths
        print(f"   path: {folder_path}")
        print(f"   html: {index_html} (Exists: {os.path.exists(index_html)})")
        
        # Output paths
        raw_video = os.path.join(OUTPUT_DIR, f"raw_{folder}.mp4")
        voiceover = os.path.join(OUTPUT_DIR, f"voice_{folder}.mp3")
        final_video = os.path.join(OUTPUT_DIR, f"final_{folder}.mp4")
        meta_file = os.path.join(OUTPUT_DIR, f"metadata_{folder}.json")

        if not os.path.exists(index_html):
            print(f"⚠️ Skipping {folder}: No index.html found at {index_html}")
            continue

        # ... (Script/Audio Logic skipped for brevity, keeps existing) ...
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
                print("Silent Mode Active (Trend Music Strategy)")
                duration = script_data.get("video_duration_override", 30)

        # 2. Viral Hooks & Metadata
        hooks = generate_viral_hooks(script_data.get("narration", ""))
        
        # Merge hooks
        overlay_text = script_data.get("overlay_text") or hooks.get("overlay_text")
        overlay_header = script_data.get("overlay_header") or hooks.get("overlay_header")
        cta_text = script_data.get("cta_text") or hooks.get("cta_text")
        cta_subtext = script_data.get("cta_subtext") or hooks.get("cta_subtext")
        
        # Save Metadata
        yt_meta = generate_upload_metadata(script_data.get("narration", ""), hooks)
        with open(meta_file, 'w') as f:
            json.dump(yt_meta, f, indent=2)
        print(f"✅ Metadata saved to {meta_file}")

        # 3. Record Video
        print(f"Recording {folder} for {duration}s to {raw_video}...")
        try:
            asyncio.run(record_url(index_html, duration, raw_video, 
                                   overlay_text=overlay_text, 
                                   overlay_header=overlay_header, 
                                   cta_text=cta_text, 
                                   cta_subtext=cta_subtext))
        except Exception as e:
            print(f"❌ RECORDING FAILED for {folder}: {e}")
            import traceback
            traceback.print_exc()

        # 4. Finalize
        if os.path.exists(raw_video):
            # Check file size
            size = os.path.getsize(raw_video)
            print(f"   Raw Video Created: {size} bytes")
            if size < 1000:
                 print("⚠️ Warning: Video file is suspiciously small.")
            
            if has_audio and os.path.exists(voiceover):
                assemble_video(raw_video, voiceover, final_video)
            else:
                # Silent Finalization
                shutil.copy(raw_video, final_video)
                print(f"Silent video ready: {final_video}")
            
            # Update History (Temporarily disabled for debug)
            # previous_history.append(folder)
            # with open(history_file, 'w') as f:
            #     json.dump(previous_history, f)
        else:
            print(f"❌ Critical: Raw video file not found at {raw_video}")
            
    print("\n✅ Batch Run Complete. Directory Listing of Output:")
    print(os.listdir(OUTPUT_DIR))

if __name__ == "__main__":
    main()
