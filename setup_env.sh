#!/bin/bash

# This script prepares the environment for the Python audio chatter application
# (PyAudio version) on Debian/Ubuntu-based Linux systems.

echo "Starting environment setup for Audio Chatter Python script (PyAudio version)..."
echo "This script will use 'sudo' for system-wide package installations."

set -e

echo ""
echo "Step 1: Updating package lists..."
sudo apt-get update

echo ""
echo "Step 2: Installing Python 3, pip, and python3-venv..."
sudo apt-get install -y python3 python3-pip python3-venv python3-dev

echo ""
echo "Step 3: Installing system dependencies for PyAudio..."
echo " PyAudio requires PortAudio development files (portaudio19-dev) and potentially others."
sudo apt-get install -y libportaudio2 portaudio19-dev alsa-utils

echo ""
echo "Step 4: Checking for requirements.txt..."
if [ ! -f "requirements.txt" ]; then
    echo "ERROR: requirements.txt not found in the current directory."
    echo "Please create it with content:"
    echo "requests"
    echo "PyAudio"
    exit 1
else
    echo "requirements.txt found."
fi

VENV_DIR="venv_audio_chatter_pyaudio" # Changed venv directory name
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
echo "Setup Complete! (PyAudio version)"
echo "---------------------------------------------------------------------"
echo ""
echo "Next Steps:"
echo "1. Activate the virtual environment in your terminal:"
echo "   source ${VENV_DIR}/bin/activate"
echo ""
echo "2. Ensure your microphone is not muted and is selected as the default input."
echo "   Use 'alsamixer' or your desktop sound settings."
echo ""
echo "3. Run the Python script (e.g., audio_chatter.py with PyAudio changes):"
echo "   python audio_chatter.py"
echo ""
echo "4. When you are done, deactivate the virtual environment by typing:"
echo "   deactivate"
echo ""

exit 0