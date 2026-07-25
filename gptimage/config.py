"""Configuration module for the GPT Image CLI (OpenAI GPT Image models).

Uses an aspect-ratio + resolution vocabulary (-a / -r) rather than raw pixel sizes,
so the same flags work across models that accept arbitrary dimensions (gpt-image-2)
and models limited to three fixed sizes (gpt-image-1 / 1.5 / mini).
"""

from __future__ import annotations

import math
import os
from enum import StrEnum
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Configuration
OPENAI_API_KEY_ENV = "OPENAI_API_KEY"

# Image generation model. Default = current flagship (gpt-image-2, 2026).
# Alternatives selectable via --model: gpt-image-1.5, gpt-image-1-mini, gpt-image-1.
MODEL_NAME = "gpt-image-2"
# Vision model used by the `describe` command for image analysis. gpt-5 (2025-08) is
# superseded; gpt-5.4-mini is the cheap current vision model ($0.75/$4.50 per 1M).
DESCRIBE_MODEL_NAME = "gpt-5.4-mini"

# Per-1M-token prices (USD), source: https://developers.openai.com/api/docs/pricing
# (verified 2026-07-25). Images are billed as tokens: input (text + any reference
# image) plus image output tokens.
MODEL_PRICING: dict[str, dict[str, float]] = {
    "gpt-image-2": {"in": 8.0, "out": 30.0},
    "gpt-image-1.5": {"in": 8.0, "out": 32.0},
    "gpt-image-1-mini": {"in": 2.5, "out": 8.0},
    "gpt-image-1": {"in": 10.0, "out": 40.0},
}

# Published per-image prices at 1024x1024, used when the API returns no usage data.
# gpt-image-2 figures are the official ones from the image generation guide;
# the others are derived from the token rates above and are rough.
# Source: https://developers.openai.com/api/docs/guides/image-generation
FALLBACK_COST: dict[str, dict[str, float]] = {
    "gpt-image-2": {"low": 0.006, "medium": 0.053, "high": 0.211},
    "gpt-image-1.5": {"low": 0.009, "medium": 0.034, "high": 0.133},
    "gpt-image-1-mini": {"low": 0.005, "medium": 0.011, "high": 0.036},
    "gpt-image-1": {"low": 0.011, "medium": 0.042, "high": 0.167},
}

VALID_MODELS: set[str] = set(MODEL_PRICING.keys())

# gpt-image-2 rejects background="transparent" outright: "gpt-image-2 doesn't
# currently support transparent backgrounds." The older models still accept it.
MODELS_WITHOUT_TRANSPARENCY: frozenset[str] = frozenset({"gpt-image-2"})

# HTTP status codes worth retrying: 429 = rate limit, 5xx = transient server-side
# failures (OpenAI's image endpoint does return sporadic 500s). Everything else —
# 400 invalid request, 401 bad key, 403, 404 unknown model — fails identically on
# every attempt, so retrying only wastes time and quota.
RETRYABLE_STATUS_CODES: frozenset[int] = frozenset({429, 500, 502, 503, 504})

# Default values. quality=high and format=png by default so the first result is the
# best the model can do; drop to --quality low for cheap drafts (see pricing below).
DEFAULT_MODEL = MODEL_NAME
DEFAULT_ASPECT_RATIO = "1:1"
DEFAULT_RESOLUTION = "1K"
DEFAULT_QUALITY = "high"
DEFAULT_BACKGROUND = "auto"
DEFAULT_OUTPUT_FORMAT = "png"
DEFAULT_OUTPUT_DIR = Path("./output")
DEFAULT_DELAY_SECONDS = 1.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_BASE_DELAY = 2.0
DEFAULT_RETRY_MAX_DELAY = 60.0

# gpt-image-2 supports arbitrary sizes (divisible by 16, ratio 1:3..3:1) but with
# a MINIMUM pixel budget (~1 MP) and a 3840x2160 bounding box. So we size by target
# AREA (not long edge) — otherwise wide ratios at 1K fall below the minimum (e.g.
# 1024x576 = 0.59 MP is rejected).
RESOLUTION_AREA: dict[str, int] = {"1K": 1_150_000, "2K": 4_000_000, "4K": 8_200_000}
MIN_PIXELS = 1_050_000  # gpt-image-2 minimum pixel budget (~1 MP)
MAX_LONG_EDGE = 3840
MAX_SHORT_EDGE = 2160


