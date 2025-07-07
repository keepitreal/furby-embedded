#!/bin/bash

# Debug script to capture mixer settings before and after running the server
# This will help us identify what settings are getting changed

BEFORE_FILE="/tmp/mixer_before.txt"
AFTER_FILE="/tmp/mixer_after.txt"

case "$1" in
    "before")
        echo "📸 Capturing mixer settings BEFORE running server..."
        amixer scontents > "$BEFORE_FILE"
        echo "✅ Settings saved to $BEFORE_FILE"
        echo "Now run: python3 furby_server.py"
        echo "Then stop it with Ctrl+C"
        echo "Then run: $0 after"
        ;;
    "after")
        echo "📸 Capturing mixer settings AFTER running server..."
        amixer scontents > "$AFTER_FILE"
        echo "✅ Settings saved to $AFTER_FILE"
        echo ""
        echo "🔍 Comparing mixer settings (showing differences):"
        echo "Legend: < = BEFORE (working), > = AFTER (broken)"
        echo "----------------------------------------"
        diff "$BEFORE_FILE" "$AFTER_FILE" | head -50
        echo "----------------------------------------"
        echo ""
        echo "🔧 Full mixer state after server:"
        echo "Key output mixer settings:"
        amixer sget 'Mono Output Mixer Left'
        amixer sget 'Mono Output Mixer Right'
        amixer sget 'Left Output Mixer PCM'
        amixer sget 'Right Output Mixer PCM'
        amixer sget 'Speaker Playback ZC'
        ;;
    *)
        echo "Usage: $0 {before|after}"
        echo ""
        echo "Steps:"
        echo "1. Run: $0 before"
        echo "2. Run: python3 furby_server.py (then stop with Ctrl+C)"
        echo "3. Run: $0 after"
        echo ""
        echo "This will show you exactly what mixer settings change."
        ;;
esac 