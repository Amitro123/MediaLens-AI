"""Unit tests for app.core.config settings"""
import pytest


class TestSettings:
    """Test configuration settings"""

    def test_settings_import(self):
        """Test that settings can be imported"""
        from app.core.config import settings
        assert settings is not None

    def test_default_upload_dir(self):
        """Test default upload directory"""
        from app.core.config import settings
        assert settings.upload_dir is not None
        assert "uploads" in settings.upload_dir

    def test_frame_interval_positive(self):
        """Test frame interval is a positive number"""
        from app.core.config import settings
        assert settings.frame_interval > 0

    def test_max_video_length_reasonable(self):
        """Test max video length is reasonable (< 1 hour)"""
        from app.core.config import settings
        assert 0 < settings.max_video_length <= 3600

    def test_gemini_model_configured(self):
        """Test Gemini model names are configured"""
        from app.core.config import settings
        # Check doc model names exist (renamed from gemini_model)
        assert settings.doc_model_pro_name is not None
        assert settings.doc_model_flash_name is not None

    def test_redis_url_configured(self):
        """Test Redis URL is configured"""
        from app.core.config import settings
        assert settings.redis_url is not None
        assert "redis" in settings.redis_url

    def test_api_settings(self):
        """Test API host and port settings"""
        from app.core.config import settings
        assert settings.api_host is not None
        assert settings.api_port > 0

    def test_fast_stt_config(self):
        """Test Fast STT configuration"""
        from app.core.config import settings
        assert isinstance(settings.fast_stt_enabled, bool)
        assert settings.fast_stt_model in ["tiny", "base", "small", "medium", "large"]

    def test_get_upload_path_method(self):
        """Test get_upload_path method exists and works"""
        from app.core.config import settings
        from pathlib import Path
        
        path = settings.get_upload_path()
        assert path is not None
        assert isinstance(path, Path)
