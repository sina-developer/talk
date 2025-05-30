# audio_player.py
"""
Handles playback of audio files using an external player (e.g., ffplay).
"""
import subprocess
import os
import config

def play_audio_external(filename_path):
    """
    Plays an audio file using the external player command defined in config.
    Args:
        filename_path (str): The full path to the audio file to be played.
    """
    if not (filename_path and os.path.exists(filename_path) and os.path.getsize(filename_path) > 0):
        print(f"Audio file for playback not found, empty, or path invalid: {filename_path}")
        return

    print(f"Attempting to play {filename_path} using: {' '.join(config.EXTERNAL_PLAYER_COMMAND)}...")
    
    command_to_run = config.EXTERNAL_PLAYER_COMMAND + [filename_path]

    try:
        # Using Popen for non-blocking if needed, but run with check=True is fine for sequential playback.
        # For ffplay with -autoexit, it will block until playback finishes or an error occurs.
        process = subprocess.run(command_to_run, check=True, capture_output=True, text=True)
        print("Playback finished (external player).")
        if process.stdout:
            print(f"Player stdout: {process.stdout}")
        # ffplay with -loglevel error should mostly output to stderr on error
        # if process.stderr: 
        #     print(f"Player stderr: {process.stderr}") # Can be noisy if loglevel isn't 'error'
            
    except subprocess.CalledProcessError as e:
        print(f"Error during external player playback (CalledProcessError): {e}")
        if e.stdout:
            print(f"Player stdout on error: {e.stdout}")
        if e.stderr:
            print(f"Player stderr on error: {e.stderr}")
    except FileNotFoundError:
        player_name = config.EXTERNAL_PLAYER_COMMAND[0]
        print(f"Error: '{player_name}' command not found. Please ensure it is installed and in your system's PATH.")
        if player_name == "ffplay":
            print("You can usually install ffplay (part of FFmpeg) on Debian/Ubuntu/Raspberry Pi OS with:")
            print("  sudo apt-get update && sudo apt-get install ffmpeg")
        elif player_name == "mpg123":
            print("You can usually install mpg123 with: sudo apt-get install mpg123")
    except Exception as e:
        print(f"An unexpected error occurred during playback with external player: {e}")

