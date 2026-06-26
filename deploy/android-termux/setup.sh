#!/usr/bin/env bash
# FamilyRobot Android Termux Setup Script
# Installs and configures system dependencies, audio backends, and virtualenv inside Termux.

set -e

echo "=== FamilyRobot Android Termux Setup ==="
echo "Make sure you have: "
echo "  1. Installed Termux app (F-Droid version recommended)"
echo "  2. Installed Termux:API app from the same source"
echo "  3. Granted Camera & Microphone permissions to Termux:API in Android settings"
echo ""

# 1. Update packages
echo "--> Updating Termux packages..."
pkg update -y && pkg upgrade -y

# 2. Install required system packages
echo "--> Installing system packages..."
pkg install -y \
    termux-api \
    pulseaudio \
    portaudio \
    clang \
    make \
    pkg-config \
    python \
    libjpeg-turbo \
    ffmpeg

# 3. Setup PulseAudio config for real-time audio
echo "--> Configuring PulseAudio..."
mkdir -p ~/.config/pulse
if [ ! -f ~/.config/pulse/default.pa ]; then
    echo "load-module module-native-protocol-tcp auth-ip-acl=127.0.0.1" > ~/.config/pulse/default.pa
    echo "load-module module-sles-source" >> ~/.config/pulse/default.pa
    echo "load-module module-sles-sink" >> ~/.config/pulse/default.pa
fi

# Ensure PulseAudio autostarts when starting a terminal session
if ! grep -q "pulseaudio --start" ~/.bashrc; then
    echo "echo 'Starting PulseAudio server...'" >> ~/.bashrc
    echo "pulseaudio --start --exit-idle-time=-1 2>/dev/null" >> ~/.bashrc
    echo "pactl load-module module-sles-source 2>/dev/null || true" >> ~/.bashrc
fi

# Start PulseAudio for this setup run
pulseaudio --start --exit-idle-time=-1 2>/dev/null || true
pactl load-module module-sles-source 2>/dev/null || true

# 4. Check Termux API permissions & functionality
echo "--> Checking Termux:API functionality..."
if command -v termux-battery-status &>/dev/null; then
    if termux-battery-status &>/dev/null; then
        echo " [+] Termux:API is working and permissions are granted."
    else
        echo " [!] Termux:API command failed. Ensure the Termux:API app is installed and permissions are granted."
    fi
else
    echo " [!] termux-api CLI not found. Please ensure pkg install termux-api succeeded."
fi

# 5. Virtual Environment & Python dependencies
echo "--> Setting up Python Virtual Environment..."
if [ ! -d "venv" ]; then
    python -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip

echo "--> Installing FamilyRobot package and dependencies..."
# Install with android extra dependencies (if specified) or base
pip install -e .

echo ""
echo "=== Setup Complete ==="
echo "To run the robot on Android, execute:"
echo "  source venv/bin/activate"
echo "  python -m apps.familyrobot --platform android"
echo ""
