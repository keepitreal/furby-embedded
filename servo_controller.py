#!/usr/bin/env python3
"""
Servo Control for Furby - Mouth Movement Animation
"""

import time
from typing import Optional, List, Dict

# Optional import
try:
    import pigpio
    PIGPIO_AVAILABLE = True
except ImportError:
    print("⚠️ pigpio not available - using mock servo control")
    PIGPIO_AVAILABLE = False


class ServoController:
    """Servo motor control for mouth movement"""
    
    def __init__(self, config):
        self.config = config
        self.pi = None
        self.is_active = False
        self.current_position = config.SERVO_CLOSED_POSITION
        
        if PIGPIO_AVAILABLE:
            try:
                self.pi = pigpio.pi()
                if self.pi.connected:
                    self.is_active = True
                    self.pi.set_servo_pulsewidth(config.SERVO_PIN, 0)  # Stop servo initially
                    print("✅ Servo controller initialized")
                else:
                    print("⚠️ pigpio daemon not running - using mock servo")
            except Exception as e:
                print(f"⚠️ Servo initialization failed: {e} - using mock servo")
        else:
            print("⚠️ pigpio not available - using mock servo")
    
    def move_to_position(self, position: int):
        """Move servo to specific position (0-180 degrees)"""
        position = max(0, min(180, position))  # Clamp to valid range
        
        if self.is_active and self.pi:
            # Convert position to pulse width
            pulse_width = self.config.SERVO_MIN_PULSE + (
                (position / 180.0) * (self.config.SERVO_MAX_PULSE - self.config.SERVO_MIN_PULSE)
            )
            self.pi.set_servo_pulsewidth(self.config.SERVO_PIN, pulse_width)
            print(f"🦾 Servo moved to {position}°")
        else:
            print(f"🎭 [MOCK] Servo would move to {position}°")
        
        self.current_position = position
    
    def animate_mouth(self, phonemes: Optional[List[Dict]] = None):
        """Animate mouth based on phoneme data or default animation"""
        if phonemes:
            print("🎭 Starting phoneme-based mouth animation")
            for phoneme in phonemes:
                position = self.phoneme_to_position(phoneme.get('phoneme', ''))
                duration = phoneme.get('duration', 0.1)
                self.move_to_position(position)
                time.sleep(duration)
        else:
            print("🎭 Starting default mouth animation")
            # Default talking animation
            positions = [45, 90, 60, 80, 50, 70, 90]  
            for position in positions:
                self.move_to_position(position)
                time.sleep(0.2)
        
        # Return to closed position
        self.move_to_position(self.config.SERVO_CLOSED_POSITION)
    
    def phoneme_to_position(self, phoneme: str) -> int:
        """Convert phoneme to servo position"""
        phoneme_map = {
            'AA': 70, 'AE': 65, 'AH': 60, 'AO': 75, 'AW': 80, 'AY': 70,
            'EH': 55, 'ER': 60, 'EY': 50, 'IH': 45, 'IY': 40, 'OW': 85,
            'OY': 80, 'UH': 70, 'UW': 90, 'B': 90, 'CH': 60, 'D': 50,
            'DH': 45, 'F': 75, 'G': 70, 'HH': 55, 'JH': 65, 'K': 80,
            'L': 50, 'M': 90, 'N': 55, 'NG': 60, 'P': 90, 'R': 65,
            'S': 45, 'SH': 55, 'T': 50, 'TH': 45, 'V': 70, 'W': 85,
            'Y': 50, 'Z': 50, 'ZH': 60
        }
        return phoneme_map.get(phoneme.upper(), self.config.SERVO_CLOSED_POSITION)
    
    def express_emotion(self, emotion: str):
        """Express emotion through servo movement"""
        emotions = {
            'happy': [30, 60, 40, 70, 45],
            'sad': [90, 75, 85, 70, 90],
            'excited': [20, 80, 30, 90, 25, 85],
            'sleepy': [85, 90, 88, 92, 90]
        }
        
        positions = emotions.get(emotion, [90, 60, 90])
        print(f"😊 Expressing emotion: {emotion}")
        
        for position in positions:
            self.move_to_position(position)
            time.sleep(0.3)
        
        self.move_to_position(self.config.SERVO_CLOSED_POSITION)
    
    def cleanup(self):
        """Cleanup servo resources"""
        if self.is_active and self.pi:
            self.pi.set_servo_pulsewidth(self.config.SERVO_PIN, 0)  # Stop servo
            self.pi.stop() 