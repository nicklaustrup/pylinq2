import customtkinter as ctk
import threading
import time
import logging
import cv2
import numpy as np

from app.video.capture import VideoCapture
from app.video.encoder import VideoEncoder
from app.audio.audio_capture import AudioCapture
from app.audio.audio_playback import AudioPlayback
from app.network.connection import Connection
from app.network.protocol_pb2 import ControlType, StatusType


# Set the appearance mode and default color theme
ctk.set_appearance_mode("System")  # Modes: System, Dark, Light
ctk.set_default_color_theme("blue")  # Themes: blue, green, dark-blue


class MainWindow:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Video Chat App")
        self.root.geometry("1200x700")
        self.root.minsize(800, 600)
        
        # Configure grid layout
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=3)
        self.root.grid_rowconfigure(0, weight=1)
        
        # Create the sidebar frame
        self.create_sidebar()
        
        # Create the main content frame
        self.create_main_content()
        
        # Initialize components
        self.init_components()
        
        # Set up event handlers
        self.setup_event_handlers()
        
    def init_components(self):
        """Initialize video, audio, and network components"""
        # Video components
        self.local_video_capture = VideoCapture(self.on_local_video_frame)
        self.video_encoder = VideoEncoder(
            encoding=VideoEncoder.JPEG, quality=80
        )
        self.video_frame_count = 0
        self.remote_frame = None
        
        # Audio components
        self.audio_capture = AudioCapture(
            callback=self.on_local_audio_frame,
            sample_rate=44100,
            channels=1,
            chunk_size=1024
        )
        self.audio_frame_count = 0
        
        # Audio playback
        self.audio_playback = AudioPlayback(
            sample_rate=44100,
            channels=1
        )
        self.audio_playback.start()
        
        # Network components
        self.connection = Connection(
            on_video_frame=self.on_remote_video_frame,
            on_audio_frame=self.on_remote_audio_frame,
            on_control=self.on_control_message,
            on_status=self.on_status_message,
            on_connect=self.on_connected,
            on_disconnect=self.on_disconnected
        )
        
        # State variables
        self.is_connected = False
        self.is_hosting = False
        self.video_enabled = False
        self.audio_enabled = False
        self.remote_video_enabled = False
        self.remote_audio_enabled = False
        
        # Statistics
        self.stats_update_interval = 1.0  # seconds
        self.last_stats_update = 0
        
        # Populate audio device dropdowns
        self.populate_audio_devices()
        
    def populate_audio_devices(self):
        """Populate the audio device dropdowns with available devices"""
        # Input devices
        input_devices = self.audio_capture.get_devices()
        input_device_names = [f"{i}: {d['name']}" for i, d in enumerate(input_devices) 
                             if d.get('max_input_channels', 0) > 0]
        if input_device_names:
            self.input_device_menu.configure(values=input_device_names)
            self.input_device_menu.set(input_device_names[0])
        
        # Output devices
        output_devices = self.audio_playback.get_output_devices()
        output_device_names = [f"{id}: {name}" for id, name in output_devices]
        if output_device_names:
            self.output_device_menu.configure(values=output_device_names)
            self.output_device_menu.set(output_device_names[0])
        
    def setup_event_handlers(self):
        """Set up event handlers for the application"""
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Set up periodic tasks
        self.root.after(
            int(self.stats_update_interval * 1000), 
            self.update_statistics
        )
        
    def create_sidebar(self):
        """Create the sidebar with controls and settings"""
        sidebar_frame = ctk.CTkFrame(self.root, width=200, corner_radius=0)
        sidebar_frame.grid(row=0, column=0, sticky="nsew")
        sidebar_frame.grid_rowconfigure(4, weight=1)
        
        # App title
        app_title = ctk.CTkLabel(
            sidebar_frame, 
            text="Video Chat", 
            font=ctk.CTkFont(size=20, weight="bold")
        )
        app_title.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        # Connection controls
        connection_frame = ctk.CTkFrame(sidebar_frame)
        connection_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        
        connection_label = ctk.CTkLabel(
            connection_frame, 
            text="Connection", 
            font=ctk.CTkFont(weight="bold")
        )
        connection_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        self.host_entry = ctk.CTkEntry(
            connection_frame, 
            placeholder_text="Host address"
        )
        self.host_entry.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        
        self.port_entry = ctk.CTkEntry(
            connection_frame, 
            placeholder_text="Port"
        )
        self.port_entry.insert(0, "8000")  # Default port
        self.port_entry.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        
        self.connect_button = ctk.CTkButton(
            connection_frame, 
            text="Connect", 
            command=self.connect
        )
        self.connect_button.grid(row=3, column=0, padx=10, pady=5, sticky="ew")
        
        self.host_button = ctk.CTkButton(
            connection_frame, 
            text="Host Session", 
            command=self.host_session
        )
        self.host_button.grid(row=4, column=0, padx=10, pady=5, sticky="ew")
        
        self.disconnect_button = ctk.CTkButton(
            connection_frame, 
            text="Disconnect", 
            command=self.disconnect,
            state="disabled"
        )
        self.disconnect_button.grid(
            row=5, column=0, padx=10, pady=5, sticky="ew"
        )
        
        # Video controls
        video_frame = ctk.CTkFrame(sidebar_frame)
        video_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        
        video_label = ctk.CTkLabel(
            video_frame, 
            text="Video Controls", 
            font=ctk.CTkFont(weight="bold")
        )
        video_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        self.camera_switch = ctk.CTkSwitch(
            video_frame, 
            text="Camera", 
            command=self.toggle_camera
        )
        self.camera_switch.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        
        self.mic_switch = ctk.CTkSwitch(
            video_frame, 
            text="Microphone", 
            command=self.toggle_mic
        )
        self.mic_switch.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        
        # Audio device selection
        audio_device_frame = ctk.CTkFrame(sidebar_frame)
        audio_device_frame.grid(
            row=3, column=0, padx=20, pady=10, sticky="ew"
        )
        
        audio_device_label = ctk.CTkLabel(
            audio_device_frame, 
            text="Audio Devices", 
            font=ctk.CTkFont(weight="bold")
        )
        audio_device_label.grid(
            row=0, column=0, padx=10, pady=5, sticky="w"
        )
        
        # Input device selection
        input_label = ctk.CTkLabel(
            audio_device_frame, 
            text="Microphone:"
        )
        input_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        
        self.input_device_menu = ctk.CTkOptionMenu(
            audio_device_frame, 
            values=["Default"], 
            command=self.change_input_device
        )
        self.input_device_menu.grid(
            row=2, column=0, padx=10, pady=5, sticky="ew"
        )
        
        # Output device selection
        output_label = ctk.CTkLabel(
            audio_device_frame, 
            text="Speaker:"
        )
        output_label.grid(row=3, column=0, padx=10, pady=5, sticky="w")
        
        self.output_device_menu = ctk.CTkOptionMenu(
            audio_device_frame, 
            values=["Default"], 
            command=self.change_output_device
        )
        self.output_device_menu.grid(
            row=4, column=0, padx=10, pady=5, sticky="ew"
        )
        
        # Settings
        settings_frame = ctk.CTkFrame(sidebar_frame)
        settings_frame.grid(row=4, column=0, padx=20, pady=10, sticky="ew")
        
        settings_label = ctk.CTkLabel(
            settings_frame, 
            text="Settings", 
            font=ctk.CTkFont(weight="bold")
        )
        settings_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        appearance_label = ctk.CTkLabel(
            settings_frame, 
            text="Appearance Mode:"
        )
        appearance_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        
        appearance_menu = ctk.CTkOptionMenu(
            settings_frame, 
            values=["System", "Dark", "Light"], 
            command=self.change_appearance_mode
        )
        appearance_menu.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        
        # Statistics frame
        self.stats_frame = ctk.CTkFrame(sidebar_frame)
        self.stats_frame.grid(row=5, column=0, padx=20, pady=10, sticky="nsew")
        
        stats_label = ctk.CTkLabel(
            self.stats_frame, 
            text="Statistics", 
            font=ctk.CTkFont(weight="bold")
        )
        stats_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        self.stats_text = ctk.CTkTextbox(
            self.stats_frame,
            height=150,
            state="disabled"
        )
        self.stats_text.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        
        # Status indicator at the bottom of sidebar
        self.status_label = ctk.CTkLabel(
            sidebar_frame, 
            text="Status: Disconnected", 
            text_color="gray"
        )
        self.status_label.grid(row=6, column=0, padx=20, pady=20, sticky="s")
        
    def create_main_content(self):
        """Create the main content area with video displays"""
        main_frame = ctk.CTkFrame(self.root)
        main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        
        # Configure grid layout for main frame
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=3)
        
        # Header with connection info
        header_frame = ctk.CTkFrame(main_frame)
        header_frame.grid(
            row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=10
        )
        
        self.connection_info = ctk.CTkLabel(
            header_frame, 
            text="Not connected", 
            font=ctk.CTkFont(size=16)
        )
        self.connection_info.pack(pady=10)
        
        # Local video frame
        local_frame = ctk.CTkFrame(main_frame)
        local_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        
        local_label = ctk.CTkLabel(
            local_frame, 
            text="Local Video", 
            font=ctk.CTkFont(weight="bold")
        )
        local_label.pack(pady=5)
        
        self.local_video = ctk.CTkLabel(local_frame, text="Camera Off")
        self.local_video.pack(expand=True, fill="both", padx=10, pady=10)
        
        # Remote video frame
        remote_frame = ctk.CTkFrame(main_frame)
        remote_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)
        
        remote_label = ctk.CTkLabel(
            remote_frame, 
            text="Remote Video", 
            font=ctk.CTkFont(weight="bold")
        )
        remote_label.pack(pady=5)
        
        self.remote_video = ctk.CTkLabel(remote_frame, text="Not Connected")
        self.remote_video.pack(expand=True, fill="both", padx=10, pady=10)
        
    def connect(self):
        """Connect to a remote host"""
        host = self.host_entry.get()
        port = self.port_entry.get()
        
        if not host or not port:
            self.update_status("Please enter host and port", "red")
            return
            
        try:
            port = int(port)
        except ValueError:
            self.update_status("Port must be a number", "red")
            return
            
        self.update_status(f"Connecting to {host}:{port}...", "orange")
        
        # Disable connect and host buttons
        self.connect_button.configure(state="disabled")
        self.host_button.configure(state="disabled")
        
        # Connect to the remote host
        if self.connection.connect(host, port):
            self.is_connected = True
            self.is_hosting = False
        else:
            self.update_status("Failed to connect", "red")
            self.connect_button.configure(state="normal")
            self.host_button.configure(state="normal")
        
    def host_session(self):
        """Host a new session"""
        port = self.port_entry.get()
        
        if not port:
            self.update_status("Please enter a port", "red")
            return
            
        try:
            port = int(port)
        except ValueError:
            self.update_status("Port must be a number", "red")
            return
            
        self.update_status("Starting host session...", "orange")
        
        # Disable connect and host buttons
        self.connect_button.configure(state="disabled")
        self.host_button.configure(state="disabled")
        
        # Start hosting
        if self.connection.host(port):
            self.is_hosting = True
            self.update_status("Hosting - Waiting for connection", "blue")
            self.connection_info.configure(text=f"Hosting on port {port}")
        else:
            self.update_status("Failed to start hosting", "red")
            self.connect_button.configure(state="normal")
            self.host_button.configure(state="normal")
            
    def disconnect(self):
        """Disconnect from the current session"""
        if self.connection.disconnect():
            self.is_connected = False
            self.is_hosting = False
            self.update_status("Disconnected", "gray")
            self.connection_info.configure(text="Not connected")
            
            # Enable connect and host buttons
            self.connect_button.configure(state="normal")
            self.host_button.configure(state="normal")
            self.disconnect_button.configure(state="disabled")
            
            # Turn off camera and mic if they're on
            if self.video_enabled:
                self.camera_switch.deselect()
                self.toggle_camera()
                
            if self.audio_enabled:
                self.mic_switch.deselect()
                self.toggle_mic()
                
            # Clear remote video
            self.remote_video.configure(image=None, text="Not Connected")
            self.remote_video_enabled = False
            self.remote_audio_enabled = False
        
    def toggle_camera(self):
        """Toggle camera on/off"""
        if self.camera_switch.get() == 1:
            success = self.local_video_capture.start()
            if success:
                self.video_enabled = True
                self.update_status("Camera turned on", "green")
                
                # Notify remote peer if connected
                if self.is_connected:
                    self.connection.set_video_state(True)
            else:
                self.update_status("Could not start camera", "red")
                self.camera_switch.deselect()
        else:
            self.local_video_capture.stop()
            self.local_video.configure(image=None, text="Camera Off")
            self.video_enabled = False
            self.update_status("Camera turned off", "gray")
            
            # Notify remote peer if connected
            if self.is_connected:
                self.connection.set_video_state(False)
            
    def toggle_mic(self):
        """Toggle microphone on/off"""
        if self.mic_switch.get() == 1:
            success = self.audio_capture.start()
            if success:
                self.audio_enabled = True
                self.update_status("Microphone turned on", "green")
                
                # Notify remote peer if connected
                if self.is_connected:
                    self.connection.set_audio_state(True)
            else:
                self.update_status("Could not start microphone", "red")
                self.mic_switch.deselect()
        else:
            self.audio_capture.stop()
            self.audio_enabled = False
            self.update_status("Microphone turned off", "gray")
            
            # Notify remote peer if connected
            if self.is_connected:
                self.connection.set_audio_state(False)
    
    def change_input_device(self, device_str):
        """Change the input audio device"""
        if not device_str or ":" not in device_str:
            return
            
        # Extract device ID from the string
        device_id = int(device_str.split(":")[0])
        
        # Stop the current capture if it's running
        was_running = self.audio_enabled
        if was_running:
            self.audio_capture.stop()
            
        # Create a new audio capture with the selected device
        self.audio_capture = AudioCapture(
            callback=self.on_local_audio_frame,
            sample_rate=44100,
            channels=1,
            chunk_size=1024,
            device_id=device_id
        )
        
        # Restart if it was running
        if was_running:
            success = self.audio_capture.start()
            if not success:
                self.update_status("Failed to start with new device", "red")
                self.mic_switch.deselect()
                self.audio_enabled = False
                
    def change_output_device(self, device_str):
        """Change the output audio device"""
        if not device_str or ":" not in device_str:
            return
            
        # Extract device ID from the string
        device_id = int(device_str.split(":")[0])
        
        # Set the new output device
        success = self.audio_playback.set_output_device(device_id)
        if not success:
            self.update_status("Failed to set output device", "red")
            
    def change_appearance_mode(self, new_appearance_mode):
        """Change the app's appearance mode"""
        ctk.set_appearance_mode(new_appearance_mode)
        
    def update_status(self, message, color="gray"):
        """Update the status message"""
        self.status_label.configure(
            text=f"Status: {message}", 
            text_color=color
        )
        logging.info(f"Status: {message}")
        
    def on_local_video_frame(self, frame):
        """Callback for updating the local video frame"""
        # Frame is already in RGB format from VideoCapture
        # Resize for display
        img = cv2.resize(frame, (640, 480))
            
        # Convert to PIL Image and then to CTkImage
        from PIL import Image
        pil_img = Image.fromarray(img)
        ctk_image = ctk.CTkImage(
            light_image=pil_img, 
            dark_image=pil_img,
            size=(640, 480)
        )
        
        # Update the local video display
        self.local_video.configure(image=ctk_image, text="")
        self.local_video.image = ctk_image
        
        # Send the frame to the remote peer if connected and video is enabled
        if self.is_connected and self.video_enabled:
            # Encode the frame
            frame_data, width, height = self.video_encoder.encode_frame(frame)
            
            # Increment frame count
            self.video_frame_count += 1
            
            # Send the frame
            self.connection.send_video_frame(
                frame_data, 
                width, 
                height, 
                self.video_encoder.encoding,
                self.video_frame_count
            )
            
    def on_local_audio_frame(self, audio_data, sample_rate, channels, 
                            frame_number):
        """Callback for local audio frames"""
        # Send the audio frame to the remote peer if connected and audio is enabled
        if self.is_connected and self.audio_enabled:
            self.connection.send_audio_frame(
                audio_data, 
                sample_rate, 
                channels, 
                frame_number
            )
            
    def on_remote_video_frame(self, frame_data, width, height, encoding, 
                             frame_number):
        """Callback for remote video frames"""
        # Decode the frame
        frame = self.video_encoder.decode_frame(
            frame_data, 
            width, 
            height, 
            encoding
        )
        
        if frame is not None:
            # Convert to RGB if needed
            if frame.shape[2] == 3:  # BGR format
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
            # Resize for display
            frame = cv2.resize(frame, (640, 480))
            
            # Convert to PIL Image and then to CTkImage
            from PIL import Image
            pil_img = Image.fromarray(frame)
            ctk_image = ctk.CTkImage(
                light_image=pil_img, 
                dark_image=pil_img,
                size=(640, 480)
            )
            
            # Update the remote video display
            self.remote_video.configure(image=ctk_image, text="")
            self.remote_video.image = ctk_image
            self.remote_video_enabled = True
            
    def on_remote_audio_frame(self, audio_data, sample_rate, channels, 
                             frame_number):
        """Callback for remote audio frames"""
        # Play the audio
        if self.remote_audio_enabled:
            self.audio_playback.play_audio(
                audio_data, 
                sample_rate, 
                channels
            )
        
    def on_control_message(self, control_type, data):
        """Callback for control messages"""
        if control_type == ControlType.VIDEO_ON:
            self.remote_video_enabled = True
            logging.info("Remote video turned on")
        elif control_type == ControlType.VIDEO_OFF:
            self.remote_video_enabled = False
            self.remote_video.configure(image=None, text="Remote Camera Off")
            logging.info("Remote video turned off")
        elif control_type == ControlType.AUDIO_ON:
            self.remote_audio_enabled = True
            logging.info("Remote audio turned on")
        elif control_type == ControlType.AUDIO_OFF:
            self.remote_audio_enabled = False
            logging.info("Remote audio turned off")
            
    def on_status_message(self, status_type, message, code):
        """Callback for status messages"""
        if status_type == StatusType.ERROR:
            self.update_status(f"Error: {message}", "red")
        elif status_type == StatusType.WARNING:
            self.update_status(f"Warning: {message}", "orange")
        else:
            self.update_status(message)
            
    def on_connected(self):
        """Callback when a connection is established"""
        self.is_connected = True
        self.update_status("Connected", "green")
        
        # Update connection info
        if self.is_hosting:
            addr = self.connection.remote_address
            if addr:
                self.connection_info.configure(
                    text=f"Client connected from {addr[0]}:{addr[1]}"
                )
        else:
            addr = self.connection.remote_address
            if addr:
                self.connection_info.configure(
                    text=f"Connected to {addr[0]}:{addr[1]}"
                )
                
        # Enable disconnect button
        self.disconnect_button.configure(state="normal")
        
    def on_disconnected(self):
        """Callback when a connection is closed"""
        self.is_connected = False
        self.is_hosting = False
        self.update_status("Disconnected", "gray")
        self.connection_info.configure(text="Not connected")
        
        # Enable connect and host buttons
        self.connect_button.configure(state="normal")
        self.host_button.configure(state="normal")
        self.disconnect_button.configure(state="disabled")
        
        # Clear remote video
        self.remote_video.configure(image=None, text="Not Connected")
        self.remote_video_enabled = False
        self.remote_audio_enabled = False
        
    def update_statistics(self):
        """Update the statistics display"""
        if not self.is_connected:
            stats = "Not connected"
        else:
            net_stats = self.connection.get_statistics()
            
            # Format statistics
            stats = (
                f"Connection:\n"
                f"  Connected: {net_stats['connected']}\n"
                f"  Remote: {net_stats['remote_address']}\n"
                f"  Local: {net_stats['local_address']}\n\n"
                f"Data:\n"
                f"  Sent: {net_stats['bytes_sent'] / 1024:.1f} KB\n"
                f"  Received: {net_stats['bytes_received'] / 1024:.1f} KB\n"
                f"  Messages sent: {net_stats['messages_sent']}\n"
                f"  Messages received: {net_stats['messages_received']}\n\n"
                f"Video:\n"
                f"  Local: {'On' if self.video_enabled else 'Off'}\n"
                f"  Remote: {'On' if self.remote_video_enabled else 'Off'}\n\n"
                f"Audio:\n"
                f"  Local: {'On' if self.audio_enabled else 'Off'}\n"
                f"  Remote: {'On' if self.remote_audio_enabled else 'Off'}"
            )
            
        # Update the statistics text
        self.stats_text.configure(state="normal")
        self.stats_text.delete("1.0", "end")
        self.stats_text.insert("1.0", stats)
        self.stats_text.configure(state="disabled")
        
        # Schedule the next update
        self.root.after(
            int(self.stats_update_interval * 1000), 
            self.update_statistics
        )
        
    def on_close(self):
        """Handle window close event"""
        # Disconnect if connected
        if self.is_connected:
            self.connection.disconnect()
            
        # Stop video and audio capture
        self.local_video_capture.stop()
        self.audio_capture.stop()
        self.audio_playback.stop()
        
        # Close the window
        self.root.destroy()
        
    def run(self):
        """Run the application"""
        self.root.mainloop()
        
    def __del__(self):
        """Clean up resources"""
        if hasattr(self, 'local_video_capture'):
            self.local_video_capture.stop()
            
        if hasattr(self, 'audio_capture'):
            self.audio_capture.stop()
            
        if hasattr(self, 'audio_playback'):
            self.audio_playback.stop()
            
        if hasattr(self, 'connection') and self.is_connected:
            self.connection.disconnect() 