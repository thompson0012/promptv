# PromptV Quick Start Guide

## Overview

PromptV is a developer-first CLI tool for managing prompts locally with git-like version control, secure API key storage, and a powerful Python SDK.

## Installation

```bash
# Using uv (recommended)
uv pip install -e .

# Or using pip
pip install -e .
```

## Initialization

Initialize promptv to create the required directory structure:

```bash
promptv init
```

This creates:
- `~/.promptv/.config/` - Configuration and pricing data
- `~/.promptv/.secrets/` - Secure API key storage
- `~/.promptv/prompts/` - Your saved prompts

**Note:** promptv auto-initializes on first command if not already done.

## Quick Start

### 1. Set Up API Keys

```bash
# Set provider API key (for OpenAI, Anthropic, etc.)
promptv secrets set openai --provider

# Set generic secrets (with optional project scoping)
promptv secrets set DATABASE_URL
promptv secrets set API_KEY --project my-app

# List all secrets
promptv secrets list

# Activate secrets in your shell (like 'source .env')
source <(promptv secrets activate)
source <(promptv secrets activate --project my-app)
```

### 2. Create Your First Prompt

**Note:** All prompts are saved to the `default` project unless you specify `--project`.

```bash
# Create a simple prompt (saved to /default)
promptv set greeting -c "Hello, {{name}}!"

# Create a more complex prompt with multiple variables
promptv set welcome-email -c "Hello {{user_name}}, welcome to {{product}}!"

# Create a prompt in a specific project
promptv set api-prompt -c "API request template" --project my-app
```

### 3. Tag Versions

**Note:** Tags are scoped to projects. Tags in `default` are separate from tags in `my-app`.

```bash
# Tag the current version as production (in default project)
promptv tag create welcome-email prod --description "Production ready"

# Tag as staging
promptv tag create welcome-email staging --description "Staging environment"

# Tag with project organization
promptv tag create welcome-email prod --project my-app --description "Production for my-app"
```

### 4. Retrieve and Render Prompts

```bash
# Get prompt by tag
promptv get welcome-email --label prod

# Render with variables
promptv render welcome-email --var user_name=Alice --var product=PromptV

# Get by tag and render in one command
promptv get welcome-email --label prod --var user_name=Bob --var product="PromptV CLI"
```

### 5. List and Inspect

```bash
# List all prompts
promptv list

# List prompts in a specific project
promptv list --project my-app

# List with tags and variables
promptv list --show-tags --show-variables

# Show variables in a prompt
promptv variables list welcome-email

# Show all tags
promptv tag list welcome-email
promptv tag list welcome-email --project my-app
```

## Python SDK Usage

### Basic Usage

```python
from promptv.sdk import PromptClient

# Initialize client
client = PromptClient()

# Get prompt by tag
prompt = client.get_prompt('welcome-email', label='prod')

# Get and render with variables
prompt = client.get_prompt(
    'welcome-email',
    label='prod',
    variables={'user_name': 'Alice', 'product': 'PromptV'}
)
print(prompt)  # "Hello Alice, welcome to PromptV!"
```

### Secrets Management via SDK

```python
from promptv.sdk import PromptClient

client = PromptClient()

# Set provider API key
client.set_api_key("openai", "sk-...")

# Set generic secret
client.set_secret("DATABASE_URL", "postgres://...")
client.set_secret("API_KEY", "abc123", project="my-app")

# Get secrets
openai_key = client.get_api_key("openai")
db_url = client.get_secret("DATABASE_URL")
api_key = client.get_secret("API_KEY", project="my-app")

# List all secrets
all_secrets = client.list_secrets()
print(f"Providers: {all_secrets['providers']}")
for project, keys in all_secrets['secrets'].items():
    print(f"{project}: {keys}")

# Programmatic access to secrets (useful for automation)
from promptv.secrets_manager import SecretsManager
manager = SecretsManager()
secrets = manager.get_project_secrets_with_values(project="my-app")
# Returns: {"DATABASE_URL": "postgres://...", "API_KEY": "abc123", ...}
```

