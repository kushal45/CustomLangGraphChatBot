#!/usr/bin/env python3
"""
Verify Python setup for debugging.
Run this script to check if your Python environment is correctly configured.
"""

import sys
import subprocess
import os

def main():
    print("🔍 Python Environment Verification")
    print("=" * 50)
    
    # Check Python version and path
    print(f"✅ Python Version: {sys.version}")
    print(f"✅ Python Executable: {sys.executable}")
    print(f"✅ Python Path: {sys.path[0]}")
    
    # Check if pytest is available
    try:
        import pytest
        print(f"✅ Pytest Version: {pytest.__version__}")
        print(f"✅ Pytest Location: {pytest.__file__}")
    except ImportError:
        print("❌ Pytest NOT FOUND - Install with: pip3 install pytest")
        return False
    
    # Check if our project modules can be imported
    try:
        from tools.communication_tools import SlackNotificationTool
        print("✅ Project modules can be imported")
    except ImportError as e:
        print(f"❌ Project import failed: {e}")
        print("💡 Make sure PYTHONPATH includes the project directory")
    
    # Check environment variables
    pythonpath = os.environ.get('PYTHONPATH', 'Not set')
    print(f"📁 PYTHONPATH: {pythonpath}")
    
    # Test pytest command
    try:
        result = subprocess.run([sys.executable, '-m', 'pytest', '--version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ Pytest command works")
            print(f"   Output: {result.stdout.strip()}")
        else:
            print(f"❌ Pytest command failed: {result.stderr}")
    except Exception as e:
        print(f"❌ Pytest command error: {e}")
    
    print("\n🎯 Debugging Recommendations:")
    print("1. In VSCode, press Cmd+Shift+P")
    print("2. Type 'Python: Select Interpreter'")
    print(f"3. Choose: {sys.executable}")
    print("4. Restart VSCode if needed")
    
    return True

if __name__ == "__main__":
    main()
