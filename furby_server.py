#!/usr/bin/env python3
"""
Furby Server - Main Application Entry Point
"""

import os
import signal
import sys
import threading
import time
from flask import Flask, request, jsonify

# Import Furby components
from audio_manager import AudioManager
from servo_controller import ServoController
from wake_word_detector import WakeWordDetector
from vosk_stt_engine import VoskSTTEngine
from backend_client import BackendClient

# Import configuration
from config import FurbyConfig


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    print(f"\n🛑 Received signal {signum}, shutting down gracefully...")
    
    # Get the server instance if it exists
    if 'furby_server' in globals():
        furby_server.cleanup()
    
    print("✅ Shutdown complete")
    sys.exit(0)


class FurbyServer:
    """Main Furby server application with ALSA audio support"""
    
    def __init__(self):
        print("🚀 Initializing Furby Server with ALSA Audio...")
        
        # Load configuration
        self.config = FurbyConfig()
        
        # Initialize Flask app
        self.app = Flask(__name__)
        
        # Initialize audio system first
        print("🔧 Initializing audio system...")
        self.audio_manager = AudioManager(self.config)
        
        # Initialize other components
        print("🔧 Initializing servo controller...")
        self.servo_controller = ServoController(self.config)
        
        print("🔧 Initializing speech-to-text engine...")
        self.stt_engine = VoskSTTEngine(self.config)
        
        print("🔧 Initializing backend client...")
        self.backend_client = BackendClient(self.config)
        
        # Initialize wake word detector (depends on audio system)
        print("🔧 Initializing wake word detector...")
        self.wake_word_detector = WakeWordDetector(self.config, self.handle_wake_word)
        
        # Server state
        self.is_processing = False
        
        # Setup Flask routes
        self.setup_routes()
        
        print("✅ Furby Server initialization complete")
        print(f"   Audio system: {'ALSA' if self.audio_manager.alsa_audio.is_available else 'Fallback'}")
        print(f"   Wake word detection: {'Enabled' if self.wake_word_detector.is_available else 'Disabled'}")
        print(f"   STT engine: {'Enabled' if self.stt_engine.is_available else 'Disabled'}")
        print(f"   Servo controller: {'Enabled' if self.servo_controller.is_active else 'Disabled'}")
        
    def setup_routes(self):
        """Setup Flask API routes"""
        
        @self.app.route('/health', methods=['GET'])
        def health():
            """Health check endpoint"""
            return jsonify({
                'status': 'healthy',
                'audio_system': 'alsa' if self.audio_manager.alsa_audio.is_available else 'fallback',
                'wake_word_detector': self.wake_word_detector.is_available,
                'stt_engine': self.stt_engine.is_available,
                'servo_controller': self.servo_controller.is_active,
                'is_processing': self.is_processing
            })
        
        @self.app.route('/start_listening', methods=['POST'])
        def start_listening():
            """Start wake word detection"""
            try:
                print("📡 API: Starting wake word detection...")
                self.wake_word_detector.start_listening()
                return jsonify({'success': True, 'message': 'Wake word detection started'})
            except Exception as e:
                print(f"❌ Start listening error: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/stop_listening', methods=['POST'])
        def stop_listening():
            """Stop wake word detection"""
            try:
                print("📡 API: Stopping wake word detection...")
                self.wake_word_detector.stop_listening()
                return jsonify({'success': True, 'message': 'Wake word detection stopped'})
            except Exception as e:
                print(f"❌ Stop listening error: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/record', methods=['POST'])
        def record():
            """Record audio with VAD"""
            try:
                data = request.get_json()
                max_duration = data.get('max_duration', self.config.MAX_RECORDING_DURATION)
                
                print(f"📡 API: Recording audio (max {max_duration}s)...")
                audio_file = self.audio_manager.record_with_vad(max_duration)
                
                if audio_file:
                    return jsonify({'success': True, 'audio_file': audio_file})
                else:
                    return jsonify({'error': 'Recording failed'}), 500
                    
            except Exception as e:
                print(f"❌ Recording error: {e}")
                return jsonify({'error': str(e)}), 500
        
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
        
        @self.app.route('/servo/<action>', methods=['POST'])
        def servo_control(action):
            """Control servo actions"""
            try:
                data = request.get_json() or {}
                
                if action == 'move_to_position':
                    position = data.get('position', 90)
                    self.servo_controller.move_to_position(position)
                elif action == 'animate_mouth':
                    phonemes = data.get('phonemes', [])
                    self.servo_controller.animate_mouth(phonemes)
                elif action == 'express_emotion':
                    emotion = data.get('emotion', 'neutral')
                    self.servo_controller.express_emotion(emotion)
                else:
                    return jsonify({'error': 'Unknown servo action'}), 400
                
                return jsonify({'success': True, 'action': action})
                
            except Exception as e:
                print(f"❌ Servo control error: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/devices', methods=['GET'])
        def list_devices():
            """List available audio devices"""
            try:
                print("📡 API: Listing audio devices...")
                devices = self.audio_manager.list_audio_devices()
                return jsonify({'devices': devices})
            except Exception as e:
                print(f"❌ Device listing error: {e}")
                return jsonify({'error': str(e)}), 500
    
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
            print(f"   Error type: {type(e).__name__}")
            # Express sad emotion on error
            try:
                self.servo_controller.express_emotion('sad')
            except:
                pass
        finally:
            self.is_processing = False
            # Resume wake word detection after processing
            try:
                self.wake_word_detector.resume_listening()
            except Exception as e:
                print(f"⚠️ Failed to resume wake word detection: {e}")
    
    def run(self):
        """Start the Furby server"""
        print("🚀 Starting Furby Server...")
        
        # Start wake word detection
        print("👂 Starting wake word detection...")
        self.wake_word_detector.start_listening()
        
        try:
            # Start Flask server
            print(f"🌐 Starting web server on {self.config.HOST}:{self.config.PORT}")
            self.app.run(
                host=self.config.HOST,
                port=self.config.PORT,
                debug=self.config.DEBUG,
                threaded=True
            )
        except KeyboardInterrupt:
            print("\n🛑 Keyboard interrupt received")
        except Exception as e:
            print(f"❌ Server error: {e}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Cleanup all resources in proper order for ALSA"""
        print("🧹 Cleaning up Furby Server...")
        
        cleanup_errors = []
        
        # 1. Stop wake word detection first (releases audio resources)
        try:
            print("🛑 Stopping wake word detection...")
            self.wake_word_detector.stop_listening()
            print("✅ Wake word detection stopped")
        except Exception as e:
            cleanup_errors.append(f"Wake word cleanup: {e}")
            print(f"⚠️ Wake word cleanup error: {e}")
        
        # 2. Clean up audio manager (closes ALSA streams)
        try:
            print("🧹 Cleaning up audio manager...")
            self.audio_manager.cleanup()
            print("✅ Audio manager cleanup completed")
        except Exception as e:
            cleanup_errors.append(f"Audio manager cleanup: {e}")
            print(f"⚠️ Audio manager cleanup error: {e}")
        
        # 3. Clean up servo controller
        try:
            print("🧹 Cleaning up servo controller...")
            self.servo_controller.cleanup()
            print("✅ Servo controller cleanup completed")
        except Exception as e:
            cleanup_errors.append(f"Servo cleanup: {e}")
            print(f"⚠️ Servo cleanup error: {e}")
        
        # 4. Clean up other components
        try:
            print("🧹 Cleaning up other components...")
            # STT and backend client don't need special cleanup
            print("✅ Other components cleanup completed")
        except Exception as e:
            cleanup_errors.append(f"Other cleanup: {e}")
            print(f"⚠️ Other cleanup error: {e}")
        
        if cleanup_errors:
            print(f"⚠️ Cleanup completed with {len(cleanup_errors)} errors:")
            for error in cleanup_errors:
                print(f"   - {error}")
        else:
            print("✅ Cleanup completed successfully")


def main():
    """Main entry point"""
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and run server
    global furby_server
    furby_server = FurbyServer()
    furby_server.run()


if __name__ == "__main__":
    main() 