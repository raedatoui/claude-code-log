#!/usr/bin/env python3
"""Tests for project working directory matching functionality."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from claude_code_log.cli import find_projects_by_cwd


class TestProjectMatching:
    """Test cases for working directory based project matching."""

    def test_find_projects_by_cwd_with_cache(self):
        """Test finding projects by current working directory using cache data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            projects_dir = Path(temp_dir)

            # Create mock project directories
            project1 = projects_dir / "project1"
            project2 = projects_dir / "project2"
            project1.mkdir()
            project2.mkdir()

            # Create mock JSONL files
            (project1 / "test1.jsonl").touch()
            (project2 / "test2.jsonl").touch()

            # Mock cache data for projects
            mock_cache1 = Mock()
            mock_cache1.working_directories = ["/Users/test/workspace/myproject"]

            mock_cache2 = Mock()
            mock_cache2.working_directories = ["/Users/test/other/project"]

            with patch("claude_code_log.cli.CacheManager") as mock_cache_manager:

                def cache_side_effect(project_dir, version):
                    cache_instance = Mock()
                    if project_dir == project1:
                        cache_instance.get_cached_project_data.return_value = (
                            mock_cache1
                        )
                    elif project_dir == project2:
                        cache_instance.get_cached_project_data.return_value = (
                            mock_cache2
                        )
                    else:
                        cache_instance.get_cached_project_data.return_value = None
                    return cache_instance

                mock_cache_manager.side_effect = cache_side_effect

                # Test matching current working directory
                matching_projects = find_projects_by_cwd(
                    projects_dir, "/Users/test/workspace/myproject"
                )
                assert len(matching_projects) == 1
                assert matching_projects[0] == project1

                # Test non-matching current working directory
                matching_projects = find_projects_by_cwd(
                    projects_dir, "/Users/test/completely/different"
                )
                assert len(matching_projects) == 0

    def test_find_projects_by_cwd_subdirectory_matching(self):
        """Test that subdirectories of project working directories are matched."""
        with tempfile.TemporaryDirectory() as temp_dir:
            projects_dir = Path(temp_dir)

            # Create mock project directory
            project1 = projects_dir / "project1"
            project1.mkdir()
            (project1 / "test1.jsonl").touch()

            # Mock cache data with parent directory
            mock_cache1 = Mock()
            mock_cache1.working_directories = ["/Users/test/workspace/myproject"]

            with patch("claude_code_log.cli.CacheManager") as mock_cache_manager:

                def cache_side_effect(project_dir, version):
                    cache_instance = Mock()
                    if project_dir == project1:
                        cache_instance.get_cached_project_data.return_value = (
                            mock_cache1
                        )
                    else:
                        cache_instance.get_cached_project_data.return_value = None
                    return cache_instance

                mock_cache_manager.side_effect = cache_side_effect

                # Test from subdirectory
                matching_projects = find_projects_by_cwd(
                    projects_dir, "/Users/test/workspace/myproject/subdir"
                )
                assert len(matching_projects) == 1
                assert matching_projects[0] == project1

    def test_find_projects_by_cwd_fallback_to_name_matching(self):
        """Test fallback to project name matching when no cache data available."""
        with tempfile.TemporaryDirectory() as temp_dir:
            projects_dir = Path(temp_dir)

            # Create project with Claude-style naming convention
            project_name = "-Users-test-workspace-myproject"
            project1 = projects_dir / project_name
            project1.mkdir()
            (project1 / "test1.jsonl").touch()

            with patch("claude_code_log.cli.CacheManager") as mock_cache_manager:
                # Mock no cache data available
                cache_instance = Mock()
                cache_instance.get_cached_project_data.return_value = None
                mock_cache_manager.return_value = cache_instance

                # Test matching based on reconstructed path from project name
                matching_projects = find_projects_by_cwd(
                    projects_dir, "/Users/test/workspace/myproject"
                )
                assert len(matching_projects) == 1
                assert matching_projects[0] == project1

    def test_find_projects_by_cwd_default_current_directory(self):
        """Test using current working directory when none specified."""
        with tempfile.TemporaryDirectory() as temp_dir:
            projects_dir = Path(temp_dir)

            with (
                patch("claude_code_log.cli.os.getcwd") as mock_getcwd,
                patch("claude_code_log.cli.CacheManager") as mock_cache_manager,
            ):
                mock_getcwd.return_value = "/current/working/directory"

                # Mock no projects found
                cache_instance = Mock()
                cache_instance.get_cached_project_data.return_value = None
                mock_cache_manager.return_value = cache_instance

                # Should use current working directory from os.getcwd()
                find_projects_by_cwd(projects_dir)  # No cwd specified

                # Verify os.getcwd() was called
                mock_getcwd.assert_called_once()
