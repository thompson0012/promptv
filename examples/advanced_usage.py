"""
Advanced PromptV SDK Usage Example

This example demonstrates advanced SDK features including:
- Variable rendering
- Caching
- Context managers
- Tag-based retrieval
"""

from promptv.sdk import PromptClient
from promptv.manager import PromptManager
from promptv.tag_manager import TagManager

def setup_demo_prompts():
    """Set up demo prompts for this example."""
    print("Setting up demo prompts...\n")
    
    manager = PromptManager()
    
    # Create an onboarding email prompt with variables
    onboarding_v1 = """Hello {{user_name}},

Welcome to {{product}}! We're excited to have you on board.

Getting started is easy:
1. Log in to your account
2. Complete your profile
3. Explore our features

Best regards,
The {{product}} Team"""
    
    result = manager.set_prompt("onboarding-email", onboarding_v1)
    print(f"✓ Created 'onboarding-email' v{result['version']}")
    
    # Create version 2 with more details
    onboarding_v2 = """Hi {{user_name}},

Welcome to {{product}}! We're thrilled to have you join our community.

Here's what you can do next:
1. Log in to your account at {{app_url}}
2. Complete your profile
3. Explore our features
4. Join our community forum

Need help? Contact us at {{support_email}}

Best regards,
The {{product}} Team"""
    
    result = manager.set_prompt("onboarding-email", onboarding_v2)
    print(f"✓ Created 'onboarding-email' v{result['version']}")
    
    # Create tags
    tag_manager = TagManager(manager.prompts_dir)
    tag_manager.create_tag("onboarding-email", "prod", 1, allow_update=True)
    tag_manager.create_tag("onboarding-email", "staging", 2, allow_update=True)
    print("✓ Created tags: prod → v1, staging → v2\n")
    
    return manager

def example_1_basic_retrieval():
    """Example 1: Basic prompt retrieval with variables."""
    print("=== Example 1: Basic Retrieval with Variables ===\n")
    
    client = PromptClient()
    
    # Get prompt with variables
    content = client.get_prompt(
        "onboarding-email",
        label="prod",
        variables={
            "user_name": "Alice",
            "product": "PromptV"
        }
    )
    
    print("Retrieved prompt with variables:")
    print(content)
    print()

def example_2_caching():
    """Example 2: Caching behavior."""
    print("=== Example 2: Caching Behavior ===\n")
    
    # Create client with custom cache TTL
    client = PromptClient(cache_ttl=600)  # 10 minutes
    
    print("First retrieval (will cache):")
    content1 = client.get_prompt("onboarding-email", label="prod")
    stats1 = client.get_cache_stats()
    print(f"Cache stats: {stats1['cached_count']} cached, {stats1['active_count']} active\n")
    
    print("Second retrieval (from cache):")
    content2 = client.get_prompt("onboarding-email", label="prod")
    stats2 = client.get_cache_stats()
    print(f"Cache stats: {stats2['cached_count']} cached, {stats2['active_count']} active")
    print(f"Same content: {content1 == content2}\n")
    
    print("Different label (new cache entry):")
    content3 = client.get_prompt("onboarding-email", label="staging")
    stats3 = client.get_cache_stats()
    print(f"Cache stats: {stats3['cached_count']} cached, {stats3['active_count']} active\n")
    
    print("Clearing cache:")
    client.clear_cache()
    stats4 = client.get_cache_stats()
    print(f"Cache stats: {stats4['cached_count']} cached, {stats4['active_count']} active\n")

def example_3_context_manager():
    """Example 3: Using context manager."""
    print("=== Example 3: Context Manager ===\n")
    
    print("Using PromptClient with context manager:")
    with PromptClient() as client:
        # Cache some prompts
        client.get_prompt("onboarding-email", label="prod")
        client.get_prompt("onboarding-email", label="staging")
        
        stats = client.get_cache_stats()
        print(f"Inside context: {stats['cached_count']} cached prompts")
        
        # Render with variables
        rendered = client.get_prompt(
            "onboarding-email",
            label="staging",
            variables={
                "user_name": "Bob",
                "product": "PromptV",
                "app_url": "https://app.example.com",
                "support_email": "support@example.com"
            }
        )
        print("\nRendered prompt:")
        print(rendered)
    
    print("\nAfter context exit, cache is automatically cleared\n")

def example_4_version_comparison():
    """Example 4: Comparing different versions."""
    print("=== Example 4: Version Comparison ===\n")
    
    client = PromptClient()
    
    # Get both versions with same variables
    variables = {
        "user_name": "Charlie",
        "product": "PromptV",
        "app_url": "https://app.example.com",
        "support_email": "support@example.com"
    }
    
    print("Production version (v1):")
    prod_content = client.get_prompt(
        "onboarding-email",
        label="prod",
        variables=variables
    )
    print(prod_content)
    print("\n" + "="*50 + "\n")
    
    print("Staging version (v2):")
    staging_content = client.get_prompt(
        "onboarding-email",
        label="staging",
        variables=variables
    )
    print(staging_content)
    print()

def example_5_metadata_inspection():
    """Example 5: Inspecting metadata."""
    print("=== Example 5: Metadata Inspection ===\n")
    
    client = PromptClient()
    
    # Get all versions
    versions = client.get_versions("onboarding-email")
    print(f"Total versions: {len(versions)}")
    for v in versions:
        print(f"\nVersion {v.version}:")
        print(f"  Timestamp: {v.timestamp}")
        print(f"  Variables: {', '.join(v.variables) if v.variables else 'None'}")
        if v.message:
            print(f"  Message: {v.message}")
    
    # Get tags
    print("\nTags:")
    tags = client.get_tags("onboarding-email")
    for tag_name, version in tags.items():
        print(f"  {tag_name} → v{version}")
    print()

def example_6_error_handling():
    """Example 6: Error handling."""
    print("=== Example 6: Error Handling ===\n")
    
    client = PromptClient()
    
    # Try to get non-existent prompt
    try:
        client.get_prompt("non-existent-prompt")
    except Exception as e:
        print(f"Expected error for non-existent prompt: {e}")
    
    # Try to get non-existent label
    try:
        client.get_prompt("onboarding-email", label="non-existent")
    except Exception as e:
        print(f"Expected error for non-existent label: {e}")
    
    # Try to specify both label and version
    try:
        client.get_prompt("onboarding-email", label="prod", version=1)
    except ValueError as e:
        print(f"Expected error for both label and version: {e}")
    
    print()

def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("     Advanced PromptV SDK Usage Examples")
    print("="*60 + "\n")
    
    # Set up demo prompts
    setup_demo_prompts()
    
    # Run examples
    example_1_basic_retrieval()
    example_2_caching()
    example_3_context_manager()
    example_4_version_comparison()
    example_5_metadata_inspection()
    example_6_error_handling()
    
    print("="*60)
    print("     All Examples Complete!")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
