#!/bin/bash

echo "Starting environment setup for AI Audio Chatter (PyAudio/ffplay/evdev/vlc)..."
# ... (rest of initial echos and set -e) ...
set -e

echo ""
echo "Step 1: Updating package lists..."
sudo apt-get update

echo ""
echo "Step 2: Installing Python 3, pip, python3-venv, python3-dev..."
sudo apt-get install -y python3 python3-pip python3-venv python3-dev

echo ""
echo "Step 3: Installing system dependencies..."
# libportaudio2, portaudio19-dev for PyAudio
# alsa-utils for audio tools
# ffmpeg for ffplay (audio response playback)
# libudev-dev for evdev (gamepad input)
# evtest for gamepad diagnostics
# vlc-bin for cvlc (video playback, no X11 needed for basic operation)
sudo apt-get install -y libportaudio2 portaudio19-dev alsa-utils ffmpeg libudev-dev evtest vlc-bin

# ... (rest of the script: requirements.txt check, venv creation, pip install) ...

echo ""
echo "Step 4: Checking for requirements.txt..." # Ensure this step number is correct if changed above
if [ ! -f "requirements.txt" ]; then
    echo "ERROR: requirements.txt not found."
    echo "Please create it with content: requests, PyAudio, evdev"
    exit 1
fi
echo "requirements.txt found."

VENV_DIR="venv_audio_chatter_pyaudio" 
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
echo "Setup Complete! (PyAudio/ffplay/evdev/vlc version)"
# ... (rest of the instructions, including activating venv manually) ...
echo "Next Steps:"
echo "1. Create a 'videos' folder in your app directory and add:"
echo "   idle.mp4, listening.mp4, thinking.mp4, talking.mp4"
echo "2. Configure video paths and gamepad settings in 'config.py'."
echo "3. Activate the virtual environment: source ${VENV_DIR}/bin/activate"
echo "4. Run the Python script: python main.py"
echo "---------------------------------------------------------------------"
echo ""
echo "Script finished."
exit 0
