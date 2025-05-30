# gamepad_manager.py
"""
Manages gamepad detection and the main application loop based on gamepad events.
"""
import os
import sys
import time
import select   # For detect_gamepad_by_press
from evdev import InputDevice, categorize, ecodes, list_devices

import config # User and application configurations
import audio_recorder
import audio_uploader
import audio_player
import os

def clear_screen():
    """Clears the terminal screen."""
    # For Windows
    if os.name == 'nt':
        os.system('cls')
    # For macOS and Linux
    else:
        os.system('clear')

# You would then call clear_screen() at the appropriate point in your application's loop.

def detect_gamepad_interactively(timeout_seconds=config.GAMEPAD_DETECT_TIMEOUT_S):
    """
    Asks user to press any button on their gamepad and identifies it.
    Returns:
        InputDevice object: The detected and opened gamepad device, or None.
    """
    print(f"\n--- Interactive Gamepad Detection ---")
    print(f"Please press ANY button on your desired gamepad within {timeout_seconds} seconds...")
    print("Scanning for input devices...")

    monitored_devices_map = {} # Maps file descriptor (fd) to InputDevice object
    opened_devices_for_cleanup = [] # Keep track of all devices opened during scan

    try:
        all_device_paths = list_devices()
        if not all_device_paths:
            print("No input devices found in /dev/input/*.")
            return None
        
        print(f"Found {len(all_device_paths)} potential input devices. Filtering for gamepads...")

        for path in all_device_paths:
            dev = None # Ensure dev is defined for finally block in case of early exception
            try:
                dev = InputDevice(path)
                opened_devices_for_cleanup.append(dev) # Add to cleanup list immediately after open
                capabilities = dev.capabilities(verbose=False)
                # Broad filter for devices that have any typical gamepad buttons
                if ecodes.EV_KEY in capabilities and \
                   any(code in capabilities[ecodes.EV_KEY] for code in [
                       ecodes.BTN_GAMEPAD, ecodes.BTN_SOUTH, ecodes.BTN_EAST, ecodes.BTN_NORTH, ecodes.BTN_WEST,
                       ecodes.BTN_A, ecodes.BTN_B, ecodes.BTN_C, ecodes.BTN_X, ecodes.BTN_Y, ecodes.BTN_Z,
                       ecodes.BTN_START, ecodes.BTN_SELECT, ecodes.BTN_MODE,
                       ecodes.BTN_JOYSTICK, ecodes.BTN_TRIGGER, ecodes.BTN_THUMB, ecodes.BTN_THUMB2,
                       ecodes.BTN_DPAD_UP, ecodes.BTN_DPAD_DOWN, ecodes.BTN_DPAD_LEFT, ecodes.BTN_DPAD_RIGHT
                   ]):
                    monitored_devices_map[dev.fd] = dev
                    # print(f"  Monitoring: {dev.name} ({dev.path})") # Can be verbose
                # else:
                    # If not added to monitored_devices_map, it will be closed in the main finally block
                    # print(f"  Skipping (not gamepad-like): {dev.name} ({dev.path})")
            except Exception: 
                # Ignore devices we can't open or check capabilities for
                # It will be in opened_devices_for_cleanup if 'dev' was assigned
                pass
    except Exception as e:
        print(f"Error listing or pre-filtering input devices: {e}. Check permissions for /dev/input/*")
        # Clean up any opened devices before returning
        for dev_to_close in opened_devices_for_cleanup:
            try: dev_to_close.close()
            except: pass
        return None

    if not monitored_devices_map:
        print("No suitable gamepad-like devices found to monitor for a button press.")
        # opened_devices_for_cleanup will be handled by the main finally
        return None
    
    print(f"Monitoring {len(monitored_devices_map)} potential gamepad(s) for a button press...")

    readable_fds, _, _ = select.select(monitored_devices_map.keys(), [], [], timeout_seconds)

    detected_device_object = None
    if not readable_fds: # Timeout occurred
        print(f"No gamepad button press detected within {timeout_seconds} seconds.")
    else:
        for fd in readable_fds:
            device_that_fired = monitored_devices_map[fd]
            try:
                # Read all immediately available events for this fd to find a key down
                for event in device_that_fired.read(): 
                    if event.type == ecodes.EV_KEY and event.value == 1: # Key down event
                        print(f"\nButton press detected on: {device_that_fired.name} ({device_that_fired.path})")
                        detected_device_object = device_that_fired # Keep this device open
                        break 
                if detected_device_object:
                    break 
            except BlockingIOError: continue 
            except Exception as e: 
                print(f"Error reading from device {device_that_fired.path}: {e}")
            if detected_device_object: break
    
    # Close all monitored devices EXCEPT the one that was detected (if any)
    for fd_to_close, dev_to_close in monitored_devices_map.items():
        if detected_device_object and dev_to_close.fd == detected_device_object.fd:
            continue # Don't close the detected device
        try: dev_to_close.close()
        except: pass
    
    # Also close any devices from the initial scan that weren't monitored
    for dev_to_clean in opened_devices_for_cleanup:
        is_monitored_or_detected = False
        if detected_device_object and dev_to_clean.path == detected_device_object.path:
            is_monitored_or_detected = True
        if not is_monitored_or_detected and dev_to_clean.path not in [d.path for d in monitored_devices_map.values()]:
             try: dev_to_clean.close()
             except: pass


    return detected_device_object # Return the opened InputDevice object or None


