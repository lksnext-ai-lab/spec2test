"""Pre-processed artefacts follow the same name-based rules as the cache."""

from __future__ import annotations

from pathlib import Path

import pytest

from cache.preprocessed import IMAGES_SUFFIX, PreprocessedStore
from cache.reconcile import CacheStatus
from cache.repository import CacheRepository
from cache.source import SourceFile
from preprocessing.pdf_to_markdown import PdfConversionError, PdfToMarkdown
from support import source_for


def write(directory: Path, name: str, content: str = "content") -> SourceFile:
    path = directory / name
    path.write_text(content, encoding="utf-8")
    return SourceFile.from_path(path)


def build_with(images: bool = True):
    """A ``build`` callable that writes one image and returns Markdown."""
    calls: list[Path] = []

    def build(images_dir: Path) -> str:
        calls.append(images_dir)
        if images:
            images_dir.mkdir(parents=True, exist_ok=True)
            (images_dir / "figure-1.png").write_bytes(b"png")
        return "![Image description: a chart]()"

    build.calls = calls  # type: ignore[attr-defined]
    return build


def test_images_directory_is_named_after_the_source(preprocessed: PreprocessedStore, tmp_path: Path) -> None:
    source = write(tmp_path, "guide.md")

    assert preprocessed.images_dir(source) == preprocessed.directory / f"guide.md{IMAGES_SUFFIX}"


def test_build_runs_once_and_the_result_is_reused(
    preprocessed: PreprocessedStore, tmp_path: Path
) -> None:
    source = write(tmp_path, "guide.md")
    build = build_with()

    content, status = preprocessed.ensure(source, build, "stub", "stub-model")
    again, second_status = preprocessed.ensure(source, build, "stub", "stub-model")

    assert status is CacheStatus.NEW
    assert content == "![Image description: a chart]()"
    assert second_status is CacheStatus.CACHED
    assert again.strip() == content
    assert len(build.calls) == 1  # type: ignore[attr-defined]
    assert (preprocessed.directory / f"guide.md{IMAGES_SUFFIX}").is_dir()


def test_a_changed_source_rebuilds_and_archives_the_old_images(
    preprocessed: PreprocessedStore, tmp_path: Path
) -> None:
    source = write(tmp_path, "guide.md", "first version")
    build = build_with()
    preprocessed.ensure(source, build, "stub", "stub-model")

    changed = write(tmp_path, "guide.md", "second version")
    _, status = preprocessed.ensure(changed, build, "stub", "stub-model")

    assert status is CacheStatus.UPDATED
    assert len(build.calls) == 2  # type: ignore[attr-defined]
    archived = list(preprocessed.repository.history_dir.glob(f"guide.md{IMAGES_SUFFIX}.*"))
    assert len(archived) == 1
    assert (archived[0] / "figure-1.png").is_file()


def test_a_renamed_source_reuses_the_content_without_rebuilding(
    preprocessed: PreprocessedStore, tmp_path: Path
) -> None:
    source = write(tmp_path, "guide.md", "same bytes")
    build = build_with()
    preprocessed.ensure(source, build, "stub", "stub-model")

    renamed = write(tmp_path, "renamed.md", "same bytes")
    content, status = preprocessed.ensure(renamed, build, "stub", "stub-model")

    assert status is CacheStatus.RENAMED
    assert content.strip() == "![Image description: a chart]()"
    assert len(build.calls) == 1  # type: ignore[attr-defined]
    moved = preprocessed.directory / f"renamed.md{IMAGES_SUFFIX}"
    assert (moved / "figure-1.png").is_file()
    assert not (preprocessed.directory / f"guide.md{IMAGES_SUFFIX}").exists()


def test_a_source_with_a_different_format_is_rebuilt(
    preprocessed: PreprocessedStore, tmp_path: Path
) -> None:
    source = write(tmp_path, "guide.md", "same bytes")
    build = build_with()
    preprocessed.ensure(source, build, "stub", "stub-model")

    twin = write(tmp_path, "guide.txt", "same bytes")
    _, status = preprocessed.ensure(twin, build, "stub", "stub-model")

    assert status is CacheStatus.NEW
    assert len(build.calls) == 2  # type: ignore[attr-defined]


def test_cached_returns_the_stored_markdown(
    preprocessed: PreprocessedStore, tmp_path: Path
) -> None:
    source = write(tmp_path, "guide.md")

    assert preprocessed.cached(source) is None
    preprocessed.ensure(source, build_with(), "stub", "stub-model")
    assert preprocessed.cached(source).strip() == "![Image description: a chart]()"  # type: ignore[union-attr]


def test_refresh_rebuilds_the_index(preprocessed: PreprocessedStore, tmp_path: Path) -> None:
    source = write(tmp_path, "guide.md", "alpha")
    preprocessed.ensure(source, build_with(), "stub", "stub-model")
    other = write(tmp_path, "other.md", "beta")
    preprocessed.repository.write(other, "beta body", "stub", "stub-model")

    assert preprocessed.reconciler.plan(other).status is CacheStatus.NEW
    preprocessed.refresh()
    assert preprocessed.reconciler.plan(other).status is CacheStatus.CACHED


