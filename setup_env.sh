#!/bin/bash

echo "Starting environment setup for Audio Chatter Python script (PyAudio/ffplay/evdev version)..."
echo "This script will use 'sudo' for system-wide package installations."
set -e

echo ""
echo "Step 1: Updating package lists..."
sudo apt-get update

echo ""
echo "Step 2: Installing Python 3, pip, python3-venv, python3-dev..."
sudo apt-get install -y python3 python3-pip python3-venv python3-dev

echo ""
echo "Step 3: Installing system dependencies..."
sudo apt-get install -y libportaudio2 portaudio19-dev alsa-utils ffmpeg libudev-dev evtest # ADDED libudev-dev, evtest

echo ""
echo "Step 4: Checking for requirements.txt..."
if [ ! -f "requirements.txt" ]; then
    echo "ERROR: requirements.txt not found."
    echo "Please create it with content: requests, PyAudio, evdev"
    exit 1
fi
echo "requirements.txt found."

VENV_DIR="venv_audio_chatter_pyaudio" # Keeping same venv name for consistency
echo ""
echo "Step 5: Setting up Python virtual environment in './${VENV_DIR}'..."
if [ -d "$VENV_DIR" ]; then
    echo "Virtual environment '$VENV_DIR' already exists. Skipping creation."
else
    python3 -m venv "$VENV_DIR"
    echo "Virtual environment created."
fi

echo ""
echo "Step 6: Activating virtual environment and installing Python packages..."
source "${VENV_DIR}/bin/activate"
echo "Attempting to install packages from requirements.txt into '${VENV_DIR}'..."
pip install -r requirements.txt
echo "Pip install command finished."
deactivate 
echo "Virtual environment deactivated after package installation."

echo ""
echo "---------------------------------------------------------------------"
echo "Setup Complete! (PyAudio/ffplay/evdev version)"
echo "---------------------------------------------------------------------"
echo "Next Steps:"
echo "1. Identify your gamepad's event path (e.g., /dev/input/eventX)."
echo "   You can use 'ls /dev/input/by-id/' or run 'sudo evtest' and select your gamepad."
echo "2. Update GAMEPAD_DEVICE_PATH in audio_chatter.py with this path."
echo "3. Activate the virtual environment: source ${VENV_DIR}/bin/activate"
echo "4. Ensure microphone is configured (alsamixer)."
echo "5. Run the Python script: python audio_chatter.py"
echo "6. To deactivate: deactivate"
echo ""
# (The final source command here only affects this script's subshell, not the parent terminal)
# echo "Activating venv '${VENV_DIR}' for the remainder of this script's execution (which is minimal)..."
# source "${VENV_DIR}/bin/activate"
echo "Script finished. Remember to activate the venv manually in your terminal as instructed above."
exit 0