def run_application_loop(gamepad_device_object):
    """
    Main application loop, controlled by gamepad events.
    Args:
        gamepad_device_object (evdev.InputDevice): The opened and active gamepad device.
    """
    gamepad = gamepad_device_object # Use the passed, already opened device
    print(f"\nApplication ready. Using gamepad: {gamepad.name}")
    start_stop_key_name = ecodes.KEY.get(config.BTN_ACTION_START_STOP, f"Code {config.BTN_ACTION_START_STOP}")
    quit_key_name = ecodes.KEY.get(config.BTN_ACTION_QUIT, f"Code {config.BTN_ACTION_QUIT}")
    clear_screen()
    print(f"--- Controls ---")
    print(f"- Press '{start_stop_key_name}' to Start/Stop Recording.")
    print(f"- Press '{quit_key_name}' to Exit Application.")
    print("----------------")

    if not os.path.exists(config.TEMP_DIR):
        os.makedirs(config.TEMP_DIR, exist_ok=True)
    
    temp_recording_full_path = os.path.join(config.TEMP_DIR, config.TEMP_RECORDING_FILENAME)
    
    is_recording = False
    current_recording_thread = None
    should_quit_application = False

    try:
        for event in gamepad.read_loop(): 
            if should_quit_application:
                break

            if event.type == ecodes.EV_KEY:
                key_event = categorize(event)
                if key_event.keystate == key_event.key_down: # Process only on button press
                    
                    if event.code == config.BTN_ACTION_QUIT:
                        print(f"'{quit_key_name}' button pressed. Signaling application to exit...")
                        should_quit_application = True
                        if is_recording and current_recording_thread and current_recording_thread.is_alive():
                            print("Stopping active recording before quitting...")
                            audio_recorder._stop_event.set() 
                            current_recording_thread.join(timeout=2) 
                        break 

                    elif event.code == config.BTN_ACTION_START_STOP:
                        if not is_recording:
                            print(f"'{start_stop_key_name}' pressed. Starting recording...")
                            current_recording_thread = audio_recorder.start_recording_thread(config.TEMP_RECORDING_FILENAME)
                            if current_recording_thread:
                                is_recording = True
                                print(f"RECORDING STARTED. Press '{start_stop_key_name}' again to STOP.")
                            else:
                                print("Failed to start recording thread.")
                        else: # Was recording, now stop
                            print(f"'{start_stop_key_name}' pressed. Stopping recording...")
                            if audio_recorder.stop_and_save_recording(current_recording_thread, config.TEMP_RECORDING_FILENAME):
                                if os.path.exists(temp_recording_full_path) and os.path.getsize(temp_recording_full_path) > 44:
                                    response_audio_path = audio_uploader.upload_audio(temp_recording_full_path)
                                    if response_audio_path:
                                        audio_player.play_audio_external(response_audio_path)
                                        try: os.remove(response_audio_path)
                                        except OSError as e: print(f"Error removing response file: {e}")
                                    
                                    try: os.remove(temp_recording_full_path)
                                    except OSError as e: print(f"Error removing recording file: {e}")
                                else:
                                    print(f"Recording file {temp_recording_full_path} invalid. Skipping upload.")
                            is_recording = False
                            print(f"\nReady for next action. ('{start_stop_key_name}' to Record, '{quit_key_name}' to Exit)")
            
            if should_quit_application: break

    except KeyboardInterrupt:
        print("\nExiting application due to KeyboardInterrupt.")
        if is_recording and current_recording_thread and current_recording_thread.is_alive():
            print("Stopping active recording due to interrupt...")
            audio_recorder._stop_event.set()
            current_recording_thread.join(timeout=2)
    except OSError as e: 
        print(f"OSError in gamepad read_loop (gamepad may have disconnected): {e}")
    except Exception as e:
        print(f"An unexpected error occurred in the application loop: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Gamepad object is closed by the caller (main.py)
        print("Application main loop finished.")
        # Final cleanup of temporary files is good practice here too
        if os.path.exists(temp_recording_full_path) and os.path.isfile(temp_recording_full_path):
            try: os.remove(temp_recording_full_path)
            except OSError: pass
        
        response_audio_final_path = os.path.join(config.TEMP_DIR, config.TEMP_RESPONSE_FILENAME)
        if os.path.exists(response_audio_final_path) and os.path.isfile(response_audio_final_path):
            try: os.remove(response_audio_final_path)
            except OSError: pass
