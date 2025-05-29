print("Python script execution started!")

import requests
print("Requests imported.")
import pyaudio # Replacement for sounddevice
print("PyAudio imported.")
import wave    # Built-in module for WAV files
print("Wave module imported.")
import time
print("Time imported.")
import os
print("OS imported.")
import tempfile
print("Tempfile imported.")
import threading
print("Threading imported.")

# --- Configuration ---
SAMPLE_RATE = 48000  # Set to 48000 Hz as determined by device check
CHANNELS = 1
UPLOAD_URL = 'https://n8n.c-na.dev/webhook-test/talk'
TEMP_DIR = tempfile.gettempdir()
TEMP_RECORDING_FILENAME = "manual_recording_pyaudio.wav"
TEMP_RESPONSE_FILENAME = "response_audio_pyaudio.wav" # Keep .wav for now, will inspect

# PyAudio settings
PYAUDIO_FORMAT = pyaudio.paInt16  # 16-bit audio
FRAMES_PER_BUFFER = 1024        # Chunk size for PyAudio stream processing
INPUT_DEVICE_INDEX = 2          # Set based on your device check (e.g., your USB mic)

print("Configuration variables set.")

# --- Global variables for recording thread ---
_recorded_frames_list_bytes = [] # Will store byte chunks
_stop_event = threading.Event()
_recording_error = None

def _get_pyaudio_sample_width():
    p = pyaudio.PyAudio()
    width = p.get_sample_size(PYAUDIO_FORMAT)
    p.terminate()
    return width

PYAUDIO_SAMPLE_WIDTH = _get_pyaudio_sample_width()

def _record_worker_pyaudio(samplerate, channels, frames_per_buffer, audio_format, device_index):
    """Worker function to run in a separate thread for recording using PyAudio."""
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
                         input_device_index=device_index, # Use specified device index
                         frames_per_buffer=frames_per_buffer)
        print("Debug: PyAudio InputStream opened in worker.")
        while not _stop_event.is_set():
            try:
                data_bytes = stream.read(frames_per_buffer, exception_on_overflow=False)
                _recorded_frames_list_bytes.append(data_bytes)
            except IOError as e:
                if hasattr(pyaudio, 'paInputOverflowed') and e.errno == pyaudio.paInputOverflowed: # Check if paInputOverflowed exists
                    print("Warning: Input overflowed during recording (PyAudio)!")
                elif e.errno == -9988: # Another common overflow error code from PortAudio/ALSA
                    print("Warning: Input overflowed during recording (PyAudio Error -9988)!")
                else:
                    # For other IOErrors, print them and continue or break if severe
                    print(f"Warning: IOError during stream.read(): {e}") 
                    # Depending on severity, you might want to break or set _recording_error
        print("Debug: Stop event received by worker, exiting record loop.")
    except Exception as e:
        print(f"ERROR in PyAudio recording worker thread: {e}")
        _recording_error = e
    finally:
        if stream:
            try:
                if stream.is_active(): # Check if stream is active before stopping
                    stream.stop_stream()
                stream.close()
                print("Debug: PyAudio stream stopped and closed.")
            except Exception as e_close:
                print(f"Error closing PyAudio stream: {e_close}")
        if pa:
            try:
                pa.terminate()
                print("Debug: PyAudio instance terminated.")
            except Exception as e_term:
                print(f"Error terminating PyAudio: {e_term}")
        print("Debug: PyAudio Record worker thread finished.")


