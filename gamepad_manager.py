# gamepad_manager.py
"""
Manages gamepad detection and the main application loop based on gamepad events.
"""
import os
import sys
import time
import threading # Though recording thread is in audio_recorder, this module might need it for timing/state
import select   # For detect_gamepad_by_press
from evdev import InputDevice, categorize, ecodes, list_devices

import config # For gamepad button mappings, paths, etc.
import audio_recorder
import audio_uploader
import audio_player

def auto_detect_gamepad_by_name_caps():
    """
    Attempts to find a suitable gamepad device path automatically by checking
    device names and capabilities. Non-interactive.
    Returns:
        str: The path to the detected gamepad, or None if not found.
    """
    print("Attempting auto-detection of gamepad by name/capabilities...")
    try:
        all_device_paths = list_devices()
    except Exception as e:
        print(f"Error listing input devices for auto-detect: {e}. Check permissions for /dev/input/*")
        return None
        
    if not all_device_paths:
        print("Auto-detect: No input devices found by evdev in /dev/input/*")
        return None

    potential_gamepads_opened = [] # Store (device_object, path)
    for path in all_device_paths:
        try:
            device = InputDevice(path)
            capabilities = device.capabilities(verbose=False)
            # Check for a broad range of common gamepad buttons
            has_gamepad_buttons = ecodes.EV_KEY in capabilities and \
                                  any(code in capabilities[ecodes.EV_KEY] for code in [
                                      ecodes.BTN_GAMEPAD, ecodes.BTN_SOUTH, ecodes.BTN_A, ecodes.BTN_EAST, 
                                      ecodes.BTN_B, ecodes.BTN_START, ecodes.BTN_SELECT, 
                                      ecodes.BTN_JOYSTICK, ecodes.BTN_TRIGGER, ecodes.BTN_LEFT, ecodes.BTN_RIGHT,
                                      ecodes.BTN_DPAD_UP, ecodes.BTN_DPAD_DOWN, 
                                      ecodes.BTN_MODE, ecodes.BTN_THUMB, ecodes.BTN_C, ecodes.BTN_X
                                  ])
            if has_gamepad_buttons:
                potential_gamepads_opened.append(device) # Keep device open for now
                # print(f"  Auto-detect: Found potential: {device.path} (Name: {device.name})") # Verbose
            else:
                device.close() # Not a gamepad, close it
        except Exception: 
            # Could fail to open if permissions are wrong or device is weird
            if 'device' in locals() and device and not device.fd is None:
                try: device.close()
                except: pass
            continue 

    if not potential_gamepads_opened:
        print("Auto-detect: No devices with typical gamepad button capabilities found.")
        return None

    # Prioritize devices whose names match keywords from config
    for device in potential_gamepads_opened:
        if any(keyword.lower() in device.name.lower() for keyword in config.GAMEPAD_PREFERRED_NAME_KEYWORDS):
            print(f"Auto-detect: Selected '{device.name}' ({device.path}) based on name keywords and capabilities.")
            path_to_return = device.path
            # Close all other opened potential gamepads
            for dev_to_close in potential_gamepads_opened:
                if dev_to_close.path != path_to_return:
                    try: dev_to_close.close()
                    except: pass
            return path_to_return
    
    # If no strong name match, return the first device found with gamepad capabilities
    first_gamepad = potential_gamepads_opened[0]
    print(f"Auto-detect: No strong name match. Selecting first found device with gamepad capabilities: {first_gamepad.name} ({first_gamepad.path})")
    path_to_return = first_gamepad.path
    for dev_to_close in potential_gamepads_opened: # Close all others
        if dev_to_close.path != path_to_return:
            try: dev_to_close.close()
            except: pass
    return path_to_return


