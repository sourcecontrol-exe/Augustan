#!/usr/bin/env python3
"""
CLI Demo Script - Showcases the futures trading CLI functionality.
"""

import subprocess
import time
import json
from pathlib import Path


def run_command(cmd, description=""):
    """Run a CLI command and display the results."""
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print(result.stdout)
            if result.stderr:
                print(f"Warnings: {result.stderr}")
        else:
            print(f"❌ Command failed with exit code {result.returncode}")
            print(f"Error: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        print("❌ Command timed out after 60 seconds")
    except Exception as e:
        print(f"❌ Error running command: {e}")
    
    print(f"\n{'='*60}")
    return result.returncode == 0


def main():
    """Run the CLI demo."""
    print("🎯 Futures Trading CLI Demo")
    print("This demo showcases the key features of the futures trading CLI")
    print("Each command will be executed with explanations")
    
    input("\nPress Enter to start the demo...")
    
    # Demo commands in order
    demos = [
        {
            "cmd": ["python3", "cli.py", "--help"],
            "desc": "Show main CLI help and available commands"
        },
        {
            "cmd": ["python3", "cli.py", "config", "show"],
            "desc": "Show current configuration (if exists)"
        },
        {
            "cmd": ["python3", "cli.py", "volume", "--help"],
            "desc": "Show volume analysis command help"
        },
        {
            "cmd": ["python3", "cli.py", "volume", "top", "--limit", "5"],
            "desc": "Show top 5 markets by volume (from latest analysis)"
        },
        {
            "cmd": ["python3", "cli.py", "trading", "--help"],
            "desc": "Show trading analysis command help"
        },
        {
            "cmd": ["python3", "cli.py", "trading", "signals", "--limit", "3"],
            "desc": "Show latest 3 trading signals (if any exist)"
        },
        {
            "cmd": ["python3", "cli.py", "job", "--help"],
            "desc": "Show job management command help"
        },
        {
            "cmd": ["python3", "cli.py", "job", "status"],
            "desc": "Show job status and latest results"
        }
    ]
    
    successful_commands = 0
    total_commands = len(demos)
    
    for i, demo in enumerate(demos, 1):
        print(f"\n\n📋 Demo Step {i}/{total_commands}")
        input("Press Enter to continue...")
        
        success = run_command(demo["cmd"], demo["desc"])
        if success:
            successful_commands += 1
        
        time.sleep(1)  # Brief pause between commands
    
    # Summary
    print(f"\n\n🎉 Demo Complete!")
    print(f"Successfully executed {successful_commands}/{total_commands} commands")
    
    if successful_commands < total_commands:
        print(f"\n⚠️  Some commands failed. This might be because:")
        print("   • No volume analysis has been run yet")
        print("   • No trading signals have been generated yet")
        print("   • Configuration file doesn't exist")
        print("\n💡 To get full functionality, try running:")
        print("   python3 cli.py config init")
        print("   python3 cli.py volume analyze")
        print("   python3 cli.py trading analyze")
    
    print(f"\n📚 For more information:")
    print("   • Read CLI_GUIDE.md for detailed documentation")
    print("   • Use --help with any command for specific help")
    print("   • Use --verbose for debugging information")
    
    # Show example commands
    print(f"\n🔥 Try these powerful commands:")
    example_commands = [
        "python3 cli.py volume analyze",
        "python3 cli.py trading analyze --timeframe 4h",
        "python3 cli.py trading signals --type buy --min-confidence 0.7",
        "python3 cli.py dashboard --refresh 30",
        "python3 cli.py job start --schedule"
    ]
    
    for cmd in example_commands:
        print(f"   {cmd}")
    
    print(f"\n🚀 Happy trading!")


if __name__ == "__main__":
    main()
