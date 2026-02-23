#!/usr/bin/env python3
"""Newprompt MCP Server — multi-prompt session management for Claude Code.

Exposes tools to create and continue prompt sessions within a single
Claude Code conversation, writing indexed prompt/plan files in the
same session directory.
"""

import logging
import os
import re
import sys

from mcp.server.fastmcp import FastMCP

from newprompt.cli import (
    get_default_history_dir,
    create_prompt_dir,
    get_next_prompt_index,
    read_current_session_marker,
    write_indexed_prompt_md,
    write_prompt_md,
)

# Configure logging to stderr (never stdout for stdio MCP servers)
logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("newprompt")

# In-memory state: the active session directory for this server instance
_active_session_dir: str | None = None


# ---------------------------------------------------------------------------
# Pure-logic helpers (testable without MCP framework)
# ---------------------------------------------------------------------------


def _find_latest_session_dir(history_dir: str | None = None) -> str | None:
    """Find the most recent session directory in the history folder.

    Checks the session marker file first (set by ``newprompt --launch``),
    then falls back to scanning directories sorted lexicographically
    (YYYY-MM-DD-SEQ-slug), where the last one is the most recent.
    """
    # Check session marker first (set by newprompt --launch)
    marker = read_current_session_marker()
    if marker:
        return marker

    if history_dir is None:
        history_dir = get_default_history_dir()

    if not os.path.isdir(history_dir):
        return None

    candidates = []
    for entry in os.listdir(history_dir):
        full = os.path.join(history_dir, entry)
        if os.path.isdir(full) and not entry.startswith("_"):
            # Must have a prompt.md to count as a session
            if os.path.exists(os.path.join(full, "prompt.md")):
                candidates.append(full)

    if not candidates:
        return None
    candidates.sort()
    return candidates[-1]


def _init_session_logic(
    keywords: str,
    history_dir: str | None = None,
) -> dict:
    """Create a new session directory and initial prompt.md."""
    if history_dir is None:
        history_dir = get_default_history_dir()
    keyword_list = keywords.strip().split()
    if not keyword_list:
        return {"error": "At least one keyword is required."}

    dirpath = create_prompt_dir(keyword_list, history_dir=history_dir)
    prompt_file = write_prompt_md(dirpath)
    plan_file = os.path.join(dirpath, "plan.md")

    return {
        "session_dir": dirpath,
        "prompt_file": prompt_file,
        "plan_file": plan_file,
    }


def _continue_session_logic(
    session_dir: str,
    prompt_text: str = "",
) -> dict:
    """Create the next indexed prompt file in the session directory."""
    if not os.path.isdir(session_dir):
        return {"error": f"Session directory not found: {session_dir}"}

    index = get_next_prompt_index(session_dir)
    prompt_file = write_indexed_prompt_md(session_dir, index, prompt_text)
    plan_file = os.path.join(session_dir, f"plan{index}.md")

    return {
        "prompt_index": index,
        "prompt_file": prompt_file,
        "plan_file": plan_file,
        "session_dir": session_dir,
    }


def _get_session_info_logic(session_dir: str) -> dict:
    """Get information about the current session."""
    if not os.path.isdir(session_dir):
        return {"error": f"Session directory not found: {session_dir}"}

    prompts = sorted(
        f for f in os.listdir(session_dir) if re.match(r"^prompt\d*\.md$", f)
    )
    plans = sorted(f for f in os.listdir(session_dir) if re.match(r"^plan\d*\.md$", f))

    return {
        "session_dir": session_dir,
        "session_name": os.path.basename(session_dir),
        "prompt_count": len(prompts),
        "plan_count": len(plans),
        "prompts": prompts,
        "plans": plans,
        "next_prompt_index": get_next_prompt_index(session_dir),
    }


# ---------------------------------------------------------------------------
# MCP tool definitions
# ---------------------------------------------------------------------------


@mcp.tool()
def init_session(keywords: str) -> str:
    """Create a new prompt session directory for a Claude Code conversation.

    Creates a timestamped directory (YYYY-MM-DD-SEQ-slug) with an initial
    prompt.md template. Call this at the start of a new multi-task session.

    Args:
        keywords: Space-separated keywords describing the session topic
                  (e.g. "CNN visualization debug").
    """
    global _active_session_dir

    result = _init_session_logic(keywords)
    if "error" in result:
        return result["error"]

    _active_session_dir = result["session_dir"]
    logger.info(f"Initialized session: {_active_session_dir}")

    return (
        f"Session created: {result['session_dir']}\n"
        f"Prompt file: {result['prompt_file']}\n"
        f"Plan saves to: {result['plan_file']}\n\n"
        f"Paste your prompt into the chat. "
        f"The plan will be saved to {result['plan_file']}."
    )


@mcp.tool()
def continue_session(prompt_text: str = "", session_dir: str = "") -> str:
    """Create the next prompt file in the current session for a new task.

    Call this when the user wants to start a new task within the same
    Claude Code session. Creates promptN.md and tells Claude where to
    save planN.md.

    Args:
        prompt_text: The user's prompt text for this task. If empty,
                     a blank template is created.
        session_dir: Explicit session directory path. If empty, uses the
                     active session or auto-detects the latest one.
    """
    global _active_session_dir

    target_dir = session_dir or _active_session_dir
    if not target_dir:
        target_dir = _find_latest_session_dir()
    if not target_dir:
        return (
            "No active session found. Use init_session first to create one, "
            "or provide session_dir explicitly."
        )

    result = _continue_session_logic(target_dir, prompt_text)
    if "error" in result:
        return result["error"]

    _active_session_dir = result["session_dir"]
    idx = result["prompt_index"]

    return (
        f"Continuation prompt created: {result['prompt_file']}\n"
        f"Plan saves to: {result['plan_file']}\n\n"
        f"This is prompt #{idx} in session: {os.path.basename(target_dir)}\n"
        f"Please write your plan using your plan skill, "
        f"and save to {result['plan_file']}."
    )


@mcp.tool()
def get_session_info(session_dir: str = "") -> str:
    """Get information about the current or specified prompt session.

    Shows the session directory, number of prompts and plans, and the
    next prompt index.

    Args:
        session_dir: Explicit session directory path. If empty, uses the
                     active session or auto-detects the latest one.
    """
    target_dir = session_dir or _active_session_dir
    if not target_dir:
        target_dir = _find_latest_session_dir()
    if not target_dir:
        return "No active session found."

    result = _get_session_info_logic(target_dir)
    if "error" in result:
        return result["error"]

    lines = [
        f"Session: {result['session_name']}",
        f"Directory: {result['session_dir']}",
        f"Prompts ({result['prompt_count']}): {', '.join(result['prompts'])}",
        f"Plans ({result['plan_count']}): {', '.join(result['plans'])}",
        f"Next prompt index: {result['next_prompt_index']}",
    ]
    return "\n".join(lines)


def main():
    """Run the MCP server on stdio transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
