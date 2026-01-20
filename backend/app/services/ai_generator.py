"""AI documentation generation service using Google Gemini"""

import google.generativeai as genai
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging
import json
import re

from app.core.config import settings
from app.core.observability import trace_pipeline, record_event, EventType

logger = logging.getLogger(__name__)


class AIGenerationError(Exception):
    """Custom exception for AI generation errors"""
    pass


class DocumentationGenerator:
    """Service for generating documentation using Google Gemini"""
    
    def __init__(self):
        """Initialize the Gemini API clients"""
        try:
            genai.configure(api_key=settings.gemini_api_key)
            
            # Use configurable model names
            pro_model = getattr(settings, 'doc_model_pro_name', 'gemini-2.5-flash-lite')
            flash_model = getattr(settings, 'doc_model_flash_name', 'gemini-2.5-flash-lite')
            
            self.model_pro = genai.GenerativeModel(pro_model)
            self.model_flash = genai.GenerativeModel(flash_model)
            
            logger.info(f"Gemini API initialized: Pro={pro_model}, Flash={flash_model}")
        except Exception as e:
            raise AIGenerationError(f"Failed to initialize Gemini API: {str(e)}")
    
    
    def _analyze_multimodal_fast(self, video_file, context_keywords: List[str] = None):
        """
        Internal method to analyze video proxy with Gemini Flash.
        Uses multimodal understanding to find technical segments and quality frames.
        """
        keywords_str = ", ".join(context_keywords) if context_keywords else "general technical content"
        prompt = f"""
        Analyze this video demonstration. 
        1. Identify segments where TECHNICAL content related to "{keywords_str}" is discussed or shown.
        2. Within those segments, identify the EXACT timestamps for high-quality screenshots.
        3. Visual Quality Control: NEVER select a frame that shows a blank/white screen, a loading spinner, or a blurred transition.
        4. If a key moment happens during a loading state, look forward/backward by 2-3 seconds to find the fully rendered UI.
        
        Return STRICTLY JSON:
        {{
          "relevant_segments": [
            {{
              "start": float,
              "end": float,
              "reason": "string",
              "key_timestamps": [float, float]
            }}
          ],
          "technical_percentage": float
        }}
        """
        
        response = self.model_flash.generate_content(
            [video_file, prompt],
            generation_config=genai.GenerationConfig(
                temperature=0.1,
                top_p=0.95,
                max_output_tokens=2048,
                response_mime_type="application/json"
            )
        )
        return response

    @trace_pipeline
    def analyze_video_relevance(
        self,
        video_path: str,
        context_keywords: List[str],
        audio_path: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Analyze video/audio to identify relevant segments and key timestamps.
        
        Uses FastSTT for local transcription when available, with fallback to
        Gemini multimodal analysis.
        """
        try:
            # Try Fast STT path if audio is available and STT is enabled
            if audio_path and settings.fast_stt_enabled:
                try:
                    from app.services.stt_fast_service import get_fast_stt_service
                    stt_service = get_fast_stt_service()
                    
                    if stt_service.is_available:
                        stt_result = stt_service.transcribe_video(audio_path)
                        
                        # Log STT metrics
                        logger.info(
                            f"STT: {stt_result.model_used}, "
                            f"{stt_result.segment_count} segments, "
                            f"{stt_result.processing_time_ms:.0f}ms"
                        )
                        
                        # If we have segments, use text-based relevance analysis
                        if stt_result.segments:
                            return self._analyze_text_relevance(
                                stt_result, 
                                context_keywords
                            )
                except ImportError:
                    logger.warning("FastSttService not available, using video analysis")
                except Exception as e:
                    logger.warning(f"Fast STT failed, falling back to video analysis: {e}")
            
            # Fall back to multimodal video analysis
            logger.info(f"Performing multimodal analysis on: {video_path}")
            
            # Upload video file (Gemini handles video files directly)
            logger.info("Uploading video proxy to Gemini Flash...")
            video_file = genai.upload_file(video_path)
            
            # Wait for file to be processed if needed (Gemini backend async)
            # For small proxies it's usually fast, but let's be safe
            import time
            while video_file.state.name == "PROCESSING":
                time.sleep(1)
                video_file = genai.get_file(video_file.name)
            
            if video_file.state.name == "FAILED":
                raise AIGenerationError(f"Video file processing failed: {video_file.name}")

            # Call internal analysis method
            logger.info("Analyzing video with Gemini Flash (Multimodal)...")
            response = self._analyze_multimodal_fast(video_file, context_keywords)
            
            if not response.text:
                raise AIGenerationError("Gemini Flash returned empty response")
            
            # Parse JSON response
            try:
                result = json.loads(response.text)
                segments = result.get("relevant_segments", [])
                logger.info(f"Found {len(segments)} relevant segments via multimodal analysis")
                
                return segments
            
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {response.text}")
                raise AIGenerationError(f"Invalid JSON from video analysis: {str(e)}")
        
        except Exception as e:
            logger.error(f"Video analysis failed: {str(e)}")
            raise AIGenerationError(f"Failed to analyze video proxy: {str(e)}")
    
    def _analyze_text_relevance(
        self,
        stt_result: 'SttResult',
        context_keywords: List[str],
        session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Analyze STT transcript text to identify relevant segments.
        Uses Gemini Flash for text-based relevance scoring - much faster than video.
        """
        from app.services.stt_fast_service import SttResult
        
        # Get condensed summary for Gemini
        summary_text = stt_result.get_text_summary(max_tokens=500)
        keywords_str = ", ".join(context_keywords) if context_keywords else "general technical content"
        
        prompt = f"""
You are analyzing a video transcript to find relevant technical segments.
The video contains discussion about: {keywords_str}

TRANSCRIPT (with timestamps):
{summary_text}

Identify the time ranges where TECHNICAL content related to "{keywords_str}" is discussed.
For each relevant segment, suggest key_timestamps for screenshot extraction.

Return STRICTLY JSON:
{{
  "relevant_segments": [
    {{
      "start": float,
      "end": float,
      "reason": "string",
      "key_timestamps": [float, float]
    }}
  ],
  "technical_percentage": float
}}
"""
        
        response = self.model_flash.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.1,
                top_p=0.95,
                max_output_tokens=2048,
                response_mime_type="application/json"
            )
        )
        
        try:
            result = json.loads(response.text)
            segments = result.get("relevant_segments", [])
            logger.info(f"Found {len(segments)} relevant segments via text analysis (Fast STT)")
            
            # Log AGENT_NOTE turns for each relevant segment
            if session_id and segments:
                self._log_agent_notes(session_id, segments, keywords_str)
            
            return segments
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse text analysis response: {response.text}")
            raise AIGenerationError(f"Invalid JSON from text analysis: {str(e)}")
    
    @trace_pipeline
    def generate_documentation(
        self,
        frame_paths: List[str],
        prompt_config: Optional['PromptConfig'] = None,
        context: str = "",
        project_name: str = "Project",
        audio_transcript: Optional[str] = None,
        session_id: Optional[str] = None,
        system_instruction: Optional[str] = None,
        user_prompt: Optional[str] = None,
        model_name: str = "pro"
    ) -> str:
        """
        Generate technical documentation from video frames using dynamic prompts.
        
        Args:
            frame_paths: List of paths to extracted frame images
            prompt_config: PromptConfig object (optional if system_instruction provided)
            context: Optional organizational context from RAG
            project_name: Name of the project being documented
            audio_transcript: Optional audio transcript to include
            system_instruction: content for system prompt (overrides prompt_config)
            user_prompt: content for user prompt (overrides default construction)
            model_name: "pro" or "flash" (default: "pro")
        
        Returns:
            Generated Markdown documentation
        
        Raises:
            AIGenerationError: If generation fails
        """
        try:
            logger.info(f"Generating documentation for {project_name} with {len(frame_paths)} frames")
            # Determine system instruction
            sys_instr = system_instruction
            if not sys_instr and prompt_config:
                sys_instr = prompt_config.system_instruction
            
            if not sys_instr:
                raise AIGenerationError("No system instruction provided (neither explicit nor in prompt_config)")

            # Prepare the user prompt
            final_user_prompt = ""
            
            if user_prompt:
                final_user_prompt = user_prompt
            else:
                final_user_prompt = f"# Documentation Request\n\n"
                final_user_prompt += f"**Project:** {project_name}\n\n"
                
                if context:
                    final_user_prompt += f"**Organizational Context:**\n{context}\n\n"
                
                if audio_transcript:
                    final_user_prompt += f"**Audio Transcript:**\n{audio_transcript}\n\n"
                
                final_user_prompt += f"**Visual Frames:** {len(frame_paths)} screenshots from a video demonstration.\n\n"
                final_user_prompt += "Please analyze the frames"
                if audio_transcript:
                    final_user_prompt += " and transcript"
                final_user_prompt += " and create documentation according to your instructions.\n"
            
            # Upload frames
            uploaded_files = []
            for i, frame_path in enumerate(frame_paths):
                try:
                    file = genai.upload_file(frame_path)
                    uploaded_files.append(file)
                    logger.debug(f"Uploaded frame {i + 1}/{len(frame_paths)}")
                except Exception as e:
                    logger.warning(f"Failed to upload frame {frame_path}: {str(e)}")
            
            if not uploaded_files:
                raise AIGenerationError("Failed to upload any frames to Gemini")
            
            # Construct the full prompt
            prompt_parts = [sys_instr, final_user_prompt]
            prompt_parts.extend(uploaded_files)
            
            # Select model
            model = self.model_pro if model_name == "pro" else self.model_flash
            
            # Generate content
            logger.info(f"Sending generation request to Gemini {model_name}...")
            response = model.generate_content(
                prompt_parts,
                generation_config=genai.GenerationConfig(
                    temperature=0.4,
                    top_p=0.95,
                    top_k=40,
                    max_output_tokens=8192,
                )
            )
            
            # Extract text from response
            if not response.text:
                raise AIGenerationError("Gemini returned empty response")
            
            raw_text = response.text
            logger.info(f"Successfully generated {len(raw_text)} characters of documentation")
            
            # Get raw response
            documentation = response.text.strip()

            # CRITICAL: Strip markdown fences before further processing
            documentation = self.strip_markdown_fences(documentation)
            logger.info(f"🧹 After stripping fences: {len(documentation)} chars")

            # Validate JSON (don't fail - just log)
            try:
                parsed = json.loads(documentation)
                item_count = len(parsed) if isinstance(parsed, list) else 1
                logger.info(f"✅ Valid JSON detected: {item_count} items")
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ Content is not JSON (might be Markdown): {e}")
            logger.info(f"Cleaned documentation: {len(documentation)} characters")
            
            # --- Post-Processing: Embed Images ---
            # Replace [Frame X] with actual image Markdown
            
            def _get_web_url(local_path: str) -> str:
                try:
                    rel_path = Path(local_path).relative_to(settings.get_upload_path().resolve())
                    return f"/uploads/{rel_path.as_posix()}"
                except ValueError:
                    # Try non-resolved path too
                    try:
                        rel_path = Path(local_path).relative_to(settings.get_upload_path())
                        return f"/uploads/{rel_path.as_posix()}"
                    except ValueError:
                        return f"/uploads/{Path(local_path).name}"

            def replace_match(match):
                try:
                    idx = int(match.group(1)) - 1 # 1-based index to 0-based
                    if 0 <= idx < len(frame_paths):
                        url = _get_web_url(frame_paths[idx])
                        return f"![Frame {idx+1}]({url})"
                except Exception:
                    pass
                return match.group(0)

            # Replace [Frame X] patterns
            documentation = re.sub(r'\[Frame (\d+)\]', replace_match, documentation)
            
            logger.info(f"Final output: {len(documentation)} characters")
            
            # Log DOC_SECTION turn if session_id provided
            if session_id:
                self._log_doc_section(
                    session_id=session_id,
                    section_markdown=documentation,
                    heading=f"{project_name} Full Document",
                    segment_ids=[]
                )
            
            return documentation
        
        except Exception as e:
            logger.error(f"Documentation generation failed: {str(e)}")
            raise AIGenerationError(f"Failed to generate documentation: {str(e)}")

    @staticmethod
    def strip_markdown_fences(text: str) -> str:
        """
        Remove markdown code fences from Gemini JSON responses.
        
        DevLens pattern: Handle cases where Gemini wraps JSON in ```json blocks
        despite being instructed not to.
        """
        s = text.strip()
        
        # Check if wrapped in code fences
        if s.startswith("```"):
            lines = s.splitlines()
            
            # Remove first line (```json or ```)
            if lines:
                lines = lines[1:]
            
            # Remove last line (```)
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            
            s = "\n".join(lines)
        
        return s.strip()

    def _strip_markdown_codeblocks(self, text: str) -> str:
        """
        Remove markdown code block formatting.
        
        Handles:
        - ```json\n...\n```
        - ```\n...\n```
        - ` ` (inline code)
        
        Returns:
            Clean text without markdown
        """
        return self.strip_markdown_fences(text)
    
    def generate_segment_doc(
        self,
        segment: Dict[str, Any],
        frame_paths: List[str],
        prompt_config: 'PromptConfig',
        project_name: str = "Project",
        audio_summary: Optional[str] = None
    ) -> str:
        """
        Generate documentation for a single video segment (chunk).
        
        Args:
            segment: Segment descriptor with start, end, index
            frame_paths: List of frame paths for this segment
            prompt_config: PromptConfig object with system instructions
            project_name: Name of the project
            audio_summary: Optional audio transcript/summary for segment
        
        Returns:
            Generated Markdown for this segment only
        
        Raises:
            AIGenerationError: If generation fails
        """
        try:
            seg_start = segment.get("start", 0)
            seg_end = segment.get("end", 0)
            seg_index = segment.get("index", 0)
            
            logger.info(f"Generating doc for segment {seg_index} ({seg_start:.1f}s - {seg_end:.1f}s) with {len(frame_paths)} frames")
            
            # Build segment-specific prompt
            user_prompt = f"# Segment {seg_index + 1} Documentation\n\n"
            user_prompt += f"**Project:** {project_name}\n"
            user_prompt += f"**Time Range:** {seg_start:.1f}s - {seg_end:.1f}s\n\n"
            
            if audio_summary:
                user_prompt += f"**Audio Summary:**\n{audio_summary}\n\n"
            
            user_prompt += f"**Visual Frames:** {len(frame_paths)} screenshots from this segment.\n\n"
            user_prompt += "Please analyze the frames and document what's shown in this segment.\n"
            user_prompt += "Focus on the key actions, UI elements, and any important details visible.\n"
            
            # Upload frames
            uploaded_files = []
            for i, frame_path in enumerate(frame_paths):
                try:
                    file = genai.upload_file(frame_path)
                    uploaded_files.append(file)
                except Exception as e:
                    logger.warning(f"Failed to upload frame {frame_path}: {str(e)}")
            
            if not uploaded_files:
                # Return placeholder if no frames uploaded
                return f"## Segment {seg_index + 1} ({seg_start:.1f}s - {seg_end:.1f}s)\n\n*No frames available for this segment.*\n\n"
            
            # Construct prompt with system instruction
            prompt_parts = [prompt_config.system_instruction, user_prompt]
            prompt_parts.extend(uploaded_files)
            
            # Generate with Flash model for speed (segments are smaller)
            response = self.model_flash.generate_content(
                prompt_parts,
                generation_config=genai.GenerationConfig(
                    temperature=0.3,
                    top_p=0.95,
                    max_output_tokens=4096,
                )
            )
            
            if not response.text:
                return f"## Segment {seg_index + 1}\n\n*No content generated.*\n\n"
            
            segment_doc = response.text.strip()
            
            # Post-process: Replace [Frame X] with actual images
            def _get_web_url(local_path: str) -> str:
                try:
                    rel_path = Path(local_path).relative_to(settings.get_upload_path().resolve())
                    return f"/uploads/{rel_path.as_posix()}"
                except ValueError:
                    try:
                        rel_path = Path(local_path).relative_to(settings.get_upload_path())
                        return f"/uploads/{rel_path.as_posix()}"
                    except ValueError:
                        return f"/uploads/{Path(local_path).name}"

            def replace_match(match):
                try:
                    idx = int(match.group(1)) - 1
                    if 0 <= idx < len(frame_paths):
                        url = _get_web_url(frame_paths[idx])
                        return f"![Frame {idx+1}]({url})"
                except Exception:
                    pass
                return match.group(0)

            segment_doc = re.sub(r'\[Frame (\d+)\]', replace_match, segment_doc)
            
            logger.info(f"Generated {len(segment_doc)} characters for segment {seg_index}")
            
            return segment_doc
        
        except Exception as e:
            logger.error(f"Segment doc generation failed: {str(e)}")
            raise AIGenerationError(f"Failed to generate segment documentation: {str(e)}")
    
    def merge_segments(
        self,
        segment_docs: List[Dict[str, Any]],
        project_name: str = "Project"
    ) -> str:
        """
        Merge segment documentations into a cohesive final document.
        
        Args:
            segment_docs: List of [{"index": 0, "doc": "...", "start": 0, "end": 30}, ...]
            project_name: Project name for the header
        
        Returns:
            Merged Markdown documentation
        """
        if not segment_docs:
            return "# Documentation\n\n*No content generated.*\n"
        
        # Sort by index
        sorted_docs = sorted(segment_docs, key=lambda x: x.get("index", 0))
        
        # Build merged document
        merged = f"# {project_name} Documentation\n\n"
        merged += f"*Generated from {len(sorted_docs)} video segments*\n\n"
        merged += "---\n\n"
        
        for seg in sorted_docs:
            seg_index = seg.get("index", 0)
            seg_start = seg.get("start", 0)
            seg_end = seg.get("end", 0)
            doc = seg.get("doc", "")
            
            # Add segment header
            merged += f"## Part {seg_index + 1} ({seg_start:.0f}s - {seg_end:.0f}s)\n\n"
            
            # Add segment content (strip duplicate headers if any)
            content = doc.strip()
            # Remove any leading # headers since we add our own
            lines = content.split("\n")
            if lines and lines[0].startswith("#"):
                lines = lines[1:]
            content = "\n".join(lines).strip()
            
            merged += content + "\n\n"
            merged += "---\n\n"
        
        logger.info(f"Merged {len(sorted_docs)} segments into {len(merged)} character document")
        
        return merged
    
    def _log_agent_notes(self, session_id: str, segments: List[Dict], keywords: str) -> None:
        """Log AGENT_NOTE turns for relevant segments identified during analysis."""
        try:
            from app.services.turn_log_service import get_turn_log_service, SessionTurn, TurnType
            
            turn_log = get_turn_log_service()
            for i, seg in enumerate(segments):
                turn = SessionTurn(
                    session_id=session_id,
                    type=TurnType.AGENT_NOTE,
                    segment_id=f"rel_{i}",
                    start=seg.get("start"),
                    end=seg.get("end"),
                    text=seg.get("reason", "Identified as relevant"),
                    metadata={
                        "keywords": keywords,
                        "key_timestamps": seg.get("key_timestamps", [])
                    }
                )
                turn_log.append_turn(turn)
            
            logger.info(f"Logged {len(segments)} AGENT_NOTE turns for session {session_id}")
        except Exception as e:
            logger.warning(f"Failed to log agent notes: {e}")
    
    def _log_doc_section(self, session_id: str, section_markdown: str, heading: str, segment_ids: List[str] = None) -> None:
        """Log a DOC_SECTION turn for generated documentation."""
        try:
            from app.services.turn_log_service import get_turn_log_service, SessionTurn, TurnType
            
            turn_log = get_turn_log_service()
            turn = SessionTurn(
                session_id=session_id,
                type=TurnType.DOC_SECTION,
                markdown=section_markdown[:2000],  # Truncate to avoid huge logs
                metadata={
                    "heading": heading,
                    "segment_ids": segment_ids or [],
                    "char_count": len(section_markdown)
                }
            )
            turn_log.append_turn(turn)
            
            logger.debug(f"Logged DOC_SECTION turn: {heading}")
        except Exception as e:
            logger.warning(f"Failed to log doc section: {e}")


# Singleton instance
_generator: Optional[DocumentationGenerator] = None


def get_generator() -> DocumentationGenerator:
    """Get or create the documentation generator singleton"""
    global _generator
    if _generator is None:
        _generator = DocumentationGenerator()
    return _generator
