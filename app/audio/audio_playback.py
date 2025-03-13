"""
Audio playback module for the video chat application.
"""

import threading
import logging
import queue
import numpy as np
import sounddevice as sd


class AudioPlayback:
    """
    Handles audio playback for received audio frames.
    """
    
    def __init__(self, sample_rate=44100, channels=1, device_id=None):
        """
        Initialize the audio playback.
        
        Args:
            sample_rate: Sample rate in Hz (default: 44100)
            channels: Number of channels (default: 1 for mono)
            device_id: Audio device ID (default: None for system default)
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.device_id = device_id
        self.volume = 1.0  # Default to full volume
        
        self.is_running = False
        self.stream = None
        
        # Queue for audio data
        self.audio_queue = queue.Queue(maxsize=100)
        
        # Get available devices
        self.devices = sd.query_devices()
        self.output_devices = [
            (i, d['name']) for i, d in enumerate(self.devices) 
            if d.get('max_output_channels', 0) > 0
        ]
        
    def start(self):
        """
        Start audio playback.
        
        Returns:
            bool: True if started successfully, False otherwise
        """
        if self.is_running:
            return True
            
        try:
            self.is_running = True
            
            # Start the audio stream
            self.stream = sd.OutputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                callback=self._audio_callback,
                device=self.device_id
            )
            self.stream.start()
            
            return True
        except Exception as e:
            logging.error(f"Error starting audio playback: {e}")
            self.is_running = False
            return False
            
    def stop(self):
        """
        Stop audio playback.
        
        Returns:
            bool: True if stopped successfully
        """
        if not self.is_running:
            return True
            
        self.is_running = False
        
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
            
        # Clear the queue
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
                
        return True
        
    def _audio_callback(self, outdata, frames, time_info, status):
        """
        Callback function for the audio stream.
        
        Args:
            outdata: Output audio buffer
            frames: Number of frames
            time_info: Time information
            status: Status information
        """
        if status:
            logging.warning(f"Audio callback status: {status}")
            
        try:
            # Get audio data from the queue
            audio_data = self.audio_queue.get_nowait()
            
            # Make sure the data is the right shape
            if audio_data.shape[0] < frames:
                # Not enough data, pad with zeros
                padding = np.zeros((frames - audio_data.shape[0], self.channels), 
                                  dtype=audio_data.dtype)
                audio_data = np.vstack((audio_data, padding))
            elif audio_data.shape[0] > frames:
                # Too much data, truncate
                audio_data = audio_data[:frames]
                
            # Apply volume control if defined
            if hasattr(self, 'volume'):
                audio_data = audio_data * self.volume
                
            # Copy the data to the output buffer
            outdata[:] = audio_data
            
        except queue.Empty:
            # No audio data available, output silence
            outdata.fill(0)
            
    def play_audio(self, audio_data, sample_rate, channels):
        """
        Queue audio data for playback.
        
        Args:
            audio_data: Audio data as numpy array
            sample_rate: Sample rate of the audio data
            channels: Number of channels in the audio data
            
        Returns:
            bool: True if queued successfully, False otherwise
        """
        if not self.is_running:
            return False
            
        try:
            # Convert audio data to numpy array if it's not already
            if not isinstance(audio_data, np.ndarray):
                audio_data = np.frombuffer(audio_data, dtype=np.float32)
                audio_data = audio_data.reshape(-1, channels)
                
            # Resample if needed
            if sample_rate != self.sample_rate:
                # Simple resampling by linear interpolation
                # In a real app, you'd use a proper resampling library
                ratio = self.sample_rate / sample_rate
                new_length = int(len(audio_data) * ratio)
                indices = np.arange(new_length) / ratio
                indices = indices.astype(np.int32)
                audio_data = audio_data[indices]
                
            # Convert channels if needed
            if channels != self.channels:
                if channels == 1 and self.channels == 2:
                    # Mono to stereo
                    audio_data = np.column_stack((audio_data, audio_data))
                elif channels == 2 and self.channels == 1:
                    # Stereo to mono
                    audio_data = np.mean(audio_data, axis=1, keepdims=True)
                    
            # Add the audio data to the queue
            self.audio_queue.put_nowait(audio_data)
            return True
            
        except queue.Full:
            logging.warning("Audio queue is full, dropping frame")
            return False
        except Exception as e:
            logging.error(f"Error queueing audio data: {e}")
            return False
            
    def get_output_devices(self):
        """
        Get a list of available output devices.
        
        Returns:
            list: List of (device_id, device_name) tuples
        """
        return self.output_devices
        
    def set_output_device(self, device_id):
        """
        Set the output device.
        
        Args:
            device_id: Device ID to use
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Stop the current stream
        was_running = self.is_running
        if was_running:
            self.stop()
            
        # Set the new device ID
        self.device_id = device_id
        
        # Restart if it was running
        if was_running:
            return self.start()
            
        return True
        
    def is_active(self):
        """
        Check if audio playback is active.
        
        Returns:
            bool: True if active, False otherwise
        """
        return self.is_running and self.stream is not None
        
    def set_volume(self, volume):
        """
        Set the volume level for audio playback.
        
        Args:
            volume: Volume level from 0.0 (mute) to 1.0 (full volume)
            
        Returns:
            bool: True if successful
        """
        # Ensure volume is within valid range
        volume = max(0.0, min(1.0, volume))
        
        # Store the volume level for use in audio processing
        self.volume = volume
        
        return True 