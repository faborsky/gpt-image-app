"""Core image generation module using the OpenAI Image API."""

from __future__ import annotations

import base64
import random
import time
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path

from openai import OpenAI
from rich.console import Console

from gptimage.config import (
    DEFAULT_BACKGROUND,
    DEFAULT_MAX_RETRIES,
    DEFAULT_MODEL,
    DEFAULT_OUTPUT_FORMAT,
    DEFAULT_QUALITY,
    DEFAULT_RETRY_BASE_DELAY,
    DEFAULT_RETRY_MAX_DELAY,
    aspect_res_to_size,
    estimate_cost,
    get_api_key,
    is_retryable_error,
    validate_aspect_ratio,
    validate_background,
    validate_background_for_model,
    validate_input_fidelity_for_model,
    validate_model,
    validate_output_format,
    validate_quality,
    validate_reference_paths,
    validate_resolution,
)
from gptimage.utils import get_output_path

# Retry notices are progress diagnostics, not results — they always belong on
# stderr, so that `--json` keeps stdout a clean, parseable payload.
console = Console(stderr=True)

# Sizes the non-flagship models accept (gpt-image-1 / 1.5 / mini): only these
# three plus "auto". gpt-image-2 accepts arbitrary WxH.
_FIXED_SIZES = {"square": "1024x1024", "landscape": "1536x1024", "portrait": "1024x1536"}


@dataclass
class GenerationResult:
    """Result of an image generation attempt."""

    success: bool
    output_path: Path | None = None
    error_message: str | None = None
    cost_usd: float | None = None
    cost_source: str | None = None
    size: str | None = None
    attempts: int = 0
    reference_count: int = 0
    input_fidelity: str | None = None


class ImageGenerationError(Exception):
    """Error during image generation."""


def _snap_size_for_model(size: str, model: str) -> str:
    """gpt-image-2 takes any WxH; other models only 3 fixed sizes. Snap to nearest."""
    if model == "gpt-image-2":
        return size
    w, h = (int(x) for x in size.split("x"))
    ratio = w / h
    if 0.9 <= ratio <= 1.1:
        return _FIXED_SIZES["square"]
    return _FIXED_SIZES["landscape"] if ratio > 1.1 else _FIXED_SIZES["portrait"]


