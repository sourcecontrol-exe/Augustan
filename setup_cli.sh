#!/bin/bash
"""
Setup script for Futures Trading CLI
"""

echo "🚀 Setting up Futures Trading CLI..."

# Check Python version
python3 --version
if [ $? -ne 0 ]; then
    echo "❌ Python 3 is required but not found"
    exit 1
fi

echo "✅ Python 3 found"

# Install dependencies
echo "📦 Installing dependencies..."
python3 -m pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    exit 1
fi

echo "✅ Dependencies installed"

# Make scripts executable
echo "🔧 Making scripts executable..."
chmod +x futures-cli
chmod +x demo_cli.py

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p config volume_data logs

# Initialize configuration
echo "⚙️ Initializing configuration..."
python3 cli.py config init --force

if [ $? -ne 0 ]; then
    echo "❌ Failed to initialize configuration"
    exit 1
fi

echo "✅ Configuration initialized"

# Test CLI
echo "🧪 Testing CLI..."
python3 cli.py --version

if [ $? -ne 0 ]; then
    echo "❌ CLI test failed"
    exit 1
fi

echo "✅ CLI test passed"

echo ""
echo "🎉 Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Edit config/exchanges_config.json to add your API keys"
echo "2. Run: python3 cli.py volume analyze"
echo "3. Run: python3 cli.py trading analyze"
echo "4. Try: python3 demo_cli.py for a demo"
echo ""
echo "📚 Documentation:"
echo "• CLI_GUIDE.md - Complete CLI documentation"
echo "• README_FUTURES.md - System overview"
echo ""
echo "🚀 Happy trading!"
