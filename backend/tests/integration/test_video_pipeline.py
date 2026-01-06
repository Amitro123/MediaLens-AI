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
        assert mock_gen_inst.merge_segments.called
        assert mock_split.called

