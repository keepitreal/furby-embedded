# ALSA Audio System Migration

## Overview

The Furby embedded system has been migrated from PyAudio to ALSA (Advanced Linux Sound Architecture) for better WM8960 Audio HAT compatibility and more reliable audio operations.

## Key Changes Made

### 1. New Audio Architecture

**Before (PyAudio-based):**

- `shared_audio_manager.py` - Singleton PyAudio instance manager
- Device locks at kernel level after cleanup
- Required reboots between runs
- Inconsistent audio output

**After (ALSA-based):**

- `alsa_audio_manager.py` - Direct ALSA interface using `alsaaudio`
- `config.py` - Centralized configuration management
- Proper cleanup without device locks
- Native WM8960 HAT support

### 2. Files Modified

#### New Files:

- `alsa_audio_manager.py` - Core ALSA audio functionality
- `config.py` - Configuration management
- `test_alsa_audio.py` - Comprehensive test suite

#### Updated Files:

- `wake_word_detector.py` - Uses ALSA instead of PyAudio
- `audio_manager.py` - ALSA recording/playback with fallback
- `furby_server.py` - Updated initialization and cleanup order

#### Deprecated Files:

- `shared_audio_manager.py` - No longer needed
- Test files using PyAudio - Replaced with ALSA tests

### 3. Key Features

#### ALSA Audio Manager (`alsa_audio_manager.py`)

- **Native WM8960 support** - Uses `hw:0,0` device directly
- **Stereo recording** - 48kHz native rate, resampled to 16kHz for Vosk
- **Robust cleanup** - Proper stream management and resource cleanup
- **Comprehensive logging** - Debug information for troubleshooting
- **Fallback support** - Graceful degradation when ALSA unavailable

#### Wake Word Detection (`wake_word_detector.py`)

- **ALSA integration** - Direct audio stream processing
- **Audio processing** - Stereo to mono conversion with resampling
- **Pause/resume** - Proper audio resource management during recording
- **Debug logging** - Audio levels and processing information

#### Audio Manager (`audio_manager.py`)

- **VAD recording** - Voice Activity Detection using ALSA
- **Playback options** - ALSA primary, system fallback
- **File management** - Proper audio file handling and cleanup

## Setup Instructions

### 1. Install Required Dependencies

```bash
# Install ALSA development headers
sudo apt-get install libasound2-dev

# Compile and install pyalsaaudio
git clone https://github.com/larsimmisch/pyalsaaudio
cd pyalsaaudio
sudo python3 setup.py build
sudo python3 setup.py install
```

### 2. Configure Audio Device

Ensure your WM8960 Audio HAT is properly configured:

```bash
# Check if device is available
aplay -l

# Should show:
# card 0: wm8960soundcard [wm8960-soundcard], device 0: ...

# Test playback
aplay -D hw:0,0 /usr/share/sounds/alsa/Front_Left.wav
```

### 3. Enable Microphone Input

```bash
# Enable microphone boost mixers
amixer sset 'Left Boost Mixer LINPUT2' on
amixer sset 'Right Boost Mixer RINPUT2' on
amixer sset 'Left Boost Mixer LINPUT3' on
amixer sset 'Right Boost Mixer RINPUT3' on

# Set appropriate volume levels
amixer sset 'Speaker' 100%
amixer sset 'Headphone' 100%
```

## Testing the System

### 1. Basic ALSA Test

```bash
# Run comprehensive test suite
python3 test_alsa_audio.py

# Expected output:
# ✅ ALSA Audio Manager: PASSED
# ✅ Audio Manager with VAD: PASSED
# ✅ Wake Word Detector: PASSED
# ✅ Complete Audio System: PASSED
```

### 2. Manual Component Testing

```bash
# Test individual components
python3 -c "
from alsa_audio_manager import AlsaAudioManager
from config import FurbyConfig
config = FurbyConfig()
alsa = AlsaAudioManager(config)
print('ALSA Available:', alsa.is_available)
alsa.list_devices()
"
```

### 3. Wake Word Detection Test

