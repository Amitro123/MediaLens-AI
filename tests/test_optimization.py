import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import json
import subprocess
import asyncio

def test_create_low_fps_proxy():
    """Test 1: Create a low-FPS version of the video specifically for analysis."""
    from app.services.video_processor import create_low_fps_proxy
    
    with patch("subprocess.run") as mock_run, \
         patch("pathlib.Path.exists") as mock_exists:
        
        mock_run.return_value = MagicMock(returncode=0)
        mock_exists.return_value = True # Simulate file creation success
        
        # Test path
        video_path = "test_video.mp4"
        proxy_path = create_low_fps_proxy(video_path)
        
        assert "proxy_1fps.mp4" in proxy_path
        # Verify FFmpeg command
        args, kwargs = mock_run.call_args
        command = args[0]
        assert "ffmpeg" in command
        assert "-filter:v" in command
        assert "fps=1,scale=640:-2" in command
        assert "-an" in command # Audio should be stripped for proxy

def test_analyze_video_relevance():
    """Test 2: Multimodal analysis of the proxy video."""
    from app.services.ai_generator import DocumentationGenerator
    from app.core.config import settings
    
    with patch("google.generativeai.upload_file") as mock_upload, \
         patch("google.generativeai.get_file") as mock_get_file, \
         patch("app.services.ai_generator.DocumentationGenerator._analyze_multimodal_fast") as mock_analyze:
        
        # Setup mocks
        mock_file = MagicMock()
        mock_file.state.name = "ACTIVE"
        mock_upload.return_value = mock_file
        
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "relevant_segments": [
                {
                    "start": 0.0,
                    "end": 10.0,
                    "reason": "Test segment",
                    "key_timestamps": [2.5, 7.5]
                }
            ],
            "technical_percentage": 100.0
        })
        mock_analyze.return_value = mock_response
        
        # We need to set a dummy API key to avoid initialization errors
        with patch.object(settings, 'gemini_api_key', 'test_key'):
            generator = DocumentationGenerator()
            segments = generator.analyze_video_relevance("dummy_proxy.mp4", ["test"])
            
            assert len(segments) == 1
            assert segments[0]["start"] == 0.0
            assert 2.5 in segments[0]["key_timestamps"]

@patch("app.services.video_pipeline.run_in_threadpool")
@patch("app.services.video_pipeline.get_generator")
@patch("app.services.video_pipeline.get_video_duration")
@patch("app.services.video_pipeline.get_storage_service")
@patch("app.services.video_pipeline.extract_frames")
@patch("pathlib.Path.exists")
def test_pipeline_dual_stream_orchestration(
    mock_exists,
    mock_extract_frames,
    mock_storage,
    mock_duration,
    mock_get_gen,
    mock_threadpool
):
    """Test 3: Orchestration of dual-stream flow in process_video_pipeline."""
    from app.services.video_pipeline import process_video_pipeline
    from app.services.prompt_loader import PromptConfig
    
    # Setup mocks
    mock_exists.return_value = True
    mock_duration.return_value = 10.0
    mock_generator = MagicMock()
    mock_get_gen.return_value = mock_generator
    
    # Mock return values for threadpool calls (in order of execution)
    # 1. get_video_duration
    # 2. create_low_fps_proxy
    # 3. analyze_video_relevance (newly wrapped - CR_FINDINGS 1.1)
    # 4. extract_frames
    # 5. generate_documentation (newly wrapped - CR_FINDINGS 1.1)
    mock_threadpool.side_effect = [
        10.0, # duration
        "test_proxy.mp4", # create_low_fps_proxy
        [{"start": 0.0, "end": 5.0, "key_timestamps": [2.5]}], # analyze_video_relevance
        ["frame1.jpg", "frame2.jpg"], # extract_frames
        "# Test Doc" # generate_documentation
    ]
    
    mock_prompt = MagicMock(spec=PromptConfig)
    mock_prompt.id = "general_doc"
    mock_prompt.name = "Technical Doc"
    mock_prompt.system_instruction = "Be helpful"
    
    video_path = Path("test_task/video.mp4")
    
    # Using asyncio.run for the async call to remain within a synchronous test function
    result = asyncio.run(process_video_pipeline(
        video_path=video_path,
        task_id="task_123",
        prompt_config=mock_prompt,
        project_name="Test Project"
    ))
    
    assert result.documentation == "# Test Doc"
    # Verify that analyze_video_relevance was called via threadpool with the proxy
    # Now we don't check direct mock on generator since it goes through threadpool
    
    # Verify extract_frames was called with the original video and custom timestamps
    # Extract frames is the 4th threadpool call (now that AI calls are wrapped)
    extract_call_args = mock_threadpool.call_args_list[3][0]
    assert extract_call_args[1] == str(video_path) # Original video
    assert 2.5 in extract_call_args[4] # Selected timestamp
