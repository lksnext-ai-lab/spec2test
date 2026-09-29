"""The name-based cache: front-matter, archiving, migration and lookup."""

from __future__ import annotations

from pathlib import Path

import pytest

from cache.entry import (
    CacheEntry,
    FrontMatterError,
    entry_from_text,
    parse,
    render,
    timestamp_for_filename,
    utc_from_timestamp,
    utc_now,
)
from cache.index import CacheIndex
from cache.lookup import CacheLookupError, find, resolve
from cache.repository import CacheRepository
from cache.source import SourceFile
from support import source_for

HISTORY_LEGACY = ".history/legacy"


def entry_for(path: Path, sha256: str = "a" * 64, name: str | None = None) -> CacheEntry:
    return CacheEntry(
        source=name or path.name,
        format=path.suffix.lower(),
        size=10,
        sha256=sha256,
        processed_at="2026-09-29T10:00:00Z",
        provider="stub",
        model="stub-model",
        path=path,
    )


def legacy_text(name: str = "login-demo.mp4", sha256: str = "b" * 64) -> str:
    return (
        f"original_name,format,file_size,hash\n{name},{Path(name).suffix},4321,{sha256}\n"
        "=" * 50
        + "\nPROCESSED CONTENT:\n"
        + "=" * 50
        + "\nlegacy body\n"
    )


# --- front-matter ------------------------------------------------------------


def test_front_matter_round_trips() -> None:
    fields = {
        "source": "guide over: the app.md",
        "format": ".md",
        "size": 12,
        "sha256": "c" * 64,
        "processed_at": "2026-09-29T10:00:00Z",
        "provider": "stub",
        "model": "stub-model",
    }

    parsed, body = parse(render(fields) + "body line\n")

    assert parsed == fields
    assert body == "body line\n"


def test_front_matter_renders_booleans_and_quotes_unsafe_values() -> None:
    rendered = render({"flag": True, "other": False, "text": 'a "quoted" value'})

    assert 'flag: true' in rendered
    assert 'other: false' in rendered
    assert 'text: "a \\"quoted\\" value"' in rendered


def test_documents_without_front_matter_are_returned_whole() -> None:
    parsed, body = parse("# Just markdown\n")

    assert parsed == {}
    assert body == "# Just markdown\n"


def test_unterminated_front_matter_is_reported() -> None:
    with pytest.raises(FrontMatterError, match="not terminated"):
        parse("---\nsource: x\n")


def test_invalid_front_matter_line_is_reported() -> None:
    with pytest.raises(FrontMatterError, match="Invalid front-matter line"):
        parse("---\nnot-a-pair\n---\nbody")


def test_entry_from_text_requires_every_key(tmp_path: Path) -> None:
    document = render({"source": "a.txt", "format": ".txt"}) + "body"

    with pytest.raises(FrontMatterError, match="missing front-matter keys"):
        entry_from_text(document, tmp_path / "a.txt.md")


def test_entry_from_text_rejects_a_non_numeric_size(tmp_path: Path) -> None:
    document = render(entry_for(tmp_path / "a.txt").to_front_matter()).replace("size: 10", "size: big")

    with pytest.raises(FrontMatterError, match="non-numeric size"):
        entry_from_text(document, tmp_path / "a.txt.md")


def test_entry_exposes_name_and_short_hash(tmp_path: Path) -> None:
    entry = entry_for(tmp_path / "login-demo.mp4", "0123456789" + "0" * 54)

    assert entry.name == "login-demo.mp4"
    assert entry.short_hash == "01234567"


def test_timestamps_are_filesystem_safe() -> None:
    assert timestamp_for_filename("2026-09-29T10:00:00Z") == "20260929T100000Z"
    assert utc_from_timestamp(0) == "1970-01-01T00:00:00Z"
    assert utc_now().endswith("Z")


# --- repository --------------------------------------------------------------


def test_write_and_read_round_trip(cache: CacheRepository, tmp_path: Path) -> None:
    path = tmp_path / "notes.txt"
    path.write_text("hello", encoding="utf-8")
    source = source_for(path)

    entry = cache.write(source, "processed body\n", "stub", "stub-model")

    assert entry.path == cache.directory / "notes.txt.md"
    assert cache.read(entry) == "processed body\n"
    assert cache.read_by_name("notes.txt") == "processed body\n"
    assert cache.index().find_by_source("notes.txt") == entry


