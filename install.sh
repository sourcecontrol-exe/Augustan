#!/bin/bash

# Augustan Trading System Installation Script
echo "🚀 Installing Augustan Trading System..."

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 3.8+ required. Found: $python_version"
    exit 1
fi

echo "✅ Python version check passed: $python_version"

# Install package
echo "📦 Installing Augustan package..."
if python3 -m pip install -e . --user; then
    echo "✅ Package installed successfully!"
else
    echo "⚠️  Package installation failed. Trying alternative method..."
    # Fallback: just make the local command executable
    chmod +x aug
    echo "✅ Local 'aug' command is ready to use"
fi

# Test installation
echo "🧪 Testing installation..."
if python3 -m trading_system --version >/dev/null 2>&1; then
    echo "✅ Installation test passed!"
    echo ""
    echo "🎉 Augustan Trading System is ready!"
    echo ""
    echo "📚 Quick start:"
    echo "   python3 -m trading_system --help"
    echo "   python3 -m trading_system position analyze --symbol DOGE/USDT --budget 50"
    echo "   python3 -m trading_system position tradeable --budget 50"
    echo ""
    echo "💡 Or use the local command:"
    echo "   ./aug --help"
    echo "   ./aug position analyze --symbol DOGE/USDT --budget 50"
else
    echo "⚠️  Package installation not working, but local command available:"
    echo "   ./aug --help"
    echo "   ./aug position analyze --symbol DOGE/USDT --budget 50"
fi

echo ""
echo "🎯 Ready to start trading smarter with Augustan!"
