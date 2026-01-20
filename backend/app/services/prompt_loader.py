"""Dynamic prompt loading service for DevLens AI"""

import yaml
from pathlib import Path
from typing import Dict, Optional
from string import Template
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)


class PromptConfig(BaseModel):
    """Configuration model for AI prompts"""
    name: str = Field(..., description="Display name of the prompt mode")
    description: str = Field(..., description="Description of what this mode does")
    department: str = Field(default="R&D", description="Department this mode belongs to (R&D, HR, Finance)")
    system_instruction: Optional[str] = Field(None, description="System instruction for the AI")
    system_prompt: Optional[str] = Field(None, description="Alias for system_instruction")
    user_prompt: Optional[str] = Field(None, description="User prompt template")
    output_format: str = Field(default="markdown", description="Expected output format")
    guidelines: list[str] = Field(default_factory=list, description="Additional guidelines")

    def __init__(self, **data):
        # Allow system_prompt alias for system_instruction
        if 'system_prompt' in data and not data.get('system_instruction'):
            data['system_instruction'] = data['system_prompt']
        super().__init__(**data)


class PromptLoadError(Exception):
    """Custom exception for prompt loading errors"""
    pass


class PromptLoader:
    """Service for loading AI prompts from YAML configuration files"""
    
    def __init__(self, prompts_dir: Optional[Path] = None):
        """
        Initialize the PromptLoader.
        
        Args:
            prompts_dir: Directory containing prompt YAML files.
                        Defaults to backend/prompts/
        """
        if prompts_dir is None:
            # Default to backend/prompts/ relative to this file
            current_file = Path(__file__)
            # Adjust path: app/services/prompt_loader.py -> app/services -> app -> backend -> backend/prompts
            self.prompts_dir = current_file.parent.parent.parent / "prompts"
        else:
            self.prompts_dir = Path(prompts_dir)
        
        # Cache for loaded prompts
        self._cache: Dict[str, PromptConfig] = {}
        
        logger.info(f"PromptLoader initialized with directory: {self.prompts_dir}")
    
    def load_prompt(self, mode: str, context: Optional[Dict[str, str]] = None) -> PromptConfig:
        """
        Load a prompt configuration by mode name with optional context interpolation.
        
        Args:
            mode: Name of the prompt mode (e.g., 'bug_report', 'feature_spec')
            context: Optional dictionary of context variables to interpolate
        
        Returns:
            PromptConfig object with the loaded configuration
        
        Raises:
            PromptLoadError: If the prompt file doesn't exist or is invalid
        """
        # Check cache first (without context interpolation)
        cache_key = mode
        if cache_key in self._cache and context is None:
            logger.debug(f"Returning cached prompt for mode: {mode}")
            return self._cache[cache_key]
        
        # Construct file path
        prompt_file = self.prompts_dir / f"{mode}.yaml"
        
        if not prompt_file.exists():
            available_modes = self.list_available_modes()
            raise PromptLoadError(
                f"Prompt mode '{mode}' not found. "
                f"Available modes: {', '.join(available_modes)}"
            )
        
        try:
            # Load YAML file
            with open(prompt_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            # Apply context interpolation if provided
            if context:
                data = self._interpolate_context(data, context)
            
            # Validate and create PromptConfig
            prompt_config = PromptConfig(**data)
            
            # Cache the result (only if no context)
            if context is None:
                self._cache[cache_key] = prompt_config
            
            logger.info(f"Loaded prompt mode: {mode} - {prompt_config.name}")
            
            return prompt_config
        
        except yaml.YAMLError as e:
            raise PromptLoadError(f"Invalid YAML in {prompt_file}: {str(e)}")
        except Exception as e:
            raise PromptLoadError(f"Failed to load prompt {mode}: {str(e)}")
    
    def _interpolate_context(self, data: Dict, context: Dict[str, str]) -> Dict:
        """
        Interpolate context variables into prompt data.
        
        Replaces placeholders like {meeting_title}, {attendees}, {keywords} in the
        system_instruction and other string fields.
        
        Args:
            data: Prompt data dictionary
            context: Context variables to interpolate
        
        Returns:
            Data dictionary with interpolated values
        """
        def interpolate_string(s: str) -> str:
            """Interpolate a single string using safe_substitute to avoid crashes."""
            # Convert {var} syntax to $var for Template
            # This handles cases where prompts contain {} for JSON examples
            import re
            # Only convert {word} patterns, not arbitrary {}
            template_str = re.sub(r'\{(\w+)\}', r'$\1', s)
            try:
                return Template(template_str).safe_substitute(**context)
            except Exception as e:
                logger.warning(f"Template substitution failed: {e}")
                return s
        
        # Interpolate system_instruction
        if 'system_instruction' in data and isinstance(data['system_instruction'], str):
            data['system_instruction'] = interpolate_string(data['system_instruction'])
        
        # Interpolate description
        if 'description' in data and isinstance(data['description'], str):
            data['description'] = interpolate_string(data['description'])
        
        # Interpolate guidelines
        if 'guidelines' in data and isinstance(data['guidelines'], list):
            data['guidelines'] = [
                interpolate_string(g) if isinstance(g, str) else g
                for g in data['guidelines']
            ]
        
        return data
    
    def list_available_modes(self) -> list[str]:
        """
        List all available prompt modes.
        
        Returns:
            List of mode names (without .yaml extension)
        """
        if not self.prompts_dir.exists():
            logger.warning(f"Prompts directory does not exist: {self.prompts_dir}")
            return []
        
        modes = []
        for file in self.prompts_dir.glob("*.yaml"):
            modes.append(file.stem)
        
        return sorted(modes)
    
    def get_modes_metadata(self) -> list[Dict[str, str]]:
        """
        Get metadata for all available prompt modes.
        
        Returns:
            List of dictionaries with mode, name, and description
        """
        metadata = []
        
        for mode in self.list_available_modes():
            try:
                config = self.load_prompt(mode)
                metadata.append({
                    "mode": mode,
                    "name": config.name,
                    "description": config.description
                })
            except PromptLoadError as e:
                logger.error(f"Failed to load metadata for mode {mode}: {str(e)}")
        
        return metadata
    
    def clear_cache(self):
        """Clear the prompt cache. Useful for development/testing."""
        self._cache.clear()
        logger.info("Prompt cache cleared")


# Singleton instance
_loader: Optional[PromptLoader] = None


def get_prompt_loader() -> PromptLoader:
    """Get or create the PromptLoader singleton"""
    global _loader
    if _loader is None:
        _loader = PromptLoader()
    return _loader
