# newprompt

CLI tool for managing Claude Code prompt history directories. Creates timestamped
directories with prompt templates, launches Claude Code sessions with tracked
session IDs, and copies/converts chat history (JSONL to Markdown) after sessions end.

## Setup

- Python >=3.10, Hatchling build system
- Install: `uv pip install -e .` (always use `uv`, never raw `pip`)

## Entry Points

- `newprompt` CLI command -> `src/newprompt/cli.py:main`
- `newprompt-mcp` -> `src/newprompt/mcp_server.py:main` (not yet implemented)

## Project Layout

```
src/newprompt/
  __init__.py    # Package init, version string
  cli.py         # All CLI logic: arg parsing, dir creation, session launch, chat history
tests/
  test_cli.py    # Unit tests for core functions (pytest)
```

## Key Concepts

- Prompt directories follow the format: `{YYYY}-{MM}-{DD}-{SEQ}-{keywords}/`
- Each directory contains: prompt.md, plan.md, chat_history.jsonl, chat_history.md, .session_id
- Default history dir: `$NEWPROMPT_HISTORY_DIR` env var > `history_dir` in config > `{cwd}/ClaudeCode_PromptHistory`
- Claude projects dir: auto-computed from cwd as `~/.claude/projects/{cwd-slug}`
- Persistent config stored at `~/.config/newprompt/config.json`

## Running Tests

```bash
pytest tests/
```

## Common CLI Usage

```bash
newprompt keyword1 keyword2          # Create prompt directory
newprompt --launch keyword1 keyword2 # Create + launch Claude Code session
newprompt --resume my-feature        # Resume a previous session
newprompt --save-chat <uuid> <dir>   # Manually save chat history
```

## Dependencies

- `mcp[cli]>=1.0.0` (only runtime dependency)