def test_cache_files_are_named_after_their_source(cache: CacheRepository, tmp_path: Path) -> None:
    path = tmp_path / "login-demo.mp4"
    path.write_bytes(b"video")
    cache.write(source_for(path), "body", "stub", "stub-model")

    assert [item.name for item in cache.directory.glob("*.md")] == ["login-demo.mp4.md"]


def test_invalid_names_are_refused(cache: CacheRepository) -> None:
    for name in ("", "../escape.txt", "nested/file.txt"):
        with pytest.raises(ValueError, match="Invalid source file name"):
            cache.path_for(name)


def test_paths_that_escape_the_cache_directory_are_refused(cache: CacheRepository) -> None:
    for name in (".", "..", "nested/../escape.txt", "/etc/passwd"):
        with pytest.raises(ValueError, match="Invalid source file name"):
            cache.path_for(name)


def test_archiving_refuses_an_entry_that_points_outside_the_cache(
    cache: CacheRepository, tmp_path: Path
) -> None:
    outside = tmp_path / "outside.md"
    outside.write_text("body", encoding="utf-8")

    with pytest.raises(ValueError, match="outside the cache directory"):
        cache.archive(entry_for(outside))


def test_legacy_migration_refuses_a_traversing_hash(cache: CacheRepository) -> None:
    legacy = cache.directory / f"{'b' * 64}.txt"
    legacy.write_text(legacy_text(sha256="../../escape"), encoding="utf-8")

    assert cache.migrate_legacy() == []
    assert legacy.is_file()


def test_read_by_name_returns_none_when_absent(cache: CacheRepository) -> None:
    assert cache.read_by_name("missing.txt") is None
    assert cache.read_by_name("../escape.txt") is None


def test_index_skips_unreadable_cache_files(cache: CacheRepository, tmp_path: Path) -> None:
    path = tmp_path / "notes.txt"
    path.write_text("hello", encoding="utf-8")
    cache.write(source_for(path), "body", "stub", "stub-model")
    (cache.directory / "broken.md").write_text("no front matter here", encoding="utf-8")

    index = cache.index()

    assert [entry.source for entry in index.entries] == ["notes.txt"]


def test_archiving_keeps_the_previous_version(cache: CacheRepository, tmp_path: Path) -> None:
    path = tmp_path / "notes.txt"
    path.write_text("hello", encoding="utf-8")
    entry = cache.write(source_for(path), "first", "stub", "stub-model")

    archived = cache.archive(entry)

    assert not entry.path.exists()
    assert archived.name.startswith(f"notes.txt.{entry.short_hash}.")
    assert archived.name.endswith("Z.md")
    assert archived.parent == cache.history_dir
    assert "first" in archived.read_text(encoding="utf-8")


def test_archiving_twice_does_not_overwrite(cache: CacheRepository, tmp_path: Path) -> None:
    path = tmp_path / "notes.txt"
    path.write_text("hello", encoding="utf-8")
    first = cache.write(source_for(path), "first", "stub", "stub-model")
    cache.archive(first)
    second = cache.write(source_for(path), "second", "stub", "stub-model")

    archived = cache.archive(second)

    assert archived.name.endswith("-1.md")
    assert len(list(cache.history_dir.glob("*.md"))) == 2


def test_rename_rekeys_without_touching_the_content(cache: CacheRepository, tmp_path: Path) -> None:
    original = tmp_path / "old-name.txt"
    original.write_text("hello", encoding="utf-8")
    entry = cache.write(source_for(original), "unchanged body", "stub", "stub-model")

    renamed_path = tmp_path / "new-name.txt"
    renamed_path.write_text("hello", encoding="utf-8")
    renamed = cache.rename(entry, source_for(renamed_path))

    assert renamed.source == "new-name.txt"
    assert renamed.path == cache.directory / "new-name.txt.md"
    assert renamed.sha256 == entry.sha256
    assert cache.read(renamed).strip() == "unchanged body"
    assert not entry.path.exists()


# --- legacy migration --------------------------------------------------------


