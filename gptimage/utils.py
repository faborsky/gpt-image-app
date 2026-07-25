"""Utility functions for the GPT Image CLI."""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from pathlib import Path


def sanitize_filename(text: str, max_length: int = 50) -> str:
    """Sanitize text to be used as a filename."""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "_", text)
    text = text.strip("_")
    if len(text) > max_length:
        text = text[:max_length].rstrip("_")
    return text or "image"


def generate_filename(
    prompt: str,
    aspect_ratio: str,
    resolution: str,
    custom_name: str | None = None,
    output_format: str = "png",
) -> str:
    """Generate a filename for the output image.

    Prefixed with `gpt_` so GPT Image outputs stay identifiable when several image
    tools write into the same folder.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = sanitize_filename(custom_name) if custom_name else sanitize_filename(prompt)
    ratio_str = aspect_ratio.replace(":", "x")
    ext = "jpg" if output_format == "jpeg" else output_format
    return f"gpt_{base_name}_{ratio_str}_{resolution}_{timestamp}.{ext}"


def get_output_path(
    output_dir: Path,
    prompt: str,
    aspect_ratio: str,
    resolution: str,
    custom_name: str | None = None,
    output_format: str = "png",
) -> Path:
    """Get the full output path for an image."""
    filename = generate_filename(prompt, aspect_ratio, resolution, custom_name, output_format)
    return output_dir / filename


def truncate_prompt(prompt: str, max_length: int = 60) -> str:
    """Truncate a prompt for display purposes."""
    if len(prompt) <= max_length:
        return prompt
    return prompt[: max_length - 3] + "..."
