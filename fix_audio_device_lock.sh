#!/bin/bash

# Fix audio device locks and reset ALSA system
# This addresses PyAudio device locks and ALSA state issues

echo "🔧 Fixing audio device locks..."

# Step 1: Kill any processes that might be holding the audio device
echo "🔪 Killing audio processes..."
sudo pkill -f "python.*furby_server" 2>/dev/null || true
sudo pkill -f "python.*wake_word" 2>/dev/null || true
sudo pkill -f "python.*test_" 2>/dev/null || true

# Step 2: Release any ALSA locks
echo "🔓 Releasing ALSA locks..."
sudo fuser -k /dev/snd/* 2>/dev/null || true

# Step 3: Reset ALSA system
echo "🔄 Resetting ALSA system..."
sudo alsactl store
sudo alsactl restore

# Step 4: Reset the audio device at kernel level
echo "⚡ Resetting audio device..."
echo "  Current audio card status:"
cat /proc/asound/cards

# Force reload the audio drivers
sudo modprobe -r snd_soc_wm8960 2>/dev/null || true
sudo modprobe -r snd_soc_simple_card 2>/dev/null || true
sleep 2
sudo modprobe snd_soc_simple_card
sudo modprobe snd_soc_wm8960
sleep 3

echo "  Audio card status after reset:"
cat /proc/asound/cards

# Step 5: Check if device is accessible
echo "🧪 Testing device accessibility..."
if aplay -D hw:0,0 -f S16_LE -c 2 -r 48000 /dev/zero -d 0.1 2>/dev/null; then
    echo "✅ Audio device is accessible"
else
    echo "❌ Audio device is NOT accessible"
    echo "   Checking device status..."
    ls -la /dev/snd/
    echo "   Checking permissions..."
    groups $USER
fi

# Step 6: Test actual playback
echo "🎵 Testing playback..."
if [ -f "../WM8960_Audio_HAT_Code/music_48k.wav" ]; then
    echo "Playing test file for 2 seconds..."
    timeout 2 aplay -D hw:0,0 ../WM8960_Audio_HAT_Code/music_48k.wav 2>/dev/null && echo "✅ Playback working!" || echo "❌ Playback failed!"
else
    echo "⚠️ Test file not found, skipping playback test"
fi

echo "🏁 Audio fix complete. Try: aplay -D hw:0,0 ../WM8960_Audio_HAT_Code/music_48k.wav" 