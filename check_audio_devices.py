import pyaudio

print("PyAudio version:", pyaudio.__version__)
p = pyaudio.PyAudio()

print("\n--- Default Input Device Info ---")
default_input_device_info = None # Initialize
try:
    default_input_device_info = p.get_default_input_device_info()
    print(f"Index: {default_input_device_info['index']}")
    print(f"Name: {default_input_device_info['name']}")
    print(f"Default Sample Rate: {default_input_device_info['defaultSampleRate']}")
    print(f"Max Input Channels: {default_input_device_info['maxInputChannels']}")

    rates_to_check = [44100, 48000, 32000, 16000, 8000]
    print(f"Checking specific rates for default input device (Index {default_input_device_info['index']}):")
    for rate in rates_to_check:
        print(f"  Attempting to check rate: {rate} Hz...") # Print rate before check
        try:
            is_supported = p.is_format_supported(
                rate=rate,
                input_device=default_input_device_info['index'],
                input_channels=1, # Assuming mono
                input_format=pyaudio.paInt16
            )
            print(f"    Is {rate} Hz supported by default input device? {is_supported}")
        except ValueError as e: # Catch ValueError specifically, as seen in your traceback
            print(f"    Could not check format support for {rate} Hz on default device (ValueError): {e}")
        except Exception as e: # Catch any other exceptions during the check
            print(f"    Could not check format support for {rate} Hz on default device (Other Exception): {e}")
except IOError as e:
    print(f"Could not get default input device info: {e} (This might mean no default input device is configured or found by PortAudio/ALSA)")
except Exception as e:
    print(f"An unexpected error occurred while getting default input device info: {e}")


print("\n--- All Available Audio Devices ---")
num_devices = 0
try:
    num_devices = p.get_device_count()
except Exception as e:
    print(f"Error getting device count: {e}")

if num_devices == 0:
    print("No audio devices found by PyAudio.")

for i in range(num_devices):
    dev_info = None # Initialize
    try:
        dev_info = p.get_device_info_by_index(i)
        # Check if it's an input device by looking for maxInputChannels > 0
        if dev_info.get('maxInputChannels', 0) > 0:
            print(f"\nInput Device ID {i} - {dev_info.get('name', 'Unknown Device')}")
            try:
                host_api_info = p.get_host_api_info_by_index(dev_info.get('hostApi'))
                host_api_name = host_api_info.get('name', 'Unknown API')
                print(f"  Host API: {host_api_name} (Type Index: {host_api_info.get('type')})") # Type index is more reliable than name
            except Exception as e_host_api:
                print(f"  Host API: Error retrieving - {e_host_api}")
                
            print(f"  Default Sample Rate: {dev_info.get('defaultSampleRate', 'N/A')}")
            print(f"  Max Input Channels: {dev_info.get('maxInputChannels', 'N/A')}")
            
            rates_to_check = [44100, 48000, 32000, 16000, 8000]
            print(f"  Checking specific rates for device ID {i}:")
            for rate in rates_to_check:
                print(f"    Attempting to check rate: {rate} Hz...") # Print rate before check
                try:
                    is_supported = p.is_format_supported(
                        rate=rate,
                        input_device=dev_info['index'],
                        input_channels=1, # Assuming mono
                        input_format=pyaudio.paInt16
                    )
                    print(f"      Is {rate} Hz supported? {is_supported}")
                except ValueError as e: # Catch ValueError specifically
                    print(f"      Could not check format support for {rate} Hz (ValueError): {e}")
                except Exception as e: # Catch any other exceptions during the check
                    print(f"      Could not check format support for {rate} Hz (Other Exception): {e}")
            print("-" * 20)
    except Exception as e_dev_loop:
        print(f"\nError retrieving or processing info for device index {i}: {e_dev_loop}")

try:
    p.terminate()
except Exception as e:
    print(f"Error during PyAudio termination: {e}")