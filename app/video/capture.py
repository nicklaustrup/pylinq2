import cv2
import threading
import time
from PIL import Image
import customtkinter as ctk


class VideoCapture:
    """
    Handles video capture from the webcam and provides frames for display.
    """
    def __init__(self, callback=None):
        """
        Initialize the video capture.
        
        Args:
            callback: Optional callback function to be called with each frame
        """
        self.cap = None
        self.is_running = False
        self.video_thread = None
        self.callback = callback
        self.frame_size = (640, 480)
        
    def start(self, device_id=0):
        """
        Start capturing video from the specified device.
        
        Args:
            device_id: Camera device ID (default: 0 for primary webcam)
            
        Returns:
            bool: True if started successfully, False otherwise
        """
        if self.is_running:
            return True
            
        self.cap = cv2.VideoCapture(device_id)
        if not self.cap.isOpened():
            return False
            
        self.is_running = True
        self.video_thread = threading.Thread(target=self._update)
        self.video_thread.daemon = True
        self.video_thread.start()
        return True
        
    def stop(self):
        """
        Stop the video capture.
        
        Returns:
            bool: True if stopped successfully
        """
        self.is_running = False
        if self.video_thread:
            self.video_thread.join(timeout=1.0)
            
        if self.cap:
            self.cap.release()
            self.cap = None
            
        return True
        
    def _update(self):
        """
        Internal method to continuously update frames.
        """
        while self.is_running:
            ret, frame = self.cap.read()
            if not ret:
                break
                
            # Convert the frame to RGB (from BGR)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.resize(frame, self.frame_size)
            
            # If a callback is provided, call it with the frame
            if self.callback:
                self.callback(frame)
                
            time.sleep(0.03)  # ~30 FPS
            
    def get_frame(self):
        """
        Get the current frame from the camera.
        
        Returns:
            numpy.ndarray or None: The current frame if available, None otherwise
        """
        if not self.is_running or not self.cap:
            return None
            
        ret, frame = self.cap.read()
        if not ret:
            return None
            
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = cv2.resize(frame, self.frame_size)
        return frame
        
    def get_ctk_image(self, frame=None):
        """
        Convert a frame to a CTkImage for use with CustomTkinter.
        
        Args:
            frame: Optional frame to convert. If None, gets the current frame.
            
        Returns:
            ctk.CTkImage or None: The converted image if available
        """
        if frame is None:
            frame = self.get_frame()
            
        if frame is None:
            return None
            
        img = Image.fromarray(frame)
        return ctk.CTkImage(light_image=img, dark_image=img, 
                           size=(self.frame_size[0], self.frame_size[1]))
        
    def set_frame_size(self, width, height):
        """
        Set the frame size for captured video.
        
        Args:
            width: Frame width in pixels
            height: Frame height in pixels
        """
        self.frame_size = (width, height)
        
    def is_active(self):
        """
        Check if the video capture is active.
        
        Returns:
            bool: True if active, False otherwise
        """
        return self.is_running and self.cap is not None 