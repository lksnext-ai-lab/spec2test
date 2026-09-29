"""End-to-end reconciliation: input directory in, cache statuses out."""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from cache.lookup import CacheLookupError
from cache.reconcile import CacheStatus
from cache.repository import CacheRepository
from handlers.registry import HandlerRegistry
from processing_service import ProcessingService
from support import FailingHandler, RecordingHandler, StubChatModel


def service_for(
    inputs: Path,
    cache_dir: Path,
    model: StubChatModel,
    handlers: HandlerRegistry | None = None,
) -> ProcessingService:
    return ProcessingService(
        input_dir=inputs,
        cache=CacheRepository(cache_dir),
        handlers=handlers or HandlerRegistry([RecordingHandler(model)]),
        provider="stub",
        model="stub-model",
    )


def write(directory: Path, name: str, content: str = "hello") -> Path:
    path = directory / name
    path.write_text(content, encoding="utf-8")
    return path


def statuses(service: ProcessingService) -> dict[str, str]:
    return {result.name: result.status.value for result in service.process_all().results}


def test_new_files_are_processed_and_cached(inputs_dir: Path, cache_dir: Path) -> None:
    model = StubChatModel("processed")
    write(inputs_dir, "b-notes.txt", "beta")
    write(inputs_dir, "a-notes.txt", "alpha")
    write(inputs_dir, "ignore.csv", "not supported")
    service = service_for(inputs_dir, cache_dir, model)

    report = service.process_all()

    assert [result.name for result in report.results] == ["a-notes.txt", "b-notes.txt"]
    assert report.counts == {"new": 2}
    assert report.summarise() == "new=2"
    assert model.call_count == 2
    assert sorted(item.name for item in cache_dir.glob("*.md")) == [
        "a-notes.txt.md",
        "b-notes.txt.md",
    ]


def test_results_carry_the_cache_metadata(inputs_dir: Path, cache_dir: Path) -> None:
    model = StubChatModel("processed")
    path = write(inputs_dir, "notes.txt", "alpha")
    service = service_for(inputs_dir, cache_dir, model)

    result = service.process_all().results[0]

    assert result.format == ".txt"
    assert result.size == path.stat().st_size
    assert result.sha256 == service.cache_index().find_by_source("notes.txt").sha256  # type: ignore[union-attr]
    assert result.processed_at.endswith("Z")
    assert set(result.to_dict()) == {"name", "format", "size", "sha256", "status", "processed_at"}


def test_an_unchanged_file_is_reused(inputs_dir: Path, cache_dir: Path) -> None:
    model = StubChatModel("processed")
    write(inputs_dir, "notes.txt", "alpha")
    service = service_for(inputs_dir, cache_dir, model)
    service.process_all()

    assert statuses(service) == {"notes.txt": "cached"}
    assert model.call_count == 1


def test_a_modified_file_is_reprocessed_and_the_old_version_archived(
    inputs_dir: Path, cache_dir: Path
) -> None:
    model = StubChatModel("v1")
    write(inputs_dir, "notes.txt", "alpha")
    service = service_for(inputs_dir, cache_dir, model)
    first = service.process_all().results[0]

    model.response = "v2"
    write(inputs_dir, "notes.txt", "beta")
    report = service.process_all()

    assert report.counts == {"updated": 1}
    assert model.call_count == 2
    assert service.read_cached("notes.txt") == "v2\n"
    archived = list((cache_dir / ".history").glob("notes.txt.*.md"))
    assert len(archived) == 1
    previous = archived[0].read_text(encoding="utf-8")
    assert first.sha256 in previous  # the digest of the replaced version
    assert "v1" in previous


def test_a_renamed_file_is_rekeyed_without_reprocessing(
    inputs_dir: Path, cache_dir: Path
) -> None:
    model = StubChatModel("processed")
    write(inputs_dir, "old-name.txt", "alpha")
    service = service_for(inputs_dir, cache_dir, model)
    service.process_all()
    (inputs_dir / "old-name.txt").rename(inputs_dir / "new-name.txt")

    report = service.process_all()

    assert report.counts == {"renamed": 1}
    assert model.call_count == 1  # no second LLM call
    assert service.read_cached("new-name.txt") == "processed\n"
    assert [item.name for item in cache_dir.glob("*.md")] == ["new-name.txt.md"]


def test_a_rename_across_formats_is_reprocessed(inputs_dir: Path, cache_dir: Path) -> None:
    model = StubChatModel("processed")
    write(inputs_dir, "guide.md", "# Heading")
    service = service_for(inputs_dir, cache_dir, model)
    service.process_all()
    (inputs_dir / "guide.md").rename(inputs_dir / "guide.txt")

    assert statuses(service) == {"guide.txt": "new"}
    assert model.call_count == 2


def test_a_deleted_file_is_reported_as_orphaned(inputs_dir: Path, cache_dir: Path) -> None:
    model = StubChatModel("processed")
    write(inputs_dir, "notes.txt", "alpha")
    write(inputs_dir, "gone.txt", "beta")
    service = service_for(inputs_dir, cache_dir, model)
    service.process_all()

    (inputs_dir / "gone.txt").unlink()
    report = service.process_all()

    assert report.counts == {"cached": 1}
    assert [entry.source for entry in report.orphaned] == ["gone.txt"]
    assert report.summarise() == "cached=1, orphaned=1"
    assert service.read_cached("gone.txt") == "processed\n"


