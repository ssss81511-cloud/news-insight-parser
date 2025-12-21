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
import random

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

    def __init__(self, output_dir: str = 'generated_reels', use_ai: bool = True, pexels_key: Optional[str] = None):
        """
        Initialize ReelGenerator

        Args:
            output_dir: Directory to save generated images
            use_ai: Use AI-generated images (FREE via Pollinations.ai) or stock photos
            pexels_key: Pexels API key for stock photo fallback (get free at https://www.pexels.com/api/)
        """
        if not PIL_AVAILABLE:
            raise ImportError("Pillow is required for ReelGenerator. Install with: pip install Pillow")

        self.output_dir = output_dir
        self.use_ai = use_ai
        self.pexels_key = pexels_key
        os.makedirs(output_dir, exist_ok=True)

        # Custom font and background paths
        self.custom_font_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'шрифт', 'CorrectionBrush.otf')
        self.custom_background_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'фон для постов.png')

        # Check if custom assets exist
        if os.path.exists(self.custom_font_path):
            print(f"[REEL GENERATOR] ✅ Custom font loaded: CorrectionBrush.otf", flush=True)
        else:
            print(f"[REEL GENERATOR] ⚠️  Custom font not found, using system fonts", flush=True)

        if os.path.exists(self.custom_background_path):
            print(f"[REEL GENERATOR] ✅ Custom background loaded: фон для постов.png", flush=True)
        else:
            print(f"[REEL GENERATOR] ⚠️  Custom background not found", flush=True)

        # APIs
        self.pexels_api_url = "https://api.pexels.com/v1/search"
        self.pollinations_base_url = "https://image.pollinations.ai/prompt"  # FREE, no API key needed!

        # Determine image generation mode
        if use_ai:
            print(f"[REEL GENERATOR] ✅ AI Image Generation ENABLED (Pollinations.ai - FREE!)", flush=True)
            self.image_mode = 'ai_generate'
            if pexels_key:
                print(f"[REEL GENERATOR] ℹ️  Pexels fallback available", flush=True)
        else:
            if pexels_key:
                print(f"[REEL GENERATOR] ✅ Stock Photos ENABLED (Pexels)", flush=True)
                self.image_mode = 'stock_photos'
            else:
                print(f"[REEL GENERATOR] ⚠️  Using gradient backgrounds", flush=True)
                self.image_mode = 'gradient'

    def _generate_ai_image(self, title: str, keywords: List[str]) -> Optional[Image.Image]:
        """
        Generate image using Pollinations.ai (100% FREE, no API key needed!)

        Args:
            title: Content title
            keywords: Keywords for prompt

        Returns:
            PIL Image or None if failed
        """
        # Create optimized prompt
        prompt = self._create_ai_prompt(title, keywords)
        print(f"[AI GEN] 🎨 Pollinations.ai generating: {prompt[:80]}...", flush=True)

        try:
            # URL encode the prompt
            import urllib.parse
            encoded_prompt = urllib.parse.quote(prompt)

            # Build Pollinations.ai URL (simple and elegant!)
            image_url = f"{self.pollinations_base_url}/{encoded_prompt}?width=1024&height=1024&nologo=true&model=flux"

            print(f"[AI GEN] 🌐 Requesting: {image_url[:100]}...", flush=True)

            # Download image directly (Pollinations returns image immediately)
            response = requests.get(image_url, timeout=30)

            if response.status_code == 200:
                # Check if we got an image
                if response.headers.get('content-type', '').startswith('image/'):
                    image = Image.open(io.BytesIO(response.content))
                    print(f"[AI GEN] ✅ Pollinations generated: {image.size} (FREE!)", flush=True)
                    return image
                else:
                    print(f"[AI GEN] ❌ Response is not an image: {response.headers.get('content-type')}", flush=True)
                    return None
            else:
                print(f"[AI GEN] ❌ Pollinations Error {response.status_code}", flush=True)
                return None

        except Exception as e:
            print(f"[AI GEN] ❌ Exception: {e}", flush=True)
            import traceback
            print(f"[AI GEN] Traceback: {traceback.format_exc()[:300]}", flush=True)
            return None

    def _create_ai_prompt(self, title: str, keywords: List[str]) -> str:
        """
        Create optimized prompt for AI image generation

        IMPORTANT: Prompts MUST be abstract/visual only to prevent text generation in images.
        Avoid words like: "about", "for", "illustration", "infographic", "text", "words"

        Args:
            title: Content title
            keywords: Topic keywords

        Returns:
            Optimized prompt for FLUX/Stable Diffusion (VISUAL ONLY)
        """
        # Create abstract, purely visual prompts (NO text/words in images!)
        prompts = [
            "abstract geometric shapes, vibrant gradient background, modern tech aesthetic, floating particles, deep blue purple cyan colors, clean minimalist design, 4k digital art",
            "futuristic technology concept, glowing neon elements, dark background with light rays, sleek professional style, cyberpunk aesthetic, high quality render",
            "modern gradient waves, smooth flowing curves, bold vibrant colors, professional corporate design, abstract patterns, contemporary art style, premium quality",
            "geometric low poly background, triangular shapes, gradient mesh, tech startup aesthetic, clean composition, modern color palette, digital illustration",
            "abstract bokeh lights, defocused particles, deep space atmosphere, glowing orbs, professional dark theme, cinematic lighting, 4k wallpaper quality",
            "fluid gradients, organic shapes, vibrant color transitions, modern minimalist aesthetic, smooth flowing forms, professional branding style, high-end design",
            "circuit board patterns, technology background, glowing connections, abstract digital network, dark blue tones, futuristic concept, premium render",
            "abstract light beams, colorful rays, modern tech background, dynamic energy flow, professional gradient design, clean geometric elements, high quality",
        ]

        # Rotate through prompts based on title hash for variety
        import hashlib
        index = int(hashlib.md5(title.encode()).hexdigest(), 16) % len(prompts)

        selected_prompt = prompts[index]
        print(f"[AI PROMPT] Using visual-only prompt (NO text generation): {selected_prompt[:60]}...", flush=True)

        return selected_prompt

    def _fetch_pexels_photo(self, keywords: List[str]) -> Optional[Image.Image]:
        """
        Fetch professional photo from Pexels

        Args:
            keywords: Keywords for search

        Returns:
            PIL Image or None if failed
        """
        if not self.pexels_key:
            print(f"[PEXELS] No API key - skipping photo fetch", flush=True)
            return None

        # Process keywords - split CamelCase and take simple words
        import re
        processed = []
        for kw in keywords[:3]:
            # Split CamelCase: AIRevolution → AI Revolution
            words = re.sub('([A-Z][a-z]+)', r' \1', re.sub('([A-Z]+)', r' \1', kw)).split()
            processed.extend(words)

        # Use simple, common words that Pexels understands
        query = ' '.join(processed[:5]).lower() if processed else 'technology business abstract'

        # Fallback to generic tech terms if query is too specific
        if not any(word in query for word in ['tech', 'business', 'work', 'startup', 'office', 'computer', 'digital']):
            query = 'technology business innovation'

        print(f"[PEXELS] Searching: {query}", flush=True)

        try:
            headers = {
                'Authorization': self.pexels_key
            }

            params = {
                'query': query,
                'orientation': 'square',
                'size': 'large',
                'per_page': 10  # Get 10 photos for randomization
            }

            response = requests.get(
                self.pexels_api_url,
                headers=headers,
                params=params,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()

                if data.get('photos') and len(data['photos']) > 0:
                    # Pick random photo from results
                    photo = random.choice(data['photos'])
                    photo_index = data['photos'].index(photo) + 1
                    print(f"[PEXELS] 🎲 Selected random photo {photo_index}/{len(data['photos'])}", flush=True)

                    # Get large photo URL
                    photo_url = photo['src']['large2x']

                    # Download image
                    img_response = requests.get(photo_url, timeout=15)
                    if img_response.status_code == 200:
                        image = Image.open(io.BytesIO(img_response.content))
                        print(f"[PEXELS] ✅ Downloaded photo: {image.size}", flush=True)
                        return image
                    else:
                        print(f"[PEXELS] Failed to download image", flush=True)
                        return None
                else:
                    print(f"[PEXELS] No photos found for query", flush=True)
                    return None

            else:
                print(f"[PEXELS] API error {response.status_code}: {response.text[:200]}", flush=True)
                return None

        except Exception as e:
            print(f"[PEXELS] Exception: {e}", flush=True)
            return None

    def _load_custom_background(self, width: int, height: int) -> Optional[Image.Image]:
        """
        Load custom background image from user's file

        Args:
            width: Target width
            height: Target height

        Returns:
            PIL Image or None if not found
        """
        if not os.path.exists(self.custom_background_path):
            return None

        try:
            print(f"[CUSTOM BG] Loading custom background: {self.custom_background_path}", flush=True)
            img = Image.open(self.custom_background_path)

            # Resize to target dimensions
            img = img.resize((width, height), Image.Resampling.LANCZOS)

            # Add light overlay for text readability
            overlay = Image.new('RGBA', (width, height), (0, 0, 0, 100))  # Light overlay
            img = img.convert('RGBA')
            img = Image.alpha_composite(img, overlay)
            img = img.convert('RGB')

            print(f"[CUSTOM BG] ✅ Custom background loaded: {img.size}", flush=True)
            return img
        except Exception as e:
            print(f"[CUSTOM BG] ❌ Failed to load custom background: {e}", flush=True)
            return None

    def _generate_gradient_background(self, keywords: List[str], width: int, height: int) -> Image.Image:
        """
        Generate beautiful gradient background based on keywords

        Args:
            keywords: Keywords to determine color palette
            width: Image width
            height: Image height

        Returns:
            PIL Image with gradient
        """
        import hashlib

        # Color palettes (modern, vibrant gradients)
        palettes = [
            # Tech/AI themes
            [(99, 102, 241), (139, 92, 246)],      # Indigo to Purple
            [(59, 130, 246), (147, 51, 234)],      # Blue to Purple
            [(16, 185, 129), (59, 130, 246)],      # Emerald to Blue

            # Business/Professional
            [(15, 23, 42), (99, 102, 241)],        # Dark to Indigo
            [(30, 58, 138), (59, 130, 246)],       # Navy to Blue

            # Creative/Modern
            [(236, 72, 153), (239, 68, 68)],       # Pink to Red
            [(251, 146, 60), (239, 68, 68)],       # Orange to Red
            [(34, 211, 238), (139, 92, 246)],      # Cyan to Purple

            # Elegant
            [(88, 28, 135), (219, 39, 119)],       # Purple to Pink
            [(124, 58, 237), (236, 72, 153)],      # Violet to Pink
        ]

        # Select palette based on keywords hash (deterministic)
        keyword_str = ''.join(keywords[:3]) if keywords else 'default'
        hash_val = int(hashlib.md5(keyword_str.encode()).hexdigest(), 16)
        palette_idx = hash_val % len(palettes)
        color1, color2 = palettes[palette_idx]

        print(f"[GRADIENT] Creating gradient: {color1} → {color2}", flush=True)

        # Create gradient image
        img = Image.new('RGB', (width, height))
        draw = ImageDraw.Draw(img)

        # Draw gradient
        for y in range(height):
            # Calculate blend ratio
            ratio = y / height

            # Interpolate colors
            r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
            g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
            b = int(color1[2] * (1 - ratio) + color2[2] * ratio)

            # Draw line
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        print(f"[GRADIENT] ✅ Generated: {width}x{height}", flush=True)
        return img

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

        # Generate or fetch background image based on mode
        search_keywords = keywords if keywords else []
        img = None

        print(f"[REEL] 🔍 Image mode: {self.image_mode}", flush=True)

        # PRIORITY 1: Try custom background FIRST (if exists)
        if os.path.exists(self.custom_background_path):
            print(f"[REEL] 🎨 Using custom background (user's image)", flush=True)
            img = self._load_custom_background(width, height)
            if img:
                print(f"[REEL] ✅ Custom background loaded successfully!", flush=True)

        # PRIORITY 2: AI Image Generation (if custom background failed or not available)
        if img is None and self.image_mode == 'ai_generate':
            # AI Image Generation (Pollinations.ai - FREE!)
            print(f"[REEL] 🎨 Starting AI Image Generation (Pollinations.ai - FREE)", flush=True)
            img = self._generate_ai_image(title, search_keywords)

            if img:
                print(f"[REEL] ✅ AI generation SUCCESS!", flush=True)
            else:
                print(f"[REEL] ❌ AI generation FAILED - falling back to stock photos", flush=True)

            if img:
                # Resize to target dimensions
                img = img.resize((width, height), Image.Resampling.LANCZOS)
                # Add stronger overlay for text readability (darker background = better contrast)
                overlay = Image.new('RGBA', (width, height), (0, 0, 0, 150))  # Increased from 120 to 150
                img = img.convert('RGBA')
                img = Image.alpha_composite(img, overlay)
                img = img.convert('RGB')
                print(f"[REEL] ✅ Using AI-generated image with enhanced text overlay", flush=True)

        if img is None and self.image_mode in ['ai_generate', 'stock_photos']:
            # Stock Photos (Pexels) - fallback or primary
            print(f"[REEL] 📷 Stock photos mode (or AI fallback)", flush=True)
            photo = self._fetch_pexels_photo(search_keywords)

            if photo:
                img = photo.resize((width, height), Image.Resampling.LANCZOS)
                overlay = Image.new('RGBA', (width, height), (0, 0, 0, 130))  # Increased from 100 to 130
                img = img.convert('RGBA')
                img = Image.alpha_composite(img, overlay)
                img = img.convert('RGB')
                print(f"[REEL] ✅ Using Pexels stock photo with enhanced text overlay", flush=True)

        if img is None:
            # Gradient fallback (final fallback or primary if no AI/photos)
            print(f"[REEL] 🎨 Using gradient background (fallback)", flush=True)
            img = self._generate_gradient_background(search_keywords, width, height)
            overlay = Image.new('RGBA', (width, height), (0, 0, 0, 80))
            img = img.convert('RGBA')
            img = Image.alpha_composite(img, overlay)
            img = img.convert('RGB')

        draw = ImageDraw.Draw(img)

        # Adaptive font sizes and margins based on aspect ratio
        if aspect_ratio == 'square':
            # Square needs smaller fonts and tighter spacing
            title_font_size = 60
            points_font_size = 38
            footer_font_size = 32
            margin = 50
            max_key_points = 4  # Limit points for square
        elif aspect_ratio in ['reel', 'story']:
            # Vertical formats have more space
            title_font_size = 80
            points_font_size = 50
            footer_font_size = 40
            margin = 60
            max_key_points = 5
        else:
            # Landscape formats
            title_font_size = 70
            points_font_size = 45
            footer_font_size = 35
            margin = 60
            max_key_points = 5

        # Load fonts with proper Linux font fallback
        title_font = self._get_font(title_font_size)
        points_font = self._get_font(points_font_size)
        footer_font = self._get_font(footer_font_size)

        # Calculate layout
        y_pos = margin + 30

        # Draw title with professional outline and shadow
        title_wrapped = self._wrap_text(title, width - 2 * margin, title_font, draw)
        for line in title_wrapped:
            bbox = draw.textbbox((0, 0), line, font=title_font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = (width - text_width) // 2

            # Use professional text rendering with outline
            self._draw_text_with_outline(
                draw, (x, y_pos), line, title_font,
                fill_color=colors['title'],
                outline_width=4,  # Thick outline for title
                shadow=True
            )
            y_pos += text_height + 20

        # Add accent line
        accent_spacing = 25 if aspect_ratio == 'square' else 40
        y_pos += accent_spacing
        line_width = min(350 if aspect_ratio == 'square' else 400, width - 2 * margin)
        line_x = (width - line_width) // 2
        draw.rectangle(
            [(line_x, y_pos), (line_x + line_width, y_pos + 5)],
            fill=colors['accent']
        )
        y_pos += accent_spacing + 20

        # Draw key points
        bullet_radius = 10 if aspect_ratio == 'square' else 12
        for i, point in enumerate(key_points[:max_key_points], 1):
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

            # Draw point text with outline for readability
            point_wrapped = self._wrap_text(
                point,
                width - 2 * margin - 80,
                points_font,
                draw
            )

            point_x = bullet_x + bullet_radius + 25
            for line in point_wrapped:
                # Use professional text rendering with outline
                self._draw_text_with_outline(
                    draw, (point_x, y_pos), line, points_font,
                    fill_color=colors['text'],
                    outline_width=2,  # Thinner outline for body text
                    shadow=True
                )
                bbox = draw.textbbox((0, 0), line, font=points_font)
                y_pos += bbox[3] - bbox[1] + 8

            # Space between points - less for square
            y_pos += 20 if aspect_ratio == 'square' else 30

        # Draw footer if provided
        if footer_text:
            y_footer = height - margin - 60
            footer_wrapped = self._wrap_text(footer_text, width - 2 * margin, footer_font, draw)
            for line in footer_wrapped:
                bbox = draw.textbbox((0, 0), line, font=footer_font)
                text_width = bbox[2] - bbox[0]
                x = (width - text_width) // 2
                # Use professional text rendering with outline
                self._draw_text_with_outline(
                    draw, (x, y_footer), line, footer_font,
                    fill_color=colors['accent'],
                    outline_width=2,
                    shadow=True
                )
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

        Priority:
        1. Custom font (CorrectionBrush.otf)
        2. Linux system fonts
        3. Windows fonts
        4. Default font

        Args:
            size: Font size in points

        Returns:
            ImageFont object
        """
        # PRIORITY 1: Try custom font first
        if os.path.exists(self.custom_font_path):
            try:
                font = ImageFont.truetype(self.custom_font_path, size)
                return font
            except Exception as e:
                print(f"[REEL] Failed to load custom font: {e}", flush=True)

        # PRIORITY 2: Try Linux system fonts (common on Render, Heroku, etc.)
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

        # PRIORITY 3: Try Windows fonts
        try:
            return ImageFont.truetype("arial.ttf", size)
        except:
            pass

        # Last resort: default font (will look bad but at least won't crash)
        print(f"[WARNING] No system fonts found! Using default font (will look bad)", flush=True)
        print(f"[WARNING] Install fonts: apt-get install fonts-dejavu-core", flush=True)
        return ImageFont.load_default()

    def _draw_text_with_outline(self, draw, position: Tuple[int, int], text: str, font,
                                fill_color: Tuple[int, int, int], outline_width: int = 3,
                                shadow: bool = True) -> None:
        """
        Draw text with outline and shadow for maximum readability on any background

        Args:
            draw: ImageDraw object
            position: (x, y) position
            text: Text to draw
            font: Font to use
            fill_color: RGB color for text
            outline_width: Width of outline in pixels (default: 3)
            shadow: Whether to add drop shadow (default: True)
        """
        x, y = position

        # Draw shadow first (if enabled)
        if shadow:
            shadow_offset = outline_width + 2
            draw.text((x + shadow_offset, y + shadow_offset), text, fill=(0, 0, 0, 180), font=font)

        # Draw outline by drawing text multiple times in a circle around the position
        # This creates a thick, smooth outline
        for offset_x in range(-outline_width, outline_width + 1):
            for offset_y in range(-outline_width, outline_width + 1):
                if offset_x != 0 or offset_y != 0:  # Skip center (that's the main text)
                    draw.text((x + offset_x, y + offset_y), text, fill=(0, 0, 0, 200), font=font)

        # Draw main text on top
        draw.text((x, y), text, fill=fill_color, font=font)

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
            footer_text=None  # No watermark
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
def create_reel_generator(output_dir: str = 'generated_reels', use_ai: bool = True, pexels_key: Optional[str] = None):
    """
    Create ReelGenerator or MockReelGenerator depending on Pillow availability

    Args:
        output_dir: Directory for generated images
        use_ai: Use AI-generated images (FREE via Pollinations.ai) or stock photos
        pexels_key: Pexels API key for stock photo fallback (get free at https://www.pexels.com/api/)

    Returns:
        ReelGenerator or MockReelGenerator instance
    """
    if PIL_AVAILABLE:
        return ReelGenerator(output_dir, use_ai=use_ai, pexels_key=pexels_key)
    else:
        return MockReelGenerator(output_dir)
