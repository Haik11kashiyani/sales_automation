from moviepy.editor import VideoFileClip, AudioFileClip, CompositeVideoClip
import os

def assemble_video(video_path: str, audio_path: str, output_path: str):
    """
    Combines the recorded video and the generated audio.
    Time-stretches video to match audio duration.
    """
    print(f"Assembling video: {video_path} + {audio_path}")
    
    if not os.path.exists(video_path) or not os.path.exists(audio_path):
        print("Missing video or audio file.")
        return

    video = VideoFileClip(video_path)
    audio = AudioFileClip(audio_path)
    
    # Calculate speed factor
    # We want video duration to match audio duration
    # BUT, we might want to keep the video linear. 
    # If the video is simply scrolling, changing speed is fine.
    
    final_duration = audio.duration
    video_duration = video.duration
    
    print(f"Video duration: {video_duration}, Audio duration: {final_duration}")
    
    # Speed up or slow down video
    speed_factor = video_duration / final_duration
    final_video = video.fx(lambda clip: clip.speedx(speed_factor))
    
    # Set audio
    final_video = final_video.set_audio(audio)
    
    # Write output
    final_video.write_videofile(
        output_path, 
        codec='libx264', 
        audio_codec='aac', 
        fps=30,
        preset='medium' 
        # preset medium is good balance for speed/quality
    )
    
    # Close clips
    video.close()
    audio.close()
    
    print(f"Final video saved to {output_path}")

if __name__ == "__main__":
    pass
