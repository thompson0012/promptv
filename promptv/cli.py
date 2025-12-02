import click
import sys
import os
import tempfile
import subprocess
from pathlib import Path
import shutil
from .manager import PromptManager
from .tag_manager import TagManager
from .variable_engine import VariableEngine
from .secrets_manager import (
    SecretsManager,
    SecretsManagerError
)
from .config_manager import ConfigManager
from .exceptions import (
    PromptNotFoundError,
    TagNotFoundError,
    TagAlreadyExistsError,
    VersionNotFoundError,
    VariableMissingError
)
from .cost_estimator import CostEstimator, UnknownModelError
from .utils import (
    format_cost_estimate,
    format_cost_comparison,
    format_token_count,
    format_error
)
from .resources import list_available_models, get_pricing_data_date
from .diff_engine import DiffEngine, DiffFormat


@click.group()
@click.version_option(version='0.1.6')
@click.pass_context
def cli(ctx):
    """
    promptv - A CLI tool for managing prompts locally with versioning.
    
    On first run, creates ~/.promptv/.config and ~/.promptv/prompts directories.
    All prompts are saved in Markdown (.md) format.
    """
    # Auto-initialize on first run (skip for 'init' command)
    if ctx.invoked_subcommand != 'init':
        base_dir = Path.home() / ".promptv"
        if not base_dir.exists():
            try:
                # Silent initialization
                initialize_promptv_directory(silent=True)
            except Exception:
                # Silently ignore initialization errors
                # User can run 'promptv init' explicitly if needed
                pass


