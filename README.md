# Video Chat Application

A simple video chat application that allows two users to connect and stream video to each other.

## Features

- Modern, clean user interface
- Video streaming between two users
- Audio streaming between two users
- Audio device selection for microphone and speakers
- Network connection handling with error recovery
- Video encoding/decoding for efficient transmission
- Statistics display for monitoring connection quality
- Simple to use and set up

## Preview


## Setup

1. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Run the application:
   ```
   python run.py
   ```

## Usage

1. **Host a Session**:
   - Enter a port number (default: 8000)
   - Click "Host Session"
   - Wait for a client to connect

2. **Connect to a Host**:
   - Enter the host address and port
   - Click "Connect"

3. **Video and Audio Controls**:
   - Toggle camera on/off
   - Toggle microphone on/off
   - Select microphone and speaker devices from the dropdown menus

4. **Disconnect**:
   - Click "Disconnect" to end the session

## Project Structure

- `run.py`: Entry point for the application
- `app/`: Contains the application code
  - `gui/`: GUI components
  - `video/`: Video streaming functionality
    - `capture.py`: Video capture from webcam
    - `encoder.py`: Video encoding/decoding
  - `audio/`: Audio streaming functionality
    - `audio_capture.py`: Audio capture from microphone
    - `audio_playback.py`: Audio playback for received audio
  - `network/`: Network connection handling
    - `connection.py`: Network connection management
    - `protocol_pb2.py`: Protocol buffer definitions

## Dependencies

- OpenCV: For video capture and processing
- Pillow: For image handling
- CustomTkinter: For modern UI components
- NumPy: For numerical operations
- PyAudio: For audio capture and playback
- SoundDevice: For audio streaming
- SoundFile: For audio file handling
- AV: For video encoding/decoding 