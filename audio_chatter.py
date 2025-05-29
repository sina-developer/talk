print("Python script execution started!") # For debugging startup

import requests
print("Requests imported.")
import sounddevice as sd
print("Sounddevice imported.")
import soundfile as sf
print("Soundfile imported.")
import time
print("Time imported.")
import os
print("OS imported.")
import tempfile
print("Tempfile imported.")
import threading # For manual stop
print("Threading imported.")

# --- Configuration ---
SAMPLE_RATE = 44100  # Standard sample rate
CHANNELS = 1
UPLOAD_URL = 'https://n8n.c-na.dev/webhook-test/talk'
TEMP_DIR = tempfile.gettempdir() # Define TEMP_DIR globally or pass to functions
TEMP_RECORDING_FILENAME = "manual_recording.wav"
TEMP_RESPONSE_FILENAME = "response_audio.wav" # Give a distinct name

# Manual recording settings
CHUNK_FRAMES = 1024  # Number of frames per chunk read from the stream
MAX_RECORDING_DURATION_S = 300  # Optional: A safety max duration (5 minutes)

print("Configuration variables set.")

# --- Global variables for recording thread ---
_recorded_frames_list = []
_stop_event = threading.Event()
_recording_error = None

def _record_worker(samplerate, channels, chunk_frames):
    """Worker function to run in a separate thread for recording."""
    global _recorded_frames_list, _stop_event, _recording_error
    
    _recorded_frames_list = [] # Clear previous recording
    _recording_error = None    # Reset error state

    try:
        print("Debug: Record worker thread started.")
        with sd.InputStream(samplerate=samplerate, channels=channels,
                             dtype='int16', blocksize=chunk_frames) as stream:
            print("Debug: sd.InputStream opened in worker.")
            while not _stop_event.is_set():
                audio_chunk, overflowed = stream.read(chunk_frames)
                if overflowed:
                    print("Warning: Input overflowed during recording!")
                _recorded_frames_list.append(audio_chunk.copy()) # audio_chunk is a NumPy array
            print("Debug: Stop event received by worker, exiting record loop.")
    except Exception as e:
        print(f"ERROR in recording worker thread: {e}")
        _recording_error = e
    finally:
        print("Debug: Record worker thread finished.")

def record_audio_manual(filename, samplerate, channels):
    """Records audio manually, starting and stopping with Enter key."""
    global _stop_event, _recorded_frames_list, _recording_error

    print(f"Preparing to record to {filename}")
    _stop_event.clear() # Reset event for a new recording

    input("Press Enter to START recording...")
    print("Starting recording worker thread...")
    
    recording_thread = threading.Thread(target=_record_worker, args=(samplerate, channels, CHUNK_FRAMES))
    recording_thread.start()
    print("Recording... Press Enter to STOP.")

    # Optional: Implement max duration timeout for input()
    # This is tricky with standard input() which is blocking.
    # For simplicity, we rely on user pressing Enter.
    # Or, the main loop could have a separate timeout mechanism if desired.

    input() # Wait for user to press Enter to stop
    
    print("Stop signal received. Finalizing recording...")
    _stop_event.set()
    recording_thread.join(timeout=5) # Wait for thread to finish, with a timeout

    if recording_thread.is_alive():
        print("Warning: Recording thread did not finish cleanly after stop signal.")
        return False
        
    if _recording_error:
        print(f"Recording failed due to an error in the worker: {_recording_error}")
        return False

    if not _recorded_frames_list:
        print("No audio frames were recorded.")
        return False

    try:
        print(f"Saving recording with {_len_recorded_frames_list()} chunks...")
        with sf.SoundFile(filename, mode='w', samplerate=samplerate, 
                          channels=channels, subtype='PCM_16') as audio_file:
            for chunk in _recorded_frames_list:
                audio_file.write(chunk) # soundfile handles NumPy array chunks directly
        print(f"Recording saved to {filename}")
        return True
    except Exception as e:
        print(f"ERROR saving recorded audio: {e}")
        return False
    finally:
        _recorded_frames_list = [] # Clear frames for next recording

def _len_recorded_frames_list(): # Helper to avoid issues if _recorded_frames_list is None or not list
    global _recorded_frames_list
    return len(_recorded_frames_list) if isinstance(_recorded_frames_list, list) else 0


