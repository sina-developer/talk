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
SAMPLE_RATE = 44100  # Standard sample rate
CHANNELS = 1
UPLOAD_URL = 'https://n8n.c-na.dev/webhook-test/talk'
TEMP_DIR = tempfile.gettempdir()
TEMP_RECORDING_FILENAME = "manual_recording_pyaudio.wav"
TEMP_RESPONSE_FILENAME = "response_audio_pyaudio.wav"

# PyAudio settings
PYAUDIO_FORMAT = pyaudio.paInt16  # 16-bit audio
FRAMES_PER_BUFFER = 1024        # Chunk size for PyAudio stream processing

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

def _record_worker_pyaudio(samplerate, channels, frames_per_buffer, audio_format):
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
                         frames_per_buffer=frames_per_buffer)
        print("Debug: PyAudio InputStream opened in worker.")
        while not _stop_event.is_set():
            try:
                data_bytes = stream.read(frames_per_buffer, exception_on_overflow=False)
                _recorded_frames_list_bytes.append(data_bytes)
            except IOError as e:
                if e.errno == pyaudio.paInputOverflowed:
                    print("Warning: Input overflowed during recording (PyAudio)!")
                else:
                    raise # Re-raise other IOErrors
        print("Debug: Stop event received by worker, exiting record loop.")
    except Exception as e:
        print(f"ERROR in PyAudio recording worker thread: {e}")
        _recording_error = e
    finally:
        if stream:
            try:
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


def record_audio_manual_pyaudio(filename, samplerate, channels):
    """Records audio manually using PyAudio, starting and stopping with Enter key."""
    global _stop_event, _recorded_frames_list_bytes, _recording_error

    print(f"Preparing to record to {filename} using PyAudio...")
    _stop_event.clear()

    input("Press Enter to START recording...")
    print("Starting PyAudio recording worker thread...")
    
    recording_thread = threading.Thread(target=_record_worker_pyaudio,
                                       args=(samplerate, channels, FRAMES_PER_BUFFER, PYAUDIO_FORMAT))
    recording_thread.start()
    print("Recording... Press Enter to STOP.")

    input() # Wait for user to press Enter to stop
    
    print("Stop signal received. Finalizing PyAudio recording...")
    _stop_event.set()
    recording_thread.join(timeout=5)

    if recording_thread.is_alive():
        print("Warning: PyAudio recording thread did not finish cleanly.")
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
        wf.setsampwidth(PYAUDIO_SAMPLE_WIDTH) # Use pre-calculated or get from PyAudio instance
        wf.setframerate(samplerate)
        wf.writeframes(b''.join(_recorded_frames_list_bytes))
        wf.close()
        print(f"PyAudio recording saved to {filename}")
        return True
    except Exception as e:
        print(f"ERROR saving PyAudio recorded audio: {e}")
        return False
    finally:
        _recorded_frames_list_bytes = []


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
        stream_play = pa_play.open(format=pa_play.get_format_from_width(wf.getsampwidth()),
                                   channels=wf.getnchannels(),
                                   rate=wf.getframerate(),
                                   output=True,
                                   frames_per_buffer=FRAMES_PER_BUFFER)
        
        data = wf.readframes(FRAMES_PER_BUFFER)
        while data: # Ensure data is not empty bytes
            stream_play.write(data)
            data = wf.readframes(FRAMES_PER_BUFFER)
        
        stream_play.stop_stream() # Ensure it finishes outputting buffer
        print("Playback finished (PyAudio).")

    except Exception as e:
        print(f"Error playing audio with PyAudio: {e}")
    finally:
        if stream_play:
            try:
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

            if record_audio_manual_pyaudio(temp_recording_path, SAMPLE_RATE, CHANNELS):
                # Check file size (WAV header is 44 bytes, so > 44 means some data)
                if os.path.exists(temp_recording_path) and os.path.getsize(temp_recording_path) > 44:
                    print(f"Debug: PyAudio Recording file exists at {temp_recording_path}, proceeding to upload.")
                    response_audio_path = upload_audio(UPLOAD_URL, temp_recording_path)
                    if response_audio_path:
                        play_audio_pyaudio(response_audio_path)
                        try:
                            os.remove(response_audio_path)
                            print(f"Cleaned up response audio: {response_audio_path}")
                        except OSError as e:
                            print(f"Error removing temporary response file: {e}")
                    else:
                        print("No audio response to play or error during upload.")
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
        if os.path.exists(temp_recording_path) and os.path.isfile(temp_recording_path):
            try:
                os.remove(temp_recording_path)
                print(f"Cleaned up lingering recording: {temp_recording_path}")
            except OSError: pass # Ignore errors on final cleanup
        
        response_audio_final_path = os.path.join(TEMP_DIR, TEMP_RESPONSE_FILENAME)
        if os.path.exists(response_audio_final_path) and os.path.isfile(response_audio_final_path):
            try:
                os.remove(response_audio_final_path)
                print(f"Cleaned up lingering response audio: {response_audio_final_path}")
            except OSError: pass
        print("Script cleanup attempt done. Exiting.")

if __name__ == "__main__":
    print("Script reached __main__ block (PyAudio version).")
    main_loop()