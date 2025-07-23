#!/usr/bin/env python3
"""
Setup script for Bewital Pet Store Scraper.
Handles dependency installation and project initialization.
"""

import os
import sys
import subprocess
import platform


def run_command(command, description=""):
    """Run a shell command and handle errors."""
    print(f"Running: {description or command}")
    try:
        subprocess.run(command, shell=True, check=True)
        print("✅ Success")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        return False


def check_python_version():
    """Check if Python version is compatible."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8 or higher is required")
        print(f"Current version: {version.major}.{version.minor}.{version.micro}")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} is compatible")
    return True


def check_chrome():
    """Check if Chrome browser is installed."""
    chrome_commands = {
        'Windows': 'where chrome',
        'Darwin': 'which google-chrome || which "Google Chrome"',
        'Linux': 'which google-chrome || which chromium-browser'
    }
    
    system = platform.system()
    command = chrome_commands.get(system, 'which google-chrome')
    
    try:
        subprocess.run(command, shell=True, check=True, capture_output=True)
        print("✅ Chrome browser found")
        return True
    except subprocess.CalledProcessError:
        print("⚠️  Chrome browser not found")
        print("Please install Google Chrome for web scraping to work properly")
        return False


def setup_virtual_environment():
    """Set up Python virtual environment."""
    if os.path.exists('venv'):
        print("✅ Virtual environment already exists")
        return True
    
    print("Creating virtual environment...")
    return run_command(f"{sys.executable} -m venv venv", "Creating virtual environment")


def install_dependencies():
    """Install Python dependencies."""
    pip_command = "venv/Scripts/pip" if platform.system() == "Windows" else "venv/bin/pip"
    
    if not os.path.exists(pip_command.replace('pip', 'python')):
        print("❌ Virtual environment not found. Please run setup first.")
        return False
    
    return run_command(f"{pip_command} install -r requirements.txt", 
                      "Installing Python dependencies")


def create_directories():
    """Create necessary directories."""
    directories = ['data/raw', 'data/processed', 'logs', 'docs']
    
    for directory in directories:
        try:
            os.makedirs(directory, exist_ok=True)
            print(f"✅ Created directory: {directory}")
        except Exception as e:
            print(f"❌ Error creating directory {directory}: {e}")
            return False
    
    return True


def setup_environment_file():
    """Set up environment file if it doesn't exist."""
    if os.path.exists('.env'):
        print("✅ Environment file already exists")
        return True
    
    if os.path.exists('env.example'):
        try:
            import shutil
            shutil.copy('env.example', '.env')
            print("✅ Created .env from template")
            print("📝 Please edit .env file with your specific settings")
            return True
        except Exception as e:
            print(f"❌ Error creating .env file: {e}")
            return False
    
    print("⚠️  No env.example file found")
    return True


def test_installation():
    """Test the installation by running a basic command."""
    python_command = "venv/Scripts/python" if platform.system() == "Windows" else "venv/bin/python"
    
    print("Testing installation...")
    return run_command(f"{python_command} main.py --list", "Testing scraper list command")


def display_next_steps():
    """Display next steps after setup."""
    print("\n" + "="*60)
    print("🎉 SETUP COMPLETE!")
    print("="*60)
    
    activation_cmd = "venv\\Scripts\\activate" if platform.system() == "Windows" else "source venv/bin/activate"
    
    print("\nNext steps:")
    print(f"1. Activate virtual environment: {activation_cmd}")
    print("2. Edit config.yaml to customize settings")
    print("3. Edit .env file if you need to override settings")
    print("4. Run your first scraper: python main.py --website bozita")
    print("5. View all available commands: python main.py --help")
    
    print("\nUseful commands:")
    print("• List scrapers: python main.py --list")
    print("• Run all scrapers: python main.py")
    print("• Run with verbose output: python main.py --verbose")
    print("• Test specific scraper: python main.py --website bozita")
    
    print("\nConfiguration files:")
    print("• Main config: config.yaml")
    print("• Environment overrides: .env")
    print("• Output directory: data/raw/")
    print("• Logs directory: logs/")
    
    print("\n" + "="*60)


def main():
    """Main setup function."""
    print("🚀 Bewital Pet Store Scraper Setup")
    print("="*60)
    
    # Check prerequisites
    if not check_python_version():
        sys.exit(1)
    
    check_chrome()  # Not critical, just a warning
    
    # Setup steps
    steps = [
        ("Setting up virtual environment", setup_virtual_environment),
        ("Installing dependencies", install_dependencies),
        ("Creating directories", create_directories),
        ("Setting up environment file", setup_environment_file),
        ("Testing installation", test_installation),
    ]
    
    for description, function in steps:
        print(f"\n📋 {description}...")
        if not function():
            print(f"❌ Setup failed at: {description}")
            sys.exit(1)
    
    display_next_steps()


if __name__ == "__main__":
    main() 