### Advanced SDK Features

```python
from promptv.sdk import PromptClient

client = PromptClient()

# Get prompt with metadata
content, metadata = client.get_prompt_with_metadata(
    'welcome-email',
    label='prod'
)
print(f"Version: {metadata.version}")
print(f"Variables: {metadata.variables}")
print(f"Message: {metadata.message}")

# List all prompts
prompts = client.list_prompts()

# Get version history
versions = client.get_versions('welcome-email')
for v in versions:
    print(f"v{v.version}: {v.message}")

# Get all tags
tags = client.get_tags('welcome-email')
# Returns: {'prod': 1, 'staging': 2}

# Cache statistics
stats = client.get_cache_stats()
print(f"Cached: {stats['cached_count']}, TTL: {stats['ttl_seconds']}s")

# Clear cache manually
client.clear_cache()
```

### Context Manager Pattern

```python
from promptv.sdk import PromptClient

# Cache is automatically cleared when exiting context
with PromptClient() as client:
    prompt = client.get_prompt('welcome-email', label='prod')
    # Use prompt...
# Cache cleared here
```

## Cost Estimation & Analysis

### CLI Commands

```bash
# Estimate cost for a prompt
promptv cost estimate my-prompt --model gpt-4 --output-tokens 100

# Compare costs across multiple models
promptv cost compare my-prompt \
  -m openai/gpt-4 \
  -m openai/gpt-3.5-turbo \
  -m anthropic/claude-3-sonnet \
  --output-tokens 50

# Count tokens only
promptv cost tokens my-prompt --label prod

# List available models
promptv cost models --provider openai
```

### SDK Cost Estimation

```python
from promptv.sdk import PromptClient

client = PromptClient()

# Estimate cost
cost = client.estimate_cost(
    'my-prompt',
    model='gpt-4',
    label='prod',
    variables={'name': 'Alice'},
    output_tokens=100
)
print(f"Total cost: ${cost.total_cost:.6f}")
print(f"Input tokens: {cost.prompt_tokens}")

# Count tokens
tokens = client.count_tokens('my-prompt', label='prod')

# Compare costs across models
comparisons = client.compare_costs(
    'my-prompt',
    models=[
        ('openai', 'gpt-4'),
        ('openai', 'gpt-3.5-turbo'),
        ('anthropic', 'claude-3-sonnet')
    ],
    output_tokens=50
)
```

### Supported Models

**30+ models across 6 providers:**
- **OpenAI**: GPT-4, GPT-4-turbo, GPT-4o, GPT-3.5-turbo
- **Anthropic**: Claude 3 Opus/Sonnet/Haiku, Claude 3.5 Sonnet, Claude 2
- **Google**: Gemini 1.5 Pro/Flash, Gemini 1.0 Pro
- **Cohere**: Command R+, Command R, Command
- **Mistral AI**: Large, Medium, Small, Open Mistral 7B
- **Together AI**: Llama 3, Mixtral models

## Visual Tools

### Diff Viewer

```bash
# Side-by-side diff (default)
promptv diff my-prompt prod staging

# Unified diff format
promptv diff my-prompt 1 2 --format unified

# JSON output
promptv diff my-prompt v1 v2 --format json
```

**Features:**
- Compare any two versions (by number, tag, or 'latest')
- Beautiful Rich-formatted output
- Color-coded changes (red/green/yellow)
- Line-by-line statistics

### Interactive Playground (TUI)

```bash
# Launch playground
promptv playground

# Open specific prompt
promptv playground my-prompt
```

