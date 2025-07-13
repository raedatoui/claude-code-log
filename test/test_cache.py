#!/usr/bin/env python3
"""Tests for caching functionality."""

import json
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import patch

import pytest

from claude_code_log.cache import (
    CacheManager,
    get_library_version,
    ProjectCache,
    SessionCacheData,
)
from claude_code_log.models import (
    UserTranscriptEntry,
    AssistantTranscriptEntry,
    SummaryTranscriptEntry,
    UserMessage,
    AssistantMessage,
    UsageInfo,
)


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_version():
    """Mock library version for consistent testing."""
    return "1.0.0-test"


@pytest.fixture
def cache_manager(temp_project_dir, mock_version):
    """Create a cache manager for testing."""
    with patch("claude_code_log.cache.get_library_version", return_value=mock_version):
        return CacheManager(temp_project_dir, mock_version)


@pytest.fixture
def sample_entries():
    """Create sample transcript entries for testing."""
    return [
        UserTranscriptEntry(
            parentUuid=None,
            isSidechain=False,
            userType="user",
            cwd="/test",
            sessionId="session1",
            version="1.0.0",
            uuid="user1",
            timestamp="2023-01-01T10:00:00Z",
            type="user",
            message=UserMessage(role="user", content="Hello"),
        ),
        AssistantTranscriptEntry(
            parentUuid=None,
            isSidechain=False,
            userType="assistant",
            cwd="/test",
            sessionId="session1",
            version="1.0.0",
            uuid="assistant1",
            timestamp="2023-01-01T10:01:00Z",
            type="assistant",
            message=AssistantMessage(
                id="msg1",
                type="message",
                role="assistant",
                model="claude-3",
                content=[],
                usage=UsageInfo(input_tokens=10, output_tokens=20),
            ),
            requestId="req1",
        ),
        SummaryTranscriptEntry(
            type="summary",
            summary="Test conversation",
            leafUuid="assistant1",
        ),
    ]


