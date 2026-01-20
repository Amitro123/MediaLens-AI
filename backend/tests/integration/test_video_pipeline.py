"""Integration tests for Video Pipeline"""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from app.services.video_pipeline import process_video_pipeline, VideoPipelineResult
from app.services.prompt_loader import PromptConfig


@pytest.fixture
def mock_prompt_config():
    return PromptConfig(
        name="Test Mode",
        description="Test Description",
        system_instruction="Test Instruction",
        department="R&D"
    )


class TestVideoPipeline:
    """Test the video processing pipeline with mocks"""

    @pytest.mark.asyncio
    @patch("app.services.video_pipeline.get_generator")
    @patch("app.services.video_pipeline.extract_frames")
    @patch("app.services.video_pipeline.create_low_fps_proxy")
    @patch("app.services.video_pipeline.get_video_duration")
    @patch("app.services.video_pipeline.get_storage_service")
    @patch("app.services.video_pipeline.get_acontext_client")
    async def test_process_video_pipeline_success(
        self, mock_acontext, mock_storage, mock_duration, mock_proxy, mock_extract, mock_generator, mock_prompt_config
    ):
        # Setup mocks
        mock_duration.return_value = 60.0  # 60 seconds
        mock_proxy.return_value = "proxy.mp4"
        mock_extract.return_value = [str(Path("f1.jpg")), str(Path("f2.jpg"))]
        
        mock_gen_inst = mock_generator.return_value
        mock_gen_inst.analyze_video_relevance.return_value = [
            {"start": 0, "end": 10, "reason": "test", "key_timestamps": [1.0, 5.0]}
        ]
        mock_gen_inst.generate_documentation.return_value = "# Generated Docs"
        
        mock_storage_inst = mock_storage.return_value
        mock_acontext_inst = mock_acontext.return_value
        mock_acontext_inst.is_enabled = False
        
        # Run pipeline
        result = await process_video_pipeline(
            video_path=Path("test.mp4"),
            task_id="test_task",
            prompt_config=mock_prompt_config,
            project_name="Test Project"
        )
        
        # Verify
        assert isinstance(result, VideoPipelineResult)
        assert result.documentation == "# Generated Docs"
        assert result.status == "completed"
        assert result.project_name == "Test Project"

    @pytest.mark.asyncio
    @patch("app.services.video_pipeline.get_video_duration")
    async def test_process_video_pipeline_failure(
        self, mock_duration, mock_prompt_config
    ):
        # Setup mock to fail validation (video too long)
        from app.core.config import settings
        mock_duration.return_value = settings.max_video_length + 100
        
        from app.services.video_pipeline import PipelineError
        
        # Run pipeline and expect error
        with pytest.raises(PipelineError, match="Video too long"):
            await process_video_pipeline(
                video_path=Path("test.mp4"),
                task_id="test_task",
                prompt_config=mock_prompt_config,
                project_name="Test Project"
            )

    @pytest.mark.asyncio
    @patch("app.services.video_pipeline.get_generator")
    @patch("app.services.video_pipeline.extract_segment_frames")
    @patch("app.services.video_pipeline.split_into_segments")
    @patch("app.services.video_pipeline.get_video_duration")
    @patch("app.services.video_pipeline.get_storage_service")
    @patch("app.services.video_pipeline.get_acontext_client")
    async def test_process_video_pipeline_segmented(
        self, mock_acontext, mock_storage, mock_duration, mock_split, mock_extract_seg, mock_generator, mock_prompt_config
    ):
        # Setup mocks for segmented processing
        mock_duration.return_value = 60.0
        mock_split.return_value = [
            {"index": 0, "start": 0.0, "end": 30.0},
            {"index": 1, "start": 30.0, "end": 60.0}
        ]
        mock_extract_seg.return_value = [str(Path("f1.jpg"))]
        
        mock_gen_inst = mock_generator.return_value
        mock_gen_inst.generate_segment_doc.return_value = "Segment doc"
        mock_gen_inst.merge_segments.return_value = "# Merged Documentation\n\nSegment doc\n\nSegment doc"
        
        mock_storage_inst = mock_storage.return_value
        mock_acontext_inst = mock_acontext.return_value
        mock_acontext_inst.is_enabled = False
        
        from app.services.video_pipeline import process_video_pipeline_segmented
        
        # Run segmented pipeline
        result = await process_video_pipeline_segmented(
            video_path=Path("test.mp4"),
            task_id="test_task",
            prompt_config=mock_prompt_config,
            project_name="Test Project",
            segment_duration_sec=30
        )
        
        # Verify
        assert result is not None
        assert "Segment doc" in result.documentation
    @pytest.mark.asyncio
    @patch("app.services.video_pipeline.get_generator")
    @patch("app.services.video_pipeline.extract_frames")
    @patch("app.services.video_pipeline.create_low_fps_proxy")
    @patch("app.services.video_pipeline.get_video_duration")
    @patch("app.services.video_pipeline.get_storage_service")
    @patch("app.services.video_pipeline.get_acontext_client")
    @patch("app.services.video_pipeline.extract_audio")
    @patch("app.services.stt_hebrish_service.get_hebrish_stt_service")
    async def test_process_video_pipeline_with_stt(
        self, mock_stt_service_getter, mock_audio_extractor, mock_acontext, mock_storage, mock_duration, mock_proxy, mock_extract, mock_generator, mock_prompt_config
    ):
        # Setup mocks
        mock_duration.return_value = 60.0
        mock_proxy.return_value = "proxy.mp4"
        mock_extract.return_value = [str(Path("f1.jpg"))]
        mock_audio_extractor.return_value = "audio.wav"
        
        # Setup STT Mock
        mock_stt_service = MagicMock()
        mock_stt_service.is_available = True
        mock_stt_service.transcribe = AsyncMock()
        
        # Mock segments result
        mock_stt_result = MagicMock()
        mock_stt_result.model_used = "groq"
        mock_stt_result.segments = [
            {"start": 0, "end": 5, "text": "Hello world"},
            {"start": 5, "end": 10, "text": "Testing STT"}
        ]
        mock_stt_service.transcribe.return_value = mock_stt_result
        mock_stt_service_getter.return_value = mock_stt_service

        mock_gen_inst = mock_generator.return_value
        mock_gen_inst.analyze_video_relevance.return_value = None
        mock_gen_inst.generate_documentation.return_value = "# Documents"
        
        mock_storage_inst = mock_storage.return_value
        mock_acontext_inst = mock_acontext.return_value
        mock_acontext_inst.is_enabled = False
        
        # Run pipeline
        from app.core.config import settings
        original_stt_setting = settings.hebrish_stt_enabled
        settings.hebrish_stt_enabled = True # Force enable STT
        
        try:
            result = await process_video_pipeline(
                video_path=Path("test.mp4"),
                task_id="test_task_stt",
                prompt_config=mock_prompt_config,
                project_name="Test Project",
                mode="general_doc"
            )
        finally:
            settings.hebrish_stt_enabled = original_stt_setting
        
        # Verify result contains transcript
        assert result.transcript is not None
        assert "Hello world" in result.transcript
        assert result.transcript_segments == mock_stt_result.segments
        
        # Verify storage was called with transcript data
        mock_storage_inst.add_session.assert_called_with(
            "test_task_stt",
            {
                "title": "Test Project",
                "topic": "Test Mode",
                "status": "completed",
                "documentation": "# Documents",
                "mode": "general_doc",
                "mode_name": "Test Mode",
                "stt_provider": "groq",
                "transcript": "Hello world\nTesting STT",
                "transcript_segments": mock_stt_result.segments
            }
        )

