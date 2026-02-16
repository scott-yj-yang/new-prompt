"""Tests for newprompt CLI core logic."""

import os
import tempfile
import datetime
from newprompt.cli import get_next_seq, create_prompt_dir, write_prompt_md


def test_get_next_seq_empty_dir():
    """First prompt of the day should get sequence 1."""
    with tempfile.TemporaryDirectory() as tmpdir:
        seq = get_next_seq("2-16-26", history_dir=tmpdir)
        assert seq == 1


def test_get_next_seq_existing():
    """Should return max existing seq + 1."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, "2-16-26-1-foo"))
        os.makedirs(os.path.join(tmpdir, "2-16-26-3-bar"))
        seq = get_next_seq("2-16-26", history_dir=tmpdir)
        assert seq == 4


def test_create_prompt_dir():
    """Should create directory with correct name format."""
    with tempfile.TemporaryDirectory() as tmpdir:
        dirpath = create_prompt_dir(
            ["CNN", "debug"], history_dir=tmpdir, seq_override=5
        )
        assert os.path.isdir(dirpath)
        basename = os.path.basename(dirpath)
        assert "-5-cnn-debug" in basename


def test_write_prompt_md():
    """Should write prompt.md with blank lines and footer."""
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = write_prompt_md(tmpdir)
        assert os.path.exists(filepath)
        content = open(filepath).read()
        assert "Please write your plan" in content
        assert tmpdir in content
        # Should have blank lines at the top
        assert content.startswith("\n")
