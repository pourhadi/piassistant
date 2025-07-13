#!/bin/bash

# Enterprise Voice Control - Audio Setup Script
# Sets up audio devices for optimal voice recognition and playback

echo "🔊 Enterprise Voice Control - Audio Setup"
echo "=========================================="

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    echo "⚠️  Warning: This script is designed for Raspberry Pi. Continue anyway? (y/n)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo
echo "Step 1: Updating system packages..."
sudo apt update

echo
echo "Step 2: Installing audio packages..."
sudo apt install -y alsa-utils mpg123 pulseaudio pulseaudio-utils

echo
echo "Step 3: Detecting audio devices..."
echo "Available recording devices:"
arecord -l

echo
echo "Available playback devices:"
aplay -l

echo
echo "Step 4: Testing microphone..."
echo "We'll record 3 seconds of audio and play it back."
echo "Press Enter when ready to test microphone..."
read -r

arecord -d 3 -f cd -t wav /tmp/test_mic.wav
echo "Playing back recorded audio..."
aplay /tmp/test_mic.wav
rm -f /tmp/test_mic.wav

echo
echo "Did you hear the playback clearly? (y/n)"
read -r mic_test
if [[ ! "$mic_test" =~ ^[Yy]$ ]]; then
    echo "❌ Microphone test failed. Check connections and try again."
    echo "Common solutions:"
    echo "- Ensure USB microphone is properly connected"
    echo "- Try a different USB port"
    echo "- Check microphone permissions"
    exit 1
fi

echo
echo "Step 5: Bluetooth audio setup..."
echo "Starting Bluetooth service..."
sudo systemctl enable bluetooth
sudo systemctl start bluetooth

echo
echo "Bluetooth setup instructions:"
echo "1. Put your Bluetooth speaker in pairing mode"
echo "2. Run: bluetoothctl"
echo "3. In bluetoothctl, run: scan on"
echo "4. Find your speaker's MAC address"
echo "5. Run: pair [MAC_ADDRESS]"
echo "6. Run: connect [MAC_ADDRESS]"
echo "7. Run: trust [MAC_ADDRESS]"
echo "8. Run: exit"

echo
echo "Step 6: Audio configuration..."
# Create ALSA configuration for better audio handling
cat > ~/.asoundrc << 'EOF'
pcm.!default {
    type asym
    playback.pcm "plughw:1,0"
    capture.pcm "plughw:2,0"
}

ctl.!default {
    type hw
    card 1
}
EOF

echo "Created ~/.asoundrc for optimal audio routing"

echo
echo "Step 7: PulseAudio configuration..."
# Start PulseAudio if not running
pulseaudio --start 2>/dev/null || true

echo
echo "✅ Audio setup complete!"
echo
echo "Next steps:"
echo "1. Note your microphone device index (usually 2,0 for USB mics)"
echo "2. Note your Bluetooth speaker MAC address"
echo "3. Update config.json with these values"
echo "4. Test with: python3 download_beeps.py"
echo
echo "Microphone device indices detected:"
arecord -l | grep "card" | awk '{print "  - Card " $2 " Device " $6}'

echo
echo "🎵 Ready for Enterprise computer sounds!"