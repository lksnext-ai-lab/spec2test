import base64
import hashlib
import os
import re
import shutil
import subprocess
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional
import PyPDF2
import csv
from io import StringIO
import cv2
import numpy as np

from langchain_core.messages import HumanMessage
from langchain.chat_models import init_chat_model
from pdf_preprocessor import PdfPreprocessor

_DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"
_DEFAULT_DEEPSEEK_MODEL = "deepseek-v4-flash"

class FileProcessor:
    def __init__(self, input_dir: str = "/app/inputs/", cache_dir: str = "/app/inputs/.cache/"):
        self.input_dir = Path(input_dir)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        self.provider = os.environ.get("INPUT_PROCESSOR_PROVIDER", "google_genai")
        
        # Validate API keys and resolve default model
        if self.provider == "openai" and "OPENAI_API_KEY" not in os.environ:
            raise ValueError("OPENAI_API_KEY environment variable is not set.")
        elif self.provider == "anthropic" and "ANTHROPIC_API_KEY" not in os.environ:
            raise ValueError("ANTHROPIC_API_KEY environment variable is not set.")
        elif self.provider == "google_genai" and "GOOGLE_API_KEY" not in os.environ:
            raise ValueError("GOOGLE_API_KEY environment variable is not set.")
        elif self.provider == "deepseek" and "DEEPSEEK_API_KEY" not in os.environ:
            raise ValueError("DEEPSEEK_API_KEY environment variable is not set.")
        elif self.provider == "openrouter" and "OPENROUTER_API_KEY" not in os.environ:
            raise ValueError("OPENROUTER_API_KEY environment variable is not set.")

        model = os.environ.get("INPUT_PROCESSOR_MODEL")
        if not model:
            if self.provider == "deepseek":
                model = _DEFAULT_DEEPSEEK_MODEL
            else:
                model = _DEFAULT_GEMINI_MODEL

        # DeepSeek and OpenRouter use the OpenAI-compatible protocol with custom base URLs
        if self.provider == "deepseek":
            self.llm = init_chat_model(
                model,
                model_provider="openai",
                base_url="https://api.deepseek.com/v1",
                api_key=os.environ["DEEPSEEK_API_KEY"],
                temperature=0,
                max_tokens=None,
                timeout=None,
                max_retries=2,
            )
        elif self.provider == "openrouter":
            self.llm = init_chat_model(
                model,
                model_provider="openai",
                base_url="https://openrouter.ai/api/v1",
                api_key=os.environ["OPENROUTER_API_KEY"],
                temperature=0,
                max_tokens=None,
                timeout=None,
                max_retries=2,
            )
        else:
            self.llm = init_chat_model(
                model,
                model_provider=self.provider,
                temperature=0,
                max_tokens=None,
                timeout=None,
                max_retries=2,
            )

        pdf_provider = None
        pdf_api_key = None
        if self.provider == "openrouter" and "OPENROUTER_API_KEY" in os.environ:
            pdf_provider = "openrouter"
            pdf_api_key = os.environ["OPENROUTER_API_KEY"]
        elif "GOOGLE_API_KEY" in os.environ:
            pdf_provider = "google_genai"
            pdf_api_key = os.environ["GOOGLE_API_KEY"]

        if pdf_provider and pdf_api_key:
            gemini_model = (
                os.environ.get("INPUT_PROCESSOR_MODEL", _DEFAULT_GEMINI_MODEL)
                if self.provider in {"google_genai", "openrouter"}
                else _DEFAULT_GEMINI_MODEL
            )
            self.pdf_preprocessor = PdfPreprocessor(
                api_key=pdf_api_key,
                model=gemini_model,
                provider=pdf_provider,
            )
        else:
            self.pdf_preprocessor = None
            print(
                "Warning: GOOGLE_API_KEY/OPENROUTER_API_KEY not set. "
                "PDF and Markdown image preprocessing with PyMuPDF4LLM+Gemini is disabled."
            )

        self.supported_formats = {'.mp4', '.pdf', '.md', '.txt'}
    
    def get_file_hash(self, file_path: Path) -> str:
        """Generate SHA-256 hash of file content"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def is_processed(self, file_hash: str) -> bool:
        """Check if file is already processed"""
        cache_file = self.cache_dir / f"{file_hash}.txt"
        return cache_file.exists()
    
    def _ensure_str(self, content: Any) -> str:
        """Convert LLM content blocks to plain text."""
        if isinstance(content, str):
            return content.strip()
        elif isinstance(content, dict):
            if isinstance(content.get("text"), str):
                return content["text"].strip()
            if "content" in content:
                return self._ensure_str(content["content"])
            return str(content)
        elif isinstance(content, list):
            parts = [self._ensure_str(item) for item in content]
            return "\n".join(part for part in parts if part).strip()
        else:
            return str(content).strip()
    
    def extract_frames(self, video_path: Path, interval_seconds: int = 2) -> List[str]:
        """Extract frames from video at given interval, return as base64 strings"""
        video = cv2.VideoCapture(str(video_path))
        base64_frames = []
        
        if not video.isOpened():
            print(f"Error: Could not open video file {video_path}")
            return []

        fps = video.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30 # Default fallback
            
        frame_interval = int(fps * interval_seconds)
        if frame_interval == 0:
            frame_interval = 1
        
        count = 0
        while video.isOpened():
            ret, frame = video.read()
            if not ret:
                break
                
            if count % frame_interval == 0:
                # Resize to reduce size (max dimension 480px)
                height, width = frame.shape[:2]
                if width > 480:
                    scale = 480 / width
                    new_height = int(height * scale)
                    frame = cv2.resize(frame, (480, new_height))
                
                # Compress as JPEG with lower quality
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 70]
                _, buffer = cv2.imencode(".jpg", frame, encode_param)
                base64_frame = base64.b64encode(buffer).decode("utf-8")
                base64_frames.append(base64_frame)
            
            count += 1
            
        video.release()
        return base64_frames

    def _get_env_int(self, key: str, default: int) -> int:
        value = os.environ.get(key)
        if not value:
            return default
        try:
            return int(value)
        except ValueError:
            return default

    def _get_env_float(self, key: str, default: float) -> float:
        value = os.environ.get(key)
        if not value:
            return default
        try:
            return float(value)
        except ValueError:
            return default

    def _format_mmss(self, seconds: int) -> str:
        mm = seconds // 60
        ss = seconds % 60
        return f"{mm}:{ss:02d}"

    def _get_video_duration_seconds(self, video_path: Path) -> int:
        video = cv2.VideoCapture(str(video_path))
        if not video.isOpened():
            return 0
        fps = video.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30
        total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
        video.release()
        if total_frames <= 0:
            return 0
        return int(round(total_frames / fps))

    def _offset_timestamps(self, text: str, offset_seconds: int) -> str:
        pattern = re.compile(r"\((\d{1,2}):(\d{2})(?:\s*-\s*(\d{1,2}):(\d{2}))?\)")

        def _shift(match: re.Match) -> str:
            start = int(match.group(1)) * 60 + int(match.group(2)) + offset_seconds
            start_str = f"{start // 60}:{start % 60:02d}"
            if match.group(3) is not None:
                end = int(match.group(3)) * 60 + int(match.group(4)) + offset_seconds
                end_str = f"{end // 60}:{end % 60:02d}"
                return f"({start_str}-{end_str})"
            return f"({start_str})"

        return pattern.sub(_shift, text)

    def _split_video_with_ffmpeg(self, file_path: Path, segment_dir: Path, segment_seconds: int) -> bool:
        if shutil.which("ffmpeg") is None:
            return False

        output_template = segment_dir / f"{file_path.stem}_%03d.mp4"
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(file_path),
            "-c",
            "copy",
            "-map",
            "0",
            "-f",
            "segment",
            "-segment_time",
            str(segment_seconds),
            "-reset_timestamps",
            "1",
            str(output_template),
        ]

        try:
            subprocess.run(cmd, check=True)
        except Exception as e:
            print(f"Warning: ffmpeg split failed, falling back to OpenCV: {e}")
            return False

        return True

    def _audio_required_for_splitting(self) -> bool:
        value = os.environ.get("INPUT_PROCESSOR_VIDEO_REQUIRE_AUDIO", "true").strip().lower()
        return value not in {"0", "false", "no"}

    def _split_video_with_cv2(self, file_path: Path, segment_dir: Path, segment_seconds: int) -> List[Path]:
        video = cv2.VideoCapture(str(file_path))
        if not video.isOpened():
            raise ValueError(f"Error: Could not open video file {file_path.name}")

        fps = video.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30
        frames_per_segment = max(int(fps * segment_seconds), 1)

        width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")

        segments: List[Path] = []
        writer = None
        frame_index = 0
        segment_index = 0

        print("Splitting video with OpenCV (audio will be dropped).")

        while True:
            ret, frame = video.read()
            if not ret:
                break

            if frame_index % frames_per_segment == 0:
                if writer is not None:
                    writer.release()

                segment_index += 1
                segment_path = segment_dir / f"{file_path.stem}_part{segment_index:03d}.mp4"
                writer = cv2.VideoWriter(str(segment_path), fourcc, fps, (width, height))
                if not writer.isOpened():
                    video.release()
                    raise ValueError("Failed to open video writer for segment output.")
                segments.append(segment_path)

            writer.write(frame)
            frame_index += 1

        if writer is not None:
            writer.release()
        video.release()

        if not segments:
            raise ValueError("No segments were created for the video.")

        return segments

    def _split_video_into_segments(self, file_path: Path, segment_seconds: int) -> List[Path]:
        segment_dir = self.cache_dir / "_segments" / file_path.stem
        segment_dir.mkdir(parents=True, exist_ok=True)

        for old_file in segment_dir.glob("*.mp4"):
            try:
                old_file.unlink()
            except Exception:
                pass

        if self._split_video_with_ffmpeg(file_path, segment_dir, segment_seconds):
            segments = sorted(segment_dir.glob("*.mp4"))
            if segments:
                return segments

        if self._audio_required_for_splitting():
            raise ValueError("Audio-preserving split requires ffmpeg. Install ffmpeg or disable splitting.")

        return self._split_video_with_cv2(file_path, segment_dir, segment_seconds)

    def _cleanup_segment_files(self, segments: List[Path]) -> None:
        for segment in segments:
            try:
                segment.unlink()
            except Exception:
                pass

        if segments:
            try:
                segments[0].parent.rmdir()
            except Exception:
                pass

    def _process_openrouter_video_inline(self, file_path: Path, prompt_text: str) -> str:
        with open(file_path, "rb") as video_file:
            encoded_video = base64.b64encode(video_file.read()).decode("utf-8")

        message = HumanMessage(
            content=[
                {
                    "type": "text",
                    "text": prompt_text,
                },
                {
                    "type": "video_url",
                    "video_url": {
                        "url": f"data:video/mp4;base64,{encoded_video}",
                    },
                },
            ]
        )
        response = self.llm.invoke([message])
        return self._ensure_str(response.content)

    def _build_segment_prompt(self, prompt_text: str, index: int, total: int, offset_seconds: int) -> str:
        offset = self._format_mmss(offset_seconds)
        return (
            f"{prompt_text}\n\n"
            f"Segment {index} of {total}. This segment starts at {offset} in the full video. "
            "Use timestamps relative to the segment start (MM:SS). Keep the same output structure. "
            "Only describe pages and UI elements visible in this segment."
        )

    def _consolidate_segment_summaries(self, segment_summaries: List[str]) -> str:
        merged = "\n\n".join(
            f"[Segment {index + 1}]\n{summary}" for index, summary in enumerate(segment_summaries)
        )

        consolidate = os.environ.get("INPUT_PROCESSOR_VIDEO_CONSOLIDATE", "true").strip().lower()
        if consolidate in {"0", "false", "no"}:
            return merged

        message = HumanMessage(
            content=(
                "You will be given segment summaries from a single video. "
                "Merge them into one complete, de-duplicated report with a continuous timeline.\n"
                "Requirements:\n"
                "- Keep the same headings and structure as the original prompt.\n"
                "- Preserve per-page UI inventory detail (do not collapse fields/options).\n"
                "- Present a single, chronological timeline with unified timestamps.\n"
                "- Remove duplicates and resolve overlaps.\n"
                "- Do not mention segments.\n\n"
                f"Segment summaries:\n{merged}"
            )
        )
        response = self.llm.invoke([message])
        return self._ensure_str(response.content)

    def _process_openrouter_video_split(self, file_path: Path, prompt_text: str, segment_seconds: int) -> str:
        try:
            segments = self._split_video_into_segments(file_path, segment_seconds)
        except Exception as e:
            print(f"Warning: Video split failed, processing whole file: {e}")
            return self._process_openrouter_video_inline(file_path, prompt_text)

        if not segments:
            return self._process_openrouter_video_inline(file_path, prompt_text)

        segment_summaries: List[str] = []
        offset_seconds = 0
        total_segments = len(segments)

        try:
            for index, segment_path in enumerate(segments, start=1):
                segment_prompt = self._build_segment_prompt(prompt_text, index, total_segments, offset_seconds)
                print(f"Processing segment {index}/{total_segments}: {segment_path.name}")
                summary = self._process_openrouter_video_inline(segment_path, segment_prompt)
                if offset_seconds > 0:
                    summary = self._offset_timestamps(summary, offset_seconds)
                segment_summaries.append(summary)

                duration = self._get_video_duration_seconds(segment_path)
                offset_seconds += duration if duration > 0 else segment_seconds
        finally:
            self._cleanup_segment_files(segments)

        return self._consolidate_segment_summaries(segment_summaries)

    def _analyze_video_metadata_only(self, file_path: Path) -> str:
        """Fallback video analysis for text-only providers (e.g. DeepSeek V4).
        
        DeepSeek V4 API does not support vision/multimodal inputs (as of May 2026).
        This method extracts frame-level metadata — count, timestamps, resolution
        changes — without sending image data, producing a structural timeline
        that is still useful for test-scenario generation.
        """
        video = cv2.VideoCapture(str(file_path))
        if not video.isOpened():
            return f"Error: Could not open video file {file_path.name}"

        fps = video.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30
        total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_sec = total_frames / fps if fps > 0 else 0
        width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
        file_size_mb = file_path.stat().st_size / (1024 * 1024)

        # Sample frames at 2-second intervals for structural analysis
        interval_frames = int(fps * 2) or 1
        frames_metadata = []
        prev_resolution = None
        frame_idx = 0

        while True:
            ret, frame = video.read()
            if not ret:
                break

            if frame_idx % interval_frames == 0:
                h, w = frame.shape[:2]
                curr_res = f"{w}x{h}"
                
                # Detect resolution changes (potential page/scene transitions)
                resolution_change = ""
                if prev_resolution and curr_res != prev_resolution:
                    resolution_change = f" (resolution change from {prev_resolution})"
                
                timestamp = frame_idx / fps
                mm = int(timestamp // 60)
                ss = int(timestamp % 60)
                
                frames_metadata.append(
                    f"({mm:02d}:{ss:02d}) Frame {frame_idx}: {curr_res}{resolution_change}"
                )
                prev_resolution = curr_res

            frame_idx += 1

        video.release()

        # Build a structural summary
        metadata_summary = (
            f"VIDEO METADATA ANALYSIS (text-only — provider does not support vision)\n"
            f"{'=' * 60}\n"
            f"File: {file_path.name}\n"
            f"Duration: {int(duration_sec // 60)}m {int(duration_sec % 60)}s "
            f"({total_frames} frames @ {fps:.1f} fps)\n"
            f"Resolution: {width}x{height}\n"
            f"File Size: {file_size_mb:.1f} MB\n"
            f"Sampled frames (every 2s): {len(frames_metadata)}\n"
            f"{'=' * 60}\n\n"
            f"FRAME TIMELINE:\n"
            f"{chr(10).join(frames_metadata)}\n\n"
            f"NOTE: This is a structural-only analysis. The current provider "
            f"('{self.provider}') does not support vision/multimodal inputs. "
            f"For full visual analysis (UI elements, workflows, interactions), "
            f"use INPUT_PROCESSOR_PROVIDER=google_genai (Gemini supports native "
            f"video upload) or INPUT_PROCESSOR_PROVIDER=openai (frame-based "
            f"image analysis).\n"
        )

        return metadata_summary

    def process_video(self, file_path: Path) -> str:
        """Process video file and return description"""
        
        prompt_text = """Analyze this video recording of a web browser session and provide a detailed description focusing on:

                    1. **Visual Elements and UI Components:**
                    - For EACH page/screen, provide a UI inventory snapshot
                    - Layout and design elements
                    - Navigation bars, menus, buttons, forms
                    - Input fields, dropdowns, checkboxes, radio buttons, date pickers
                    - Tables, lists, cards, modals
                    - Any visual feedback (alerts, notifications, loading states)
                    - If dropdown options are visible, list ALL visible options
                    - If fields show defaults, placeholders, or required markers, include them

                    2. **User Interactions and Workflows:**
                    - Complete user journey from start to finish
                    - Form submissions and data entry patterns
                    - Navigation flows between pages/sections

                    3. **Key Functionality Demonstrated:**
                    - Main features being used
                    - CRUD operations (Create, Read, Update, Delete)
                    - Search, filtering, sorting functionality

                    4. **Detailed Action Timeline with Timestamps:**
                    For each significant action, provide:
                    - (MM:SS) Page/Section Name: Brief description of what happens
                    - Include specific data entered (form values, search terms, etc.)
                    - Note page transitions and URL changes if visible
                    - Identify clickable elements (buttons, links, tabs)
                    - Describe form interactions and data validation
                    - If no visible changes occur for 10+ seconds, note an idle period with timestamps

                    Format example:
                    (0:00) Home Page: Description of initial state
                    (0:03) Click "Button Name": User clicks specific button
                    (0:05) New Page/Form: Description of what loads
                    (0:08-0:15) Enter Data: List specific values entered in each field
                    (0:18) Submit Action: What happens when form is submitted

                    5. **Technical Details:**
                    - Try to identify page URLs visible in the browser address bar
                    - Note any error messages or validation feedback
                    - Identify data models/entities being manipulated
                    - Record any API calls or data loading states if visible

                    6. **Test Scenario Relevance:**
                    - Highlight reusable patterns for automation
                    - Note edge cases or error handling demonstrated
                    - Identify data dependencies between actions

                    7. **Per-Page UI Inventory (Required):**
                    For each distinct page/screen encountered, include:
                    - Page name/title and visible URL (if shown)
                    - Primary purpose of the page
                    - Controls and fields (label, type, default/placeholder, required)
                    - Dropdowns: list all visible options
                    - Tables/lists: column headers and key rows if visible

                    Provide a chronological, step-by-step breakdown that would allow someone to recreate the exact same user journey for test automation purposes."""

        if self.provider == "google_genai":
            # For large video files, Google's File API must be used instead of inline base64 encoding 
            # to prevent HTTP timeouts and payload size limit errors.
            import google.generativeai as genai
            import time
            
            genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
            
            print(f"Uploading {file_path.name} via Gemini File API...")
            video_file = genai.upload_file(path=str(file_path))
            
            print("Waiting for video processing", end="")
            while video_file.state.name == "PROCESSING":
                print(".", end="", flush=True)
                time.sleep(5)
                video_file = genai.get_file(video_file.name)
            print()
            
            if video_file.state.name == "FAILED":
                raise ValueError("Video processing failed on Google servers.")
                
            model_name = os.environ.get("INPUT_PROCESSOR_MODEL", _DEFAULT_GEMINI_MODEL)
            model = genai.GenerativeModel(model_name)
            
            response = model.generate_content([video_file, prompt_text])
            
            # Cleanup File API 
            try:
                genai.delete_file(video_file.name)
            except Exception as e:
                print(f"Warning: Failed to clean up remote video file: {e}")
                
            return response.text

        elif self.provider == "openrouter":
            segment_seconds = self._get_env_int("INPUT_PROCESSOR_VIDEO_SEGMENT_SECONDS", 60)
            split_min_mb = self._get_env_float("INPUT_PROCESSOR_VIDEO_SPLIT_MIN_MB", 12.0)
            force_split = os.environ.get("INPUT_PROCESSOR_VIDEO_FORCE_SPLIT", "false").strip().lower() in {
                "1",
                "true",
                "yes",
            }
            split_by_duration = os.environ.get("INPUT_PROCESSOR_VIDEO_SPLIT_BY_DURATION", "true").strip().lower() not in {
                "0",
                "false",
                "no",
            }
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            duration_seconds = self._get_video_duration_seconds(file_path)
            exceeds_duration = duration_seconds > 0 and duration_seconds > segment_seconds

            if force_split or file_size_mb >= split_min_mb or (split_by_duration and exceeds_duration):
                print(
                    "OpenRouter video split enabled ("
                    f"file {file_size_mb:.1f} MB, "
                    f"duration {duration_seconds}s, "
                    f"segment {segment_seconds}s)."
                )
                return self._process_openrouter_video_split(file_path, prompt_text, segment_seconds)

            return self._process_openrouter_video_inline(file_path, prompt_text)

        elif self.provider == "deepseek":
            # DeepSeek V4 is text-only (no vision/multimodal API support as of May 2026).
            # Fall back to metadata-only analysis with frame count and timing info.
            return self._analyze_video_metadata_only(file_path)

        else:
            # For OpenAI, Anthropic, etc., extract frames as image_url blocks
            print(f"Extracting frames from {file_path} for {self.provider}...")
            frames = self.extract_frames(file_path, interval_seconds=2)
            print(f"Extracted {len(frames)} frames.")
            
            content = [{"type": "text", "text": prompt_text}]
            
            # Limit number of frames to avoid payload limits (Anthropic ~10MB limit)
            # Max 20 frames
            MAX_FRAMES = 20
            if len(frames) > MAX_FRAMES:
                print(f"Warning: Too many frames ({len(frames)}). Sampling down to {MAX_FRAMES}.")
                step = len(frames) // MAX_FRAMES
                frames = frames[::step][:MAX_FRAMES]

            total_size = sum(len(f) for f in frames)
            print(f"Total payload size (base64 images): {total_size / 1024 / 1024:.2f} MB")

            for frame in frames:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{frame}"}
                })
            
            message = HumanMessage(content=content)
            response = self.llm.invoke([message])
            return self._ensure_str(response.content)
    
    def process_pdf(self, file_path: Path) -> str:
        """Process PDF file and return summary.

        When a Google API key is available the PDF is first converted to
        enriched Markdown by PyMuPDF4LLM (text + Gemini image descriptions) and
        that Markdown is used as the source for the LLM summarisation step.
        Otherwise the method falls back to plain PyPDF2 text extraction.
        """
        if self.pdf_preprocessor is not None:
            print(f"Pre-processing PDF with PyMuPDF4LLM+Gemini: {file_path.name}")
            text_content = self.pdf_preprocessor.preprocess(file_path, self.cache_dir)
        else:
            text_content = self._extract_text_pypdf2(file_path)

        if not text_content.strip():
            return "No content could be extracted from this PDF. The file may be image-based or corrupted."

        return self._summarize_document(text_content, "PDF")

    def process_text_document(self, file_path: Path) -> str:
        """Process plain text and Markdown files and return a summary."""
        suffix = file_path.suffix.lower()

        if suffix == '.md' and self.pdf_preprocessor is not None:
            print(f"Pre-processing Markdown images with Gemini: {file_path.name}")
            text_content = self.pdf_preprocessor.preprocess_markdown(file_path, self.cache_dir)
        else:
            text_content = self._read_text_file(file_path)

        if not text_content.strip():
            return f"No content could be extracted from this {suffix} file."

        source_label = "Markdown" if suffix == '.md' else "text"
        return self._summarize_document(text_content, source_label)

    def _summarize_document(self, text_content: str, source_label: str) -> str:
        """Summarize document content into test-generation-friendly output."""
        print(f"Using {len(text_content)} characters of {source_label} content")

        # Use LLM to summarise and extract key elements
        message = HumanMessage(
            content=f"""Analyze this document content and provide a structured summary focusing on:
            1. Key requirements or specifications
            2. User stories or use cases
            3. Business rules and constraints
            4. Data models or entities mentioned
            5. Workflow processes
            6. Acceptance criteria if present

            Format the response in a structured way that would be useful for generating test scenarios.
            Use clear headings and bullet points for easy parsing.

            Document content:
            {text_content}"""
        )

        response = self.llm.invoke([message])
        return self._ensure_str(response.content)

    def _read_text_file(self, file_path: Path) -> str:
        """Read UTF-8 text content, replacing undecodable bytes when needed."""
        try:
            return file_path.read_text(encoding='utf-8', errors='replace')
        except Exception as e:
            print(f"Error reading text file {file_path.name}: {str(e)}")
            return ""

    def _extract_text_pypdf2(self, file_path: Path) -> str:
        """Fallback: extract plain text from a PDF using PyPDF2."""
        text_content = ""
        try:
            with open(file_path, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                if pdf_reader.is_encrypted:
                    print(f"Warning: PDF {file_path.name} is encrypted, attempting to decrypt...")
                    pdf_reader.decrypt("")
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text.strip():
                            text_content += f"--- Page {page_num + 1} ---\n"
                            text_content += page_text + "\n\n"
                    except Exception as e:
                        print(f"Error extracting text from page {page_num + 1}: {str(e)}")
        except Exception as e:
            print(f"Error reading PDF {file_path.name}: {str(e)}")
            return f"Error processing PDF: {str(e)}"
        return text_content
    
    def create_cache_file(self, file_path: Path, file_hash: str, processed_content: str):
        """Create cache file with metadata and processed content"""
        cache_file_path = self.cache_dir / f"{file_hash}.txt"
        
        # Ensure content is a string (defensive)
        processed_content = self._ensure_str(processed_content)
        
        # Create CSV metadata line
        metadata = {
            'original_name': file_path.name,
            'format': file_path.suffix.lower(),
            'file_size': file_path.stat().st_size,
            'hash': file_hash
        }
        
        # Convert metadata to CSV format
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['original_name', 'format', 'file_size', 'hash'])
        writer.writerow([metadata['original_name'], metadata['format'], 
                        metadata['file_size'], metadata['hash']])
        csv_metadata = output.getvalue().strip()
        
        # Write cache file
        with open(cache_file_path, 'w', encoding='utf-8') as cache_file:
            cache_file.write(csv_metadata + "\n")
            cache_file.write("=" * 50 + "\n")
            cache_file.write("PROCESSED CONTENT:\n")
            cache_file.write("=" * 50 + "\n")
            cache_file.write(processed_content)
        
        print(f"Created cache file: {cache_file_path}")
    
    def process_file(self, file_path: Path) -> Optional[str]:
        """Process a single file based on its format"""
        suffix = file_path.suffix.lower()

        if suffix not in self.supported_formats:
            print(f"Unsupported format: {file_path.suffix}")
            return None
        
        file_hash = self.get_file_hash(file_path)
        
        if self.is_processed(file_hash):
            print(f"File already processed: {file_path.name} (hash: {file_hash[:8]}...)")
            return file_hash
        
        print(f"Processing file: {file_path.name}")
        
        try:
            if suffix == '.mp4':
                processed_content = self.process_video(file_path)
            elif suffix == '.pdf':
                processed_content = self.process_pdf(file_path)
            elif suffix in {'.md', '.txt'}:
                processed_content = self.process_text_document(file_path)
            else:
                return None
            
            self.create_cache_file(file_path, file_hash, processed_content)
            return file_hash
            
        except Exception as e:
            print(f"Error processing {file_path.name}: {str(e)}")
            print("Detailed traceback:")
            print(traceback.format_exc())
            cause = e.__cause__
            while cause is not None:
                print(f"Caused by: {type(cause).__name__}: {cause}")
                cause = cause.__cause__
            return None
    
    def process_all_files(self) -> List[str]:
        """Process all supported files in the input directory"""
        if not self.input_dir.exists():
            print(f"Input directory does not exist: {self.input_dir}")
            return []
        
        processed_hashes = []
        
        for file_path in self.input_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in self.supported_formats:
                file_hash = self.process_file(file_path)
                if file_hash:
                    processed_hashes.append(file_hash)
        
        return processed_hashes
    
    def get_cached_content(self, file_hash: str) -> Optional[str]:
        """Retrieve cached content by hash"""
        cache_file = self.cache_dir / f"{file_hash}.txt"
        if cache_file.exists():
            with open(cache_file, 'r', encoding='utf-8') as f:
                return f.read()
        return None

def main():
    processor = FileProcessor()
    
    print("Starting file processing...")
    processed_files = processor.process_all_files()
    
    if processed_files:
        print(f"\nProcessed {len(processed_files)} files:")
        for file_hash in processed_files:
            print(f"  - {file_hash[:8]}...")
    else:
        print("No files were processed.")
    
    print(f"\nCache directory: {processor.cache_dir}")
    print("Processing complete!")

if __name__ == "__main__":
    main()