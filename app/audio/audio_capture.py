"""
Audio capture module for the video chat application.
"""

import threading
import time
import logging
import queue
import numpy as np
import sounddevice as sd


class AudioCapture:
    """
    Handles audio capture from the microphone and provides audio frames for streaming.
    """
    
    def __init__(self, callback=None, sample_rate=44100, channels=1, 
                 chunk_size=1024, device_id=None):
        """
        Initialize the audio capture.
        
        Args:
            callback: Optional callback function to be called with each audio chunk
            sample_rate: Sample rate in Hz (default: 44100)
            channels: Number of audio channels (default: 1 for mono)
            chunk_size: Number of frames per buffer (default: 1024)
            device_id: Audio device ID (default: None for system default)
        """
        self.callback = callback
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.device_id = device_id
        
        self.is_running = False
        self.stream = None
        self.audio_thread = None
        self.frame_number = 0
        
        # Queue for audio data
        self.audio_queue = queue.Queue(maxsize=100)
        
        # Get available devices
        self.devices = sd.query_devices()
        
    def start(self):
        """
        Start capturing audio from the microphone.
        
        Returns:
            bool: True if started successfully, False otherwise
        """
        if self.is_running:
            return True
            
        try:
            self.is_running = True
            self.frame_number = 0
            
            # Start the audio stream
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                callback=self._audio_callback,
                blocksize=self.chunk_size,
                device=self.device_id
            )
            self.stream.start()
            
            # Start the processing thread
            self.audio_thread = threading.Thread(target=self._process_audio)
            self.audio_thread.daemon = True
            self.audio_thread.start()
            
            return True
        except Exception as e:
            logging.error(f"Error starting audio capture: {e}")
            self.is_running = False
            return False
            
    def stop(self):
        """
        Stop the audio capture.
        
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
            
        if self.audio_thread:
            # Wait for the thread to finish
            self.audio_thread.join(timeout=1.0)
            self.audio_thread = None
            
        # Clear the queue
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
                
        return True
        
    def _audio_callback(self, indata, frames, time_info, status):
        """
        Callback function for the audio stream.
        
        Args:
            indata: Input audio data
            frames: Number of frames
            time_info: Time information
            status: Status information
        """
        if status:
            logging.warning(f"Audio callback status: {status}")
            
        # Add the audio data to the queue
        try:
            self.audio_queue.put_nowait(indata.copy())
        except queue.Full:
            logging.warning("Audio queue is full, dropping frame")
            
    def _process_audio(self):
        """
        Process audio data from the queue.
        """
        while self.is_running:
            try:
                # Get audio data from the queue
                audio_data = self.audio_queue.get(timeout=0.1)
                
                # Increment frame number
                self.frame_number += 1
                
                # Call the callback if provided
                if self.callback:
                    self.callback(audio_data, self.sample_rate, self.channels, 
                                 self.frame_number)
                    
            except queue.Empty:
                # No audio data available, just continue
                continue
            except Exception as e:
                logging.error(f"Error processing audio: {e}")
                
    def get_devices(self):
        """
        Get a list of available audio devices.
        
        Returns:
            list: List of available audio devices
        """
        return self.devices
        
    def is_active(self):
        """
        Check if the audio capture is active.
        
        Returns:
            bool: True if active, False otherwise
        """
        return self.is_running and self.stream is not None 