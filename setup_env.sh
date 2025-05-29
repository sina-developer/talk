#!/bin/bash

# This script prepares the environment for the Python audio chatter application
# on Debian/Ubuntu-based Linux systems.

echo "Starting environment setup for Audio Chatter Python script..."
echo "This script will use 'sudo' for system-wide package installations."

# Ensure the script exits on any error
set -e

# 1. Update package lists
echo ""
echo "Step 1: Updating package lists..."
sudo apt-get update

# 2. Install Python 3, pip, and venv
echo ""
echo "Step 2: Installing Python 3, pip, and python3-venv..."
sudo apt-get install -y python3 python3-pip python3-venv

# 3. Install system dependencies for Python audio libraries
# libportaudio2: For sounddevice (PortAudio runtime)
# libasound2: ALSA runtime library (often a dependency for PortAudio on Linux)
# libsndfile1: For soundfile (reading/writing audio files)
# alsa-utils: For ALSA utilities like 'arecord' and 'aplay' (good for diagnostics)
echo ""
echo "Step 3: Installing system dependencies (libportaudio2, libasound2, libsndfile1, alsa-utils)..."
sudo apt-get install -y libportaudio2 libasound2 libsndfile1 alsa-utils

# 4. Check if requirements.txt exists
echo ""
echo "Step 4: Checking for requirements.txt..."
if [ ! -f "requirements.txt" ]; then
    echo "ERROR: requirements.txt not found in the current directory."
    echo "Please create it with content like:"
    echo "requests"
    echo "sounddevice"
    echo "soundfile"
    echo "numpy"
    exit 1
else
    echo "requirements.txt found."
fi

# 5. Set up Python virtual environment
VENV_DIR="venv_audio_chatter"
echo ""
echo "Step 5: Setting up Python virtual environment in './${VENV_DIR}'..."
if [ -d "$VENV_DIR" ]; then
    echo "Virtual environment '$VENV_DIR' already exists. Skipping creation."
    echo "If you want to recreate it, please remove the directory './${VENV_DIR}' first."
else
    python3 -m venv "$VENV_DIR"
    echo "Virtual environment created."
fi

# 6. Install Python packages into the virtual environment
echo ""
echo "Step 6: Activating virtual environment and installing Python packages..."
# Note: 'source' might behave differently depending on how the script is run (e.g. sh vs bash).
# This activates it for the pip install command. The user will need to activate it manually later.
source "${VENV_DIR}/bin/activate"
pip install -r requirements.txt
deactivate # Deactivate after install; user will activate manually for running the app

echo ""
echo "---------------------------------------------------------------------"
echo "Setup Complete!"
echo "---------------------------------------------------------------------"
echo ""
echo "Next Steps:"
echo "1. Activate the virtual environment in your terminal:"
echo "   source ${VENV_DIR}/bin/activate"
echo ""
echo "2. Ensure your microphone is not muted and is selected as the default input."
echo "   You can use 'alsamixer' (from alsa-utils) in the terminal to check levels."
echo "   Or use your desktop environment's sound settings."
echo ""
echo "3. Run the Python script (e.g., audio_chatter.py):"
echo "   python audio_chatter.py"
echo ""
echo "4. When you are done, you can deactivate the virtual environment by typing:"
echo "   deactivate"
echo ""

exit 0