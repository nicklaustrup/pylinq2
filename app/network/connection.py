"""
Network connection module for video chat application.
"""

import socket
import threading
import json
import logging
import time
import queue
import pickle
from typing import Callable, Dict, Any, Optional, List, Tuple

from app.network.protocol_pb2 import (
    VideoMessage, VideoFrame, AudioFrame, ControlMessage, StatusMessage,
    ControlType, StatusType
)


class Connection:
    """
    Handles network connections for video streaming.
    """
    
    def __init__(self, on_video_frame=None, on_audio_frame=None,
                 on_control=None, on_status=None, on_connect=None,
                 on_disconnect=None):
        """
        Initialize the connection handler.
        
        Args:
            on_video_frame: Callback for video frames
            on_audio_frame: Callback for audio frames
            on_control: Callback for control messages
            on_status: Callback for status messages
            on_connect: Callback when a connection is established
            on_disconnect: Callback when a connection is closed
        """
        self.socket = None
        self.client_socket = None
        self.is_server = False
        self.is_connected = False
        self.is_running = False
        self.recv_thread = None
        self.send_thread = None
        
        # Callbacks
        self.on_video_frame = on_video_frame
        self.on_audio_frame = on_audio_frame
        self.on_control = on_control
        self.on_status = on_status
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        
        # Default port
        self.default_port = 8000
        
        # Message queue for sending
        self.send_queue = queue.Queue(maxsize=100)
        
        # Connection info
        self.remote_address = None
        self.local_address = None
        
        # Statistics
        self.bytes_sent = 0
        self.bytes_received = 0
        self.messages_sent = 0
        self.messages_received = 0
        self.last_ping_time = 0
        self.ping_interval = 5.0  # seconds
        
        # Heartbeat
        self.last_heartbeat = 0
        self.heartbeat_interval = 1.0  # seconds
        self.heartbeat_timeout = 10.0  # seconds
        
    def host(self, port=None):
        """
        Host a session, waiting for a client to connect.
        
        Args:
            port: Port to listen on (default: 5000)
            
        Returns:
            bool: True if hosting started successfully, False otherwise
        """
        if self.is_running:
            return False
            
        if port is None:
            port = self.default_port
            
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(('0.0.0.0', port))
            self.socket.listen(1)
            
            self.is_server = True
            self.is_running = True
            
            # Start the server thread
            self.recv_thread = threading.Thread(target=self._server_loop)
            self.recv_thread.daemon = True
            self.recv_thread.start()
            
            # Get local address
            self.local_address = (socket.gethostbyname(socket.gethostname()), port)
            
            logging.info(f"Hosting on {self.local_address[0]}:{self.local_address[1]}")
            
            return True
        except Exception as e:
            logging.error(f"Error hosting: {e}")
            if self.socket:
                self.socket.close()
                self.socket = None
            return False
            
    def connect(self, host, port=None):
        """
        Connect to a remote host.
        
        Args:
            host: Host address to connect to
            port: Port to connect to (default: 5000)
            
        Returns:
            bool: True if connection successful, False otherwise
        """
        if self.is_running:
            return False
            
        if port is None:
            port = self.default_port
            
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, port))
            
            self.is_server = False
            self.is_connected = True
            self.is_running = True
            
            # Set remote address
            self.remote_address = (host, port)
            
            # Get local address
            self.local_address = self.socket.getsockname()
            
            # Start the receive thread
            self.recv_thread = threading.Thread(target=self._client_loop)
            self.recv_thread.daemon = True
            self.recv_thread.start()
            
            # Start the send thread
            self.send_thread = threading.Thread(target=self._send_loop)
            self.send_thread.daemon = True
            self.send_thread.start()
            
            # Send a connect control message
            self._send_control(ControlType.CONNECT)
            
            # Call the connect callback
            if self.on_connect:
                self.on_connect()
                
            logging.info(f"Connected to {host}:{port}")
            
            return True
        except Exception as e:
            logging.error(f"Error connecting: {e}")
            if self.socket:
                self.socket.close()
                self.socket = None
            return False
            
    def disconnect(self):
        """
        Disconnect from the current session.
        
        Returns:
            bool: True if disconnected successfully
        """
        if not self.is_running:
            return True
            
        # Send a disconnect control message if connected
        if self.is_connected:
            try:
                self._send_control(ControlType.DISCONNECT)
            except Exception as e:
                logging.debug(f"Error sending disconnect message: {e}")
                
        self.is_running = False
        self.is_connected = False
        
        # Wait for threads to finish
        current_thread = threading.current_thread()
        
        if self.recv_thread and self.recv_thread != current_thread:
            self.recv_thread.join(timeout=1.0)
            self.recv_thread = None
            
        if self.send_thread and self.send_thread != current_thread:
            self.send_thread.join(timeout=1.0)
            self.send_thread = None
            
        # Close sockets
        if self.client_socket:
            try:
                self.client_socket.close()
            except Exception as e:
                logging.debug(f"Error closing client socket: {e}")
            self.client_socket = None
            
        if self.socket:
            try:
                self.socket.close()
            except Exception as e:
                logging.debug(f"Error closing socket: {e}")
            self.socket = None
            
        # Clear the queue
        while not self.send_queue.empty():
            try:
                self.send_queue.get_nowait()
            except queue.Empty:
                break
                
        # Call the disconnect callback
        if self.on_disconnect:
            self.on_disconnect()
            
        logging.info("Disconnected")
            
        return True
        
    def send_video_frame(self, frame_data, width, height, encoding, frame_number):
        """
        Send a video frame to the remote peer.
        
        Args:
            frame_data: Encoded video frame data
            width: Frame width
            height: Frame height
            encoding: Encoding format
            frame_number: Frame number
            
        Returns:
            bool: True if queued successfully, False otherwise
        """
        if not self.is_connected:
            return False
            
        # Create a video frame message
        video_frame = VideoFrame(
            frame_data=frame_data,
            width=width,
            height=height,
            encoding=encoding,
            frame_number=frame_number
        )
        
        # Create a video message
        message = VideoMessage(payload=video_frame)
        
        # Queue the message for sending
        return self._queue_message(message)
        
    def send_audio_frame(self, audio_data, sample_rate, channels, frame_number):
        """
        Send an audio frame to the remote peer.
        
        Args:
            audio_data: Audio data
            sample_rate: Sample rate
            channels: Number of channels
            frame_number: Frame number
            
        Returns:
            bool: True if queued successfully, False otherwise
        """
        if not self.is_connected:
            return False
            
        # Convert numpy array to bytes if needed
        if hasattr(audio_data, 'tobytes'):
            audio_bytes = audio_data.tobytes()
        else:
            audio_bytes = audio_data
            
        # Create an audio frame message
        audio_frame = AudioFrame(
            audio_data=audio_bytes,
            sample_rate=sample_rate,
            channels=channels,
            frame_number=frame_number
        )
        
        # Create a video message
        message = VideoMessage(payload=audio_frame)
        
        # Queue the message for sending
        return self._queue_message(message)
        
    def send_status(self, status_type, message, code=0):
        """
        Send a status message to the remote peer.
        
        Args:
            status_type: Status type (INFO, WARNING, ERROR)
            message: Status message
            code: Optional error code
            
        Returns:
            bool: True if queued successfully, False otherwise
        """
        if not self.is_connected:
            return False
            
        # Create a status message
        status = StatusMessage(
            type=status_type,
            message=message,
            code=code
        )
        
        # Create a video message
        message = VideoMessage(payload=status)
        
        # Queue the message for sending
        return self._queue_message(message)
        
    def _send_control(self, control_type, data=""):
        """
        Send a control message to the remote peer.
        
        Args:
            control_type: Control type
            data: Optional data for the control message
            
        Returns:
            bool: True if queued successfully, False otherwise
        """
        if not self.is_connected and control_type != ControlType.DISCONNECT:
            return False
            
        # Create a control message
        control = ControlMessage(
            type=control_type,
            data=data
        )
        
        # Create a video message
        message = VideoMessage(payload=control)
        
        # Queue the message for sending
        return self._queue_message(message)
        
    def _queue_message(self, message):
        """
        Queue a message for sending.
        
        Args:
            message: Message to queue
            
        Returns:
            bool: True if queued successfully, False otherwise
        """
        try:
            self.send_queue.put_nowait(message)
            return True
        except queue.Full:
            logging.warning("Send queue is full, dropping message")
            return False
            
    def _server_loop(self):
        """Internal method for the server connection loop."""
        try:
            logging.info("Waiting for connection...")
            
            # Wait for a client to connect
            self.client_socket, addr = self.socket.accept()
            self.is_connected = True
            self.remote_address = addr
            
            logging.info(f"Client connected from {addr[0]}:{addr[1]}")
            
            # Start the send thread
            self.send_thread = threading.Thread(target=self._send_loop)
            self.send_thread.daemon = True
            self.send_thread.start()
            
            # Call the connect callback
            if self.on_connect:
                self.on_connect()
                
            # Process incoming data
            self._process_incoming_data(self.client_socket)
        except Exception as e:
            if self.is_running:
                logging.error(f"Server error: {e}")
        finally:
            self.disconnect()
            
    def _client_loop(self):
        """Internal method for the client connection loop."""
        try:
            # Process incoming data
            self._process_incoming_data(self.socket)
        except Exception as e:
            if self.is_running:
                logging.error(f"Client error: {e}")
        finally:
            self.disconnect()
            
    def _send_loop(self):
        """Internal method for sending messages."""
        last_heartbeat = time.time()
        
        while self.is_running and self.is_connected:
            try:
                # Check if we need to send a heartbeat
                current_time = time.time()
                if current_time - last_heartbeat >= self.heartbeat_interval:
                    self._send_control(ControlType.PING)
                    last_heartbeat = current_time
                    
                # Get a message from the queue
                try:
                    message = self.send_queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                    
                # Convert the message to a dictionary
                message_dict = message.to_dict()
                
                # Serialize the message
                data = pickle.dumps(message_dict)
                
                # Add length prefix for message framing
                length = len(data)
                length_bytes = length.to_bytes(4, byteorder='big')
                
                # Send the length prefix and data
                if self.is_server:
                    self.client_socket.sendall(length_bytes + data)
                else:
                    self.socket.sendall(length_bytes + data)
                    
                # Update statistics
                self.bytes_sent += length + 4
                self.messages_sent += 1
                
            except Exception as e:
                if self.is_running and self.is_connected:
                    logging.error(f"Error sending message: {e}")
                    self.disconnect()
                break
                
    def _process_incoming_data(self, sock):
        """
        Process incoming data from the socket.
        
        Args:
            sock: Socket to read from
        """
        last_heartbeat = time.time()
        
        while self.is_running and self.is_connected:
            try:
                # Check for heartbeat timeout
                current_time = time.time()
                if current_time - last_heartbeat >= self.heartbeat_timeout:
                    logging.warning("Heartbeat timeout, disconnecting")
                    self.disconnect()
                    break
                    
                # Set a timeout for the socket
                sock.settimeout(1.0)
                
                # Read the length prefix (4 bytes)
                length_bytes = sock.recv(4)
                if not length_bytes or len(length_bytes) < 4:
                    if self.is_connected:
                        logging.debug("Connection closed by remote host")
                        self.disconnect()
                    break
                    
                # Convert length bytes to integer
                length = int.from_bytes(length_bytes, byteorder='big')
                
                # Read the data
                data_bytes = b''
                remaining = length
                while remaining > 0:
                    chunk = sock.recv(min(remaining, 4096))
                    if not chunk:
                        break
                    data_bytes += chunk
                    remaining -= len(chunk)
                    
                if len(data_bytes) < length:
                    if self.is_connected:
                        logging.warning("Incomplete message received")
                        self.disconnect()
                    break
                    
                # Update statistics
                self.bytes_received += length + 4
                self.messages_received += 1
                
                # Deserialize the message
                message_dict = pickle.loads(data_bytes)
                
                # Convert the dictionary to a VideoMessage
                message = VideoMessage.from_dict(message_dict)
                
                # Update last heartbeat time
                last_heartbeat = time.time()
                
                # Process the message based on its type
                payload = message.payload
                
                if isinstance(payload, VideoFrame):
                    # Video frame
                    if self.on_video_frame:
                        self.on_video_frame(
                            payload.frame_data,
                            payload.width,
                            payload.height,
                            payload.encoding,
                            payload.frame_number
                        )
                elif isinstance(payload, AudioFrame):
                    # Audio frame
                    if self.on_audio_frame:
                        self.on_audio_frame(
                            payload.audio_data,
                            payload.sample_rate,
                            payload.channels,
                            payload.frame_number
                        )
                elif isinstance(payload, ControlMessage):
                    # Control message
                    self._handle_control_message(payload)
                elif isinstance(payload, StatusMessage):
                    # Status message
                    if self.on_status:
                        self.on_status(
                            payload.type,
                            payload.message,
                            payload.code
                        )
                else:
                    logging.warning(f"Unknown message type: {type(payload)}")
                    
            except socket.timeout:
                # Socket timeout, just continue
                continue
            except Exception as e:
                if self.is_running and self.is_connected:
                    logging.error(f"Error processing data: {e}")
                    self.disconnect()
                break
                
    def _handle_control_message(self, control):
        """
        Handle a control message.
        
        Args:
            control: Control message
        """
        if control.type == ControlType.CONNECT:
            # Connection request
            logging.info("Received connection request")
            # Only respond if we're not already connected
            if not self.is_connected:
                # Send a connect response
                self._send_control(ControlType.CONNECT)
        elif control.type == ControlType.DISCONNECT:
            # Disconnect request
            logging.info("Received disconnect request")
            self.disconnect()
        elif control.type == ControlType.PING:
            # Ping request
            # Send a pong response
            self._send_control(ControlType.PONG)
        elif control.type == ControlType.PONG:
            # Pong response
            # Update ping time
            self.last_ping_time = time.time()
        elif control.type == ControlType.VIDEO_ON:
            # Video on
            logging.info("Remote video turned on")
            if self.on_control:
                self.on_control(control.type, control.data)
        elif control.type == ControlType.VIDEO_OFF:
            # Video off
            logging.info("Remote video turned off")
            if self.on_control:
                self.on_control(control.type, control.data)
        elif control.type == ControlType.AUDIO_ON:
            # Audio on
            logging.info("Remote audio turned on")
            if self.on_control:
                self.on_control(control.type, control.data)
        elif control.type == ControlType.AUDIO_OFF:
            # Audio off
            logging.info("Remote audio turned off")
            if self.on_control:
                self.on_control(control.type, control.data)
        else:
            logging.warning(f"Unknown control type: {control.type}")
            
    def get_statistics(self):
        """
        Get connection statistics.
        
        Returns:
            dict: Connection statistics
        """
        return {
            "bytes_sent": self.bytes_sent,
            "bytes_received": self.bytes_received,
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "connected": self.is_connected,
            "remote_address": self.remote_address,
            "local_address": self.local_address
        }
        
    def is_hosting(self):
        """
        Check if this connection is hosting a session.
        
        Returns:
            bool: True if hosting, False otherwise
        """
        return self.is_server and self.is_running
        
    def is_client(self):
        """
        Check if this connection is a client.
        
        Returns:
            bool: True if client, False otherwise
        """
        return not self.is_server and self.is_running
        
    def set_video_state(self, enabled):
        """
        Set the video state and notify the remote peer.
        
        Args:
            enabled: True to enable video, False to disable
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_connected:
            return False
            
        control_type = ControlType.VIDEO_ON if enabled else ControlType.VIDEO_OFF
        return self._send_control(control_type)
        
    def set_audio_state(self, enabled):
        """
        Set the audio state and notify the remote peer.
        
        Args:
            enabled: True to enable audio, False to disable
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_connected:
            return False
            
        control_type = ControlType.AUDIO_ON if enabled else ControlType.AUDIO_OFF
        return self._send_control(control_type) 