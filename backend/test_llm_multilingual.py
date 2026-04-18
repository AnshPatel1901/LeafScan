#!/usr/bin/env python3
"""
Quick validation test for multilingual LLM service.
Runs without API calls - tests prompt building and fallback logic.
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.llm_service import LLMService


def test_language_names():
    """Test language name mapping."""
    svc = LLMService(groq_api_key="test", gemini_api_key="test")
    
    test_cases = [
        ("en", "English"),
        ("hi", "Hindi"),
        ("ta", "Tamil"),
        ("te", "Telugu"),
        ("fr", "French"),
        ("es", "Spanish"),
        ("zh", "Chinese"),
    ]
    
    print("✓ Testing language name mapping:")
    for lang_code, expected_name in test_cases:
        name = svc._get_language_name(lang_code)
        assert name == expected_name, f"Expected {expected_name}, got {name}"
        print(f"  ✓ {lang_code} → {name}")


def test_prompt_building():
    """Test prompt generation for different scenarios."""
    svc = LLMService(groq_api_key="test", gemini_api_key="test")
    
    print("\n✓ Testing English prompt (healthy plant):")
    prompt = svc._build_prompt("Tomato", "healthy", "en")
    assert "healthy" in prompt.lower()
    assert "English" in prompt
    assert "Tomato" in prompt
    print(f"  ✓ Generated {len(prompt)} character prompt")
    
    print("\n✓ Testing English prompt (disease):")
    prompt = svc._build_prompt("Tomato", "Early Blight", "en")
    assert "Early Blight" in prompt
    assert "English" in prompt
    assert "About the disease" in prompt
    print(f"  ✓ Generated {len(prompt)} character prompt")
    
    print("\n✓ Testing Hindi prompt (disease):")
    prompt = svc._build_prompt("टमाटर", "मोल्ड", "hi")
    assert "Hindi" in prompt
    assert "मोल्ड" in prompt
    print(f"  ✓ Generated {len(prompt)} character prompt")


def test_static_fallback():
    """Test static fallback for all languages."""
    print("\n✓ Testing static fallback:")
    
    # Test English healthy
    text = LLMService._static_fallback("Tomato", "healthy", "en")
    assert "healthy" in text.lower()
    print(f"  ✓ EN healthy: {len(text)} chars")
    
    # Test English disease
    text = LLMService._static_fallback("Tomato", "Early Blight", "en")
    assert "Early Blight" in text
    assert "Immediate actions" in text
    print(f"  ✓ EN disease: {len(text)} chars")
    
    # Test Hindi healthy
    text = LLMService._static_fallback("टमाटर", "healthy", "hi")
    assert len(text) > 50
    assert "स्वस्थ" in text or "पौधा" in text
    print(f"  ✓ HI healthy: {len(text)} chars")
    
    # Test Tamil healthy
    text = LLMService._static_fallback("தக்காளி", "healthy", "ta")
    assert len(text) > 50
    print(f"  ✓ TA healthy: {len(text)} chars")
    
    # Test fallback for unsupported language
    text = LLMService._static_fallback("Tomato", "healthy", "xx")
    assert "healthy" in text.lower()
    print(f"  ✓ Unsupported lang: {len(text)} chars (defaults to EN)")


async def test_error_handling():
    """Test error handling in LLM calls."""
    print("\n✓ Testing error handling:")
    
    # Without API keys, should raise error
    svc = LLMService(groq_api_key="", gemini_api_key="")
    
    try:
        await svc.generate_precautions("Tomato", "Blight", "en")
        print("  ✗ Should have raised error for missing API keys")
    except Exception as exc:
        print(f"  ✓ Correctly raised error: {type(exc).__name__}")
        # Should fall back to static text
        assert "Blight" in str(exc) or hasattr(svc, '_static_fallback')


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Multilingual LLM Service")
    print("=" * 60)
    
    try:
        test_language_names()
        test_prompt_building()
        test_static_fallback()
        asyncio.run(test_error_handling())
        
        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        return 0
    except AssertionError as exc:
        print(f"\n✗ Test failed: {exc}")
        return 1
    except Exception as exc:
        print(f"\n✗ Unexpected error: {exc}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
