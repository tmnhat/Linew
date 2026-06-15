#!/usr/bin/env python3
"""
Test AI Gateway connection and configuration.
"""
import asyncio
import sys
sys.path.insert(0, '/path/to/linew')

from app.config import get_settings
from app.core.ai_gateway import AIGateway


async def test_ai_gateway():
    settings = get_settings()
    
    print("=" * 60)
    print("AI Gateway Configuration")
    print("=" * 60)
    print(f"Gateway URL: {settings.ai_gateway_url}")
    print(f"API Key: {settings.ai_gateway_key[:20]}...")
    print(f"Writer Model: {settings.ai_writer_model}")
    print(f"Light Model: {settings.ai_light_model}")
    print()
    
    # Test simple call
    print("=" * 60)
    print("Testing AI Gateway...")
    print("=" * 60)
    
    gateway = AIGateway()
    
    test_prompts = [
        ("Simple test", "Categorize this: 'Stock market rises on AI news'", "categorize"),
        ("Write test", "Write a short headline for an article about AI", "write"),
    ]
    
    for name, prompt, task_type in test_prompts:
        print(f"\nTest: {name}")
        print(f"Task type: {task_type}")
        print(f"Prompt: {prompt[:50]}...")
        
        try:
            result = await gateway.call_ai(
                prompt=prompt,
                task_type=task_type,
                max_tokens=100,
                temperature=0.7,
            )
            print(f"✓ Success!")
            print(f"  Response: {result.get('text', result)[:100]}...")
        except Exception as e:
            print(f"✗ Failed: {e}")
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_ai_gateway())
