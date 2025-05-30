# config.py
"""
Configuration constants for the Audio Chatter application.
"""
import tempfile
import pyaudio # For PYAUDIO_FORMAT
from evdev import ecodes # For button codes
import os # Make sure this is at the top if not already present



# --- Video Configuration ---
# Assumes videos are in a 'videos' subdirectory of your APP_DIR.
# You'll need to create these video files.
VIDEO_BASE_PATH = "videos" # Relative to your main application directory
VIDEO_IDLE = os.path.join(VIDEO_BASE_PATH, "idle.mp4")
VIDEO_LISTENING = os.path.join(VIDEO_BASE_PATH, "listening.mp4")
VIDEO_THINKING = os.path.join(VIDEO_BASE_PATH, "thinking.mp4") # e.g., during upload & server wait
VIDEO_TALKING = os.path.join(VIDEO_BASE_PATH, "talking.mp4")  # e.g., while server response audio plays

# Command for VLC (cvlc) to play video, loop, without OSD, non-interactive.
VIDEO_PLAYER_COMMAND_TEMPLATE = [
    'cvlc',
    '--no-osd',         # No On-Screen Display
    '--no-interact',    # Disable dummy interface, run in background
    '--loop',           # Loop the video
    '--no-video-title-show', # Don't show the title
    # '--fullscreen',   # Uncomment if you want fullscreen
    # Video path will be appended to this list
]

# ... (all your other existing configurations for audio, gamepad, etc.) ...
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

