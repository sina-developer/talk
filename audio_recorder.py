# audio_recorder.py
"""
Handles audio recording using PyAudio.
"""
import pyaudio
import wave
import threading
import os
import sys
import time # For potential small delays if needed, though not currently used heavily

# Import configurations
import config

# --- Module-level variables for recording state ---
# These are managed by the functions in this module.
_recorded_frames_list_bytes = []
_stop_event = threading.Event()
_recording_error = None # Stores any exception from the recording thread

# --- Initialization based on config ---
PYAUDIO_SAMPLE_WIDTH = None # Will be set by _initialize_pyaudio_sample_width

def _initialize_pyaudio_sample_width():
    """Helper to get sample width for PyAudio format. Must be called once."""
    global PYAUDIO_SAMPLE_WIDTH
    if PYAUDIO_SAMPLE_WIDTH is None: # Initialize only once
        p_temp = None
        try:
            # Suppress ALSA messages for this temporary instance
            original_stderr_fd_init = sys.stderr.fileno()
            saved_stderr_fd_init = os.dup(original_stderr_fd_init)
            devnull_fd_init = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull_fd_init, original_stderr_fd_init)
            
            p_temp = pyaudio.PyAudio()
            PYAUDIO_SAMPLE_WIDTH = p_temp.get_sample_size(config.PYAUDIO_FORMAT)
            
            os.dup2(saved_stderr_fd_init, original_stderr_fd_init) # Restore stderr
            os.close(saved_stderr_fd_init)
            os.close(devnull_fd_init)
        except Exception as e:
            print(f"Error initializing PyAudio sample width: {e}")
            # Fallback or raise error if critical
            if p_temp: p_temp.terminate() # Ensure termination if instance created
            raise # Re-raise as this is critical for WAV saving
        finally:
            if p_temp:
                try:
                    p_temp.terminate()
                except Exception: # Suppress errors during cleanup
                    pass
_initialize_pyaudio_sample_width() # Initialize when module is loaded


def _record_worker_pyaudio(samplerate, channels, frames_per_buffer, audio_format, device_index):
    """Worker function to run in a separate thread for recording using PyAudio."""
    global _recorded_frames_list_bytes, _stop_event, _recording_error
    
    _recorded_frames_list_bytes = [] # Clear for new recording
    _recording_error = None    # Reset error state
    pa_instance = None
    stream = None

    # Variables for stderr redirection
    original_stderr_fd = None
    saved_stderr_fd = None
    devnull_fd = None

    try:
        # Suppress ALSA lib messages during PyAudio initialization and stream opening
        original_stderr_fd = sys.stderr.fileno()
        saved_stderr_fd = os.dup(original_stderr_fd)
        devnull_fd = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull_fd, original_stderr_fd)
        
        pa_instance = pyaudio.PyAudio()
        stream = pa_instance.open(format=audio_format,
                                  channels=channels,
                                  rate=samplerate,
                                  input=True,
                                  input_device_index=device_index,
                                  frames_per_buffer=frames_per_buffer)
    finally:
        # Restore stderr as soon as PyAudio initialization is done
        if original_stderr_fd is not None and saved_stderr_fd is not None:
            os.dup2(saved_stderr_fd, original_stderr_fd)
            os.close(saved_stderr_fd)
        if devnull_fd is not None:
            os.close(devnull_fd)

    if not pa_instance or not stream:
        _recording_error = _recording_error or Exception("PyAudio instance or stream failed to initialize.")
        print(f"ERROR in PyAudio recording worker: {_recording_error}")
        if pa_instance: # Terminate if instance was created but stream failed
            try: pa_instance.terminate()
            except Exception: pass
        return # Exit worker if initialization failed

    try:
        print("PyAudio stream opened. Recording audio...")
        while not _stop_event.is_set():
            try:
                data_bytes = stream.read(frames_per_buffer, exception_on_overflow=False)
                _recorded_frames_list_bytes.append(data_bytes)
            except IOError as e:
                pa_input_overflowed_exists = hasattr(pyaudio, 'paInputOverflowed')
                is_overflow_error = (pa_input_overflowed_exists and e.errno == pyaudio.paInputOverflowed) or \
                                    (e.errno == -9988) # Common ALSA/PortAudio overflow indicator
                if is_overflow_error:
                    print("Warning: Input overflowed during recording (PyAudio)!")
                else:
                    # For other IOErrors, print them but continue recording if possible
                    print(f"Warning: IOError during stream.read(): {e}")
        print("Recording stop signal received by worker.")
    except Exception as e:
        print(f"ERROR in PyAudio recording worker thread (during read loop): {e}")
        _recording_error = e
    finally:
        if stream:
            try:
                if stream.is_active(): stream.stop_stream()
                stream.close()
            except Exception: pass # Suppress errors on close during shutdown
        if pa_instance:
            try: pa_instance.terminate()
            except Exception: pass # Suppress errors on terminate
        print("PyAudio recording worker finished.")

def start_recording_thread(output_filename):
    """Starts the recording worker thread."""
    global _stop_event, _recording_error
    
    print(f"Preparing to record to {output_filename} (Mic Index: {config.INPUT_DEVICE_INDEX})...")
    _stop_event.clear()
    _recording_error = None # Reset error status for new recording
    
    recording_thread = threading.Thread(target=_record_worker_pyaudio,
                                       args=(config.SAMPLE_RATE, config.CHANNELS, 
                                             config.FRAMES_PER_BUFFER, config.PYAUDIO_FORMAT, 
                                             config.INPUT_DEVICE_INDEX))
    recording_thread.daemon = True # Allows main program to exit even if thread is somehow stuck
    recording_thread.start()
    return recording_thread

def stop_and_save_recording(thread, output_filename):
    """Signals recording thread to stop, joins it, and saves the recorded audio to a WAV file."""
    global _stop_event, _recorded_frames_list_bytes, _recording_error
    
    print("Sending stop signal to recording thread...")
    _stop_event.set()
    thread.join(timeout=5) # Wait for the thread to finish, with a timeout

    if thread.is_alive():
        print("Warning: Recording thread did not finish cleanly after stop signal.")
        # Potentially try to force close resources if thread is stuck, though risky
        return False
        
    if _recording_error:
        print(f"Recording failed due to an error in the worker: {_recording_error}")
        return False

    if not _recorded_frames_list_bytes:
        print("No audio frames were recorded.")
        return False

    try:
        full_path = os.path.join(config.TEMP_DIR, output_filename)
        if not os.path.exists(config.TEMP_DIR):
            os.makedirs(config.TEMP_DIR, exist_ok=True)

        with wave.open(full_path, 'wb') as wf:
            wf.setnchannels(config.CHANNELS)
            wf.setsampwidth(PYAUDIO_SAMPLE_WIDTH) # Use the module-level initialized width
            wf.setframerate(config.SAMPLE_RATE)
            wf.writeframes(b''.join(_recorded_frames_list_bytes))
        print(f"Recording saved to {full_path}")
        return True
    except Exception as e:
        print(f"ERROR saving recorded audio to {output_filename}: {e}")
        return False
    finally:
        _recorded_frames_list_bytes = [] # Clear frames for next recording

