# gamepad_manager.py
"""
Manages gamepad detection and the main application loop with states and video playback.
"""
import os
import sys
import time
import select
from evdev import InputDevice, categorize, ecodes, list_devices

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
                # This 'dev' might not have been fully initialized or might be None
                # The cleanup loop handles devices in opened_devices_for_cleanup
                pass
    except Exception as e:
        print(f"Error listing/filtering devices: {e}.")
        for dev_to_close in opened_devices_for_cleanup: # Ensure all opened are attempted to be closed
            try: dev_to_close.close()
            except: pass
        return None
    if not monitored_devices_map:
        print("No gamepad-like devices found to monitor."); 
        for dev_to_close in opened_devices_for_cleanup: # Close all scanned devices
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
                    if event.type == ecodes.EV_KEY and event.value == 1:
                        print(f"\nButton press on: {device_that_fired.name} ({device_that_fired.path})")
                        detected_device_object = device_that_fired; break 
                if detected_device_object: break 
            except Exception as e: print(f"Error reading from {device_that_fired.path}: {e}")
            if detected_device_object: break
            
    # Close all monitored devices EXCEPT the one that was detected (if any)
    for fd_to_close, dev_to_close in monitored_devices_map.items():
        if detected_device_object and dev_to_close.fd == detected_device_object.fd:
            continue 
        try: dev_to_close.close()
        except: pass
    
    # Also close any devices from the initial scan that weren't monitored and aren't the detected one
    for dev_to_clean in opened_devices_for_cleanup:
        is_detected_device = detected_device_object and dev_to_clean.path == detected_device_object.path
        was_monitored = dev_to_clean.fd in monitored_devices_map # Check if it was even in the map

        if not is_detected_device:
            # If it was monitored, it's already handled by the loop above.
            # If not monitored, it means it was opened but filtered out before select.
            # This check ensures we don't try to double-close or close if it wasn't monitored.
            # The simplest here is just to ensure that if it's not the detected one, it's closed.
             try:
                 # Check if it was the one we are returning, if so, don't close
                 if not (detected_device_object and dev_to_clean.fd == detected_device_object.fd):
                    dev_to_clean.close()
             except: pass
    return detected_device_object


def run_application_loop(gamepad_device_object):
    global current_app_state 
    
    gamepad = gamepad_device_object
    print(f"\nApplication ready. Using gamepad: {gamepad.name}")
    
    # Correctly get button names from codes
    start_stop_key_name = ecodes.bytype[ecodes.EV_KEY].get(config.BTN_ACTION_START_STOP, f"Code {config.BTN_ACTION_START_STOP}")
    quit_key_name = ecodes.bytype[ecodes.EV_KEY].get(config.BTN_ACTION_QUIT, f"Code {config.BTN_ACTION_QUIT}")
    
    current_app_state = STATE_IDLE
    # The video path in config is already "videos/idle.mp4" etc.
    video_manager.start_looping_video(config.VIDEO_IDLE) 
    print(f"--- STATE: {current_app_state} ---")
    print(f"Controls: Press '{start_stop_key_name}' to Start. Press '{quit_key_name}' to Exit.")

    if not os.path.exists(config.TEMP_DIR):
        os.makedirs(config.TEMP_DIR, exist_ok=True)
    temp_recording_full_path = os.path.join(config.TEMP_DIR, config.TEMP_RECORDING_FILENAME)
    
    current_recording_thread = None
    should_quit_application = False

    try:
        for event in gamepad.read_loop(): 
            if should_quit_application: break

            if event.type == ecodes.EV_KEY:
                # --- FIX 1: Move categorize here ---
                key_event = categorize(event) 
                if key_event.keystate == ecodes.KeyEvent.key_down: # Process only on button press
                    
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
                            video_manager.start_looping_video(config.VIDEO_LISTENING) # Pass full relative path
                            print(f"--- STATE: {current_app_state} ---")
                            current_recording_thread = audio_recorder.start_recording_thread(config.TEMP_RECORDING_FILENAME)
                            if current_recording_thread:
                                print(f"RECORDING STARTED. Press '{start_stop_key_name}' again to STOP.")
                            else:
                                print("Failed to start recording thread. Returning to IDLE.")
                                current_app_state = STATE_IDLE
                                video_manager.start_looping_video(config.VIDEO_IDLE)
                                print(f"--- STATE: {current_app_state} ---")
                                print(f"Controls: Press '{start_stop_key_name}' to Start. Press '{quit_key_name}' to Exit.")

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
                            print(f"Controls: Press '{start_stop_key_name}' to Start. Press '{quit_key_name}' to Exit.")
            if should_quit_application: break
    # ... (rest of the try...except...finally block as before) ...
    except KeyboardInterrupt: print("\nExiting application due to KeyboardInterrupt.") # ... (cleanup as before)
    except OSError as e: print(f"OSError in gamepad read_loop (gamepad disconnected?): {e}")
    except Exception as e: print(f"Unexpected error in application loop: {e}"); import traceback; traceback.print_exc()
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