@cli.command()
@click.option('--source', required=True, type=click.Path(exists=True), help='Source file path')
@click.option('--name', required=True, help='Name for the prompt')
@click.option('--message', '-m', help='Commit message describing the changes')
@click.option('--tag', help='Create a tag for this version')
@click.option('--project', default='default', help='Project name for organizing prompts (default: default)')
def commit(source, name, message, tag, project):
    """
    Save a prompt file with a specific name.
    
    Examples:
        promptv commit --source prompt.md --name my-prompt
        promptv commit --source prompt.md --name my-prompt -m "Updated instructions"
        promptv commit --source prompt.md --name my-prompt --tag prod
        promptv commit --source prompt.md --name my-prompt --project my-app
    """
    try:
        manager = PromptManager()
        result = manager.commit_prompt(source, name, message=message, project=project)
        click.echo(f"✓ Committed prompt '{result['name']}' (version {result['version']})")
        click.echo(f"  Project: {project}")
        if message:
            click.echo(f"  Message: {message}")
        click.echo(f"  Saved to: {result['file_path']}")
        
        # Create tag if requested
        if tag:
            tag_manager = TagManager(manager.prompts_dir)
            tag_obj = tag_manager.create_tag(
                prompt_name=name,
                tag_name=tag,
                version=result['version'],
                allow_update=True,
                project=project
            )
            click.echo(f"  Tagged as: {tag}")
            
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except TagAlreadyExistsError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('name')
@click.option('--file', '-f', type=click.Path(exists=True), help='Read content from file')
@click.option('--content', '-c', help='Direct content input')
@click.option('--message', '-m', help='Commit message describing the changes')
@click.option('--project', default='default', help='Project name for organizing prompts (default: default)')
def set(name, file, content, message, project):
    """
    Set/update a prompt with the given name.
    
    You can provide content either from a file or directly:
    
    Examples:
        promptv set my-prompt -f prompt.txt
        promptv set my-prompt -c "This is my prompt content"
        promptv set my-prompt -m "Updated with new instructions" -f prompt.txt
        promptv set my-prompt --project my-app -f prompt.txt
        echo "Content" | promptv set my-prompt
    """
    try:
        manager = PromptManager()
        
        # Determine content source
        prompt_content = None
        if file:
            with open(file, 'r') as f:
                prompt_content = f.read()
        elif content:
            prompt_content = content
        elif not sys.stdin.isatty():
            # Read from stdin (pipe)
            prompt_content = sys.stdin.read()
        else:
            # Interactive mode - open editor or read multiline
            click.echo("Enter prompt content (press Ctrl+D when done):")
            prompt_content = sys.stdin.read()
        
        if not prompt_content:
            click.echo("Error: No content provided", err=True)
            sys.exit(1)
        
        result = manager.set_prompt(name, prompt_content, message=message, project=project)
        click.echo(f"✓ Set prompt '{result['name']}' (version {result['version']})")
        click.echo(f"  Project: {project}")
        if message:
            click.echo(f"  Message: {message}")
        click.echo(f"  Saved to: {result['file_path']}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('name')
@click.option('--version', default='latest', help='Version to edit (default: latest)')
@click.option('--message', '-m', help='Commit message for the changes')
@click.option('--project', default='default', help='Project name for organizing prompts (default: default)')
@click.option('--editor', help='Editor to use (default: $EDITOR or $VISUAL or nano)')
def edit(name, version, message, project, editor):
    """
    Edit a prompt directly in your terminal editor.
    
    Opens the specified prompt version in your default editor ($EDITOR or $VISUAL),
    or nano if neither is set. After editing, saves the changes as a new version.
    
    Examples:
        promptv edit my-prompt
        promptv edit my-prompt --version 2
        promptv edit my-prompt -m "Updated instructions"
        promptv edit my-prompt --project my-app
        promptv edit my-prompt --editor vim
    """
    try:
        manager = PromptManager()
        
        # Check if prompt exists
        if not manager.prompt_exists(name, project=project):
            click.echo(f"Error: Prompt '{name}' not found", err=True)
            click.echo(f"  Project: {project}", err=True)
            sys.exit(1)
        
        # Get the current content
        content = manager.get_prompt(name, version, project=project)
        
        if content is None:
            click.echo(f"Error: Version '{version}' not found for prompt '{name}'", err=True)
            sys.exit(1)
        
        # Determine which editor to use
        if not editor:
            editor = os.environ.get('EDITOR') or os.environ.get('VISUAL') or 'nano'
        
        # Create a temporary file with the content
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as tmp_file:
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        try:
            # Open the editor
            subprocess.run([editor, tmp_path], check=True)
            
            # Read the edited content
            with open(tmp_path, 'r') as f:
                edited_content = f.read()
            
            # Check if content was changed
            if edited_content == content:
                click.echo("No changes made. Prompt not updated.")
                return
            
            # Save the new version
            result = manager.set_prompt(name, edited_content, message=message, project=project)
            click.echo(f"✓ Updated prompt '{result['name']}' (version {result['version']})")
            click.echo(f"  Project: {project}")
            if message:
                click.echo(f"  Message: {message}")
            click.echo(f"  Saved to: {result['file_path']}")
            
        finally:
            # Clean up temporary file
            os.unlink(tmp_path)
            
    except PromptNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except subprocess.CalledProcessError:
        click.echo("Error: Editor exited with error", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def parse_variables(ctx, param, value):
    """
    Parse variable arguments in format: key1=val1 key2=val2
    Supports both --var "key1=val1 key2=val2" and --var key1=val1 --var key2=val2
    """
    if not value:
        return {}
    
    var_dict = {}
    for var_arg in value:
        # Split by whitespace to handle multiple key=value pairs in one --var
        parts = var_arg.split()
        for part in parts:
            if '=' not in part:
                raise click.BadParameter(f"Invalid variable format '{part}'. Expected key=value")
            key, val = part.split('=', 1)
            var_dict[key.strip()] = val.strip()
    
    return var_dict


@cli.command()
@click.argument('name')
@click.option('--version', default=None, help='Version to retrieve')
@click.option('--label', help='Tag/label to retrieve')
@click.option('--var', multiple=True, callback=parse_variables, 
              help='Variable substitution (supports: "key1=val1 key2=val2" or multiple --var flags)')
@click.option('--project', default='default', help='Project name for organizing prompts (default: default)')
def get(name, version, label, var, project):
    """
    Retrieve a specific version of a prompt.
    
    Examples:
        promptv get my-prompt --version latest
        promptv get my-prompt --version 1
        promptv get my-prompt --label prod
        promptv get my-prompt --var "name=Alice count=5"
        promptv get my-prompt --var key1=val1 --var key2=val2
        promptv get my-prompt --project my-app
    """
    try:
        manager = PromptManager()
        tag_manager = TagManager(manager.prompts_dir)
        
        # Determine which version to get
        if label and version:
            click.echo("Error: Cannot specify both --version and --label", err=True)
            sys.exit(1)
        
        # Resolve version reference
        if label:
            # Resolve tag to version number
            metadata = manager._load_metadata(name, project=project)
            if not metadata.versions:
                raise PromptNotFoundError(name)
            max_version = metadata.current_version
            version_num = tag_manager.resolve_version(name, label, max_version, project=project)
            version_ref = str(version_num)
        elif version:
            version_ref = version
        else:
            version_ref = "latest"
        
        content = manager.get_prompt(name, version_ref, project=project)
        
        if content is None:
            click.echo(f"Error: Prompt '{name}' not found or version '{version_ref}' does not exist", err=True)
            sys.exit(1)
        
        # Apply variable substitution if requested
        if var:
            var_engine = VariableEngine()
            
            # Validate and render
            is_valid, missing = var_engine.validate_variables(content, var)
            if not is_valid:
                raise VariableMissingError(missing)
            
            content = var_engine.render(content, var)
        
        click.echo(content)
    except PromptNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except TagNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except VersionNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except VariableMissingError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except ValueError as e:
        click.echo(f"Error: Invalid version number", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command(name='list')
@click.argument('name', required=False)
@click.option('--show-tags', is_flag=True, help='Show tags for each prompt')
@click.option('--show-variables', is_flag=True, help='Show variables for each version')
@click.option('--project', default='default', help='Project name for organizing prompts (default: default)')
def list_command(name, show_tags, show_variables, project):
    """
    List all versions and metadata for a specific prompt name.
    If no name is provided, list all prompts.
    
    Examples:
        promptv list
        promptv list my-prompt
        promptv list my-prompt --show-tags
        promptv list my-prompt --show-variables
        promptv list --project my-app
    """
    try:
        manager = PromptManager()
        tag_manager = TagManager(manager.prompts_dir)
        
        if name:
            # List specific prompt
            metadata = manager.list_versions(name, project=project)
            
            if metadata is None:
                click.echo(f"Error: Prompt '{name}' not found", err=True)
                sys.exit(1)
            
            click.echo(f"Prompt: {metadata['name']}")
            click.echo(f"Project: {project}")
            click.echo(f"Total versions: {len(metadata['versions'])}")
            
            # Show tags if requested
            if show_tags:
                tags = tag_manager.list_tags(name, project=project)
                if tags:
                    click.echo(f"\nTags:")
                    for tag_name, tag_obj in tags.items():
                        desc = f" - {tag_obj.description}" if tag_obj.description else ""
                        click.echo(f"  {tag_name} → v{tag_obj.version}{desc}")
                else:
                    click.echo("\nTags: (none)")
            
            click.echo("\nVersions:")
            
            for version_info in metadata['versions']:
                click.echo(f"\n  Version {version_info['version']}:")
                click.echo(f"    Timestamp: {version_info['timestamp']}")
                if version_info.get('message'):
                    click.echo(f"    Message: {version_info['message']}")
                click.echo(f"    File: {version_info['file_path']}")
                if version_info.get('source_file'):
                    click.echo(f"    Source: {version_info['source_file']}")
                if show_variables and version_info.get('variables'):
                    click.echo(f"    Variables: {', '.join(version_info['variables'])}")
        else:
            # List all prompts
            prompts_dir = manager.prompts_dir
            if not prompts_dir.exists():
                click.echo("No prompts found")
                return
            
            prompt_dirs = [d for d in prompts_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
            
            if not prompt_dirs:
                click.echo("No prompts found")
                return
            
            click.echo(f"Found {len(prompt_dirs)} prompt(s):\n")
            
            for prompt_dir in sorted(prompt_dirs, key=lambda p: p.name):
                prompt_name = prompt_dir.name
                metadata = manager.list_versions(prompt_name)
                if metadata:
                    version_count = len(metadata['versions'])
                    current_ver = metadata['versions'][-1]['version'] if metadata['versions'] else 0
                    click.echo(f"  {prompt_name} (v{current_ver}, {version_count} version(s))")
                    
                    if show_tags:
                        tags = tag_manager.list_tags(prompt_name)
                        if tags:
                            tag_list = [f"{tn}→v{to.version}" for tn, to in tags.items()]
                            click.echo(f"    Tags: {', '.join(tag_list)}")
                        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('names', nargs=-1, required=True)
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation prompt')
@click.option('--project', default='default', help='Project name for organizing prompts (default: default)')
def remove(names, yes, project):
    """
    Remove one or more prompts by name.
    
    Examples:
        promptv remove my-prompt
        promptv remove prompt1 prompt2 prompt3
        promptv remove my-prompt --yes
        promptv remove my-prompt --project my-app
    """
    try:
        manager = PromptManager()
        
        # Check which prompts exist
        existing = [name for name in names if manager.prompt_exists(name, project=project)]
        not_existing = [name for name in names if not manager.prompt_exists(name, project=project)]
        
        if not existing:
            click.echo("Error: None of the specified prompts exist", err=True)
            for name in not_existing:
                click.echo(f"  - {name} (not found)")
            sys.exit(1)
        
        if not_existing:
            click.echo("Warning: Some prompts do not exist:")
            for name in not_existing:
                click.echo(f"  - {name}")
            click.echo()
        
        # Confirm deletion
        if not yes:
            click.echo(f"About to remove {len(existing)} prompt(s):")
            for name in existing:
                click.echo(f"  - {name}")
            click.echo(f"  Project: {project}")
            if not click.confirm("\nAre you sure?"):
                click.echo("Cancelled")
                return
        
        # Remove prompts
        results = manager.remove_prompts([n for n in names], project=project)
        
        click.echo()
        for name, success in results.items():
            if success:
                click.echo(f"✓ Removed prompt '{name}'")
            else:
                click.echo(f"✗ Failed to remove prompt '{name}' (not found)")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# Tag management commands
@cli.group()
def tag():
    """Manage tags for prompts."""
    pass


@tag.command('create')
@click.argument('prompt_name')
@click.argument('tag_name')
@click.option('--version', '-v', type=int, help='Version to tag (default: latest)')
@click.option('--description', '-d', help='Tag description')
@click.option('--force', '-f', is_flag=True, help='Update existing tag')
@click.option('--project', default='default', help='Project name for organizing prompts (default: default)')
def tag_create(prompt_name, tag_name, version, description, force, project):
    """
    Create a tag for a specific version.
    
    Examples:
        promptv tag create my-prompt prod --version 3
        promptv tag create my-prompt stable -d "Stable release"
        promptv tag create my-prompt prod --force  # Update existing tag to latest
        promptv tag create my-prompt prod --project my-app
    """
    try:
        manager = PromptManager()
        tag_manager = TagManager(manager.prompts_dir)
        
        # Get metadata to determine version
        metadata = manager._load_metadata(prompt_name, project=project)
        if not metadata.versions:
            raise PromptNotFoundError(prompt_name)
        
        # Use latest version if not specified
        if version is None:
            version = metadata.current_version
        else:
            # Validate version exists
            if version < 1 or version > metadata.current_version:
                click.echo(f"Error: Version {version} does not exist (available: 1-{metadata.current_version})", err=True)
                sys.exit(1)
        
        tag_obj = tag_manager.create_tag(
            prompt_name=prompt_name,
            tag_name=tag_name,
            version=version,
            description=description,
            allow_update=force,
            project=project
        )
        
        action = "Updated" if force else "Created"
        click.echo(f"✓ {action} tag '{tag_name}' → v{version} for prompt '{prompt_name}'")
        click.echo(f"  Project: {project}")
        if description:
            click.echo(f"  Description: {description}")
            
    except PromptNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except TagAlreadyExistsError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@tag.command('list')
@click.argument('prompt_name')
@click.option('--project', default='default', help='Project name for organizing prompts (default: default)')
def tag_list(prompt_name, project):
    """
    List all tags for a prompt.
    
    Examples:
        promptv tag list my-prompt
        promptv tag list my-prompt --project my-app
    """
    try:
        manager = PromptManager()
        tag_manager = TagManager(manager.prompts_dir)
        
        # Check if prompt exists
        if not manager.prompt_exists(prompt_name, project=project):
            raise PromptNotFoundError(prompt_name)
        
        tags = tag_manager.list_tags(prompt_name, project=project)
        
        if not tags:
            click.echo(f"No tags found for prompt '{prompt_name}'")
            return
        
        click.echo(f"Tags for prompt '{prompt_name}':\n")
        
        for tag_name, tag_obj in sorted(tags.items()):
            desc = f" - {tag_obj.description}" if tag_obj.description else ""
            click.echo(f"  {tag_name} → v{tag_obj.version}{desc}")
            click.echo(f"    Created: {tag_obj.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            if tag_obj.updated_at != tag_obj.created_at:
                click.echo(f"    Updated: {tag_obj.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")
                
    except PromptNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@tag.command('show')
@click.argument('prompt_name')
@click.argument('tag_name')
@click.option('--project', default='default', help='Project name for organizing prompts (default: default)')
def tag_show(prompt_name, tag_name, project):
    """
    Show details about a specific tag.
    
    Examples:
        promptv tag show my-prompt prod
        promptv tag show my-prompt prod --project my-app
    """
    try:
        manager = PromptManager()
        tag_manager = TagManager(manager.prompts_dir)
        
        tag_obj = tag_manager.get_tag(prompt_name, tag_name, project=project)
        
        if tag_obj is None:
            raise TagNotFoundError(tag_name, prompt_name)
        
        click.echo(f"Tag: {tag_obj.name}")
        click.echo(f"Prompt: {prompt_name}")
        click.echo(f"Project: {project}")
        click.echo(f"Version: {tag_obj.version}")
        if tag_obj.description:
            click.echo(f"Description: {tag_obj.description}")
        click.echo(f"Created: {tag_obj.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        click.echo(f"Updated: {tag_obj.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")
        
    except TagNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@tag.command('delete')
@click.argument('prompt_name')
@click.argument('tag_name')
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation prompt')
@click.option('--project', default='default', help='Project name for organizing prompts (default: default)')
def tag_delete(prompt_name, tag_name, yes, project):
    """
    Delete a tag.
    
    Examples:
        promptv tag delete my-prompt old-version
        promptv tag delete my-prompt staging --yes
        promptv tag delete my-prompt prod --project my-app
    """
    try:
        manager = PromptManager()
        tag_manager = TagManager(manager.prompts_dir)
        
        # Check if tag exists
        tag_obj = tag_manager.get_tag(prompt_name, tag_name, project=project)
        if tag_obj is None:
            raise TagNotFoundError(tag_name, prompt_name)
        
        # Confirm deletion
        if not yes:
            click.echo(f"About to delete tag '{tag_name}' (→ v{tag_obj.version}) from prompt '{prompt_name}'")
            click.echo(f"  Project: {project}")
            if not click.confirm("\nAre you sure?"):
                click.echo("Cancelled")
                return
        
        tag_manager.delete_tag(prompt_name, tag_name, project=project)
        click.echo(f"✓ Deleted tag '{tag_name}' from prompt '{prompt_name}'")
        
    except TagNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# Variable and rendering commands
@cli.command()
@click.argument('prompt_name')
@click.option('--version', help='Version to render (default: latest)')
@click.option('--label', help='Tag/label to render')
@click.option('--var', multiple=True, required=True, help='Variable substitution (key=value)')
def render(prompt_name, version, label, var):
    """
    Render a prompt with variable substitution.
    
    Examples:
        promptv render my-prompt --var name=Alice --var count=5
        promptv render my-prompt --label prod --var api_key=sk-xxx
        promptv render my-prompt --version 2 --var temperature=0.7
    """
    try:
        manager = PromptManager()
        tag_manager = TagManager(manager.prompts_dir)
        var_engine = VariableEngine()
        
        # Determine which version to get
        if label and version:
            click.echo("Error: Cannot specify both --version and --label", err=True)
            sys.exit(1)
        
        # Resolve version reference
        if label:
            metadata = manager._load_metadata(prompt_name)
            if not metadata.versions:
                raise PromptNotFoundError(prompt_name)
            max_version = metadata.current_version
            version_num = tag_manager.resolve_version(prompt_name, label, max_version)
            version_ref = str(version_num)
        elif version:
            version_ref = version
        else:
            version_ref = "latest"
        
        content = manager.get_prompt(prompt_name, version_ref)
        
        if content is None:
            raise PromptNotFoundError(prompt_name)
        
        # Parse variables
        var_dict = {}
        for v in var:
            if '=' not in v:
                click.echo(f"Error: Invalid variable format '{v}'. Expected key=value", err=True)
                sys.exit(1)
            key, value = v.split('=', 1)
            var_dict[key] = value
        
        # Validate and render
        is_valid, missing = var_engine.validate_variables(content, var_dict)
        if not is_valid:
            raise VariableMissingError(missing)
        
        rendered = var_engine.render(content, var_dict)
        click.echo(rendered)
        
    except PromptNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except TagNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except VariableMissingError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.group()
def variables():
    """Manage and inspect variables in prompts."""
    pass


@variables.command('list')
@click.argument('prompt_name')
@click.option('--version', help='Version to inspect (default: latest)')
def variables_list(prompt_name, version):
    """
    List all variables in a prompt.
    
    Examples:
        promptv variables list my-prompt
        promptv variables list my-prompt --version 2
    """
    try:
        manager = PromptManager()
        var_engine = VariableEngine()
        
        version_ref = version if version else "latest"
        content = manager.get_prompt(prompt_name, version_ref)
        
        if content is None:
            raise PromptNotFoundError(prompt_name)
        
        variables_found = var_engine.extract_variables(content)
        
        if not variables_found:
            click.echo(f"No variables found in prompt '{prompt_name}' (version {version_ref})")
            return
        
        click.echo(f"Variables in prompt '{prompt_name}' (version {version_ref}):\n")
        for var_name in variables_found:
            click.echo(f"  {var_name}")
        
        click.echo(f"\nTotal: {len(variables_found)} variable(s)")
        
    except PromptNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.group()
def secrets():
    """
    Manage API keys and secrets securely.
    
    Supports both provider API keys and generic project-scoped secrets.
    All secrets are stored encrypted in ~/.promptv/.secrets/secrets.json
    
    Examples:
        # Provider API keys
        promptv secrets set openai --provider
        promptv secrets get openai --provider
        
        # Generic secrets
        promptv secrets set DATABASE_URL
        promptv secrets set API_KEY --project my-app
        promptv secrets list
    """
    pass


@secrets.command('set')
@click.argument('key')
@click.option('--provider', is_flag=True, 
              help='Set as provider API key (validates against supported providers)')
@click.option('--project', default='default', 
              help='Project name for secret scoping (default: "default")')
def secrets_set(key, provider, project):
    """
    Set an API key or environment secret.
    
    Provider API keys are global and validated against supported providers.
    Generic secrets can be scoped to specific projects.
    
    Examples:
        # Provider API key
        promptv secrets set openai --provider
        promptv secrets set anthropic --provider
        
        # Generic secret (uses "default" project)
        promptv secrets set DATABASE_URL
        promptv secrets set MY_API_KEY
        
        # Project-scoped secret
        promptv secrets set DATABASE_URL --project my-app
        promptv secrets set REDIS_URL --project moonshoot
    """
    try:
        manager = SecretsManager()
        
        if provider:
            # Validate provider
            if key not in manager.SUPPORTED_PROVIDERS:
                click.echo(f"❌ Error: Unsupported provider '{key}'", err=True)
                click.echo(f"\nSupported providers:", err=True)
                for p in manager.SUPPORTED_PROVIDERS:
                    click.echo(f"  - {p}", err=True)
                sys.exit(1)
            
            # Prompt for API key (hidden input)
            click.echo(f"Setting API key for provider: {key}")
            click.echo("\n⚠️  Security Note:")
            click.echo("   Your API key will be stored locally in ~/.promptv/.secrets/secrets.json")
            click.echo("   The file has restrictive permissions (owner read/write only).\n")
            
            api_key = click.prompt(
                f"Enter API key for {key}",
                hide_input=True,
                confirmation_prompt=True
            )
            
            # Store the key
            manager.set_api_key(key, api_key)
            click.echo(f"\n✓ API key for '{key}' stored securely")
        else:
            # Generic secret
            click.echo(f"Setting secret: {key}")
            if project != 'default':
                click.echo(f"Project: {project}")
            click.echo("\n⚠️  Security Note:")
            click.echo("   Your secret will be stored locally in ~/.promptv/.secrets/secrets.json")
            click.echo("   The file has restrictive permissions (owner read/write only).\n")
            
            value = click.prompt(
                f"Enter value for {key}",
                hide_input=True,
                confirmation_prompt=True
            )
            
            # Store the secret
            manager.set_secret(key, value, project=project)
            click.echo(f"\n✓ Secret '{key}' stored securely")
            if project != 'default':
                click.echo(f"  Project: {project}")
        
    except SecretsManagerError as e:
        click.echo(f"\n❌ Secrets Error:\n{e}", err=True)
        sys.exit(1)
    except click.Abort:
        click.echo("\nCancelled", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@secrets.command('get')
@click.argument('key')
@click.option('--provider', is_flag=True,
              help='Get provider API key')
@click.option('--project', default='default',
              help='Project name for secret scoping (default: "default")')
def secrets_get(key, provider, project):
    """
    Retrieve a secret or API key.
    
    Shows the last 4 characters of provider API keys for security.
    Generic secrets are displayed in full.
    
    Examples:
        # Provider API key
        promptv secrets get openai --provider
        promptv secrets get anthropic --provider
        
        # Generic secret
        promptv secrets get DATABASE_URL
        promptv secrets get API_KEY --project my-app
    """
    try:
        manager = SecretsManager()
        
        if provider:
            # Get provider API key
            api_key = manager.get_api_key(key)
            
            if api_key:
                # Show masked key (last 4 chars only)
                if len(api_key) > 4:
                    masked = f"{'*' * (len(api_key) - 4)}{api_key[-4:]}"
                else:
                    masked = "****"
                
                click.echo(f"Provider API Key: {key}")
                click.echo(f"Value: {masked}")
                click.echo(f"\n(Showing last 4 characters for security)")
            else:
                click.echo(f"❌ No API key found for provider '{key}'", err=True)
                click.echo(f"\nTo add an API key, run:")
                click.echo(f"  promptv secrets set {key} --provider")
                sys.exit(1)
        else:
            # Get generic secret
            value = manager.get_secret(key, project=project)
            
            if value:
                click.echo(f"Secret: {key}")
                if project != 'default':
                    click.echo(f"Project: {project}")
                click.echo(f"Value: {value}")
            else:
                click.echo(f"❌ No secret found: '{key}'", err=True)
                if project != 'default':
                    click.echo(f"   Project: {project}", err=True)
                click.echo(f"\nTo add a secret, run:")
                if project != 'default':
                    click.echo(f"  promptv secrets set {key} --project {project}")
                else:
                    click.echo(f"  promptv secrets set {key}")
                sys.exit(1)
        
    except SecretsManagerError as e:
        click.echo(f"\n❌ Secrets Error:\n{e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@secrets.command('list')
@click.option('--project', 
              help='Filter by project name (shows all if not specified)')
def secrets_list(project):
    """
    List all configured secrets and API keys.
    
    Shows provider API keys and project-scoped secrets grouped by project.
    
    Examples:
        promptv secrets list
        promptv secrets list --project my-app
        promptv secrets list --project default
    """
    try:
        manager = SecretsManager()
        all_secrets = manager.list_all_secrets(project=project)
        
        providers = all_secrets.get('providers', [])
        secrets = all_secrets.get('secrets', {})
        
        if not providers and not secrets:
            if project:
                click.echo(f"No secrets found for project '{project}'.")
            else:
                click.echo("No secrets configured.")
            click.echo("\nTo add secrets, run:")
            click.echo("  promptv secrets set <key>                    # Generic secret")
            click.echo("  promptv secrets set <key> --project <name>   # Project-scoped secret")
            click.echo("  promptv secrets set <provider> --provider    # Provider API key")
            return
        
        # Display provider API keys
        if providers:
            click.echo("Provider API Keys:")
            for prov in providers:
                click.echo(f"  ✓ {prov}")
            click.echo()
        
        # Display project secrets
        if secrets:
            click.echo("Project Secrets:")
            for proj_name, keys in secrets.items():
                click.echo(f"  {proj_name}:")
                for secret_key in keys:
                    click.echo(f"    ✓ {secret_key}")
                click.echo()
        
        # Summary
        total_providers = len(providers)
        total_secrets = sum(len(keys) for keys in secrets.values())
        total_projects = len(secrets)
        
        parts = []
        if total_providers:
            parts.append(f"{total_providers} provider(s)")
        if total_secrets:
            parts.append(f"{total_secrets} secret(s) across {total_projects} project(s)")
        
        if parts:
            click.echo(f"Total: {', '.join(parts)}")
        
    except SecretsManagerError as e:
        click.echo(f"\n❌ Secrets Error:\n{e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@secrets.command('delete')
@click.argument('key')
@click.option('--provider', is_flag=True,
              help='Delete provider API key')
@click.option('--project', default='default',
              help='Project name for secret scoping (default: "default")')
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation')
def secrets_delete(key, provider, project, yes):
    """
    Delete a secret or API key.
    
    Examples:
        # Provider API key
        promptv secrets delete openai --provider
        promptv secrets delete anthropic --provider --yes
        
        # Generic secret
        promptv secrets delete DATABASE_URL
        promptv secrets delete API_KEY --project my-app --yes
    """
    try:
        manager = SecretsManager()
        
        if provider:
            # Check if provider key exists
            if not manager.has_api_key(key):
                click.echo(f"No API key found for provider '{key}'")
                return
            
            # Confirm deletion
            if not yes:
                click.echo(f"⚠️  About to delete API key for provider: {key}")
                if not click.confirm("\nAre you sure?"):
                    click.echo("Cancelled")
                    return
            
            manager.delete_api_key(key)
            click.echo(f"✓ API key for '{key}' deleted")
        else:
            # Check if generic secret exists
            value = manager.get_secret(key, project=project)
            if not value:
                click.echo(f"No secret found: '{key}'")
                if project != 'default':
                    click.echo(f"  Project: {project}")
                return
            
            # Confirm deletion
            if not yes:
                click.echo(f"⚠️  About to delete secret: {key}")
                if project != 'default':
                    click.echo(f"   Project: {project}")
                if not click.confirm("\nAre you sure?"):
                    click.echo("Cancelled")
                    return
            
            manager.delete_secret(key, project=project)
            click.echo(f"✓ Secret '{key}' deleted")
            if project != 'default':
                click.echo(f"  Project: {project}")
        
    except SecretsManagerError as e:
        click.echo(f"\n❌ Secrets Error:\n{e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@secrets.command('test')
@click.argument('provider')
def secrets_test(provider):
    """
    Test if an API key is configured for a provider.
    
    Examples:
        promptv secrets test openai
        promptv secrets test anthropic
    """
    try:
        manager = SecretsManager()
        
        if manager.has_api_key(provider):
            click.echo(f"✓ API key for '{provider}' is configured")
            
            # Show partial key for verification (last 4 chars only)
            api_key = manager.get_api_key(provider)
            if api_key and len(api_key) > 4:
                masked = f"{'*' * (len(api_key) - 4)}{api_key[-4:]}"
                click.echo(f"  Key: {masked}")
        else:
            click.echo(f"❌ No API key configured for '{provider}'")
            click.echo("\nTo add an API key, run:")
            click.echo(f"  promptv secrets set {provider}")
        
    except SecretsManagerError as e:
        click.echo(f"\n❌ Secrets Error:\n{e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@secrets.command('activate')
@click.option('--project', default='default',
              help='Project name to activate secrets from (default: "default")')
@click.option('--format', 'output_format', 
              type=click.Choice(['shell', 'json', 'export'], case_sensitive=False),
              default='shell',
              help='Output format: shell (default), json, or export')
@click.option('--include-providers/--no-include-providers',
              default=True,
              help='Include provider API keys (default: True)')
def secrets_activate(project, output_format, include_providers):
    """
    Export secrets as environment variables for shell sourcing.
    
    This command outputs shell export statements that can be sourced
    into your current shell, similar to 'source .env'.
    
    Usage:
        source <(promptv secrets activate --project moonshoot)
        eval "$(promptv secrets activate --project moonshoot)"
    
    Shell Function (add to ~/.bashrc or ~/.zshrc):
        promptv-activate() {
            eval "$(promptv secrets activate --project ${1:-default})"
        }
        
        # Then use: promptv-activate moonshoot
    
    Examples:
        # Activate default project
        source <(promptv secrets activate)
        
        # Activate specific project
        source <(promptv secrets activate --project moonshoot)
        
        # Exclude provider API keys
        source <(promptv secrets activate --project moonshoot --no-include-providers)
        
        # JSON output for other tools
        promptv secrets activate --project moonshoot --format json
        
        # Export statements only (no comments)
        promptv secrets activate --project moonshoot --format export
    """
    try:
        manager = SecretsManager()
        secrets = manager.get_project_secrets_with_values(
            project=project,
            include_providers=include_providers
        )
        
        if not secrets:
            click.echo(f"# No secrets found for project '{project}'", err=True)
            return
        
        if output_format == 'json':
            import json
            click.echo(json.dumps(secrets, indent=2))
        
        elif output_format == 'export':
            for key, value in sorted(secrets.items()):
                click.echo(f'export {key}="{value}"')
        
        else:
            for key, value in sorted(secrets.items()):
                click.echo(f'export {key}="{value}"')
            click.echo(f"# Activated {len(secrets)} secret(s) from project '{project}'")
        
    except SecretsManagerError as e:
        click.echo(f"# Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"# Error: {e}", err=True)
        sys.exit(1)


@cli.group()
def cost():
    """
    Cost estimation commands for LLM API calls.
    
    Estimate token counts and costs before making API calls.
    """
    pass


@cost.command(name='estimate')
@click.argument('prompt_name')
@click.option('--version', '-v', help='Version number or "latest" (default: latest)')
@click.option('--label', '-l', help='Tag/label to retrieve (e.g., prod, staging)')
@click.option('--var', '-d', multiple=True, help='Variables in key=value format (can be used multiple times)')
@click.option('--model', '-m', default='gpt-4', help='Model name (default: gpt-4)')
@click.option('--provider', '-p', default='openai', help='Provider name (default: openai)')
@click.option('--output-tokens', '-o', type=int, default=500, help='Estimated output tokens (default: 500)')
def cost_estimate(prompt_name, version, label, var, model, provider, output_tokens):
    """
    Estimate the cost of running a prompt.
    
    Examples:
        promptv cost estimate my-prompt
        promptv cost estimate my-prompt --label prod
        promptv cost estimate my-prompt --model gpt-3.5-turbo
        promptv cost estimate my-prompt --var name=Alice --var city=NYC
        promptv cost estimate my-prompt -m claude-3-sonnet -p anthropic -o 1000
    """
    try:
        manager = PromptManager()
        var_engine = VariableEngine()
        
        # Parse variables
        variables = {}
        for v in var:
            if '=' not in v:
                click.echo(f"Error: Variable must be in key=value format: {v}", err=True)
                sys.exit(1)
            key, value = v.split('=', 1)
            variables[key.strip()] = value.strip()
        
        # Get prompt content
        if label:
            tag_manager = TagManager(manager.prompts_dir)
            metadata_obj = manager._load_metadata(prompt_name)
            if not metadata_obj.versions:
                raise PromptNotFoundError(prompt_name)
            version_num = tag_manager.resolve_version(prompt_name, label, metadata_obj.current_version)
            content, metadata = manager.get_prompt_with_metadata(prompt_name, str(version_num))
        elif version:
            content, metadata = manager.get_prompt_with_metadata(prompt_name, version)
        else:
            content, metadata = manager.get_prompt_with_metadata(prompt_name)
        
        # Render with variables if provided
        if variables:
            content = var_engine.render(content, variables)
        
        # Estimate cost
        estimator = CostEstimator()
        cost = estimator.estimate_cost(
            text=content,
            model=model,
            provider=provider,
            estimated_output_tokens=output_tokens
        )
        
        # Display result
        format_cost_estimate(cost, show_detail=True)
        
    except PromptNotFoundError as e:
        format_error(str(e), "Use 'promptv list' to see available prompts")
        sys.exit(1)
    except TagNotFoundError as e:
        format_error(str(e), "Use 'promptv tag list <prompt>' to see available tags")
        sys.exit(1)
    except UnknownModelError as e:
        format_error(str(e), "Use 'promptv cost models' to see available models")
        sys.exit(1)
    except VariableMissingError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cost.command(name='tokens')
@click.argument('prompt_name')
@click.option('--version', '-v', help='Version number or "latest" (default: latest)')
@click.option('--label', '-l', help='Tag/label to retrieve (e.g., prod, staging)')
@click.option('--var', '-d', multiple=True, help='Variables in key=value format (can be used multiple times)')
@click.option('--model', '-m', default='gpt-4', help='Model name (default: gpt-4)')
@click.option('--provider', '-p', default='openai', help='Provider name (default: openai)')
def cost_tokens(prompt_name, version, label, var, model, provider):
    """
    Count tokens in a prompt.
    
    Examples:
        promptv cost tokens my-prompt
        promptv cost tokens my-prompt --label prod
        promptv cost tokens my-prompt --model gpt-3.5-turbo
        promptv cost tokens my-prompt --var name=Alice
    """
    try:
        manager = PromptManager()
        var_engine = VariableEngine()
        
        # Parse variables
        variables = {}
        for v in var:
            if '=' not in v:
                click.echo(f"Error: Variable must be in key=value format: {v}", err=True)
                sys.exit(1)
            key, value = v.split('=', 1)
            variables[key.strip()] = value.strip()
        
        # Get prompt content
        if label:
            tag_manager = TagManager(manager.prompts_dir)
            metadata_obj = manager._load_metadata(prompt_name)
            if not metadata_obj.versions:
                raise PromptNotFoundError(prompt_name)
            version_num = tag_manager.resolve_version(prompt_name, label, metadata_obj.current_version)
            content, metadata = manager.get_prompt_with_metadata(prompt_name, str(version_num))
        elif version:
            content, metadata = manager.get_prompt_with_metadata(prompt_name, version)
        else:
            content, metadata = manager.get_prompt_with_metadata(prompt_name)
        
        # Render with variables if provided
        if variables:
            content = var_engine.render(content, variables)
        
        # Count tokens
        estimator = CostEstimator()
        count = estimator.count_tokens(content, model, provider)
        
        # Display result
        format_token_count(count, model, provider)
        
    except PromptNotFoundError as e:
        format_error(str(e), "Use 'promptv list' to see available prompts")
        sys.exit(1)
    except TagNotFoundError as e:
        format_error(str(e), "Use 'promptv tag list <prompt>' to see available tags")
        sys.exit(1)
    except UnknownModelError as e:
        format_error(str(e), "Use 'promptv cost models' to see available models")
        sys.exit(1)
    except VariableMissingError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cost.command(name='compare')
@click.argument('prompt_name')
@click.option('--version', '-v', help='Version number or "latest" (default: latest)')
@click.option('--label', '-l', help='Tag/label to retrieve (e.g., prod, staging)')
@click.option('--var', '-d', multiple=True, help='Variables in key=value format (can be used multiple times)')
@click.option('--models', '-m', multiple=True, help='Models to compare in provider/model format (e.g., openai/gpt-4)')
@click.option('--output-tokens', '-o', type=int, default=500, help='Estimated output tokens (default: 500)')
def cost_compare(prompt_name, version, label, var, models, output_tokens):
    """
    Compare costs across multiple models.
    
    Examples:
        promptv cost compare my-prompt -m openai/gpt-4 -m openai/gpt-3.5-turbo
        promptv cost compare my-prompt --label prod -m anthropic/claude-3-sonnet -m openai/gpt-4
        promptv cost compare my-prompt --var name=Alice -m openai/gpt-4o -m google/gemini-1.5-pro
    """
    try:
        manager = PromptManager()
        var_engine = VariableEngine()
        
        # Parse variables
        variables = {}
        for v in var:
            if '=' not in v:
                click.echo(f"Error: Variable must be in key=value format: {v}", err=True)
                sys.exit(1)
            key, value = v.split('=', 1)
            variables[key.strip()] = value.strip()
        
        # Get prompt content
        if label:
            tag_manager = TagManager(manager.prompts_dir)
            metadata_obj = manager._load_metadata(prompt_name)
            if not metadata_obj.versions:
                raise PromptNotFoundError(prompt_name)
            version_num = tag_manager.resolve_version(prompt_name, label, metadata_obj.current_version)
            content, metadata = manager.get_prompt_with_metadata(prompt_name, str(version_num))
        elif version:
            content, metadata = manager.get_prompt_with_metadata(prompt_name, version)
        else:
            content, metadata = manager.get_prompt_with_metadata(prompt_name)
        
        # Render with variables if provided
        if variables:
            content = var_engine.render(content, variables)
        
        # Parse model specifications or use defaults
        if models:
            model_list = []
            for model_spec in models:
                if '/' not in model_spec:
                    click.echo(f"Error: Model must be in provider/model format: {model_spec}", err=True)
                    sys.exit(1)
                provider, model = model_spec.split('/', 1)
                model_list.append((provider.strip(), model.strip()))
        else:
            # Default comparison set
            model_list = [
                ('openai', 'gpt-4'),
                ('openai', 'gpt-4-turbo'),
                ('openai', 'gpt-3.5-turbo'),
                ('anthropic', 'claude-3-opus-20240229'),
                ('anthropic', 'claude-3-sonnet-20240229')
            ]
        
        # Compare costs
        estimator = CostEstimator()
        comparisons = estimator.compare_costs(content, model_list, output_tokens)
        
        # Display results
        format_cost_comparison(comparisons)
        
    except PromptNotFoundError as e:
        format_error(str(e), "Use 'promptv list' to see available prompts")
        sys.exit(1)
    except TagNotFoundError as e:
        format_error(str(e), "Use 'promptv tag list <prompt>' to see available tags")
        sys.exit(1)
    except VariableMissingError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cost.command(name='models')
@click.option('--provider', '-p', help='Filter by provider (e.g., openai, anthropic)')
def cost_models(provider):
    """
    List available models and providers for cost estimation.
    
    Examples:
        promptv cost models
        promptv cost models --provider openai
        promptv cost models -p anthropic
    """
    try:
        models_dict = list_available_models(provider)
        
        click.echo("\n📊 Available Models for Cost Estimation\n")
        
        for prov, model_list in models_dict.items():
            click.echo(f"[{prov}]")
            for model in model_list:
                click.echo(f"  • {model}")
            click.echo()
        
        if not provider:
            click.echo("💡 Tip: Use --provider to filter by a specific provider")
            click.echo("   Example: promptv cost models --provider openai")
        
    except ValueError as e:
        format_error(str(e))
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('prompt_name')
@click.argument('ref_a', metavar='REF-A')
@click.argument('ref_b', metavar='REF-B')
@click.option('--format', '-f', 'diff_format', type=click.Choice(['side-by-side', 'unified', 'json']), default='side-by-side', help='Output format (default: side-by-side)')
def diff(prompt_name, ref_a, ref_b, diff_format):
    """
    Show differences between two versions of a prompt.
    
    REF-A and REF-B can be:
    - Version numbers (e.g., 1, 2, 3)
    - Tags (e.g., prod, staging, dev)
    - 'latest' for the latest version
    
    Examples:
        promptv diff my-prompt 1 2
        promptv diff my-prompt prod staging
        promptv diff my-prompt 1 latest
        promptv diff my-prompt prod staging --format unified
        promptv diff my-prompt 1 2 --format json
    """
    try:
        manager = PromptManager()
        tag_manager = TagManager(manager.prompts_dir)
        
        # Get metadata to find max_version
        prompt_dir = manager.prompts_dir / prompt_name
        metadata = manager._load_metadata(prompt_name)
        max_version = metadata.current_version
        
        # Resolve references to version numbers
        version_a = tag_manager.resolve_version(prompt_name, ref_a, max_version)
        version_b = tag_manager.resolve_version(prompt_name, ref_b, max_version)
        
        # Get content for both versions
        content_a, _ = manager.get_prompt_with_metadata(prompt_name, version_a)
        content_b, _ = manager.get_prompt_with_metadata(prompt_name, version_b)
        
        # Create labels for display
        label_a = f"{ref_a} (v{version_a})" if ref_a != str(version_a) else f"v{version_a}"
        label_b = f"{ref_b} (v{version_b})" if ref_b != str(version_b) else f"v{version_b}"
        
        # Generate diff
        engine = DiffEngine()
        diff_output = engine.diff_versions(
            content_a,
            content_b,
            label_a=label_a,
            label_b=label_b,
            format=DiffFormat(diff_format),
        )
        
        # Print diff output
        click.echo(diff_output)
        
    except PromptNotFoundError as e:
        format_error(str(e), "Use 'promptv list' to see available prompts")
        sys.exit(1)
    except VersionNotFoundError as e:
        format_error(str(e), "Use 'promptv history <prompt>' to see available versions")
        sys.exit(1)
    except TagNotFoundError as e:
        format_error(str(e), "Use 'promptv tag list <prompt>' to see available tags")
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def initialize_promptv_directory(silent: bool = False) -> dict:
    """
    Initialize the ~/.promptv directory structure.
    
    Creates required directories and files:
    - ~/.promptv/
    - ~/.promptv/.config/ (with config.yaml and pricing.yaml)
    - ~/.promptv/.secrets/ (with secrets.json)
    - ~/.promptv/prompts/
    
    Args:
        silent: If True, suppress output messages
    
    Returns:
        Dictionary with creation status for each component
    """
    base_dir = Path.home() / ".promptv"
    config_dir = base_dir / ".config"
    secrets_dir = base_dir / ".secrets"
    prompts_dir = base_dir / "prompts"
    
    results = {
        'base_dir_created': False,
        'config_dir_created': False,
        'secrets_dir_created': False,
        'prompts_dir_created': False,
        'config_yaml_created': False,
        'pricing_yaml_copied': False,
        'secrets_json_created': False
    }
    
    try:
        # Create base directory
        if not base_dir.exists():
            base_dir.mkdir(parents=True, exist_ok=True)
            results['base_dir_created'] = True
        
        # Create .config directory
        if not config_dir.exists():
            config_dir.mkdir(parents=True, exist_ok=True)
            results['config_dir_created'] = True
        
        # Create .secrets directory with restrictive permissions
        if not secrets_dir.exists():
            secrets_dir.mkdir(parents=True, exist_ok=True)
            secrets_dir.chmod(0o700)
            results['secrets_dir_created'] = True
        
        # Create prompts directory
        if not prompts_dir.exists():
            prompts_dir.mkdir(parents=True, exist_ok=True)
            results['prompts_dir_created'] = True
        
        # Initialize config.yaml using ConfigManager
        config_file = config_dir / "config.yaml"
        if not config_file.exists():
            config_mgr = ConfigManager(config_path=config_file)
            config_mgr.get_config()  # This creates the file if it doesn't exist
            results['config_yaml_created'] = True
        
        # Copy pricing.yaml from package resources
        pricing_file = config_dir / "pricing.yaml"
        if not pricing_file.exists():
            # Get package resource path (absolute path)
            import promptv
            package_dir = Path(promptv.__file__).parent
            package_pricing = package_dir / "resources" / "pricing.yaml"
            
            if package_pricing.exists():
                shutil.copy2(package_pricing, pricing_file)
                results['pricing_yaml_copied'] = True
            else:
                if not silent:
                    click.echo(f"Warning: Could not find pricing.yaml in package resources at {package_pricing}", err=True)
        
        # Initialize secrets.json using SecretsManager
        secrets_file = secrets_dir / "secrets.json"
        if not secrets_file.exists():
            secrets_mgr = SecretsManager(secrets_dir=secrets_dir)
            # SecretsManager automatically creates secrets.json on init
            if secrets_file.exists():
                secrets_file.chmod(0o600)
                results['secrets_json_created'] = True
        
        return results
    
    except Exception as e:
        if not silent:
            click.echo(f"Error during initialization: {e}", err=True)
        raise


@cli.command()
@click.option('--force', is_flag=True, help='Delete existing ~/.promptv and reinitialize (WARNING: destructive!)')
def init(force):
    """
    Initialize promptv directory structure and configuration.
    
    Creates the following structure:
    
    ~/.promptv/
    ├── .config/
    │   ├── config.yaml      # User configuration
    │   └── pricing.yaml     # LLM pricing data (customizable)
    ├── .secrets/
    │   └── secrets.json     # API keys and secrets
    └── prompts/             # Saved prompts
    
    The initialization is idempotent - safe to run multiple times.
    Use --force to delete and recreate (WARNING: deletes all data).
    
    Examples:
        promptv init
        promptv init --force
    """
    try:
        base_dir = Path.home() / ".promptv"
        
        # Handle force mode
        if force:
            if base_dir.exists():
                click.echo("⚠️  Force mode: This will DELETE all data in ~/.promptv/")
                click.echo("   Including all prompts, secrets, and configuration!")
                click.echo()
                if not click.confirm("Are you absolutely sure?"):
                    click.echo("Cancelled")
                    return
                
                # Delete existing directory
                shutil.rmtree(base_dir)
                click.echo("✓ Removed existing ~/.promptv directory")
                click.echo()
        
        # Initialize directory structure
        click.echo("Initializing promptv...")
        results = initialize_promptv_directory(silent=False)
        
        # Display results
        click.echo()
        click.echo("Directory Structure:")
        
        if results['base_dir_created']:
            click.echo("  ✓ Created ~/.promptv/")
        else:
            click.echo("  - ~/.promptv/ (already exists)")
        
        if results['config_dir_created']:
            click.echo("    ✓ Created .config/")
        else:
            click.echo("    - .config/ (already exists)")
        
        if results['config_yaml_created']:
            click.echo("      ✓ Created config.yaml")
        else:
            click.echo("      - config.yaml (already exists)")
        
        if results['pricing_yaml_copied']:
            click.echo("      ✓ Copied pricing.yaml")
            pricing_date = get_pricing_data_date()
            click.echo(f"        Last updated: {pricing_date}")
        else:
            click.echo("      - pricing.yaml (already exists)")
        
        if results['secrets_dir_created']:
            click.echo("    ✓ Created .secrets/ (permissions: 0700)")
        else:
            click.echo("    - .secrets/ (already exists)")
        
        if results['secrets_json_created']:
            click.echo("      ✓ Created secrets.json (permissions: 0600)")
        else:
            click.echo("      - secrets.json (already exists)")
        
        if results['prompts_dir_created']:
            click.echo("    ✓ Created prompts/")
        else:
            click.echo("    - prompts/ (already exists)")
        
        click.echo()
        click.echo("✅ Initialization complete!")
        click.echo()
        click.echo("Next steps:")
        click.echo("  1. Set up API keys:")
        click.echo("     promptv secrets set openai --provider")
        click.echo()
        click.echo("  2. Create your first prompt:")
        click.echo("     promptv set my-prompt -c 'You are a helpful assistant'")
        click.echo()
        click.echo("  3. Customize pricing (optional):")
        click.echo("     Edit ~/.promptv/.config/pricing.yaml")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    cli()