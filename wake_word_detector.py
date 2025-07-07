#!/usr/bin/env python3
"""
Wake Word Detection using Vosk for Furby
"""

import json
import os
import time
import threading
import pyaudio
import numpy as np
from typing import Callable
from shared_audio_manager import SharedAudioManager

# Optional import
try:
    import vosk
    VOSK_AVAILABLE = True
except ImportError:
    print("⚠️ Vosk not available - wake word detection disabled")
    VOSK_AVAILABLE = False


class WakeWordDetector:
    """Wake word detection using Vosk"""
    
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
        
        # Use shared audio manager
        self.audio_manager = SharedAudioManager(config)
        self.stream_id = "wake_word_detector"
        self.listen_thread = None
        
        if VOSK_AVAILABLE:
            self.setup_vosk()
    
    def setup_vosk(self):
        """Initialize Vosk for wake word detection"""
        if not os.path.exists(self.config.VOSK_MODEL_PATH):
            print(f"❌ Vosk model not found: {self.config.VOSK_MODEL_PATH}")
            return
        
        try:
            self.model = vosk.Model(self.config.VOSK_MODEL_PATH)
            # Vosk recognizer expects 16000 Hz after our resampling
            self.recognizer = vosk.KaldiRecognizer(self.model, 16000)
            self.recognizer.SetWords(True)
            self.is_available = True
            print(f"✅ Wake word detector ready - Words: {', '.join(self.wake_words)}")
        except Exception as e:
            print(f"❌ Wake word detector setup failed: {e}")
    
    def start_listening(self):
        """Start listening for wake words"""
        if not self.is_available:
            print("⚠️ Wake word detection not available")
            return
        
        if self.is_listening:
            print("⚠️ Already listening for wake words")
            return
        
        print("👂 Starting wake word detection...")
        self.is_listening = True
        self.is_paused = False
        
        # Start listening thread
        self.listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.listen_thread.start()
    
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
    
    def _listen_loop(self):
        """Main listening loop"""
        try:
            # Create stream through shared audio manager
            stream = self.audio_manager.create_stream(
                self.stream_id,
                format=pyaudio.paInt16,
                channels=2,  # Always use stereo from WM8960 HAT
                rate=48000,  # Use WM8960's native sample rate
                input=True,
                frames_per_buffer=self.config.FRAME_SIZE
            )
            
            if not stream:
                print("❌ Failed to create wake word audio stream")
                return
            
            print("👂 Listening for wake words...")
            
            while self.is_listening:
                try:
                    # Skip processing if paused
                    if self.is_paused:
                        # Still read data to prevent buffer overflow
                        if stream and not stream.is_stopped():
                            stream.read(self.config.FRAME_SIZE, exception_on_overflow=False)
                        time.sleep(0.1)
                        continue
                    
                    if stream and not stream.is_stopped():
                        data = stream.read(self.config.FRAME_SIZE, exception_on_overflow=False)
                        
                        # Convert stereo to mono and resample for Vosk
                        # WM8960 gives us stereo at 48000 Hz, but Vosk needs mono at 16000 Hz
                        stereo_data = np.frombuffer(data, dtype=np.int16)
                        stereo_data = stereo_data.reshape(-1, 2)
                        mono_data = np.mean(stereo_data, axis=1).astype(np.int16)
                        
                        # Simple decimation to resample from 48000 Hz to 16000 Hz (3:1 ratio)
                        if len(mono_data) >= 3:
                            resampled_data = mono_data[::3]  # Take every 3rd sample
                            data = resampled_data.tobytes()
                        else:
                            data = mono_data.tobytes()
                        
                        if self.recognizer and self.recognizer.AcceptWaveform(data):
                            result = json.loads(self.recognizer.Result())
                            self._check_wake_word(result.get('text', ''))
                        elif self.recognizer:
                            partial = json.loads(self.recognizer.PartialResult())
                            self._check_wake_word(partial.get('partial', ''))
                    else:
                        time.sleep(0.1)
                
                except Exception as e:
                    print(f"⚠️ Wake word detection error: {e}")
                    time.sleep(0.1)
            
        except Exception as e:
            print(f"❌ Wake word listening failed: {e}")
        finally:
            self._cleanup_audio()
            print("🛑 Wake word detection stopped")
    
    def _cleanup_audio(self):
        """Clean up audio resources properly"""
        try:
            # Close the stream through shared audio manager
            self.audio_manager.close_stream(self.stream_id)
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
                    print(f"🎯 WAKE WORD DETECTED: '{wake_word}' (confidence: {confidence:.2f})")
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
            print("⏳ Waiting for listening thread to finish...")
            self.listen_thread.join(timeout=3.0)
            if self.listen_thread.is_alive():
                print("⚠️ Listening thread did not finish gracefully")
        
        # Force cleanup even if thread didn't finish properly
        if self.audio_manager.is_stream_active(self.stream_id):
            print("🔧 Force cleaning up audio resources...")
            self._cleanup_audio()
        
        print("✅ Wake word detection stopped") 