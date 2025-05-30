# wait_for_exit_input.py
"""
Listens for either an Enter key press from stdin or a specific gamepad button press.
Exits silently when either is detected or on timeout.
This script is intended to be called by a shell script.
"""
import sys
import select
import os
import termios # For raw keyboard input on Linux/macOS
import tty     # For raw keyboard input on Linux/macOS

# Attempt to import from your project's config and evdev from the venv
# This assumes this script is run with the venv's Python interpreter
# and that the main app_dir is in PYTHONPATH or it's run from there.
try:
    from evdev import InputDevice, ecodes, list_devices
    import config # Your existing config.py
except ImportError as e:
    # Fallback if run in a weird context, print to stderr so shell script doesn't show it as normal output
    sys.stderr.write(f"Error importing modules in wait_for_exit_input.py: {e}\n")
    sys.stderr.write("Ensure evdev is installed in the venv and config.py is accessible.\n")
    sys.exit(1) # Exit with error

# --- Configuration for this helper ---
# Use the quit button defined in your main config.py
GAMEPAD_BUTTON_TO_DETECT = config.BTN_ACTION_QUIT # e.g., ecodes.BTN_START
TIMEOUT_SECONDS = 60  # How long to wait for input before exiting automatically (e.g., 60 seconds)
                      # Set to 0 or None for indefinite wait (not recommended for unattended script)

def find_gamepad_for_exit_detection(button_to_check):
    """
    Tries to find any connected gamepad that has the specified button.
    Returns an opened InputDevice object or None.
    """
    try:
        device_paths = list_devices()
        for path in device_paths:
            try:
                dev = InputDevice(path)
                capabilities = dev.capabilities(verbose=False)
                if ecodes.EV_KEY in capabilities and button_to_check in capabilities[ecodes.EV_KEY]:
                    # Found a device that has the button we're looking for
                    return dev 
                dev.close() # Close if not suitable
            except Exception: # Ignore errors for individual devices (e.g., permission denied)
                if 'dev' in locals() and dev and dev.fd is not None:
                    try: dev.close()
                    except: pass
                continue
    except Exception as e:
        sys.stderr.write(f"Error listing devices in wait_for_exit_input.py: {e}\n")
        pass
    return None

def main():
    gamepad_device = None
    inputs_to_monitor = [sys.stdin] # Always listen for keyboard Enter

    # Try to find a gamepad that has the configured QUIT button
    gamepad_device = find_gamepad_for_exit_detection(GAMEPAD_BUTTON_TO_DETECT)

    if gamepad_device:
        # sys.stderr.write(f"wait_for_exit_input: Listening for Enter or button {GAMEPAD_BUTTON_TO_DETECT} on {gamepad_device.name}\n")
        inputs_to_monitor.append(gamepad_device) # Add its file descriptor to select()
    # else:
        # sys.stderr.write(f"wait_for_exit_input: Gamepad for button {GAMEPAD_BUTTON_TO_DETECT} not found. Listening for Enter key only.\n")

    # Set stdin to raw mode to capture Enter key immediately
    old_stdin_settings = None
    if sys.stdin.isatty(): # Check if stdin is a terminal
        try:
            old_stdin_settings = termios.tcgetattr(sys.stdin)
            tty.setraw(sys.stdin.fileno())
        except Exception as e:
            sys.stderr.write(f"Warning: Could not set stdin to raw mode: {e}\n")
            old_stdin_settings = None # Ensure it's None if setup failed

    # Use select to wait for input on either stdin or the gamepad device
    try:
        ready_to_read, _, _ = select.select(inputs_to_monitor, [], [], TIMEOUT_SECONDS)

        if not ready_to_read:
            # sys.stderr.write("wait_for_exit_input: Timeout waiting for input.\n")
            pass # Timeout, script will just exit
        else:
            for readable_input in ready_to_read:
                if readable_input == sys.stdin: # Keyboard input
                    key = sys.stdin.read(1) # Read one character
                    if key in ['\r', '\n']: # Check for Enter key (carriage return or newline)
                        # sys.stderr.write("wait_for_exit_input: Enter key detected.\n")
                        break # Exit loop, proceed to exit script
                elif gamepad_device and readable_input == gamepad_device: # Gamepad input
                    for event in gamepad_device.read(): # Read events from the gamepad
                        if event.type == ecodes.EV_KEY and \
                           event.code == GAMEPAD_BUTTON_TO_DETECT and \
                           event.value == 1: # Button press (value 1 = down)
                            # sys.stderr.write(f"wait_for_exit_input: Gamepad button {GAMEPAD_BUTTON_TO_DETECT} detected.\n")
                            break # Exit loop
                    else: # Inner loop didn't break
                        continue
                    break # Break outer loop too
    except Exception as e:
        # sys.stderr.write(f"Error during select/input read in wait_for_exit_input.py: {e}\n")
        pass
    finally:
        # Restore terminal settings for stdin
        if old_stdin_settings and sys.stdin.isatty():
            try:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_stdin_settings)
            except Exception as e_termios:
                 sys.stderr.write(f"Warning: Could not restore stdin settings: {e_termios}\n")
        # Close the gamepad device if it was opened
        if gamepad_device:
            try:
                gamepad_device.close()
            except Exception:
                pass
    
    # This script exits silently on success (input detected or timeout)
    # The calling shell script will simply continue after this script exits.
    sys.exit(0)

if __name__ == "__main__":
    main()