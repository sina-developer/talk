print("Python script execution started!") # <-- ADDED THIS LINE

import requests
print("Requests imported.") # <-- ADDED THIS LINE
import sounddevice as sd
print("Sounddevice imported.") # <-- ADDED THIS LINE
import soundfile as sf
print("Soundfile imported.") # <-- ADDED THIS LINE
import time
print("Time imported.") # <-- ADDED THIS LINE
import os
print("OS imported.") # <-- ADDED THIS LINE
import tempfile
print("Tempfile imported.") # <-- ADDED THIS LINE
import numpy as np
print("Numpy imported.") # <-- ADDED THIS LINE

# Configuration
# RECORD_SECONDS = 5 # Kept for reference, but VAD is primary
SAMPLE_RATE = 44100  # Standard sample rate
CHANNELS = 1
UPLOAD_URL = 'https://n8n.c-na.dev/webhook-test/talk' # User's original URL
TEMP_RECORDING_FILENAME = "temp_recording.wav"
TEMP_RESPONSE_FILENAME = "temp_response.wav"

# VAD Configurations
CHUNK_DURATION_MS = 50  # Duration of each audio chunk in milliseconds
SILENCE_THRESHOLD = 0.008  # RMS amplitude threshold for silence (needs tuning)
MIN_SILENCE_DURATION_MS = 1500 # Silence duration in ms to trigger recording stop
MAX_RECORDING_DURATION_S = 30  # Maximum recording time in seconds
PRE_SPEECH_BUFFER_MS = 200 # Keep some audio before speech starts

print("Configuration variables set.") # <-- ADDED THIS LINE

def record_audio_vad(filename, samplerate, channels,
                     chunk_duration_ms=CHUNK_DURATION_MS,
                     silence_threshold=SILENCE_THRESHOLD,
                     min_silence_duration_ms=MIN_SILENCE_DURATION_MS,
                     max_recording_duration_s=MAX_RECORDING_DURATION_S,
                     pre_speech_buffer_ms=PRE_SPEECH_BUFFER_MS):
    """Records audio from the microphone, stopping when silence is detected."""
    print(f"Debug: record_audio_vad called with filename: {filename}")

    chunk_frames = int(samplerate * chunk_duration_ms / 1000)
    min_silence_chunks = min_silence_duration_ms // chunk_duration_ms
    pre_speech_chunks = pre_speech_buffer_ms // chunk_duration_ms
    max_chunks = (max_recording_duration_s * 1000) // chunk_duration_ms

    print(f"Listening... Speak into the microphone. Recording will stop after {min_silence_duration_ms/1000:.1f}s of silence.")
    print(f"(Silence threshold: {silence_threshold}, Max duration: {max_recording_duration_s}s)")
    print(f"Debug: chunk_frames={chunk_frames}, min_silence_chunks={min_silence_chunks}, pre_speech_chunks={pre_speech_chunks}, max_chunks={max_chunks}")

    recorded_frames_list = []
    silence_counter = 0
    has_spoken = False
    
    pre_buffer = [np.zeros((chunk_frames, channels), dtype=np.int16) for _ in range(pre_speech_chunks)]
    print("Debug: Pre_buffer initialized.")

    stream = None # Initialize stream to None for finally block
    try:
        print("Debug: Attempting to open sd.InputStream...")
        stream = sd.InputStream(samplerate=samplerate, channels=channels, dtype='int16', blocksize=chunk_frames)
        print("Debug: sd.InputStream opened successfully.")
        with stream:
            print("Debug: Entered stream context manager.")
            for i in range(max_chunks):
                # print(f"Debug: Reading chunk {i+1}/{max_chunks}") # Can be very verbose
                audio_chunk, overflowed = stream.read(chunk_frames)
                if overflowed:
                    print("Warning: Input overflowed!")

                pre_buffer.pop(0)
                pre_buffer.append(audio_chunk.copy())

                rms = np.sqrt(np.mean(audio_chunk.astype(np.float32)**2))
                # print(f"Chunk {i}, RMS: {rms:.4f}, Silence Counter: {silence_counter}") # For detailed RMS debugging

                if rms > silence_threshold:
                    if not has_spoken:
                        print("Speech detected, recording...")
                        for pre_chunk in pre_buffer:
                            recorded_frames_list.append(pre_chunk)
                        has_spoken = True
                    else:
                        recorded_frames_list.append(audio_chunk)
                    silence_counter = 0
                elif has_spoken:
                    recorded_frames_list.append(audio_chunk)
                    silence_counter += 1
                    if silence_counter >= min_silence_chunks:
                        print(f"Silence detected for {min_silence_duration_ms/1000:.1f}s. Stopping recording.")
                        break
            else: 
                if has_spoken:
                    print("Max recording duration reached.")
                else:
                    print("Max recording duration reached, but no speech was detected.")
                    recorded_frames_list = []
        print("Debug: Exited stream context manager.")

    except Exception as e:
        print(f"ERROR in record_audio_vad stream processing: {e}")
        if stream: # Attempt to close if open
             if not stream.closed:
                stream.close()
        return False


    if not recorded_frames_list:
        print("No audio recorded (either no speech or only silence).")
        return False

    try:
        final_recording = np.concatenate(recorded_frames_list, axis=0)
        sf.write(filename, final_recording, samplerate)
        print(f"Recording finished and saved to {filename}")
        return True
    except Exception as e:
        print(f"ERROR saving recorded audio: {e}")
        return False


