"""CLI entry point for the GPT Image CLI (OpenAI GPT Image models)."""

from __future__ import annotations

import base64
import json as jsonlib
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from gptimage import __version__
from gptimage.config import (
    DEFAULT_ASPECT_RATIO,
    DEFAULT_BACKGROUND,
    DEFAULT_DELAY_SECONDS,
    DEFAULT_MODEL,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_OUTPUT_FORMAT,
    DEFAULT_QUALITY,
    DEFAULT_RESOLUTION,
    SUPPORTED_IMAGE_FORMATS,
    VALID_ASPECT_RATIOS,
    VALID_BACKGROUNDS,
    VALID_MODELS,
    VALID_OUTPUT_FORMATS,
    VALID_QUALITIES,
    VALID_RESOLUTIONS,
    ConfigError,
    aspect_res_to_size,
)
from gptimage.generator import ImageGenerator

app = typer.Typer(
    name="gptimage",
    help="CLI for image generation via OpenAI GPT Image models (gpt-image-2 and siblings).",
    add_completion=False,
)
console = Console()

# Human-readable output goes to stderr so that --json keeps stdout clean and parseable.
err_console = Console(stderr=True)


def emit_json(payload: dict[str, object]) -> None:
    """Print a machine-readable result to stdout."""
    print(jsonlib.dumps(payload, ensure_ascii=False, indent=2))


def version_callback(value: bool) -> None:
    """Print the version and exit."""
    if value:
        console.print(f"gptimage {__version__} (default model: {DEFAULT_MODEL})")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-V",
            help="Show the version and exit",
            callback=version_callback,
            is_eager=True,
        ),
    ] = False,
) -> None:
    """CLI for image generation via OpenAI GPT Image models."""


def _validate_choice(value: str, valid: set[str], label: str) -> str:
    if value not in valid:
        raise typer.BadParameter(f"Invalid {label}. Valid options: {', '.join(sorted(valid))}")
    return value


def validate_aspect_ratio_callback(value: str) -> str:
    return _validate_choice(value, VALID_ASPECT_RATIOS, "aspect ratio")


def validate_resolution_callback(value: str) -> str:
    return _validate_choice(value, VALID_RESOLUTIONS, "resolution")


def validate_quality_callback(value: str) -> str:
    return _validate_choice(value, VALID_QUALITIES, "quality")


def validate_background_callback(value: str) -> str:
    return _validate_choice(value, VALID_BACKGROUNDS, "background")


def validate_format_callback(value: str) -> str:
    return _validate_choice(value, VALID_OUTPUT_FORMATS, "output format")


def validate_model_callback(value: str) -> str:
    return _validate_choice(value, VALID_MODELS, "model")


def validate_reference_callback(value: Path | None) -> Path | None:
    if value is None:
        return None
    if not value.exists():
        raise typer.BadParameter(f"Reference image not found: {value}")
    if not value.is_file():
        raise typer.BadParameter(f"Reference path is not a file: {value}")
    if value.suffix.lower() not in SUPPORTED_IMAGE_FORMATS:
        valid = ", ".join(sorted(SUPPORTED_IMAGE_FORMATS))
        raise typer.BadParameter(f"Unsupported image format. Valid formats: {valid}")
    return value


@app.command()
def generate(
    prompt: Annotated[str, typer.Argument(help="Text prompt for image generation")],
    aspect: Annotated[
        str,
        typer.Option("--aspect", "-a", help="Aspect ratio (1:1, 16:9, 9:16, 4:5, 21:9, ...)",
                     callback=validate_aspect_ratio_callback),
    ] = DEFAULT_ASPECT_RATIO,
    resolution: Annotated[
        str,
        typer.Option("--resolution", "-r", help="Resolution target (1K, 2K, 4K)",
                     callback=validate_resolution_callback),
    ] = DEFAULT_RESOLUTION,
    quality: Annotated[
        str,
        typer.Option("--quality", "-q", help="Quality (low, medium, high, auto)",
                     callback=validate_quality_callback),
    ] = DEFAULT_QUALITY,
    model: Annotated[
        str,
        typer.Option(
            "--model", "-m",
            help="Model (gpt-image-2, gpt-image-1.5, gpt-image-1-mini, gpt-image-1)",
            callback=validate_model_callback,
        ),
    ] = DEFAULT_MODEL,
    background: Annotated[
        str,
        typer.Option("--background", "-b", help="Background (auto, transparent, opaque)",
                     callback=validate_background_callback),
    ] = DEFAULT_BACKGROUND,
    output: Annotated[
        Path, typer.Option("--output", "-o", help="Output directory"),
    ] = DEFAULT_OUTPUT_DIR,
    name: Annotated[
        str | None, typer.Option("--name", "-n", help="Custom filename (without extension)"),
    ] = None,
    format: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format (png, webp, jpeg)",
                     callback=validate_format_callback),
    ] = DEFAULT_OUTPUT_FORMAT,
    reference: Annotated[
        Path | None,
        typer.Option("--reference", "-ref", help="Reference image for edit/style guidance",
                     callback=validate_reference_callback),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit a machine-readable JSON result on stdout"),
    ] = False,
) -> None:
    """Generate a single image from a text prompt with optional reference image."""
    out = err_console if json_output else console

    try:
        generator = ImageGenerator(model=model)
    except ConfigError as e:
        if json_output:
            emit_json({"error": str(e)})
        else:
            console.print(f"[red]Configuration error: {e}[/red]")
        raise typer.Exit(code=1) from e

    size = aspect_res_to_size(aspect, resolution)
    out.print("[blue]Generating image (OpenAI GPT Image)...[/blue]")
    out.print(f"  Model: {model}")
    out.print(f"  Prompt: {prompt}")
    out.print(f"  Aspect / resolution: {aspect} @ {resolution}  ->  {size} px")
    out.print(f"  Quality: {quality}   Format: {format.upper()}   Background: {background}")
    if reference:
        out.print(f"  Reference: {reference}")

    result = generator.generate(
        prompt=prompt,
        aspect_ratio=aspect,
        resolution=resolution,
        output_dir=output,
        custom_name=name,
        reference_path=reference,
        output_format=format,
        quality=quality,
        background=background,
    )

    if result.success:
        if json_output:
            emit_json(
                {
                    "success": True,
                    "output_path": str(result.output_path),
                    "model": model,
                    "aspect_ratio": aspect,
                    "resolution": resolution,
                    "size": result.size,
                    "quality": quality,
                    "format": format,
                    "background": background,
                    "cost_usd": round(result.cost_usd, 4) if result.cost_usd is not None else None,
                    "cost_source": result.cost_source,
                    "attempts": result.attempts,
                }
            )
        else:
            console.print(f"[green]Image saved to: {result.output_path}[/green]")
            if result.cost_usd is not None:
                console.print(
                    f"[dim]Cost: ${result.cost_usd:.4f} — {result.cost_source}[/dim]"
                )
    else:
        if json_output:
            emit_json({"success": False, "error": result.error_message})
        else:
            console.print(f"[red]Generation failed: {result.error_message}[/red]")
        raise typer.Exit(code=1)


