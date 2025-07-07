#!/usr/bin/env python3
"""
Shared Audio Manager for Furby - Single PyAudio instance for all components
This prevents multiple PyAudio instances from competing for the same device
"""

import os
import time
import threading
import pyaudio
import numpy as np
from typing import Optional, Callable
import atexit


class SharedAudioManager:
    """Single shared PyAudio instance for all audio operations"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, config=None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config=None):
        if self._initialized:
            return
            
        self.config = config
        self.pyaudio_instance = None
        self.active_streams = {}
        self.stream_lock = threading.Lock()
        self._initialized = True
        
        # Initialize PyAudio
        self._init_pyaudio()
        
        # Register cleanup on exit
        atexit.register(self.cleanup)
    
    def _init_pyaudio(self):
        """Initialize PyAudio instance"""
        try:
            self.pyaudio_instance = pyaudio.PyAudio()
            print("✅ Shared PyAudio instance initialized")
        except Exception as e:
            print(f"❌ Failed to initialize PyAudio: {e}")
            self.pyaudio_instance = None
    
    def create_stream(self, stream_id: str, **kwargs) -> Optional[pyaudio.Stream]:
        """Create a new audio stream"""
        if not self.pyaudio_instance:
            print("❌ PyAudio not available")
            return None
        
        with self.stream_lock:
            # Close existing stream with same ID
            if stream_id in self.active_streams:
                self.close_stream(stream_id)
            
            try:
                # Ensure device index is set
                if 'input_device_index' not in kwargs and self.config and hasattr(self.config, 'AUDIO_DEVICE_INDEX'):
                    kwargs['input_device_index'] = self.config.AUDIO_DEVICE_INDEX
                
                stream = self.pyaudio_instance.open(**kwargs)
                self.active_streams[stream_id] = stream
                print(f"🎵 Created audio stream: {stream_id}")
                return stream
            except Exception as e:
                print(f"❌ Failed to create stream {stream_id}: {e}")
                return None
    
    def close_stream(self, stream_id: str):
        """Close a specific audio stream"""
        with self.stream_lock:
            if stream_id in self.active_streams:
                stream = self.active_streams[stream_id]
                try:
                    if not stream.is_stopped():
                        stream.stop_stream()
                    stream.close()
                    print(f"🔧 Closed audio stream: {stream_id}")
                except Exception as e:
                    print(f"⚠️ Error closing stream {stream_id}: {e}")
                finally:
                    del self.active_streams[stream_id]
    
    def get_stream(self, stream_id: str) -> Optional[pyaudio.Stream]:
        """Get an existing stream by ID"""
        with self.stream_lock:
            return self.active_streams.get(stream_id)
    
    def is_stream_active(self, stream_id: str) -> bool:
        """Check if a stream is active"""
        with self.stream_lock:
            stream = self.active_streams.get(stream_id)
            if stream:
                try:
                    return not stream.is_stopped()
                except:
                    return False
            return False
    
    def list_devices(self):
        """List available audio devices"""
        if not self.pyaudio_instance:
            return []
        
        devices = []
        for i in range(self.pyaudio_instance.get_device_count()):
            info = self.pyaudio_instance.get_device_info_by_index(i)
            devices.append({
                'index': i,
                'name': info['name'],
                'channels': info['maxInputChannels'],
                'sample_rate': info['defaultSampleRate']
            })
        return devices
    
    def get_device_info(self, device_index: int):
        """Get device information"""
        if not self.pyaudio_instance:
            return None
        
        try:
            return self.pyaudio_instance.get_device_info_by_index(device_index)
        except Exception as e:
            print(f"❌ Failed to get device info for index {device_index}: {e}")
            return None
    
    def cleanup(self):
        """Cleanup all audio resources"""
        print("🧹 Cleaning up shared audio manager...")
        
        # Close all active streams
        with self.stream_lock:
            for stream_id, stream in list(self.active_streams.items()):
                try:
                    if not stream.is_stopped():
                        stream.stop_stream()
                    stream.close()
                    print(f"🔧 Force closed stream: {stream_id}")
                except Exception as e:
                    print(f"⚠️ Error force closing stream {stream_id}: {e}")
            
            self.active_streams.clear()
        
        # Terminate PyAudio
        if self.pyaudio_instance:
            try:
                self.pyaudio_instance.terminate()
                self.pyaudio_instance = None
                print("🔧 Shared PyAudio instance terminated")
            except Exception as e:
                print(f"⚠️ Error terminating PyAudio: {e}")
        
        # Force garbage collection
        try:
            import gc
            gc.collect()
            print("🧹 Shared audio manager garbage collection completed")
        except Exception as e:
            print(f"⚠️ Garbage collection error: {e}")
        
        print("✅ Shared audio manager cleanup completed")
    
    def force_reset(self):
        """Force reset the audio system"""
        print("🔄 Force resetting shared audio manager...")
        
        # Close all streams aggressively
        with self.stream_lock:
            for stream_id in list(self.active_streams.keys()):
                try:
                    stream = self.active_streams[stream_id]
                    stream.stop_stream()
                    stream.close()
                    del self.active_streams[stream_id]
                    print(f"🔧 Force reset stream: {stream_id}")
                except:
                    pass
        
        # Terminate and reinitialize PyAudio
        if self.pyaudio_instance:
            try:
                self.pyaudio_instance.terminate()
            except:
                pass
            self.pyaudio_instance = None
        
        # Wait a moment before reinitializing
        time.sleep(0.5)
        self._init_pyaudio()
        
        print("✅ Shared audio manager force reset completed") 