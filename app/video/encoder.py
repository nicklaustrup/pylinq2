"""
Video encoder/decoder module for the video chat application.
"""

import cv2
import numpy as np
import logging
from typing import Tuple, Optional


class VideoEncoder:
    """
    Handles video encoding and decoding for efficient streaming.
    """
    
    # Available encoding formats
    JPEG = "jpeg"
    H264 = "h264"
    
    def __init__(self, encoding=JPEG, quality=80):
        """
        Initialize the video encoder.
        
        Args:
            encoding: Encoding format (default: JPEG)
            quality: Encoding quality for JPEG (0-100, default: 80)
        """
        self.encoding = encoding
        self.quality = quality
        
        # For H.264 encoding
        if self.encoding == self.H264:
            # Try to use hardware acceleration if available
            try:
                self.codec = cv2.VideoWriter_fourcc(*'avc1')
                self.encoder = cv2.VideoWriter_fourcc(*'avc1')
            except Exception as e:
                logging.warning(f"H.264 hardware encoding not available: {e}")
                self.codec = cv2.VideoWriter_fourcc(*'X264')
                self.encoder = cv2.VideoWriter_fourcc(*'X264')
        
    def encode_frame(self, frame: np.ndarray) -> Tuple[bytes, int, int]:
        """
        Encode a video frame.
        
        Args:
            frame: Video frame as a numpy array (BGR format)
            
        Returns:
            Tuple containing:
                - Encoded frame data as bytes
                - Frame width
                - Frame height
        """
        height, width = frame.shape[:2]
        
        if self.encoding == self.JPEG:
            # JPEG encoding
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.quality]
            _, encoded_frame = cv2.imencode('.jpg', frame, encode_param)
            return encoded_frame.tobytes(), width, height
        elif self.encoding == self.H264:
            # H.264 encoding (simplified)
            # In a real application, you would use a proper H.264 encoder
            # This is a simplified version using JPEG as a fallback
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.quality]
            _, encoded_frame = cv2.imencode('.jpg', frame, encode_param)
            return encoded_frame.tobytes(), width, height
        else:
            raise ValueError(f"Unsupported encoding format: {self.encoding}")
    
    def decode_frame(self, encoded_data: bytes, width: int, height: int, 
                    encoding: str) -> Optional[np.ndarray]:
        """
        Decode an encoded video frame.
        
        Args:
            encoded_data: Encoded frame data
            width: Frame width
            height: Frame height
            encoding: Encoding format
            
        Returns:
            Decoded frame as a numpy array (BGR format), or None if decoding fails
        """
        try:
            if encoding == self.JPEG:
                # JPEG decoding
                frame_array = np.frombuffer(encoded_data, dtype=np.uint8)
                return cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
            elif encoding == self.H264:
                # H.264 decoding (simplified)
                # In a real application, you would use a proper H.264 decoder
                # This is a simplified version using JPEG as a fallback
                frame_array = np.frombuffer(encoded_data, dtype=np.uint8)
                return cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
            else:
                logging.error(f"Unsupported encoding format: {encoding}")
                return None
        except Exception as e:
            logging.error(f"Error decoding frame: {e}")
            return None 