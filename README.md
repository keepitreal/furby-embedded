# 🎤 Furby Onboard Server (Python Edition)

A comprehensive Python server for controlling a Furby-like device with voice interaction capabilities. This server handles integrated wake word detection, voice recording with VAD, speech-to-text conversion, backend API communication, audio playback, and servo-controlled mouth movements.

## Features

- 🎯 **Integrated Wake Word Detection** with Vosk (local, open source)
- 🎤 **Voice Activity Detection (VAD)** for automatic recording start/stop
- 📝 **Speech-to-Text** with Vosk integration
- 🌐 **Backend API Communication** for chat responses with retry logic
- 🔊 **Audio Playback** with TTS support
- 🎭 **Servo Control** for mouth animation based on phonemes
- 🎭 **Emotion Expression** via servo movements
- 📊 **Status Monitoring** and health checks
- ⚙️ **Configurable** via environment variables
- 🔧 **Mock Mode** for development without hardware

## Prerequisites

### System Dependencies

1. **Python 3.7+** with pip

2. **Audio System** (auto-detected):

   - `PyAudio` for microphone input
   - `afplay` (macOS) / `aplay` (Linux) / `paplay` (PulseAudio) for playback

3. **GPIO Control** (Raspberry Pi only):

   - `pigpio` daemon for servo control
   - Runs in mock mode on development machines

4. **Vosk Models**:
   - Downloaded automatically via setup script
   - Local processing (no internet required for STT/wake word detection)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd furby-embedded

# Install Python dependencies
pip3 install -r requirements.txt

# Set up Vosk models and dependencies
chmod +x setup_vosk.sh
./setup_vosk.sh

# Create environment configuration
cp env.template .env
# Edit .env with your settings
```

## Configuration

Create a `.env` file based on `env.template`:

```bash
# Server Configuration
PORT=3000
HOST=0.0.0.0

# Backend API Configuration
BACKEND_URL=http://localhost:3001

# Audio Configuration
AUDIO_PATH=./audio
SAMPLE_RATE=16000
CHANNELS=1
FRAME_SIZE=4000

# Voice Activity Detection
VAD_SILENCE_DURATION=2.0
VAD_ENERGY_THRESHOLD=0.01
MAX_RECORDING_DURATION=30.0

# Wake Word Configuration
WAKE_WORDS=furby,hey furby,furby wake up
WAKE_WORD_COOLDOWN=5.0
WAKE_WORD_CONFIDENCE=0.7

# Model Paths
VOSK_MODEL_PATH=./models/vosk-model-small-en-us-0.15

# Servo Configuration (GPIO)
SERVO_PIN=18
SERVO_MIN_PULSE=500
SERVO_MAX_PULSE=2500
SERVO_CLOSED_POSITION=90
SERVO_OPEN_POSITION=45
```

## Usage

### Start the Server

```bash
# Start the Python server (includes integrated wake word detection)
python3 furby_server.py
```

The server will automatically:

- Initialize Vosk STT and wake word detection
- Start listening for wake words in the background
- Serve the Flask API on the configured port

### Wake Word Detection

The system uses **Vosk** for integrated wake word detection:

**Default Wake Words**: "furby", "hey furby", "furby wake up"

**How it works**:

1. Vosk continuously processes microphone audio locally
2. When wake word detected, pauses detection and starts VAD recording
3. Records until user stops speaking (silence detection)
4. Transcribes speech using Vosk STT
5. Sends to backend API and handles response
6. Resumes wake word detection after processing

**Key Features**:

- Local processing (no internet required)
- Automatic pause/resume to prevent feedback loops
- Configurable cooldown periods
- Confidence scoring
- Works on macOS, Linux, and Raspberry Pi

### Voice Activity Detection (VAD)

Advanced recording that automatically detects when user starts/stops speaking:

- **Energy-based detection** using audio amplitude analysis
- **Configurable silence duration** before stopping recording
- **Maximum recording duration** as safety limit
- **Real-time feedback** with dots showing recording progress

### API Endpoints

#### Health Check

```bash
GET /ping
```

Returns server status and version information.

#### System Status

```bash
GET /status
```

Returns detailed status of all subsystems:

- Server state and processing status
- Audio recording/playback state and available devices
- STT engine availability
- Servo control status and current position
- Backend health check results
- Wake word detection status and configured words

#### Manual Wake Word Trigger

```bash
POST /wake
```

Manually trigger the wake word detection flow for testing.

#### Response Playback

```bash
POST /respond
Content-Type: application/json

