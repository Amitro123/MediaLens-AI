"""
Hebrish STT Service - Optimized for Hebrew + English technical terms.

Uses ivrit-ai/faster-whisper-v2-d4 model with tech vocabulary bias
for transcribing Israeli dev meeting recordings.
"""

import time
import logging
import threading
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class HebrishResult:
    """Result from Hebrish transcription with metrics"""
    segments: List[Dict[str, Any]] = field(default_factory=list)
    processing_time_ms: float = 0.0
    model_used: str = "ivrit-ai/faster-whisper-v2-d4"
    
    @property
    def segment_count(self) -> int:
        return len(self.segments)
    
    @property
    def total_duration(self) -> float:
        if not self.segments:
            return 0.0
        return max(s.get("end", 0) for s in self.segments)


# Tech vocabulary for initial prompt bias
# Try to load from Kaggle-extracted file, fallback to default
def _load_tech_prompt() -> str:
    """Load tech vocab prompt from file or use default"""
    from pathlib import Path
    prompt_file = Path(__file__).parent.parent.parent / "models" / "tech_prompt.txt"
    if prompt_file.exists():
        try:
            return prompt_file.read_text(encoding="utf-8").strip()
        except Exception:
            pass
    # Fallback to default prompt
    return (
        "deploy production logs API JSON React kubernetes commit PR merge "
        "git branch code review backend frontend database server endpoint "
        "docker container npm webpack eslint typescript debug stack trace "
        "authentication authorization JWT token session cookies cache redis "
        "async await promise callback function class component state props "
        "route controller service repository model schema migration query"
    )

TECH_VOCAB_PROMPT = _load_tech_prompt()


class HebrishSTTService:
    """
    Hebrew + Technical English STT using ivrit-ai Whisper model.
    
    Optimized for Israeli dev meetings with mixed Hebrew/English content.
    Uses tech vocabulary bias to improve recognition of English terms.
    
    Usage:
        service = HebrishSTTService()
        result = service.transcribe("/path/to/audio.wav")
        print(result.segments)
    """
    
    def __init__(self, device: Optional[str] = None):
        """
        Initialize the Hebrish STT service.
        
        Args:
            device: "cuda" or "cpu". If None, auto-detect.
        """
        self.model = None
        self._model_load_error: Optional[str] = None
        self._device = device
        self._load_model()
    
    def _load_model(self) -> None:
        """Load the Hebrew-optimized Whisper model"""
        try:
            import torch
            from faster_whisper import WhisperModel
            
            # Auto-detect device
            if self._device is None:
                self._device = "cuda" if torch.cuda.is_available() else "cpu"
            
            # Compute type based on device
            compute_type = "float16" if self._device == "cuda" else "int8"
            
            logger.info(f"Loading Hebrish model on {self._device}...")
            self.model = WhisperModel(
                "ivrit-ai/faster-whisper-v2-d4",
                device=self._device,
                compute_type=compute_type
            )
            logger.info("✅ Hebrish STT ready")
            
        except ImportError as e:
            self._model_load_error = f"Missing dependency: {e}"
            logger.warning(f"⚠️ Hebrish STT unavailable: {self._model_load_error}")
        except Exception as e:
            self._model_load_error = str(e)
            logger.warning(f"⚠️ Hebrish STT unavailable: {e}")
    
    @property
    def is_available(self) -> bool:
        """Check if the model is loaded and ready"""
        return self.model is not None
    
    def transcribe(self, audio_path: str) -> HebrishResult:
        """
        Transcribe audio file with Hebrew + tech vocab optimization.
        
        Args:
            audio_path: Path to audio file (WAV, MP3, etc.)
        
        Returns:
            HebrishResult with segments and metrics
        """
        if not self.model:
            logger.error("Hebrish model not available")
            return HebrishResult(
                segments=[],
                processing_time_ms=0.0,
                model_used="unavailable"
            )
        
        start_time = time.time()
        
        try:
            # Run transcription with Hebrew language and tech vocab bias
            segments_iter, info = self.model.transcribe(
                audio_path,
                language="he",  # Hebrew primary
                initial_prompt=TECH_VOCAB_PROMPT,  # Tech vocab bias
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500)
            )
            
            # Convert to list of dicts
            segments_list = []
            for seg in segments_iter:
                segments_list.append({
                    "start": seg.start,
                    "end": seg.end,
                    "text": seg.text.strip(),
                    "confidence": getattr(seg, 'avg_logprob', 0.0)
                })
            
            processing_time = (time.time() - start_time) * 1000
            
            logger.info(
                f"Hebrish STT completed: {len(segments_list)} segments "
                f"in {processing_time:.0f}ms (duration: {info.duration:.1f}s)"
            )
            
            return HebrishResult(
                segments=segments_list,
                processing_time_ms=processing_time,
                model_used="ivrit-ai/faster-whisper-v2-d4"
            )
        
        except Exception as e:
            logger.error(f"Hebrish transcription failed: {e}")
            return HebrishResult(
                segments=[],
                processing_time_ms=0.0,
                model_used="error"
            )
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status for monitoring"""
        return {
            "available": self.is_available,
            "device": self._device,
            "model": "ivrit-ai/faster-whisper-v2-d4",
            "error": self._model_load_error
        }


# Singleton instance with thread-safe initialization
_hebrish_stt_service: Optional[HebrishSTTService] = None
_hebrish_stt_lock = threading.Lock()


def get_hebrish_stt_service() -> HebrishSTTService:
    """Get or create the HebrishSTTService singleton (thread-safe)"""
    global _hebrish_stt_service
    if _hebrish_stt_service is None:
        with _hebrish_stt_lock:
            # Double-check after acquiring lock
            if _hebrish_stt_service is None:
                _hebrish_stt_service = HebrishSTTService()
    return _hebrish_stt_service


def reset_hebrish_stt_service() -> None:
    """Reset the singleton (for testing)"""
    global _hebrish_stt_service
    with _hebrish_stt_lock:
        _hebrish_stt_service = None
