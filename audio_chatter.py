import requests
import pyaudio
import wave
import time
import os
import tempfile
import threading
import subprocess

# --- Configuration ---
SAMPLE_RATE = 48000
CHANNELS = 1
UPLOAD_URL = 'https://n8n.c-na.dev/webhook/talk' # Target URL for audio upload
TEMP_DIR = tempfile.gettempdir()
TEMP_RECORDING_FILENAME = "manual_recording_pyaudio.wav"
TEMP_RESPONSE_FILENAME = "response_audio.mp3" # Assuming MP3 response based on previous findings

# PyAudio settings
PYAUDIO_FORMAT = pyaudio.paInt16  # 16-bit audio
FRAMES_PER_BUFFER = 1024        # Chunk size for PyAudio stream processing
INPUT_DEVICE_INDEX = 2          # Set based on your device check (e.g., your USB mic)

# --- Global variables for recording thread ---
_recorded_frames_list_bytes = []
_stop_event = threading.Event()
_recording_error = None

def _get_pyaudio_sample_width():
    """Helper to get sample width for PyAudio format."""
    p = pyaudio.PyAudio()
    try:
        width = p.get_sample_size(PYAUDIO_FORMAT)
    finally:
        p.terminate()
    return width

PYAUDIO_SAMPLE_WIDTH = _get_pyaudio_sample_width()

def _record_worker_pyaudio(samplerate, channels, frames_per_buffer, audio_format, device_index):
    """Worker function to run in a separate thread for recording using PyAudio."""
    global _recorded_frames_list_bytes, _stop_event, _recording_error
    
    _recorded_frames_list_bytes = []
    _recording_error = None
    pa_instance = None
    stream = None

    try:
        pa_instance = pyaudio.PyAudio()
        stream = pa_instance.open(format=audio_format,
                                  channels=channels,
                                  rate=samplerate,
                                  input=True,
                                  input_device_index=device_index,
                                  frames_per_buffer=frames_per_buffer)
        print("PyAudio stream opened for recording.")
        while not _stop_event.is_set():
            try:
                data_bytes = stream.read(frames_per_buffer, exception_on_overflow=False)
                _recorded_frames_list_bytes.append(data_bytes)
            except IOError as e:
                # Basic overflow check, specific error codes can be OS/backend dependent
                # Common PortAudio/ALSA overflow error codes for PyAudio
                pa_input_overflowed_exists = hasattr(pyaudio, 'paInputOverflowed')
                is_overflow_error = (pa_input_overflowed_exists and e.errno == pyaudio.paInputOverflowed) or \
                                    (e.errno == -9988) # Another common ALSA/PortAudio overflow indicator
                if is_overflow_error:
                    print("Warning: Input overflowed during recording (PyAudio)!")
                else:
                    print(f"Warning: IOError during stream.read(): {e}")
        print("Recording stop signal received by worker.")
    except Exception as e:
        print(f"ERROR in PyAudio recording worker thread: {e}")
        _recording_error = e
    finally:
        if stream:
            try:
                if stream.is_active(): stream.stop_stream()
                stream.close()
            except Exception as e_close: print(f"Error closing PyAudio stream: {e_close}")
        if pa_instance:
            try: pa_instance.terminate()
            except Exception as e_term: print(f"Error terminating PyAudio: {e_term}")
        print("PyAudio recording worker finished.")

def record_audio_manual_pyaudio(filename, samplerate, channels, device_index):
    """Records audio manually using PyAudio, starting and stopping with Enter key."""
    global _stop_event, _recorded_frames_list_bytes, _recording_error

    print(f"Preparing to record to {filename} (Device Index: {device_index})...")
    _stop_event.clear()

    input("Press Enter to START recording...")
    
    recording_thread = threading.Thread(target=_record_worker_pyaudio,
                                       args=(samplerate, channels, FRAMES_PER_BUFFER, PYAUDIO_FORMAT, device_index))
    print("Recording... Press Enter to STOP.")
    recording_thread.start()

    input() # Wait for user to press Enter to stop
    
    print("Stop signal sent. Finalizing recording...")
    _stop_event.set()
    recording_thread.join(timeout=5) # Wait for thread to finish

    if recording_thread.is_alive():
        print("Warning: PyAudio recording thread did not finish cleanly.")
        return False
        
    if _recording_error:
        print(f"PyAudio recording failed: {_recording_error}")
        return False

    if not _recorded_frames_list_bytes:
        print("No audio frames were recorded.")
        return False

    try:
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(PYAUDIO_SAMPLE_WIDTH)
            wf.setframerate(samplerate)
            wf.writeframes(b''.join(_recorded_frames_list_bytes))
        print(f"Recording saved to {filename}")
        return True
    except Exception as e:
        print(f"ERROR saving recorded audio: {e}")
        return False
    finally:
        _recorded_frames_list_bytes = [] # Clear frames for next recording