**Playground Features:**
- 📋 **Prompt browser** - List and select prompts
- ✏️ **Content editor** - View/edit prompt content with markdown support
- 🔍 **Variable detection** - Auto-detect `{{variables}}`
- 💰 **Real-time cost estimation** - Live token count and cost display
- 🧪 **Mock LLM testing** - Test prompts (foundation for real API calls)
- 💾 **Version saving** - Save new versions with commit messages
- ⌨️ **Keyboard shortcuts** - Ctrl+E (execute), Ctrl+S (save), Q (quit)

## Secrets Management

### Secure API Key Storage

```bash
# Set API key (stored securely)
promptv secrets set openai --provider
# Enter your API key: [input hidden]

# Set generic secrets
promptv secrets set DATABASE_URL
promptv secrets set API_KEY --project my-app

# List configured secrets
promptv secrets list

# Test if key exists
promptv secrets test openai

# Delete API key
promptv secrets delete openai --provider

# Activate secrets in shell (like 'source .env')
source <(promptv secrets activate --project my-app)
```

### Shell Function Helper

Add this to your `~/.bashrc` or `~/.zshrc` for convenient secret activation:

```bash
# Convenient alias for activating secrets
promptv-activate() {
    eval "$(promptv secrets activate --project ${1:-default})"
}

# Usage examples:
promptv-activate                # Activate default project
promptv-activate moonshoot      # Activate moonshoot project
promptv-activate my-app         # Activate my-app project
```

**How it works:**
- Exports all project secrets as environment variables
- Provider API keys become `PROVIDER_API_KEY` (e.g., `OPENAI_API_KEY`)
- Works like `source .env` but pulls from secure storage
- Changes only affect the current shell session

### Supported Providers

- `openai` - OpenAI API
- `anthropic` - Anthropic Claude API
- `cohere` - Cohere API
- `huggingface` - HuggingFace API
- `together` - Together AI API
- `google` - Google AI API
- `replicate` - Replicate API
- `custom` - Custom provider

API keys are stored securely in:
- **macOS**: Keychain
- **Windows**: Credential Manager
- **Linux**: Secret Service (freedesktop.org)

## Common Workflows

### Development to Production Flow

```bash
# 1. Create initial prompt
 promptv set my-prompt -c "Your prompt here with {{variable}}"

# 2. Tag as development
 promptv tag create my-prompt dev

# 3. Update prompt
 promptv set my-prompt -c "Updated prompt with {{variable}}"

# 4. Tag as staging
 promptv tag create my-prompt staging

# 5. Test in staging
 promptv get my-prompt --label staging --var variable=test

# 6. Promote to production
 promptv tag create my-prompt prod
```

### Using in Python Applications

```python
from promptv.sdk import PromptClient

class MyApp:
    def __init__(self):
        self.prompt_client = PromptClient()
    
    def send_welcome_email(self, user_name: str, user_email: str):
        # Get production prompt template
        email_template = self.prompt_client.get_prompt(
            'welcome-email',
            label='prod',
            variables={
                'user_name': user_name,
                'product': 'MyApp',
                'support_email': 'support@myapp.com'
            }
        )
        
        # Send email with rendered template
        self.send_email(user_email, email_template)
```

### Version Comparison

```python
from promptv.sdk import PromptClient

client = PromptClient()

# Compare production vs staging
prod_version = client.get_prompt('my-prompt', label='prod')
staging_version = client.get_prompt('my-prompt', label='staging')

print("=== Production ===")
print(prod_version)
print("\n=== Staging ===")
print(staging_version)
```

## Key Features

### ✅ Fully Implemented (All Phases Complete)

#### **Phase 1 & 2: Core Features**

- **Git-like Version Control**
  - Immutable versioning
  - Tag/alias system
  - Version history tracking

- **Variable Management**
  - Jinja2 template engine
  - Variable extraction and validation
  - Live rendering

- **Secrets Management**
  - OS keyring integration (macOS Keychain, Windows Credential Manager, Linux Secret Service)
  - Multi-provider support (OpenAI, Anthropic, Google, Cohere, Mistral, Together)
  - Secure storage (no plaintext)

