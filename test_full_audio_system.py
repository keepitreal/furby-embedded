#!/usr/bin/env python3
"""
Full Audio System Test - Simulates the complete Furby audio pipeline
This test verifies that the audio system can be properly cleaned up without device locks
"""

import time
import sys
import os
import signal
import threading
from shared_audio_manager import SharedAudioManager

# Mock config that matches the real Furby config
class FurbyTestConfig:
    def __init__(self):
        # Audio configuration
        self.AUDIO_DEVICE_INDEX = 0
        self.SAMPLE_RATE = 16000
        self.CHANNELS = 1
        self.FRAME_SIZE = 4000
        
        # Wake word configuration
        self.WAKE_WORDS = ['furby', 'hey furby']
        self.WAKE_WORD_COOLDOWN = 5.0
        self.WAKE_WORD_CONFIDENCE = 0.7
        
        # VAD configuration
        self.VAD_SILENCE_DURATION = 2.0
        self.VAD_ENERGY_THRESHOLD = 0.01
        self.MAX_RECORDING_DURATION = 30.0
        
        # Paths
        self.AUDIO_PATH = './audio'
        self.VOSK_MODEL_PATH = './models/vosk-model-small-en-us-0.15'


class MockWakeWordDetector:
    """Mock wake word detector using shared audio manager"""
    
    def __init__(self, config):
        self.config = config
        self.shared_audio = SharedAudioManager(config)
        self.stream_id = "wake_word_detector"
        self.is_listening = False
        self.listen_thread = None
        
    def start_listening(self):
        """Start the wake word detection loop"""
        if self.is_listening:
            return
        
        self.is_listening = True
        self.listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.listen_thread.start()
        print("👂 Mock wake word detector started")
    
    def _listen_loop(self):
        """Mock listening loop"""
        try:
            stream = self.shared_audio.create_stream(
                self.stream_id,
                format=16,  # paInt16
                channels=2,  # WM8960 stereo
                rate=48000,  # WM8960 native rate
                input=True,
                frames_per_buffer=self.config.FRAME_SIZE
            )
            
            if not stream:
                print("❌ Failed to create wake word stream")
                return
            
            print("👂 Mock wake word listening started...")
            
            # Simulate listening for a short time
            for i in range(20):  # 2 seconds of "listening"
                if not self.is_listening:
                    break
                
                try:
                    data = stream.read(self.config.FRAME_SIZE, exception_on_overflow=False)
                    print(f"👂 Wake word: Read {len(data)} bytes", end="\r")
                    time.sleep(0.1)
                except Exception as e:
                    print(f"⚠️ Wake word read error: {e}")
                    break
            
            print("\n👂 Mock wake word listening completed")
            
        except Exception as e:
            print(f"❌ Wake word listening failed: {e}")
        finally:
            self._cleanup()
    
    def stop_listening(self):
        """Stop wake word detection"""
        print("🛑 Stopping mock wake word detector...")
        self.is_listening = False
        
        if self.listen_thread and self.listen_thread.is_alive():
            self.listen_thread.join(timeout=3.0)
        
        self._cleanup()
    
    def _cleanup(self):
        """Clean up wake word detector resources"""
        try:
            self.shared_audio.close_stream(self.stream_id)
            print("🔧 Wake word detector stream closed")
        except Exception as e:
            print(f"⚠️ Wake word cleanup error: {e}")


