#!/usr/bin/env python3
"""
Test runner for Augustan Trading Bot

This script runs all unit tests and provides coverage reports.
"""

import sys
import subprocess
import os

def run_tests():
    """Run all tests with coverage"""
    print("🧪 Running Augustan Trading Bot Tests...")
    print("=" * 50)
    
    # Check if pytest is installed
    try:
        import pytest
    except ImportError:
        print("❌ pytest not found. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pytest", "pytest-cov", "pytest-mock"])
    
    # Run tests with coverage
    test_args = [
        sys.executable, "-m", "pytest",
        "tests/",
        "-v",  # Verbose output
        "--cov=.",  # Coverage for all modules
        "--cov-report=term-missing",  # Show missing lines
        "--cov-report=html:htmlcov",  # Generate HTML report
        "--tb=short"  # Short traceback format
    ]
    
    print("Running tests...")
    result = subprocess.run(test_args)
    
    if result.returncode == 0:
        print("\n✅ All tests passed!")
        print("\n📊 Coverage report generated in htmlcov/ directory")
        print("   Open htmlcov/index.html in your browser to view detailed coverage")
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)

def run_specific_test(test_file):
    """Run a specific test file"""
    if not os.path.exists(test_file):
        print(f"❌ Test file not found: {test_file}")
        return
    
    print(f"🧪 Running specific test: {test_file}")
    print("=" * 50)
    
    test_args = [
        sys.executable, "-m", "pytest",
        test_file,
        "-v"
    ]
    
    result = subprocess.run(test_args)
    
    if result.returncode == 0:
        print("\n✅ Test passed!")
    else:
        print("\n❌ Test failed!")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Run specific test file
        test_file = sys.argv[1]
        run_specific_test(test_file)
    else:
        # Run all tests
        run_tests()
