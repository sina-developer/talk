# video_manager.py
"""
Manages background video playback using an external player like cvlc.
"""
import subprocess
import os
import signal 
import config

current_video_process = None

def start_looping_video(video_path_from_config): # Argument is the full relative path from config
    """
    Stops any currently playing video and starts a new one, looped.
    Args:
        video_path_from_config (str): The full relative path to the video file
                                      (e.g., "videos/idle.mp4") as defined in config.py.
    """
    global current_video_process
    stop_current_video() 

    # --- FIX 2: Use the passed video_path_from_config directly ---
    # It already includes the VIDEO_BASE_PATH due to how it's defined in config.py
    # e.g., config.VIDEO_IDLE is os.path.join(config.VIDEO_BASE_PATH, "idle.mp4")
    video_path = video_path_from_config 
    
    # If APP_DIR is needed for absolute paths and CWD is not guaranteed:
    # current_app_dir = os.path.dirname(os.path.abspath(config.__file__)) # Get dir of config.py
    # video_path = os.path.join(current_app_dir, video_path_from_config)
    # For now, assume AI.sh cds into the correct app directory.

    if not os.path.exists(video_path):
        print(f"Video file not found: {video_path}")
        print(f"Current working directory: {os.getcwd()}")
        print(f"Ensure '{config.VIDEO_BASE_PATH}' directory exists in your app root and contains the video.")
        return

    command = config.VIDEO_PLAYER_COMMAND_TEMPLATE + [video_path]
    
    print(f"Starting video: {' '.join(command)}")
    try:
        current_video_process = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.PIPE    
        )
        # print(f"Looping video '{video_path}' started (PID: {current_video_process.pid}).") # Less verbose
    except FileNotFoundError:
        player_name = config.VIDEO_PLAYER_COMMAND_TEMPLATE[0]
        print(f"ERROR: Video player '{player_name}' not found. Please install it.")
        current_video_process = None
    except Exception as e:
        print(f"Error starting video {video_path}: {e}")
        current_video_process = None

def stop_current_video():
    # ... (This function remains the same as the last version you have - no changes needed here) ...
    global current_video_process
    if current_video_process:
        # print(f"Stopping current video (PID: {current_video_process.pid})...") # Less verbose
        try:
            current_video_process.terminate()
            try: current_video_process.wait(timeout=0.5) 
            except subprocess.TimeoutExpired:
                current_video_process.kill()
                current_video_process.wait(timeout=0.5)
        except Exception: pass # Ignore errors during stop
        finally: current_video_process = None
