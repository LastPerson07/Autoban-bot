#!/bin/bash
# setup.sh - Easy setup script for Guardian Bot
# Run this once: chmod +x setup.sh && ./setup.sh

set -e  # Exit on any error

echo "🛡️ Guardian Bot Setup Script"
echo "=============================="

# Check for Python 3.10+
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Install Python 3.10+ first."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')
echo "✅ Found Python $PYTHON_VERSION"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install requirements
if [ ! -f "requirements.txt" ]; then
    echo "❌ requirements.txt not found! Make sure it's in the project root."
    exit 1
fi

echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Create .env if not exists
if [ ! -f ".env" ]; then
    echo "🔑 Creating .env file with your credentials..."
    echo ""
    read -p "Enter your API_ID: " API_ID
    read -p "Enter your API_HASH: " API_HASH
    read -p "Enter your BOT_TOKEN: " BOT_TOKEN
    read -p "Enter your MONGO_URI (MongoDB connection string): " MONGO_URI
    read -p "Enter your BOT_OWNER_ID (your Telegram user ID): " BOT_OWNER_ID
    read -p "Enter INTRO_PHOTO URL (optional, press Enter to skip): " INTRO_PHOTO
    read -p "Enter WELCOME_STICKER file_id (optional, press Enter to skip): " WELCOME_STICKER

    cat > .env << EOL
API_ID=$API_ID
API_HASH=$API_HASH
BOT_TOKEN=$BOT_TOKEN
MONGO_URI=$MONGO_URI
BOT_OWNER_ID=$BOT_OWNER_ID
INTRO_PHOTO=${INTRO_PHOTO:-https://example.com/shield.jpg}
WELCOME_STICKER=${WELCOME_STICKER}
EOL

    echo "✅ .env file created!"
else
    echo "✅ .env already exists – skipping."
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "To run the bot:"
echo "   source venv/bin/activate   # (if not already active)"
echo "   python bot.py"
echo ""
echo "Alternative: Use Docker (recommended for production)"
echo "   docker build -t guardian-bot ."
echo "   docker run -d --env-file .env guardian-bot"
echo ""
echo "Or with docker-compose (includes local MongoDB):"
echo "   docker-compose up -d"
echo ""
echo "Happy guarding! 🛡️"