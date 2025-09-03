#!/bin/bash

# Setup script for Augustan CLI auto-completion
# This script will configure completion for both bash and zsh

echo "🔧 Setting up Augustan CLI auto-completion..."

# Detect shell
CURRENT_SHELL=$(basename "$SHELL")
echo "Detected shell: $CURRENT_SHELL"

# Create completions directory
mkdir -p ~/.zsh/completions
mkdir -p ~/.bash_completion.d

# Copy completion script
if [ "$CURRENT_SHELL" = "zsh" ]; then
    echo "📁 Installing zsh completion..."
    cp _aug ~/.zsh/completions/
    
    # Add to .zshrc if not already present
    if ! grep -q "fpath=(~/.zsh/completions" ~/.zshrc; then
        echo "fpath=(~/.zsh/completions \$fpath)" >> ~/.zshrc
        echo "autoload -U compinit && compinit" >> ~/.zshrc
        echo "✅ Added completion setup to ~/.zshrc"
    else
        echo "✅ Completion setup already in ~/.zshrc"
    fi
    
elif [ "$CURRENT_SHELL" = "bash" ]; then
    echo "📁 Installing bash completion..."
    cp completion.sh ~/.bash_completion.d/aug_completion.sh
    
    # Add to .bashrc if not already present
    if ! grep -q "source.*aug_completion" ~/.bashrc; then
        echo "source ~/.bash_completion.d/aug_completion.sh" >> ~/.bashrc
        echo "✅ Added completion setup to ~/.bashrc"
    else
        echo "✅ Completion setup already in ~/.bashrc"
    fi
else
    echo "⚠️  Unknown shell: $CURRENT_SHELL"
    echo "📁 Installing both bash and zsh completions..."
    cp _aug ~/.zsh/completions/
    cp completion.sh ~/.bash_completion.d/aug_completion.sh
fi

echo ""
echo "🎉 Auto-completion setup complete!"
echo ""
echo "💡 To test completion:"
echo "   1. Open a new terminal window"
echo "   2. Type: aug <TAB>"
echo "   3. You should see available commands"
echo ""
echo "🔧 Manual setup (if needed):"
echo "   For zsh: source ~/.zsh/completions/_aug"
echo "   For bash: source ~/.bash_completion.d/aug_completion.sh"
echo ""
echo "📚 Available completions:"
echo "   aug <TAB>                    # Show main commands"
echo "   aug volume <TAB>             # Show volume subcommands"
echo "   aug position analyze --symbol <TAB>  # Show trading symbols"
echo "   aug trading analyze --timeframe <TAB> # Show timeframes"