def record_audio_manual_pyaudio(filename, samplerate, channels, device_index):
    """Records audio manually using PyAudio, starting and stopping with Enter key."""
    global _stop_event, _recorded_frames_list_bytes, _recording_error

    print(f"Preparing to record to {filename} using PyAudio (Device Index: {device_index})...")
    _stop_event.clear()

    input("Press Enter to START recording...")
    print("Starting PyAudio recording worker thread...")
    
    recording_thread = threading.Thread(target=_record_worker_pyaudio,
                                       args=(samplerate, channels, FRAMES_PER_BUFFER, PYAUDIO_FORMAT, device_index))
    recording_thread.start()
    print("Recording... Press Enter to STOP.")

    input() # Wait for user to press Enter to stop
    
    print("Stop signal received. Finalizing PyAudio recording...")
    _stop_event.set()
    recording_thread.join(timeout=5) # Wait for thread to finish, with a timeout

    if recording_thread.is_alive():
        print("Warning: PyAudio recording thread did not finish cleanly.")
        # Attempt to force close resources if thread is stuck, though this is risky
        # (This part is complex and generally not advised unless absolutely necessary)
        return False
        
    if _recording_error:
        print(f"PyAudio recording failed due to an error in the worker: {_recording_error}")
        return False

    if not _recorded_frames_list_bytes:
        print("No audio frames were recorded (PyAudio).")
        return False

    try:
        print(f"Saving PyAudio recording with {len(_recorded_frames_list_bytes)} byte chunks...")
        wf = wave.open(filename, 'wb')
        wf.setnchannels(channels)
        wf.setsampwidth(PYAUDIO_SAMPLE_WIDTH)
        wf.setframerate(samplerate)
        wf.writeframes(b''.join(_recorded_frames_list_bytes))
        wf.close()
        print(f"PyAudio recording saved to {filename}")
        return True
    except Exception as e:
        print(f"ERROR saving PyAudio recorded audio: {e}")
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
            files = {'audio': (os.path.basename(filepath), f, 'audio/wav')} # Assuming server accepts .wav
            response = requests.post(url, files=files, timeout=30)
            response.raise_for_status() # Raises an HTTPError for bad responses (4XX or 5XX)

        # MODIFICATION: Print Content-Type header
        print(f"Server Response Content-Type: {response.headers.get('Content-Type')}")

        if response.content:
            # Ensure TEMP_DIR exists for response file
            if not os.path.exists(TEMP_DIR):
                os.makedirs(TEMP_DIR, exist_ok=True)
            response_audio_path = os.path.join(TEMP_DIR, TEMP_RESPONSE_FILENAME)
            with open(response_audio_path, 'wb') as out_file:
                out_file.write(response.content)
            print(f"Audio response saved to {response_audio_path}")
            return response_audio_path
        else:
            print("No content in response.")
            return None
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred during upload: {http_err}")
        print(f"Response body: {response.text}") # Print text content of error response
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error uploading audio (RequestException): {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during upload: {e}")
        return None

def play_audio_pyaudio(filename_path):
    """Plays a WAV audio file using PyAudio."""
    if not (filename_path and os.path.exists(filename_path) and os.path.getsize(filename_path) > 0):
        print(f"Audio file not found, empty, or no path provided: {filename_path}")
        return

    wf = None
    pa_play = None
    stream_play = None
    try:
        print(f"Playing {filename_path} using PyAudio...")
        wf = wave.open(filename_path, 'rb')
        pa_play = pyaudio.PyAudio()
        
        print(f"  Response WAV properties: Channels={wf.getnchannels()}, Rate={wf.getframerate()}, Width={wf.getsampwidth()}")

        stream_play = pa_play.open(format=pa_play.get_format_from_width(wf.getsampwidth()),
                                   channels=wf.getnchannels(),
                                   rate=wf.getframerate(),
                                   output=True,
                                   frames_per_buffer=FRAMES_PER_BUFFER)
        
        data_chunk = wf.readframes(FRAMES_PER_BUFFER)
        while data_chunk: # Loop as long as data_chunk is not empty bytes
            stream_play.write(data_chunk)
            data_chunk = wf.readframes(FRAMES_PER_BUFFER)
        
        # Let the stream play out its buffer
        time.sleep(0.2) # Small delay to ensure buffer is played, might need adjustment
        stream_play.stop_stream() 
        print("Playback finished (PyAudio).")

    except wave.Error as wave_err: # Catch wave-specific errors like "file does not start with RIFF id"
        print(f"Error playing audio with PyAudio (wave.Error): {wave_err}")
        print(f"The file '{filename_path}' may not be a valid WAV file or is corrupted.")
    except Exception as e:
        print(f"Error playing audio with PyAudio: {e}")
    finally:
        if stream_play:
            try:
                if stream_play.is_active():
                    stream_play.stop_stream()
                stream_play.close()
                print("Debug: PyAudio playback stream closed.")
            except Exception as e_close:
                print(f"Error closing PyAudio playback stream: {e_close}")
        if pa_play:
            try:
                pa_play.terminate()
                print("Debug: PyAudio playback instance terminated.")
            except Exception as e_term:
                print(f"Error terminating PyAudio playback instance: {e_term}")
        if wf:
            try:
                wf.close()
            except Exception as e_wf:
                 print(f"Error closing wave file: {e_wf}")


print("Functions defined.")

def main_loop():
    print("Main_loop started (PyAudio version).")
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR, exist_ok=True)
        print(f"Created temp directory: {TEMP_DIR}")

    temp_recording_path = os.path.join(TEMP_DIR, TEMP_RECORDING_FILENAME)
    
    try:
        while True:
            print("\n--- New Cycle (PyAudio) ---")
            user_choice = input("Press Enter to Record, or type 'q' to quit: ").lower()
            if user_choice == 'q':
                print("Exiting...")
                break

            if record_audio_manual_pyaudio(temp_recording_path, SAMPLE_RATE, CHANNELS, INPUT_DEVICE_INDEX):
                if os.path.exists(temp_recording_path) and os.path.getsize(temp_recording_path) > 44:
                    print(f"Debug: PyAudio Recording file exists at {temp_recording_path}, proceeding to upload.")
                    response_audio_path = upload_audio(UPLOAD_URL, temp_recording_path)
                    if response_audio_path:
                        play_audio_pyaudio(response_audio_path)
                        
                        # MODIFICATION: File is kept for inspection
                        print(f"DEBUG: Response file kept for inspection: {response_audio_path}")
                        # try:
                        #     os.remove(response_audio_path)
                        #     print(f"Cleaned up response audio: {response_audio_path}")
                        # except OSError as e:
                        #     print(f"Error removing temporary response file: {e}")
                    else:
                        print("No audio response to play or error during upload/saving.")
                    
                    # Clean up the recording file after use
                    try:
                        os.remove(temp_recording_path)
                        print(f"Cleaned up recording: {temp_recording_path}")
                    except OSError as e:
                        print(f"Error removing temporary recording file: {e}")
                else:
                    print(f"PyAudio recording file {temp_recording_path} is missing, empty, or invalid. Skipping upload.")
            else:
                print("PyAudio recording was skipped or failed.")

    except KeyboardInterrupt:
        print("\nExiting application due to KeyboardInterrupt.")
    except Exception as e:
        print(f"An unexpected error occurred in main_loop: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("Main_loop finally block reached (PyAudio version).")
        # Clean up any remaining specific temp files if they exist
        # The response file is intentionally left for debugging now.
        # if os.path.exists(temp_recording_path) and os.path.isfile(temp_recording_path):
        #     try: os.remove(temp_recording_path)
        #     except OSError: pass
        
        # response_audio_final_path = os.path.join(TEMP_DIR, TEMP_RESPONSE_FILENAME)
        # if os.path.exists(response_audio_final_path) and os.path.isfile(response_audio_final_path):
        #     try: os.remove(response_audio_final_path)
        #     except OSError: pass
        print("Script cleanup: Check /tmp for any remaining audio files if needed.")

if __name__ == "__main__":
    print("Script reached __main__ block (PyAudio version).")
    # Add a check for INPUT_DEVICE_INDEX, or make it configurable
    if INPUT_DEVICE_INDEX is None: # Basic check example
        print("Warning: INPUT_DEVICE_INDEX is not set. PyAudio will use the default input device.")
        print("Please run check_audio_devices.py to determine the correct index if you encounter issues.")
    main_loop()