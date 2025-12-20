"""
Self-verification test for AI image generation

This script tests the Stable Diffusion API directly and generates a sample image
so you can verify it's working properly.
"""
import requests
import io
from PIL import Image
from datetime import datetime
import time

# Hugging Face Stable Diffusion endpoint (FREE, no API key needed)
HF_API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-2-1"

def test_ai_image_generation():
    """Test Stable Diffusion API and save a sample image"""
    print("=" * 60)
    print("AI IMAGE GENERATION TEST")
    print("=" * 60)

    # Test prompt
    prompt = "Professional news background with modern design, technology theme, abstract visualization, high quality, detailed"

    print(f"\n📝 Prompt: {prompt}")
    print(f"\n🔄 Calling Stable Diffusion API...")

    headers = {"Content-Type": "application/json"}
    payload = {"inputs": prompt}

    retries = 3
    for attempt in range(retries):
        try:
            print(f"\nAttempt {attempt + 1}/{retries}...", flush=True)

            response = requests.post(HF_API_URL, headers=headers, json=payload, timeout=60)

            print(f"Status Code: {response.status_code}", flush=True)
            print(f"Response Headers: {dict(response.headers)}", flush=True)

            if response.status_code == 200:
                # Success!
                print("\n✅ SUCCESS! Image generated", flush=True)

                # Save image
                image = Image.open(io.BytesIO(response.content))
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = f"test_ai_image_{timestamp}.png"
                image.save(output_path)

                print(f"\n🖼️  Image saved: {output_path}", flush=True)
                print(f"📐 Size: {image.size}", flush=True)
                print(f"🎨 Mode: {image.mode}", flush=True)

                return True, output_path

            elif response.status_code == 503:
                # Model loading
                try:
                    error_data = response.json()
                    wait_time = error_data.get('estimated_time', 20)
                    print(f"\n⏳ Model loading... estimated wait: {wait_time}s", flush=True)
                    print(f"Response: {error_data}", flush=True)
                except Exception as e:
                    wait_time = 20
                    print(f"\n⏳ Model loading... waiting {wait_time}s", flush=True)
                    print(f"Raw response: {response.text[:500]}", flush=True)

                if attempt < retries - 1:
                    print(f"Sleeping {wait_time}s...", flush=True)
                    time.sleep(wait_time)
                    continue
                else:
                    print("\n❌ Model still loading after all retries", flush=True)
                    return False, None

            else:
                # Error
                print(f"\n❌ ERROR {response.status_code}", flush=True)
                print(f"Response: {response.text[:1000]}", flush=True)
                return False, None

        except Exception as e:
            print(f"\n❌ Exception: {e}", flush=True)
            import traceback
            print(traceback.format_exc(), flush=True)

            if attempt < retries - 1:
                print("Retrying in 5s...", flush=True)
                time.sleep(5)
            else:
                return False, None

    return False, None

if __name__ == "__main__":
    success, image_path = test_ai_image_generation()

    print("\n" + "=" * 60)
    if success:
        print("✅ AI IMAGE GENERATION WORKS!")
        print(f"✅ Check the generated image: {image_path}")
        print("\nIf you see a proper AI-generated image (not just colored background),")
        print("then AI generation is working and the issue is in the integration.")
        print("\nIf you see a colored background, then the API is not working properly.")
    else:
        print("❌ AI IMAGE GENERATION FAILED!")
        print("\nPossible reasons:")
        print("1. Hugging Face API is down or rate limited")
        print("2. Network connectivity issue")
        print("3. Model is taking too long to load")
        print("\nTry running this script again in a few minutes.")
    print("=" * 60)