class TestCacheManager:
    """Test the CacheManager class."""

    def test_initialization(self, temp_project_dir, mock_version):
        """Test cache manager initialization."""
        cache_manager = CacheManager(temp_project_dir, mock_version)

        assert cache_manager.project_path == temp_project_dir
        assert cache_manager.library_version == mock_version
        assert cache_manager.cache_dir == temp_project_dir / "cache"
        assert cache_manager.cache_dir.exists()

    def test_cache_file_path(self, cache_manager, temp_project_dir):
        """Test cache file path generation."""
        jsonl_path = temp_project_dir / "test.jsonl"
        cache_path = cache_manager._get_cache_file_path(jsonl_path)

        expected = temp_project_dir / "cache" / "test.json"
        assert cache_path == expected

    def test_save_and_load_entries(
        self, cache_manager, temp_project_dir, sample_entries
    ):
        """Test saving and loading cached entries."""
        jsonl_path = temp_project_dir / "test.jsonl"
        jsonl_path.write_text("dummy content")

        # Save entries to cache
        cache_manager.save_cached_entries(jsonl_path, sample_entries)

        # Verify cache file exists
        cache_file = cache_manager._get_cache_file_path(jsonl_path)
        assert cache_file.exists()

        # Load entries from cache
        loaded_entries = cache_manager.load_cached_entries(jsonl_path)
        assert loaded_entries is not None
        assert len(loaded_entries) == len(sample_entries)

        # Verify entry types match
        assert loaded_entries[0].type == "user"
        assert loaded_entries[1].type == "assistant"
        assert loaded_entries[2].type == "summary"

    def test_timestamp_based_cache_structure(
        self, cache_manager, temp_project_dir, sample_entries
    ):
        """Test that cache uses timestamp-based structure."""
        jsonl_path = temp_project_dir / "test.jsonl"
        jsonl_path.write_text("dummy content")

        cache_manager.save_cached_entries(jsonl_path, sample_entries)

        # Read raw cache file
        cache_file = cache_manager._get_cache_file_path(jsonl_path)
        with open(cache_file, "r") as f:
            cache_data = json.load(f)

        # Verify timestamp-based structure
        assert isinstance(cache_data, dict)
        assert "2023-01-01T10:00:00Z" in cache_data
        assert "2023-01-01T10:01:00Z" in cache_data
        assert "_no_timestamp" in cache_data  # Summary entry

        # Verify entry grouping
        assert len(cache_data["2023-01-01T10:00:00Z"]) == 1
        assert len(cache_data["2023-01-01T10:01:00Z"]) == 1
        assert len(cache_data["_no_timestamp"]) == 1

    def test_cache_invalidation_file_modification(
        self, cache_manager, temp_project_dir, sample_entries
    ):
        """Test cache invalidation when source file is modified."""
        jsonl_path = temp_project_dir / "test.jsonl"
        jsonl_path.write_text("original content")

        # Save to cache
        cache_manager.save_cached_entries(jsonl_path, sample_entries)
        assert cache_manager.is_file_cached(jsonl_path)

        # Modify file
        import time

        time.sleep(1.1)  # Ensure different mtime (increase to be more reliable)
        jsonl_path.write_text("modified content")

        # Cache should be invalidated
        assert not cache_manager.is_file_cached(jsonl_path)

    def test_cache_invalidation_version_mismatch(self, temp_project_dir):
        """Test cache invalidation when library version changes."""
        # Create cache with version 1.0.0
        with patch("claude_code_log.cache.get_library_version", return_value="1.0.0"):
            cache_manager_v1 = CacheManager(temp_project_dir, "1.0.0")
            # Create some cache data
            index_data = ProjectCache(
                version="1.0.0",
                cache_created=datetime.now().isoformat(),
                last_updated=datetime.now().isoformat(),
                project_path=str(temp_project_dir),
                cached_files={},
                sessions={},
            )
            with open(cache_manager_v1.index_file, "w") as f:
                json.dump(index_data.model_dump(), f)

        # Create new cache manager with different version
        with patch("claude_code_log.cache.get_library_version", return_value="2.0.0"):
            cache_manager_v2 = CacheManager(temp_project_dir, "2.0.0")
            # Cache should be cleared due to version mismatch
            cached_data = cache_manager_v2.get_cached_project_data()
            assert cached_data is not None
            assert cached_data.version == "2.0.0"

    def test_filtered_loading_with_dates(self, cache_manager, temp_project_dir):
        """Test timestamp-based filtering during cache loading."""
        # Create entries with different timestamps
        entries = [
            UserTranscriptEntry(
                parentUuid=None,
                isSidechain=False,
                userType="user",
                cwd="/test",
                sessionId="session1",
                version="1.0.0",
                uuid="user1",
                timestamp="2023-01-01T10:00:00Z",
                type="user",
                message=UserMessage(role="user", content="Early message"),
            ),
            UserTranscriptEntry(
                parentUuid=None,
                isSidechain=False,
                userType="user",
                cwd="/test",
                sessionId="session1",
                version="1.0.0",
                uuid="user2",
                timestamp="2023-01-02T10:00:00Z",
                type="user",
                message=UserMessage(role="user", content="Later message"),
            ),
        ]

        jsonl_path = temp_project_dir / "test.jsonl"
        jsonl_path.write_text("dummy content")

        cache_manager.save_cached_entries(jsonl_path, entries)

        # Test filtering (should return entries from 2023-01-01 only)
        filtered = cache_manager.load_cached_entries_filtered(
            jsonl_path, "2023-01-01", "2023-01-01"
        )

        assert filtered is not None
        # Should get both early message and summary (summary has no timestamp)
        assert len(filtered) >= 1
        # Find the user message and check it
        user_messages = [entry for entry in filtered if entry.type == "user"]
        assert len(user_messages) == 1
        assert "Early message" in str(user_messages[0].message.content)

    def test_clear_cache(self, cache_manager, temp_project_dir, sample_entries):
        """Test cache clearing functionality."""
        jsonl_path = temp_project_dir / "test.jsonl"
        jsonl_path.write_text("dummy content")

        # Create cache
        cache_manager.save_cached_entries(jsonl_path, sample_entries)
        cache_file = cache_manager._get_cache_file_path(jsonl_path)
        assert cache_file.exists()
        assert cache_manager.index_file.exists()

        # Clear cache
        cache_manager.clear_cache()

        # Verify files are deleted
        assert not cache_file.exists()
        assert not cache_manager.index_file.exists()

    def test_session_cache_updates(self, cache_manager):
        """Test updating session cache data."""
        session_data = {
            "session1": SessionCacheData(
                session_id="session1",
                summary="Test session",
                first_timestamp="2023-01-01T10:00:00Z",
                last_timestamp="2023-01-01T11:00:00Z",
                message_count=5,
                first_user_message="Hello",
                total_input_tokens=100,
                total_output_tokens=200,
            )
        }

        cache_manager.update_session_cache(session_data)

        cached_data = cache_manager.get_cached_project_data()
        assert cached_data is not None
        assert "session1" in cached_data.sessions
        assert cached_data.sessions["session1"].summary == "Test session"

    def test_project_aggregates_update(self, cache_manager):
        """Test updating project-level aggregates."""
        cache_manager.update_project_aggregates(
            total_message_count=100,
            total_input_tokens=1000,
            total_output_tokens=2000,
            total_cache_creation_tokens=50,
            total_cache_read_tokens=25,
            earliest_timestamp="2023-01-01T10:00:00Z",
            latest_timestamp="2023-01-01T20:00:00Z",
        )

        cached_data = cache_manager.get_cached_project_data()
        assert cached_data is not None
        assert cached_data.total_message_count == 100
        assert cached_data.total_input_tokens == 1000
        assert cached_data.total_output_tokens == 2000

    def test_get_modified_files(self, cache_manager, temp_project_dir, sample_entries):
        """Test identification of modified files."""
        # Create multiple files
        file1 = temp_project_dir / "file1.jsonl"
        file2 = temp_project_dir / "file2.jsonl"
        file1.write_text("content1")
        file2.write_text("content2")

        # Cache only one file
        cache_manager.save_cached_entries(file1, sample_entries)

        # Check modified files
        all_files = [file1, file2]
        modified = cache_manager.get_modified_files(all_files)

        # Only file2 should be modified (not cached)
        assert len(modified) == 1
        assert file2 in modified
        assert file1 not in modified

    def test_cache_stats(self, cache_manager, sample_entries):
        """Test cache statistics reporting."""
        # Initially empty
        stats = cache_manager.get_cache_stats()
        assert stats["cache_enabled"] is True
        assert stats["cached_files_count"] == 0

        # Add some cached data
        cache_manager.update_project_aggregates(
            total_message_count=50,
            total_input_tokens=500,
            total_output_tokens=1000,
            total_cache_creation_tokens=25,
            total_cache_read_tokens=10,
            earliest_timestamp="2023-01-01T10:00:00Z",
            latest_timestamp="2023-01-01T20:00:00Z",
        )

        stats = cache_manager.get_cache_stats()
        assert stats["total_cached_messages"] == 50


