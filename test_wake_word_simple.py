#!/usr/bin/env python3
"""
Simple test for wake word detection debugging
"""
import pyaudio
import numpy as np
import time
import json
import os
try:
    import vosk
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False
    print("Vosk not available")

class SimpleWakeWordTest:
    def __init__(self):
        self.model = None
        self.recognizer = None
        
        if VOSK_AVAILABLE:
            model_path = "./models/vosk-model-small-en-us-0.15"
            if os.path.exists(model_path):
                print(f"Loading model from {model_path}")
                self.model = vosk.Model(model_path)
                self.recognizer = vosk.KaldiRecognizer(self.model, 16000)
                self.recognizer.SetWords(True)
                print("✅ Model loaded successfully")
            else:
                print("❌ Model not found")
    
    def test_audio_levels(self):
        """Test audio input levels"""
        p = pyaudio.PyAudio()
        
        print("Testing audio input levels...")
        print("Device 0 (WM8960):", p.get_device_info_by_index(0))
        
        try:
            stream = p.open(
                format=pyaudio.paInt16,
                channels=2,
                rate=48000,
                input=True,
                input_device_index=0,
                frames_per_buffer=4000
            )
            
            print("Recording for 5 seconds to check audio levels...")
            for i in range(50):  # 5 seconds at 0.1s intervals
                try:
                    data = stream.read(4000, exception_on_overflow=False)
                    stereo_data = np.frombuffer(data, dtype=np.int16)
                    stereo_data = stereo_data.reshape(-1, 2)
                    mono_data = np.mean(stereo_data, axis=1).astype(np.int16)
                    
                    # Calculate audio level
                    audio_level = np.sqrt(np.mean(mono_data**2))
                    print(f"Audio level: {audio_level:.1f} {'🎤' if audio_level > 100 else '📻'}")
                    
                    if audio_level > 100:
                        print("🔊 Audio detected!")
                    
                    time.sleep(0.1)
                except Exception as e:
                    print(f"Error reading audio: {e}")
                    
            stream.stop_stream()
            stream.close()
            
        except Exception as e:
            print(f"❌ Failed to open audio stream: {e}")
        finally:
            p.terminate()
    
    def test_wake_word_detection(self):
        """Test wake word detection"""
        if not self.recognizer:
            print("❌ No recognizer available")
            return
            
        p = pyaudio.PyAudio()
        
        try:
            stream = p.open(
                format=pyaudio.paInt16,
                channels=2,
                rate=48000,
                input=True,
                input_device_index=0,
                frames_per_buffer=4000
            )
            
            print("🎤 Listening for wake words... (say 'furby' or 'hey furby')")
            print("Press Ctrl+C to stop")
            
            while True:
                try:
                    data = stream.read(4000, exception_on_overflow=False)
                    
                    # Convert stereo to mono and resample
                    stereo_data = np.frombuffer(data, dtype=np.int16)
                    stereo_data = stereo_data.reshape(-1, 2)
                    mono_data = np.mean(stereo_data, axis=1).astype(np.int16)
                    
                    # Resample from 48kHz to 16kHz
                    if len(mono_data) >= 3:
                        resampled_data = mono_data[::3]
                        processed_data = resampled_data.tobytes()
                        
                        # Check audio level
                        audio_level = np.sqrt(np.mean(resampled_data**2))
                        if audio_level > 50:  # Only process if there's audio
                            print(f"Processing audio (level: {audio_level:.1f})")
                            
                            if self.recognizer.AcceptWaveform(processed_data):
                                result = json.loads(self.recognizer.Result())
                                text = result.get('text', '')
                                if text:
                                    print(f"🎯 RECOGNIZED: '{text}'")
                                    if any(word in text.lower() for word in ['furby', 'hey furby']):
                                        print("🚨 WAKE WORD DETECTED!")
                            else:
                                partial = json.loads(self.recognizer.PartialResult())
                                partial_text = partial.get('partial', '')
                                if partial_text:
                                    print(f"📝 Partial: '{partial_text}'")
                        else:
                            print(".", end="", flush=True)  # Show activity
                    
                    time.sleep(0.01)
                    
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    print(f"❌ Error in recognition: {e}")
                    time.sleep(0.1)
                    
            stream.stop_stream()
            stream.close()
            
        except Exception as e:
            print(f"❌ Failed to start recognition: {e}")
        finally:
            p.terminate()

if __name__ == "__main__":
    print("=== Wake Word Detection Test ===")
    
    test = SimpleWakeWordTest()
    
    print("\n1. Testing audio levels...")
    test.test_audio_levels()
    
    print("\n2. Testing wake word detection...")
    test.test_wake_word_detection() 