print("Python script execution started!")

import requests
print("Requests imported.")
import pyaudio
print("PyAudio imported.")
import wave
print("Wave module imported.")
import time
print("Time imported.")
import os
print("OS imported.")
import tempfile
print("Tempfile imported.")
import threading
print("Threading imported.")
import subprocess # For calling external players
print("Subprocess imported.")

# --- Configuration ---
SAMPLE_RATE = 48000
CHANNELS = 1
UPLOAD_URL = 'https://n8n.c-na.dev/webhook-test/talk'
TEMP_DIR = tempfile.gettempdir()
TEMP_RECORDING_FILENAME = "manual_recording_pyaudio.wav"
TEMP_RESPONSE_FILENAME = "response_audio.mp3" # MODIFIED: Save as .mp3

PYAUDIO_FORMAT = pyaudio.paInt16
FRAMES_PER_BUFFER = 1024
INPUT_DEVICE_INDEX = 2 # As determined previously

print("Configuration variables set.")

_recorded_frames_list_bytes = []
_stop_event = threading.Event()
_recording_error = None

def _get_pyaudio_sample_width():
    p = pyaudio.PyAudio()
    width = p.get_sample_size(PYAUDIO_FORMAT)
    p.terminate()
    return width

PYAUDIO_SAMPLE_WIDTH = _get_pyaudio_sample_width()

def _record_worker_pyaudio(samplerate, channels, frames_per_buffer, audio_format, device_index):
    global _recorded_frames_list_bytes, _stop_event, _recording_error
    _recorded_frames_list_bytes = []
    _recording_error = None
    pa = None
    stream = None
    try:
        print("Debug: PyAudio Record worker thread started.")
        pa = pyaudio.PyAudio()
        stream = pa.open(format=audio_format,
                         channels=channels,
                         rate=samplerate,
                         input=True,
                         input_device_index=device_index,
                         frames_per_buffer=frames_per_buffer)
        print("Debug: PyAudio InputStream opened in worker.")
        while not _stop_event.is_set():
            try:
                data_bytes = stream.read(frames_per_buffer, exception_on_overflow=False)
                _recorded_frames_list_bytes.append(data_bytes)
            except IOError as e:
                # Basic overflow check, specific error codes can be OS/backend dependent
                if e.errno == -9988 or (hasattr(pyaudio, 'paInputOverflowed') and e.errno == pyaudio.paInputOverflowed):
                    print("Warning: Input overflowed during recording (PyAudio)!")
                else:
                    print(f"Warning: IOError during stream.read(): {e}")
        print("Debug: Stop event received by worker, exiting record loop.")
    except Exception as e:
        print(f"ERROR in PyAudio recording worker thread: {e}")
        _recording_error = e
    finally:
        if stream:
            try:
                if stream.is_active(): stream.stop_stream()
                stream.close()
                print("Debug: PyAudio stream stopped and closed.")
            except Exception as e_close: print(f"Error closing PyAudio stream: {e_close}")
        if pa:
            try: pa.terminate()
            except Exception as e_term: print(f"Error terminating PyAudio: {e_term}")
        print("Debug: PyAudio Record worker thread finished.")

def record_audio_manual_pyaudio(filename, samplerate, channels, device_index):
    global _stop_event, _recorded_frames_list_bytes, _recording_error
    print(f"Preparing to record to {filename} using PyAudio (Device Index: {device_index})...")
    _stop_event.clear()
    input("Press Enter to START recording...")
    print("Starting PyAudio recording worker thread...")
    recording_thread = threading.Thread(target=_record_worker_pyaudio,
                                       args=(samplerate, channels, FRAMES_PER_BUFFER, PYAUDIO_FORMAT, device_index))
    recording_thread.start()
    print("Recording... Press Enter to STOP.")
    input()
    print("Stop signal received. Finalizing PyAudio recording...")
    _stop_event.set()
    recording_thread.join(timeout=5)
    if recording_thread.is_alive():
        print("Warning: PyAudio recording thread did not finish cleanly.")
        return False
    if _recording_error:
        print(f"PyAudio recording failed: {_recording_error}")
        return False
    if not _recorded_frames_list_bytes:
        print("No audio frames were recorded (PyAudio).")
        return False
    try:
        print(f"Saving PyAudio recording with {len(_recorded_frames_list_bytes)} byte chunks...")
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(PYAUDIO_SAMPLE_WIDTH)
            wf.setframerate(samplerate)
            wf.writeframes(b''.join(_recorded_frames_list_bytes))
        print(f"PyAudio recording saved to {filename}")
        return True
    except Exception as e:
        print(f"ERROR saving PyAudio recorded audio: {e}")
        return False
    finally:
        _recorded_frames_list_bytes = []

