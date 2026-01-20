"""Unit tests for Agent Orchestrator"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.services.agent_orchestrator import DevLensAgent, DevLensAgentOptions
from pathlib import Path


class TestDevLensAgent:
    """Test the DevLensAgent service with mocks"""

    @pytest.fixture
    def agent(self):
        return DevLensAgent()

    @pytest.mark.asyncio
    @patch("app.services.agent_orchestrator.get_prompt_loader")
    @patch("app.services.agent_orchestrator.process_video_pipeline")
    async def test_generate_documentation_success(self, mock_pipeline, mock_loader, agent):
        # Setup mocks
        mock_prompt = MagicMock()
        mock_prompt.name = "Test Mode"
        mock_loader.return_value.load_prompt.return_value = mock_prompt
        
        mock_result = MagicMock()
        mock_result.documentation = "# Done"
        mock_result.status = "completed"
        mock_result.mode = "general_doc"
        mock_result.mode_name = "General Documentation"
        mock_result.project_name = "Test"
        mock_result.stt_provider = "unknown"
        mock_result.transcript = None
        mock_result.transcript_segments = None
        mock_pipeline.return_value = mock_result
        
        options = DevLensAgentOptions(
            mode="general_doc",
            project_name="Test"
        )
        
        result = await agent.generate_documentation(
            session_id="test_s",
            video_path=Path("test.mp4"),
            options=options
        )
        
        assert result.documentation == "# Done"
        assert result.status == "completed"

    @pytest.mark.asyncio
    @patch("app.services.agent_orchestrator.get_session_manager")
    @patch("app.services.agent_orchestrator.get_prompt_loader")
    @patch("app.services.agent_orchestrator.process_video_pipeline")
    async def test_handle_pipeline_failure(self, mock_pipeline, mock_loader, mock_manager, agent):
        mock_manager_inst = mock_manager.return_value
        
        mock_prompt = MagicMock()
        mock_prompt.name = "Test Mode"
        mock_loader.return_value.load_prompt.return_value = mock_prompt
        
        # Test error handling
        from app.services.video_pipeline import PipelineError
        mock_pipeline.side_effect = PipelineError("Crash")
        
        options = DevLensAgentOptions(
            mode="general_doc",
            project_name="Test"
        )
        
        with pytest.raises(PipelineError):
            await agent.generate_documentation(
                session_id="test_fail",
                video_path=Path("test.mp4"),
                options=options
            )
        
        assert mock_manager_inst.fail.called

        assert mock_manager_inst.fail.called

    @pytest.mark.asyncio
    @patch("app.services.agent_orchestrator.extract_frames_at_timestamps")
    @patch("app.services.agent_orchestrator.detect_scene_boundaries_with_flash")
    @patch("app.services.agent_orchestrator.create_low_fps_proxy")
    @patch("app.services.agent_orchestrator.transcribe_audio")
    @patch("app.services.agent_orchestrator.extract_frames_uniform")
    @patch("app.services.agent_orchestrator.get_video_duration")
    @patch("app.services.agent_orchestrator.get_generator")
    @patch("app.services.agent_orchestrator.get_prompt_loader")
    async def test_scene_cataloging_flow(
        self, mock_loader, mock_gen, mock_dur, mock_ext, mock_trans, mock_proxy, mock_detect, mock_ext_timestamps, agent
    ):
        # Setup
        # Setup
        mock_dur.return_value = 60.0
        mock_trans.return_value = {"full_text": "dialogue", "segments": []}
        mock_ext.return_value = ["frame1.jpg", "frame2.jpg"]
        mock_proxy.return_value = "proxy.mp4"
        mock_detect.return_value = [{"time_sec": 10.0, "reason": "Cut", "quality_ok": True}]
        mock_ext_timestamps.return_value = ["frame_cut.jpg"]
        
        mock_prompt = MagicMock()
        mock_prompt.name = "Scene Detection"
        mock_prompt.system_instruction = "sys"
        mock_prompt.user_prompt = "user {project_name}"
        mock_loader.return_value.load_prompt.return_value = mock_prompt
        
        mock_gen_inst = mock_gen.return_value
        mock_gen_inst.generate_documentation = MagicMock(return_value="[JSON]")
        
        options = DevLensAgentOptions(
            mode="scene_detection",
            project_name="Test Project"
        )
        
        result = await agent.generate_documentation(
            session_id="test_scene",
            video_path=Path("video.mp4"),
            options=options
        )
        
        assert result.mode == "scene_detection"
        assert result.documentation == "[JSON]"
        mock_trans.assert_called_once()
        # Either uniform or timestamps extraction should be called. 
        # Since we mocked detection to return boundaries, extract_frames_at_timestamps should be called.
        mock_ext_timestamps.assert_called_once()
        mock_gen_inst.generate_documentation.assert_called_once()
