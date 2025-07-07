#!/usr/bin/env python3
"""
Audio Management for Furby - Recording and Playback using ALSA
Updated to use AlsaAudioManager for both recording and playback
"""

import os
import time
import wave
import base64
import subprocess
import sys
import numpy as np
from typing import Optional, List, Dict
from alsa_audio_manager import AlsaAudioManager


class AudioManager:
    """Audio recording and playback management using ALSA"""
    
    def __init__(self, config):
        self.config = config
        self.alsa_audio = AlsaAudioManager(config)
        self.is_recording = False
        self.is_playing = False
        
        # Ensure audio directory exists
        os.makedirs(config.AUDIO_PATH, exist_ok=True)
        
        print(f"🔧 AudioManager initialized")
        print(f"   ALSA available: {self.alsa_audio.is_available}")
        print(f"   Audio path: {config.AUDIO_PATH}")
        
    def list_audio_devices(self):
        """List available audio devices"""
        print("🔍 Listing audio devices...")
        return self.alsa_audio.list_devices()
    
    def record_with_vad(self, max_duration: Optional[float] = None) -> Optional[str]:
        """Record audio with voice activity detection using ALSA"""
        if self.is_recording:
            print("⚠️ Already recording")
            return None
        
        if not self.alsa_audio.is_available:
            print("❌ ALSA audio not available for recording")
            return None
            
        max_duration = max_duration or self.config.MAX_RECORDING_DURATION
        print(f"🎤 Starting VAD recording (max {max_duration}s)...")
        print(f"   Device: {self.alsa_audio.device_name}")
        print(f"   Sample rate: {self.config.SAMPLE_RATE} Hz")
        print(f"   Channels: {self.config.CHANNELS}")
        
        self.is_recording = True
        audio_data = []
        silence_start = None
        
        try:
            # Create ALSA recording stream
            if not self.alsa_audio.create_recording_stream(
                channels=self.config.CHANNELS,
                rate=self.config.SAMPLE_RATE,
                period_size=self.config.FRAME_SIZE
            ):
                print("❌ Failed to create recording stream")
                return None
            
            start_time = time.time()
            frames_read = 0
            
            print("🎤 Recording started - speak now...")
            
            while self.is_recording and (time.time() - start_time) < max_duration:
                try:
                    # Read audio chunk
                    chunk = self.alsa_audio.read_audio()
                    
                    if chunk is None:
                        print("⚠️ Failed to read audio data")
                        time.sleep(0.01)
                        continue
                    
                    if len(chunk) == 0:
                        # No data available (non-blocking mode)
                        time.sleep(0.01)
                        continue
                    
                    audio_data.append(chunk)
                    frames_read += len(chunk) // (self.config.CHANNELS * 2)  # 2 bytes per sample
                    
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
                    print(f"   Error type: {type(e).__name__}")
                    break
            
            # Close recording stream
            self.alsa_audio.close_recording_stream()
            
            if not audio_data:
                print("❌ No audio recorded")
                return None
            
            # Save audio file
            timestamp = int(time.time() * 1000)
            filename = os.path.join(self.config.AUDIO_PATH, f"input_{timestamp}.wav")
            
            print(f"\n💾 Saving recording to: {filename}")
            
            with wave.open(filename, 'wb') as wav_file:
                wav_file.setnchannels(self.config.CHANNELS)
                wav_file.setsampwidth(2)  # 16-bit = 2 bytes
                wav_file.setframerate(self.config.SAMPLE_RATE)
                wav_file.writeframes(b''.join(audio_data))
            
            duration = time.time() - start_time
            file_size = os.path.getsize(filename)
            print(f"✅ Recording saved: {filename}")
            print(f"   Duration: {duration:.1f}s")
            print(f"   Frames: {frames_read}")
            print(f"   File size: {file_size} bytes")
            
            return filename
            
        except Exception as e:
            print(f"❌ Recording failed: {e}")
            print(f"   Error type: {type(e).__name__}")
            return None
        finally:
            self.is_recording = False
            # Ensure recording stream is closed
            if self.alsa_audio.is_recording:
                self.alsa_audio.close_recording_stream()
    
    def play_audio(self, file_path: str) -> bool:
        """Play audio file using ALSA"""
        if self.is_playing:
            print("⏹️ Stopping current playback")
            self.stop_playback()
        
        if not os.path.exists(file_path):
            print(f"❌ Audio file not found: {file_path}")
            return False
        
        if not self.alsa_audio.is_available:
            print("⚠️ ALSA not available, falling back to system aplay")
            return self._fallback_play_audio(file_path)
        
        try:
            print(f"🔊 Playing audio file: {file_path}")
            self.is_playing = True
            
            # Use ALSA audio manager to play the file
            success = self.alsa_audio.play_wav_file(file_path)
            
            if success:
                print("✅ ALSA playback completed successfully")
                return True
            else:
                print("⚠️ ALSA playback failed, falling back to system aplay")
                return self._fallback_play_audio(file_path)
            
        except Exception as e:
            print(f"❌ ALSA playback error: {e}")
            print(f"   Error type: {type(e).__name__}")
            print("⚠️ Falling back to system aplay")
            return self._fallback_play_audio(file_path)
        finally:
            self.is_playing = False
    
    def _fallback_play_audio(self, file_path: str) -> bool:
        """Fallback to system audio player if ALSA fails"""
        try:
            print(f"🔊 Fallback playback: {file_path}")
            
            # Use system audio player as fallback
            if sys.platform == 'darwin':  # macOS
                result = subprocess.run(['afplay', file_path], check=True, 
                                      capture_output=True, text=True)
            elif sys.platform.startswith('linux'):  # Linux/Raspberry Pi
                result = subprocess.run(['aplay', file_path], check=True,
                                      capture_output=True, text=True)
            else:
                print("⚠️ Unsupported platform for audio playback")
                return False
            
            print("✅ Fallback playback completed")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Fallback playback failed: {e}")
            if e.stderr:
                print(f"   stderr: {e.stderr}")
            return False
        except Exception as e:
            print(f"❌ Fallback playback error: {e}")
            return False
    
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
            print(f"💾 Saving base64 audio data...")
            print(f"   Type: {audio_type}")
            print(f"   File: {file_path}")
            
            audio_data = base64.b64decode(base64_data)
            with open(file_path, 'wb') as f:
                f.write(audio_data)
            
            file_size = len(audio_data)
            print(f"✅ Audio saved: {file_path} ({file_size} bytes)")
            return file_path
            
        except Exception as e:
            print(f"❌ Failed to save audio: {e}")
            print(f"   Error type: {type(e).__name__}")
            raise
    
    def stop_recording(self):
        """Stop current recording"""
        if self.is_recording:
            print("🛑 Stopping recording...")
            self.is_recording = False
    
    def stop_playback(self):
        """Stop current playback"""
        if self.is_playing:
            print("🛑 Stopping playback...")
            self.is_playing = False
            # Close playback stream if active
            if self.alsa_audio.is_playing:
                self.alsa_audio.close_playback_stream()
    
    def cleanup(self):
        """Cleanup audio resources"""
        print("🧹 Cleaning up audio manager...")
        
        # Stop any active operations
        self.stop_recording()
        self.stop_playback()
        
        # Clean up ALSA audio manager
        try:
            self.alsa_audio.cleanup()
            print("🔧 ALSA audio manager cleanup completed")
        except Exception as e:
            print(f"⚠️ ALSA cleanup error: {e}")
        
        print("✅ Audio manager cleanup completed") 