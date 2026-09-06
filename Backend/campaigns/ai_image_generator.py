"""AI image generation service using OpenAI DALL-E 3.

Generates professional marketing images for campaigns.
Falls back to None (Pillow-only composition) when API key is not configured.
"""

import io
import logging
import os
import uuid
from pathlib import Path

from config import settings

logger = logging.getLogger(__name__)

STORAGE_ROOT = Path(getattr(settings, "STORAGE_ROOT", "storage/"))
CREATIVE_DIR = STORAGE_ROOT / "campaign_creatives"

OPENAI_API_KEY = getattr(settings, "OPENAI_API_KEY", "")
OPENAI_MODEL = getattr(settings, "OPENAI_MODEL", "dall-e-3")


STYLE_PROMPTS = {
    "hero": (
        "Professional product-focused marketing image. "
        "The product is the hero, centered and prominent against a clean, "
        "modern dark background. Dramatic studio lighting highlights the product. "
        "Minimal distractions. Sleek, premium feel suitable for social media ads."
    ),
    "split": (
        "Professional promotional marketing image with a split layout. "
        "Left side features the product on a clean background. "
        "Right side is an open dark area suitable for text overlay. "
        "Modern, clean design with balanced composition. "
        "Suitable for Facebook and Instagram ads."
    ),
    "minimal": (
        "Professional lifestyle marketing image. "
        "Full-bleed atmospheric scene with the product in context. "
        "Moody, elegant dark tones. Shallow depth of field. "
        "Cinematic quality suitable for premium brand campaigns."
    ),
}


def _build_prompt(product_name, product_description, offer_text, template, extra_context=""):
    style = STYLE_PROMPTS.get(template, STYLE_PROMPTS["hero"])

    prompt_parts = [
        style,
        f"Product: {product_name}.",
    ]

    if product_description:
        prompt_parts.append(f"Description: {product_description}.")

    if offer_text:
        prompt_parts.append(f"Include a subtle visual element suggesting: {offer_text}.")

    if extra_context:
        prompt_parts.append(extra_context)

    prompt_parts.append(
        "No text, no words, no letters, no watermarks. "
        "High resolution, photorealistic, 1200x628 aspect ratio composition."
    )

    return " ".join(prompt_parts)


def _save_image(image_bytes, campaign_id):
    _ensure_dir()
    filename = f"ai_creative_{uuid.uuid4().hex[:12]}.png"
    subdir = CREATIVE_DIR / str(campaign_id) if campaign_id else CREATIVE_DIR
    subdir.mkdir(parents=True, exist_ok=True)
    filepath = subdir / filename

    with open(filepath, "wb") as f:
        f.write(image_bytes)

    storage_key = f"campaign_creatives/{campaign_id}/{filename}" if campaign_id else f"campaign_creatives/{filename}"
    return {
        "filepath": str(filepath),
        "storage_key": storage_key,
        "filename": filename,
    }


def _ensure_dir():
    CREATIVE_DIR.mkdir(parents=True, exist_ok=True)


def is_available():
    return bool(OPENAI_API_KEY)


def generate_image(
    product_name,
    product_description=None,
    offer_text=None,
    template="hero",
    campaign_id=None,
    extra_context="",
):
    """Generate a marketing image using DALL-E 3.

    Returns dict with storage_key, filepath, width, height, mime_type.
    Raises RuntimeError if generation fails.
    """
    if not OPENAI_API_KEY:
        raise RuntimeError(
            "AI image generation is not configured. "
            "Set CRM_OPENAI_API_KEY environment variable."
        )

    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError(
            "openai package is not installed. Run: pip install openai"
        )

    prompt = _build_prompt(
        product_name, product_description, offer_text, template, extra_context
    )
    logger.info("Generating AI image for campaign %s (template=%s)", campaign_id, template)
    logger.debug("DALL-E prompt: %s", prompt)

    client = OpenAI(api_key=OPENAI_API_KEY)

    try:
        response = client.images.generate(
            model=OPENAI_MODEL,
            prompt=prompt,
            size="1792x1024",
            quality="hd",
            n=1,
            response_format="b64_json",
        )
    except Exception as exc:
        logger.error("DALL-E API error: %s", exc)
        raise RuntimeError(f"AI image generation failed: {exc}")

    import base64
    image_b64 = response.data[0].b64_json
    image_bytes = base64.b64decode(image_b64)

    saved = _save_image(image_bytes, campaign_id)

    try:
        from PIL import Image
        img = Image.open(io.BytesIO(image_bytes))
        width, height = img.size
    except Exception:
        width, height = 1792, 1024

    revised_prompt = getattr(response.data[0], "revised_prompt", None)
    if revised_prompt:
        logger.debug("DALL-E revised prompt: %s", revised_prompt)

    logger.info("AI image generated: %s (%dx%d)", saved["storage_key"], width, height)

    return {
        "storage_key": saved["storage_key"],
        "filepath": saved["filepath"],
        "filename": saved["filename"],
        "width": width,
        "height": height,
        "mime_type": "image/png",
        "template": template,
        "provider": "dall-e-3",
        "prompt": prompt,
    }


def generate_multi_template(
    product_name,
    product_description=None,
    offer_text=None,
    campaign_id=None,
    extra_context="",
):
    """Generate images for all template styles."""
    results = {}
    for template_name in STYLE_PROMPTS:
        try:
            result = generate_image(
                product_name=product_name,
                product_description=product_description,
                offer_text=offer_text,
                template=template_name,
                campaign_id=campaign_id,
                extra_context=extra_context,
            )
            results[template_name] = result
        except Exception as exc:
            logger.warning("Failed to generate %s template: %s", template_name, exc)
            results[template_name] = None
    return results
