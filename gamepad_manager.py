# gamepad_manager.py
"""
Manages gamepad detection and the main application loop with states and video playback.
"""
import os
import sys
import time
import select
from evdev import InputDevice, categorize, ecodes, list_devices # KeyEvent is in evdev.events

import config
import audio_recorder
import audio_uploader
import audio_player
import video_manager 

# --- Application States ---
STATE_IDLE = "IDLE"
STATE_LISTENING = "LISTENING"
STATE_THINKING = "THINKING" 
STATE_TALKING = "TALKING"  

def detect_gamepad_interactively(timeout_seconds=config.GAMEPAD_DETECT_TIMEOUT_S):
    # ... (This function remains the same as the last version you have - no changes needed here) ...
    print(f"\n--- Interactive Gamepad Detection ---")
    print(f"Please press ANY button on your desired gamepad within {timeout_seconds} seconds...")
    print("Scanning for input devices...")
    monitored_devices_map = {}; opened_devices_for_cleanup = []
    try:
        all_device_paths = list_devices()
        if not all_device_paths: print("No input devices found."); return None
        # print(f"Found {len(all_device_paths)} potential input devices. Filtering for gamepads...") # Less verbose
        for path in all_device_paths:
            dev = None
            try:
                dev = InputDevice(path); opened_devices_for_cleanup.append(dev)
                capabilities = dev.capabilities(verbose=False)
                if ecodes.EV_KEY in capabilities and \
                   any(code in capabilities[ecodes.EV_KEY] for code in [
                       ecodes.BTN_GAMEPAD, ecodes.BTN_SOUTH, ecodes.BTN_EAST, ecodes.BTN_NORTH, ecodes.BTN_WEST,
                       ecodes.BTN_A, ecodes.BTN_B, ecodes.BTN_C, ecodes.BTN_X, ecodes.BTN_Y, ecodes.BTN_Z,
                       ecodes.BTN_START, ecodes.BTN_SELECT, ecodes.BTN_MODE, ecodes.BTN_JOYSTICK, 
                       ecodes.BTN_TRIGGER, ecodes.BTN_THUMB, ecodes.BTN_THUMB2, ecodes.BTN_DPAD_UP, 
                       ecodes.BTN_DPAD_DOWN, ecodes.BTN_DPAD_LEFT, ecodes.BTN_DPAD_RIGHT
                   ]):
                    monitored_devices_map[dev.fd] = dev
                # else: # Device doesn't have typical gamepad keys
                #     pass # It will be closed in the cleanup loop
            except Exception: 
                pass
    except Exception as e:
        print(f"Error listing/filtering devices: {e}.")
        for dev_to_close in opened_devices_for_cleanup: 
            try: dev_to_close.close()
            except: pass
        return None
    if not monitored_devices_map:
        print("No gamepad-like devices found to monitor."); 
        for dev_to_close in opened_devices_for_cleanup: 
            try: dev_to_close.close()
            except: pass
        return None
    
    print(f"Monitoring {len(monitored_devices_map)} potential gamepad(s) for a button press...")
    readable_fds, _, _ = select.select(monitored_devices_map.keys(), [], [], timeout_seconds)
    detected_device_object = None
    if not readable_fds: print(f"No gamepad press detected within {timeout_seconds}s.")
    else:
        for fd in readable_fds:
            device_that_fired = monitored_devices_map[fd]
            try:
                for event in device_that_fired.read(): 
                    if event.type == ecodes.EV_KEY and event.value == 1: # event.value == 1 is key_down
                        print(f"\nButton press on: {device_that_fired.name} ({device_that_fired.path})")
                        detected_device_object = device_that_fired; break 
                if detected_device_object: break 
            except Exception as e: print(f"Error reading from {device_that_fired.path}: {e}")
            if detected_device_object: break
            
    for fd_to_close, dev_to_close in monitored_devices_map.items():
        if detected_device_object and dev_to_close.fd == detected_device_object.fd:
            continue 
        try: dev_to_close.close()
        except: pass
    
    for dev_to_clean in opened_devices_for_cleanup:
        is_detected_device = detected_device_object and dev_to_clean.path == detected_device_object.path
        if not is_detected_device:
             try:
                 if not (detected_device_object and dev_to_clean.fd == detected_device_object.fd):
                    dev_to_clean.close()
             except: pass
    return detected_device_object


def get_user_friendly_button_name(button_code, default_name_if_list=None):
    """Gets a user-friendly name for a button code."""
    name_or_list = ecodes.bytype[ecodes.EV_KEY].get(button_code)
    if isinstance(name_or_list, list):
        if default_name_if_list and default_name_if_list in name_or_list:
            return default_name_if_list
        # Try to pick a common or primary name from the list
        if 'BTN_A' in name_or_list: return 'BTN_A (A)'
        if 'BTN_SOUTH' in name_or_list: return 'BTN_SOUTH (A)'
        if 'BTN_B' in name_or_list: return 'BTN_B (B)'
        if 'BTN_EAST' in name_or_list: return 'BTN_EAST (B)'
        if 'BTN_X' in name_or_list: return 'BTN_X (X)'
        if 'BTN_WEST' in name_or_list: return 'BTN_WEST (X)'
        if 'BTN_Y' in name_or_list: return 'BTN_Y (Y)'
        if 'BTN_NORTH' in name_or_list: return 'BTN_NORTH (Y)'
        if 'BTN_START' in name_or_list: return 'BTN_START (Start)'
        if 'BTN_SELECT' in name_or_list: return 'BTN_SELECT (Select)'
        return name_or_list[0] # Fallback to the first name in the list
    elif name_or_list:
        return name_or_list
    else:
        return f"Code {button_code}"

