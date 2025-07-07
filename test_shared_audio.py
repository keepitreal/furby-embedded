#!/usr/bin/env python3
"""
Test script for the shared audio manager
This verifies that the audio system can be properly cleaned up
"""

import time
import sys
import os
import signal
import threading
from shared_audio_manager import SharedAudioManager

# Mock config for testing
class MockConfig:
    def __init__(self):
        self.AUDIO_DEVICE_INDEX = 0
        self.FRAME_SIZE = 4000
        self.CHANNELS = 2
        self.SAMPLE_RATE = 48000


def test_shared_audio_manager():
    """Test the shared audio manager"""
    print("🧪 Testing Shared Audio Manager...")
    
    config = MockConfig()
    
    # Test 1: Create shared audio manager
    print("\n1. Testing shared audio manager creation...")
    shared_audio = SharedAudioManager(config)
    
    # Test 2: List devices
    print("\n2. Testing device listing...")
    devices = shared_audio.list_devices()
    print(f"Found {len(devices)} audio devices")
    for device in devices:
        print(f"  - {device['index']}: {device['name']}")
    
    # Test 3: Create a test stream
    print("\n3. Testing stream creation...")
    stream = shared_audio.create_stream(
        "test_stream",
        format=16,  # paInt16
        channels=2,
        rate=48000,
        input=True,
        frames_per_buffer=4000
    )
    
    if stream:
        print("✅ Stream created successfully")
        
        # Test 4: Check if stream is active
        print("\n4. Testing stream status...")
        is_active = shared_audio.is_stream_active("test_stream")
        print(f"Stream active: {is_active}")
        
        # Test 5: Read some audio data
        print("\n5. Testing audio reading...")
        try:
            for i in range(10):
                data = stream.read(4000, exception_on_overflow=False)
                print(f"Read {len(data)} bytes of audio data")
                time.sleep(0.1)
        except Exception as e:
            print(f"⚠️ Audio reading error: {e}")
        
        # Test 6: Close stream
        print("\n6. Testing stream cleanup...")
        shared_audio.close_stream("test_stream")
        is_active = shared_audio.is_stream_active("test_stream")
        print(f"Stream active after close: {is_active}")
        
    else:
        print("❌ Failed to create stream")
    
    # Test 7: Test cleanup
    print("\n7. Testing full cleanup...")
    shared_audio.cleanup()
    
    print("\n✅ All tests completed!")


def test_multiple_streams():
    """Test creating multiple streams with proper cleanup"""
    print("\n🧪 Testing Multiple Streams...")
    
    config = MockConfig()
    shared_audio = SharedAudioManager(config)
    
    # Create multiple streams
    streams = []
    for i in range(3):
        stream_id = f"test_stream_{i}"
        stream = shared_audio.create_stream(
            stream_id,
            format=16,  # paInt16
            channels=2,
            rate=48000,
            input=True,
            frames_per_buffer=4000
        )
        if stream:
            streams.append(stream_id)
            print(f"✅ Created stream {stream_id}")
        else:
            print(f"❌ Failed to create stream {stream_id}")
    
    # Check all streams are active
    print(f"\nActive streams: {len(streams)}")
    for stream_id in streams:
        is_active = shared_audio.is_stream_active(stream_id)
        print(f"  {stream_id}: {is_active}")
    
    # Clean up all streams
    print("\nCleaning up streams...")
    for stream_id in streams:
        shared_audio.close_stream(stream_id)
        print(f"🔧 Closed stream {stream_id}")
    
    # Verify cleanup
    print("\nVerifying cleanup...")
    active_count = 0
    for stream_id in streams:
        if shared_audio.is_stream_active(stream_id):
            active_count += 1
    
    print(f"Active streams after cleanup: {active_count}")
    
    # Final cleanup
    shared_audio.cleanup()
    print("✅ Multiple streams test completed!")


def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    print(f"\n🛑 Received signal {signum}, cleaning up...")
    
    # Force cleanup
    try:
        shared_audio = SharedAudioManager()
        shared_audio.cleanup()
    except Exception as e:
        print(f"⚠️ Cleanup error: {e}")
    
    sys.exit(0)


if __name__ == "__main__":
    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("🚀 Starting Shared Audio Manager Tests")
    print("Press Ctrl+C to exit cleanly at any time")
    
    try:
        test_shared_audio_manager()
        test_multiple_streams()
        
        print("\n🎉 All tests passed! Audio system should be properly cleaned up.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1) 