def detect_gamepad_by_press():
    """
    Asks the user to press a button on their desired gamepad and identifies it.
    Returns:
        str: The path to the detected gamepad, or None if no press detected or error.
    """
    print(f"\n--- Interactive Gamepad Detection ---")
    print(f"Please press any button on your desired gamepad within {config.GAMEPAD_DETECT_TIMEOUT_S} seconds...")
    print("Listening for input events on potential gamepads...")

    monitored_devices_map = {} # Maps file descriptor (fd) to InputDevice object
    
    try:
        all_device_paths = list_devices()
        if not all_device_paths:
            print("No input devices found in /dev/input/* for interactive detection.")
            return None
        
        for path in all_device_paths:
            try:
                dev = InputDevice(path)
                # Pre-filter: only monitor devices that seem like gamepads based on capabilities
                capabilities = dev.capabilities(verbose=False)
                if ecodes.EV_KEY in capabilities and \
                   any(code in capabilities[ecodes.EV_KEY] for code in [
                       # Using a broad list of common gamepad buttons for filtering
                       ecodes.BTN_GAMEPAD, ecodes.BTN_SOUTH, ecodes.BTN_EAST, ecodes.BTN_NORTH, ecodes.BTN_WEST,
                       ecodes.BTN_A, ecodes.BTN_B, ecodes.BTN_C, ecodes.BTN_X, ecodes.BTN_Y, ecodes.BTN_Z,
                       ecodes.BTN_START, ecodes.BTN_SELECT, ecodes.BTN_MODE,
                       ecodes.BTN_JOYSTICK, ecodes.BTN_TRIGGER, ecodes.BTN_THUMB, ecodes.BTN_THUMB2,
                       ecodes.BTN_DPAD_UP, ecodes.BTN_DPAD_DOWN, ecodes.BTN_DPAD_LEFT, ecodes.BTN_DPAD_RIGHT
                   ]):
                    monitored_devices_map[dev.fd] = dev
                    # print(f"  Interactively Monitoring: {dev.name} ({dev.path})") # Can be verbose
                else:
                    dev.close() # Not a gamepad, close it immediately
            except Exception: 
                if 'dev' in locals() and dev and dev.fd is not None: 
                    try: dev.close()
                    except: pass
                pass # Ignore devices we can't open or check
    except Exception as e:
        print(f"Error listing or pre-filtering input devices for interactive detection: {e}.")
        # Clean up any opened devices before returning
        for dev_to_close in monitored_devices_map.values():
            try: dev_to_close.close()
            except: pass
        return None

    if not monitored_devices_map:
        print("No suitable gamepad-like devices found to monitor for a button press.")
        return None
    
    print(f"Monitoring {len(monitored_devices_map)} potential gamepad(s) for a button press...")

    # Monitor file descriptors for readability using select
    # This allows waiting for an event on any of the devices without busy-looping
    readable_fds, _, _ = select.select(monitored_devices_map.keys(), [], [], config.GAMEPAD_DETECT_TIMEOUT_S)

    detected_device_path = None
    if not readable_fds: # Timeout occurred
        print(f"No gamepad button press detected within {config.GAMEPAD_DETECT_TIMEOUT_S} seconds.")
    else:
        # Process the first event from the first device that became readable
        for fd in readable_fds:
            device = monitored_devices_map[fd]
            try:
                # Read all immediately available events for this fd to find a key down
                for event in device.read(): 
                    if event.type == ecodes.EV_KEY and event.value == 1: # Key down event
                        print(f"\nButton press detected on: {device.name} ({device.path})")
                        detected_device_path = device.path
                        break # Take the first button press on the first device
                if detected_device_path:
                    break # Exit outer loop once a device is identified
            except BlockingIOError: 
                # Should not happen if select reported it as readable, but handle defensively
                continue 
            except Exception as e: 
                print(f"Error reading from device {device.path} during interactive detection: {e}")
            if detected_device_path: break # Ensure we exit if detected inside inner loop
    
    # Close all monitored devices
    for dev_to_close in monitored_devices_map.values():
        try: dev_to_close.close()
        except: pass # Ignore errors on close

    return detected_device_path


