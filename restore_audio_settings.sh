#!/bin/bash

# Restore WM8960 Audio HAT mixer settings
# This script configures both microphone input and speaker output

echo "🔧 Restoring WM8960 Audio HAT mixer settings..."

# MICROPHONE INPUT SETTINGS
echo "🎤 Configuring microphone inputs..."

# Enable microphone boost mixers (for microphone input)
amixer -q sset 'Left Boost Mixer LINPUT2' on
amixer -q sset 'Right Boost Mixer RINPUT2' on
amixer -q sset 'Left Boost Mixer LINPUT3' on
amixer -q sset 'Right Boost Mixer RINPUT3' on

# Set capture volume
amixer -q sset 'Capture' 62%

# SPEAKER OUTPUT SETTINGS
echo "🔊 Configuring speaker outputs..."

# Enable mono output mixers (for speaker output)
amixer -q sset 'Mono Output Mixer Left' on
amixer -q sset 'Mono Output Mixer Right' on

# Enable speaker zero-cross controls
amixer -q sset 'Speaker Playback ZC' on

# Set speaker and headphone volumes
amixer -q sset 'Speaker' 86%
amixer -q sset 'Headphone' 87%

# Set main playback volume
amixer -q sset 'Playback' 100%

# Enable PCM output routing
amixer -q sset 'Left Output Mixer PCM' on
amixer -q sset 'Right Output Mixer PCM' on

echo "✅ WM8960 mixer settings restored successfully!"
echo "🎤 Microphone inputs: LINPUT2/3 and RINPUT2/3 enabled"
echo "🔊 Speaker outputs: Mono output mixers enabled"
echo "🔧 Audio system ready for recording and playback" 