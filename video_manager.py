# video_manager.py
"""
Manages background video playback using an external player like cvlc.
"""
import subprocess
import os
import signal # For sending signals to processes
import config

# To keep track of the currently running video player process
current_video_process = None

def start_looping_video(video_file_name):
    """
    Stops any currently playing video and starts a new one, looped.
    Args:
        video_file_name (str): The base name of the video file (e.g., "idle.mp4").
                               It will be joined with VIDEO_BASE_PATH from config.
    """
    global current_video_process
    stop_current_video() # Stop any video that might be playing

    video_path = os.path.join(config.VIDEO_BASE_PATH, video_file_name) # Use base name
    
    # If using relative path from config, and AI.sh cds into APP_DIR, this should be fine.
    # Otherwise, ensure video_path is absolute or correctly relative to CWD.
    # For robustness if APP_DIR is defined in config:
    # APP_DIR = getattr(config, 'APP_DIR', '.') # Get APP_DIR if defined, else current dir
    # video_path = os.path.join(APP_DIR, config.VIDEO_BASE_PATH, video_file_name)


    if not os.path.exists(video_path):
        print(f"Video file not found: {video_path}")
        return

    command = config.VIDEO_PLAYER_COMMAND_TEMPLATE + [video_path]
    
    print(f"Starting video: {' '.join(command)}")
    try:
        # Use Popen for non-blocking execution, allowing Python script to continue.
        # Hide stdout/stderr unless debugging is needed.
        current_video_process = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL, # Suppress player's normal output
            stderr=subprocess.PIPE    # Capture errors for potential logging
        )
        # Check if process started successfully (optional quick check)
        # time.sleep(0.1) # Give it a moment to potentially fail
        # if current_video_process.poll() is not None: # Process already terminated
        #     stderr_output = current_video_process.stderr.read().decode()
        #     print(f"Video player failed to start or exited immediately for {video_path}. Error: {stderr_output}")
        #     current_video_process = None
        # else:
        #     print(f"Looping video '{video_path}' started (PID: {current_video_process.pid}).")
    except FileNotFoundError:
        player_name = config.VIDEO_PLAYER_COMMAND_TEMPLATE[0]
        print(f"ERROR: Video player '{player_name}' not found. Please install it.")
        current_video_process = None
    except Exception as e:
        print(f"Error starting video {video_path}: {e}")
        current_video_process = None

def stop_current_video():
    """Stops the currently playing video, if any."""
    global current_video_process
    if current_video_process:
        print(f"Stopping current video (PID: {current_video_process.pid})...")
        try:
            # Try to terminate gracefully first
            current_video_process.terminate()
            try:
                # Wait for a short period for the process to terminate
                current_video_process.wait(timeout=1.0) 
            except subprocess.TimeoutExpired:
                # If it doesn't terminate, force kill it
                print(f"Video process (PID: {current_video_process.pid}) did not terminate, killing...")
                current_video_process.kill()
                current_video_process.wait() # Ensure it's killed
            # print(f"Video process (PID: {current_video_process.pid}) stopped.")
            # stderr_output = current_video_process.stderr.read().decode()
            # if stderr_output:
            #     print(f"Video player stderr: {stderr_output}")

        except Exception as e:
            print(f"Error stopping video process: {e}")
        finally:
            current_video_process = None