@app.command()
def batch(
    job_file: Annotated[Path, typer.Argument(help="Path to the batch job JSON file")],
    model: Annotated[
        str,
        typer.Option("--model", "-m", help="Model for all jobs", callback=validate_model_callback),
    ] = DEFAULT_MODEL,
    delay: Annotated[
        float, typer.Option("--delay", "-d", help="Delay between requests in seconds"),
    ] = DEFAULT_DELAY_SECONDS,
    output: Annotated[
        Path, typer.Option("--output", "-o", help="Output directory (overrides job file defaults)"),
    ] = DEFAULT_OUTPUT_DIR,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit a machine-readable JSON summary on stdout"),
    ] = False,
) -> None:
    """Run a batch job from a JSON file."""
    from gptimage.batch import run_batch

    if not job_file.exists():
        if json_output:
            emit_json({"error": f"Job file not found: {job_file}"})
        else:
            console.print(f"[red]Job file not found: {job_file}[/red]")
        raise typer.Exit(code=1)

    try:
        generator = ImageGenerator(model=model)
    except ConfigError as e:
        if json_output:
            emit_json({"error": str(e)})
        else:
            console.print(f"[red]Configuration error: {e}[/red]")
        raise typer.Exit(code=1) from e

    if not run_batch(
        job_file=job_file,
        generator=generator,
        output_dir=output,
        delay=delay,
        json_output=json_output,
    ):
        raise typer.Exit(code=1)


@app.command()
def validate(
    job_file: Annotated[Path, typer.Argument(help="Path to the batch job JSON file")],
) -> None:
    """Validate a batch job JSON file."""
    from gptimage.batch import validate_job_file

    if not job_file.exists():
        console.print(f"[red]Job file not found: {job_file}[/red]")
        raise typer.Exit(code=1)

    errors = validate_job_file(job_file)
    if errors:
        console.print("[red]Validation failed:[/red]")
        for error in errors:
            console.print(f"  - {error}")
        raise typer.Exit(code=1)
    console.print("[green]Validation passed![/green]")


@app.command()
def describe(
    image_path: Annotated[Path, typer.Argument(help="Path to the image to describe")],
    detailed: Annotated[
        bool,
        typer.Option("--detailed", "-d", help="More detailed description suitable as a prompt"),
    ] = False,
) -> None:
    """Analyze an image and generate a text description suitable as a prompt."""
    from openai import OpenAI

    from gptimage.config import DESCRIBE_MODEL_NAME, get_api_key

    if not image_path.exists():
        console.print(f"[red]Image not found: {image_path}[/red]")
        raise typer.Exit(code=1)
    if image_path.suffix.lower() not in SUPPORTED_IMAGE_FORMATS:
        valid = ", ".join(sorted(SUPPORTED_IMAGE_FORMATS))
        console.print(f"[red]Unsupported format. Valid: {valid}[/red]")
        raise typer.Exit(code=1)

    try:
        api_key = get_api_key()
    except ConfigError as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        raise typer.Exit(code=1) from e

    console.print(f"[blue]Analyzing image: {image_path}[/blue]")

    suffix = image_path.suffix.lower()
    mime = "jpeg" if suffix in {".jpg", ".jpeg"} else suffix.lstrip(".")
    data_uri = f"data:image/{mime};base64," + base64.b64encode(image_path.read_bytes()).decode()

    if detailed:
        instruction = (
            "Analyze this image in detail and create a comprehensive text description "
            "usable as a prompt for AI image generation. Include subject and composition, "
            "art style and technique, color palette and lighting, mood, background details, "
            "and notable textures. Write it as a single flowing paragraph."
        )
    else:
        instruction = (
            "Describe this image concisely, focusing on the main subject, style, and visual "
            "characteristics. Keep it under 100 words."
        )

    client = OpenAI(api_key=api_key)
    try:
        response = client.chat.completions.create(
            model=DESCRIBE_MODEL_NAME,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": instruction},
                        {"type": "image_url", "image_url": {"url": data_uri}},
                    ],
                }
            ],
        )
        description = response.choices[0].message.content
    except Exception as e:  # noqa: BLE001
        console.print(f"[red]Failed to analyze image: {e}[/red]")
        raise typer.Exit(code=1) from e

    console.print()
    console.print("[green]Description:[/green]")
    console.print(description)


if __name__ == "__main__":
    app()
