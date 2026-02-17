#!/usr/bin/env python3
"""newprompt - Create Claude Code prompt history directories.

Usage:
    newprompt keyword1 keyword2 ...
    newprompt --launch keyword1 keyword2 ...
    newprompt --save-chat SESSION_ID PROMPT_DIR
"""

import argparse
import datetime
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import uuid

DEFAULT_HISTORY_DIR = "/home/talmolab/Desktop/SalkResearch/ClaudeCode_PromptHistory"
DEFAULT_CLAUDE_PROJECTS_DIR = os.path.expanduser(
    "~/.claude/projects/-home-talmolab-Desktop-SalkResearch"
)
DEFAULT_CONFIG_PATH = os.path.expanduser("~/.config/newprompt/config.json")
CONFIG_DEFAULTS = {"always_launch": False, "skip_permissions": False}


def load_config(config_path: str = DEFAULT_CONFIG_PATH) -> dict:
    """Load config from disk, returning defaults if file doesn't exist."""
    if not os.path.exists(config_path):
        return dict(CONFIG_DEFAULTS)
    with open(config_path) as f:
        stored = json.load(f)
    config = dict(CONFIG_DEFAULTS)
    config.update(stored)
    return config


def save_config(config: dict, config_path: str = DEFAULT_CONFIG_PATH) -> None:
    """Persist config to disk."""
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
        f.write("\n")


def get_next_seq(date_prefix: str, history_dir: str = DEFAULT_HISTORY_DIR) -> int:
    """Find the next sequence number for a given date prefix."""
    pattern = os.path.join(history_dir, f"{date_prefix}-*")
    existing = glob.glob(pattern)
    max_seq = 0
    for d in existing:
        basename = os.path.basename(d)
        match = re.match(rf"^{re.escape(date_prefix)}-(\d+)-", basename)
        if match:
            seq = int(match.group(1))
            max_seq = max(max_seq, seq)
    return max_seq + 1


def create_prompt_dir(
    keywords: list[str],
    history_dir: str = DEFAULT_HISTORY_DIR,
    seq_override: int | None = None,
) -> str:
    """Create the prompt directory and return its path."""
    now = datetime.datetime.now()
    date_prefix = f"{now.month}-{now.day:02d}-{now.year % 100}"

    seq = seq_override if seq_override is not None else get_next_seq(date_prefix, history_dir)

    keyword_slug = "-".join(k.lower().replace(" ", "-") for k in keywords)
    dirname = f"{date_prefix}-{seq}-{keyword_slug}"
    dirpath = os.path.join(history_dir, dirname)

    os.makedirs(dirpath, exist_ok=True)
    return dirpath


def write_prompt_md(dirpath: str) -> str:
    """Write the prompt.md template file."""
    filepath = os.path.join(dirpath, "prompt.md")
    content = f"""\




Please write your plan using your plan skill, and save to {dirpath}.
"""
    with open(filepath, "w") as f:
        f.write(content)
    return filepath


def _format_timestamp(ts: str) -> str:
    """Format an ISO 8601 timestamp as 'YYYY-MM-DD HH:MM:SS UTC'."""
    try:
        dt = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except (ValueError, AttributeError):
        return ts


def _format_tool_use(block: dict) -> str:
    """Format a tool_use block as a concise summary line."""
    name = block.get("name", "Unknown")
    inp = block.get("input", {})

    # Pick the most relevant input key to display
    if "file_path" in inp:
        detail = f"`{inp['file_path']}`"
    elif "command" in inp:
        cmd = inp["command"]
        detail = f"`{cmd[:80]}`" if len(cmd) > 80 else f"`{cmd}`"
    elif "pattern" in inp:
        detail = f"`{inp['pattern']}`"
    elif "query" in inp:
        detail = f"`{inp['query']}`"
    else:
        return f"> Used tool: **{name}**"

    return f"> Used tool: **{name}**({detail})"


