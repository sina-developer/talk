import pyaudio

print("PyAudio version:", pyaudio.__version__)
p = pyaudio.PyAudio()

print("\n--- Default Input Device Info ---")
try:
    default_input_device_info = p.get_default_input_device_info()
    print(f"Index: {default_input_device_info['index']}")
    print(f"Name: {default_input_device_info['name']}")
    print(f"Default Sample Rate: {default_input_device_info['defaultSampleRate']}")
    print(f"Max Input Channels: {default_input_device_info['maxInputChannels']}")

    # Test specific sample rates for the default input device
    rates_to_check = [44100, 48000, 32000, 16000, 8000]
    for rate in rates_to_check:
        try:
            is_supported = p.is_format_supported(
                rate=rate,
                input_device=default_input_device_info['index'],
                input_channels=1, # Assuming mono
                input_format=pyaudio.paInt16
            )
            print(f"  Is {rate} Hz supported by default input device? {is_supported}")
        except pyaudio.PaError as e:
            print(f"  Could not check format support for {rate} Hz on default device: {e}")
except IOError as e:
    print(f"Could not get default input device info: {e} (This might mean no default input device is configured or found by PortAudio/ALSA)")

print("\n--- All Available Audio Devices ---")
num_devices = p.get_device_count()
if num_devices == 0:
    print("No audio devices found by PyAudio.")

for i in range(num_devices):
    dev_info = p.get_device_info_by_index(i)
    if dev_info.get('maxInputChannels', 0) > 0: # Check if it's an input device
        print(f"\nInput Device ID {i} - {dev_info.get('name', 'Unknown Device')}")
        print(f"  Host API: {dev_info.get('hostApi')_info.get('name', 'Unknown API')}") # Shows ALSA, etc.
        print(f"  Default Sample Rate: {dev_info.get('defaultSampleRate', 'N/A')}")
        print(f"  Max Input Channels: {dev_info.get('maxInputChannels', 'N/A')}")
        
        # Test specific sample rates for this device
        rates_to_check = [44100, 48000, 32000, 16000, 8000]
        for rate in rates_to_check:
            try:
                is_supported = p.is_format_supported(
                    rate=rate,
                    input_device=dev_info['index'],
                    input_channels=1, # Assuming mono
                    input_format=pyaudio.paInt16
                )
                print(f"  Supports {rate} Hz (1 ch, 16-bit): {is_supported}")
            except pyaudio.PaError: # Catch specific error for format check
                print(f"  Format (1 ch, 16-bit) not directly supported or check failed for {rate} Hz")
        print("-" * 20)

p.terminate()