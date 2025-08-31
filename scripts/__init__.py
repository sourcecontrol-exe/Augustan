"""
Scripts Module

Entry point scripts for various Augustan operations.
"""

# Import main entry points
from .augustan_cli import main as cli_main
from .cli_demos import main as demo_main

__all__ = ['cli_main', 'demo_main']
