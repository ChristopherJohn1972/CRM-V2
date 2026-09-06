"""Billboard image composition service.

Composes campaign billboard images from product images + text overlays
using Pillow. No external AI image generation API required.
"""

import io
import logging
import os
import textwrap
import uuid
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    Image = ImageDraw = ImageFilter = ImageFont = None

from config import settings

logger = logging.getLogger(__name__)

STORAGE_ROOT = Path(getattr(settings, "STORAGE_ROOT", "storage/"))
CREATIVE_DIR = STORAGE_ROOT / "campaign_creatives"

BILLBOARD_WIDTH = 1200
BILLBOARD_HEIGHT = 628

FONT_SEARCH_PATHS = [
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/impact.ttf",
    "C:/Windows/Fonts/calibrib.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


def _ensure_dir():
    CREATIVE_DIR.mkdir(parents=True, exist_ok=True)


def _get_font(size, bold=True):
    for path in FONT_SEARCH_PATHS:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _wrap_text(text, font, max_width, draw):
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        test_line = f"{current_line} {word}".strip()
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return lines


def _draw_text_block(draw, text, y, font, color, canvas_width, align="center"):
    lines = _wrap_text(text, font, canvas_width - 120, draw)
    line_height = font.size + 8
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        text_width = bbox[2] - bbox[0]
        if align == "center":
            x = (canvas_width - text_width) // 2
        elif align == "left":
            x = 60
        else:
            x = canvas_width - text_width - 60
        draw.text((x, y), line, fill=color, font=font)
        y += line_height
    return y


def _draw_offer_badge(draw, offer_text, y, canvas_width):
    if not offer_text:
        return y
    font = _get_font(36, bold=True)
    bbox = draw.textbbox((0, 0), offer_text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    badge_w = text_w + 40
    badge_h = text_h + 20
    badge_x = (canvas_width - badge_w) // 2
    badge_y = y
    draw.rounded_rectangle(
        [badge_x, badge_y, badge_x + badge_w, badge_y + badge_h],
        radius=8,
        fill=(220, 53, 69),
    )
    draw.text(
        (badge_x + 20, badge_y + 10),
        offer_text,
        fill=(255, 255, 255),
        font=font,
    )
    return y + badge_h + 20


def _draw_cta_button(draw, cta_text, y, canvas_width):
    if not cta_text:
        return y
    font = _get_font(28, bold=True)
    bbox = draw.textbbox((0, 0), cta_text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    btn_w = text_w + 60
    btn_h = text_h + 24
    btn_x = (canvas_width - btn_w) // 2
    btn_y = y
    draw.rounded_rectangle(
        [btn_x, btn_y, btn_x + btn_w, btn_y + btn_h],
        radius=8,
        fill=(33, 37, 41),
    )
    draw.text(
        (btn_x + 30, btn_y + 12),
        cta_text,
        fill=(255, 255, 255),
        font=font,
    )
    return y + btn_h + 20


def _compose_hero(product_img, headline, subheadline, offer_text, cta_text, bg_color):
    img = Image.new("RGB", (BILLBOARD_WIDTH, BILLBOARD_HEIGHT), bg_color)
    draw = ImageDraw.Draw(img)

    if product_img:
        pw, ph = product_img.size
        max_product_h = int(BILLBOARD_HEIGHT * 0.55)
        max_product_w = int(BILLBOARD_WIDTH * 0.45)
        scale = min(max_product_w / pw, max_product_h / ph)
        new_w = int(pw * scale)
        new_h = int(ph * scale)
        product_resized = product_img.resize((new_w, new_h), Image.LANCZOS)
        px = (BILLBOARD_WIDTH - new_w) // 2
        py = (BILLBOARD_HEIGHT - new_h) // 2
        img.paste(product_resized, (px, py), product_resized if product_resized.mode == "RGBA" else None)
        draw = ImageDraw.Draw(img)

    headline_font = _get_font(52, bold=True)
    y = 40
    if headline:
        y = _draw_text_block(draw, headline, y, headline_font, (255, 255, 255), BILLBOARD_WIDTH)
        y += 10

    if subheadline:
        sub_font = _get_font(24, bold=False)
        y = _draw_text_block(draw, subheadline, y, sub_font, (200, 200, 200), BILLBOARD_WIDTH)
        y += 10

    bottom_y = BILLBOARD_HEIGHT - 100
    if cta_text:
        _draw_cta_button(draw, cta_text, bottom_y, BILLBOARD_WIDTH)
    if offer_text:
        _draw_offer_badge(draw, offer_text, bottom_y - 70, BILLBOARD_WIDTH)

    return img


def _compose_split(product_img, headline, subheadline, offer_text, cta_text, bg_color):
    img = Image.new("RGB", (BILLBOARD_WIDTH, BILLBOARD_HEIGHT), bg_color)
    draw = ImageDraw.Draw(img)

    product_zone_w = BILLBOARD_WIDTH // 2
    if product_img:
        pw, ph = product_img.size
        max_h = BILLBOARD_HEIGHT - 80
        max_w = product_zone_w - 60
        scale = min(max_w / pw, max_h / ph)
        new_w = int(pw * scale)
        new_h = int(ph * scale)
        product_resized = product_img.resize((new_w, new_h), Image.LANCZOS)
        px = (product_zone_w - new_w) // 2
        py = (BILLBOARD_HEIGHT - new_h) // 2
        img.paste(product_resized, (px, py), product_resized if product_resized.mode == "RGBA" else None)
        draw = ImageDraw.Draw(img)

    text_x = product_zone_w + 40
    text_zone_w = BILLBOARD_WIDTH - product_zone_w - 80

    headline_font = _get_font(44, bold=True)
    y = 80
    if headline:
        lines = _wrap_text(headline, headline_font, text_zone_w, draw)
        for line in lines:
            draw.text((text_x, y), line, fill=(255, 255, 255), font=headline_font)
            y += headline_font.size + 10
        y += 20

    if subheadline:
        sub_font = _get_font(22, bold=False)
        lines = _wrap_text(subheadline, sub_font, text_zone_w, draw)
        for line in lines:
            draw.text((text_x, y), line, fill=(200, 200, 200), font=sub_font)
            y += sub_font.size + 8
        y += 20

    if offer_text:
        y = _draw_offer_badge(draw, offer_text, y, BILLBOARD_WIDTH)
    if cta_text:
        _draw_cta_button(draw, cta_text, y + 10, BILLBOARD_WIDTH)

    return img


def _compose_minimal(product_img, headline, subheadline, offer_text, cta_text, bg_color):
    img = Image.new("RGB", (BILLBOARD_WIDTH, BILLBOARD_HEIGHT), bg_color)
    draw = ImageDraw.Draw(img)

    if product_img:
        pw, ph = product_img.size
        scale = max(BILLBOARD_WIDTH / pw, BILLBOARD_HEIGHT / ph)
        new_w = int(pw * scale)
        new_h = int(ph * scale)
        product_resized = product_img.resize((new_w, new_h), Image.LANCZOS)
        px = (BILLBOARD_WIDTH - new_w) // 2
        py = (BILLBOARD_HEIGHT - new_h) // 2
        img.paste(product_resized, (px, py))
        overlay = Image.new("RGBA", (BILLBOARD_WIDTH, BILLBOARD_HEIGHT), (0, 0, 0, 120))
        img = img.convert("RGBA")
        img = Image.alpha_composite(img, overlay)
        draw = ImageDraw.Draw(img)

    headline_font = _get_font(56, bold=True)
    y = 60
    if headline:
        y = _draw_text_block(draw, headline, y, headline_font, (255, 255, 255), BILLBOARD_WIDTH)
        y += 10

    if subheadline:
        sub_font = _get_font(26, bold=False)
        y = _draw_text_block(draw, subheadline, y, sub_font, (220, 220, 220), BILLBOARD_WIDTH)

    bottom_y = BILLBOARD_HEIGHT - 100
    if cta_text:
        _draw_cta_button(draw, cta_text, bottom_y, BILLBOARD_WIDTH)
    if offer_text:
        _draw_offer_badge(draw, offer_text, bottom_y - 70, BILLBOARD_WIDTH)

    return img.convert("RGB")


TEMPLATES = {
    "hero": _compose_hero,
    "split": _compose_split,
    "minimal": _compose_minimal,
}

TEMPLATE_COLORS = {
    "hero": (25, 25, 35),
    "split": (18, 18, 28),
    "minimal": (30, 30, 40),
}


def generate_billboard(
    product_image_path=None,
    product_image_url=None,
    headline=None,
    subheadline=None,
    offer_text=None,
    cta_text=None,
    template="hero",
    campaign_id=None,
):
    if not PILLOW_AVAILABLE:
        raise RuntimeError("Pillow is not installed. Run: pip install Pillow")

    _ensure_dir()

    product_img = None
    if product_image_path and os.path.exists(product_image_path):
        try:
            product_img = Image.open(product_image_path).convert("RGBA")
        except Exception as exc:
            logger.warning("Failed to load product image from path: %s", exc)
    elif product_image_url:
        # Try local file first (storage_key like "campaign_products/xxx.png")
        # Strip /api/storage/ prefix if present
        storage_key = product_image_url
        if storage_key.startswith("/api/storage/"):
            storage_key = storage_key[len("/api/storage/"):]
        elif storage_key.startswith("/storage/"):
            storage_key = storage_key[len("/storage/"):]
        local_path = STORAGE_ROOT / storage_key
        if not local_path.is_absolute():
            from config import settings as _settings
            local_path = Path(_settings.BASE_DIR) / local_path
        if local_path.exists():
            try:
                product_img = Image.open(local_path).convert("RGBA")
            except Exception as exc:
                logger.warning("Failed to load product image from local path %s: %s", local_path, exc)
        else:
            # Fall back to HTTP fetch for full URLs
            try:
                import requests as req
                resp = req.get(product_image_url, timeout=10)
                resp.raise_for_status()
                product_img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
            except Exception as exc:
                logger.warning("Failed to load product image from URL %s: %s", product_image_url, exc)

    compose_fn = TEMPLATES.get(template, _compose_hero)
    bg_color = TEMPLATE_COLORS.get(template, (25, 25, 35))

    billboard = compose_fn(product_img, headline, subheadline, offer_text, cta_text, bg_color)

    filename = f"billboard_{uuid.uuid4().hex[:12]}.png"
    subdir = CREATIVE_DIR / str(campaign_id) if campaign_id else CREATIVE_DIR
    subdir.mkdir(parents=True, exist_ok=True)
    filepath = subdir / filename
    billboard.save(filepath, "PNG", quality=95)

    storage_key = f"campaign_creatives/{campaign_id}/{filename}" if campaign_id else f"campaign_creatives/{filename}"
    logger.info("Billboard generated: %s", storage_key)

    return {
        "storage_key": storage_key,
        "filepath": str(filepath),
        "filename": filename,
        "width": billboard.width,
        "height": billboard.height,
        "mime_type": "image/png",
        "template": template,
    }


def generate_multi_template(
    product_image_path=None,
    product_image_url=None,
    headline=None,
    subheadline=None,
    offer_text=None,
    cta_text=None,
    campaign_id=None,
):
    results = {}
    for template_name in TEMPLATES:
        result = generate_billboard(
            product_image_path=product_image_path,
            product_image_url=product_image_url,
            headline=headline,
            subheadline=subheadline,
            offer_text=offer_text,
            cta_text=cta_text,
            template=template_name,
            campaign_id=campaign_id,
        )
        results[template_name] = result
    return results
