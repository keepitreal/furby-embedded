#!/usr/bin/env python3
"""
Configuration for Furby Application
"""

import os


class FurbyConfig:
    """Configuration management for Furby"""
    
    def __init__(self):
        # Server configuration
        self.PORT = int(os.getenv('PORT', 3000))
        self.HOST = os.getenv('HOST', '0.0.0.0')
        self.DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
        self.DEVELOPMENT_MODE = os.getenv('DEVELOPMENT_MODE', 'true').lower() == 'true'
        
        # Backend configuration
        self.BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:3001')
        
        # Audio configuration
        self.AUDIO_PATH = os.getenv('AUDIO_PATH', './audio')
        self.SAMPLE_RATE = int(os.getenv('SAMPLE_RATE', 16000))
        self.CHANNELS = int(os.getenv('CHANNELS', 2))  # Changed to stereo for WM8960 compatibility
        self.FRAME_SIZE = int(os.getenv('FRAME_SIZE', 4000))
        self.AUDIO_DEVICE_INDEX = int(os.getenv('AUDIO_DEVICE_INDEX', 0))
        
        # Voice Activity Detection
        self.VAD_SILENCE_DURATION = float(os.getenv('VAD_SILENCE_DURATION', 2.0))  # seconds
        self.VAD_ENERGY_THRESHOLD = float(os.getenv('VAD_ENERGY_THRESHOLD', 0.01))
        self.MAX_RECORDING_DURATION = float(os.getenv('MAX_RECORDING_DURATION', 30.0))  # seconds
        
        # Wake word configuration
        self.WAKE_WORDS = os.getenv('WAKE_WORDS', 'furby,hey furby,furby wake up').split(',')
        self.WAKE_WORD_COOLDOWN = float(os.getenv('WAKE_WORD_COOLDOWN', 5.0))
        self.WAKE_WORD_CONFIDENCE = float(os.getenv('WAKE_WORD_CONFIDENCE', 0.7))
        
        # Model paths
        self.VOSK_MODEL_PATH = os.getenv('VOSK_MODEL_PATH', './models/vosk-model-small-en-us-0.15')
        
        # Servo configuration
        self.SERVO_PIN = int(os.getenv('SERVO_PIN', 18))
        self.SERVO_MIN_PULSE = int(os.getenv('SERVO_MIN_PULSE', 500))
        self.SERVO_MAX_PULSE = int(os.getenv('SERVO_MAX_PULSE', 2500))
        self.SERVO_CLOSED_POSITION = int(os.getenv('SERVO_CLOSED_POSITION', 90))
        self.SERVO_OPEN_POSITION = int(os.getenv('SERVO_OPEN_POSITION', 45))
        
        print(f"🔧 Configuration loaded:")
        print(f"   Server: {self.HOST}:{self.PORT}")
        print(f"   Backend: {self.BACKEND_URL}")
        print(f"   Audio: {self.SAMPLE_RATE}Hz, {self.CHANNELS}ch")
        print(f"   Wake words: {len(self.WAKE_WORDS)} configured")
        print(f"   Development mode: {self.DEVELOPMENT_MODE}") 