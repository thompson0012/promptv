# PromptV Test Command Documentation

The `promptv test` command allows you to interactively test your saved prompts with various LLM providers in real-time. This feature provides a chat-like interface for experimenting with prompts and seeing how different models respond.

## Table of Contents

- [Overview](#overview)
- [Basic Usage](#basic-usage)
- [Supported Providers](#supported-providers)
- [Command Options](#command-options)
- [Variable Handling](#variable-handling)
- [Interactive Session](#interactive-session)
- [Cost Tracking](#cost-tracking)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)

## Overview

The test command loads a saved prompt from your local promptv repository, handles variable substitution by prompting you for values, and starts an interactive chat session with your chosen LLM provider. Responses are streamed in real-time, and token usage and estimated costs are tracked throughout the session.

## Basic Usage

```bash
# Basic usage with OpenAI
promptv test my-prompt --llm gpt-4 --provider openai

# With Anthropic
promptv test my-prompt --llm claude-3-5-sonnet-20241022 --provider anthropic

# With OpenRouter
promptv test my-prompt --llm openai/gpt-4-turbo --provider openrouter

# With custom endpoint
promptv test my-prompt --llm my-model --endpoint http://localhost:8000/v1
```

## Supported Providers

The test command supports the following LLM providers:

| Provider    | Description                              | Example Model Names |
|-------------|------------------------------------------|---------------------|
| `openai`    | OpenAI models (GPT series)               | `gpt-4`, `gpt-3.5-turbo` |
| `anthropic` | Anthropic models (Claude series)         | `claude-3-5-sonnet-20241022`, `claude-3-opus-20240229` |
| `openrouter`| OpenRouter models (multi-provider access)| `openai/gpt-4-turbo`, `anthropic/claude-3-opus` |
| `custom`    | Custom endpoints (OpenAI-compatible)     | Any custom model name |

## Command Options

| Option        | Description                                    | Required | Default |
|---------------|------------------------------------------------|----------|---------|
| `PROMPT_NAME` | Name of the saved prompt to test               | Yes      | N/A |
| `--llm`       | Model name to use                              | Yes      | N/A |
| `--provider`  | LLM provider (`openai`, `anthropic`, `openrouter`) | Conditional* | N/A |
| `--endpoint`  | Custom endpoint URL                            | Conditional* | N/A |
| `--version`   | Specific version to test                       | No       | `latest` |
| `--project`   | Project name                                   | No       | `default` |
| `--temperature` | Sampling temperature (0.0-2.0)              | No       | Provider default |
| `--max-tokens` | Maximum tokens in response                    | No       | Provider default |

*Either `--provider` or `--endpoint` must be specified, but not both.

## Variable Handling

If your prompt contains Jinja2-style variables (e.g., `{{name}}`, `{{topic}}`), the test command will automatically detect them and prompt you to enter values before starting the session:

```markdown
# My Prompt

Hello {{name}}! Today we'll discuss {{topic}}.
```

When you run `promptv test my-prompt --llm gpt-4 --provider openai`, you'll be prompted:

```
Detected variables in prompt:
Enter value for 'name': Alice
Enter value for 'topic': artificial intelligence
```

The variables will be substituted in the prompt before sending to the LLM.

## Interactive Session

Once the session starts, you can have a conversation with the LLM:

```
🚀 PromptV Test Mode

You: What are the benefits of using promptv?
🤖 Assistant:
[promptv responds with streaming output...]

Tokens: 125 (input: 42, output: 83) | Cost: $0.0021

You: How does version control work?
🤖 Assistant:
[promptv responds with streaming output...]

Tokens: 98 (input: 35, output: 63) | Cost: $0.0015

You: exit
```

### Exit Commands

You can end the session with any of these commands:
- `exit`
- `quit`
- Press `Ctrl+D` (EOF)
- Press `Ctrl+C` (Interrupt)

## Cost Tracking

The test command tracks and displays token usage and estimated costs in real-time:

- **Input tokens**: Tokens in your messages
- **Output tokens**: Tokens in the LLM responses
- **Total tokens**: Combined input and output tokens
- **Estimated cost**: Based on current pricing data

At the end of the session, a summary is displayed:

```
📊 Session Summary
┌────────────────────┬──────────┐
│ Metric             │ Value    │
├────────────────────┼──────────┤
│ Messages Sent      │ 3        │
│ Session Duration   │ 2m 15s   │
│ Total Tokens       │ 427      │
│   - Input Tokens   │ 152      │
│   - Output Tokens  │ 275      │
│ Total Cost         │ $0.0084  │
└────────────────────┴──────────┘
```

## Examples

### Testing with OpenAI

```bash
# Test with GPT-4
promptv test customer-support-prompt --llm gpt-4 --provider openai

# Test with specific temperature
promptv test creative-writing-prompt --llm gpt-4 --provider openai --temperature 0.8

# Test specific version
promptv test email-template --llm gpt-3.5-turbo --provider openai --version 3
```

### Testing with Anthropic

```bash
# Test with Claude 3.5 Sonnet
promptv test technical-docs-prompt --llm claude-3-5-sonnet-20241022 --provider anthropic

# Test with specific max tokens
promptv test summarization-prompt --llm claude-3-opus-20240229 --provider anthropic --max-tokens 500
```

### Testing with OpenRouter

```bash
# Access GPT-4 through OpenRouter
promptv test general-prompt --llm openai/gpt-4-turbo --provider openrouter

# Access Claude through OpenRouter
promptv test analysis-prompt --llm anthropic/claude-3-opus --provider openrouter
```

### Testing with Custom Endpoints

```bash
# Test with local LLM server
promptv test local-prompt --llm llama3 --endpoint http://localhost:8000/v1

# Test with custom hosted model
promptv test hosted-prompt --llm mistral-7b --endpoint https://api.mycompany.com/v1
```

## Troubleshooting

### API Key Errors

If you get an API key error:

```bash
Error: API key not found for provider 'openai'
Set your API key with: promptv secrets set openai_api_key
```

Solution: Set your API key using the secrets command:

```bash
promptv secrets set openai_api_key
# Enter your API key when prompted
```

### Prompt Not Found

If you get a prompt not found error:

```bash
Error: Prompt 'my-prompt' not found in project 'default'
Run 'promptv list --project default' to see available prompts
```

Solution: Check available prompts or create the prompt:

```bash
# List available prompts
promptv list --project default

# Create the prompt
promptv commit --source my-prompt.md --name my-prompt
```

### Network Errors

If you experience network issues:

- Check your internet connection
- Verify the endpoint URL is correct
- Check if your API key has the necessary permissions
- Try again after a few moments

### Rate Limit Errors

If you hit rate limits:

- Wait a few moments before trying again
- Consider using a different model or provider
- Check your provider's rate limit documentation

## SDK Usage

You can also test prompts programmatically using the SDK:

```python
from promptv.sdk.client import PromptClient

client = PromptClient()

# Test a prompt interactively
client.test_prompt_interactive(
    name='my-prompt',
    provider='openai',
    model='gpt-4',
    temperature=0.7
)
```