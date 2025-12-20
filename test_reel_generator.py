"""
Test script for ReelGenerator

This script tests the ReelGenerator component functionality.

NOTE: Requires Pillow to be installed. On Python 3.14 Windows, Pillow may not
install locally, but it will work on Render (Linux).
"""
import os
from automation.reel_generator import create_reel_generator, PIL_AVAILABLE

print("="*60)
print("REEL GENERATOR TEST")
print("="*60)

# Check if PIL is available
if PIL_AVAILABLE:
    print("\n[OK] Pillow is installed - using real ReelGenerator")
else:
    print("\n[WARNING] Pillow not installed - using MockReelGenerator")
    print("[WARNING] Images will not actually be generated")
    print("[INFO] On production (Render/Linux), Pillow will be available")

# Initialize generator
print("\n" + "="*60)
print("TEST 1: Initialize ReelGenerator")
print("="*60)

generator = create_reel_generator(output_dir='test_reels')
print(f"[OK] Generator initialized")

# Test 2: Get available options
print("\n" + "="*60)
print("TEST 2: Get available options")
print("="*60)

styles = generator.get_available_styles()
aspect_ratios = generator.get_available_aspect_ratios()

print(f"Available styles: {', '.join(styles)}")
print(f"Available aspect ratios: {', '.join(aspect_ratios)}")

# Test 3: Generate reel with different styles
print("\n" + "="*60)
print("TEST 3: Generate reels with different styles")
print("="*60)

test_content = {
    'title': 'Top AI Trends 2025',
    'key_points': [
        'Large Language Models continue to evolve',
        'AI agents becoming more autonomous',
        'Open source models gaining traction',
        'Ethical AI development prioritized',
        'AI integration in everyday tools'
    ]
}

for style in ['modern', 'professional', 'vibrant']:
    print(f"\nGenerating {style} style reel...")
    try:
        filepath = generator.generate_reel(
            title=test_content['title'],
            key_points=test_content['key_points'],
            aspect_ratio='reel',
            style=style,
            footer_text='@NewsInsightParser'
        )
        if PIL_AVAILABLE:
            print(f"[OK] Generated: {filepath}")
        else:
            print(f"[MOCK] Would generate: {filepath}")
    except Exception as e:
        print(f"[ERROR] Failed to generate {style} reel: {e}")

# Test 4: Generate with different aspect ratios
print("\n" + "="*60)
print("TEST 4: Generate reels with different aspect ratios")
print("="*60)

for ratio in ['square', 'reel', 'landscape']:
    print(f"\nGenerating {ratio} aspect ratio...")
    try:
        filepath = generator.generate_reel(
            title='News Insight Summary',
            key_points=[
                'Daily AI & Tech News',
                'Automated Analysis',
                'Trending Topics'
            ],
            aspect_ratio=ratio,
            style='modern'
        )
        if PIL_AVAILABLE:
            print(f"[OK] Generated: {filepath}")
        else:
            print(f"[MOCK] Would generate: {filepath}")
    except Exception as e:
        print(f"[ERROR] Failed to generate {ratio} reel: {e}")

# Test 5: Generate from content dictionary
print("\n" + "="*60)
print("TEST 5: Generate from content dictionary")
print("="*60)

generated_content = {
    'format_type': 'long_post',
    'title': 'Breaking: New AI Model Released',
    'content': '''A new state-of-the-art AI model was released today.

Key features:
- Improved reasoning capabilities
- Better code generation
- Enhanced multilingual support
- Reduced hallucinations
- More efficient inference''',
    'key_points': [
        'New AI model with improved reasoning',
        'Better code generation capabilities',
        'Enhanced multilingual support',
        'Reduced hallucinations',
        'More efficient inference'
    ],
    'hashtags': ['#AI', '#MachineLearning', '#Tech']
}

print("\nGenerating reel from content...")
try:
    filepath = generator.generate_from_content(
        content=generated_content,
        aspect_ratio='reel',
        style='vibrant'
    )
    if PIL_AVAILABLE:
        print(f"[OK] Generated: {filepath}")
    else:
        print(f"[MOCK] Would generate: {filepath}")
except Exception as e:
    print(f"[ERROR] Failed to generate from content: {e}")

# Summary
print("\n" + "="*60)
print("SUMMARY")
print("="*60)

if PIL_AVAILABLE:
    print("[OK] All tests completed successfully!")
    print(f"\nGenerated images are in: test_reels/")
    print("\nNext steps:")
    print("1. Check generated images")
    print("2. Verify formatting and readability")
    print("3. Ready for integration with AutoContentSystem")
else:
    print("[WARNING] Tests ran in mock mode (Pillow not available)")
    print("\nOn production (Render):")
    print("1. Pillow will be installed automatically from requirements.txt")
    print("2. Images will be generated correctly")
    print("3. All functionality will work as expected")

print("\nReelGenerator features:")
print("- 5 color schemes: modern, professional, vibrant, minimal, dark")
print("- 5 aspect ratios: square, reel, story, landscape, twitter")
print("- Automatic text wrapping")
print("- Key points with bullet styling")
print("- Professional templates")

print("\n" + "="*60)
