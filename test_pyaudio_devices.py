#!/usr/bin/env python3
"""
Test PyAudio device detection and WM8960 HAT access
"""
import pyaudio
import sys

def list_audio_devices():
    """List all available audio devices"""
    p = pyaudio.PyAudio()
    print("=== Available Audio Devices ===")
    
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        print(f"Device {i}: {info['name']}")
        print(f"  - Max input channels: {info['maxInputChannels']}")
        print(f"  - Max output channels: {info['maxOutputChannels']}")
        print(f"  - Default sample rate: {info['defaultSampleRate']}")
        print(f"  - Host API: {p.get_host_api_info_by_index(int(info['hostApi']))['name']}")
        print()
    
    p.terminate()

def test_device_access(device_name=None, device_index=None):
    """Test opening a specific audio device"""
    p = pyaudio.PyAudio()
    
    print(f"=== Testing Device Access ===")
    print(f"Device: {device_name or f'Index {device_index}'}")
    
    try:
        # Test parameters that match our WM8960 setup
        stream = p.open(
            format=pyaudio.paInt16,
            channels=2,  # Stereo for WM8960
            rate=48000,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=1024
        )
        print("✅ Successfully opened audio stream!")
        stream.close()
        
    except Exception as e:
        print(f"❌ Failed to open audio stream: {e}")
    
    p.terminate()

def find_wm8960_device():
    """Try to find the WM8960 device"""
    p = pyaudio.PyAudio()
    
    print("=== Searching for WM8960 Device ===")
    
    # Look for devices with "wm8960" or "WM8960" in the name
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        name = str(info['name']).lower()
        
        if 'wm8960' in name or 'soundcard' in name or int(info['maxInputChannels']) >= 2:
            print(f"Potential WM8960 device found:")
            print(f"  Index: {i}")
            print(f"  Name: {info['name']}")
            print(f"  Input channels: {info['maxInputChannels']}")
            print(f"  Sample rate: {info['defaultSampleRate']}")
            print()
            
            # Test this device
            test_device_access(info['name'], i)
    
    p.terminate()

if __name__ == "__main__":
    print("PyAudio Device Detection and Testing")
    print("=" * 50)
    
    # List all devices
    list_audio_devices()
    
    # Try to find WM8960
    find_wm8960_device()
    
    # Test default device
    print("=== Testing Default Device ===")
    test_device_access("default", None) 