def test_legacy_cache_is_migrated_to_the_named_layout(cache: CacheRepository) -> None:
    legacy = cache.directory / f"{'b' * 64}.txt"
    legacy.write_text(legacy_text(), encoding="utf-8")

    migrated = cache.migrate_legacy()

    assert [entry.source for entry in migrated] == ["login-demo.mp4"]
    migrated_entry = migrated[0]
    assert migrated_entry.path == cache.directory / "login-demo.mp4.md"
    assert migrated_entry.size == 4321
    assert migrated_entry.provider == "legacy"
    assert "legacy body" in cache.read(migrated_entry)


def test_legacy_files_are_parked_not_deleted(cache: CacheRepository) -> None:
    legacy = cache.directory / f"{'b' * 64}.txt"
    legacy.write_text(legacy_text(), encoding="utf-8")

    cache.migrate_legacy()

    parked = cache.directory / HISTORY_LEGACY / f"{'b' * 64}.txt"
    assert parked.is_file()
    assert not legacy.exists()


def test_migrating_twice_is_harmless(cache: CacheRepository) -> None:
    legacy = cache.directory / f"{'b' * 64}.txt"
    legacy.write_text(legacy_text(), encoding="utf-8")
    cache.migrate_legacy()

    assert cache.migrate_legacy() == []
    assert len(list(cache.directory.glob("*.md"))) == 1


def test_an_already_migrated_legacy_file_is_only_parked(cache: CacheRepository) -> None:
    path = cache.directory / "login-demo.mp4.md"
    path.write_text(render(entry_for(path, "b" * 64, "login-demo.mp4").to_front_matter()) + "kept\n")
    legacy = cache.directory / f"{'b' * 64}.txt"
    legacy.write_text(legacy_text(), encoding="utf-8")

    assert cache.migrate_legacy() == []
    assert "kept" in path.read_text(encoding="utf-8")
    assert (cache.directory / HISTORY_LEGACY / f"{'b' * 64}.txt").is_file()


def test_unparseable_legacy_files_are_left_alone(cache: CacheRepository) -> None:
    legacy = cache.directory / "not-a-cache.txt"
    legacy.write_text("just some text", encoding="utf-8")

    assert cache.migrate_legacy() == []
    assert legacy.is_file()


def test_legacy_entry_falls_back_to_the_file_name(cache: CacheRepository) -> None:
    sha256 = "c" * 64
    body = (
        f"hash,format,file_size,extra\n{sha256},.txt,5,x\n"
        + "=" * 50
        + "\nPROCESSED CONTENT:\nbody\n"
    )
    legacy = cache.directory / f"{sha256}.txt"
    legacy.write_text(body, encoding="utf-8")

    migrated = cache.migrate_legacy()

    assert migrated[0].source == f"{sha256}.md"
    assert migrated[0].size == 5


# --- lookup ------------------------------------------------------------------


def index_of(*entries: CacheEntry) -> CacheIndex:
    return CacheIndex.build(entries)


def test_lookup_by_name_sha_and_prefix(tmp_path: Path) -> None:
    digest = "a" * 32 + "b" * 32
    entry = entry_for(tmp_path / "login-demo.mp4", digest)
    index = index_of(entry)

    assert resolve(index, "login-demo.mp4") is entry
    assert resolve(index, "login-demo.mp4.md") is entry
    assert resolve(index, digest) is entry
    assert resolve(index, "aaaa") is entry
    assert resolve(index, "login") is entry
    assert find(index, "nope") is None


def test_lookup_reports_an_ambiguous_prefix(tmp_path: Path) -> None:
    index = index_of(
        entry_for(tmp_path / "login-demo.mp4", name="login-demo.mp4"),
        entry_for(tmp_path / "login-admin.mp4", name="login-admin.mp4"),
    )

    with pytest.raises(CacheLookupError, match="matches several files"):
        resolve(index, "login")


def test_lookup_explains_an_empty_key(tmp_path: Path) -> None:
    with pytest.raises(CacheLookupError, match="No file specified"):
        resolve(index_of(entry_for(tmp_path / "a.txt")), "   ")


def test_lookup_explains_a_missing_key(tmp_path: Path) -> None:
    with pytest.raises(CacheLookupError, match="No cached content for 'x'"):
        resolve(index_of(), "x")


def test_index_reports_orphans(tmp_path: Path) -> None:
    index = index_of(
        entry_for(tmp_path / "kept.txt", name="kept.txt"),
        entry_for(tmp_path / "gone.txt", name="gone.txt"),
    )

    assert [entry.source for entry in index.orphaned(["kept.txt"])] == ["gone.txt"]
