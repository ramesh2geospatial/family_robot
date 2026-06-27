#!/usr/bin/env bash
# Raspberry Pi 5 installation script for FamilyRobot.
# Run as root or with sudo.

set -e

echo "=== FamilyRobot Raspberry Pi 5 Setup Script ==="

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root or with sudo."
  exit 1
fi

TARGET_USER=${SUDO_USER:-$USER}

echo "1. Installing system dependencies..."
apt-get update
apt-get install -y \
  python3-pip \
  python3-venv \
  python3-lgpio \
  python3-smbus \
  libcamera-dev \
  portaudio19-dev \
  pulseaudio \
  alsa-utils \
  i2c-tools \
  git \
  mpv \
  espeak-ng

echo "2. Adding user '$TARGET_USER' to hardware access groups..."
usermod -a -G gpio,i2c,audio,video "$TARGET_USER"

echo "3. Creating Python virtual environment..."
PROJECT_DIR="/home/$TARGET_USER/family_robots"
if [ ! -d "$PROJECT_DIR" ]; then
  PROJECT_DIR=$(pwd)
  echo "Using current directory: $PROJECT_DIR"
fi

if [ ! -d "$PROJECT_DIR/venv" ]; then
  sudo -u "$TARGET_USER" python3 -m venv "$PROJECT_DIR/venv"
fi

echo "4. Installing Python dependencies..."
sudo -u "$TARGET_USER" "$PROJECT_DIR/venv/bin/pip" install --upgrade pip
sudo -u "$TARGET_USER" "$PROJECT_DIR/venv/bin/pip" install -r "$PROJECT_DIR/requirements.txt"

# Install smbus2 for I2C battery telemetry
sudo -u "$TARGET_USER" "$PROJECT_DIR/venv/bin/pip" install smbus2

echo "5. Installing and enabling systemd service..."
SERVICE_FILE="$PROJECT_DIR/deploy/raspberrypi/familyrobot.service"
if [ -f "$SERVICE_FILE" ]; then
  # Adjust Username in systemd service if it differs from default 'pi'
  sed -i "s/User=pi/User=$TARGET_USER/g" "$SERVICE_FILE"
  sed -i "s|/home/pi/family_robots|$PROJECT_DIR|g" "$SERVICE_FILE"
  
  cp "$SERVICE_FILE" /etc/systemd/system/familyrobot.service
  systemctl daemon-reload
  systemctl enable familyrobot.service
  echo "Systemd service registered and enabled."
else
  echo "Warning: familyrobot.service file not found at $SERVICE_FILE. Skipping systemd service registration."
fi

echo "=== Setup complete! Please restart your Raspberry Pi to apply group and hardware overrides. ==="
echo "You can check status using: systemctl status familyrobot"