def test_legacy_image_folders_are_renamed(
    preprocessed: PreprocessedStore, tmp_path: Path
) -> None:
    """A legacy ``<sha>_images`` folder follows its migrated cache file."""
    sha256 = "d" * 64
    cache_file = preprocessed.directory / f"{sha256}.txt"
    cache_file.write_text(
        f"original_name,format,file_size,hash\nguide.pdf,.pdf,10,{sha256}\n"
        + "=" * 50
        + "\nPROCESSED CONTENT:\nbody\n",
        encoding="utf-8",
    )
    legacy_images = preprocessed.directory / f"{sha256}{IMAGES_SUFFIX}"
    legacy_images.mkdir()
    (legacy_images / "figure-1.png").write_bytes(b"png")

    preprocessed.migrate_legacy()

    renamed = preprocessed.directory / f"guide.pdf{IMAGES_SUFFIX}"
    assert renamed.is_dir()
    assert (renamed / "figure-1.png").is_file()
    assert not legacy_images.exists()


# --- PDF conversion ----------------------------------------------------------


def pdf_source(tmp_path: Path) -> SourceFile:
    path = tmp_path / "specs.pdf"
    path.write_bytes(b"%PDF-1.4")
    return SourceFile.from_path(path)


def stub_conversion(monkeypatch: pytest.MonkeyPatch, markdown: str, images=()) -> None:
    import preprocessing.pdf_to_markdown as module

    monkeypatch.setattr(module, "_to_markdown", lambda pdf_path, images_dir: markdown)
    monkeypatch.setattr(module, "_extract_images_in_order", lambda pdf_path: list(images))


def test_conversion_is_cached(preprocessed: PreprocessedStore, tmp_path: Path, monkeypatch) -> None:
    calls: list[Path] = []
    import preprocessing.pdf_to_markdown as module

    monkeypatch.setattr(
        module,
        "_to_markdown",
        lambda pdf_path, images_dir: calls.append(pdf_path) or "plain markdown\n",
    )
    source = pdf_source(tmp_path)
    converter = PdfToMarkdown(preprocessed, None, "stub", "stub-model")

    first = converter.convert(source)
    second = converter.convert(source)

    assert first == "plain markdown\n"
    assert second.strip() == "plain markdown"
    assert len(calls) == 1


def test_placeholders_are_replaced_with_descriptions(
    preprocessed: PreprocessedStore, tmp_path: Path, monkeypatch
) -> None:
    stub_conversion(
        monkeypatch,
        "Intro\n\n![](figure-1.png)\n\n![](figure-2.png)\n",
        images=[(b"one", "image/png"), (b"two", "image/jpeg")],
    )
    converter = PdfToMarkdown(
        preprocessed, _Describer(["a login form", "a results table"]), "stub", "vision"
    )

    markdown = converter.convert(pdf_source(tmp_path))

    assert "![Image description: a login form]" in markdown
    assert "![Image description: a results table]" in markdown
    assert "![](figure-1.png)" not in markdown


def test_surplus_placeholders_are_left_untouched(
    preprocessed: PreprocessedStore, tmp_path: Path, monkeypatch
) -> None:
    stub_conversion(
        monkeypatch,
        "![](figure-1.png)\n\n![](figure-2.png)\n",
        images=[(b"one", "image/png")],
    )
    converter = PdfToMarkdown(preprocessed, _Describer(["a login form"]), "stub", "vision")

    markdown = converter.convert(pdf_source(tmp_path))

    assert "![Image description: a login form]" in markdown
    assert "![](figure-2.png)" in markdown


def test_a_failed_conversion_leaves_no_partial_images(
    preprocessed: PreprocessedStore, tmp_path: Path, monkeypatch
) -> None:
    import preprocessing.pdf_to_markdown as module

    images_dir = preprocessed.images_dir(pdf_source(tmp_path))
    images_dir.mkdir()
    (images_dir / "kept.png").write_bytes(b"older run")

    def explode(pdf_path: Path, directory: Path) -> str:
        (directory / "half-written.png").write_bytes(b"partial")
        raise PdfConversionError("boom")

    monkeypatch.setattr(module, "_to_markdown", explode)

    with pytest.raises(PdfConversionError, match="boom"):
        PdfToMarkdown(preprocessed, None, "stub", "stub-model").convert(pdf_source(tmp_path))

    assert [item.name for item in images_dir.glob("*")] == ["kept.png"]


class _Describer:
    """Image describer double returning canned descriptions in order."""

    def __init__(self, descriptions: list[str]) -> None:
        self._descriptions = list(descriptions)
        self.seen: list[bytes] = []

    def describe(self, image_bytes: bytes, media_type: str) -> str:
        self.seen.append(image_bytes)
        return self._descriptions.pop(0)


def test_preprocessed_cache_is_per_project(tmp_path: Path) -> None:
    """Two stores in different directories never see each other's artefacts."""
    first = PreprocessedStore.in_directory(tmp_path / "a")
    second = PreprocessedStore.in_directory(tmp_path / "b")
    source = write(tmp_path, "guide.md", "same bytes")

    first.ensure(source, build_with(), "stub", "stub-model")

    assert first.cached(source) is not None
    assert second.cached(source) is None
    assert isinstance(second.repository, CacheRepository)
    assert second.repository.directory == tmp_path / "b"