def upload_audio(url, filepath):
    print(f"Uploading {filepath} to {url}...")
    if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
        print(f"Error: File {filepath} does not exist or is empty. Skipping upload.")
        return None
    try:
        with open(filepath, 'rb') as f:
            files = {'audio': (os.path.basename(filepath), f, 'audio/wav')}
            response = requests.post(url, files=files, timeout=30)
            response.raise_for_status()
        print(f"Server Response Content-Type: {response.headers.get('Content-Type')}") # Keep this for debugging
        if response.content:
            if not os.path.exists(TEMP_DIR): os.makedirs(TEMP_DIR, exist_ok=True)
            response_audio_path = os.path.join(TEMP_DIR, TEMP_RESPONSE_FILENAME) # Uses new .mp3 extension
            with open(response_audio_path, 'wb') as out_file:
                out_file.write(response.content)
            print(f"Audio response saved to {response_audio_path}")
            return response_audio_path
        else:
            print("No content in response.")
            return None
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred during upload: {http_err}")
        if hasattr(response, 'text'): print(f"Response body: {response.text[:500]}") # Print partial text
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error uploading audio (RequestException): {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during upload: {e}")
        return None

# MODIFIED: Replaced play_audio_pyaudio with play_audio_external
def play_audio_external(filename_path):
    """Plays an audio file using an external player (ffplay)."""
    if not (filename_path and os.path.exists(filename_path) and os.path.getsize(filename_path) > 0):
        print(f"Audio file not found, empty, or no path provided: {filename_path}")
        return

    print(f"Attempting to play {filename_path} using ffplay...")
    try:
        # -autoexit: ffplay quits when playback is finished
        # -nodisp: No graphical display window (audio only)
        # -loglevel error: Show only errors from ffplay
        command = ['ffplay', '-autoexit', '-nodisp', '-loglevel', 'error', filename_path]
        subprocess.run(command, check=True) # check=True will raise CalledProcessError on non-zero exit
        print("Playback finished (ffplay).")
    except subprocess.CalledProcessError as e:
        print(f"Error during ffplay playback (CalledProcessError): {e}")
        # stderr might be empty if ffplay's loglevel is high, but good to check
        if e.stderr: print(f"ffplay stderr: {e.stderr.decode('utf-8', errors='ignore')}")
    except FileNotFoundError:
        print("Error: 'ffplay' command not found. Please ensure FFmpeg (which includes ffplay) is installed and in your system's PATH.")
        print("You can usually install it on Debian/Ubuntu/Raspberry Pi OS with: sudo apt-get install ffmpeg")
    except Exception as e:
        print(f"An unexpected error occurred during playback with ffplay: {e}")

print("Functions defined.")

def main_loop():
    print("Main_loop started (PyAudio version with ffplay).")
    if not os.path.exists(TEMP_DIR): os.makedirs(TEMP_DIR, exist_ok=True)
    temp_recording_path = os.path.join(TEMP_DIR, TEMP_RECORDING_FILENAME)
    
    try:
        while True:
            print("\n--- New Cycle (PyAudio / ffplay) ---")
            user_choice = input("Press Enter to Record, or type 'q' to quit: ").lower()
            if user_choice == 'q': print("Exiting..."); break

            if record_audio_manual_pyaudio(temp_recording_path, SAMPLE_RATE, CHANNELS, INPUT_DEVICE_INDEX):
                if os.path.exists(temp_recording_path) and os.path.getsize(temp_recording_path) > 44:
                    print(f"Debug: PyAudio Recording file exists at {temp_recording_path}, proceeding to upload.")
                    response_audio_path = upload_audio(UPLOAD_URL, temp_recording_path)
                    if response_audio_path:
                        play_audio_external(response_audio_path) # MODIFIED: Call new playback function
                        try: # Clean up response audio
                            os.remove(response_audio_path)
                            print(f"Cleaned up response audio: {response_audio_path}")
                        except OSError as e: print(f"Error removing temporary response file: {e}")
                    else: print("No audio response to play or error during upload/saving.")
                    try: # Clean up recording
                        os.remove(temp_recording_path)
                        print(f"Cleaned up recording: {temp_recording_path}")
                    except OSError as e: print(f"Error removing temporary recording file: {e}")
                else: print(f"PyAudio recording file {temp_recording_path} is missing, empty, or invalid. Skipping upload.")
            else: print("PyAudio recording was skipped or failed.")
    except KeyboardInterrupt: print("\nExiting application due to KeyboardInterrupt.")
    except Exception as e:
        print(f"An unexpected error occurred in main_loop: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("Main_loop finally block reached.")
        print("Script cleanup: Check /tmp for any lingering audio files if needed.")

if __name__ == "__main__":
    print("Script reached __main__ block.")
    if INPUT_DEVICE_INDEX is None: # Basic check example
        print("Warning: INPUT_DEVICE_INDEX is not set. PyAudio will use the default input device.")
    main_loop()