- **Python SDK**
  - Simple Pythonic API
  - Built-in caching (300s TTL)
  - Context manager support
  - Thread-safe operations

#### **Phase 3: Cost Estimation**

- **Token Counting**
  - Accurate tiktoken integration
  - Support for 30+ models
  - Multiple encoding schemes

- **Cost Estimation**
  - Real-time cost calculation
  - Input/output token pricing
  - Multi-model cost comparison
  - Pricing database for 6 major providers

- **CLI Commands**
  - `promptv cost estimate` - Full cost breakdown
  - `promptv cost compare` - Multi-model comparison
  - `promptv cost tokens` - Token counting
  - `promptv cost models` - List available models

#### **Phase 4: Visual Tools**

- **Diff Viewer**
  - Side-by-side comparison
  - Unified diff format
  - JSON output for automation
  - Beautiful Rich formatting

- **Interactive Playground (TUI)**
  - Textual-based interactive UI
  - Multi-panel layout
  - Real-time cost estimation
  - Variable detection and rendering
  - Mock LLM execution
  - Version saving with messages
  - Keyboard shortcuts

### 🚧 Future Enhancements

- **Real LLM API Integration**
  - Direct API calls from playground
  - Streaming response support
  - Real-time testing with OpenAI/Anthropic

- **Advanced Features**
  - Edge-based caching distribution
  - Export/import functionality
  - Template library
  - Collaborative features

## Best Practices

### 1. Use Descriptive Tags

```bash
# Good
 promptv tag create my-prompt v1.0.0-prod --description "Production release 1.0.0"

# Better
 promptv tag create my-prompt stable-2025-12 --description "Stable release December 2025"
```

### 2. Always Use Variables for Dynamic Content

```bash
# Don't hardcode values
 promptv set bad-prompt -c "Hello Alice, welcome to MyApp!"

# Use variables instead
 promptv set good-prompt -c "Hello {{name}}, welcome to {{app}}!"
```

### 3. Use Context Managers in Long-Running Apps

```python
# Prevents memory leaks from cache buildup
with PromptClient() as client:
    for user in users:
        prompt = client.get_prompt('welcome', variables={'name': user.name})
        send_email(user.email, prompt)
# Cache cleared automatically
```

### 4. Cache Configuration

```python
# Custom cache TTL for different use cases
client = PromptClient(cache_ttl=600)  # 10 minutes

# Disable caching for testing
prompt = client.get_prompt('my-prompt', use_cache=False)
```



### Module Not Found Errors

```bash
# Reinstall in editable mode
uv pip install -e .

# Or sync environment
uv sync
```

### Cache Issues

```python
# Clear cache manually
client = PromptClient()
client.clear_cache()

# Or disable caching
prompt = client.get_prompt('my-prompt', use_cache=False)
```

## Testing

```bash
# Run all tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=promptv --cov-report=html

# Run specific test suite
uv run pytest tests/unit/test_sdk_client.py -v
```

## Resources

- **Design Documentation**: `.qoder/specs/enhanced-promptv/design.md`
- **Task Breakdown**: `.qoder/specs/enhanced-promptv/tasks.md`
- **Examples**: `examples/basic_usage.py`, `examples/advanced_usage.py`
- **Tests**: `tests/unit/`, `tests/integration/`

## Getting Help

```bash
# CLI help
 promptv --help

# Command-specific help
 promptv tag --help
 promptv secrets --help

# Check version
 promptv --version
```

---

**Current Version**: 0.1.2  
**Status**: All Phases Complete (1, 2, 3, 4) ✅  
**Tests**: 231/231 passing (100%)  
**Coverage**: 65% overall, 90%+ for core modules  
**Production Ready**: Yes ✅

## Additional Resources

- **Demo Examples**: See [DEMO.md](DEMO.md) for comprehensive examples
- **Design Documentation**: 
- **Task Breakdown**: 
- **SDK Examples**: , 
- **Tests**: , , 