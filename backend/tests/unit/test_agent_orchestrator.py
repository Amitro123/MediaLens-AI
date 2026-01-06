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