```bash
# Test wake word detection
python3 -c "
from wake_word_detector import WakeWordDetector
from config import FurbyConfig
config = FurbyConfig()
wwd = WakeWordDetector(config, lambda: print('Wake word detected!'))
print('Available:', wwd.is_available)
wwd.start_listening()
input('Press Enter to stop...')
wwd.stop_listening()
"
```

## Running the Full System

### 1. Start the Server

```bash
# Start the Furby server
python3 furby_server.py

# Expected output:
# ✅ alsaaudio imported successfully
# 🔧 Configuration loaded:
#    Server: 0.0.0.0:3000
#    Backend: http://localhost:3001
#    Audio: 16000Hz, 1ch
#    Wake words: 3 configured
#    Development mode: True
# 🔧 AlsaAudioManager initialized for device: hw:0,0
# 🔍 ALSA Device Information:
#    Device: hw:0,0
#    Available cards: ['wm8960soundcard']
#    Available PCMs: ['hw:0,0', 'hw:0,1']
# ✅ Furby Server initialization complete
#    Audio system: ALSA
#    Wake word detection: Enabled
#    STT engine: Enabled
#    Servo controller: Enabled
```

### 2. Test API Endpoints

```bash
# Health check
curl http://localhost:3000/health

# Start wake word detection
curl -X POST http://localhost:3000/start_listening

# Record audio
curl -X POST http://localhost:3000/record -H "Content-Type: application/json" -d '{"max_duration": 5}'

# List audio devices
curl http://localhost:3000/devices
```

## Troubleshooting

### Common Issues

#### 1. `alsaaudio` Import Error

```bash
# Error: ModuleNotFoundError: No module named 'alsaaudio'
# Solution: Reinstall pyalsaaudio
sudo python3 -c "import pyalsaaudio; print('OK')"
```

#### 2. Audio Device Not Found

```bash
# Error: Device 'hw:0,0' not found
# Solution: Check device configuration
aplay -l
amixer -c 0 scontrols
```

#### 3. No Audio Output

```bash
# Check mixer settings
amixer -c 0 sget 'Speaker'
amixer -c 0 sget 'Headphone'

# Enable output mixers
amixer -c 0 sset 'Mono Output Mixer Left' on
amixer -c 0 sset 'Mono Output Mixer Right' on
```

#### 4. No Microphone Input

```bash
# Enable microphone boost
amixer sset 'Left Boost Mixer LINPUT2' on
amixer sset 'Right Boost Mixer RINPUT2' on

# Test recording
arecord -D hw:0,0 -f S16_LE -r 48000 -c 2 test.wav
```

### Debug Logging

The system includes comprehensive logging for debugging:

```python
# Audio level monitoring
🎤 Wake word audio level: 1247.3

# Stream management
🔧 Creating ALSA recording stream for wake word detection...
✅ Recording stream created successfully
🔧 Recording stream closed

# Device information
🔍 ALSA Device Information:
   Device: hw:0,0
   Format: 2
   Sample Width: 2 bytes
   Available cards: ['wm8960soundcard']
```

## Performance Improvements

### Before Migration:

- ❌ Device locks requiring reboots
- ❌ Inconsistent audio output
- ❌ PyAudio conflicts with pigpiod
- ❌ Complex stream management

### After Migration:

- ✅ No device locks - clean shutdown
- ✅ Reliable audio output
- ✅ Native ALSA compatibility
- ✅ Simplified audio pipeline
- ✅ Better error handling and logging

## Migration Benefits

1. **Stability**: No more device locks or required reboots
2. **Performance**: Direct ALSA interface with lower latency
3. **Compatibility**: Native WM8960 HAT support
4. **Reliability**: Proper resource management and cleanup
5. **Debugging**: Comprehensive logging for troubleshooting
6. **Maintainability**: Cleaner architecture with clear separation of concerns

## Next Steps

1. **Test thoroughly** with your specific hardware setup
2. **Monitor audio levels** during operation
3. **Verify wake word detection** accuracy
4. **Check audio playback** quality
5. **Test concurrent operations** (wake word + recording)

The ALSA migration provides a solid foundation for reliable audio operations on the Raspberry Pi with WM8960 Audio HAT.
