# dspy-acp

DSPy adapter for [ACP (Agent Client Protocol)](https://github.com/agentclientprotocol/agent-client-protocol) agents.

This library provides a seamless integration between [DSPy](https://github.com/stanfordnlp/dspy) and ACP-compatible agents, enabling you to use DSPy's powerful prompt optimization and evaluation capabilities with any ACP agent.

> Note: This is an experimental implementation and may change without notice.

## Installation

```bash
uv add dspy-acp
```

## Prerequisites

The quick start uses [codex-acp](https://github.com/zed-industries/codex-acp) as the ACP agent backend. Depending on how you install/run it, you may need:

1. **Node.js** (only if you run codex-acp via `npx`)
2. **A ChatGPT subscription or an API key** (refer to codex-acp/Codex CLI auth docs for current requirements)

## Quick Start

```python
import dspy
from dspy_acp import CodexACPAdapter

# Initialize the adapter
lm = CodexACPAdapter()
dspy.configure(lm=lm)

# Define your signature
class QA(dspy.Signature):
    """Answer the user's question."""
    question = dspy.InputField()
    answer = dspy.OutputField()

# Use DSPy modules as usual
qa = dspy.ChainOfThought(QA)
response = qa(question="What is the capital of France?")
print(response.answer)

# Clean up
lm.close()
```

If you use ChatGPT-based authentication, a browser window will open on first run.

## Configuration

### Authentication Methods

```python
# Example auth methods for codex-acp (check codex-acp docs for current values)
lm = CodexACPAdapter(auth_method="chatgpt")
lm = CodexACPAdapter(auth_method="openai-api-key")
lm = CodexACPAdapter(auth_method="codex-api-key")
```

### Custom ACP Agent

```python
# Use a different ACP agent
lm = ACPAdapter(command=["path/to/your-acp-agent"])
```

The `auth_method` value is defined by the selected ACP agent.

## Codex Models (Examples)

Codex CLI supports multiple models. Representative options include:

- `gpt-5.1-codex-max`
- `gpt-5.1-codex-mini`
- `gpt-5.2`

For the latest list, see the official Codex models page:
[https://developers.openai.com/codex/models](https://developers.openai.com/codex/models)

## How It Works

```
DSPy Application
       │
       ▼
ACPAdapter (Client)
       │ JSON-RPC over stdio
       ▼
ACP Agent (e.g., codex-acp)
       │
       ▼
LLM Backend
```

The adapter implements the ACP client protocol, communicating with ACP agents via JSON-RPC over stdin/stdout. This enables DSPy to work with any ACP-compatible agent.

## API Reference

### ACPAdapter

```python
ACPAdapter(
    model: str = "acp",           # Model identifier for DSPy
    command: list[str],           # ACP agent command
    auth_method: str = "chatgpt", # Authentication method (agent-specific)
    temperature: float = 0.7,     # Sampling temperature
    max_tokens: int = 1000,       # Max tokens in response
)
```

### CodexACPAdapter

```python
CodexACPAdapter(
    model: str = "acp",           # Model identifier for DSPy
    command: list[str] = None,    # codex-acp command override
    auth_method: str = "chatgpt", # Authentication method for codex-acp
    temperature: float = 0.7,     # Sampling temperature
    max_tokens: int = 1000,       # Max tokens in response
)
```

#### Methods

- `close()`: Clean up the subprocess and resources

## License

MIT
