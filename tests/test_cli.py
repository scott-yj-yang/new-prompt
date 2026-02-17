"""Tests for newprompt CLI core logic."""

import json
import os
import tempfile
import datetime
from newprompt.cli import get_next_seq, create_prompt_dir, write_prompt_md, jsonl_to_markdown, save_chat, load_config, save_config, CONFIG_DEFAULTS, find_session


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


def test_jsonl_to_markdown_basic():
    """Should convert user and assistant messages to readable markdown."""
    lines = [
        json.dumps({"type": "user", "message": {"content": "Hello, how are you?"}, "timestamp": "2026-02-17T10:00:00.000Z"}),
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "I'm doing well! How can I help?"}]}, "timestamp": "2026-02-17T10:00:05.000Z"}),
    ]
    with tempfile.TemporaryDirectory() as tmpdir:
        jsonl_path = os.path.join(tmpdir, "chat.jsonl")
        with open(jsonl_path, "w") as f:
            f.write("\n".join(lines) + "\n")
        md = jsonl_to_markdown(jsonl_path)
        assert "## User" in md
        assert "Hello, how are you?" in md
        assert "## Assistant" in md
        assert "I'm doing well! How can I help?" in md


def test_jsonl_to_markdown_skips_non_conversation():
    """Should skip summary and file-history-snapshot types."""
    lines = [
        json.dumps({"type": "summary", "summary": "Test summary"}),
        json.dumps({"type": "file-history-snapshot", "snapshot": {}}),
        json.dumps({"type": "user", "message": {"content": "Hi"}, "timestamp": "2026-02-17T10:00:00.000Z"}),
    ]
    with tempfile.TemporaryDirectory() as tmpdir:
        jsonl_path = os.path.join(tmpdir, "chat.jsonl")
        with open(jsonl_path, "w") as f:
            f.write("\n".join(lines) + "\n")
        md = jsonl_to_markdown(jsonl_path)
        assert "## User" in md
        assert "Hi" in md


def test_jsonl_to_markdown_tool_use():
    """Should show tool use as a summary line, not raw JSON."""
    lines = [
        json.dumps({
            "type": "assistant",
            "message": {"content": [
                {"type": "text", "text": "Let me read that file."},
                {"type": "tool_use", "name": "Read", "input": {"file_path": "/tmp/foo.py"}},
            ]},
            "timestamp": "2026-02-17T10:00:00.000Z",
        }),
    ]
    with tempfile.TemporaryDirectory() as tmpdir:
        jsonl_path = os.path.join(tmpdir, "chat.jsonl")
        with open(jsonl_path, "w") as f:
            f.write("\n".join(lines) + "\n")
        md = jsonl_to_markdown(jsonl_path)
        assert "Let me read that file." in md
        assert "Read" in md
        assert "tool_use" not in md


def test_save_chat_creates_markdown(tmp_path):
    """save_chat should produce both .jsonl and .md files."""
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()
    session_id = "test-session-123"
    jsonl_file = projects_dir / f"{session_id}.jsonl"
    lines = [
        json.dumps({"type": "user", "message": {"content": "Hello"}, "timestamp": "2026-02-17T10:00:00.000Z"}),
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "Hi there!"}]}, "timestamp": "2026-02-17T10:00:01.000Z"}),
    ]
    jsonl_file.write_text("\n".join(lines) + "\n")
    prompt_dir = tmp_path / "prompt"
    prompt_dir.mkdir()
    save_chat(session_id, str(prompt_dir), str(projects_dir))
    assert (prompt_dir / "chat_history.jsonl").exists()
    assert (prompt_dir / "chat_history.md").exists()
    md_content = (prompt_dir / "chat_history.md").read_text()
    assert "Hello" in md_content
    assert "Hi there!" in md_content


def test_load_config_no_file(tmp_path):
    """Should return defaults when no config file exists."""
    config = load_config(config_path=str(tmp_path / "config.json"))
    assert config == CONFIG_DEFAULTS


def test_save_and_load_config(tmp_path):
    """Should persist config to disk and load it back."""
    config_path = str(tmp_path / "config.json")
    save_config({"always_launch": True}, config_path=config_path)
    config = load_config(config_path=config_path)
    assert config["always_launch"] is True


def test_save_config_creates_parent_dirs(tmp_path):
    """Should create parent directories if they don't exist."""
    config_path = str(tmp_path / "subdir" / "config.json")
    save_config({"always_launch": True}, config_path=config_path)
    assert os.path.exists(config_path)


def test_always_launch_sets_config(tmp_path):
    """--always-launch should persist to config."""
    config_path = str(tmp_path / "config.json")
    save_config({"always_launch": True}, config_path=config_path)
    config = load_config(config_path=config_path)
    assert config["always_launch"] is True


def test_skip_permissions_config(tmp_path):
    """--skip-permissions should persist to config."""
    config_path = str(tmp_path / "config.json")
    save_config({"skip_permissions": True}, config_path=config_path)
    config = load_config(config_path=config_path)
    assert config["skip_permissions"] is True


def test_skip_permissions_default_false(tmp_path):
    """skip_permissions should default to False."""
    config = load_config(config_path=str(tmp_path / "config.json"))
    assert config["skip_permissions"] is False


def test_find_session_by_directory_name(tmp_path):
    """Should find session ID from a prompt directory's .session_id file."""
    history_dir = tmp_path / "history"
    prompt_dir = history_dir / "2-17-26-1-my-feature"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / ".session_id").write_text("abc-123-def")

    session_id, dirpath = find_session("2-17-26-1-my-feature", str(history_dir))
    assert session_id == "abc-123-def"
    assert dirpath == str(prompt_dir)


def test_find_session_by_partial_match(tmp_path):
    """Should find session by partial keyword match."""
    history_dir = tmp_path / "history"
    prompt_dir = history_dir / "2-17-26-1-my-feature"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / ".session_id").write_text("abc-123-def")

    session_id, dirpath = find_session("my-feature", str(history_dir))
    assert session_id == "abc-123-def"
    assert dirpath == str(prompt_dir)


def test_find_session_by_uuid(tmp_path):
    """Should find session when given a raw UUID (searches all .session_id files)."""
    history_dir = tmp_path / "history"
    prompt_dir = history_dir / "2-17-26-1-my-feature"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / ".session_id").write_text("abc-123-def")

    session_id, dirpath = find_session("abc-123-def", str(history_dir))
    assert session_id == "abc-123-def"
    assert dirpath == str(prompt_dir)


def test_find_session_not_found(tmp_path):
    """Should return None, None when no match is found."""
    history_dir = tmp_path / "history"
    history_dir.mkdir()

    session_id, dirpath = find_session("nonexistent", str(history_dir))
    assert session_id is None
    assert dirpath is None
