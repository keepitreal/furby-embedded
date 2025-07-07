#!/usr/bin/env python3
"""
ALSA Audio Manager for Furby - Direct ALSA interface using alsaaudio
Replaces PyAudio-based SharedAudioManager with WM8960-optimized implementation
"""

import os
import time
import threading
import wave
import numpy as np
from typing import Optional, List, Dict, Any
import atexit

# Import alsaaudio with graceful fallback
try:
    import alsaaudio
    ALSAAUDIO_AVAILABLE = True
    print("✅ alsaaudio imported successfully")
except ImportError as e:
    print(f"❌ alsaaudio not available: {e}")
    ALSAAUDIO_AVAILABLE = False


class AlsaAudioManager:
    """ALSA-based audio manager for WM8960 Audio HAT"""
    
    def __init__(self, config):
        self.config = config
        self.is_available = ALSAAUDIO_AVAILABLE
        self.recording_pcm = None
        self.playback_pcm = None
        self.is_recording = False
        self.is_playing = False
        self.device_name = 'hw:0,0'  # WM8960 HAT device
        self.lock = threading.Lock()
        
        # Audio format constants
        self.format = alsaaudio.PCM_FORMAT_S16_LE if self.is_available else None
        self.sample_width = 2  # 16-bit = 2 bytes
        
        # Register cleanup on exit
        atexit.register(self.cleanup)
        
        if self.is_available:
            print(f"✅ AlsaAudioManager initialized for device: {self.device_name}")
            self._log_alsa_info()
        else:
            print("❌ AlsaAudioManager not available - alsaaudio missing")
    
    def _log_alsa_info(self):
        """Log ALSA device information for debugging"""
        try:
            print("🔍 ALSA Device Information:")
            print(f"   Device: {self.device_name}")
            print(f"   Format: {self.format}")
            print(f"   Sample Width: {self.sample_width} bytes")
            
            # Try to get device info
            cards = alsaaudio.cards()
            print(f"   Available cards: {cards}")
            
            pcms = alsaaudio.pcms()
            print(f"   Available PCMs: {pcms}")
            
        except Exception as e:
            print(f"⚠️ Could not get ALSA info: {e}")
    
    def create_recording_stream(self, channels=2, rate=48000, period_size=None) -> bool:
        """Create a recording stream"""
        if not self.is_available:
            print("❌ Cannot create recording stream - alsaaudio not available")
            return False
        
        if self.is_recording:
            print("⚠️ Recording stream already active")
            return True
        
        try:
            with self.lock:
                if period_size is None:
                    period_size = rate // 8  # Default period size
                
                print(f"🎤 Creating recording stream:")
                print(f"   Device: {self.device_name}")
                print(f"   Channels: {channels}")
                print(f"   Rate: {rate} Hz")
                print(f"   Format: {self.format}")
                print(f"   Period size: {period_size}")
                
                self.recording_pcm = alsaaudio.PCM(
                    alsaaudio.PCM_CAPTURE,
                    alsaaudio.PCM_NONBLOCK,
                    channels=channels,
                    rate=rate,
                    format=self.format,
                    periodsize=period_size,
                    device=self.device_name
                )
                
                print("✅ Recording stream created successfully")
                self.is_recording = True
                return True
                
        except Exception as e:
            print(f"❌ Failed to create recording stream: {e}")
            print(f"   Error type: {type(e).__name__}")
            if hasattr(e, 'errno'):
                print(f"   Error code: {e.errno}")
            return False
    
    def create_playback_stream(self, channels=2, rate=44100, period_size=None) -> bool:
        """Create a playback stream"""
        if not self.is_available:
            print("❌ Cannot create playback stream - alsaaudio not available")
            return False
        
        if self.is_playing:
            print("⚠️ Playback stream already active")
            return True
        
        try:
            with self.lock:
                if period_size is None:
                    period_size = rate // 8  # Default period size
                
                print(f"🔊 Creating playback stream:")
                print(f"   Device: {self.device_name}")
                print(f"   Channels: {channels}")
                print(f"   Rate: {rate} Hz")
                print(f"   Format: {self.format}")
                print(f"   Period size: {period_size}")
                
                self.playback_pcm = alsaaudio.PCM(
                    alsaaudio.PCM_PLAYBACK,
                    alsaaudio.PCM_NORMAL,
                    channels=channels,
                    rate=rate,
                    format=self.format,
                    periodsize=period_size,
                    device=self.device_name
                )
                
                print("✅ Playback stream created successfully")
                self.is_playing = True
                return True
                
        except Exception as e:
            print(f"❌ Failed to create playback stream: {e}")
            print(f"   Error type: {type(e).__name__}")
            if hasattr(e, 'errno'):
                print(f"   Error code: {e.errno}")
            return False
    
    def read_audio(self, frames_to_read=None) -> Optional[bytes]:
        """Read audio data from recording stream"""
        if not self.is_available or not self.recording_pcm:
            print("❌ Cannot read audio - no recording stream")
            return None
        
        try:
            length, data = self.recording_pcm.read()
            
            if length > 0:
                print(f"🎤 Read {length} audio samples ({len(data)} bytes)")
                return data
            else:
                # No data available (non-blocking mode)
                return b''
                
        except Exception as e:
            print(f"❌ Audio read error: {e}")
            return None
    
    def write_audio(self, data: bytes) -> bool:
        """Write audio data to playback stream"""
        if not self.is_available or not self.playback_pcm:
            print("❌ Cannot write audio - no playback stream")
            return False
        
        try:
            bytes_written = self.playback_pcm.write(data)
            print(f"🔊 Wrote {bytes_written} bytes to playback stream")
            return bytes_written > 0
            
        except Exception as e:
            print(f"❌ Audio write error: {e}")
            return False
    
    def play_wav_file(self, file_path: str) -> bool:
        """Play a WAV file using alsaaudio"""
        if not self.is_available:
            print("❌ Cannot play WAV file - alsaaudio not available")
            return False
        
        if not os.path.exists(file_path):
            print(f"❌ Audio file not found: {file_path}")
            return False
        
        try:
            print(f"🎵 Playing WAV file: {file_path}")
            
            with wave.open(file_path, 'rb') as wav_file:
                channels = wav_file.getnchannels()
                rate = wav_file.getframerate()
                sample_width = wav_file.getsampwidth()
                
                print(f"📊 WAV file info:")
                print(f"   Channels: {channels}")
                print(f"   Sample rate: {rate} Hz")
                print(f"   Sample width: {sample_width} bytes")
                
                # Create playback stream with file's parameters
                if not self.create_playback_stream(channels=channels, rate=rate):
                    print("❌ Failed to create playback stream for WAV file")
                    return False
                
                # Calculate period size for this file
                period_size = rate // 8
                print(f"🔊 Playing with period size: {period_size}")
                
                # Read and play audio data
                total_frames = 0
                while True:
                    data = wav_file.readframes(period_size)
                    if not data:
                        break
                    
                    if not self.write_audio(data):
                        print("❌ Failed to write audio data")
                        break
                    
                    total_frames += len(data) // (channels * sample_width)
                
                duration = total_frames / rate
                print(f"✅ Playback completed: {duration:.2f} seconds")
                return True
                
        except Exception as e:
            print(f"❌ WAV playback failed: {e}")
            print(f"   Error type: {type(e).__name__}")
            return False
        finally:
            self.close_playback_stream()
    
    def close_recording_stream(self):
        """Close the recording stream"""
        try:
            with self.lock:
                if self.recording_pcm:
                    self.recording_pcm.close()
                    self.recording_pcm = None
                    print("🔧 Recording stream closed")
                
                self.is_recording = False
                
        except Exception as e:
            print(f"⚠️ Error closing recording stream: {e}")
    
    def close_playback_stream(self):
        """Close the playback stream"""
        try:
            with self.lock:
                if self.playback_pcm:
                    self.playback_pcm.close()
                    self.playback_pcm = None
                    print("🔧 Playback stream closed")
                
                self.is_playing = False
                
        except Exception as e:
            print(f"⚠️ Error closing playback stream: {e}")
    
    def list_devices(self) -> List[Dict[str, Any]]:
        """List available ALSA devices"""
        if not self.is_available:
            print("❌ Cannot list devices - alsaaudio not available")
            return []
        
        try:
            print("🔍 Listing ALSA devices:")
            
            cards = alsaaudio.cards()
            pcms = alsaaudio.pcms()
            
            devices = []
            for i, card in enumerate(cards):
                devices.append({
                    'index': i,
                    'name': card,
                    'type': 'card'
                })
                print(f"   Card {i}: {card}")
            
            for i, pcm in enumerate(pcms):
                devices.append({
                    'index': i,
                    'name': pcm,
                    'type': 'pcm'
                })
                print(f"   PCM {i}: {pcm}")
            
            return devices
            
        except Exception as e:
            print(f"❌ Failed to list devices: {e}")
            return []
    
    def get_device_info(self, device_name: str = None) -> Dict[str, Any]:
        """Get information about a specific device"""
        device_name = device_name or self.device_name
        
        print(f"🔍 Getting device info for: {device_name}")
        
        # Since alsaaudio doesn't have direct device info like PyAudio,
        # we'll provide basic information
        return {
            'name': device_name,
            'max_input_channels': 2,  # WM8960 supports stereo
            'max_output_channels': 2,  # WM8960 supports stereo
            'default_sample_rate': 44100,
            'supported_rates': [8000, 16000, 22050, 44100, 48000]
        }
    
    def cleanup(self):
        """Cleanup all audio resources"""
        print("🧹 Cleaning up ALSA audio manager...")
        
        # Close all streams
        self.close_recording_stream()
        self.close_playback_stream()
        
        # Force garbage collection
        try:
            import gc
            gc.collect()
            print("🧹 ALSA audio manager garbage collection completed")
        except Exception as e:
            print(f"⚠️ Garbage collection error: {e}")
        
        print("✅ ALSA audio manager cleanup completed")
    
    def test_recording(self, duration=2.0, channels=2, rate=48000):
        """Test recording functionality"""
        print(f"🧪 Testing recording for {duration} seconds...")
        
        if not self.create_recording_stream(channels=channels, rate=rate):
            return False
        
        try:
            audio_data = []
            start_time = time.time()
            
            while time.time() - start_time < duration:
                data = self.read_audio()
                if data:
                    audio_data.append(data)
                    # Calculate audio level for feedback
                    if len(data) > 0:
                        audio_np = np.frombuffer(data, dtype=np.int16)
                        if len(audio_np) > 0:
                            audio_level = np.sqrt(np.mean(audio_np**2))
                            print(f"🎤 Audio level: {audio_level:.1f}", end='\r')
                else:
                    time.sleep(0.01)  # Small delay for non-blocking mode
            
            total_samples = sum(len(data) for data in audio_data)
            print(f"\n✅ Recording test completed: {total_samples} bytes recorded")
            return True
            
        except Exception as e:
            print(f"❌ Recording test failed: {e}")
            return False
        finally:
            self.close_recording_stream()
    
    def test_playback(self, frequency=440, duration=1.0, channels=2, rate=44100):
        """Test playback functionality with a generated tone"""
        print(f"🧪 Testing playback: {frequency}Hz tone for {duration} seconds...")
        
        if not self.create_playback_stream(channels=channels, rate=rate):
            return False
        
        try:
            # Generate a simple sine wave
            samples = int(rate * duration)
            t = np.linspace(0, duration, samples, False)
            wave_data = np.sin(2 * np.pi * frequency * t)
            
            # Convert to 16-bit PCM
            wave_data = (wave_data * 32767).astype(np.int16)
            
            # Make stereo if needed
            if channels == 2:
                wave_data = np.column_stack((wave_data, wave_data))
            
            # Convert to bytes
            audio_bytes = wave_data.tobytes()
            
            # Play the audio
            period_size = rate // 8
            for i in range(0, len(audio_bytes), period_size * channels * 2):
                chunk = audio_bytes[i:i + period_size * channels * 2]
                if not self.write_audio(chunk):
                    print("❌ Failed to write audio chunk")
                    return False
                time.sleep(0.01)  # Small delay between chunks
            
            print(f"✅ Playback test completed")
            return True
            
        except Exception as e:
            print(f"❌ Playback test failed: {e}")
            return False
        finally:
            self.close_playback_stream() 