# config.py
"""
Configuration constants for the Audio Chatter application.
"""
import tempfile
import pyaudio # For PYAUDIO_FORMAT
from evdev import ecodes # For button codes

# --- Audio Configuration ---
SAMPLE_RATE = 48000
CHANNELS = 1
INPUT_DEVICE_INDEX = 2  # Your USB mic index, set after running check_audio_devices.py
                        # If None, PyAudio will use the system default input.

# PyAudio settings
PYAUDIO_FORMAT = pyaudio.paInt16  # 16-bit audio
FRAMES_PER_BUFFER = 1024        # Chunk size for PyAudio stream processing

# --- File Configuration ---
TEMP_DIR = tempfile.gettempdir()
TEMP_RECORDING_FILENAME = "mic_recording.wav" # Name for your microphone recording
TEMP_RESPONSE_FILENAME = "server_response.mp3" # Expecting MP3 from server

# --- Network Configuration ---
UPLOAD_URL = 'https://n8n.c-na.dev/webhook/talk' # Target URL for audio upload

# --- Gamepad Configuration ---
# OPTION 1 (MOST RELIABLE): Set this to a stable path from /dev/input/by-id/ for your gamepad
# e.g., GAMEPAD_DEVICE_PATH = "/dev/input/by-id/bluetooth-MyControllerName-event-joystick"
# OPTION 2: Leave as None to attempt auto-detection (heuristic or interactive).
GAMEPAD_DEVICE_PATH = None 

# Define button codes (these are common, verify with evtest for your gamepad)
# You can find more ecodes.BTN_ constants here:
# https://python-evdev.readthedocs.io/en/latest/ecodes.html
BTN_ACTION_START_STOP = ecodes.BTN_SOUTH # Typically 'A' on Xbox-style, 'X' on PlayStation
BTN_ACTION_QUIT = ecodes.BTN_START   # Typically the 'Start' button

# Timeout for interactive gamepad detection (in seconds)
GAMEPAD_DETECT_TIMEOUT_S = 15

# Keywords for heuristic gamepad detection
GAMEPAD_PREFERRED_NAME_KEYWORDS = ["gamepad", "joystick", "controller"]

# --- Playback Configuration ---
# External player command (ffplay is versatile)
# Ensure this player is installed on your system (e.g., via `sudo apt-get install ffmpeg`)
EXTERNAL_PLAYER_COMMAND = ['ffplay', '-autoexit', '-nodisp', '-loglevel', 'error']
# Example for mpg123 (if you know it's always MP3 and want a simpler player):
# EXTERNAL_PLAYER_COMMAND = ['mpg123', '-q'] # -q for quiet mode

