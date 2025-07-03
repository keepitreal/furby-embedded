#!/usr/bin/env python3
"""
Vosk Speech-to-Text Engine for Furby
"""

import json
import os
import wave
from typing import Optional

# Optional import
try:
    import vosk
    VOSK_AVAILABLE = True
except ImportError:
    print("⚠️ Vosk not available - STT disabled")
    VOSK_AVAILABLE = False


class VoskSTTEngine:
    """Vosk speech-to-text engine"""
    
    def __init__(self, config):
        self.config = config
        self.model = None
        self.recognizer = None
        self.is_available = False
        
        if VOSK_AVAILABLE:
            self.setup_vosk()
    
    def setup_vosk(self):
        """Initialize Vosk model"""
        if not os.path.exists(self.config.VOSK_MODEL_PATH):
            print(f"❌ Vosk model not found: {self.config.VOSK_MODEL_PATH}")
            return
        
        try:
            print(f"🔍 Loading Vosk model: {self.config.VOSK_MODEL_PATH}")
            self.model = vosk.Model(self.config.VOSK_MODEL_PATH)
            self.recognizer = vosk.KaldiRecognizer(self.model, self.config.SAMPLE_RATE)
            self.recognizer.SetWords(True)
            self.is_available = True
            print("✅ Vosk STT engine ready")
        except Exception as e:
            print(f"❌ Failed to load Vosk model: {e}")
    
    def transcribe_audio_file(self, audio_file: str) -> Optional[str]:
        """Transcribe audio file to text"""
        if not self.is_available or not self.recognizer:
            print("⚠️ Vosk not available")
            return None
        
        try:
            print(f"🎙️ Transcribing: {audio_file}")
            
            with wave.open(audio_file, 'rb') as wav_file:
                if wav_file.getnchannels() != 1 or wav_file.getsampwidth() != 2 or wav_file.getframerate() != self.config.SAMPLE_RATE:
                    print("⚠️ Audio format mismatch, results may be poor")
                
                results = []
                while True:
                    data = wav_file.readframes(self.config.FRAME_SIZE)
                    if len(data) == 0:
                        break
                    
                    if self.recognizer.AcceptWaveform(data):
                        result = json.loads(self.recognizer.Result())
                        if result.get('text'):
                            results.append(result['text'])
                
                # Get final result
                final_result = json.loads(self.recognizer.FinalResult())
                if final_result.get('text'):
                    results.append(final_result['text'])
                
                # Combine all results
                full_text = ' '.join(results).strip()
                print(f"📝 Transcription: '{full_text}'")
                return full_text if full_text else None
                
        except Exception as e:
            print(f"❌ Transcription failed: {e}")
            return None 