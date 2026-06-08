"""
PDF preprocessor using PyMuPDF4LLM + Google Gemini.

This module converts a PDF to Markdown and enriches image placeholders with
Gemini-generated descriptions. Results are cached under:

    <cache_dir>/pre-processed/<sha256>.md
"""

import base64
import hashlib
import logging
import mimetypes
import re
import shutil
from pathlib import Path
from typing import Any, Optional

import fitz  # PyMuPDF
import pymupdf4llm
from langchain_core.messages import HumanMessage, SystemMessage
from langchain.chat_models import init_chat_model
from langchain_google_genai import ChatGoogleGenerativeAI

_log = logging.getLogger(__name__)
_IMAGE_PLACEHOLDER_RE = re.compile(r"!\[\]\((.*?)\)")
_MARKDOWN_IMAGE_RE = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<target>[^)]+)\)")
_IMAGE_DESCRIPTION_SYSTEM_PROMPT = """You are a QA-focused visual analyst for software documentation.

Analyze the provided image and produce a detailed, factual description optimized for test scenario generation.
Most images are either:
1) user-flow screenshots (multi-step interactions), or
2) user interface screens/forms/components.

Requirements:
- Be precise and objective. Do not invent hidden data.
- If text is visible, quote important labels/values exactly when readable.
- If content is unclear, say "unclear" instead of guessing.

Output format (plain text, use these headings):
1. Screen / Context
- What page/view this appears to be.
- Main purpose of the screen.

2. UI Components and Fields
- List visible controls: buttons, links, tabs, menus, tables, cards, dialogs, badges, toasts.
- For forms: field labels, input types (text, select, checkbox, radio, date, password, etc.), placeholders/default values, required markers, helper/error text.

3. Content and State
- Visible user/content data, statuses, selected options, toggles, validation messages, loading/empty/error states.

4. User Flow and Actions
- Step-by-step likely user flow implied by this screen.
- Actionable elements and expected outcomes when clicked/submitted.

Keep the response concise but detailed enough to drive automated E2E test creation."""


def _extract_text_content(content: Any) -> str:
    """Extract human-readable text from LangChain/Gemini content payloads."""
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, dict):
        # Common block shape: {"type": "text", "text": "..."}
        if isinstance(content.get("text"), str):
            return content["text"].strip()
        # Fallback when nested content exists.
        if "content" in content:
            return _extract_text_content(content["content"])
        return ""

    if isinstance(content, list):
        parts = [_extract_text_content(item) for item in content]
        return "\n".join(part for part in parts if part).strip()

    return str(content).strip()


