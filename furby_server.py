#!/usr/bin/env python3
"""
Furby Onboard Server - Complete Python Implementation
Main server with imported components for modularity
"""

import json
import sys
import os
import threading
import time
from typing import Optional, Dict, Any, List
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import signal
import atexit
from datetime import datetime

# Import our modular components
from audio_manager import AudioManager
from servo_controller import ServoController
from vosk_stt_engine import VoskSTTEngine
from wake_word_detector import WakeWordDetector
from backend_client import BackendClient


class FurbyConfig:
    """Configuration management"""
    def __init__(self):
        # Server configuration
        self.PORT = int(os.getenv('PORT', 3000))
        self.HOST = os.getenv('HOST', '0.0.0.0')
        self.DEVELOPMENT_MODE = os.getenv('DEVELOPMENT_MODE', 'true').lower() == 'true'
        
        # Backend configuration
        self.BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:3001')
        
        # Audio configuration
        self.AUDIO_PATH = os.getenv('AUDIO_PATH', './audio')
        self.SAMPLE_RATE = int(os.getenv('SAMPLE_RATE', 16000))
        self.CHANNELS = int(os.getenv('CHANNELS', 1))
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


class FurbyServer:
    """Main Furby server application"""
    
    def __init__(self):
        self.config = FurbyConfig()
        self.app = Flask(__name__)
        CORS(self.app)
        
        # Initialize components
        self.audio_manager = AudioManager(self.config)
        self.servo_controller = ServoController(self.config)
        self.stt_engine = VoskSTTEngine(self.config)
        self.backend_client = BackendClient(self.config)
        self.wake_word_detector = WakeWordDetector(self.config, self.handle_wake_word)
        
        self.is_processing = False
        self.setup_routes()
        self.setup_shutdown_handlers()
    
    def setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/ping', methods=['GET'])
        def ping():
            return jsonify({
                'status': 'ok',
                'timestamp': datetime.now().isoformat(),
                'version': '2.0.0-python'
            })
        
        @self.app.route('/status', methods=['GET'])
        def status():
            return jsonify({
                'server': {
                    'status': 'running',
                    'is_processing': self.is_processing,
                    'wake_word_method': 'vosk_integrated'
                },
                'audio': {
                    'is_recording': self.audio_manager.is_recording,
                    'is_playing': self.audio_manager.is_playing,
                    'devices': self.audio_manager.list_audio_devices()
                },
                'stt': {
                    'engine': 'vosk',
                    'available': self.stt_engine.is_available
                },
                'servo': {
                    'active': self.servo_controller.is_active,
                    'position': self.servo_controller.current_position
                },
                'backend': {
                    'url': self.config.BACKEND_URL,
                    'healthy': self.backend_client.health_check()
                },
                'wake_word': {
                    'available': self.wake_word_detector.is_available,
                    'listening': self.wake_word_detector.is_listening,
                    'words': self.config.WAKE_WORDS
                }
            })
        
        @self.app.route('/wake', methods=['POST'])
        def wake():
            """Manual wake word trigger"""
            print("🎯 Manual wake word trigger")
            threading.Thread(target=self.handle_wake_word, daemon=True).start()
            return jsonify({'success': True, 'message': 'Wake word processing initiated'})
        
        @self.app.route('/respond', methods=['POST'])
        def respond():
            """Play TTS response with servo animation"""
            try:
                data = request.get_json()
                audio_b64 = data.get('audio')
                phonemes = data.get('phonemes', [])
                
                if not audio_b64:
                    return jsonify({'error': 'Audio data required'}), 400
                
                print("🎵 Received TTS audio and phoneme data")
                
                # Save and play audio
                # Save as output file in development mode, otherwise as TTS
                audio_type = 'output' if self.config.DEVELOPMENT_MODE else 'tts'
                audio_file = self.audio_manager.save_base64_audio(audio_b64, audio_type=audio_type)
                
                # Start audio and servo animation in parallel
                audio_thread = threading.Thread(target=self.audio_manager.play_audio, args=(audio_file,))
                servo_thread = threading.Thread(target=self.servo_controller.animate_mouth, args=(phonemes,))
                
                audio_thread.start()
                servo_thread.start()
                
                audio_thread.join()
                servo_thread.join()
                
                return jsonify({'success': True, 'message': 'Response played successfully'})
                
            except Exception as e:
                print(f"❌ Response playback error: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/servo/position', methods=['POST'])
        def servo_position():
            """Set servo position"""
            try:
                data = request.get_json()
                position = data.get('position')
                
                if position is None or not (0 <= position <= 180):
                    return jsonify({'error': 'Position must be between 0 and 180'}), 400
                
                self.servo_controller.move_to_position(position)
                return jsonify({'success': True, 'position': position})
                
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/servo/emotion', methods=['POST'])
        def servo_emotion():
            """Express emotion via servo"""
            try:
                data = request.get_json()
                emotion = data.get('emotion', 'happy')
                
                threading.Thread(target=self.servo_controller.express_emotion, args=(emotion,), daemon=True).start()
                return jsonify({'success': True, 'emotion': emotion})
                
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/audio/<path:filename>')
        def serve_audio(filename):
            """Serve audio files"""
            return send_from_directory(self.config.AUDIO_PATH, filename)
    
    def handle_wake_word(self):
        """Handle wake word detection"""
        if self.is_processing:
            print("🔄 Already processing a voice command...")
            return
        
        print("🎯 Wake word detected! Starting voice processing...")
        self.is_processing = True
        
        try:
            # Record audio with VAD
            print("🎤 Recording with voice activity detection...")
            audio_file = self.audio_manager.record_with_vad()
            
            if not audio_file:
                print("❌ No audio recorded")
                return
            
            # Transcribe with Vosk
            print("📝 Converting speech to text...")
            transcription = self.stt_engine.transcribe_audio_file(audio_file)
            
            if not transcription or not transcription.strip():
                print("⚠️ No speech detected")
                return
            
            print(f"📋 Transcription: '{transcription}'")
            
            # Send to backend
            print("🌐 Sending to backend...")
            response = self.backend_client.send_text_for_response(transcription)
            
            # Handle response
            print(f"🔍 Response analysis: audio={bool(response.get('audio'))}, phonemes={len(response.get('phonemes', []))}, fallback={response.get('isFallback')}")
            
            if response.get('audio') and not response.get('isFallback'):
                print("🎵 Playing audio with phoneme animation")
                # Play TTS audio with mouth animation
                # Save as output file in development mode, otherwise as TTS
                audio_type = 'output' if self.config.DEVELOPMENT_MODE else 'tts'
                print(f"🔍 Saving audio as: {audio_type} (dev_mode={self.config.DEVELOPMENT_MODE})")
                audio_file = self.audio_manager.save_base64_audio(response['audio'], audio_type=audio_type)
                
                audio_thread = threading.Thread(target=self.audio_manager.play_audio, args=(audio_file,))
                servo_thread = threading.Thread(target=self.servo_controller.animate_mouth, args=(response.get('phonemes', []),))
                
                audio_thread.start()
                servo_thread.start()
                
                audio_thread.join()
                servo_thread.join()
                
            elif response.get('phonemes'):
                print("🎭 Phoneme-only animation (no audio)")
                # Just mouth animation
                self.servo_controller.animate_mouth(response['phonemes'])
            else:
                print("🎭 Fallback animation (no audio, no phonemes)")
                # Fallback animation
                self.servo_controller.animate_mouth()
            
            print("✅ Voice interaction completed")
            
        except Exception as e:
            print(f"❌ Voice processing error: {e}")
            # Express sad emotion on error
            try:
                self.servo_controller.express_emotion('sad')
            except:
                pass
        finally:
            self.is_processing = False
            # Resume wake word detection after processing
            if hasattr(self.wake_word_detector, 'resume_listening'):
                # Add a small delay before resuming to prevent immediate re-triggering
                time.sleep(1)
                self.wake_word_detector.resume_listening()
    
    def setup_shutdown_handlers(self):
        """Setup graceful shutdown"""
        def shutdown_handler(signum, frame):
            print(f"\n🛑 Received signal {signum}, shutting down...")
            self.cleanup()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, shutdown_handler)
        signal.signal(signal.SIGTERM, shutdown_handler)
        atexit.register(self.cleanup)
    
    def cleanup(self):
        """Cleanup all resources"""
        print("🧹 Cleaning up resources...")
        
        try:
            self.wake_word_detector.stop_listening()
            self.audio_manager.cleanup()
            self.servo_controller.cleanup()
        except Exception as e:
            print(f"⚠️ Cleanup error: {e}")
        
        print("✅ Cleanup completed")
    
    def run(self):
        """Start the Furby server"""
        print("🚀 Starting Furby Server (Python Edition)")
        print(f"🎯 Wake words: {', '.join(self.config.WAKE_WORDS)}")
        print(f"🌐 Backend URL: {self.config.BACKEND_URL}")
        print(f"📁 Audio path: {self.config.AUDIO_PATH}")
        
        # Check dependencies
        if not self.wake_word_detector.is_available:
            print("⚠️ Wake word detection not available - manual /wake trigger only")
        if not self.stt_engine.is_available:
            print("⚠️ STT not available - voice interaction disabled")
        if not self.servo_controller.is_active:
            print("⚠️ Servo control not active - using mock animations")
        
        # Start wake word detection
        self.wake_word_detector.start_listening()
        
        # Start Flask server
        print(f"🚀 Server starting on {self.config.HOST}:{self.config.PORT}")
        self.app.run(
            host=self.config.HOST,
            port=self.config.PORT,
            debug=False,
            threaded=True
        )


if __name__ == '__main__':
    server = FurbyServer()
    server.run() 