def upload_audio(url, filepath):
    """Uploads an audio file to the specified URL and saves the response."""
    print(f"Uploading {filepath} to {url}...")
    if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
        print(f"Error: File {filepath} does not exist or is empty. Skipping upload.")
        return None
    try:
        with open(filepath, 'rb') as f:
            files = {'audio': (os.path.basename(filepath), f, 'audio/wav')} # Server might expect WAV despite client recording
            response = requests.post(url, files=files, timeout=30)
            response.raise_for_status()

        print(f"Server Response Content-Type: {response.headers.get('Content-Type')}") # Useful for debugging response

        if response.content:
            if not os.path.exists(TEMP_DIR):
                os.makedirs(TEMP_DIR, exist_ok=True)
            response_audio_path = os.path.join(TEMP_DIR, TEMP_RESPONSE_FILENAME)
            with open(response_audio_path, 'wb') as out_file:
                out_file.write(response.content)
            print(f"Audio response saved to {response_audio_path}")
            return response_audio_path
        else:
            print("No content in server response.")
            return None
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred during upload: {http_err}")
        if hasattr(response, 'text'): print(f"Response body: {response.text[:500]}...")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error uploading audio (RequestException): {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during upload: {e}")
        return None

def play_audio_external(filename_path):
    """Plays an audio file using an external player (ffplay)."""
    if not (filename_path and os.path.exists(filename_path) and os.path.getsize(filename_path) > 0):
        print(f"Audio file for playback not found, empty, or path invalid: {filename_path}")
        return

    print(f"Attempting to play {filename_path} using ffplay...")
    try:
        command = ['ffplay', '-autoexit', '-nodisp', '-loglevel', 'error', filename_path]
        subprocess.run(command, check=True)
        print("Playback finished (ffplay).")
    except subprocess.CalledProcessError as e:
        print(f"Error during ffplay playback: {e}")
        if e.stderr: print(f"ffplay stderr: {e.stderr.decode('utf-8', errors='ignore')}")
    except FileNotFoundError:
        print("Error: 'ffplay' command not found. Please ensure FFmpeg (which includes ffplay) is installed and in your PATH.")
        print("You can usually install it on Debian/Ubuntu/Raspberry Pi OS with: sudo apt-get install ffmpeg")
    except Exception as e:
        print(f"An unexpected error occurred during playback with ffplay: {e}")

def main_loop():
    print("Starting main loop (PyAudio version with ffplay)...")
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

            if record_audio_manual_pyaudio(temp_recording_path, SAMPLE_RATE, CHANNELS, INPUT_DEVICE_INDEX):
                # WAV header is 44 bytes, check if significantly larger
                if os.path.exists(temp_recording_path) and os.path.getsize(temp_recording_path) > 44:
                    response_audio_path = upload_audio(UPLOAD_URL, temp_recording_path)
                    if response_audio_path:
                        play_audio_external(response_audio_path)
                        try: # Clean up response audio
                            os.remove(response_audio_path)
                            print(f"Cleaned up response audio: {response_audio_path}")
                        except OSError as e: print(f"Error removing temporary response file: {e}")
                    else:
                        print("No audio response to play or error during upload/saving.")
                    
                    try: # Clean up recording
                        os.remove(temp_recording_path)
                        print(f"Cleaned up recording: {temp_recording_path}")
                    except OSError as e: print(f"Error removing temporary recording file: {e}")
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
        print("Application shutting down. Check /tmp for any lingering audio files if necessary.")

if __name__ == "__main__":
    if INPUT_DEVICE_INDEX is None: # Basic check, could be more sophisticated
        print("Warning: INPUT_DEVICE_INDEX is not explicitly set. PyAudio will use the default input device.")
        print("If you encounter recording issues, run check_audio_devices.py to find the correct index.")
    main_loop()