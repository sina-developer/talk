# main.py
"""
Main application script for AI Audio Chatter with Gamepad Control.
Initializes configurations, detects the gamepad, and starts the main application loop.
"""
import os
import sys
import config         # User and application configurations
import gamepad_manager # For gamepad detection and main loop
from evdev import InputDevice # For testing user-configured path

def run_application():
    """
    Initializes and runs the audio chatter application.
    """
    print("AI Audio Chatter with Gamepad Control - Initializing...")
    print("----------------------------------------------------")

    active_gamepad_device = None # This will hold the opened InputDevice object

    # --- Step 1: Try user-configured GAMEPAD_DEVICE_PATH first ---
    if config.GAMEPAD_DEVICE_PATH and os.path.exists(config.GAMEPAD_DEVICE_PATH):
        print(f"Attempting to use user-configured GAMEPAD_DEVICE_PATH: {config.GAMEPAD_DEVICE_PATH}")
        try:
            active_gamepad_device = InputDevice(config.GAMEPAD_DEVICE_PATH)
            print(f"Successfully opened configured gamepad: {active_gamepad_device.name}")
        except Exception as e:
            print(f"Could not open user-configured gamepad '{config.GAMEPAD_DEVICE_PATH}': {e}")
            active_gamepad_device = None # Ensure it's None so we fall through to detection
    elif config.GAMEPAD_DEVICE_PATH: # Path was set in config but doesn't exist
        print(f"User-configured GAMEPAD_DEVICE_PATH '{config.GAMEPAD_DEVICE_PATH}' does not exist.")


    # --- Step 2: If no valid configured path, try interactive detection ---
    if not active_gamepad_device:
        if config.GAMEPAD_DEVICE_PATH: # Indicated that the configured one failed
             print("Falling back to interactive gamepad detection...")
        else: # No path was configured at all
            print("GAMEPAD_DEVICE_PATH not set in config.py.")
        
        active_gamepad_device = gamepad_manager.detect_gamepad_interactively()

    # --- Step 3: Check if a gamepad was successfully identified and opened ---
    if not active_gamepad_device:
        print("--------------------------------------------------------------------------")
        print("CRITICAL: NO GAMEPAD COULD BE IDENTIFIED OR OPENED.")
        print("Please ensure your gamepad is connected BEFORE starting this script.")
        print("Recommendations:")
        print("1. Check Bluetooth/USB connection of your gamepad.")
        print("2. If detection fails, try setting GAMEPAD_DEVICE_PATH manually in 'config.py'")
        print("   to a stable path like '/dev/input/by-id/your-gamepad-link-event-joystick'.")
        print("   Find this path using 'ls -l /dev/input/by-id/' while the gamepad is connected.")
        print("3. Ensure 'sudo evtest' lists your gamepad and it generates button events.")
        print("4. Check script permissions (user needs to be in 'input' group for /dev/input/*).")
        print("--------------------------------------------------------------------------")
        sys.exit(1) # Exit if no gamepad can be used
    
    print(f"Using gamepad: {active_gamepad_device.name} ({active_gamepad_device.path})")
    print("----------------------------------------------------")

    # --- Check other critical configurations ---
    if config.INPUT_DEVICE_INDEX is None:
        print("Warning: INPUT_DEVICE_INDEX in 'config.py' is not explicitly set.")
        print("         PyAudio will attempt to use the system's default input device for the microphone.")
    else:
        print(f"Using microphone input device index: {config.INPUT_DEVICE_INDEX}")
    print("----------------------------------------------------")

    # --- Start the main application loop ---
    try:
        gamepad_manager.run_application_loop(active_gamepad_device) # Pass the opened device
    except Exception as e: 
        print(f"A critical error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if active_gamepad_device: # Ensure it's closed if it was opened
            try:
                active_gamepad_device.close()
            except Exception: pass
        print("Application has exited.")

if __name__ == "__main__":
    run_application()
