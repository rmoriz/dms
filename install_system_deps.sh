#!/bin/bash

# DMS System Dependencies Installation Script
# This script installs Tesseract OCR and language packs required by DMS

set -e  # Exit on any error

echo "🔧 DMS System Dependencies Installation"
echo "======================================"

# Detect operating system
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    OS="windows"
else
    echo "❌ Unsupported operating system: $OSTYPE"
    exit 1
fi

echo "🖥️  Detected OS: $OS"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to install on macOS
install_macos() {
    echo "🍎 Installing dependencies for macOS..."
    
    # Check if Homebrew is installed
    if ! command_exists brew; then
        echo "❌ Homebrew not found. Please install Homebrew first:"
        echo "   /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        exit 1
    fi
    
    echo "📦 Updating Homebrew..."
    brew update
    
    echo "🔤 Installing Tesseract OCR..."
    if brew list tesseract &>/dev/null; then
        echo "✅ Tesseract already installed"
    else
        brew install tesseract
    fi
    
    echo "🌍 Installing language packs..."
    if brew list tesseract-lang &>/dev/null; then
        echo "✅ Language packs already installed"
    else
        brew install tesseract-lang
    fi
}

# Function to install on Linux
install_linux() {
    echo "🐧 Installing dependencies for Linux..."
    
    # Detect Linux distribution
    if command_exists apt-get; then
        DISTRO="debian"
    elif command_exists yum; then
        DISTRO="rhel"
    elif command_exists pacman; then
        DISTRO="arch"
    else
        echo "❌ Unsupported Linux distribution"
        exit 1
    fi
    
    echo "📦 Detected distribution: $DISTRO"
    
    case $DISTRO in
        "debian")
            echo "📦 Updating package list..."
            sudo apt-get update
            
            echo "🔤 Installing Tesseract OCR..."
            sudo apt-get install -y tesseract-ocr
            
            echo "🌍 Installing language packs..."
            sudo apt-get install -y tesseract-ocr-deu tesseract-ocr-eng
            
            # Install additional useful language packs
            echo "📚 Installing additional language packs..."
            sudo apt-get install -y tesseract-ocr-fra tesseract-ocr-spa tesseract-ocr-ita || true
            ;;
            
        "rhel")
            echo "📦 Installing EPEL repository..."
            sudo yum install -y epel-release || sudo dnf install -y epel-release
            
            echo "🔤 Installing Tesseract OCR..."
            sudo yum install -y tesseract tesseract-langpack-deu tesseract-langpack-eng || \
            sudo dnf install -y tesseract tesseract-langpack-deu tesseract-langpack-eng
            ;;
            
        "arch")
            echo "📦 Updating package database..."
            sudo pacman -Sy
            
            echo "🔤 Installing Tesseract OCR..."
            sudo pacman -S --noconfirm tesseract tesseract-data-deu tesseract-data-eng
            ;;
    esac
}

# Function to install on Windows
install_windows() {
    echo "🪟 Windows detected"
    echo "❗ Please install Tesseract manually on Windows:"
    echo ""
    echo "1. Download Tesseract installer from:"
    echo "   https://github.com/UB-Mannheim/tesseract/wiki"
    echo ""
    echo "2. Run the installer and follow the instructions"
    echo ""
    echo "3. Add Tesseract to your PATH or set TESSERACT_CMD environment variable:"
    echo "   set TESSERACT_CMD=C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
    echo ""
    echo "4. Verify installation by running:"
    echo "   tesseract --version"
    echo ""
    exit 0
}

# Function to verify installation
verify_installation() {
    echo ""
    echo "🧪 Verifying installation..."
    
    if command_exists tesseract; then
        echo "✅ Tesseract found: $(which tesseract)"
        
        # Check version
        TESSERACT_VERSION=$(tesseract --version 2>&1 | head -n1)
        echo "📋 Version: $TESSERACT_VERSION"
        
        # Check available languages
        echo "🌍 Available languages:"
        tesseract --list-langs 2>/dev/null | tail -n +2 | sed 's/^/   /'
        
        # Check for required languages
        LANGS=$(tesseract --list-langs 2>/dev/null)
        if echo "$LANGS" | grep -q "deu"; then
            echo "✅ German language pack installed"
        else
            echo "⚠️  German language pack not found"
        fi
        
        if echo "$LANGS" | grep -q "eng"; then
            echo "✅ English language pack installed"
        else
            echo "⚠️  English language pack not found"
        fi
        
    else
        echo "❌ Tesseract not found in PATH"
        echo "   Please check your installation"
        exit 1
    fi
}

# Main installation logic
case $OS in
    "macos")
        install_macos
        ;;
    "linux")
        install_linux
        ;;
    "windows")
        install_windows
        ;;
esac

# Verify installation
verify_installation

echo ""
echo "🎉 System dependencies installation completed!"
echo ""
echo "📝 Next steps:"
echo "1. Install DMS: pip install dms"
echo "2. Initialize DMS: dms init --api-key your-openrouter-key"
echo "3. Start using DMS: dms import-file document.pdf"
echo ""
echo "📚 For more information, see the README.md file"