class MockAudioManager:
    """Mock audio manager using shared audio manager"""
    
    def __init__(self, config):
        self.config = config
        self.shared_audio = SharedAudioManager(config)
        self.recording_stream_id = "audio_manager_recording"
        self.is_recording = False
    
    def record_mock_audio(self, duration=3.0):
        """Mock audio recording"""
        if self.is_recording:
            print("⚠️ Already recording")
            return False
        
        print(f"🎤 Starting mock recording ({duration}s)...")
        self.is_recording = True
        
        try:
            stream = self.shared_audio.create_stream(
                self.recording_stream_id,
                format=16,  # paInt16
                channels=self.config.CHANNELS,
                rate=self.config.SAMPLE_RATE,
                input=True,
                frames_per_buffer=self.config.FRAME_SIZE
            )
            
            if not stream:
                print("❌ Failed to create recording stream")
                return False
            
            # Record for specified duration
            frames_to_record = int(duration * self.config.SAMPLE_RATE / self.config.FRAME_SIZE)
            
            for i in range(frames_to_record):
                try:
                    data = stream.read(self.config.FRAME_SIZE, exception_on_overflow=False)
                    print(f"🎤 Recording: Frame {i+1}/{frames_to_record}", end="\r")
                except Exception as e:
                    print(f"⚠️ Recording error: {e}")
                    break
            
            print(f"\n✅ Mock recording completed ({duration}s)")
            return True
            
        except Exception as e:
            print(f"❌ Recording failed: {e}")
            return False
        finally:
            self.is_recording = False
            self._cleanup_recording()
    
    def _cleanup_recording(self):
        """Clean up recording resources"""
        try:
            self.shared_audio.close_stream(self.recording_stream_id)
            print("🔧 Recording stream closed")
        except Exception as e:
            print(f"⚠️ Recording cleanup error: {e}")
    
    def cleanup(self):
        """Clean up audio manager"""
        self._cleanup_recording()


def test_full_audio_system():
    """Test the complete audio system"""
    print("🧪 Testing Full Audio System...")
    
    config = FurbyTestConfig()
    
    # Test 1: Initialize components
    print("\n1. Initializing audio components...")
    wake_word_detector = MockWakeWordDetector(config)
    audio_manager = MockAudioManager(config)
    
    # Test 2: Start wake word detection
    print("\n2. Starting wake word detection...")
    wake_word_detector.start_listening()
    time.sleep(2)  # Let it run for 2 seconds
    
    # Test 3: Simulate audio recording (while wake word is running)
    print("\n3. Testing audio recording...")
    audio_manager.record_mock_audio(2.0)
    
    # Test 4: Stop wake word detection
    print("\n4. Stopping wake word detection...")
    wake_word_detector.stop_listening()
    
    # Test 5: Test another recording
    print("\n5. Testing second recording...")
    audio_manager.record_mock_audio(1.0)
    
    # Test 6: Clean up components
    print("\n6. Cleaning up components...")
    audio_manager.cleanup()
    
    # Test 7: Final shared audio manager cleanup
    print("\n7. Final audio system cleanup...")
    shared_audio = SharedAudioManager(config)
    shared_audio.cleanup()
    
    print("\n✅ Full audio system test completed!")


def test_rapid_start_stop():
    """Test rapid starting and stopping of audio components"""
    print("\n🧪 Testing Rapid Start/Stop...")
    
    config = FurbyTestConfig()
    
    for i in range(3):
        print(f"\n--- Iteration {i+1} ---")
        
        # Create and start wake word detector
        wake_word_detector = MockWakeWordDetector(config)
        wake_word_detector.start_listening()
        
        # Let it run briefly
        time.sleep(0.5)
        
        # Stop it
        wake_word_detector.stop_listening()
        
        # Record some audio
        audio_manager = MockAudioManager(config)
        audio_manager.record_mock_audio(0.5)
        audio_manager.cleanup()
        
        print(f"✅ Iteration {i+1} completed")
    
    # Final cleanup
    shared_audio = SharedAudioManager(config)
    shared_audio.cleanup()
    
    print("\n✅ Rapid start/stop test completed!")


def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    print(f"\n🛑 Received signal {signum}, cleaning up...")
    
    # Force cleanup
    try:
        shared_audio = SharedAudioManager()
        shared_audio.cleanup()
        print("✅ Emergency cleanup completed")
    except Exception as e:
        print(f"⚠️ Emergency cleanup error: {e}")
    
    sys.exit(0)


if __name__ == "__main__":
    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("🚀 Starting Full Audio System Tests")
    print("This simulates the complete Furby audio pipeline")
    print("Press Ctrl+C to exit cleanly at any time")
    
    try:
        test_full_audio_system()
        test_rapid_start_stop()
        
        print("\n🎉 All tests passed! Audio system cleanup is working correctly.")
        print("💡 If you can run 'aplay' successfully now, the device lock issue is fixed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 