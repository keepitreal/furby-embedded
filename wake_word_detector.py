#!/usr/bin/env python3
"""
Wake Word Detection using Vosk for Furby - Updated for ALSA Audio
"""

import json
import os
import time
import threading
import numpy as np
from typing import Callable
from alsa_audio_manager import AlsaAudioManager

# Optional import
try:
    import vosk
    VOSK_AVAILABLE = True
except ImportError:
    print("⚠️ Vosk not available - wake word detection disabled")
    VOSK_AVAILABLE = False


class WakeWordDetector:
    """Wake word detection using Vosk with ALSA audio"""
    
    def __init__(self, config, callback: Callable):
        self.config = config
        self.callback = callback
        self.model = None
        self.recognizer = None
        self.is_listening = False
        self.is_paused = False
        self.is_available = False
        self.last_detection = 0
        self.wake_words = [word.strip().lower() for word in config.WAKE_WORDS]
        
        # Use ALSA audio manager
        self.audio_manager = AlsaAudioManager(config)
        self.listen_thread = None
        
        print(f"🔧 Wake word detector initialized")
        print(f"   ALSA available: {self.audio_manager.is_available}")
        print(f"   Vosk available: {VOSK_AVAILABLE}")
        print(f"   Wake words: {self.wake_words}")
        
        if VOSK_AVAILABLE:
            self.setup_vosk()
    
    def setup_vosk(self):
        """Initialize Vosk for wake word detection"""
        if not os.path.exists(self.config.VOSK_MODEL_PATH):
            print(f"❌ Vosk model not found: {self.config.VOSK_MODEL_PATH}")
            return
        
        try:
            print(f"🔧 Loading Vosk model from: {self.config.VOSK_MODEL_PATH}")
            self.model = vosk.Model(self.config.VOSK_MODEL_PATH)
            # Vosk recognizer expects 16000 Hz after our resampling
            self.recognizer = vosk.KaldiRecognizer(self.model, 16000)
            self.recognizer.SetWords(True)
            self.is_available = True
            print(f"✅ Wake word detector ready - Words: {', '.join(self.wake_words)}")
        except Exception as e:
            print(f"❌ Wake word detector setup failed: {e}")
            print(f"   Error type: {type(e).__name__}")
    
    def start_listening(self):
        """Start listening for wake words"""
        if not self.is_available:
            print("⚠️ Wake word detection not available")
            print(f"   ALSA available: {self.audio_manager.is_available}")
            print(f"   Vosk available: {VOSK_AVAILABLE}")
            return
        
        if self.is_listening:
            print("⚠️ Already listening for wake words")
            return
        
        print("👂 Starting wake word detection...")
        print(f"   Device: {self.audio_manager.device_name}")
        print(f"   Recording: 48kHz stereo → 16kHz mono for Vosk")
        
        self.is_listening = True
        self.is_paused = False
        
        # Start listening thread
        self.listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.listen_thread.start()
        print("✅ Wake word detection thread started")
    
    def pause_listening(self):
        """Pause wake word detection temporarily"""
        if self.is_listening:
            print("⏸️ Pausing wake word detection...")
            self.is_paused = True
    
    def resume_listening(self):
        """Resume wake word detection"""
        if self.is_listening and self.is_paused:
            print("▶️ Resuming wake word detection...")
            self.is_paused = False
    
    def stop_recording_stream(self):
        """Temporarily stop the recording stream (for manual recording)"""
        if self.is_listening and not self.is_paused:
            print("⏸️ Temporarily stopping wake word recording stream...")
            self.is_paused = True
            self.audio_manager.close_recording_stream()
            return True
        return False
    
    def restart_recording_stream(self):
        """Restart the recording stream (after manual recording)"""
        if self.is_listening and self.is_paused:
            print("▶️ Restarting wake word recording stream...")
            # The recording stream will be recreated in the listen loop
            self.is_paused = False
            return True
        return False
    
    def _listen_loop(self):
        """Main listening loop using ALSA audio"""
        try:
            print("🔧 Creating ALSA recording stream for wake word detection...")
            
            # Create recording stream: 48kHz stereo (WM8960 native)
            if not self.audio_manager.create_recording_stream(
                channels=2,  # Stereo
                rate=48000,  # WM8960 native rate
                period_size=self.config.FRAME_SIZE
            ):
                print("❌ Failed to create wake word recording stream")
                return
            
            print("👂 Wake word detection listening started...")
            
            while self.is_listening:
                try:
                    # Check if we need to recreate the recording stream
                    if self.is_paused and not self.audio_manager.is_recording:
                        # Stream was closed for manual recording, skip processing
                        time.sleep(0.1)
                        continue
                    
                    # If we resumed from pause, recreate the recording stream
                    if not self.is_paused and not self.audio_manager.is_recording:
                        print("🔄 Recreating wake word recording stream after manual recording...")
                        if not self.audio_manager.create_recording_stream(
                            channels=2,
                            rate=48000,
                            period_size=self.config.FRAME_SIZE
                        ):
                            print("❌ Failed to recreate wake word recording stream")
                            time.sleep(1)
                            continue
                        print("✅ Wake word recording stream recreated")
                    
                    # Skip processing if paused
                    if self.is_paused:
                        # Still read data to prevent buffer overflow if stream is active
                        if self.audio_manager.is_recording:
                            data = self.audio_manager.read_audio()
                            if data is None:
                                print("⚠️ Failed to read audio data while paused")
                                time.sleep(0.1)
                        else:
                            time.sleep(0.1)
                        continue
                    
                    # Read audio data
                    data = self.audio_manager.read_audio()
                    
                    if data is None:
                        print("⚠️ Failed to read audio data")
                        time.sleep(0.1)
                        continue
                    
                    if len(data) == 0:
                        # No data available (non-blocking mode)
                        time.sleep(0.01)
                        continue
                    
                    # Process audio for wake word detection
                    processed_data = self._process_audio_for_vosk(data)
                    
                    if processed_data and self.recognizer:
                        if self.recognizer.AcceptWaveform(processed_data):
                            result = json.loads(self.recognizer.Result())
                            self._check_wake_word(result.get('text', ''))
                        else:
                            partial = json.loads(self.recognizer.PartialResult())
                            self._check_wake_word(partial.get('partial', ''))
                    
                except Exception as e:
                    print(f"⚠️ Wake word detection error: {e}")
                    print(f"   Error type: {type(e).__name__}")
                    time.sleep(0.1)
            
        except Exception as e:
            print(f"❌ Wake word listening failed: {e}")
            print(f"   Error type: {type(e).__name__}")
        finally:
            self._cleanup_audio()
            print("🛑 Wake word detection stopped")
    
    def _process_audio_for_vosk(self, raw_data: bytes) -> bytes:
        """Process raw ALSA audio data for Vosk recognition"""
        try:
            # Convert raw bytes to numpy array (16-bit stereo)
            stereo_data = np.frombuffer(raw_data, dtype=np.int16)
            
            if len(stereo_data) == 0:
                return b''
            
            # Reshape to stereo (2 channels)
            if len(stereo_data) % 2 != 0:
                # Odd number of samples, trim one
                stereo_data = stereo_data[:-1]
            
            stereo_data = stereo_data.reshape(-1, 2)
            
            # Convert stereo to mono (average channels)
            mono_data = np.mean(stereo_data, axis=1).astype(np.int16)
            
            # Resample from 48000 Hz to 16000 Hz (3:1 ratio)
            # Simple decimation: take every 3rd sample
            if len(mono_data) >= 3:
                resampled_data = mono_data[::3]
            else:
                resampled_data = mono_data
            
            # Calculate audio level for debugging
            if len(resampled_data) > 0:
                audio_level = np.sqrt(np.mean(resampled_data**2))
                if audio_level > 100:  # Only log when there's actual audio
                    print(f"🎤 Wake word audio level: {audio_level:.1f}", end='\r')
            
            return resampled_data.tobytes()
            
        except Exception as e:
            print(f"⚠️ Audio processing error: {e}")
            return b''
    
    def _cleanup_audio(self):
        """Clean up audio resources properly"""
        try:
            print("🧹 Cleaning up wake word audio resources...")
            self.audio_manager.close_recording_stream()
            print("🔧 Wake word audio stream closed")
        except Exception as e:
            print(f"⚠️ Wake word stream cleanup error: {e}")
        
        # Additional cleanup - force garbage collection
        try:
            import gc
            gc.collect()
            print("🧹 Wake word forced garbage collection")
        except Exception as e:
            print(f"⚠️ Wake word garbage collection error: {e}")
    
    def _check_wake_word(self, text: str):
        """Check if text contains wake word"""
        if not text or self.is_paused:
            return
        
        text = text.lower().strip()
        current_time = time.time()
        
        # Check cooldown
        if current_time - self.last_detection < self.config.WAKE_WORD_COOLDOWN:
            return
        
        # Check for wake words
        for wake_word in self.wake_words:
            if wake_word in text:
                confidence = self._calculate_confidence(text, wake_word)
                if confidence >= self.config.WAKE_WORD_CONFIDENCE:
                    print(f"\n🎯 WAKE WORD DETECTED: '{wake_word}' (confidence: {confidence:.2f})")
                    print(f"   Full text: '{text}'")
                    self.last_detection = current_time
                    # Pause immediately to prevent rapid triggers
                    self.pause_listening()
                    self.callback()
                    break
    
    def _calculate_confidence(self, text: str, wake_word: str) -> float:
        """Calculate confidence score"""
        if wake_word == text:
            return 1.0
        
        words_in_text = text.split()
        words_in_wake = wake_word.split()
        
        matches = sum(1 for word in words_in_wake if word in words_in_text)
        return matches / len(words_in_wake) if words_in_wake else 0.0
    
    def stop_listening(self):
        """Stop listening for wake words"""
        print("🛑 Stopping wake word detection...")
        self.is_listening = False
        
        # Wait for thread to finish
        if self.listen_thread and self.listen_thread.is_alive():
            print("⏳ Waiting for wake word thread to finish...")
            self.listen_thread.join(timeout=3.0)
            if self.listen_thread.is_alive():
                print("⚠️ Wake word thread did not finish gracefully")
        
        # Force cleanup even if thread didn't finish properly
        if self.audio_manager.is_recording:
            print("🔧 Force cleaning up wake word audio resources...")
            self._cleanup_audio()
        
        print("✅ Wake word detection stopped") 