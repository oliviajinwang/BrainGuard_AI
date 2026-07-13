"""Circular doctor avatar processing helpers."""

from __future__ import annotations

import base64
import io

from PIL import Image, ImageDraw


def make_circular_avatar_data_url(image_bytes: bytes, size: int = 512) -> str:
    """Center-crop, resize, and mask an uploaded image into a circular PNG data URL."""
    image = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    width, height = image.size
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    image = image.crop((left, top, left + side, top + side)).resize((size, size), Image.Resampling.LANCZOS)

    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size - 1, size - 1), fill=255)

    output = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    output.paste(image, (0, 0), mask=mask)

    buffer = io.BytesIO()
    output.save(buffer, format="PNG", optimize=True)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"
