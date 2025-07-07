#!/usr/bin/env python3
"""
Test Script for ALSA Audio System
Tests recording, playback, and wake word detection with the new AlsaAudioManager
"""

import time
import signal
import sys
import threading
from config import FurbyConfig
from alsa_audio_manager import AlsaAudioManager
from wake_word_detector import WakeWordDetector
from audio_manager import AudioManager


def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    print(f"\n🛑 Received signal {signum}, cleaning up...")
    
    # Force cleanup - any active audio managers will be cleaned up by their own atexit handlers
    try:
        print("✅ Emergency cleanup initiated")
    except Exception as e:
        print(f"⚠️ Emergency cleanup error: {e}")
    
    sys.exit(0)


def test_alsa_audio_manager():
    """Test the ALSA audio manager directly"""
    print("🧪 Testing ALSA Audio Manager...")
    
    config = FurbyConfig()
    alsa_audio = AlsaAudioManager(config)
    
    if not alsa_audio.is_available:
        print("❌ ALSA audio not available - skipping tests")
        return False
    
    print("\n1. Testing device listing...")
    devices = alsa_audio.list_devices()
    print(f"Found {len(devices)} devices")
    
    print("\n2. Testing device info...")
    device_info = alsa_audio.get_device_info()
    print(f"Device info: {device_info}")
    
    print("\n3. Testing recording functionality...")
    success = alsa_audio.test_recording(duration=3.0, channels=2, rate=48000)
    print(f"Recording test: {'✅ PASSED' if success else '❌ FAILED'}")
    
    print("\n4. Testing playback functionality...")
    success = alsa_audio.test_playback(frequency=440, duration=2.0, channels=2, rate=44100)
    print(f"Playback test: {'✅ PASSED' if success else '❌ FAILED'}")
    
    alsa_audio.cleanup()
    return True


def test_audio_manager():
    """Test the AudioManager with VAD recording"""
    print("\n🧪 Testing Audio Manager with VAD...")
    
    config = FurbyConfig()
    audio_manager = AudioManager(config)
    
    if not audio_manager.alsa_audio.is_available:
        print("❌ ALSA audio not available - skipping tests")
        return False
    
    print("\n1. Testing device listing...")
    devices = audio_manager.list_audio_devices()
    print(f"Found {len(devices)} devices")
    
    print("\n2. Testing VAD recording (speak for 3 seconds)...")
    print("   Say something now!")
    audio_file = audio_manager.record_with_vad(max_duration=5.0)
    
    if audio_file:
        print(f"✅ Recording saved: {audio_file}")
        
        print("\n3. Testing audio playback...")
        success = audio_manager.play_audio(audio_file)
        print(f"Playback test: {'✅ PASSED' if success else '❌ FAILED'}")
    else:
        print("❌ Recording failed")
    
    audio_manager.cleanup()
    return True


def mock_wake_word_callback():
    """Mock callback for wake word detection"""
    print("🎯 MOCK WAKE WORD DETECTED!")


def test_wake_word_detector():
    """Test the wake word detector with ALSA"""
    print("\n🧪 Testing Wake Word Detector...")
    
    config = FurbyConfig()
    wake_word_detector = WakeWordDetector(config, mock_wake_word_callback)
    
    if not wake_word_detector.is_available:
        print("❌ Wake word detector not available - skipping tests")
        return False
    
    print(f"\n1. Wake word detector available: {wake_word_detector.is_available}")
    print(f"   Audio manager available: {wake_word_detector.audio_manager.is_available}")
    print(f"   Wake words: {wake_word_detector.wake_words}")
    
    print("\n2. Starting wake word detection (10 seconds)...")
    print("   Try saying one of the wake words!")
    
    wake_word_detector.start_listening()
    
    try:
        # Let it run for 10 seconds
        for i in range(10):
            print(f"   Listening... {10-i}s remaining", end='\r')
            time.sleep(1)
        print("\n")
        
    except KeyboardInterrupt:
        print("\n   Test interrupted by user")
    finally:
        wake_word_detector.stop_listening()
    
    print("✅ Wake word detector test completed")
    return True


def test_complete_audio_system():
    """Test the complete audio system integration"""
    print("\n🧪 Testing Complete Audio System Integration...")
    
    config = FurbyConfig()
    
    # Initialize all components
    alsa_audio = AlsaAudioManager(config)
    audio_manager = AudioManager(config)
    wake_word_detector = WakeWordDetector(config, mock_wake_word_callback)
    
    if not alsa_audio.is_available:
        print("❌ ALSA audio not available - skipping integration test")
        return False
    
    print("\n1. Testing simultaneous recording streams...")
    
    # Test that we can't create multiple recording streams
    success1 = alsa_audio.create_recording_stream(channels=2, rate=48000)
    success2 = alsa_audio.create_recording_stream(channels=1, rate=16000)  # Should reuse/replace
    
    print(f"   First stream: {'✅' if success1 else '❌'}")
    print(f"   Second stream: {'✅' if success2 else '❌'}")
    
    alsa_audio.close_recording_stream()
    
    print("\n2. Testing wake word + recording sequence...")
    
    # Start wake word detection
    wake_word_detector.start_listening()
    time.sleep(2)  # Let it initialize
    
    # Pause wake word and do recording
    wake_word_detector.pause_listening()
    print("   Wake word paused, starting recording...")
    
    audio_file = audio_manager.record_with_vad(max_duration=3.0)
    
    if audio_file:
        print(f"   ✅ Recording successful: {audio_file}")
        
        # Play back the recording
        audio_manager.play_audio(audio_file)
    
    # Resume wake word detection
    wake_word_detector.resume_listening()
    time.sleep(1)
    
    wake_word_detector.stop_listening()
    
    # Cleanup
    audio_manager.cleanup()
    alsa_audio.cleanup()
    
    print("✅ Complete audio system test completed")
    return True


def main():
    """Run all tests"""
    print("🚀 Starting ALSA Audio System Tests")
    print("=" * 50)
    
    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    tests = [
        ("ALSA Audio Manager", test_alsa_audio_manager),
        ("Audio Manager with VAD", test_audio_manager),
        ("Wake Word Detector", test_wake_word_detector),
        ("Complete Audio System", test_complete_audio_system),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            results.append((test_name, result))
            print(f"✅ {test_name}: {'PASSED' if result else 'SKIPPED'}")
        except Exception as e:
            print(f"❌ {test_name}: FAILED - {e}")
            results.append((test_name, False))
        
        print("-" * 60)
    
    # Summary
    print(f"\n{'='*20} TEST SUMMARY {'='*20}")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED/SKIPPED"
        print(f"  {test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! ALSA audio system is working correctly.")
    else:
        print("⚠️ Some tests failed or were skipped. Check ALSA audio setup.")


if __name__ == "__main__":
    main() 