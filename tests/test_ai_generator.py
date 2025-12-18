"""Comprehensive tests for AI Generator Service"""

import pytest
from unittest.mock import patch, MagicMock
from app.services.ai_generator import (
    DocumentationGenerator,
    AIGenerationError,
    get_generator
)


class TestDocumentationGenerator:
    """Test suite for DocumentationGenerator class"""
    
    @pytest.fixture
    def mock_genai(self):
        """Mock Google GenerativeAI"""
        with patch('app.services.ai_generator.genai') as mock:
            mock.configure = MagicMock()
            mock.GenerativeModel.return_value = MagicMock()
            yield mock

    @pytest.fixture
    def mock_settings(self):
        """Mock settings with API key"""
        with patch('app.services.ai_generator.settings') as mock:
            mock.gemini_api_key = "test_api_key"
            mock.groq_api_key = ""
            yield mock

    def test_generator_init(self, mock_genai, mock_settings):
        """Test DocumentationGenerator initialization"""
        generator = DocumentationGenerator()
        
        assert generator.model_pro is not None
        assert generator.model_flash is not None
        mock_genai.configure.assert_called_once()

    def test_generator_init_failure(self, mock_settings):
        """Test generator handles initialization errors"""
        with patch('app.services.ai_generator.genai') as mock_genai:
            mock_genai.configure.side_effect = Exception("API Error")
            
            with pytest.raises(AIGenerationError) as exc_info:
                DocumentationGenerator()
            
            assert "Failed to initialize" in str(exc_info.value)

    def test_analyze_video_relevance(self, mock_genai, mock_settings):
        """Test video relevance analysis (multimodal)"""
        # Mock response
        mock_response = MagicMock()
        mock_response.text = '{"relevant_segments": [{"start": 0, "end": 10, "reason": "tech talk", "key_timestamps": [5.0]}]}'
        
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        mock_genai.upload_file.return_value = MagicMock()
        
        generator = DocumentationGenerator()
        # Override the internal method
        generator._analyze_multimodal_fast = MagicMock(return_value=mock_response)
        
        segments = generator.analyze_video_relevance(
            "test_video.mp4",
            context_keywords=["api", "docs"]
        )
        
        assert isinstance(segments, list)

    def test_analyze_video_empty_response(self, mock_genai, mock_settings):
        """Test handling of empty video analysis response"""
        mock_response = MagicMock()
        mock_response.text = ""
        
        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model
        mock_genai.upload_file.return_value = MagicMock()
        
        generator = DocumentationGenerator()
        generator._analyze_multimodal_fast = MagicMock(return_value=mock_response)
        
        with pytest.raises(AIGenerationError) as exc_info:
            generator.analyze_video_relevance("test.mp4", [])
        
        assert "empty response" in str(exc_info.value)

    def test_generate_documentation(self, mock_genai, mock_settings):
        """Test documentation generation"""
        from app.services.prompt_loader import PromptConfig
        
        mock_response = MagicMock()
        mock_response.text = "# Generated Documentation\n\nThis is the content."
        
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        mock_genai.upload_file.return_value = MagicMock()
        
        generator = DocumentationGenerator()
        
        prompt_config = PromptConfig(
            id="test",
            name="Test",
            description="Test mode",
            system_instruction="Generate docs",
            output_format="markdown"
        )
        
        result = generator.generate_documentation(
            frame_paths=["frame1.jpg", "frame2.jpg"],
            prompt_config=prompt_config,
            project_name="Test Project"
        )
        
        assert "Generated Documentation" in result

    def test_generate_documentation_no_frames(self, mock_genai, mock_settings):
        """Test error when no frames can be uploaded"""
        from app.services.prompt_loader import PromptConfig
        
        mock_genai.upload_file.side_effect = Exception("Upload failed")
        
        generator = DocumentationGenerator()
        
        prompt_config = PromptConfig(
            id="test",
            name="Test",
            description="Test",
            system_instruction="Test",
            output_format="markdown"
        )
        
        with pytest.raises(AIGenerationError) as exc_info:
            generator.generate_documentation(
                frame_paths=["fail.jpg"],
                prompt_config=prompt_config
            )
        
        assert "Failed to upload any frames" in str(exc_info.value)


class TestGeneratorSingleton:
    """Test singleton pattern for generator"""
    
    def test_get_generator_singleton(self):
        """Test generator singleton returns same instance"""
        with patch('app.services.ai_generator.genai') as mock_genai:
            with patch('app.services.ai_generator.settings') as mock_settings:
                mock_settings.gemini_api_key = "test"
                mock_settings.groq_api_key = ""
                mock_genai.configure = MagicMock()
                mock_genai.GenerativeModel.return_value = MagicMock()
                
                # Reset singleton
                import app.services.ai_generator as ai_mod
                ai_mod._generator = None
                
                gen1 = get_generator()
                gen2 = get_generator()
                
                assert gen1 is gen2