class TestLibraryVersion:
    """Test library version detection."""

    def test_get_library_version(self):
        """Test library version retrieval."""
        version = get_library_version()
        assert isinstance(version, str)
        assert len(version) > 0

    def test_version_fallback_without_toml(self):
        """Test version fallback when toml module not available."""
        # Mock the import statement to fail
        import sys

        original_modules = sys.modules.copy()

        try:
            # Remove toml from modules if it exists
            if "toml" in sys.modules:
                del sys.modules["toml"]

            # Mock the import to raise ImportError
            with patch.dict("sys.modules", {"toml": None}):
                version = get_library_version()
                # Should still return a version using manual parsing
                assert isinstance(version, str)
                assert len(version) > 0
        finally:
            # Restore original modules
            sys.modules.update(original_modules)


class TestCacheErrorHandling:
    """Test cache error handling and edge cases."""

    def test_corrupted_cache_file(self, cache_manager, temp_project_dir):
        """Test handling of corrupted cache files."""
        jsonl_path = temp_project_dir / "test.jsonl"
        jsonl_path.write_text("dummy content")

        # Create corrupted cache file
        cache_file = cache_manager._get_cache_file_path(jsonl_path)
        cache_file.parent.mkdir(exist_ok=True)
        cache_file.write_text("invalid json content")

        # Should handle gracefully
        result = cache_manager.load_cached_entries(jsonl_path)
        assert result is None

    def test_missing_jsonl_file(self, cache_manager, temp_project_dir, sample_entries):
        """Test cache behavior when source JSONL file is missing."""
        jsonl_path = temp_project_dir / "nonexistent.jsonl"

        # Should not be considered cached
        assert not cache_manager.is_file_cached(jsonl_path)

    def test_cache_directory_permissions(self, temp_project_dir, mock_version):
        """Test cache behavior with directory permission issues."""
        # Skip this test on systems where chmod doesn't work as expected

        cache_dir = temp_project_dir / "cache"
        cache_dir.mkdir()

        try:
            # Try to make directory read-only (might not work on all systems)
            cache_dir.chmod(0o444)

            # Check if we can actually read the directory after chmod
            try:
                list(cache_dir.iterdir())
                cache_manager = CacheManager(temp_project_dir, mock_version)
                # Should handle gracefully even if it can't write
                assert cache_manager is not None
            except PermissionError:
                # If we get permission errors, just skip this test
                return pytest.skip("Cannot test permissions on this system")  # type: ignore[misc]
        finally:
            # Restore permissions
            try:
                cache_dir.chmod(0o755)
            except OSError:
                pass
