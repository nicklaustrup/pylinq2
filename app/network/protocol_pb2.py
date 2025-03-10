"""
Generated protocol buffer code for video chat application.
This would normally be generated using the protoc compiler, but we're creating it manually.
"""

import struct
import time
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Union, Dict, Any


class ControlType(Enum):
    CONNECT = 0
    DISCONNECT = 1
    PING = 2
    PONG = 3
    VIDEO_ON = 4
    VIDEO_OFF = 5
    AUDIO_ON = 6
    AUDIO_OFF = 7


class StatusType(Enum):
    INFO = 0
    WARNING = 1
    ERROR = 2


@dataclass
class VideoFrame:
    frame_data: bytes
    width: int
    height: int
    encoding: str
    frame_number: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frame_data": self.frame_data,
            "width": self.width,
            "height": self.height,
            "encoding": self.encoding,
            "frame_number": self.frame_number
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VideoFrame':
        return cls(
            frame_data=data["frame_data"],
            width=data["width"],
            height=data["height"],
            encoding=data["encoding"],
            frame_number=data["frame_number"]
        )


@dataclass
class AudioFrame:
    audio_data: bytes
    sample_rate: int
    channels: int
    frame_number: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "audio_data": self.audio_data,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "frame_number": self.frame_number
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AudioFrame':
        return cls(
            audio_data=data["audio_data"],
            sample_rate=data["sample_rate"],
            channels=data["channels"],
            frame_number=data["frame_number"]
        )


@dataclass
class ControlMessage:
    type: ControlType
    data: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "data": self.data
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ControlMessage':
        return cls(
            type=ControlType(data["type"]),
            data=data.get("data", "")
        )


@dataclass
class StatusMessage:
    type: StatusType
    message: str
    code: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "message": self.message,
            "code": self.code
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StatusMessage':
        return cls(
            type=StatusType(data["type"]),
            message=data["message"],
            code=data.get("code", 0)
        )


@dataclass
class VideoMessage:
    payload: Union[VideoFrame, AudioFrame, ControlMessage, StatusMessage]
    timestamp: int = 0
    
    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = int(time.time() * 1000)
    
    def to_dict(self) -> Dict[str, Any]:
        payload_type = type(self.payload).__name__
        payload_dict = self.payload.to_dict()
        
        return {
            "payload_type": payload_type,
            "payload": payload_dict,
            "timestamp": self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VideoMessage':
        payload_type = data["payload_type"]
        payload_data = data["payload"]
        
        if payload_type == "VideoFrame":
            payload = VideoFrame.from_dict(payload_data)
        elif payload_type == "AudioFrame":
            payload = AudioFrame.from_dict(payload_data)
        elif payload_type == "ControlMessage":
            payload = ControlMessage.from_dict(payload_data)
        elif payload_type == "StatusMessage":
            payload = StatusMessage.from_dict(payload_data)
        else:
            raise ValueError(f"Unknown payload type: {payload_type}")
        
        return cls(
            payload=payload,
            timestamp=data["timestamp"]
        ) 