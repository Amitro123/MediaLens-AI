"""MVP Test Script for DevLens AI"""

import sys
from pathlib import Path

def test_imports():
    """Test that all required packages can be imported"""
    print("Testing package imports...")
    
    try:
        import fastapi
        print("✓ FastAPI")
    except ImportError:
        print("✗ FastAPI not installed")
        return False
    
    try:
        import cv2
        print("✓ OpenCV")
    except ImportError:
        print("✗ OpenCV not installed")
        return False
    
    try:
        import google.generativeai
        print("✓ Google GenerativeAI")
    except ImportError:
        print("✗ Google GenerativeAI not installed")
        return False
    
    try:
        import pydantic
        print("✓ Pydantic")
    except ImportError:
        print("✗ Pydantic not installed")
        return False
    
    return True


def test_config():
    """Test configuration loading"""
    print("\nTesting configuration...")
    
    try:
        from app.core.config import settings
        print(f"✓ Configuration loaded")
        print(f"  - Upload dir: {settings.upload_dir}")
        print(f"  - Frame interval: {settings.frame_interval}s")
        print(f"  - Max video length: {settings.max_video_length}s")
        
        # Check if API key is set
        if settings.gemini_api_key == "your_gemini_api_key_here":
            print("⚠ Warning: GEMINI_API_KEY not set in .env file")
        else:
            print("✓ GEMINI_API_KEY is configured")
        
        return True
    except Exception as e:
        print(f"✗ Configuration error: {str(e)}")
        return False


def test_services():
    """Test service imports"""
    print("\nTesting services...")
    
    try:
        from app.services.video_processor import extract_frames, get_video_duration
        print("✓ Video processor service")
    except Exception as e:
        print(f"✗ Video processor error: {str(e)}")
        return False
    
    try:
        from app.services.ai_generator import DocumentationGenerator
        print("✓ AI generator service")
    except Exception as e:
        print(f"✗ AI generator error: {str(e)}")
        return False
    
    return True


def test_api():
    """Test API imports"""
    print("\nTesting API...")
    
    try:
        from app.main import app
        print("✓ FastAPI app created")
    except Exception as e:
        print(f"✗ API error: {str(e)}")
        return False
    
    return True


def main():
    """Run all tests"""
    print("=" * 50)
    print("DevLens AI - MVP Test Suite")
    print("=" * 50)
    
    tests = [
        ("Package Imports", test_imports),
        ("Configuration", test_config),
        ("Services", test_services),
        ("API", test_api),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name} failed with exception: {str(e)}")
            results.append((name, False))
    
    print("\n" + "=" * 50)
    print("Test Results:")
    print("=" * 50)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n✓ All tests passed! DevLens AI is ready to use.")
        print("\nNext steps:")
        print("1. Set GEMINI_API_KEY in .env file")
        print("2. Run: uvicorn app.main:app --reload")
        print("3. Visit: http://localhost:8000/docs")
        return 0
    else:
        print("\n✗ Some tests failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
