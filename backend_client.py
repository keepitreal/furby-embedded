#!/usr/bin/env python3
"""
Backend API Client for Furby - Communication with backend services
"""

import time
import requests
from typing import Dict, Any


class BackendClient:
    """Backend API communication"""
    
    def __init__(self, config):
        self.config = config
        self.session = requests.Session()
    
    def health_check(self) -> bool:
        """Check backend health"""
        try:
            response = self.session.get(f"{self.config.BACKEND_URL}/health", timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Backend health check failed: {e}")
            return False
    
    def send_text_for_response(self, text: str, max_retries: int = 3) -> Dict[str, Any]:
        """Send text to backend and get response"""
        for attempt in range(max_retries):
            try:
                print(f"🌐 Sending to backend (attempt {attempt + 1}/{max_retries}): '{text}'")
                
                response = self.session.post(
                    f"{self.config.BACKEND_URL}/api/chat",
                    json={'text': text},
                    headers={'Content-Type': 'application/json'},
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    print("✅ Backend response received")
                    print(f"🔍 Response keys: {list(data.keys())}")
                    print(f"🔍 Has audio: {'audioBase64' in data and data['audioBase64'] is not None}")
                    print(f"🔍 Has phonemes: {'phonemes' in data and len(data.get('phonemes', [])) > 0}")
                    return {
                        'audio': data.get('audioBase64'),  # Backend sends audioBase64, not audio
                        'phonemes': data.get('phonemes', []),
                        'text': data.get('text', ''),
                        'isFallback': False
                    }
                else:
                    try:
                        error_detail = response.text
                        print(f"❌ Backend error: {response.status_code} - {error_detail}")
                    except:
                        print(f"❌ Backend error: {response.status_code}")
                    
            except Exception as e:
                print(f"⚠️ Backend request failed (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(1 * (attempt + 1))  # Exponential backoff
        
        # Fallback response
        print("🔄 Using fallback response")
        return {
            'audio': None,
            'phonemes': [],
            'text': "I'm having trouble connecting right now, but I'm listening!",
            'isFallback': True
        } 