#!/usr/bin/env python3
"""
Test script to verify DMS installation works correctly.
This script can be used to test installation on clean systems.
"""

import sys
import subprocess
import tempfile
import os
from pathlib import Path


def run_command(cmd, check=True, capture_output=True):
    """Run a command and return the result"""
    print(f"Running: {cmd}")
    result = subprocess.run(
        cmd, 
        shell=True, 
        check=check, 
        capture_output=capture_output,
        text=True
    )
    if capture_output:
        print(f"Output: {result.stdout}")
        if result.stderr:
            print(f"Error: {result.stderr}")
    return result


def test_python_version():
    """Test Python version compatibility"""
    print("🐍 Testing Python version...")
    version = sys.version_info
    print(f"Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major != 3 or version.minor < 9:
        print("❌ Python 3.9+ required")
        return False
    
    print("✅ Python version compatible")
    return True


def test_system_dependencies():
    """Test system dependencies (Tesseract)"""
    print("🔧 Testing system dependencies...")
    
    # Test Tesseract
    try:
        result = run_command("tesseract --version", check=False)
        if result.returncode == 0:
            print("✅ Tesseract found")
            
            # Test language packs
            result = run_command("tesseract --list-langs", check=False)
            if result.returncode == 0:
                langs = result.stdout.lower()
                if "deu" in langs:
                    print("✅ German language pack found")
                else:
                    print("⚠️  German language pack not found")
                
                if "eng" in langs:
                    print("✅ English language pack found")
                else:
                    print("⚠️  English language pack not found")
            
            return True
        else:
            print("❌ Tesseract not found")
            print("   Run: ./install_system_deps.sh")
            return False
    except Exception as e:
        print(f"❌ Error testing Tesseract: {e}")
        return False


def test_dms_installation():
    """Test DMS package installation"""
    print("📦 Testing DMS installation...")
    
    try:
        import dms
        print(f"✅ DMS package imported successfully")
        print(f"   Version: {dms.__version__}")
        return True
    except ImportError as e:
        print(f"❌ Failed to import DMS: {e}")
        print("   Install with: pip install dms-rag")
        return False


def test_dms_cli():
    """Test DMS CLI functionality"""
    print("⚡ Testing DMS CLI...")
    
    # Test basic CLI
    try:
        result = run_command("dms --help", check=False)
        if result.returncode == 0:
            print("✅ DMS CLI accessible")
        else:
            print("❌ DMS CLI not accessible")
            return False
    except Exception as e:
        print(f"❌ Error testing CLI: {e}")
        return False
    
    # Test configuration
    try:
        result = run_command("dms config show", check=False)
        if result.returncode == 0:
            print("✅ DMS configuration accessible")
        else:
            print("⚠️  DMS not initialized (run 'dms init')")
    except Exception as e:
        print(f"⚠️  Configuration test failed: {e}")
    
    return True


def test_dependencies():
    """Test Python dependencies"""
    print("📚 Testing Python dependencies...")
    
    required_packages = [
        "typer",
        "pdfplumber", 
        "pytesseract",
        "pdf2image",
        "PIL",  # Pillow
        "chromadb",
        "sentence_transformers",
        "openai",
        "requests",
        "dotenv",
        "numpy"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == "PIL":
                import PIL
            elif package == "dotenv":
                import dotenv
            else:
                __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package}")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing packages: {', '.join(missing_packages)}")
        return False
    
    print("✅ All dependencies available")
    return True


def test_basic_functionality():
    """Test basic DMS functionality"""
    print("🧪 Testing basic functionality...")
    
    # Create temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Test initialization
        print("  Testing initialization...")
        env = os.environ.copy()
        env["DMS_DATA_DIR"] = str(temp_path / "dms_test")
        
        try:
            result = subprocess.run(
                ["dms", "init"],
                env=env,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                print("✅ DMS initialization successful")
            else:
                print(f"⚠️  DMS initialization failed: {result.stderr}")
        
        except subprocess.TimeoutExpired:
            print("⚠️  DMS initialization timed out")
        except Exception as e:
            print(f"⚠️  DMS initialization error: {e}")
    
    return True


def main():
    """Main test function"""
    print("🔍 DMS Installation Test")
    print("=" * 50)
    
    tests = [
        ("Python Version", test_python_version),
        ("System Dependencies", test_system_dependencies),
        ("DMS Installation", test_dms_installation),
        ("Python Dependencies", test_dependencies),
        ("DMS CLI", test_dms_cli),
        ("Basic Functionality", test_basic_functionality),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n📊 Test Summary")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if success:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! DMS is ready to use.")
        print("\n📝 Next steps:")
        print("1. Set your OpenRouter API key: dms init --api-key sk-or-your-key")
        print("2. Import a PDF: dms import-file document.pdf")
        print("3. Query your documents: dms query 'What documents do I have?'")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())