#!/bin/bash

# --- RetroPie Port Launch Script for Audio Chatter ---

# IMPORTANT: Set this to the directory where your audio_chatter.py and venv are located!
APP_DIR="/home/pi/talk" # Example path, PLEASE CHANGE THIS

VENV_NAME="venv_audio_chatter_pyaudio" # Should match the venv name created by setup_env.sh
VENV_PATH="${APP_DIR}/${VENV_NAME}"
PYTHON_MAIN_SCRIPT_NAME="main.py" # The main script to run
PYTHON_MAIN_SCRIPT_PATH="${APP_DIR}/${PYTHON_MAIN_SCRIPT_NAME}"

echo "--------------------------------------"
echo " RetroPie Port: AI Audio Chatter      "
echo "--------------------------------------"
echo "Application Directory: ${APP_DIR}"
echo "Virtual Environment: ${VENV_PATH}"
echo "Python Main Script: ${PYTHON_MAIN_SCRIPT_PATH}"
echo ""

# Check if the application directory exists
if [ ! -d "$APP_DIR" ]; then
    echo "ERROR: Application directory '$APP_DIR' not found."
    echo "Please edit this script ('$(basename "$0")') and set the APP_DIR variable correctly."
    sleep 10 # Give user time to read error
    exit 1
fi

# Check if the Python main script exists
if [ ! -f "$PYTHON_MAIN_SCRIPT_PATH" ]; then
    echo "ERROR: Python main script '$PYTHON_MAIN_SCRIPT_PATH' not found."
    echo "Please ensure it exists in the APP_DIR."
    sleep 10
    exit 1
fi

# Check if the virtual environment activation script exists
if [ ! -f "${VENV_PATH}/bin/activate" ]; then
    echo "ERROR: Virtual environment activation script not found at '${VENV_PATH}/bin/activate'."
    echo "Please ensure the virtual environment was created correctly by setup_env.sh."
    sleep 10
    exit 1
fi

echo "Changing to application directory: $APP_DIR"
cd "$APP_DIR" || {
    echo "ERROR: Failed to change to directory '$APP_DIR'. Exiting."
    sleep 10
    exit 1
}

echo "Starting AI Audio Chatter Python application..."
echo "(You will interact with the script in this terminal view)"
echo ""

# Run the Python main script within its virtual environment
# Using a subshell (...) to keep environment changes local to the script execution
(
    echo "Activating virtual environment..."
    source "${VENV_PATH}/bin/activate" || {
        echo "ERROR: Failed to activate virtual environment. Check VENV_PATH and setup."
        # Let the python command fail if venv not active.
    }
    echo "Launching: python $PYTHON_MAIN_SCRIPT_NAME"
    echo "--------------------------------------"
    # Execute the main.py script
    python "$PYTHON_MAIN_SCRIPT_NAME"
    # Deactivation is optional as subshell will exit
)

echo ""
echo "--------------------------------------"
echo "AI Audio Chatter script has finished."
echo "Press Enter to return to RetroPie menu..."
read -r # Waits for Enter key press before exiting the script

exit 0
