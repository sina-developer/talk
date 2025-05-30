# main.py
"""
Main application script for Audio Chatter with Gamepad Control.
Initializes configurations, detects the gamepad, and starts the main application loop.
"""
import os
import sys
import config # User and application configurations
import gamepad_manager # For gamepad detection and main loop

def run_application():
    """
    Initializes and runs the audio chatter application.
    """
    print("Audio Chatter with Gamepad Control - Initializing...")
    print("----------------------------------------------------")

    # --- Step 1: Determine which gamepad path to use ---
    effective_gamepad_path = config.GAMEPAD_DEVICE_PATH # Start with user-configured path

    if effective_gamepad_path and os.path.exists(effective_gamepad_path):
        try:
            # Test if the configured path is a valid evdev device by trying to open it
            # This is a quick check; gamepad_manager.run_application_loop will do a more robust open.
            from evdev import InputDevice # Local import for this test
            test_device = InputDevice(effective_gamepad_path)
            test_device.close() # Close immediately after test
            print(f"Using user-configured GAMEPAD_DEVICE_PATH: {effective_gamepad_path}")
        except Exception as e:
            print(f"User-configured GAMEPAD_DEVICE_PATH '{effective_gamepad_path}' is not valid or accessible: {e}")
            print("Attempting heuristic auto-detection of gamepad...")
            effective_gamepad_path = gamepad_manager.auto_detect_gamepad_by_name_caps()
    elif effective_gamepad_path: # Path was set in config but doesn't exist
        print(f"User-configured GAMEPAD_DEVICE_PATH '{effective_gamepad_path}' does not exist.")
        print("Attempting heuristic auto-detection of gamepad...")
        effective_gamepad_path = gamepad_manager.auto_detect_gamepad_by_name_caps()
    else: # GAMEPAD_DEVICE_PATH was None (not set by user in config.py)
        print("GAMEPAD_DEVICE_PATH not set by user in config.py.")
        print("Attempting heuristic auto-detection of gamepad by name/capabilities...")
        effective_gamepad_path = gamepad_manager.auto_detect_gamepad_by_name_caps()

    # --- Step 2: If heuristic detection failed, try interactive detection ---
    if not (effective_gamepad_path and os.path.exists(effective_gamepad_path)):
        if effective_gamepad_path : # Heuristic found something, but it seems invalid
            print(f"Heuristic auto-detection found '{effective_gamepad_path}' but it seems invalid or inaccessible.")
        else: # Heuristic detection failed to find anything
            print("Heuristic auto-detection failed to find a suitable gamepad.")
        
        print("Proceeding to interactive gamepad detection (by button press)...")
        effective_gamepad_path = gamepad_manager.detect_gamepad_by_press()

    # --- Step 3: Check if a gamepad was successfully identified ---
    if not effective_gamepad_path:
        print("--------------------------------------------------------------------------")
        print("CRITICAL: NO GAMEPAD COULD BE FOUND OR DETECTED.")
        print("Please ensure your gamepad is connected BEFORE starting this script.")
        print("Recommendations:")
        print("1. Check Bluetooth/USB connection.")
        print("2. Try setting GAMEPAD_DEVICE_PATH manually in 'config.py' to a stable")
        print("   path like '/dev/input/by-id/your-gamepad-specific-link-event-joystick'.")
        print("   Find this path using 'ls -l /dev/input/by-id/' while the gamepad is connected.")
        print("3. Ensure 'sudo evtest' lists your gamepad and it generates button events.")
        print("4. Check script permissions if running as non-root (user needs to be in 'input' group).")
        print("--------------------------------------------------------------------------")
        sys.exit(1) # Exit if no gamepad can be used
    
    print(f"Selected gamepad path for use: {effective_gamepad_path}")
    print("----------------------------------------------------")


    # --- Step 4: Check other critical configurations (optional, but good practice) ---
    if config.INPUT_DEVICE_INDEX is None:
        print("Warning: INPUT_DEVICE_INDEX in 'config.py' is not explicitly set.")
        print("         PyAudio will attempt to use the system's default input device for the microphone.")
        print("         If you have multiple microphones, this might not be the one you intend to use.")
        print("         Consider running a script to list audio devices and set INPUT_DEVICE_INDEX accordingly.")
    else:
        print(f"Using microphone input device index: {config.INPUT_DEVICE_INDEX}")
    print("----------------------------------------------------")

    # --- Step 5: Start the main application loop ---
    try:
        gamepad_manager.run_application_loop(effective_gamepad_path)
    except Exception as e: # Catch any unhandled exceptions from the main loop
        print(f"A critical error occurred in the application: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("Application has exited.")

if __name__ == "__main__":
    run_application()
