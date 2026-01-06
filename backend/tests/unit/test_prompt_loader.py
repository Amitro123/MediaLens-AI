"""Unit tests for Prompt Loader service"""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import yaml
import tempfile
import shutil
import uuid


class TestPromptConfig:
    """Test the PromptConfig pydantic model"""
    
    def test_prompt_config_validation(self):
        from app.services.prompt_loader import PromptConfig
        
        data = {
            "name": "Test Mode",
            "description": "A test mode",
            "system_instruction": "You are a test AI",
            "department": "R&D",
            "output_format": "markdown",
            "guidelines": ["Rule 1", "Rule 2"]
        }
        
        config = PromptConfig(**data)
        assert config.name == "Test Mode"
        assert config.department == "R&D"
        assert len(config.guidelines) == 2


class TestPromptLoader:
    """Test the PromptLoader service"""

    @pytest.fixture
    def temp_prompts_dir(self):
        """Create a temporary directory with mock prompts"""
        temp_dir = Path(tempfile.mkdtemp())
        
        # Create a sample prompt file
        bug_report = {
            "name": "Bug Report",
            "description": "Analyze bugs in $project_name",
            "system_instruction": "You are a QA engineer. Context: {meeting_title}.",
            "department": "R&D",
            "guidelines": ["Check {keywords} thoroughly"]
        }
        
        with open(temp_dir / "bug_report.yaml", "w") as f:
            yaml.dump(bug_report, f)
            
        yield temp_dir
        
        shutil.rmtree(temp_dir)

    def test_loader_initialization(self, temp_prompts_dir):
        from app.services.prompt_loader import PromptLoader
        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        assert loader.prompts_dir == temp_prompts_dir

    def test_list_available_modes(self, temp_prompts_dir):
        from app.services.prompt_loader import PromptLoader
        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        modes = loader.list_available_modes()
        assert "bug_report" in modes
        assert len(modes) == 1

    def test_load_prompt_no_context(self, temp_prompts_dir):
        from app.services.prompt_loader import PromptLoader
        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        config = loader.load_prompt("bug_report")
        
        assert config.name == "Bug Report"
        assert config.system_instruction == "You are a QA engineer. Context: {meeting_title}."

    def test_load_prompt_with_context(self, temp_prompts_dir):
        from app.services.prompt_loader import PromptLoader
        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        
        context = {
            "project_name": "DevLens",
            "meeting_title": "Daily Standup",
            "keywords": "login flow"
        }
        
        config = loader.load_prompt("bug_report", context=context)
        
        assert "Analyze bugs in DevLens" in config.description
        assert "Context: Daily Standup" in config.system_instruction
        assert "Check login flow thoroughly" in config.guidelines[0]

    def test_load_nonexistent_prompt(self, temp_prompts_dir):
        from app.services.prompt_loader import PromptLoader, PromptLoadError
        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        
        with pytest.raises(PromptLoadError):
            loader.load_prompt("nonexistent_mode")

    def test_get_modes_metadata(self, temp_prompts_dir):
        from app.services.prompt_loader import PromptLoader
        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        
        metadata = loader.get_modes_metadata()
        assert len(metadata) == 1
        assert metadata[0]["mode"] == "bug_report"
        assert metadata[0]["name"] == "Bug Report"

    def test_clear_cache(self, temp_prompts_dir):
        from app.services.prompt_loader import PromptLoader
        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        
        # Load once to populate cache
        loader.load_prompt("bug_report")
        assert "bug_report" in loader._cache
        
        loader.clear_cache()
        assert len(loader._cache) == 0


class TestPromptLoaderSingleton:
    """Test the singleton pattern for PromptLoader"""
    
    def test_get_prompt_loader(self):
        from app.services.prompt_loader import get_prompt_loader
        
        loader1 = get_prompt_loader()
        loader2 = get_prompt_loader()
        
        assert loader1 is loader2