def upload_audio(url, filepath):
    """Uploads an audio file to the specified URL and saves the response."""
    print(f"Uploading {filepath} to {url}...")
    try:
        with open(filepath, 'rb') as f:
            files = {'audio': (os.path.basename(filepath), f, 'audio/wav')}
            response = requests.post(url, files=files, timeout=30)
            response.raise_for_status()

        if response.content:
            with open(TEMP_RESPONSE_FILENAME, 'wb') as out_file:
                out_file.write(response.content)
            print(f"Audio response saved to {TEMP_RESPONSE_FILENAME}")
            return TEMP_RESPONSE_FILENAME
        else:
            print("No content in response.")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error uploading audio: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during upload: {e}")
        return None

def play_audio(filename):
    """Plays an audio file."""
    if filename and os.path.exists(filename):
        try:
            print(f"Playing {filename}...")
            data, fs = sf.read(filename, dtype='float32')
            sd.play(data, fs)
            sd.wait()
            print("Playback finished.")
        except Exception as e:
            print(f"Error playing audio: {e}")
    else:
        print("Response audio file not found or no response to play.")

print("Functions defined.") # <-- ADDED THIS LINE (or ensure it's after all func defs)

def main_loop():
    """Main loop to record, upload, receive, and play audio."""
    print("Main_loop started.") # <-- ADDED THIS LINE
    temp_dir = tempfile.gettempdir() # Using system temp dir
    # Ensure temp filenames are joined with this temp_dir for consistency
    global TEMP_RECORDING_FILENAME, TEMP_RESPONSE_FILENAME
    temp_recording_path = os.path.join(temp_dir, TEMP_RECORDING_FILENAME)
    temp_response_path = os.path.join(temp_dir, TEMP_RESPONSE_FILENAME)
    print(f"Debug: Temp recording path: {temp_recording_path}")
    print(f"Debug: Temp response path: {temp_response_path}")


    try:
        while True:
            print("About to ask for input...") # <-- ADDED THIS LINE
            user_input = input("Press Enter to start recording (will stop on silence), or type 'q' to quit: ")
            print(f"Input received: '{user_input}'") # <-- ADDED THIS LINE

            if user_input.lower() == 'q':
                print("Quitting main loop.")
                break

            print("Proceeding with recording.") # <-- ADDED THIS LINE

            if record_audio_vad(temp_recording_path, SAMPLE_RATE, CHANNELS):
                if os.path.exists(temp_recording_path):
                    print(f"Debug: Recording file exists at {temp_recording_path}, proceeding to upload.")
                    response_audio_path = upload_audio(UPLOAD_URL, temp_recording_path)
                    if response_audio_path:
                        play_audio(response_audio_path)
                        try:
                            # os.remove(response_audio_path) # Optional: clean up
                            print(f"Debug: Would remove response audio at {response_audio_path} if uncommented.")
                        except OSError as e:
                            print(f"Error removing temporary response file: {e}")
                    else:
                        print("No audio response to play.")
                    try:
                        # os.remove(temp_recording_path) # Optional: clean up
                        print(f"Debug: Would remove recording audio at {temp_recording_path} if uncommented.")
                    except OSError as e:
                        print(f"Error removing temporary recording file: {e}")
                else:
                    print(f"Debug: Recording file {temp_recording_path} NOT found after VAD success. Skipping upload.")
            else:
                print("Recording was skipped or failed (e.g., no speech detected or error).")

            print("\nWaiting for next recording cycle...")
    except KeyboardInterrupt:
        print("\nExiting application due to KeyboardInterrupt.")
    except Exception as e:
        print(f"An unexpected error occurred in main_loop: {e}")
    finally:
        print("Main_loop finally block reached.")
        # Clean up temporary files on exit
        if os.path.exists(temp_recording_path) and os.path.isfile(temp_recording_path):
            try:
                os.remove(temp_recording_path)
                print(f"Cleaned up {temp_recording_path}")
            except OSError as e:
                print(f"Error removing temporary recording file on exit: {e}")
        if os.path.exists(temp_response_path) and os.path.isfile(temp_response_path):
            try:
                os.remove(temp_response_path)
                print(f"Cleaned up {temp_response_path}")
            except OSError as e:
                print(f"Error removing temporary response file on exit: {e}")
        print("Script cleanup done. Exiting.")

if __name__ == "__main__":
    print("Script reached __main__ block.") # <-- ADDED THIS LINE
    main_loop()