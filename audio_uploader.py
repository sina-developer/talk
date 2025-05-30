# audio_uploader.py
"""
Handles uploading audio files to a server.
"""
import requests
import os
import config

def upload_audio(filepath_to_upload):
    """
    Uploads an audio file to the specified URL and saves the response.
    Args:
        filepath_to_upload (str): The full path to the audio file to be uploaded.
    Returns:
        str: The path to the saved response audio file, or None on failure.
    """
    print(f"Uploading {filepath_to_upload} to {config.UPLOAD_URL}...")
    
    if not os.path.exists(filepath_to_upload) or os.path.getsize(filepath_to_upload) == 0:
        print(f"Error: File {filepath_to_upload} does not exist or is empty. Skipping upload.")
        return None

    try:
        with open(filepath_to_upload, 'rb') as f:
            # Assuming server expects the field name 'audio' and client sends it as a WAV
            files = {'audio': (os.path.basename(filepath_to_upload), f, 'audio/wav')}
            response = requests.post(config.UPLOAD_URL, files=files, timeout=30)
            response.raise_for_status() # Raises an HTTPError for bad responses (4XX or 5XX)

        print(f"Server Response Content-Type: {response.headers.get('Content-Type')}") # Useful for debugging

        if response.content:
            # Ensure TEMP_DIR exists for response file
            if not os.path.exists(config.TEMP_DIR):
                os.makedirs(config.TEMP_DIR, exist_ok=True)
            
            response_audio_path = os.path.join(config.TEMP_DIR, config.TEMP_RESPONSE_FILENAME)
            with open(response_audio_path, 'wb') as out_file:
                out_file.write(response.content)
            print(f"Audio response saved to {response_audio_path}")
            return response_audio_path
        else:
            print("No content in server response.")
            return None
            
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred during upload: {http_err}")
        # Attempt to print some of the error response text if available
        if hasattr(response, 'text') and response.text:
            print(f"Response body (text): {response.text[:500]}...")
        elif response.content: # If not text, maybe some other binary error
             print(f"Response body (binary, first 100 bytes): {response.content[:100]}...")
        return None
    except requests.exceptions.RequestException as e: # Catches other network issues
        print(f"Error uploading audio (RequestException): {e}")
        return None
    except Exception as e: # Catch-all for other unexpected errors
        print(f"An unexpected error occurred during upload: {e}")
        return None

