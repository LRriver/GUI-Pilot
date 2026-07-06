"""Screenshot preprocessing utilities."""

from __future__ import annotations

import base64
import io

from PIL import ImageEnhance


def encode_image_jpeg(image, quality: int = 92) -> str:
    """Encode a PIL image as a base64 JPEG data URL after mild enhancement."""
    buffered = io.BytesIO()
    if image.mode in ("RGBA", "LA", "P"):
        image = image.convert("RGB")
    else:
        image = image.copy()
    image = ImageEnhance.Contrast(image).enhance(1.06)
    image = ImageEnhance.Sharpness(image).enhance(1.25)
    image.save(buffered, format="JPEG", quality=quality)
    base64_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{base64_str}"
