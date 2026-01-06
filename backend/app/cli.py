"""
DevLens AI CLI - Management commands for the application.

Usage:
    python -m app.cli [COMMAND] [OPTIONS]
    
Commands:
    generate-hebrish-dataset  Generate Hebrish audio dataset for Whisper fine-tuning
    test-hebrish-stt          Test Hebrish STT on an audio file
"""

import typer
import logging
from pathlib import Path
from typing import Optional

app = typer.Typer(
    name="devlens",
    help="DevLens AI management commands"
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


@app.command()
def generate_hebrish_dataset(
    output_dir: str = typer.Option(
        "static/datasets/hebrish",
        "--output-dir", "-o",
        help="Output directory for dataset"
    ),
    count: Optional[int] = typer.Option(
        None,
        "--count", "-n",
        help="Number of sentences to generate (default: all 500)"
    ),
    no_audio: bool = typer.Option(
        False,
        "--no-audio",
        help="Generate text manifest only, skip TTS audio generation"
    )
):
    """
    Generate Hebrish dataset for Whisper LoRA fine-tuning.
    
    Creates audio clips from 500 Hebrew+English technical sentences
    using Chatterbox TTS, suitable for training Whisper on Israeli
    dev meeting transcription.
    """
    from app.scripts.generate_hebrish_dataset import main as generate_main
    
    typer.echo(f"🎙️ Generating Hebrish dataset...")
    typer.echo(f"   Output: {output_dir}")
    typer.echo(f"   Count: {count or 'all 500'}")
    typer.echo(f"   TTS: {'disabled' if no_audio else 'enabled'}")
    typer.echo()
    
    manifest_path = generate_main(
        output_dir=output_dir,
        count=count,
        use_tts=not no_audio
    )
    
    typer.echo()
    typer.echo(f"✅ Dataset ready: {manifest_path}")
    typer.echo()
    typer.echo("Next steps:")
    typer.echo("  1. Upload to Colab with Unsloth for Whisper LoRA fine-tuning")
    typer.echo("  2. Or use with your preferred training framework")


@app.command()
def test_hebrish_stt(
    audio_path: str = typer.Argument(
        ...,
        help="Path to audio file to transcribe"
    ),
    json_output: bool = typer.Option(
        False,
        "--json", "-j",
        help="Output as JSON"
    )
):
    """
    Test Hebrish STT accuracy on an audio file.
    
    Uses the ivrit-ai/faster-whisper-v2-d4 model with tech
    vocabulary bias for improved recognition of English terms.
    """
    import json
    from app.services.stt_hebrish_service import HebrishSTTService
    
    path = Path(audio_path)
    if not path.exists():
        typer.echo(f"❌ File not found: {audio_path}", err=True)
        raise typer.Exit(1)
    
    typer.echo(f"🎧 Loading Hebrish STT model...")
    service = HebrishSTTService()
    
    if not service.is_available:
        typer.echo(f"❌ Hebrish STT not available", err=True)
        typer.echo(f"   Error: {service._model_load_error}", err=True)
        raise typer.Exit(1)
    
    typer.echo(f"🎙️ Transcribing: {audio_path}")
    typer.echo()
    
    result = service.transcribe(str(path))
    
    if json_output:
        output = {
            "segments": result.segments,
            "processing_time_ms": result.processing_time_ms,
            "model_used": result.model_used,
            "segment_count": result.segment_count,
            "total_duration": result.total_duration
        }
        typer.echo(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        typer.echo("📝 Transcription:")
        typer.echo("-" * 50)
        for seg in result.segments:
            start = seg.get("start", 0)
            end = seg.get("end", 0)
            text = seg.get("text", "")
            typer.echo(f"[{start:.1f}s - {end:.1f}s] {text}")
        typer.echo("-" * 50)
        typer.echo()
        typer.echo(f"⏱️  Processing time: {result.processing_time_ms:.0f}ms")
        typer.echo(f"📊 Segments: {result.segment_count}")
        typer.echo(f"🎯 Model: {result.model_used}")


@app.command()
def stt_health():
    """Check STT service health status."""
    from app.services.stt_fast_service import get_fast_stt_service
    from app.services.stt_hebrish_service import get_hebrish_stt_service
    
    typer.echo("🔍 STT Health Check")
    typer.echo("=" * 40)
    
    # Fast STT
    typer.echo("\n📦 Fast STT (General):")
    fast_stt = get_fast_stt_service()
    status = fast_stt.get_health_status()
    typer.echo(f"   Enabled: {status['enabled']}")
    typer.echo(f"   Available: {status['available']}")
    typer.echo(f"   Model: {status['model_size']}")
    if status.get('error'):
        typer.echo(f"   Error: {status['error']}")
    
    # Hebrish STT
    typer.echo("\n🇮🇱 Hebrish STT (Hebrew + Tech):")
    try:
        hebrish_stt = get_hebrish_stt_service()
        status = hebrish_stt.get_health_status()
        typer.echo(f"   Available: {status['available']}")
        typer.echo(f"   Device: {status['device']}")
        typer.echo(f"   Model: {status['model']}")
        if status.get('error'):
            typer.echo(f"   Error: {status['error']}")
    except Exception as e:
        typer.echo(f"   Error: {e}")
    
    typer.echo()


if __name__ == "__main__":
    app()
