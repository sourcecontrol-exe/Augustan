#!/bin/bash

# Test script for Augustan CLI completion
echo "🧪 Testing Augustan CLI completion..."

# Source the completion script
source completion.sh

# Test basic completion
echo "Testing 'aug' completion..."
COMP_WORDS=(aug)
COMP_CWORD=1
_aug_completion
echo "Available commands: ${COMPREPLY[@]}"

# Test volume subcommand completion
echo ""
echo "Testing 'aug volume' completion..."
COMP_WORDS=(aug volume)
COMP_CWORD=2
_aug_completion
echo "Available volume subcommands: ${COMPREPLY[@]}"

# Test symbol completion
echo ""
echo "Testing 'aug position analyze --symbol' completion..."
COMP_WORDS=(aug position analyze --symbol)
COMP_CWORD=4
_aug_completion
echo "Available symbols: ${COMPREPLY[@]}"

echo ""
echo "✅ Completion test complete!"
echo "💡 In your terminal, try:"
echo "   aug <TAB>"
echo "   aug volume <TAB>"
echo "   aug position analyze --symbol <TAB>"
