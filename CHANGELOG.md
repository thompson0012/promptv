# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- New `promptv test` command for interactively testing prompts with LLM providers
  - Supports OpenAI, Anthropic, OpenRouter, and custom endpoints
  - Interactive chat session with streaming responses
  - Variable substitution prompting
  - Real-time cost tracking and token usage display
  - Support for temperature and max_tokens parameters
- New LLM provider implementations:
  - `OpenAIProvider` for OpenAI models
  - `AnthropicProvider` for Claude models
  - `OpenRouterProvider` for OpenRouter models
  - Factory function `create_provider()` for easy instantiation
- New `InteractiveTester` class for interactive chat sessions
- SDK method `test_prompt_interactive()` for programmatic testing
- Configuration updates:
  - Added OpenRouter provider to default configuration
  - Added OpenRouter to supported providers list
- Dependency updates:
  - Added `openai>=1.0.0`
  - Added `anthropic>=0.18.0`
  - Added `httpx>=0.25.0`

### Changed
- Enhanced configuration system to support additional LLM providers
- Improved secrets management to support new provider API keys

### Fixed
- None

## [0.1.7] - 2024-12-07

### Added
- Enhanced `promptv test` command with `--custom-endpoint` and `--api-key` parameters
  - `--custom-endpoint`: Specify custom API endpoint URLs for all providers
  - `--api-key`: Directly provide API keys (with security warning)
  - Mutual exclusivity validation between `--provider`, `--endpoint`, and `--custom-endpoint`
  - URL format validation for custom endpoints
  - Enhanced provider support for custom endpoints (Anthropic and OpenRouter)
- Enhanced SDK `test_prompt_interactive()` method with new parameters
- Comprehensive test coverage for new functionality
- Updated documentation with new usage examples and security warnings

### Changed
- Updated LLM provider implementations to support custom endpoints
  - `AnthropicProvider` now accepts custom base URLs
  - `OpenRouterProvider` now accepts custom base URLs
- Enhanced parameter validation and error handling in CLI
- Improved security warnings for direct API key usage

## [0.1.6] - 2024-12-02

### Added
- Initial release with core prompt management features
- Version control for prompts
- Variable substitution with Jinja2
- Tag/label system
- Cost estimation
- Secrets management
- Git-style diff visualization