"""Offline OCR: screenshot of an SMS -> text, via Tesseract."""
from __future__ import annotations

import io

import pytesseract
from PIL import Image, ImageOps


def image_to_text(image_bytes: bytes) -> str:
    """Extract text from a screenshot. Returns "" on failure."""
    if not image_bytes:
        return ""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img = ImageOps.grayscale(img)
        # upscale small screenshots for better OCR accuracy
        if img.width < 1000:
            factor = 1000 // max(1, img.width) + 1
            img = img.resize((img.width * factor, img.height * factor))
        text = pytesseract.image_to_string(img, lang="eng")
        return (text or "").strip()
    except Exception:
        return ""
