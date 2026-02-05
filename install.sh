#!/bin/bash

# VPS Manager Installation Script
# For Ubuntu 23.04 LTS

set -e

echo "🖥️  VPS Manager Installation"
echo "=============================="
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    echo "❌ Please do not run as root. Run as a regular user with sudo privileges."
    exit 1
fi

# Check Ubuntu version
if ! grep -q "Ubuntu" /etc/os-release; then
    echo "⚠️  Warning: This script is designed for Ubuntu. Proceed anyway? (y/n)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "📦 Installing system dependencies..."
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git

echo ""
echo "📁 Setting up application directory..."
INSTALL_DIR="/opt/vps-manager"

if [ -d "$INSTALL_DIR" ]; then
    echo "⚠️  Directory $INSTALL_DIR already exists. Remove it? (y/n)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        sudo rm -rf "$INSTALL_DIR"
    else
        echo "Installation cancelled."
        exit 1
    fi
fi

sudo mkdir -p "$INSTALL_DIR"
sudo chown "$USER:$USER" "$INSTALL_DIR"

echo ""
echo "📥 Copying files..."
cp -r ./* "$INSTALL_DIR/"
cd "$INSTALL_DIR"

echo ""
echo "🐍 Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo ""
echo "📚 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "✅ Installation complete!"
echo ""
echo "To start VPS Manager:"
echo "  cd $INSTALL_DIR"
echo "  source venv/bin/activate"
echo "  python app.py"
echo ""
echo "Then access at: http://YOUR_SERVER_IP:5000"
echo ""
echo "⚠️  SECURITY WARNING:"
echo "  - This tool has NO authentication by default"
echo "  - Configure firewall to restrict access"
echo "  - See SECURITY.md for hardening recommendations"
echo ""
