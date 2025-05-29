#!/bin/bash

echo "Starting environment setup for Audio Chatter Python script (PyAudio/ffplay version)..."
echo "This script will use 'sudo' for system-wide package installations."
set -e

echo ""
echo "Step 1: Updating package lists..."
sudo apt-get update

echo ""
echo "Step 2: Installing Python 3, pip, python3-venv, python3-dev..."
sudo apt-get install -y python3 python3-pip python3-venv python3-dev

echo ""
echo "Step 3: Installing system dependencies for PyAudio and FFmpeg (for ffplay)..."
sudo apt-get install -y libportaudio2 portaudio19-dev alsa-utils ffmpeg # ADDED ffmpeg

echo ""
echo "Step 4: Checking for requirements.txt..."
if [ ! -f "requirements.txt" ]; then
    echo "ERROR: requirements.txt not found."
    echo "Please create it with content: requests, PyAudio"
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
echo "Attempting to install packages from requirements.txt..."
pip install -r requirements.txt
echo "Pip install command finished."
deactivate

echo ""
echo "---------------------------------------------------------------------"
echo "Setup Complete! (PyAudio/ffplay version)"
echo "---------------------------------------------------------------------"
echo "Next Steps:"
echo "1. Activate the virtual environment: source ${VENV_DIR}/bin/activate"
echo "2. Ensure microphone is configured (alsamixer)."
echo "3. Run the Python script: python audio_chatter.py"
echo "4. To deactivate: deactivate"
echo ""
exit 0