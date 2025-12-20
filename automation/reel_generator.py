"""
Reel Generator for Automation

Generates visual content (images) for social media reels using PIL/Pillow.
Creates professional-looking images with text overlay for Instagram Reels,
TikTok, YouTube Shorts, etc.
"""
from typing import Optional, Dict, List, Tuple
from datetime import datetime
import os
import textwrap
import io
import requests
import time

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("[WARNING] Pillow not installed. ReelGenerator will not work.")
    print("[WARNING] Install with: pip install Pillow")


class ReelGenerator:
    """
    Generates visual content for social media reels

    Features:
    - Multiple aspect ratios (1:1, 9:16, 16:9)
    - Text overlay with automatic wrapping
    - Multiple color schemes/styles
    - Configurable fonts and sizes
    - Key points highlighting
    - Professional templates
    """

    # Aspect ratios (width, height)
    ASPECT_RATIOS = {
        'square': (1080, 1080),      # Instagram post, Facebook
        'reel': (1080, 1920),         # Instagram Reels, TikTok, YouTube Shorts
        'story': (1080, 1920),        # Instagram/Facebook Stories
        'landscape': (1920, 1080),    # YouTube, LinkedIn
        'twitter': (1200, 675),       # Twitter/X
    }

    # Color schemes
    COLOR_SCHEMES = {
        'modern': {
            'background': (15, 23, 42),       # Dark blue-gray
            'title': (255, 255, 255),         # White
            'text': (226, 232, 240),          # Light gray
            'accent': (99, 102, 241),         # Indigo
            'highlight': (34, 211, 238)       # Cyan
        },
        'professional': {
            'background': (255, 255, 255),    # White
            'title': (15, 23, 42),            # Dark
            'text': (51, 65, 85),             # Gray
            'accent': (59, 130, 246),         # Blue
            'highlight': (16, 185, 129)       # Green
        },
        'vibrant': {
            'background': (139, 92, 246),     # Purple
            'title': (255, 255, 255),         # White
            'text': (243, 232, 255),          # Light purple
            'accent': (253, 224, 71),         # Yellow
            'highlight': (251, 146, 60)       # Orange
        },
        'minimal': {
            'background': (248, 250, 252),    # Very light gray
            'title': (15, 23, 42),            # Dark
            'text': (71, 85, 105),            # Medium gray
            'accent': (100, 116, 139),        # Slate
            'highlight': (148, 163, 184)      # Light slate
        },
        'dark': {
            'background': (0, 0, 0),          # Black
            'title': (255, 255, 255),         # White
            'text': (156, 163, 175),          # Gray
            'accent': (239, 68, 68),          # Red
            'highlight': (34, 197, 94)        # Green
        }
    }

    def __init__(self, output_dir: str = 'generated_reels', use_ai: bool = True):
        """
        Initialize ReelGenerator

        Args:
            output_dir: Directory to save generated images
            use_ai: Use AI image generation (Stable Diffusion) instead of basic text overlay
        """
        if not PIL_AVAILABLE:
            raise ImportError("Pillow is required for ReelGenerator. Install with: pip install Pillow")

        self.output_dir = output_dir
        self.use_ai = use_ai
        os.makedirs(output_dir, exist_ok=True)

        # Hugging Face Inference API endpoint for Stable Diffusion
        self.hf_api_url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-2-1"
        # Free API - no key needed, but has rate limits

        print(f"[REEL GENERATOR] Initialized with output dir: {output_dir}, AI: {use_ai}", flush=True)

    def _generate_ai_image(self, prompt: str, retries: int = 3) -> Optional[Image.Image]:
        """
        Generate image using Stable Diffusion via Hugging Face Inference API

        Args:
            prompt: Text prompt for image generation
            retries: Number of retries if API is loading

        Returns:
            PIL Image object or None if failed
        """
        print(f"[AI IMAGE] Generating with prompt: {prompt[:100]}...", flush=True)

        headers = {"Content-Type": "application/json"}
        payload = {"inputs": prompt}

        for attempt in range(retries):
            try:
                response = requests.post(self.hf_api_url, headers=headers, json=payload, timeout=60)

                if response.status_code == 200:
                    # Success - return image
                    image = Image.open(io.BytesIO(response.content))
                    print(f"[AI IMAGE] Generated successfully: {image.size}", flush=True)
                    return image

                elif response.status_code == 503:
                    # Model is loading - wait and retry
                    try:
                        error_data = response.json()
                        wait_time = error_data.get('estimated_time', 20)
                    except:
                        wait_time = 20

                    print(f"[AI IMAGE] Model loading... waiting {wait_time}s (attempt {attempt+1}/{retries})", flush=True)
                    time.sleep(wait_time)
                    continue

                else:
                    print(f"[AI IMAGE] Error {response.status_code}: {response.text[:200]}", flush=True)
                    return None

            except Exception as e:
                print(f"[AI IMAGE] Exception: {e}", flush=True)
                if attempt < retries - 1:
                    time.sleep(5)
                    continue
                return None

        return None

    def _create_prompt_from_content(self, title: str, keywords: List[str]) -> str:
        """
        Create Stable Diffusion prompt from content

        Args:
            title: Content title
            keywords: Topic keywords

        Returns:
            Optimized prompt for Stable Diffusion
        """
        # Create engaging prompt for tech/startup content
        topic = ', '.join(keywords[:3]) if keywords else 'technology'

        prompts = [
            f"Professional modern tech illustration about {topic}, minimalist design, vibrant colors, high quality, digital art",
            f"Futuristic {topic} concept art, sleek technology, innovation, professional lighting, 4k quality",
            f"Abstract technology visualization for {topic}, modern design, gradient background, professional",
            f"Clean minimal tech graphic about {topic}, professional illustration, vibrant gradient, modern style",
        ]

        # Rotate through prompts based on current time
        import hashlib
        index = int(hashlib.md5(title.encode()).hexdigest(), 16) % len(prompts)

        return prompts[index]

    def generate_reel(
        self,
        title: str,
        key_points: List[str],
        keywords: Optional[List[str]] = None,
        aspect_ratio: str = 'reel',
        style: str = 'modern',
        footer_text: Optional[str] = None
    ) -> str:
        """
        Generate a reel image

        Args:
            title: Main title text
            key_points: List of key points to display
            keywords: Short keywords for AI prompt (e.g., ['AI', 'technology', 'startup'])
            aspect_ratio: One of: 'square', 'reel', 'story', 'landscape', 'twitter'
            style: Color scheme: 'modern', 'professional', 'vibrant', 'minimal', 'dark'
            footer_text: Optional footer text (e.g., channel name)

        Returns:
            Path to generated image file
        """
        print(f"[REEL GENERATOR] Generating {aspect_ratio} reel with {style} style, AI: {self.use_ai}", flush=True)

        # Get dimensions and colors
        width, height = self.ASPECT_RATIOS.get(aspect_ratio, self.ASPECT_RATIOS['reel'])
        colors = self.COLOR_SCHEMES.get(style, self.COLOR_SCHEMES['modern'])

        # Use AI image generation if enabled
        if self.use_ai:
            print(f"[REEL] ✅ AI generation ENABLED - attempting to generate AI image", flush=True)
            # Use keywords (hashtags) instead of key_points for better AI prompts
            prompt_keywords = keywords if keywords else []
            print(f"[REEL] 🏷️  Keywords for AI: {prompt_keywords}", flush=True)
            prompt = self._create_prompt_from_content(title, prompt_keywords)
            print(f"[REEL] 📝 Prompt created: {prompt}", flush=True)

            ai_image = self._generate_ai_image(prompt)

            if ai_image:
                # Resize AI image to target dimensions
                img = ai_image.resize((width, height), Image.Resampling.LANCZOS)

                # Add semi-transparent overlay for text readability
                overlay = Image.new('RGBA', (width, height), (0, 0, 0, 120))
                img = img.convert('RGBA')
                img = Image.alpha_composite(img, overlay)
                img = img.convert('RGB')

                print(f"[REEL] ✅ Using AI-generated background (size: {ai_image.size})", flush=True)
            else:
                # Fallback to basic colored background if AI fails
                print(f"[REEL] ❌ AI generation FAILED - using colored fallback background", flush=True)
                print(f"[REEL] ⚠️  Check logs above for API error details", flush=True)
                img = Image.new('RGB', (width, height), colors['background'])
        else:
            # Create basic colored background
            print(f"[REEL] ⚠️  AI generation DISABLED - using colored background", flush=True)
            img = Image.new('RGB', (width, height), colors['background'])

        draw = ImageDraw.Draw(img)

        # Load fonts with proper Linux font fallback
        title_font = self._get_font(80)
        points_font = self._get_font(50)
        footer_font = self._get_font(40)

        # Calculate layout
        margin = 60
        y_pos = margin + 40

        # Draw title
        title_wrapped = self._wrap_text(title, width - 2 * margin, title_font, draw)
        for line in title_wrapped:
            bbox = draw.textbbox((0, 0), line, font=title_font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = (width - text_width) // 2

            # Draw title with shadow for better readability
            draw.text((x + 3, y_pos + 3), line, fill=(0, 0, 0, 100), font=title_font)
            draw.text((x, y_pos), line, fill=colors['title'], font=title_font)
            y_pos += text_height + 20

        # Add accent line
        y_pos += 40
        line_width = min(400, width - 2 * margin)
        line_x = (width - line_width) // 2
        draw.rectangle(
            [(line_x, y_pos), (line_x + line_width, y_pos + 6)],
            fill=colors['accent']
        )
        y_pos += 60

        # Draw key points
        bullet_radius = 12
        for i, point in enumerate(key_points[:5], 1):  # Max 5 points
            # Draw bullet point
            bullet_x = margin + 30
            bullet_y = y_pos + 30

            # Alternating colors for bullets
            bullet_color = colors['accent'] if i % 2 == 1 else colors['highlight']
            draw.ellipse(
                [(bullet_x - bullet_radius, bullet_y - bullet_radius),
                 (bullet_x + bullet_radius, bullet_y + bullet_radius)],
                fill=bullet_color
            )

            # Draw point text
            point_wrapped = self._wrap_text(
                point,
                width - 2 * margin - 80,
                points_font,
                draw
            )

            point_x = bullet_x + bullet_radius + 30
            for line in point_wrapped:
                draw.text((point_x, y_pos), line, fill=colors['text'], font=points_font)
                bbox = draw.textbbox((0, 0), line, font=points_font)
                y_pos += bbox[3] - bbox[1] + 10

            y_pos += 30  # Space between points

        # Draw footer if provided
        if footer_text:
            y_footer = height - margin - 60
            footer_wrapped = self._wrap_text(footer_text, width - 2 * margin, footer_font, draw)
            for line in footer_wrapped:
                bbox = draw.textbbox((0, 0), line, font=footer_font)
                text_width = bbox[2] - bbox[0]
                x = (width - text_width) // 2
                draw.text((x, y_footer), line, fill=colors['accent'], font=footer_font)
                y_footer += bbox[3] - bbox[1] + 10

        # Save image
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"reel_{aspect_ratio}_{style}_{timestamp}.jpg"
        filepath = os.path.join(self.output_dir, filename)

        img.save(filepath, 'JPEG', quality=95)
        print(f"[REEL GENERATOR] Saved reel to: {filepath}", flush=True)

        return filepath

    def _get_font(self, size: int):
        """
        Get font with proper fallback chain for Linux/Windows compatibility

        Args:
            size: Font size in points

        Returns:
            ImageFont object
        """
        # Try Linux system fonts (common on Render, Heroku, etc.)
        linux_fonts = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]

        for font_path in linux_fonts:
            if os.path.exists(font_path):
                try:
                    return ImageFont.truetype(font_path, size)
                except Exception as e:
                    print(f"[REEL] Failed to load {font_path}: {e}", flush=True)
                    continue

        # Try Windows fonts
        try:
            return ImageFont.truetype("arial.ttf", size)
        except:
            pass

        # Last resort: default font (will look bad but at least won't crash)
        print(f"[WARNING] No system fonts found! Using default font (will look bad)", flush=True)
        print(f"[WARNING] Install fonts: apt-get install fonts-dejavu-core", flush=True)
        return ImageFont.load_default()

    def _wrap_text(self, text: str, max_width: int, font, draw) -> List[str]:
        """
        Wrap text to fit within max_width

        Args:
            text: Text to wrap
            max_width: Maximum width in pixels
            font: Font to use
            draw: ImageDraw object

        Returns:
            List of wrapped lines
        """
        words = text.split()
        lines = []
        current_line = []

        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=font)
            width = bbox[2] - bbox[0]

            if width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    # Single word too long - force it
                    lines.append(word)

        if current_line:
            lines.append(' '.join(current_line))

        return lines if lines else [text]

    def generate_from_content(
        self,
        content: Dict,
        aspect_ratio: str = 'reel',
        style: str = 'modern'
    ) -> str:
        """
        Generate reel from generated content dictionary

        Args:
            content: Content dictionary from ContentGenerator
            aspect_ratio: Aspect ratio to use
            style: Color scheme to use

        Returns:
            Path to generated image
        """
        # Extract title
        title = content.get('title', 'Untitled')
        if not title or title == 'Untitled':
            # Use first line of content as title
            content_text = content.get('content', '')
            if isinstance(content_text, list):
                content_text = ' '.join(content_text)
            title = content_text[:50] + '...' if len(content_text) > 50 else content_text

        # Extract key points
        key_points = content.get('key_points', [])
        if isinstance(key_points, str):
            import json
            try:
                key_points = json.loads(key_points)
            except:
                key_points = [key_points]

        # If no key points, extract from content
        if not key_points:
            content_text = content.get('content', '')
            if isinstance(content_text, list):
                content_text = '\n'.join(content_text)

            # Simple extraction: split by newlines and take first few
            lines = [l.strip() for l in content_text.split('\n') if l.strip()]
            key_points = [l for l in lines if len(l) > 10 and len(l) < 200][:5]

        if not key_points:
            key_points = ['Полезная информация из анализа новостей', 'Подписывайтесь на канал']

        # Extract hashtags for AI prompt (short keywords work better than long key_points)
        hashtags = content.get('hashtags', [])
        if isinstance(hashtags, str):
            import json
            try:
                hashtags = json.loads(hashtags)
            except:
                hashtags = hashtags.split()

        # Clean hashtags - remove # symbol for AI prompt
        keywords = [tag.lstrip('#') for tag in hashtags] if hashtags else []

        # Generate
        return self.generate_reel(
            title=title,
            key_points=key_points,
            keywords=keywords,  # Pass hashtags as keywords for AI prompt
            aspect_ratio=aspect_ratio,
            style=style,
            footer_text='News Insight Parser'
        )

    def get_available_styles(self) -> List[str]:
        """Get list of available color schemes"""
        return list(self.COLOR_SCHEMES.keys())

    def get_available_aspect_ratios(self) -> List[str]:
        """Get list of available aspect ratios"""
        return list(self.ASPECT_RATIOS.keys())


