This project sponsored by [DLS by LABs21](https://dls.labs21.dev/?utm_source=github&utm_medium=banner&utm_campaign=promptv)

<img width="289" height="51" alt="image" src="https://github.com/user-attachments/assets/5eef16c4-a4a4-413f-bc3d-3e2c35d50cc5" />



If you think this project is helpful, treat me a coffee.

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://buymeacoffee.com/fdatwlnur)


# promptv - Prompt Versioning CLI Tool

A command-line interface tool for managing prompts locally with versioning support.

## Features

- Local prompt management with version control
- Cloud storage support with API key and project ID
- Markdown format support for all prompts
- Automatic directory creation on first run
- Full version history tracking
- Multiple prompt operations (create, update, retrieve, list, delete)
- Variable substitution with Jinja2 templates
- Tag/label system for easy version references
- Cost estimation for LLM API calls
- Interactive playground TUI
- API testing with LLM integration
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

# Install the package
pip install -e .
```

After installation, you can use `promptv` command directly instead of `python -m promptv.cli`.

## Configuration

On first run, promptv creates `~/.promptv/.config/config.yaml` with default settings.

### Execution Modes

**Local Mode (default)**: Stores all data in `~/.promptv/`
```yaml
execution:
  mode: "local"
```

**Cloud Mode**: Stores data in cloud with API credentials
```yaml
execution:
  mode: "cloud"
  cloud:
    api_key: "your-api-key"
    project_id: "your-project-id"
    endpoint: "https://api.promptv.io"
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
  custom:
    api_base_url: "http://localhost:8000/v1"
    default_model: "custom-model"
```

## Usage

### Commands

1. **commit** - Save a prompt file with a specific name
   ```bash
   promptv commit --source file.md --name prompt-name
   promptv commit --source file.md --name prompt-name -m "Update message"
   promptv commit --source file.md --name prompt-name --tag prod
   ```

2. **set** - Set/update a prompt with the given name
   ```bash
   promptv set prompt-name --file file.txt
   promptv set prompt-name --content "Prompt content"
   echo "Content" | promptv set prompt-name
   ```

3. **get** - Retrieve a specific version of a prompt
   ```bash
   promptv get prompt-name --version latest
   promptv get prompt-name --version 1
   promptv get prompt-name --label prod
   
   # Variable substitution - space-separated key=value pairs
   promptv get prompt-name --var "name=Alice count=5"
   
   # Multiple --var flags also supported
   promptv get prompt-name --var key1=val1 --var key2=val2
   ```

4. **list** - List all versions and metadata for a prompt
   ```bash
   promptv list prompt-name
   ```

5. **remove** - Remove one or more prompts
   ```bash
   promptv remove prompt-name
   promptv remove prompt1 prompt2 prompt3
   promptv remove prompt-name --yes  # Skip confirmation
   ```

6. **tags** - Manage tags/labels for versions
   ```bash
   promptv tags create prompt-name tag-name --version 1
   promptv tags list prompt-name
   promptv tags delete prompt-name tag-name
   ```

7. **secrets** - Manage API keys and secrets securely
   ```bash
   # Set provider API key
   promptv secrets set openai_api_key
   
   # Set custom secret (project-scoped)
   promptv secrets set db_password --project my-app
   
   # Get secret
   promptv secrets get openai_api_key
   
   # List configured providers
   promptv secrets list
   
   # Delete secret
   promptv secrets delete openai_api_key
   ```

8. **diff** - Compare two versions of a prompt
   ```bash
   promptv diff prompt-name v1 v2
   promptv diff prompt-name --label prod --label staging
   promptv diff prompt-name v1 v2 --format unified
   promptv diff prompt-name v1 v2 --format side-by-side  # Shows --, ++, ~~ markers
   ```

9. **estimate-cost** - Estimate cost of running a prompt
   ```bash
   promptv estimate-cost prompt-name --model gpt-4 --provider openai
   promptv estimate-cost prompt-name --output-tokens 1000
   ```

10. **playground** - Launch interactive TUI for testing prompts
    ```bash
    promptv playground
    promptv playground --prompt prompt-name
    ```

11. **test** - Run API tests with LLM integration
    ```bash
    promptv test --suite test-suite.json
    ```

## Project Organization

Use project tags to organize prompts and secrets:

```bash
# Set a prompt with project tag
promptv commit --source prompt.md --name my-prompt --project my-app

# Set project-scoped secret
promptv secrets set db_password --project my-app

# Get secret for specific project
promptv secrets get db_password --project my-app
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

## API Testing

Create a test suite JSON file:

```json
{
  "name": "greeting-tests",
  "prompt_name": "greeting-prompt",
  "prompt_version": "latest",
  "provider": "openai",
  "model": "gpt-4",
  "test_cases": [
    {
      "name": "test-formal",
      "variables": {"tone": "formal", "name": "Alice"},
      "expected_contains": ["Dear", "Alice"],
      "max_tokens": 100
    }
  ]
}
```

Run tests:
```bash
promptv test --suite tests.json --output results.json
```

## Directory Structure

```
~/.promptv/
├── .config/
│   └── config.yaml          # Configuration file
└── prompts/
    └── prompt-name/
        ├── metadata.json     # Version metadata
        ├── tags.json         # Tag registry
        ├── v1.md            # Version 1
        ├── v2.md            # Version 2
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

# Create a tag for production
promptv tags create email-template prod --version 3

# Get production version
promptv get email-template --label prod

# Compare versions
promptv diff email-template 2 3 --format side-by-side

# List all versions of a prompt
promptv list chatgpt-instructions

# Remove prompts
promptv remove chatgpt-instructions summarization-prompt --yes

# Set API key
promptv secrets set openai_api_key

# Estimate cost
promptv estimate-cost my-prompt --model gpt-4

# Launch playground
promptv playground --prompt my-prompt
```

## Development

Run tests:
```bash
pytest
pytest --cov=promptv  # With coverage
```

## License

MIT License
