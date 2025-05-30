# audio_player.py
"""
Handles playback of audio files using an external player (e.g., ffplay).
"""
import subprocess
import os
import config # Assuming EXTERNAL_PLAYER_COMMAND is in config.py

def play_audio_external(filename_path):
    """
    Plays an audio file using the external player command defined in config.
    Args:
        filename_path (str): The full path to the audio file to be played.
    """
    if not (filename_path and os.path.exists(filename_path) and os.path.getsize(filename_path) > 0):
        print(f"Audio file for playback not found, empty, or path invalid: {filename_path}")
        return

    player_cmd_base = config.EXTERNAL_PLAYER_COMMAND # e.g., ['ffplay', '-autoexit', '-nodisp', '-loglevel', 'error']
    command_to_run = player_cmd_base + [filename_path]

    print(f"Attempting to play {filename_path} using: {' '.join(command_to_run)}...")
    
    player_process_ran = False
    try:
        # Ensure ffplay doesn't try to read from our script's stdin
        # We are capturing output to see potential errors from ffplay itself.
        process = subprocess.run(command_to_run, 
                                 stdin=subprocess.DEVNULL, # Prevent ffplay from consuming stdin
                                 capture_output=True, # Capture stdout/stderr from ffplay
                                 text=True,           # Decode stdout/stderr as text
                                 check=True)           # Raise CalledProcessError on non-zero exit
        player_process_ran = True
        print("Playback finished (external player).")
        # If ffplay -loglevel error is used, stdout is usually empty.
        # Stderr might contain info even on success if loglevel is higher.
        # if process.stdout:
        #     print(f"Player stdout: {process.stdout.strip()}")
        # if process.stderr:
        #     print(f"Player stderr: {process.stderr.strip()}")
            
    except subprocess.CalledProcessError as e:
        player_process_ran = True # It ran, but failed
        print(f"Error during external player playback (CalledProcessError): {e}")
        if e.stdout:
            print(f"Player stdout on error: {e.stdout.strip()}")
        if e.stderr:
            print(f"Player stderr on error: {e.stderr.strip()}")
    except FileNotFoundError:
        player_name = player_cmd_base[0]
        print(f"Error: '{player_name}' command not found. Please ensure it is installed and in your system's PATH.")
        if player_name == "ffplay":
            print("You can usually install ffplay (part of FFmpeg) on Debian/Ubuntu/Raspberry Pi OS with:")
            print("  sudo apt-get update && sudo apt-get install ffmpeg")
    except Exception as e:
        print(f"An unexpected error occurred during playback with external player: {e}")
    finally:
        # Attempt to restore terminal settings, especially if ffplay was run.
        # This is a common fix for "frozen" terminals after external TUI/media apps.
        if player_process_ran or os.name == 'posix': # os.name == 'posix' for Linux/macOS
            print("Attempting to restore terminal settings with 'stty sane'...")
            try:
                # Use shell=True for simple commands like this, or pass as a list.
                # We don't need to check output here, just attempt to run it.
                subprocess.run(['stty', 'sane'], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print("'stty sane' command executed.")
            except FileNotFoundError:
                print("Warning: 'stty' command not found. Cannot restore terminal settings automatically.")
            except Exception as e_stty:
                print(f"Warning: Error trying to run 'stty sane': {e_stty}")
