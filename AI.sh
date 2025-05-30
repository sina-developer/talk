#!/bin/bash

# --- RetroPie Port Launch Script for AI Audio Chatter ---
APP_DIR="/home/pi/talk" # Example path, PLEASE CHANGE THIS
VENV_NAME="venv_audio_chatter_pyaudio"
VENV_PATH="${APP_DIR}/${VENV_NAME}"
PYTHON_MAIN_SCRIPT_NAME="main.py"
PYTHON_MAIN_SCRIPT_PATH="${APP_DIR}/${PYTHON_MAIN_SCRIPT_NAME}"
PYTHON_WAIT_SCRIPT_NAME="wait_for_exit_input.py" # Name of our new helper script
PYTHON_WAIT_SCRIPT_PATH="${APP_DIR}/${PYTHON_WAIT_SCRIPT_NAME}"

echo "--------------------------------------"
echo " RetroPie Port: AI Audio Chatter      "
# ... (rest of the initial checks and echos remain the same as your last AI.sh) ...
echo "Application Directory: ${APP_DIR}"
echo "Virtual Environment: ${VENV_PATH}"
echo "Python Main Script: ${PYTHON_MAIN_SCRIPT_PATH}"
echo ""

if [ ! -d "$APP_DIR" ]; then /* ... (error checks as before) ... */ fi
if [ ! -f "$PYTHON_MAIN_SCRIPT_PATH" ]; then /* ... */ fi
if [ ! -f "${VENV_PATH}/bin/activate" ]; then /* ... */ fi
if [ ! -f "$PYTHON_WAIT_SCRIPT_PATH" ]; then
    echo "ERROR: Python helper script '$PYTHON_WAIT_SCRIPT_PATH' not found."
    echo "Please ensure it exists in the APP_DIR."
    sleep 10
    exit 1
fi

echo "Changing to application directory: $APP_DIR"
cd "$APP_DIR" || { /* ... */ }

echo "Starting AI Audio Chatter Python application..."
echo "(You will interact with the script in this terminal view)"
echo ""

(
    echo "Activating virtual environment..."
    source "${VENV_PATH}/bin/activate" || { echo "ERROR: Failed to activate venv."; }
    echo "Launching: python $PYTHON_MAIN_SCRIPT_NAME"
    echo "--------------------------------------"
    python "$PYTHON_MAIN_SCRIPT_NAME"
)

echo ""
echo "--------------------------------------"
echo "AI Audio Chatter script has finished."
echo "Press Enter (Keyboard) or Start Button (Gamepad) to return to RetroPie menu..."

# Call the Python helper script to wait for Enter or Gamepad Start button
# It uses the same virtual environment's Python interpreter.
"${VENV_PATH}/bin/python" "$PYTHON_WAIT_SCRIPT_NAME"

# The helper script will exit after input or timeout, then this script continues.
echo "Returning to RetroPie..." # Optional message
exit 0