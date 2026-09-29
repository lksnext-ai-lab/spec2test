"""Handlers dispatch by extension and delegate to their collaborators."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from analysis.document_summarizer import DocumentSummarizer
from analysis.image_describer import ImageDescriptionError, ImageDescriber
from cache.preprocessed import PreprocessedStore
from handlers.base import HandlerContext
from handlers.markdown_handler import MarkdownHandler
from handlers.pdf_handler import EMPTY_PDF_MESSAGE, PdfHandler
from handlers.registry import HandlerRegistry, UnsupportedFormatError
from handlers.text_handler import TextHandler
from handlers.video_handler import VideoHandler
from preprocessing.markdown_images import MarkdownImageEnricher, resolve_image_path
from preprocessing.pdf_text import extract_text_with_pypdf2
from support import StubChatModel, source_for


class StubAnalyzer:
    """Video analyzer double."""

    name = "stub-analyzer"

    def analyze(self, video_path: Path) -> str:
        return f"analysis of {video_path.name}"

    def describe(self) -> str:
        return self.name


class StubConverter:
    """PDF converter double."""

    def __init__(self, result: str = "converted markdown") -> None:
        self.result = result
        self.calls: list[Path] = []

    def convert(self, source) -> str:
        self.calls.append(source.path)
        return self.result


class StubEnricher:
    """Markdown enricher double."""

    def __init__(self, result: str = "enriched markdown") -> None:
        self.result = result
        self.calls: list[Path] = []

    def enrich(self, source) -> str:
        self.calls.append(source.path)
        return self.result


def write(directory: Path, name: str, content: str = "content") -> Path:
    path = directory / name
    path.write_text(content, encoding="utf-8")
    return path


def test_registry_maps_extensions_to_handlers(chat_model: StubChatModel) -> None:
    summarizer = DocumentSummarizer(chat_model)
    video = VideoHandler(StubAnalyzer())
    registry = HandlerRegistry([video, TextHandler(summarizer), MarkdownHandler(summarizer)])

    assert registry.extensions() == (".md", ".mp4", ".txt")
    assert registry.get("session.mp4") is video
    assert registry.supports("notes.md")
    assert registry.find("sheet.csv") is None
    assert {handler.name for handler in registry.handlers()} == {"video", "text", "markdown"}


def test_registry_reports_unsupported_formats() -> None:
    registry = HandlerRegistry([TextHandler(DocumentSummarizer(StubChatModel()))])

    with pytest.raises(UnsupportedFormatError) as error:
        registry.get("sheet.csv")

    assert "No handler for .csv" in str(error.value)
    assert ".txt" in str(error.value)


def test_registry_refuses_duplicate_extensions() -> None:
    registry = HandlerRegistry([TextHandler(DocumentSummarizer(StubChatModel()))])

    with pytest.raises(ValueError, match="already registered"):
        registry.register(TextHandler(DocumentSummarizer(StubChatModel())))


def test_handlers_must_declare_extensions() -> None:
    from handlers.base import FileHandler

    class Empty(FileHandler):
        name = "empty"

        def handle(self, source, context) -> str:  # pragma: no cover - never called
            return ""

    with pytest.raises(ValueError, match="declares no extensions"):
        HandlerRegistry([Empty()])


def test_video_handler_delegates_to_the_analyzer(tmp_path: Path) -> None:
    video = tmp_path / "session.mp4"
    video.write_bytes(b"video")

    result = VideoHandler(StubAnalyzer()).handle(source_for(video), HandlerContext())

    assert result == "analysis of session.mp4"


def test_text_handler_summarises_the_file(tmp_path: Path, chat_model: StubChatModel) -> None:
    path = write(tmp_path, "notes.txt", "the requirements text")

    result = TextHandler(DocumentSummarizer(chat_model)).handle(
        source_for(path), HandlerContext()
    )

    assert result == "processed content"
    assert "the requirements text" in chat_model.prompt_text()


def test_text_handler_reports_an_empty_file(tmp_path: Path, chat_model: StubChatModel) -> None:
    path = write(tmp_path, "empty.txt", "   ")

    result = TextHandler(DocumentSummarizer(chat_model)).handle(
        source_for(path), HandlerContext()
    )

    assert result == "No content could be extracted from this .txt file."
    assert chat_model.call_count == 0


def test_markdown_handler_uses_the_enricher_when_available(
    tmp_path: Path, chat_model: StubChatModel, preprocessed: PreprocessedStore
) -> None:
    path = write(tmp_path, "guide.md", "![alt](image.png)")
    enricher = StubEnricher()

    result = MarkdownHandler(DocumentSummarizer(chat_model), enricher).handle(
        source_for(path), HandlerContext(preprocessed=preprocessed)
    )

    assert enricher.calls == [path]
    assert "enriched markdown" in chat_model.prompt_text()
    assert result == "processed content"


def test_markdown_handler_without_enricher_reads_the_file(
    tmp_path: Path, chat_model: StubChatModel
) -> None:
    path = write(tmp_path, "guide.md", "# Heading")

    MarkdownHandler(DocumentSummarizer(chat_model)).handle(source_for(path), HandlerContext())

    assert "# Heading" in chat_model.prompt_text()


def test_pdf_handler_uses_the_converter(tmp_path: Path, chat_model: StubChatModel, preprocessed) -> None:
    path = tmp_path / "specs.pdf"
    path.write_bytes(b"%PDF-1.4")
    converter = StubConverter("converted body")

    result = PdfHandler(DocumentSummarizer(chat_model), converter).handle(
        source_for(path), HandlerContext(preprocessed=preprocessed)
    )

    assert converter.calls == [path]
    assert "converted body" in chat_model.prompt_text()
    assert result == "processed content"


def test_pdf_handler_without_converter_uses_the_text_layer(
    tmp_path: Path, chat_model: StubChatModel, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "specs.pdf"
    path.write_bytes(b"%PDF-1.4")
    monkeypatch.setattr(
        "handlers.pdf_handler.extract_text_with_pypdf2", lambda pdf_path: "plain text layer"
    )

    PdfHandler(DocumentSummarizer(chat_model)).handle(source_for(path), HandlerContext())

    assert "plain text layer" in chat_model.prompt_text()


def test_pdf_handler_reports_an_empty_pdf(
    tmp_path: Path, chat_model: StubChatModel, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "scan.pdf"
    path.write_bytes(b"%PDF-1.4")
    monkeypatch.setattr("handlers.pdf_handler.extract_text_with_pypdf2", lambda pdf_path: "  ")

    result = PdfHandler(DocumentSummarizer(chat_model)).handle(source_for(path), HandlerContext())

    assert result == EMPTY_PDF_MESSAGE
    assert chat_model.call_count == 0


def test_pypdf2_guidance_when_the_package_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "specs.pdf"
    path.write_bytes(b"%PDF-1.4")
    # An import of ``None`` from sys.modules raises ImportError, installed or not.
    monkeypatch.setitem(sys.modules, "PyPDF2", None)

    with pytest.raises(RuntimeError, match="PyPDF2"):
        extract_text_with_pypdf2(path)


def test_summarizer_rejects_empty_content(chat_model: StubChatModel) -> None:
    with pytest.raises(ValueError, match="No content to summarize"):
        DocumentSummarizer(chat_model).summarize("   ", "PDF")


def test_image_describer_sends_a_data_url() -> None:
    chat_model = StubChatModel("a login form with two fields")
    describer = ImageDescriber(chat_model)

    description = describer.describe(b"png-bytes", "image/png")

    assert description == "a login form with two fields"
    content = chat_model.calls[0][-1].content
    assert content[0]["image_url"]["url"].startswith("data:image/png;base64,")


def test_image_describer_rejects_an_empty_answer() -> None:
    with pytest.raises(ImageDescriptionError):
        ImageDescriber(StubChatModel("  ")).describe(b"png-bytes", "image/png")


def test_markdown_enricher_describes_local_images(
    tmp_path: Path, preprocessed: PreprocessedStore
) -> None:
    (tmp_path / "shot.png").write_bytes(b"png")
    path = write(
        tmp_path,
        "guide.md",
        "Before\n\n![old](shot.png)\n\n![remote](https://example.test/x.png)\n",
    )

    enriched = MarkdownImageEnricher(preprocessed, ImageDescriber(StubChatModel(" Login screen "))).enrich(
        source_for(path)
    )

    assert "![Image description: Login screen](shot.png)" in enriched
    assert "![remote](https://example.test/x.png)" in enriched
    stored = list(preprocessed.directory.glob("*.md"))
    assert len(stored) == 1


def test_markdown_enricher_keeps_the_original_when_a_file_is_missing(
    tmp_path: Path, preprocessed: PreprocessedStore
) -> None:
    path = write(tmp_path, "guide.md", "![missing](nope.png)")

    enriched = MarkdownImageEnricher(preprocessed, ImageDescriber(StubChatModel("x"))).enrich(
        source_for(path)
    )

    assert enriched == "![missing](nope.png)"


def test_markdown_enricher_survives_a_failing_description(
    tmp_path: Path, preprocessed: PreprocessedStore
) -> None:
    (tmp_path / "shot.png").write_bytes(b"png")
    path = write(tmp_path, "guide.md", "![old](shot.png)")
    describer = ImageDescriber(StubChatModel(fail_with=RuntimeError("model is down")))

    enriched = MarkdownImageEnricher(preprocessed, describer).enrich(source_for(path))

    assert enriched == "![old](shot.png)"


@pytest.mark.parametrize(
    ("target", "expected"),
    [
        ("image.png", "resolved"),
        ("./image.png", "resolved"),
        ("<image.png>", "resolved"),
        ('image.png "a title"', "resolved"),
        ("https://example.test/image.png", None),
        ("data:image/png;base64,AAAA", None),
    ],
)
def test_resolve_image_path(tmp_path: Path, target: str, expected: str | None) -> None:
    resolved = resolve_image_path(tmp_path / "guide.md", target)

    if expected is None:
        assert resolved is None
    else:
        assert resolved == (tmp_path / "image.png").resolve()