def test_unsupported_files_are_reported_and_do_not_stop_the_run(
    inputs_dir: Path, cache_dir: Path
) -> None:
    model = StubChatModel("processed")
    write(inputs_dir, "notes.txt", "alpha")
    unsupported = write(inputs_dir, "sheet.csv", "a,b")
    service = service_for(inputs_dir, cache_dir, model)

    result = service.process_file(unsupported)

    assert result.status is CacheStatus.ERROR
    assert result.error == "No handler for .csv"
    assert statuses(service) == {"notes.txt": "new"}


def test_a_failing_handler_is_reported_with_its_cause(
    inputs_dir: Path, cache_dir: Path
) -> None:
    model = StubChatModel("processed")
    write(inputs_dir, "notes.txt", "alpha")
    service = service_for(
        inputs_dir, cache_dir, model, HandlerRegistry([RecordingHandler(model), FailingHandler()])
    )
    broken = inputs_dir / "broken.bin"
    broken.write_bytes(b"binary")

    report = service.process_all()

    assert report.counts == {"error": 1, "new": 1}
    failure = next(result for result in report.results if result.name == "broken.bin")
    assert failure.error == "RuntimeError: cannot process this file"
    assert failure.to_dict()["status"] == "error"
    assert service.cache_index().find_by_source("broken.bin") is None


def test_a_file_that_vanished_before_being_read_is_reported(
    inputs_dir: Path, cache_dir: Path
) -> None:
    service = service_for(inputs_dir, cache_dir, StubChatModel("processed"))

    result = service.process_file(inputs_dir / "nope.txt")

    assert result.status is CacheStatus.ERROR
    assert result.name == "nope.txt"
    assert result.sha256 == ""
    assert "FileNotFoundError" in result.error


def test_a_missing_input_directory_yields_no_work(tmp_path: Path, cache_dir: Path) -> None:
    service = service_for(tmp_path / "missing", cache_dir, StubChatModel("processed"))

    assert service.supported_files() == []
    assert service.process_all().summarise() == "nothing to process"


def test_supported_files_are_sorted_and_filtered(inputs_dir: Path, cache_dir: Path) -> None:
    write(inputs_dir, "b.txt", "b")
    write(inputs_dir, "a.md", "a")
    write(inputs_dir, "c.csv", "c")
    service = service_for(inputs_dir, cache_dir, StubChatModel("processed"))

    assert [path.name for path in service.supported_files()] == ["a.md", "b.txt"]
    assert service.extensions == (".md", ".pdf", ".txt")


def test_cached_content_can_be_read_by_name_hash_or_prefix(
    inputs_dir: Path, cache_dir: Path
) -> None:
    write(inputs_dir, "notes.txt", "alpha")
    service = service_for(inputs_dir, cache_dir, StubChatModel("processed"))
    entry = service.process_all().results[0]

    assert service.read_cached("notes.txt") == "processed\n"
    assert service.read_cached("notes.txt.md") == "processed\n"
    assert service.read_cached(entry.sha256) == "processed\n"
    assert service.read_cached("note") == "processed\n"


def test_ambiguous_prefixes_are_refused(inputs_dir: Path, cache_dir: Path) -> None:
    write(inputs_dir, "login-a.txt", "a")
    write(inputs_dir, "login-b.txt", "b")
    service = service_for(inputs_dir, cache_dir, StubChatModel("processed"))
    service.process_all()

    with pytest.raises(CacheLookupError, match="matches several files"):
        service.read_cached("login")


def test_entries_expose_the_cached_metadata(inputs_dir: Path, cache_dir: Path) -> None:
    write(inputs_dir, "notes.txt", "alpha")
    service = service_for(inputs_dir, cache_dir, StubChatModel("processed"))

    assert service.entries() == ()
    service.process_all()

    entry = service.entries()[0]
    assert entry.source == "notes.txt"
    assert entry.provider == "stub"
    assert entry.model == "stub-model"


def test_processing_runs_once_per_project(tmp_path: Path) -> None:
    """Two projects processed at the same time never touch each other's files."""
    services: dict[str, ProcessingService] = {}
    for name in ("alpha", "beta"):
        inputs = tmp_path / name / "inputs"
        inputs.mkdir(parents=True)
        write(inputs, "notes.txt", f"{name} content")
        services[name] = service_for(
            inputs, tmp_path / name / "cache", StubChatModel(f"{name} summary")
        )

    results: dict[str, str] = {}
    errors: list[BaseException] = []

    def run(name: str) -> None:
        try:
            results[name] = services[name].process_all().summarise()
        except BaseException as exc:  # noqa: BLE001 - reported below
            errors.append(exc)

    threads = [threading.Thread(target=run, args=(name,)) for name in services]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert not errors
    assert results == {"alpha": "new=1", "beta": "new=1"}
    for name in ("alpha", "beta"):
        assert services[name].read_cached("notes.txt") == f"{name} summary\n"
        assert [item.name for item in (tmp_path / name / "cache").glob("*.md")] == ["notes.txt.md"]
