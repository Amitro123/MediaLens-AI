import pytest
import sys
import os

# Add backend to path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.ai_generator import DocumentationGenerator as AIGenerator

def test_strip_markdown_fences():
    """Test markdown fence stripping."""
    # Since AIGenerator is a class but methods inside might be instance methods, 
    # but I made strip_markdown_fences static. Let's check how to invoke it.
    # The user instruction was @staticmethod.
    
    # Test with JSON fences
    input_fenced = '```json\n[{"scene": 1}]\n```'
    output = AIGenerator.strip_markdown_fences(input_fenced)
    assert output == '[{"scene": 1}]'
    assert output.startswith('[')
    assert not output.startswith('```')
    
    # Test without fences
    input_raw = '[{"scene": 1}]'
    output = AIGenerator.strip_markdown_fences(input_raw)
    assert output == '[{"scene": 1}]'
    
    # Test with language tag
    input_lang = '```json\n{"test": true}\n```'
    output = AIGenerator.strip_markdown_fences(input_lang)
    assert output == '{"test": true}'
    
    # Test with plain markdown fences
    input_plain = '```\n{"data": 123}\n```'
    output = AIGenerator.strip_markdown_fences(input_plain)
    assert output == '{"data": 123}'


def test_parse_scene_documentation():
    """Test complete JSON parsing flow."""
    import json
    
    # Simulate Gemini response with fences
    gemini_response = '''```json
[
  {
    "scene_number": 1,
    "timestamp": "00:00 - 00:15",
    "location": "Office",
    "visual_description": "Person at desk"
  },
  {
    "scene_number": 2,
    "timestamp": "00:15 - 00:30",
    "location": "Kitchen",
    "visual_description": "Making coffee"
  }
]
```'''
    
    # Strip fences
    cleaned = AIGenerator.strip_markdown_fences(gemini_response)
    
    # Parse JSON
    scenes = json.loads(cleaned)
    
    assert isinstance(scenes, list)
    assert len(scenes) == 2
    assert scenes[0]["scene_number"] == 1
    assert scenes[1]["location"] == "Kitchen"
