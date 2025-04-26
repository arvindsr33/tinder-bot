#!/usr/bin/env python3
"""
Simple entry point for running the Tinder Bot.
"""

import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import and run the CLI
from tinder_bot.cli import app

if __name__ == "__main__":
    app() 