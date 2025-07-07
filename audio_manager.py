#!/usr/bin/env python3
"""
Audio Management for Furby - Recording and Playback
"""

import os
import time
import wave
import base64
import subprocess
import sys
import numpy as np
import pyaudio
from typing import Optional, List, Dict
from shared_audio_manager import SharedAudioManager


class AudioManager:
    """Audio recording and playback management"""
    
    def __init__(self, config):
        self.config = config
        self.shared_audio = SharedAudioManager(config)
        self.is_recording = False
        self.is_playing = False
        self.recording_stream_id = "audio_manager_recording"
        
        # Ensure audio directory exists
        os.makedirs(config.AUDIO_PATH, exist_ok=True)
        
    def list_audio_devices(self):
        """List available audio devices"""
        return self.shared_audio.list_devices()
    
    def record_with_vad(self, max_duration: Optional[float] = None) -> Optional[str]:
        """Record audio with voice activity detection"""
        if self.is_recording:
            print("⚠️ Already recording")
            return None
        
        if not self.shared_audio.pyaudio_instance:
            print("❌ PyAudio not available")
            return None
            
        max_duration = max_duration or self.config.MAX_RECORDING_DURATION
        print(f"🎤 Starting VAD recording (max {max_duration}s)...")
        
        self.is_recording = True
        audio_data = []
        silence_start = None
        
        try:
            stream = self.shared_audio.create_stream(
                self.recording_stream_id,
                format=pyaudio.paInt16,
                channels=self.config.CHANNELS,
                rate=self.config.SAMPLE_RATE,
                input=True,
                frames_per_buffer=self.config.FRAME_SIZE
            )
            
            if not stream:
                print("❌ Failed to create recording stream")
                return None
            
            start_time = time.time()
            
            while self.is_recording and (time.time() - start_time) < max_duration:
                try:
                    # Read audio chunk
                    chunk = stream.read(self.config.FRAME_SIZE, exception_on_overflow=False)
                    audio_data.append(chunk)
                    
                    # Calculate energy level for VAD
                    audio_np = np.frombuffer(chunk, dtype=np.int16)
                    energy = np.sqrt(np.mean(audio_np**2)) / 32768.0  # Normalize
                    
                    # Voice activity detection
                    if energy > self.config.VAD_ENERGY_THRESHOLD:
                        # Voice detected, reset silence timer
                        silence_start = None
                        print("🗣️", end="", flush=True)  # Voice indicator
                    else:
                        # Silence detected
                        if silence_start is None:
                            silence_start = time.time()
                        elif time.time() - silence_start > self.config.VAD_SILENCE_DURATION:
                            print(f"\n🔇 Silence detected for {self.config.VAD_SILENCE_DURATION}s, stopping recording")
                            break
                        print(".", end="", flush=True)  # Silence indicator
                        
                except Exception as e:
                    print(f"⚠️ Recording error: {e}")
                    break
            
            # Close stream through shared audio manager
            self.shared_audio.close_stream(self.recording_stream_id)
            
            if not audio_data:
                print("❌ No audio recorded")
                return None
            
            # Save audio file
            timestamp = int(time.time() * 1000)
            filename = os.path.join(self.config.AUDIO_PATH, f"input_{timestamp}.wav")
            
            with wave.open(filename, 'wb') as wav_file:
                wav_file.setnchannels(self.config.CHANNELS)
                if self.shared_audio.pyaudio_instance:  # Check if pyaudio is still available
                    wav_file.setsampwidth(self.shared_audio.pyaudio_instance.get_sample_size(pyaudio.paInt16))
                else:
                    wav_file.setsampwidth(2)  # 16-bit = 2 bytes
                wav_file.setframerate(self.config.SAMPLE_RATE)
                wav_file.writeframes(b''.join(audio_data))
            
            duration = time.time() - start_time
            print(f"\n✅ Recording saved: {filename} ({duration:.1f}s)")
            return filename
            
        except Exception as e:
            print(f"❌ Recording failed: {e}")
            return None
        finally:
            self.is_recording = False
    
    def play_audio(self, file_path: str) -> bool:
        """Play audio file"""
        if self.is_playing:
            print("⏹️ Stopping current playback")
            self.stop_playback()
        
        if not os.path.exists(file_path):
            print(f"❌ Audio file not found: {file_path}")
            return False
        
        try:
            print(f"🔊 Playing: {file_path}")
            self.is_playing = True
            
            # Use system audio player
            if sys.platform == 'darwin':  # macOS
                subprocess.run(['afplay', file_path], check=True)
            elif sys.platform.startswith('linux'):  # Linux/Raspberry Pi
                subprocess.run(['aplay', file_path], check=True)
            else:
                print("⚠️ Unsupported platform for audio playback")
                return False
            
            print("✅ Playback completed")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Playback failed: {e}")
            return False
        except Exception as e:
            print(f"❌ Playback error: {e}")
            return False
        finally:
            self.is_playing = False
    
    def save_base64_audio(self, base64_data: str, filename: Optional[str] = None, audio_type: str = 'tts') -> str:
        """Save base64 audio data to file"""
        if filename is None:
            timestamp = int(time.time() * 1000)
            
            # Use different prefixes based on audio type
            if audio_type == 'output':
                filename = f"output_{timestamp}.wav"
            else:
                filename = f"tts_{timestamp}.wav"
        
        file_path = os.path.join(self.config.AUDIO_PATH, filename)
        
        try:
            audio_data = base64.b64decode(base64_data)
            with open(file_path, 'wb') as f:
                f.write(audio_data)
            print(f"💾 Audio saved: {file_path}")
            return file_path
        except Exception as e:
            print(f"❌ Failed to save audio: {e}")
            raise
    
    def stop_recording(self):
        """Stop current recording"""
        self.is_recording = False
    
    def stop_playback(self):
        """Stop current playback"""
        self.is_playing = False
    
    def cleanup(self):
        """Cleanup audio resources"""
        print("🧹 Cleaning up audio manager...")
        
        # Stop any active operations
        self.stop_recording()
        self.stop_playback()
        
        # Clean up recording stream
        try:
            if self.shared_audio.is_stream_active(self.recording_stream_id):
                self.shared_audio.close_stream(self.recording_stream_id)
                print("🔧 Audio manager recording stream closed")
        except Exception as e:
            print(f"⚠️ Audio manager stream cleanup error: {e}")
        
        # The shared audio manager will handle PyAudio cleanup
        print("✅ Audio manager cleanup completed") 