def jsonl_to_markdown(jsonl_path: str) -> str:
    """Convert a Claude Code JSONL chat history to readable Markdown.

    Args:
        jsonl_path: Path to the .jsonl file to convert.

    Returns:
        A string containing the Markdown-formatted chat history.
    """
    output_parts = ["# Chat History\n"]

    with open(jsonl_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            entry_type = entry.get("type")

            # Skip non-conversation types
            if entry_type in ("summary", "file-history-snapshot"):
                continue

            timestamp = entry.get("timestamp", "")
            ts_str = _format_timestamp(timestamp) if timestamp else ""

            if entry_type == "user":
                message = entry.get("message", {})
                content = message.get("content", "")
                if isinstance(content, str) and content:
                    output_parts.append(f"\n## User\n*{ts_str}*\n\n{content}\n")

            elif entry_type == "assistant":
                message = entry.get("message", {})
                content = message.get("content", [])
                if not isinstance(content, list):
                    continue

                section_parts = [f"\n## Assistant\n*{ts_str}*\n"]

                for block in content:
                    if not isinstance(block, dict):
                        continue

                    block_type = block.get("type")

                    if block_type == "text":
                        text = block.get("text", "")
                        if text and text != "(no content)":
                            section_parts.append(f"\n{text}\n")

                    elif block_type == "tool_use":
                        section_parts.append(f"\n{_format_tool_use(block)}\n")

                if len(section_parts) > 1:  # More than just the header
                    output_parts.extend(section_parts)

    return "\n".join(output_parts)


def save_chat(
    session_id: str,
    prompt_dir: str,
    claude_projects_dir: str = DEFAULT_CLAUDE_PROJECTS_DIR,
) -> None:
    """Copy the chat history JSONL into the prompt directory.

    Uses a direct file copy (not symlink) so the history is preserved
    even if Claude Code cleans up its internal history files.
    """
    jsonl_path = os.path.join(claude_projects_dir, f"{session_id}.jsonl")
    if not os.path.exists(jsonl_path):
        print(f"Error: Chat history not found at {jsonl_path}")
        sys.exit(1)

    dest_path = os.path.join(prompt_dir, "chat_history.jsonl")
    if os.path.exists(dest_path):
        os.remove(dest_path)

    shutil.copy2(jsonl_path, dest_path)
    size_mb = os.path.getsize(dest_path) / (1024 * 1024)
    print(f"Chat history copied to: {dest_path} ({size_mb:.1f} MB)")

    md_content = jsonl_to_markdown(dest_path)
    md_path = os.path.join(prompt_dir, "chat_history.md")
    with open(md_path, "w") as f:
        f.write(md_content)
    print(f"Markdown chat history: {md_path}")


def launch_claude(prompt_dir: str, claude_projects_dir: str = DEFAULT_CLAUDE_PROJECTS_DIR, skip_permissions: bool = False) -> str:
    """Launch Claude Code with a known session ID. Returns the session ID."""
    session_id = str(uuid.uuid4())

    # Write session ID to the prompt dir for later reference
    meta_path = os.path.join(prompt_dir, ".session_id")
    with open(meta_path, "w") as f:
        f.write(session_id)

    print(f"Launching Claude Code with session ID: {session_id}")
    print(f"Prompt directory: {prompt_dir}")
    print(f"After the session, run: newprompt --save-chat {session_id} {prompt_dir}")
    print()

    cmd = ["claude"]
    if skip_permissions:
        cmd.append("--dangerously-skip-permissions")
    cmd.extend(["--session-id", session_id])

    env = os.environ.copy()
    env.pop("CLAUDECODE", None)  # Allow launching from within a Claude session
    try:
        subprocess.run(cmd, env=env)
    except KeyboardInterrupt:
        pass

    # Auto-copy chat history after session ends
    jsonl_path = os.path.join(claude_projects_dir, f"{session_id}.jsonl")
    if os.path.exists(jsonl_path):
        save_chat(session_id, prompt_dir, claude_projects_dir)
    else:
        print(f"\nNote: Chat history file not found. You can manually save it later:")
        print(f"  newprompt --save-chat {session_id} {prompt_dir}")

    return session_id


def find_session(
    query: str,
    history_dir: str = DEFAULT_HISTORY_DIR,
) -> tuple[str | None, str | None]:
    """Find a session ID and prompt directory by query string.

    The query can be:
    - An exact directory name (e.g., "2-17-26-1-my-feature")
    - A partial match on directory name (e.g., "my-feature")
    - A raw session UUID (searches .session_id files)

    Returns (session_id, dirpath) or (None, None) if not found.
    """
    if not os.path.isdir(history_dir):
        return None, None

    entries = sorted(os.listdir(history_dir), reverse=True)  # newest first

    # Try exact directory name match
    for entry in entries:
        full_path = os.path.join(history_dir, entry)
        if not os.path.isdir(full_path):
            continue
        if entry == query:
            sid_path = os.path.join(full_path, ".session_id")
            if os.path.exists(sid_path):
                with open(sid_path) as f:
                    return f.read().strip(), full_path
            return None, full_path

    # Try partial match on directory name
    for entry in entries:
        full_path = os.path.join(history_dir, entry)
        if not os.path.isdir(full_path):
            continue
        if query in entry:
            sid_path = os.path.join(full_path, ".session_id")
            if os.path.exists(sid_path):
                with open(sid_path) as f:
                    return f.read().strip(), full_path
            return None, full_path

    # Try matching by session UUID
    for entry in entries:
        full_path = os.path.join(history_dir, entry)
        sid_path = os.path.join(full_path, ".session_id")
        if os.path.exists(sid_path):
            with open(sid_path) as f:
                stored_id = f.read().strip()
            if stored_id == query:
                return stored_id, full_path

    return None, None


def main():
    parser = argparse.ArgumentParser(
        description="Create Claude Code prompt history directories",
        usage=(
            "newprompt [--launch] [--seq N] keyword1 keyword2 ...\n"
            "       newprompt --save-chat SESSION_ID PROMPT_DIR"
        ),
    )
    parser.add_argument(
        "keywords", nargs="*", help="Keywords describing the prompt topic"
    )
    parser.add_argument(
        "--launch",
        action="store_true",
        help="Launch Claude Code after creating the directory",
    )
    parser.add_argument(
        "--seq", type=int, default=None,
        help="Override the auto-detected sequence number",
    )
    parser.add_argument(
        "--save-chat",
        nargs=2,
        metavar=("SESSION_ID", "PROMPT_DIR"),
        help="Copy chat history for a session into a prompt directory",
    )
    parser.add_argument(
        "--history-dir",
        default=DEFAULT_HISTORY_DIR,
        help=f"Base directory for prompt history (default: {DEFAULT_HISTORY_DIR})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be created without creating it",
    )
    parser.add_argument(
        "--always-launch",
        action="store_true",
        help="Set persistent config to always launch Claude Code (no need for --launch)",
    )
    parser.add_argument(
        "--no-launch",
        action="store_true",
        help="Override --always-launch for this invocation only",
    )
    skip_perms_group = parser.add_mutually_exclusive_group()
    skip_perms_group.add_argument(
        "--always-dangerously-skip-permissions",
        action="store_true",
        help="Set persistent config to always pass --dangerously-skip-permissions to Claude Code",
    )
    skip_perms_group.add_argument(
        "--no-dangerously-skip-permissions",
        action="store_true",
        help="Disable persistent --dangerously-skip-permissions (or override for this invocation)",
    )
    parser.add_argument(
        "--resume",
        metavar="QUERY",
        help="Resume a previous session by directory name, keyword, or session UUID",
    )

    args = parser.parse_args()

    if args.save_chat:
        session_id, prompt_dir = args.save_chat
        save_chat(session_id, prompt_dir)
        return

    if args.resume:
        session_id, prompt_dir = find_session(args.resume, args.history_dir)
        if session_id is None and prompt_dir is None:
            print(f"Error: No matching session found for '{args.resume}'")
            sys.exit(1)
        if session_id is None:
            print(f"Error: Found directory {prompt_dir} but no .session_id file")
            sys.exit(1)
        print(f"Resuming session: {session_id}")
        print(f"Prompt directory: {prompt_dir}")
        print()

        config = load_config()
        if args.no_dangerously_skip_permissions:
            use_skip = False
        else:
            use_skip = args.always_dangerously_skip_permissions or config.get("skip_permissions", False)

        cmd = ["claude"]
        if use_skip:
            cmd.append("--dangerously-skip-permissions")
        cmd.extend(["--resume", "--session-id", session_id])

        env = os.environ.copy()
        env.pop("CLAUDECODE", None)
        try:
            subprocess.run(cmd, env=env)
        except KeyboardInterrupt:
            pass

        # Auto-save chat history after resume session ends
        claude_projects_dir = DEFAULT_CLAUDE_PROJECTS_DIR
        jsonl_path = os.path.join(claude_projects_dir, f"{session_id}.jsonl")
        if os.path.exists(jsonl_path):
            save_chat(session_id, prompt_dir, claude_projects_dir)
        return

    # Handle --always-launch config setting
    if args.always_launch:
        config = load_config()
        config["always_launch"] = True
        save_config(config)
        print("Config saved: always_launch = True")
        print("Claude Code will now launch automatically. Use --no-launch to skip.")
        if not args.keywords:
            return

    # Handle --always-dangerously-skip-permissions / --no-dangerously-skip-permissions config
    if args.always_dangerously_skip_permissions:
        config = load_config()
        config["skip_permissions"] = True
        save_config(config)
        print("Config saved: skip_permissions = True")
        print("Claude Code will launch with --dangerously-skip-permissions.")
        if not args.keywords:
            return
    elif args.no_dangerously_skip_permissions:
        config = load_config()
        config["skip_permissions"] = False
        save_config(config)
        print("Config saved: skip_permissions = False")
        print("Claude Code will launch without --dangerously-skip-permissions.")
        if not args.keywords:
            return

    if not args.keywords:
        parser.error("At least one keyword is required")

    dirpath = create_prompt_dir(args.keywords, args.history_dir, args.seq)

    if args.dry_run:
        print(f"Would create: {dirpath}")
        print(f"Would write:  {dirpath}/prompt.md")
        return

    prompt_path = write_prompt_md(dirpath)

    print(f"Created: {dirpath}")
    print(f"Prompt:  {prompt_path}")
    print()
    print(f"Edit your prompt:")
    print(f"  vim {prompt_path}")

    # Determine whether to launch
    config = load_config()
    should_launch = args.launch or (config.get("always_launch", False) and not args.no_launch)
    if args.no_dangerously_skip_permissions:
        use_skip = False
    else:
        use_skip = args.always_dangerously_skip_permissions or config.get("skip_permissions", False)

    if should_launch:
        print()
        launch_claude(dirpath, skip_permissions=use_skip)


if __name__ == "__main__":
    main()