{
  "audio": "base64-encoded-audio-data",
  "phonemes": [
    { "start": 0.0, "end": 0.5, "phoneme": "H" },
    { "start": 0.5, "end": 1.0, "phoneme": "EH" },
    { "start": 1.0, "end": 1.5, "phoneme": "L" },
    { "start": 1.5, "end": 2.0, "phoneme": "OW" }
  ]
}
```

Plays TTS audio with synchronized mouth animation.

#### Servo Control

```bash
# Move servo to specific position (0-180 degrees)
POST /servo/position
{
  "position": 90
}

# Express emotion
POST /servo/emotion
{
  "emotion": "happy"  # happy, sad, excited, confused, sleepy
}
```

#### Audio File Access

```bash
# Access recorded audio files
GET /audio/<filename>
```

Serves audio files from the configured audio directory.

## Architecture

### Modular Design

The server is built with a modular architecture:

- **`furby_server.py`** - Main Flask application and orchestration
- **`audio_manager.py`** - Audio recording/playback with VAD
- **`wake_word_detector.py`** - Vosk-based wake word detection
- **`vosk_stt_engine.py`** - Speech-to-text transcription
- **`servo_controller.py`** - GPIO servo control with phoneme mapping
- **`backend_client.py`** - API communication with retry logic

### Configuration Management

- **`FurbyConfig`** class centralizes all environment-based configuration
- Supports development defaults with production overrides
- Automatic type conversion and validation

### Error Handling

- Comprehensive error handling with graceful degradation
- Mock modes for development without hardware
- Automatic fallback responses when backend unavailable
- Detailed logging with emoji indicators for easy debugging

## Development

### Mock Mode

The server automatically detects the environment and enables mock modes:

- **Audio**: Works with system microphone and speakers
- **Servo**: Logs servo movements to console instead of GPIO
- **Backend**: Uses fallback responses when backend unavailable

### Debugging

The server provides extensive logging:

- 🎯 Wake word detection events
- 🎤 Audio recording with VAD progress
- 📝 STT transcription results
- 🌐 Backend API communication
- 🎭 Servo control and animations
- ⚠️ Warnings and error conditions

### Testing

```bash
# Test microphone
python3 -c "from audio_manager import AudioManager; from furby_server import FurbyConfig; AudioManager(FurbyConfig()).test_microphone()"

# Test wake word detection
curl -X POST http://localhost:3000/wake

# Check system status
curl http://localhost:3000/status | python3 -m json.tool
```

## Hardware Setup

### Raspberry Pi GPIO

For servo control on Raspberry Pi:

```bash
# Install and start pigpio daemon
sudo apt install pigpio
sudo systemctl enable pigpiod
sudo systemctl start pigpiod

# Connect servo to GPIO pin 18 (configurable)
# Servo power: 5V
# Servo ground: GND
# Servo signal: GPIO18
```

### Audio Hardware

- **USB Microphone** recommended for better audio quality
- **Speaker/Audio Output** for TTS playback
- Test audio devices with `python3 -m pyaudio` to list available devices

## Troubleshooting

### Common Issues

1. **Audio Input/Output**:

   ```bash
   # List audio devices
   python3 -c "import pyaudio; p=pyaudio.PyAudio(); [print(f'{i}: {p.get_device_info_by_index(i)}') for i in range(p.get_device_count())]"
   ```

2. **GPIO Permission** (Raspberry Pi):

   ```bash
   sudo systemctl status pigpiod
   sudo systemctl start pigpiod
   ```

3. **Wake Word Not Detecting**:

   - Check microphone levels and background noise
   - Adjust `WAKE_WORD_CONFIDENCE` threshold
   - Verify Vosk model downloaded correctly

4. **Backend Connection**:
   - Verify `BACKEND_URL` in configuration
   - Check backend service is running
   - Review network connectivity

### Performance Optimization

- Use smaller Vosk models for faster processing
- Adjust `VAD_ENERGY_THRESHOLD` for your audio environment
- Optimize `FRAME_SIZE` for your hardware capabilities

## License

[Add your license information here]

## Contributing

[Add contributing guidelines here]