class PdfPreprocessor:
    """Convert PDF files to Markdown and append Gemini image descriptions."""

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash", provider: str = "google_genai") -> None:
        if provider == "openrouter":
            self._llm = init_chat_model(
                model,
                model_provider="openai",
                base_url="https://openrouter.ai/api/v1",
                api_key=api_key,
                temperature=0,
                max_tokens=None,
                timeout=None,
                max_retries=2,
            )
        elif provider == "google_genai":
            self._llm = ChatGoogleGenerativeAI(
                model=model,
                temperature=0,
                max_tokens=None,
                timeout=None,
                max_retries=2,
                api_key=api_key,
            )
        else:
            raise ValueError(f"Unsupported PDF preprocessor provider: {provider}")

    def preprocess(self, pdf_path: Path, cache_dir: Path) -> str:
        """Return cached or newly generated enriched Markdown for a PDF."""
        pre_processed_dir = cache_dir / "pre-processed"
        pre_processed_dir.mkdir(parents=True, exist_ok=True)

        file_hash = _sha256(pdf_path)
        output_path = pre_processed_dir / f"{file_hash}.md"

        if output_path.exists():
            _log.info("Pre-processed cache hit: %s", output_path.name)
            return output_path.read_text(encoding="utf-8")

        _log.info("Converting PDF with PyMuPDF4LLM: %s", pdf_path.name)

        images_dir = pre_processed_dir / f"{file_hash}_images"
        images_dir.mkdir(parents=True, exist_ok=True)

        try:
            markdown = pymupdf4llm.to_markdown(
                str(pdf_path),
                write_images=True,
                image_path=str(images_dir),
            )

            enriched_markdown = self._inject_image_descriptions(
                pdf_path=pdf_path,
                markdown=markdown,
                images_dir=images_dir,
            )

            output_path.write_text(enriched_markdown, encoding="utf-8")
            _log.info("Saved pre-processed markdown: %s", output_path)
            return enriched_markdown
        except Exception:
            if output_path.exists():
                output_path.unlink()
            if images_dir.exists():
                shutil.rmtree(images_dir, ignore_errors=True)
            raise

    def preprocess_markdown(self, markdown_path: Path, cache_dir: Path) -> str:
        """Return cached or newly generated Markdown with local image descriptions."""
        pre_processed_dir = cache_dir / "pre-processed"
        pre_processed_dir.mkdir(parents=True, exist_ok=True)

        file_hash = _sha256(markdown_path)
        output_path = pre_processed_dir / f"{file_hash}-markdown.md"

        if output_path.exists():
            _log.info("Pre-processed markdown cache hit: %s", output_path.name)
            return output_path.read_text(encoding="utf-8")

        markdown = markdown_path.read_text(encoding="utf-8", errors="replace")
        enriched_markdown = self._inject_markdown_image_descriptions(markdown_path, markdown)
        output_path.write_text(enriched_markdown, encoding="utf-8")
        _log.info("Saved pre-processed markdown: %s", output_path)
        return enriched_markdown

    def _inject_image_descriptions(self, pdf_path: Path, markdown: str, images_dir: Path) -> str:
        """
        Replace markdown image placeholders with descriptive alt text only.

        We map placeholders in document order to extracted PDF images by index.
        If mapping fails for an image, the original markdown placeholder is kept.
        """
        placeholders = _IMAGE_PLACEHOLDER_RE.findall(markdown)
        if not placeholders:
            return markdown

        doc = fitz.open(str(pdf_path))
        image_bytes_by_order: list[tuple[bytes, str]] = []

        try:
            for page in doc:
                for img in page.get_images(full=True):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image.get("image")
                    ext = (base_image.get("ext") or "png").lower()
                    if image_bytes:
                        image_bytes_by_order.append((image_bytes, ext))
        finally:
            doc.close()

        replacements = min(len(placeholders), len(image_bytes_by_order))
        if len(placeholders) != len(image_bytes_by_order):
            _log.warning(
                "Image count mismatch for %s: markdown=%d extracted=%d",
                pdf_path.name,
                len(placeholders),
                len(image_bytes_by_order),
            )

        for idx in range(replacements):
            placeholder_path = placeholders[idx]
            image_bytes, ext = image_bytes_by_order[idx]

            media_type = f"image/{ext}" if ext != "jpg" else "image/jpeg"
            description = self._describe_image(image_bytes=image_bytes, media_type=media_type)

            full_image_path = images_dir / Path(placeholder_path).name
            display_path = str(full_image_path).replace("\\", "/")
            replacement = f"![Image description: {description}]({display_path})"
            markdown = markdown.replace(f"![]({placeholder_path})", replacement, 1)

        return markdown

    def _inject_markdown_image_descriptions(self, markdown_path: Path, markdown: str) -> str:
        """Replace local markdown image alt text with Gemini-generated descriptions."""

        def replace_image(match: re.Match[str]) -> str:
            target = match.group("target")
            image_path = _resolve_markdown_image_path(markdown_path, target)
            if image_path is None:
                return match.group(0)

            if not image_path.exists() or not image_path.is_file():
                _log.warning("Markdown image not found for %s: %s", markdown_path.name, image_path)
                return match.group(0)

            media_type = _guess_media_type(image_path)

            try:
                description = self._describe_image(image_bytes=image_path.read_bytes(), media_type=media_type)
            except Exception as exc:  # noqa: BLE001
                _log.warning("Skipping markdown image description for %s: %s", image_path, exc)
                return match.group(0)

            return f"![Image description: {description}]({target})"

        return _MARKDOWN_IMAGE_RE.sub(replace_image, markdown)

    def _describe_image(self, image_bytes: bytes, media_type: str) -> str:
        """Describe one image with Gemini."""
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        system_message = SystemMessage(content=_IMAGE_DESCRIPTION_SYSTEM_PROMPT)
        image_message = HumanMessage(
            content=[
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{media_type};base64,{image_b64}"},
                },
            ]
        )

        try:
            response = self._llm.invoke([system_message, image_message])
            description = _extract_text_content(response.content)
            if not description:
                raise ValueError("Gemini returned an empty image description")
            return description
        except Exception as exc:  # noqa: BLE001
            _log.error("Gemini image description failed: %s", exc)
            raise


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(4096), b""):
            h.update(chunk)
    return h.hexdigest()


def _resolve_markdown_image_path(markdown_path: Path, target: str) -> Optional[Path]:
    cleaned_target = target.strip()
    if cleaned_target.startswith("<") and cleaned_target.endswith(">"):
        cleaned_target = cleaned_target[1:-1].strip()

    path_match = re.match(r'(?P<path>\S+)(?:\s+["\"][^"\"]*["\"])?$', cleaned_target)
    if path_match:
        cleaned_target = path_match.group("path")

    if cleaned_target.startswith("http://") or cleaned_target.startswith("https://") or cleaned_target.startswith("data:"):
        return None

    image_path = Path(cleaned_target)
    if not image_path.is_absolute():
        image_path = markdown_path.parent / image_path
    return image_path.resolve()


def _guess_media_type(image_path: Path) -> str:
    media_type, _ = mimetypes.guess_type(image_path.name)
    if media_type:
        return media_type

    suffix = image_path.suffix.lower().lstrip(".") or "png"
    if suffix == "jpg":
        return "image/jpeg"
    return f"image/{suffix}"