def run_application_loop(actual_gamepad_path):
    """
    Main application loop, controlled by gamepad events.
    This function will orchestrate recording, uploading, and playback.
    """
    print(f"Attempting to use gamepad: {actual_gamepad_path}")
    try:
        gamepad = InputDevice(actual_gamepad_path)
        print(f"Successfully opened gamepad: {gamepad.name}")
        # Dynamically get key names for display
        start_stop_key_name = ecodes.KEY.get(config.BTN_ACTION_START_STOP, f"Code {config.BTN_ACTION_START_STOP}")
        quit_key_name = ecodes.KEY.get(config.BTN_ACTION_QUIT, f"Code {config.BTN_ACTION_QUIT}")
        print(f"Controls: Press '{start_stop_key_name}' to Start/Stop. Press '{quit_key_name}' to Quit.")
    except Exception as e:
        print(f"FATAL: Could not open gamepad device {actual_gamepad_path}: {e}")
        print("Ensure the path is correct, the gamepad is connected, and you have permissions (e.g., user in 'input' group).")
        return

    if not os.path.exists(config.TEMP_DIR):
        os.makedirs(config.TEMP_DIR, exist_ok=True)
    
    temp_recording_full_path = os.path.join(config.TEMP_DIR, config.TEMP_RECORDING_FILENAME)
    
    is_recording = False
    current_recording_thread = None
    should_quit_application = False

    try:
        for event in gamepad.read_loop(): # This blocks until an event occurs
            if should_quit_application:
                break

            if event.type == ecodes.EV_KEY:
                key_event = categorize(event)
                if key_event.keystate == key_event.key_down: # Process only on button press (not release)
                    # print(f"Gamepad Event: Code={event.code} ({key_event.keycode}), Value={event.value}") # For debugging

                    if event.code == config.BTN_ACTION_QUIT:
                        print("'Quit' button pressed. Signaling application to exit...")
                        should_quit_application = True
                        if is_recording and current_recording_thread and current_recording_thread.is_alive():
                            print("Stopping active recording before quitting...")
                            audio_recorder._stop_event.set() # Access module-level event
                            current_recording_thread.join(timeout=2) # Wait briefly
                        break # Exit the event loop immediately

                    elif event.code == config.BTN_ACTION_START_STOP:
                        if not is_recording:
                            print("'Start/Stop' button pressed. Starting recording...")
                            current_recording_thread = audio_recorder.start_recording_thread(config.TEMP_RECORDING_FILENAME)
                            if current_recording_thread:
                                is_recording = True
                                print("RECORDING STARTED. Press button again to STOP.")
                            else:
                                print("Failed to start recording thread.")
                        else:
                            print("'Start/Stop' button pressed. Stopping recording...")
                            if audio_recorder.stop_and_save_recording(current_recording_thread, config.TEMP_RECORDING_FILENAME):
                                # Check if the recording file was actually created and has content
                                if os.path.exists(temp_recording_full_path) and os.path.getsize(temp_recording_full_path) > 44: # WAV header size
                                    response_audio_path = audio_uploader.upload_audio(temp_recording_full_path)
                                    if response_audio_path:
                                        audio_player.play_audio_external(response_audio_path)
                                        try:
                                            os.remove(response_audio_path)
                                            # print(f"Cleaned up response audio: {response_audio_path}")
                                        except OSError as e:
                                            print(f"Error removing temporary response file: {e}")
                                    # else: (error already printed by upload_audio)
                                    
                                    try: # Clean up the local recording file
                                        os.remove(temp_recording_full_path)
                                        # print(f"Cleaned up recording: {temp_recording_full_path}")
                                    except OSError as e:
                                        print(f"Error removing temporary recording file: {e}")
                                else:
                                    print(f"Recording file {temp_recording_full_path} is missing, empty, or invalid. Skipping upload.")
                            # else: (error already printed by stop_and_save_recording)
                            is_recording = False
                            print("\nReady for next action. (Press Start/Stop or Quit)")
                    # else:
                        # print(f"Unmapped button pressed: code {event.code}") # For debugging new buttons
            
            if should_quit_application: # Check again in case quit was set by non-key event logic if any
                break

    except KeyboardInterrupt:
        print("\nExiting application due to KeyboardInterrupt.")
        if is_recording and current_recording_thread and current_recording_thread.is_alive():
            print("Stopping active recording due to interrupt...")
            audio_recorder._stop_event.set()
            current_recording_thread.join(timeout=2)
    except OSError as e: # This can happen if the gamepad disconnects
        print(f"OSError in gamepad read_loop (gamepad may have disconnected): {e}")
    except Exception as e:
        print(f"An unexpected error occurred in the application loop: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'gamepad' in locals() and gamepad: # Ensure gamepad was successfully opened
            try:
                gamepad.close()
            except Exception: pass # Suppress errors on close during shutdown
        print("Application main loop finished.")
        
        # Final cleanup of temporary files
        if os.path.exists(temp_recording_full_path) and os.path.isfile(temp_recording_full_path):
            try: os.remove(temp_recording_full_path)
            except OSError: pass
        
        response_audio_final_path = os.path.join(config.TEMP_DIR, config.TEMP_RESPONSE_FILENAME)
        if os.path.exists(response_audio_final_path) and os.path.isfile(response_audio_final_path):
            try: os.remove(response_audio_final_path)
            except OSError: pass

