#!/bin/bash

echo "🎤 Setting up Vosk Wake Word Detection for Furby"
echo "================================================"

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3."
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"

# Install Python dependencies
echo "📦 Installing Python dependencies..."
if command -v pip3 &> /dev/null; then
    pip3 install -r requirements.txt
elif command -v pip &> /dev/null; then
    pip install -r requirements.txt
else
    echo "❌ pip not found. Please install pip."
    exit 1
fi

# Create models directory
mkdir -p models

# Download Vosk model if not exists
MODEL_DIR="models/vosk-model-small-en-us-0.15"
if [ ! -d "$MODEL_DIR" ]; then
    echo "⬇️ Downloading Vosk model (this may take a few minutes)..."
    
    # Download model
    cd models
    if command -v wget &> /dev/null; then
        wget -q --show-progress https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
    elif command -v curl &> /dev/null; then
        echo "Using curl to download..."
        curl -L -o vosk-model-small-en-us-0.15.zip https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
    else
        echo "❌ Neither wget nor curl found. Please install one of them."
        exit 1
    fi
    
    if [ $? -eq 0 ]; then
        echo "📦 Extracting model..."
        unzip -q vosk-model-small-en-us-0.15.zip
        rm vosk-model-small-en-us-0.15.zip
        echo "✅ Vosk model installed successfully"
    else
        echo "❌ Failed to download model. Please check your internet connection."
        exit 1
    fi
    
    cd ..
else
    echo "✅ Vosk model already exists"
fi

# Make Python script executable
chmod +x wake_word_service.py

echo ""
echo "🎉 Setup complete!"
echo ""
echo "📋 Usage:"
echo "  1. Start Node.js server:    npm start"
echo "  2. Start wake word service: python3 wake_word_service.py"
echo "  3. Say 'furby' or 'hey furby' to test!"
echo ""
echo "🔧 Wake words: furby, hey furby, furby wake up"
echo "🎯 You can modify wake words in wake_word_service.py" 