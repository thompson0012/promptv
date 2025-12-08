This project sponsored by [DLS by LABs21](https://dls.labs21.dev/?utm_source=github&utm_medium=banner&utm_campaign=promptv)

<img width="290" height="54" alt="image" src="https://github.com/user-attachments/assets/a9352e6c-3c52-4b6d-89a7-8604a1d85fe7" />


If you think this project is helpful, treat me a coffee.

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://buymeacoffee.com/fdatwlnur)

=================

WARNING: This is a pre-release version of promptv. Expect breaking changes.

# promptv - Prompt Versioning CLI Tool & Environment Variable Management Tool

A command-line interface tool for managing prompts locally with versioning support.

## Features

- Local prompt management with version control
<!-- - Cloud storage support with API key and project ID -->
- Markdown format support for all prompts
- Automatic directory creation on first run
- Full version history tracking
- Multiple prompt operations (create, update, retrieve, list, delete)
- Variable substitution with Jinja2 templates
- Tag/label system for easy version references
- Cost estimation for LLM API calls
- Project-based organization for prompts and secrets
- Git-style diff visualization

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd promptv

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install the package in development mode
pip install -e .

# Install from Pypi
pip install promptv==0.1.7 #lock the version to avoid API changes
```

## Configuration

### First-time Setup

Initialize promptv to create the required directory structure:

```bash
promptv init
```

This creates:

```
~/.promptv/
├── .config/
│   ├── config.yaml      # User configuration
│   └── pricing.yaml     # LLM pricing data (customizable)
├── .secrets/
│   └── secrets.json     # API keys and secrets
├── cache/               # Cache directory
├── presets/             # Presets directory
├── prompts/             # Saved prompts
└── sessions/            # Sessions directory
```

**Note:** promptv will automatically initialize on first command if not already done.

On first run, promptv creates `~/.promptv/.config/config.yaml` with default settings.

### Execution Modes

**Local Mode (default)**: Stores all data in `~/.promptv/`

```yaml
execution:
  mode: "local"
```

### LLM Provider Configuration

Configure API base URLs for different LLM providers:

```yaml
llm_providers:
  openai:
    api_base_url: "https://api.openai.com/v1"
    default_model: "gpt-4"
  anthropic:
    api_base_url: "https://api.anthropic.com/v1"
    default_model: "claude-3-5-sonnet-20241022"
  cohere:
    api_base_url: "https://api.cohere.ai/v1"
    default_model: "command-r-plus"
  google:
    api_base_url: "https://generativelanguage.googleapis.com/v1"
    default_model: "gemini-pro"
  together:
    api_base_url: "https://api.together.xyz/v1"
    default_model: "meta-llama/Llama-3-70b-chat-hf"
  custom:
    api_base_url: "http://localhost:8000/v1"
    default_model: "custom-model"
```

### Customizing LLM Pricing

You can customize LLM pricing by editing `~/.promptv/.config/pricing.yaml`. This allows you to:

- Update pricing for existing models
- Add new models
- Adjust pricing for local/custom models

The file is copied from package resources during initialization and never auto-updated.

## Usage

### Commands

0. **init** - Initialize promptv directory structure

   ```bash
   promptv init                    # Create directory structure
   promptv init --force            # Delete and recreate (WARNING: destructive!)
   ```

1. **commit** - Save a prompt file with a specific name

   ```bash
   promptv commit --source file.md --name prompt-name                    # Saves to /default project
   promptv commit --source file.md --name prompt-name -m "Update message"
   promptv commit --source file.md --name prompt-name --tag prod
   promptv commit --source file.md --name prompt-name --project my-app   # Saves to /my-app project
   ```

2. **set** - Set/update a prompt with the given name

   ```bash
   promptv set prompt-name --file file.txt                 # Saves to /default project
   promptv set prompt-name --content "Prompt content"
   echo "Content" | promptv set prompt-name
   promptv set prompt-name --file file.txt --project my-app  # Saves to /my-app project
   ```

3. **edit** - Edit a prompt directly in your terminal editor

   ```bash
   promptv edit prompt-name
   promptv edit prompt-name --version 2
   promptv edit prompt-name -m "Updated instructions"
   promptv edit prompt-name --editor vim
   ```

4. **get** - Retrieve a specific version of a prompt

   ```bash
   promptv get prompt-name --version latest
   promptv get prompt-name --version 1
   promptv get prompt-name --label prod

   # Variable substitution - space-separated key=value pairs
   promptv get prompt-name --var "name=Alice count=5"

   # Multiple --var flags also supported
   promptv get prompt-name --var key1=val1 --var key2=val2
   ```

5. **list** - List all versions and metadata for a prompt

   ```bash
   promptv list prompt-name
   ```

6. **remove** - Remove one or more prompts

   ```bash
   promptv remove prompt-name
   promptv remove prompt1 prompt2 prompt3
   promptv remove prompt-name --yes  # Skip confirmation
   ```

7. **tag** - Manage tags/labels for versions

   ```bash
   promptv tag create prompt-name tag-name --version 1
   promptv tag create prompt-name tag-name --project my-app
   promptv tag list prompt-name
   promptv tag list prompt-name --project my-app
   promptv tag show prompt-name tag-name --project my-app
   promptv tag delete prompt-name tag-name
   promptv tag delete prompt-name tag-name --project my-app --yes
   ```

8. **secrets** - Manage API keys and secrets securely

   ```bash
   # Set provider API key (validated against supported providers)
   promptv secrets set openai --provider
   promptv secrets set anthropic --provider

   # Set generic secret (default project)
   promptv secrets set DATABASE_URL
   promptv secrets set MY_API_KEY

   # Set project-scoped secret
   promptv secrets set DATABASE_URL --project my-app
   promptv secrets set REDIS_URL --project moonshoot

   # Get secret
   promptv secrets get openai --provider          # Shows masked (last 4 chars)
   promptv secrets get DATABASE_URL               # Shows full value
   promptv secrets get API_KEY --project my-app   # Get from specific project

   # List all secrets
   promptv secrets list                           # All secrets
   promptv secrets list --project my-app          # Filter by project

   # Delete secret
   promptv secrets delete openai --provider
   promptv secrets delete DATABASE_URL --project my-app --yes

   # Export secrets in shell (like 'source .env')
   source <(promptv secrets export --format shell --project moonshoot)
   eval "$(promptv secrets export --format shell --project moonshoot)"

   # Convert to .env file
   promptv secrets export --format dotenv
   ```

9. **diff** - Compare two versions of a prompt

   ```bash
   promptv diff prompt-name v1 v2
   promptv diff prompt-name --label prod --label staging
   promptv diff prompt-name v1 v2 --format unified
   promptv diff prompt-name v1 v2 --format side-by-side  # Shows --, ++, ~~ markers
   ```

10. **cost** - Cost estimation commands for LLM API calls

    ```bash
    # Estimate cost of running a prompt
    promptv cost estimate prompt-name --model gpt-4 --provider openai
    promptv cost estimate prompt-name --output-tokens 1000

    # Compare costs across multiple models
    promptv cost compare prompt-name --models gpt-4,gpt-3.5-turbo --provider openai

    # Count tokens in a prompt
    promptv cost tokens prompt-name

    # List available models
    promptv cost models
    ```

11. **render** - Render a prompt with variable substitution

    ```bash
    promptv render prompt-name --var name=Alice --var count=5
    promptv render prompt-name --label prod --var api_key=sk-xxx
    promptv render prompt-name --version 2 --var temperature=0.7
    promptv render prompt-name --project my-app --var name=Bob
    ```

12. **variables** - Manage and inspect variables in prompts

    ```bash
    promptv variables list prompt-name
    promptv variables list prompt-name --version 2
    promptv variables list prompt-name --label prod
    ```

13. **test** - Interactively test prompts with LLM providers

    ```bash
    # Test with OpenAI
    promptv test my-prompt --llm gpt-4 --provider openai
    
    # Test with Anthropic
    promptv test greeting-prompt --llm claude-3-5-sonnet-20241022 --provider anthropic
    
    # Test with OpenRouter
    promptv test creative-prompt --llm openai/gpt-4-turbo --provider openrouter
    
    # Test with custom endpoint
    promptv test custom-prompt --llm my-model --endpoint http://localhost:8000/v1
    
    # Test with custom endpoint and API key (security warning will be shown)
    promptv test custom-prompt --llm my-model --custom-endpoint https://api.example.com/v1/chat --api-key sk-12345
    
    # Test with specific version and parameters
    promptv test my-prompt --llm gpt-4 --provider openai --version 2 --temperature 0.7
    ```

## Secrets Management

promptv provides secure storage for API keys and generic secrets:

### Provider API Keys

Store API keys for supported LLM providers (openai, anthropic, cohere, etc.):

```bash
# Set provider API key (validated)
promptv secrets set openai --provider
promptv secrets set anthropic --provider

# Get provider key (shows last 4 chars only)
promptv secrets get openai --provider

# Delete provider key
promptv secrets delete openai --provider
```

### Generic Secrets

Store any secrets with optional project scoping:

```bash
# Default project
promptv secrets set DATABASE_URL
promptv secrets set API_KEY

# Project-scoped
promptv secrets set DATABASE_URL --project my-app
promptv secrets set REDIS_URL --project moonshoot

# Retrieve secrets
promptv secrets get DATABASE_URL
promptv secrets get API_KEY --project my-app
```

### Listing Secrets

```bash
# List all secrets
promptv secrets list

# Example output:
# Provider API Keys:
#   ✓ openai
#   ✓ anthropic
#
# Project Secrets:
#   default:
#     ✓ DATABASE_URL
#     ✓ API_KEY
#
#   my-app:
#     ✓ DB_PASSWORD
#     ✓ REDIS_URL

# Filter by project
promptv secrets list --project my-app
```

### Exporting Secrets

Similar to `source .env`, you can export all secrets for a project to your current shell:

```bash
# Basic usage - export default project
source <(promptv secrets export)
promptv secrets export > .env

# Export specific project
source <(promptv secrets export --project moonshoot)

# Alternative syntax with eval
eval "$(promptv secrets export --project moonshoot)"

# Exclude provider API keys
source <(promptv secrets export --project moonshoot --no-include-providers)

# Different output formats
promptv secrets export --format json
promptv secrets export --format shell
promptv secrets export --format dotenv
```

**Shell Function Helper** (add to `~/.bashrc` or `~/.zshrc`):

```bash
# Convenient alias for exporting secrets
promptv-export() {
    eval "$(promptv secrets export --format shell --project ${1:-default})"
}

# Usage:
promptv-export                # Export default project
promptv-export moonshoot      # Export moonshoot project
```

**How it works:**

- Exports all secrets for the specified project as environment variables
- Provider API keys are exported as `PROVIDER_API_KEY` (e.g., `OPENAI_API_KEY`)
- Works like `source .env` but pulls from promptv's secure storage
- Changes only affect the current shell session

**Output formats:**

```bash
# Shell format (default) - includes export statements
promptv secrets export --project moonshoot --format shell

# Dotenv format (standard .env file format)
promptv secrets export --project moonshoot --format dotenv

# JSON format for other tools
promptv secrets export --project moonshoot --format json
```

### Security

- All secrets are stored in `~/.promptv/.secrets/secrets.json`
- File has restrictive permissions (0600 - owner read/write only)
- Secrets directory has restrictive permissions (0700 - owner access only)
- Provider API keys show only last 4 characters when retrieved

## Project Organization

**Default Behavior:** All prompts are automatically saved to the `default` project unless you specify otherwise.

```bash
# These commands save to ~/.promptv/prompts/default/
promptv commit --source prompt.md --name my-prompt
promptv set my-prompt -c "Content here"
promptv tag create my-prompt prod

# These commands save to ~/.promptv/prompts/my-app/
promptv commit --source prompt.md --name my-prompt --project my-app
promptv set my-prompt -c "Content here" --project my-app
promptv tag create my-prompt prod --project my-app
```

Use project tags to organize prompts and secrets:

```bash
# Set a prompt with project tag
promptv commit --source prompt.md --name my-prompt --project my-app

# Set project-scoped secret
promptv secrets set DATABASE_URL --project my-app

# Get secret for specific project
promptv secrets get DATABASE_URL --project my-app
```

## Variable Substitution

Prompts support Jinja2 template variables:

```markdown
Hello {{ name }},

Welcome to {{ product }}! Your account is ready.

Support: {{ support_email }}
```

Retrieve with variables:

```bash
promptv get welcome-email --var "name=Alice product=MyApp support_email=help@example.com"
```

Render with variables:

```bash
promptv render welcome-email --var "name=Alice product=MyApp support_email=help@example.com"
```

## Directory Structure

```
~/.promptv/
├── .config/
│   ├── config.yaml          # Configuration file
│   └── pricing.yaml         # Pricing data
├── .secrets/
│   └── secrets.json         # Encrypted secrets
├── cache/                   # Cache directory
├── presets/                 # Presets directory
├── sessions/                # Sessions directory
└── prompts/
    ├── default/             # Default project (auto-created)
    │   └── prompt-name/
    │       ├── metadata.json     # Version metadata
    │       ├── tags.json         # Tag registry
    │       ├── v1.md            # Version 1
    │       ├── v2.md            # Version 2
    │       └── ...
    └── my-app/              # Custom project
        └── prompt-name/
            ├── metadata.json
            ├── tags.json
            └── ...
```

## Diff Visualization

The diff engine supports git-style markers:

- `--` : Deleted lines (red)
- `++` : Added lines (green)
- `~~` : Modified lines (yellow)
- `@@` : Context markers in unified diff

```bash
promptv diff my-prompt 1 2 --format side-by-side
```

## Examples

```bash
# Commit a prompt from a file
promptv commit --source my_prompt.txt --name chatgpt-instructions

# Create/update a prompt with direct content
promptv set summarization-prompt -c "Summarize the following text in 3 sentences."

# Get the latest version of a prompt with variables
promptv get email-template --var "name=John product=Widget"

# Render a prompt with variables
promptv render email-template --var "name=John product=Widget"

# Edit a prompt in your editor
promptv edit email-template

# Create a tag for production
promptv tag create email-template prod --version 3

# Get production version
promptv get email-template --label prod

# Compare versions
promptv diff email-template 2 3 --format side-by-side

# List all versions of a prompt
promptv list chatgpt-instructions

# Remove prompts
promptv remove chatgpt-instructions summarization-prompt --yes

# Set API key
promptv secrets set openai --provider

# Estimate cost
promptv cost estimate my-prompt --model gpt-4

# Export secrets to .env file
promptv secrets export --project my-app > .env
```

## Development

Run tests:

```bash
pytest
pytest --cov=promptv  # With coverage
```

## License

Apache License, Version 2.0
