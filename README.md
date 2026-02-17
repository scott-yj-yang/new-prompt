# newprompt

CLI tool for managing Claude Code prompt history directories.

## Install

```bash
pip install git+https://github.com/scott-yj-yang/new-prompt.git
```

Or for development:

```bash
git clone https://github.com/scott-yj-yang/new-prompt.git
cd new-prompt
pip install -e .
```

## Workflow

There are two ways to use `newprompt`: a manual workflow and an integrated workflow.

### Integrated workflow (recommended)

One command creates the directory, opens your editor for the prompt, then launches Claude Code with automatic chat history saving:

```bash
# 1. Create prompt directory + launch Claude Code in one step
newprompt --launch CNN visualization debug

# What happens:
#   → Creates: ClaudeCode_PromptHistory/2-16-26-5-cnn-visualization-debug/
#   → Writes:  prompt.md with a template (blank lines + plan skill footer)
#   → Generates a session UUID and saves it to .session_id
#   → Launches: claude --session-id <uuid>
#   → You work with Claude Code normally
#   → When you exit the session (ctrl+c, /exit, etc.)...
#   → Auto-copies the chat history JSONL into the prompt directory
#   → Auto-generates a human-readable chat_history.md
```

After the session, your directory looks like:

```
2-16-26-5-cnn-visualization-debug/
├── prompt.md           # Your prompt
├── plan.md             # Written by Claude during the session
├── chat_history.jsonl  # Full conversation log (copied, not symlinked)
├── chat_history.md     # Human-readable markdown version
└── .session_id         # The UUID used for this session
```

### Manual workflow

If you prefer to run Claude Code separately (e.g., you already have a session open):

```bash
# 1. Create the prompt directory
newprompt CNN visualization debug

# 2. Edit your prompt
vim ClaudeCode_PromptHistory/2-16-26-5-cnn-visualization-debug/prompt.md

# 3. Copy-paste the prompt into your Claude Code session

# 4. After the session, save the chat history manually
#    (find the session ID from: claude --resume)
newprompt --save-chat <session-id> ClaudeCode_PromptHistory/2-16-26-5-cnn-visualization-debug/
```

### How chat history saving works

Claude Code stores each conversation as a JSONL file at
`~/.claude/projects/<project-slug>/<session-uuid>.jsonl`.
There is no built-in way to redirect this.

`newprompt --launch` works around this by:
1. Generating a UUID before launching Claude Code
2. Passing it via `claude --session-id <uuid>` so we know exactly which file to look for
3. After the session exits, copying (`shutil.copy2`) the JSONL file into your prompt directory

The file is **copied, not symlinked**, so your chat history is preserved even if Claude Code cleans up its internal history files.

## Command Reference

### Create a prompt directory

```bash
newprompt CNN visualization debug
```

Creates: `ClaudeCode_PromptHistory/2-16-26-5-cnn-visualization-debug/prompt.md`

### Create + launch Claude Code with chat history saving

```bash
newprompt --launch CNN visualization debug
```

### Save chat history after a session

```bash
newprompt --save-chat <session-id> /path/to/prompt-dir
```

### Override sequence number

```bash
newprompt --seq 42 my-special-prompt
```

### Resume a previous session

```bash
# By directory name
newprompt --resume 2-17-26-1-my-feature

# By keyword
newprompt --resume my-feature

# By session UUID
newprompt --resume abc-123-def-456
```

### Always launch Claude Code

```bash
# Enable: Claude Code launches automatically (no --launch needed)
newprompt --always-launch

# Then just use:
newprompt my new feature

# Skip launch for one invocation:
newprompt --no-launch my new feature
```

### Skip permissions (auto-approve all tool calls)

```bash
# Enable: pass --dangerously-skip-permissions to Claude Code
newprompt --skip-permissions

# Then launches will auto-approve all tool calls:
newprompt --launch my new feature

# Skip for one invocation:
newprompt --no-skip-permissions --launch my new feature
```

### Custom history directory

```bash
newprompt --history-dir /other/path keywords here
```

## Directory Format

```
{M}-{DD}-{YY}-{SEQ}-{keyword1}-{keyword2}/
├── prompt.md           # Your prompt (edit before use)
├── plan.md             # Written by Claude during session
├── chat_history.jsonl  # Copied from Claude's session log
├── chat_history.md     # Human-readable markdown version
└── .session_id         # UUID of the Claude Code session
```