def upload_audio(url, filepath):
    """Uploads an audio file to the specified URL and saves the response."""
    print(f"Uploading {filepath} to {url}...")
    if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
        print(f"Error: File {filepath} does not exist or is empty. Skipping upload.")
        return None
    try:
        with open(filepath, 'rb') as f:
            files = {'audio': (os.path.basename(filepath), f, 'audio/wav')}
            response = requests.post(url, files=files, timeout=30)
            response.raise_for_status()

        if response.content:
            response_audio_path = os.path.join(TEMP_DIR, TEMP_RESPONSE_FILENAME)
            with open(response_audio_path, 'wb') as out_file:
                out_file.write(response.content)
            print(f"Audio response saved to {response_audio_path}")
            return response_audio_path
        else:
            print("No content in response.")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error uploading audio: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during upload: {e}")
        return None

def play_audio(filename_path):
    """Plays an audio file."""
    if filename_path and os.path.exists(filename_path) and os.path.getsize(filename_path) > 0:
        try:
            print(f"Playing {filename_path}...")
            data, fs = sf.read(filename_path, dtype='float32')
            sd.play(data, fs)
            sd.wait()
            print("Playback finished.")
        except Exception as e:
            print(f"Error playing audio: {e}")
    else:
        print(f"Response audio file not found, empty, or no response to play: {filename_path}")

print("Functions defined.")

def main_loop():
    """Main loop to record, upload, receive, and play audio."""
    print("Main_loop started.")
    # Ensure TEMP_DIR exists
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR, exist_ok=True)
        print(f"Created temp directory: {TEMP_DIR}")

    temp_recording_path = os.path.join(TEMP_DIR, TEMP_RECORDING_FILENAME)
    
    try:
        while True:
            print("\n--- New Cycle ---")
            user_choice = input("Press Enter to Record, or type 'q' to quit: ").lower()
            if user_choice == 'q':
                print("Exiting...")
                break

            if record_audio_manual(temp_recording_path, SAMPLE_RATE, CHANNELS):
                if os.path.exists(temp_recording_path) and os.path.getsize(temp_recording_path) > 44: # Check if file exists and has more than WAV header
                    print(f"Debug: Recording file exists at {temp_recording_path}, proceeding to upload.")
                    response_audio_path = upload_audio(UPLOAD_URL, temp_recording_path)
                    if response_audio_path:
                        play_audio(response_audio_path)
                        # Clean up response audio
                        try:
                            os.remove(response_audio_path)
                            print(f"Cleaned up response audio: {response_audio_path}")
                        except OSError as e:
                            print(f"Error removing temporary response file: {e}")
                    else:
                        print("No audio response to play or error during upload.")
                    # Clean up recording
                    try:
                        os.remove(temp_recording_path)
                        print(f"Cleaned up recording: {temp_recording_path}")
                    except OSError as e:
                        print(f"Error removing temporary recording file: {e}")
                else:
                    print(f"Recording file {temp_recording_path} is missing, empty, or invalid. Skipping upload.")
            else:
                print("Recording was skipped or failed.")

    except KeyboardInterrupt:
        print("\nExiting application due to KeyboardInterrupt.")
    except Exception as e:
        print(f"An unexpected error occurred in main_loop: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("Main_loop finally block reached.")
        # Clean up any remaining specific temp files if they exist
        if os.path.exists(temp_recording_path) and os.path.isfile(temp_recording_path):
            try:
                os.remove(temp_recording_path)
                print(f"Cleaned up lingering recording: {temp_recording_path}")
            except OSError as e:
                print(f"Error removing temp recording on exit: {e}")
        
        response_audio_final_path = os.path.join(TEMP_DIR, TEMP_RESPONSE_FILENAME)
        if os.path.exists(response_audio_final_path) and os.path.isfile(response_audio_final_path):
            try:
                os.remove(response_audio_final_path)
                print(f"Cleaned up lingering response audio: {response_audio_final_path}")
            except OSError as e:
                print(f"Error removing temp response audio on exit: {e}")
        print("Script cleanup attempt done. Exiting.")

if __name__ == "__main__":
    print("Script reached __main__ block.")
    main_loop()