def run_application_loop(gamepad_device_object):
    global current_app_state 
    
    gamepad = gamepad_device_object
    print(f"\nApplication ready. Using gamepad: {gamepad.name}")
    
    # Get user-friendly button names for prompts
    start_stop_key_name = get_user_friendly_button_name(config.BTN_ACTION_START_STOP, 'BTN_SOUTH') # Prefer BTN_SOUTH if available
    quit_key_name = get_user_friendly_button_name(config.BTN_ACTION_QUIT, 'BTN_START') # Prefer BTN_START

    current_app_state = STATE_IDLE
    video_manager.start_looping_video(config.VIDEO_IDLE) 
    print(f"--- STATE: {current_app_state} ---")
    print(f"Controls: Press '{start_stop_key_name}' to Start/Stop. Press '{quit_key_name}' to Exit.")

    if not os.path.exists(config.TEMP_DIR):
        os.makedirs(config.TEMP_DIR, exist_ok=True)
    temp_recording_full_path = os.path.join(config.TEMP_DIR, config.TEMP_RECORDING_FILENAME)
    
    current_recording_thread = None
    should_quit_application = False

    try:
        for event in gamepad.read_loop(): 
            if should_quit_application: break

            if event.type == ecodes.EV_KEY:
                key_event = categorize(event) 
                # --- FIX for AttributeError: Use key_event.key_down (instance attribute) ---
                # key_event.key_down is 1, key_event.key_up is 0, key_event.key_hold is 2
                if key_event.keystate == key_event.key_down: # This checks if the button was just pressed
                    
                    if event.code == config.BTN_ACTION_QUIT:
                        print(f"'{quit_key_name}' pressed. Signaling exit...")
                        should_quit_application = True
                        if current_app_state == STATE_LISTENING and current_recording_thread and current_recording_thread.is_alive():
                            print("Stopping active recording before quitting...")
                            audio_recorder._stop_event.set() 
                            current_recording_thread.join(timeout=2) 
                        break 

                    elif event.code == config.BTN_ACTION_START_STOP:
                        if current_app_state == STATE_IDLE:
                            print(f"'{start_stop_key_name}' pressed in IDLE state.")
                            current_app_state = STATE_LISTENING
                            video_manager.start_looping_video(config.VIDEO_LISTENING)
                            print(f"--- STATE: {current_app_state} ---")
                            current_recording_thread = audio_recorder.start_recording_thread(config.TEMP_RECORDING_FILENAME)
                            if current_recording_thread:
                                print(f"RECORDING STARTED. Press '{start_stop_key_name}' again to STOP.")
                            else:
                                print("Failed to start recording thread. Returning to IDLE.")
                                current_app_state = STATE_IDLE
                                video_manager.start_looping_video(config.VIDEO_IDLE)
                                print(f"--- STATE: {current_app_state} ---")
                                print(f"Controls: Press '{start_stop_key_name}' to Start/Stop. Press '{quit_key_name}' to Exit.")

                        elif current_app_state == STATE_LISTENING:
                            print(f"'{start_stop_key_name}' pressed in LISTENING state. Stopping recording...")
                            if audio_recorder.stop_and_save_recording(current_recording_thread, config.TEMP_RECORDING_FILENAME):
                                if os.path.exists(temp_recording_full_path) and os.path.getsize(temp_recording_full_path) > 44:
                                    current_app_state = STATE_THINKING
                                    video_manager.start_looping_video(config.VIDEO_THINKING)
                                    print(f"--- STATE: {current_app_state} ---")
                                    print("Uploading and waiting for server response...")
                                    response_audio_path = audio_uploader.upload_audio(temp_recording_full_path)
                                    if response_audio_path:
                                        current_app_state = STATE_TALKING
                                        video_manager.start_looping_video(config.VIDEO_TALKING)
                                        print(f"--- STATE: {current_app_state} ---")
                                        print("Playing server response...")
                                        audio_player.play_audio_external(response_audio_path)
                                        try: os.remove(response_audio_path)
                                        except OSError as e: print(f"Error removing response file: {e}")
                                    else: print("No audio response or error during upload.")
                                    try: os.remove(temp_recording_full_path)
                                    except OSError as e: print(f"Error removing recording file: {e}")
                                else: print(f"Recording file {temp_recording_full_path} invalid. Not uploading.")
                            else: print("Failed to save recording or recording was empty.")
                            current_app_state = STATE_IDLE
                            video_manager.start_looping_video(config.VIDEO_IDLE)
                            print(f"--- STATE: {current_app_state} ---")
                            print(f"Controls: Press '{start_stop_key_name}' to Start/Stop. Press '{quit_key_name}' to Exit.")
            if should_quit_application: break
    except KeyboardInterrupt: 
        print("\nExiting application due to KeyboardInterrupt.")
        if current_app_state == STATE_LISTENING and current_recording_thread and current_recording_thread.is_alive():
            print("Stopping active recording..."); audio_recorder._stop_event.set(); current_recording_thread.join(timeout=2)
    except OSError as e: 
        print(f"OSError in gamepad read_loop (gamepad disconnected?): {e}")
    except Exception as e: 
        print(f"Unexpected error in application loop: {e}"); import traceback; traceback.print_exc()
    finally:
        video_manager.stop_current_video() 
        print("Application main loop finished.")
        if os.path.exists(temp_recording_full_path) and os.path.isfile(temp_recording_full_path):
            try: os.remove(temp_recording_full_path)
            except OSError: pass
        response_audio_final_path = os.path.join(config.TEMP_DIR, config.TEMP_RESPONSE_FILENAME)
        if os.path.exists(response_audio_final_path) and os.path.isfile(response_audio_final_path):
            try: os.remove(response_audio_final_path)
            except OSError: pass
