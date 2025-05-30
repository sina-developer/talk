#!/bin/bash

# --- RetroPie Port Launch Script for AI Audio Chatter ---
APP_DIR="/home/pi/talk" # Example path, PLEASE CHANGE THIS

VENV_NAME="venv_audio_chatter_pyaudio" 
VENV_PATH="${APP_DIR}/${VENV_NAME}"
PYTHON_MAIN_SCRIPT_NAME="main.py" 
PYTHON_MAIN_SCRIPT_PATH="${APP_DIR}/${PYTHON_MAIN_SCRIPT_NAME}"

# --- Debugging Setup: Redirect all output to a log file ---
# Useful if the script exits immediately without showing output on screen.
# Comment out the 'exec' line for normal operation once tested.
LOG_FILE="/tmp/AI_sh_debug.log"
echo "AI.sh Log Start: $(date)" > "$LOG_FILE"
#exec >> "$LOG_FILE" 2>&1 # Redirect stdout and stderr to log file
# set -x # Uncomment for very verbose command execution logging

echo "--------------------------------------"
echo " RetroPie Port: AI Audio Chatter      "
echo "--------------------------------------"
echo "App Dir: ${APP_DIR}"
echo "Venv:    ${VENV_PATH}"
echo "Script:  ${PYTHON_MAIN_SCRIPT_PATH}"
echo ""

# Basic checks
if [ ! -d "$APP_DIR" ]; then
    echo "ERROR: APP_DIR '$APP_DIR' not found." >&2 # Ensure errors go to log if exec is active
    exit 1
fi
if [ ! -f "$PYTHON_MAIN_SCRIPT_PATH" ]; then
    echo "ERROR: Main script '$PYTHON_MAIN_SCRIPT_PATH' not found." >&2
    exit 1
fi
if [ ! -f "${VENV_PATH}/bin/activate" ]; then
    echo "ERROR: Venv activation script not found at '${VENV_PATH}/bin/activate'." >&2
    exit 1
fi

echo "Changing to application directory: $APP_DIR"
cd "$APP_DIR" || { echo "ERROR: Failed to cd to '$APP_DIR'." >&2; exit 1; }

echo "Starting AI Audio Chatter Python application..."
echo "(Output will appear here or in $LOG_FILE if redirection is active)"
echo ""

# Run the Python main script within its virtual environment
# The Python script (main.py) now handles its own exit based on gamepad input.
(
    # echo "Subshell: Activating virtual environment..." # Less verbose for final version
    source "${VENV_PATH}/bin/activate" || {
        echo "ERROR INSIDE SUBSHELL: Failed to activate virtual environment." >&2
        exit 1 
    }
    # echo "Subshell: Launching: python $PYTHON_MAIN_SCRIPT_NAME" # Less verbose
    python "$PYTHON_MAIN_SCRIPT_NAME"
    # echo "Subshell: Python main script finished." # Less verbose
)
# script_exit_status=$? # Can be logged if needed

echo ""
echo "--------------------------------------"
echo "AI Audio Chatter application has exited."
echo "Returning to RetroPie menu."
# No 'read -r' needed here, Python script controls its own lifecycle.

exit 0
