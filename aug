#!/usr/bin/env python3
"""
Augustan Trading System CLI
After installation with 'pip install -e .', you can use 'aug' directly from anywhere.
"""
import sys
import subprocess

def main():
    """Run the augustan CLI."""
    try:
        # Try to run the installed version first
        subprocess.run([sys.executable, "-m", "trading_system.cli"] + sys.argv[1:])
    except FileNotFoundError:
        # Fallback to direct import if in development
        try:
            from trading_system.cli import cli
            cli()
        except ImportError:
            print("❌ Augustan not installed. Run: pip install -e .")
            sys.exit(1)

if __name__ == '__main__':
    main()