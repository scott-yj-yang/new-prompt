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

## Usage

### Create a new prompt directory

```bash
newprompt CNN visualization debug
```

Creates: `ClaudeCode_PromptHistory/2-16-26-5-cnn-visualization-debug/prompt.md`

### Launch Claude Code with auto-saved chat history

```bash
newprompt --launch CNN visualization debug
```

Creates the directory, launches Claude Code with a tracked session ID, and
**copies** the chat history JSONL into the prompt directory when the session ends.

### Manually save chat history after a session

```bash
newprompt --save-chat <session-id> /path/to/prompt-dir
```

### Override sequence number

```bash
newprompt --seq 42 my-special-prompt
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
└── .session_id         # UUID of the Claude Code session
```
