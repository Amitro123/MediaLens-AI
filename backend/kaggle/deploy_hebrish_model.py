"""
Deploy script for fine-tuned Hebrish STT model.

After training on Kaggle, download the model and run this script
to deploy it to the DevLens backend.

Usage:
    python deploy_hebrish_model.py path/to/devlens-hebrish-stt/
"""

import sys
import shutil
from pathlib import Path


def deploy_model(model_path: str, target_dir: str = "models/hebrish-stt"):
    """
    Deploy a fine-tuned Hebrish model to the backend.
    
    Args:
        model_path: Path to the trained model directory
        target_dir: Target directory for deployment
    """
    source = Path(model_path)
    target = Path(target_dir)
    
    if not source.exists():
        print(f"❌ Model not found: {source}")
        sys.exit(1)
    
    # Create target directory
    target.mkdir(parents=True, exist_ok=True)
    
    # Copy model files
    print(f"📦 Copying model from {source} to {target}...")
    for item in source.iterdir():
        if item.is_file():
            shutil.copy2(item, target / item.name)
            print(f"  ✅ {item.name}")
        elif item.is_dir():
            shutil.copytree(item, target / item.name, dirs_exist_ok=True)
            print(f"  ✅ {item.name}/")
    
    print(f"\n✅ Model deployed to {target}")
    print(f"\n📝 Next steps:")
    print(f"1. Update .env: HEBRISH_MODEL={target}")
    print(f"2. Enable: HEBRISH_STT_ENABLED=true")
    print(f"3. Test: python -m app.cli test-hebrish-stt audio.wav")


def test_model(model_path: str = "models/hebrish-stt"):
    """
    Quick test of the deployed model.
    
    Args:
        model_path: Path to the deployed model
    """
    try:
        from faster_whisper import WhisperModel
        
        print(f"🔄 Loading model from {model_path}...")
        model = WhisperModel(model_path, device="cpu", compute_type="int8")
        
        print("✅ Model loaded successfully!")
        print(f"\n🧪 Ready to transcribe. Use:")
        print(f"   python -m app.cli test-hebrish-stt your_audio.wav")
        
    except ImportError:
        print("⚠️ faster-whisper not installed. Run: pip install faster-whisper")
    except Exception as e:
        print(f"❌ Error loading model: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python deploy_hebrish_model.py <model_path>")
        print("       python deploy_hebrish_model.py --test")
        sys.exit(1)
    
    if sys.argv[1] == "--test":
        test_model()
    else:
        deploy_model(sys.argv[1])
