"""Tests for the newprompt MCP server tools."""

import os
import tempfile
from unittest.mock import patch
import pytest
from newprompt.mcp_server import (
    _find_latest_session_dir,
    _init_session_logic,
    _continue_session_logic,
    _get_session_info_logic,
)


@patch("newprompt.mcp_server.read_current_session_marker", return_value=None)
def test_find_latest_session_dir(_mock_marker, tmp_path):
    """Should find the most recently created session directory."""
    dir1 = tmp_path / "2026-02-22-1-foo"
    dir1.mkdir()
    (dir1 / "prompt.md").touch()

    dir2 = tmp_path / "2026-02-22-2-bar"
    dir2.mkdir()
    (dir2 / "prompt.md").touch()

    result = _find_latest_session_dir(str(tmp_path))
    assert result == str(dir2)


@patch("newprompt.mcp_server.read_current_session_marker", return_value=None)
def test_find_latest_session_dir_empty(_mock_marker, tmp_path):
    """Should return None when no session dirs exist."""
    result = _find_latest_session_dir(str(tmp_path))
    assert result is None


@patch("newprompt.mcp_server.read_current_session_marker", return_value=None)
def test_find_latest_session_dir_skips_underscore(_mock_marker, tmp_path):
    """Should skip directories starting with underscore."""
    archive = tmp_path / "_archive"
    archive.mkdir()
    (archive / "prompt.md").touch()

    result = _find_latest_session_dir(str(tmp_path))
    assert result is None


def test_init_session_logic(tmp_path):
    """Should create session directory with prompt.md."""
    result = _init_session_logic("test feature", str(tmp_path))
    assert "session_dir" in result
    assert os.path.isdir(result["session_dir"])
    prompt_path = os.path.join(result["session_dir"], "prompt.md")
    assert os.path.exists(prompt_path)
    content = open(prompt_path).read()
    assert "plan.md" in content


def test_init_session_logic_empty_keywords(tmp_path):
    """Should return error for empty keywords."""
    result = _init_session_logic("", str(tmp_path))
    assert "error" in result


def test_continue_session_logic(tmp_path):
    """Should create indexed prompt file."""
    session_dir = tmp_path / "2026-02-22-1-test"
    session_dir.mkdir()
    (session_dir / "prompt.md").write_text("original prompt")

    result = _continue_session_logic(
        str(session_dir), "Fix the login bug"
    )
    assert result["prompt_index"] == 1
    assert result["prompt_file"].endswith("prompt1.md")
    assert result["plan_file"].endswith("plan1.md")
    assert os.path.exists(result["prompt_file"])

    content = open(result["prompt_file"]).read()
    assert "Fix the login bug" in content
    assert "plan1.md" in content


def test_continue_session_increments(tmp_path):
    """Should increment index for each continuation."""
    session_dir = tmp_path / "2026-02-22-1-test"
    session_dir.mkdir()
    (session_dir / "prompt.md").write_text("original")
    (session_dir / "prompt1.md").write_text("second")

    result = _continue_session_logic(str(session_dir), "Third task")
    assert result["prompt_index"] == 2
    assert result["prompt_file"].endswith("prompt2.md")
    assert result["plan_file"].endswith("plan2.md")


def test_continue_session_nonexistent_dir(tmp_path):
    """Should return error for nonexistent directory."""
    result = _continue_session_logic(str(tmp_path / "nonexistent"), "test")
    assert "error" in result


def test_get_session_info_logic(tmp_path):
    """Should return session state."""
    session_dir = tmp_path / "2026-02-22-1-test"
    session_dir.mkdir()
    (session_dir / "prompt.md").write_text("original")
    (session_dir / "prompt1.md").write_text("second")
    (session_dir / "plan.md").write_text("plan 0")

    result = _get_session_info_logic(str(session_dir))
    assert result["session_dir"] == str(session_dir)
    assert result["prompt_count"] == 2  # prompt.md + prompt1.md
    assert "prompt.md" in result["prompts"]
    assert "prompt1.md" in result["prompts"]
    assert "plan.md" in result["plans"]


def test_get_session_info_nonexistent_dir(tmp_path):
    """Should return error for nonexistent directory."""
    result = _get_session_info_logic(str(tmp_path / "nonexistent"))
    assert "error" in result
