#!/bin/bash

# Restore WM8960 Audio HAT mixer settings
# This script configures both microphone input and speaker output

echo "🔧 Restoring WM8960 Audio HAT mixer settings..."

# CRITICAL: Save current device state for debugging
echo "📋 Current mixer state check:"
echo "  Mono Output Mixer Left: $(amixer sget 'Mono Output Mixer Left' | grep -o '\[on\]\|\[off\]' | head -1)"
echo "  Mono Output Mixer Right: $(amixer sget 'Mono Output Mixer Right' | grep -o '\[on\]\|\[off\]' | head -1)"

# MICROPHONE INPUT SETTINGS
echo "🎤 Configuring microphone inputs..."

# Enable microphone boost mixers (for microphone input)
amixer -q sset 'Left Boost Mixer LINPUT1' on
amixer -q sset 'Right Boost Mixer RINPUT1' on
amixer -q sset 'Left Boost Mixer LINPUT2' on
amixer -q sset 'Right Boost Mixer RINPUT2' on
amixer -q sset 'Left Boost Mixer LINPUT3' on
amixer -q sset 'Right Boost Mixer RINPUT3' on

# Set capture volume and enable
amixer -q sset 'Capture' 62% on

# Additional input mixer settings
amixer -q sset 'Left Input Mixer Boost' on 2>/dev/null || true
amixer -q sset 'Right Input Mixer Boost' on 2>/dev/null || true

# SPEAKER OUTPUT SETTINGS
echo "🔊 Configuring speaker outputs..."

# Enable mono output mixers (CRITICAL for speaker output)
amixer -q sset 'Mono Output Mixer Left' on
amixer -q sset 'Mono Output Mixer Right' on

# Enable speaker zero-cross controls
amixer -q sset 'Speaker Playback ZC' on

# Set speaker and headphone volumes
amixer -q sset 'Speaker' 86%
amixer -q sset 'Headphone' 87%

# Set main playback volume
amixer -q sset 'Playback' 100%

# Enable PCM output routing (CRITICAL)
amixer -q sset 'Left Output Mixer PCM' on
amixer -q sset 'Right Output Mixer PCM' on

# Additional output mixer settings
amixer -q sset 'Left Output Mixer Boost Bypass' on 2>/dev/null || true
amixer -q sset 'Right Output Mixer Boost Bypass' on 2>/dev/null || true

# Speaker AC/DC settings
amixer -q sset 'Speaker AC' 80% 2>/dev/null || true
amixer -q sset 'Speaker DC' 80% 2>/dev/null || true

# Make sure headphone ZC is also enabled
amixer -q sset 'Headphone Playback ZC' on 2>/dev/null || true

echo "✅ WM8960 mixer settings restored!"

# VERIFICATION
echo "🔍 Verification:"
echo "  Mono Output Mixer Left: $(amixer sget 'Mono Output Mixer Left' | grep -o '\[on\]\|\[off\]' | head -1)"
echo "  Mono Output Mixer Right: $(amixer sget 'Mono Output Mixer Right' | grep -o '\[on\]\|\[off\]' | head -1)"
echo "  Left Output Mixer PCM: $(amixer sget 'Left Output Mixer PCM' | grep -o '\[on\]\|\[off\]' | head -1)"
echo "  Right Output Mixer PCM: $(amixer sget 'Right Output Mixer PCM' | grep -o '\[on\]\|\[off\]' | head -1)"
echo "  Speaker Playback ZC: $(amixer sget 'Speaker Playback ZC' | grep -o '\[on\]\|\[off\]' | head -1)"

echo "🎤 Microphone inputs: All LINPUT/RINPUT enabled"
echo "🔊 Speaker outputs: Mono output mixers enabled"
echo "🔧 Audio system ready for recording and playback"

# Test if settings took effect
echo "🧪 Quick test - try: aplay -D hw:0,0 ../WM8960_Audio_HAT_Code/music_48k.wav" 