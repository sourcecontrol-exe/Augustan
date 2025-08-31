#!/usr/bin/env python3
"""
Augustan Test Runner

Run comprehensive test suite for Augustan trading bot.
"""

import sys
import os
import unittest
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_tests():
    """Run all tests"""
    try:
        # Discover and run tests
        test_dir = project_root / 'tests'
        if not test_dir.exists():
            logger.warning("No tests directory found")
            return
        
        loader = unittest.TestLoader()
        suite = loader.discover(str(test_dir), pattern='test_*.py')
        
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        if result.wasSuccessful():
            logger.info("All tests passed!")
            return 0
        else:
            logger.error(f"Tests failed: {len(result.failures)} failures, {len(result.errors)} errors")
            return 1
            
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        return 1

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Augustan Test Runner")
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    exit_code = run_tests()
    sys.exit(exit_code)

if __name__ == '__main__':
    main()
