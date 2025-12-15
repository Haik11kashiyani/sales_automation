# Autonomous YouTube Shorts Factory

## How to Add New Videos
This engine automatically turns folders into videos. To add a new video to the queue:

1.  **Create a new folder** inside `content_pool/`.
    *   Example: `content_pool/my_new_website/`
2.  **Add your files**:
    *   `index.html`: The full webpage you want to record. Ensure it is responsive (mobile-first is best for Shorts).
    *   `script.json`: The narration and configuration.

### script.json Format
```json
{
    "narration": "Your narration text here. The AI will read this.",
    "video_duration_override": 30,
    "has_intro": false,
    "has_outro": false
}
```

## How it Works
1.  The system scans `content_pool/` for any folder.
2.  It checks `output/` to see if a video already exists for that folder (e.g., `final_my_new_website.mp4`).
3.  If not, it starts the pipeline:
    *   **Audio**: Generates voiceover from `script.json`.
    *   **Video**: Records `index.html` scrolling for the exact duration of the audio.
    *   **Edit**: Combines them into a final MP4.

## GitHub Automation
This project runs entirely on GitHub Actions.
1.  Push your new folders to GitHub.
2.  The "Production Schedule" workflow runs automatically (Mon/Wed/Fri) or you can trigger it manually in the "Actions" tab.
3.  Download your videos from the "Artifacts" section of the workflow run.