class AspectRatio(StrEnum):
    """Supported aspect ratios."""

    SQUARE = "1:1"
    PORTRAIT_2_3 = "2:3"
    LANDSCAPE_3_2 = "3:2"
    PORTRAIT_3_4 = "3:4"
    LANDSCAPE_4_3 = "4:3"
    PORTRAIT_4_5 = "4:5"
    LANDSCAPE_5_4 = "5:4"
    PORTRAIT_9_16 = "9:16"
    LANDSCAPE_16_9 = "16:9"
    ULTRAWIDE = "21:9"


class Resolution(StrEnum):
    """Supported resolution targets (mapped to concrete pixel sizes)."""

    RES_1K = "1K"
    RES_2K = "2K"
    RES_4K = "4K"


class Quality(StrEnum):
    """OpenAI GPT Image quality tiers."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    AUTO = "auto"


class Background(StrEnum):
    """Background handling. transparent requires png/webp output."""

    AUTO = "auto"
    TRANSPARENT = "transparent"
    OPAQUE = "opaque"


class OutputFormat(StrEnum):
    """Supported output image formats."""

    PNG = "png"
    WEBP = "webp"
    JPEG = "jpeg"


VALID_ASPECT_RATIOS: set[str] = {r.value for r in AspectRatio}
VALID_RESOLUTIONS: set[str] = {r.value for r in Resolution}
VALID_QUALITIES: set[str] = {q.value for q in Quality}
VALID_BACKGROUNDS: set[str] = {b.value for b in Background}
VALID_OUTPUT_FORMATS: set[str] = {f.value for f in OutputFormat}

# Supported image formats for reference images
SUPPORTED_IMAGE_FORMATS: frozenset[str] = frozenset({".jpg", ".jpeg", ".png", ".webp"})

# Type aliases
AspectRatioType = Literal["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"]
ResolutionType = Literal["1K", "2K", "4K"]
QualityType = Literal["low", "medium", "high", "auto"]
OutputFormatType = Literal["png", "webp", "jpeg"]


class ConfigError(Exception):
    """Configuration-related errors."""


def get_api_key() -> str:
    """Get the OpenAI API key from environment.

    Raises:
        ConfigError: If the API key is not set.
    """
    api_key = os.environ.get(OPENAI_API_KEY_ENV)
    if not api_key:
        raise ConfigError(
            f"Missing API key. Set the {OPENAI_API_KEY_ENV} environment variable "
            f"or add it to a .env file."
        )
    return api_key


def _round16(value: float) -> int:
    """Round to nearest multiple of 16, minimum 16."""
    return max(16, int(round(value / 16.0)) * 16)


def aspect_res_to_size(aspect_ratio: str, resolution: str) -> str:
    """Convert an aspect ratio + resolution target into a concrete WxH size.

    Sizes by target AREA (so wide ratios stay above the ~1 MP minimum), keeps the
    requested aspect ratio, fits inside the 3840x2160 box, snaps to a multiple of
    16 (API requirement), and guarantees the result is above the minimum pixel
    budget whenever the box has room.

    Examples:
        ("1:1", "1K")  -> "1072x1072"
        ("16:9", "1K") -> "1424x800"    (1.14 MP, above the minimum)
        ("16:9", "4K") -> "3824x2144"
        ("1:1", "4K")  -> "2160x2160"   (fit inside the box)
    """
    wr_str, hr_str = aspect_ratio.split(":")
    wr, hr = float(wr_str), float(hr_str)
    ratio = wr / hr

    landscape = wr >= hr
    box_w, box_h = (MAX_LONG_EDGE, MAX_SHORT_EDGE) if landscape else (MAX_SHORT_EDGE, MAX_LONG_EDGE)

    # Size by area, keeping the aspect ratio.
    h = math.sqrt(RESOLUTION_AREA[resolution] / ratio)
    w = ratio * h

    # Fit inside the bounding box, then snap to /16.
    scale = min(box_w / w, box_h / h, 1.0)
    wi, hi = _round16(w * scale), _round16(h * scale)

    # Rounding must never exceed the box.
    while wi > box_w:
        wi -= 16
    while hi > box_h:
        hi -= 16

    # Ensure we stay above the minimum pixel budget while the box has room.
    while wi * hi < MIN_PIXELS and (wi < box_w or hi < box_h):
        if wi < box_w:
            wi += 16
        if hi < box_h:
            hi += 16

    return f"{wi}x{hi}"


def validate_aspect_ratio(aspect_ratio: str) -> str:
    if aspect_ratio not in VALID_ASPECT_RATIOS:
        valid = ", ".join(sorted(VALID_ASPECT_RATIOS))
        raise ValueError(f"Invalid aspect ratio '{aspect_ratio}'. Valid options: {valid}")
    return aspect_ratio


def validate_resolution(resolution: str) -> str:
    if resolution not in VALID_RESOLUTIONS:
        valid = ", ".join(sorted(VALID_RESOLUTIONS))
        raise ValueError(f"Invalid resolution '{resolution}'. Valid options: {valid}")
    return resolution


def validate_quality(quality: str) -> str:
    if quality not in VALID_QUALITIES:
        valid = ", ".join(sorted(VALID_QUALITIES))
        raise ValueError(f"Invalid quality '{quality}'. Valid options: {valid}")
    return quality


def validate_background(background: str) -> str:
    if background not in VALID_BACKGROUNDS:
        valid = ", ".join(sorted(VALID_BACKGROUNDS))
        raise ValueError(f"Invalid background '{background}'. Valid options: {valid}")
    return background


def validate_output_format(output_format: str) -> str:
    if output_format not in VALID_OUTPUT_FORMATS:
        valid = ", ".join(sorted(VALID_OUTPUT_FORMATS))
        raise ValueError(f"Invalid output format '{output_format}'. Valid options: {valid}")
    return output_format


def validate_model(model: str) -> str:
    if model not in VALID_MODELS:
        valid = ", ".join(sorted(VALID_MODELS))
        raise ValueError(f"Invalid model '{model}'. Valid options: {valid}")
    return model


def ensure_output_dir(output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def validate_reference_path(reference_path: Path) -> Path:
    if not reference_path.exists():
        raise ValueError(f"Reference image not found: {reference_path}")
    if not reference_path.is_file():
        raise ValueError(f"Reference path is not a file: {reference_path}")
    suffix = reference_path.suffix.lower()
    if suffix not in SUPPORTED_IMAGE_FORMATS:
        valid = ", ".join(sorted(SUPPORTED_IMAGE_FORMATS))
        raise ValueError(f"Unsupported image format '{suffix}'. Supported formats: {valid}")
    return reference_path


def validate_background_for_model(background: str, model: str, output_format: str) -> None:
    """
    Check that the requested background is actually possible for this model/format.

    Two independent constraints:
      1. gpt-image-2 does not support transparency at all.
      2. Transparency needs an alpha-capable container, so jpeg is out.

    Args:
        background: "auto", "transparent" or "opaque".
        model: The target model.
        output_format: "png", "webp" or "jpeg".

    Raises:
        ValueError: If the combination is impossible, with the workaround spelled out.
    """
    if background != "transparent":
        return

    if model in MODELS_WITHOUT_TRANSPARENCY:
        alternatives = ", ".join(sorted(VALID_MODELS - MODELS_WITHOUT_TRANSPARENCY))
        raise ValueError(
            f"{model} does not support transparent backgrounds. "
            f"Either use a model that does ({alternatives}) via --model, "
            f"or generate on a flat background and remove it afterwards."
        )

    if output_format == "jpeg":
        raise ValueError(
            "Transparent background requires png or webp output (jpeg has no alpha channel)."
        )


def estimate_cost(
    model: str,
    quality: str,
    usage: dict | None = None,
) -> tuple[float, str]:
    """Estimate the USD cost of a generation.

    Prefers real token usage returned by the API; falls back to a per-image
    table keyed by (model, quality) at ~1024x1024.

    Returns:
        (cost_usd, source_label)
    """
    if usage:
        rates = MODEL_PRICING.get(model, MODEL_PRICING[DEFAULT_MODEL])
        in_tok = usage.get("input_tokens", 0) or 0
        out_tok = usage.get("output_tokens", 0) or 0
        cost = (in_tok * rates["in"] + out_tok * rates["out"]) / 1_000_000
        return cost, f"actual ({in_tok} in + {out_tok} out tokens)"

    q = quality if quality != "auto" else "high"
    table = FALLBACK_COST.get(model, FALLBACK_COST[DEFAULT_MODEL])
    return table.get(q, table["high"]), "estimate (no usage data, ~1024x1024)"


def is_retryable_error(error: Exception) -> bool:
    """
    Decide whether a failed API call is worth retrying.

    Retries rate limits (429), transient server errors (5xx) and network-level
    failures. Hard errors — invalid request, bad key, unknown model — are not
    retried, because the same request fails identically every time.

    The OpenAI SDK exposes the code as `.status_code` on APIStatusError; some
    exception types carry `.code` instead, so both are checked.

    Args:
        error: The exception raised by the API call.

    Returns:
        True if the call should be retried.
    """
    for attr in ("status_code", "code"):
        code = getattr(error, attr, None)
        if isinstance(code, int):
            return code in RETRYABLE_STATUS_CODES

    transient_markers = ("timeout", "timed out", "connection", "temporarily unavailable")
    message = str(error).lower()
    return any(marker in message for marker in transient_markers)
