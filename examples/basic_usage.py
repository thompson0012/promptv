"""
Basic PromptV SDK Usage Example

This example demonstrates the basic usage of the PromptV SDK
for programmatic prompt access.
"""

from promptv.sdk import PromptClient

def main():
    # Initialize the client
    client = PromptClient()
    
    print("=== Basic PromptV SDK Usage ===\n")
    
    # Example 1: List all available prompts
    print("1. Listing all prompts:")
    prompts = client.list_prompts()
    if prompts:
        for prompt in prompts:
            print(f"   - {prompt}")
    else:
        print("   No prompts found. Create one first using:")
        print("   promptv set my-prompt -c 'Your prompt content here'")
    print()
    
    # Example 2: Get a prompt (latest version)
    if prompts:
        prompt_name = prompts[0]
        print(f"2. Getting latest version of '{prompt_name}':")
        try:
            content = client.get_prompt(prompt_name)
            print(f"   Content: {content[:100]}..." if len(content) > 100 else f"   Content: {content}")
        except Exception as e:
            print(f"   Error: {e}")
        print()
        
        # Example 3: Get all versions
        print(f"3. Listing versions of '{prompt_name}':")
        try:
            versions = client.get_versions(prompt_name)
            for v in versions:
                print(f"   - v{v.version}: {v.message or 'No message'}")
        except Exception as e:
            print(f"   Error: {e}")
        print()
        
        # Example 4: Get all tags
        print(f"4. Listing tags for '{prompt_name}':")
        try:
            tags = client.get_tags(prompt_name)
            if tags:
                for tag_name, version in tags.items():
                    print(f"   - {tag_name} → v{version}")
            else:
                print("   No tags found")
        except Exception as e:
            print(f"   Error: {e}")
        print()
        
        # Example 5: Get prompt with metadata
        print(f"5. Getting prompt with metadata:")
        try:
            content, metadata = client.get_prompt_with_metadata(prompt_name)
            print(f"   Version: {metadata.version}")
            print(f"   Timestamp: {metadata.timestamp}")
            if metadata.author:
                print(f"   Author: {metadata.author}")
            if metadata.message:
                print(f"   Message: {metadata.message}")
        except Exception as e:
            print(f"   Error: {e}")
        print()
    
    # Example 6: Cache statistics
    print("6. Cache statistics:")
    stats = client.get_cache_stats()
    print(f"   Cached prompts: {stats['cached_count']}")
    print(f"   Active (not expired): {stats['active_count']}")
    print(f"   TTL: {stats['ttl_seconds']}s")
    print()
    
    print("=== Example Complete ===")

if __name__ == "__main__":
    main()
