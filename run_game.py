#!/usr/bin/env python3
"""
ChronoQuest: Fractures In Time - Game Launcher
===============================================
This script automatically installs dependencies and launches the game.
Works on Windows, Mac, and Linux.

Usage: python run_game.py
"""
import subprocess
import sys
import os

def install_dependencies():
    """Install required packages if missing."""
    print("Checking dependencies...")
    try:
        import pygame
        print("  ✓ pygame is installed")
    except ImportError:
        print("  Installing pygame...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pygame"])
        print("  ✓ pygame installed successfully")

def check_assets():
    """Verify required asset files exist."""
    # Set working directory to script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    required_folders = [
        "assets",
        os.path.join("assets", "Background"),
        os.path.join("assets", "Terrain"),
        os.path.join("assets", "MainCharacters"),
        os.path.join("assets", "MainCharacters", "VirtualGuy"),
        os.path.join("assets", "Traps"),
    ]
    
    missing = []
    for folder in required_folders:
        if not os.path.exists(folder):
            missing.append(folder)
    
    if missing:
        print("\n⚠ Missing required folders:")
        for f in missing:
            print(f"    - {f}")
        print("\n  Make sure the 'assets' folder is included with the game!")
        return False
    
    print("  ✓ Asset folders found")
    return True

def main():
    print("=" * 55)
    print("   ChronoQuest: Fractures In Time")
    print("=" * 55)
    print()
    
    install_dependencies()
    
    if not check_assets():
        input("\nPress Enter to exit...")
        sys.exit(1)
    
    print("\nStarting game...")
    print("-" * 55)
    
    # Run the main game
    try:
        import main
    except Exception as e:
        print(f"\nError starting game: {e}")
        input("\nPress Enter to exit...")
        sys.exit(1)

if __name__ == "__main__":
    main()