class ImageGenerator:
    """Wrapper for the OpenAI Image API with retry logic and cost reporting."""

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_base_delay: float = DEFAULT_RETRY_BASE_DELAY,
    ) -> None:
        self._api_key = get_api_key()
        self._client = OpenAI(api_key=self._api_key)
        self._model = validate_model(model)
        self._max_retries = max_retries
        self._retry_base_delay = retry_base_delay

    @property
    def model(self) -> str:
        return self._model

    def generate(
        self,
        prompt: str,
        aspect_ratio: str,
        resolution: str,
        output_dir: Path,
        custom_name: str | None = None,
        reference_paths: list[Path] | None = None,
        output_format: str = DEFAULT_OUTPUT_FORMAT,
        quality: str = DEFAULT_QUALITY,
        background: str = DEFAULT_BACKGROUND,
        input_fidelity: str | None = None,
    ) -> GenerationResult:
        """
        Generate a single image, optionally guided by one or more reference images.

        Passing several references is how compositing works — e.g. one image of a
        product plus one of the target scene. They are billed as input image tokens,
        so more references means a higher cost per call.
        """
        references = list(reference_paths or [])

        # Validate parameters
        try:
            validate_aspect_ratio(aspect_ratio)
            validate_resolution(resolution)
            validate_output_format(output_format)
            validate_quality(quality)
            validate_background(background)
            if references:
                validate_reference_paths(references)
        except ValueError as e:
            return GenerationResult(success=False, error_message=str(e))

        # Catch impossible parameter/model combinations before spending a call.
        try:
            validate_background_for_model(background, self._model, output_format)
            validate_input_fidelity_for_model(input_fidelity, self._model)
        except ValueError as e:
            return GenerationResult(success=False, error_message=str(e))

        if input_fidelity and not references:
            return GenerationResult(
                success=False,
                error_message=(
                    "input_fidelity only applies when editing reference images. "
                    "Pass at least one reference, or drop the flag."
                ),
            )

        output_dir.mkdir(parents=True, exist_ok=True)

        size = _snap_size_for_model(aspect_res_to_size(aspect_ratio, resolution), self._model)

        last_error: str | None = None
        for attempt in range(self._max_retries):
            try:
                result = self._generate_with_api(
                    prompt=prompt,
                    size=size,
                    output_dir=output_dir,
                    custom_name=custom_name,
                    reference_paths=references,
                    output_format=output_format,
                    quality=quality,
                    background=background,
                    aspect_ratio=aspect_ratio,
                    resolution=resolution,
                    input_fidelity=input_fidelity,
                )
                result.attempts = attempt + 1
                return result
            except Exception as e:  # noqa: BLE001 - classified below, then re-surfaced
                last_error = str(e)
                low = last_error.lower()

                # Moderation is a verdict on the prompt — retrying identical words
                # produces the identical refusal.
                if "content" in low and ("policy" in low or "moderation" in low or "safety" in low):
                    return GenerationResult(
                        success=False,
                        error_message=f"Content filtered: {last_error}",
                        attempts=attempt + 1,
                    )

                # Hard errors fail the same way every time — surface immediately.
                if not is_retryable_error(e):
                    return GenerationResult(
                        success=False, error_message=last_error, attempts=attempt + 1
                    )

                if attempt < self._max_retries - 1:
                    delay = self._backoff_delay(attempt)
                    console.print(
                        f"[yellow]Attempt {attempt + 1} failed ({last_error[:80]}), "
                        f"retrying in {delay:.1f}s...[/yellow]"
                    )
                    time.sleep(delay)

        return GenerationResult(
            success=False,
            error_message=f"Failed after {self._max_retries} attempts: {last_error}",
            attempts=self._max_retries,
        )

    def _backoff_delay(self, attempt: int) -> float:
        """
        Exponential backoff with jitter, capped at DEFAULT_RETRY_MAX_DELAY.

        OpenAI explicitly recommends jitter: without it, parallel runs that hit the
        same rate limit retry in lockstep and collide again.

        Args:
            attempt: Zero-based attempt index.

        Returns:
            Delay in seconds.
        """
        delay = min(self._retry_base_delay * (2**attempt), DEFAULT_RETRY_MAX_DELAY)
        return delay * (0.5 + random.random() * 0.5)

    def _generate_with_api(
        self,
        prompt: str,
        size: str,
        output_dir: Path,
        custom_name: str | None,
        reference_paths: list[Path],
        output_format: str,
        quality: str,
        background: str,
        aspect_ratio: str,
        resolution: str,
        input_fidelity: str | None = None,
    ) -> GenerationResult:
        common: dict = {
            "model": self._model,
            "prompt": prompt,
            "size": size,
            "quality": quality,
            "background": background,
            "output_format": output_format,
            "n": 1,
        }

        if reference_paths:
            # The edit endpoint takes a list of file handles — that list is what makes
            # compositing possible (e.g. product + target scene). ExitStack closes every
            # handle even if the call raises, which matters because retries reopen them.
            with ExitStack() as stack:
                handles = [stack.enter_context(open(path, "rb")) for path in reference_paths]
                if input_fidelity:
                    common["input_fidelity"] = input_fidelity
                response = self._client.images.edit(image=handles, **common)
        else:
            response = self._client.images.generate(**common)

        if not response.data or response.data[0].b64_json is None:
            raise ImageGenerationError("No image data in API response.")

        image_bytes = base64.b64decode(response.data[0].b64_json)

        usage = None
        if getattr(response, "usage", None) is not None:
            u = response.usage
            usage = {
                "input_tokens": getattr(u, "input_tokens", 0),
                "output_tokens": getattr(u, "output_tokens", 0),
            }
        cost, source = estimate_cost(self._model, quality, usage)

        output_path = get_output_path(
            output_dir=output_dir,
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            custom_name=custom_name,
            output_format=output_format,
        )
        output_path.write_bytes(image_bytes)

        return GenerationResult(
            success=True,
            output_path=output_path,
            cost_usd=cost,
            cost_source=source,
            size=size,
            reference_count=len(reference_paths),
            input_fidelity=input_fidelity,
        )
