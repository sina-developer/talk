# main.py
"""
Main application script for AI Audio Chatter with Gamepad Control.
Initializes configurations, detects the gamepad, and starts the main application loop.
"""
import os
import sys
import config         
import gamepad_manager 
import video_manager # Import for cleanup
from evdev import InputDevice 

def run_application():
    print("AI Audio Chatter with Video States - Initializing...")
    print("----------------------------------------------------")
    active_gamepad_device = None 

    if config.GAMEPAD_DEVICE_PATH and os.path.exists(config.GAMEPAD_DEVICE_PATH):
        print(f"Attempting user-configured GAMEPAD_DEVICE_PATH: {config.GAMEPAD_DEVICE_PATH}")
        try:
            active_gamepad_device = InputDevice(config.GAMEPAD_DEVICE_PATH)
            print(f"Successfully opened configured gamepad: {active_gamepad_device.name}")
        except Exception as e:
            print(f"Could not open '{config.GAMEPAD_DEVICE_PATH}': {e}")
            active_gamepad_device = None
    elif config.GAMEPAD_DEVICE_PATH: 
        print(f"User-configured GAMEPAD_DEVICE_PATH '{config.GAMEPAD_DEVICE_PATH}' does not exist.")

    if not active_gamepad_device:
        if config.GAMEPAD_DEVICE_PATH: print("Falling back to interactive gamepad detection...")
        else: print("GAMEPAD_DEVICE_PATH not set in config.py. Starting interactive detection...")
        active_gamepad_device = gamepad_manager.detect_gamepad_interactively()

    if not active_gamepad_device:
        print("CRITICAL: NO GAMEPAD COULD BE IDENTIFIED. Please check connections and config.")
        sys.exit(1)
    
    print(f"Using gamepad: {active_gamepad_device.name} ({active_gamepad_device.path})")
    print("----------------------------------------------------")
    if config.INPUT_DEVICE_INDEX is None:
        print("Warning: INPUT_DEVICE_INDEX not set. Using default PyAudio input for microphone.")
    else:
        print(f"Using microphone input device index: {config.INPUT_DEVICE_INDEX}")
    print("----------------------------------------------------")

    try:
        gamepad_manager.run_application_loop(active_gamepad_device) 
    except Exception as e: 
        print(f"A critical error occurred: {e}")
        import traceback; traceback.print_exc()
    finally:
        print("Exiting application. Cleaning up video...")
        video_manager.stop_current_video() # Ensure video is stopped
        if active_gamepad_device: 
            try: active_gamepad_device.close()
            except Exception: pass
        print("Application has exited.")

if __name__ == "__main__":
    run_application()