# Mock version for when Pillow is not available
class MockReelGenerator:
    """
    Mock ReelGenerator for environments where Pillow is not available

    This allows the code to run without errors, but doesn't actually generate images.
    Useful for development on systems where Pillow can't be installed (e.g., Python 3.14 on Windows).
    """

    def __init__(self, output_dir: str = 'generated_reels'):
        self.output_dir = output_dir
        print(f"[MOCK REEL GENERATOR] Running in mock mode (Pillow not available)", flush=True)

    def generate_reel(self, title: str, key_points: List[str], **kwargs) -> str:
        print(f"[MOCK] Would generate reel: {title}", flush=True)
        return "mock_reel.jpg"

    def generate_from_content(self, content: Dict, **kwargs) -> str:
        print(f"[MOCK] Would generate reel from content", flush=True)
        return "mock_reel.jpg"

    def get_available_styles(self) -> List[str]:
        return ['modern', 'professional', 'vibrant', 'minimal', 'dark']

    def get_available_aspect_ratios(self) -> List[str]:
        return ['square', 'reel', 'story', 'landscape', 'twitter']


# Factory function to get appropriate generator
def create_reel_generator(output_dir: str = 'generated_reels', use_ai: bool = True):
    """
    Create ReelGenerator or MockReelGenerator depending on Pillow availability

    Args:
        output_dir: Directory for generated images
        use_ai: Use AI image generation (Stable Diffusion) for professional images

    Returns:
        ReelGenerator or MockReelGenerator instance
    """
    if PIL_AVAILABLE:
        return ReelGenerator(output_dir, use_ai=use_ai)
    else:
        return MockReelGenerator(output_dir)
