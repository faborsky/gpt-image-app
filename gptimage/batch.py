"""Batch processing module for the GPT Image CLI."""

from __future__ import annotations

import json
import signal
import time
from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)

from gptimage.config import (
    DEFAULT_ASPECT_RATIO,
    DEFAULT_BACKGROUND,
    DEFAULT_OUTPUT_FORMAT,
    DEFAULT_QUALITY,
    DEFAULT_RESOLUTION,
    SUPPORTED_IMAGE_FORMATS,
    VALID_ASPECT_RATIOS,
    VALID_BACKGROUNDS,
    VALID_OUTPUT_FORMATS,
    VALID_QUALITIES,
    VALID_RESOLUTIONS,
)
from gptimage.generator import GenerationResult, ImageGenerator
from gptimage.utils import truncate_prompt

console = Console()


@dataclass
class JobConfig:
    """Configuration for a single generation job."""

    prompt: str
    aspect_ratio: str = DEFAULT_ASPECT_RATIO
    resolution: str = DEFAULT_RESOLUTION
    quality: str = DEFAULT_QUALITY
    background: str = DEFAULT_BACKGROUND
    output_name: str | None = None
    reference_path: Path | None = None
    output_format: str = DEFAULT_OUTPUT_FORMAT


@dataclass
class BatchConfig:
    """Configuration for a batch of jobs."""

    jobs: list[JobConfig] = field(default_factory=list)


@dataclass
class BatchResult:
    """Result summary of a batch run."""

    total: int = 0
    successful: int = 0
    failed: int = 0
    interrupted: bool = False
    total_cost_usd: float = 0.0
    results: list[tuple[JobConfig, GenerationResult]] = field(default_factory=list)


class BatchProcessor:
    """Handles batch processing of image generation jobs."""

    def __init__(
        self,
        generator: ImageGenerator,
        output_dir: Path,
        delay: float,
        out: Console | None = None,
    ) -> None:
        self._generator = generator
        self._output_dir = output_dir
        self._delay = delay
        self._console = out or console
        self._interrupted = False
        signal.signal(signal.SIGINT, self._handle_interrupt)

    def _handle_interrupt(self, signum: int, frame: object) -> None:
        self._interrupted = True
        self._console.print("\n[yellow]Interrupt received, finishing current job...[/yellow]")

    def process(self, batch_config: BatchConfig) -> BatchResult:
        result = BatchResult(total=len(batch_config.jobs))
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=self._console,
        ) as progress:
            task = progress.add_task("Processing jobs", total=len(batch_config.jobs))
            for i, job in enumerate(batch_config.jobs):
                if self._interrupted:
                    result.interrupted = True
                    self._console.print(
                        f"[yellow]Stopped at job {i + 1}/{len(batch_config.jobs)}[/yellow]"
                    )
                    break

                progress.update(
                    task,
                    description=(
                        f"[{i + 1}/{len(batch_config.jobs)}] {truncate_prompt(job.prompt, 40)}"
                    ),
                )

                gen_result = self._generator.generate(
                    prompt=job.prompt,
                    aspect_ratio=job.aspect_ratio,
                    resolution=job.resolution,
                    output_dir=self._output_dir,
                    custom_name=job.output_name,
                    reference_path=job.reference_path,
                    output_format=job.output_format,
                    quality=job.quality,
                    background=job.background,
                )
                result.results.append((job, gen_result))

                if gen_result.success:
                    result.successful += 1
                    if gen_result.cost_usd:
                        result.total_cost_usd += gen_result.cost_usd
                else:
                    result.failed += 1
                    self._console.print(
                        f"\n[red]Failed: {truncate_prompt(job.prompt, 30)} - "
                        f"{gen_result.error_message}[/red]"
                    )

                progress.advance(task)
                if i < len(batch_config.jobs) - 1 and not self._interrupted:
                    time.sleep(self._delay)
        return result


def parse_job_file(job_file: Path) -> BatchConfig:
    """Parse a batch job JSON file into a BatchConfig."""
    with open(job_file, encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("Job file must be a JSON object")
    if "jobs" not in data:
        raise ValueError("Job file must contain a 'jobs' array")

    defaults = data.get("defaults", {})
    d_aspect = defaults.get("aspect_ratio", DEFAULT_ASPECT_RATIO)
    d_resolution = defaults.get("resolution", DEFAULT_RESOLUTION)
    d_quality = defaults.get("quality", DEFAULT_QUALITY)
    d_background = defaults.get("background", DEFAULT_BACKGROUND)
    d_format = defaults.get("format", DEFAULT_OUTPUT_FORMAT)

    jobs: list[JobConfig] = []
    for i, job_data in enumerate(data["jobs"]):
        if not isinstance(job_data, dict):
            raise ValueError(f"Job {i + 1} must be an object")
        if "prompt" not in job_data:
            raise ValueError(f"Job {i + 1} missing required 'prompt' field")

        ref_path = Path(job_data["reference_path"]) if "reference_path" in job_data else None
        jobs.append(
            JobConfig(
                prompt=job_data["prompt"],
                aspect_ratio=job_data.get("aspect_ratio", d_aspect),
                resolution=job_data.get("resolution", d_resolution),
                quality=job_data.get("quality", d_quality),
                background=job_data.get("background", d_background),
                output_name=job_data.get("output_name"),
                reference_path=ref_path,
                output_format=job_data.get("format", d_format),
            )
        )
    return BatchConfig(jobs=jobs)


def validate_job_file(job_file: Path) -> list[str]:
    """Validate a batch job JSON file; return a list of error strings (empty if OK)."""
    errors: list[str] = []
    try:
        with open(job_file, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return [f"Invalid JSON: {e}"]
    except OSError as e:
        return [f"Cannot read file: {e}"]

    if not isinstance(data, dict):
        return ["Job file must be a JSON object"]
    if "jobs" not in data:
        return ["Missing required 'jobs' array"]
    if not isinstance(data["jobs"], list):
        return ["'jobs' must be an array"]

    defaults = data.get("defaults", {})
    if not isinstance(defaults, dict):
        errors.append("'defaults' must be an object")
    else:
        _check(errors, defaults, "aspect_ratio", VALID_ASPECT_RATIOS, "default ")
        _check(errors, defaults, "resolution", VALID_RESOLUTIONS, "default ")
        _check(errors, defaults, "quality", VALID_QUALITIES, "default ")
        _check(errors, defaults, "background", VALID_BACKGROUNDS, "default ")
        _check(errors, defaults, "format", VALID_OUTPUT_FORMATS, "default ")

    for i, job in enumerate(data["jobs"]):
        n = i + 1
        if not isinstance(job, dict):
            errors.append(f"Job {n}: must be an object")
            continue
        if "prompt" not in job:
            errors.append(f"Job {n}: missing required 'prompt' field")
        elif not isinstance(job["prompt"], str) or not job["prompt"].strip():
            errors.append(f"Job {n}: 'prompt' must be a non-empty string")

        _check(errors, job, "aspect_ratio", VALID_ASPECT_RATIOS, f"Job {n}: ")
        _check(errors, job, "resolution", VALID_RESOLUTIONS, f"Job {n}: ")
        _check(errors, job, "quality", VALID_QUALITIES, f"Job {n}: ")
        _check(errors, job, "background", VALID_BACKGROUNDS, f"Job {n}: ")
        _check(errors, job, "format", VALID_OUTPUT_FORMATS, f"Job {n}: ")

        if "output_name" in job and not isinstance(job["output_name"], str):
            errors.append(f"Job {n}: 'output_name' must be a string")

        if "reference_path" in job:
            if not isinstance(job["reference_path"], str):
                errors.append(f"Job {n}: 'reference_path' must be a string")
            else:
                ref_path = Path(job["reference_path"])
                if not ref_path.exists():
                    errors.append(f"Job {n}: reference image not found: {ref_path}")
                elif ref_path.suffix.lower() not in SUPPORTED_IMAGE_FORMATS:
                    valid = ", ".join(sorted(SUPPORTED_IMAGE_FORMATS))
                    errors.append(f"Job {n}: unsupported reference format. Valid: {valid}")
    return errors


def _check(errors: list[str], obj: dict, key: str, valid: set[str], prefix: str) -> None:
    if key in obj and obj[key] not in valid:
        errors.append(f"{prefix}invalid {key} '{obj[key]}'")


def run_batch(
    job_file: Path,
    generator: ImageGenerator,
    output_dir: Path,
    delay: float,
    json_output: bool = False,
) -> bool:
    """
    Validate, parse, and process a batch job file. Returns True on full success.

    With json_output the summary goes to stdout as JSON and all prose to stderr.
    """
    out = Console(stderr=True) if json_output else console

    def fail(message: str, errors: list[str] | None = None) -> bool:
        if json_output:
            payload: dict[str, object] = {"success": False, "error": message}
            if errors:
                payload["validation_errors"] = errors
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            out.print(f"[red]{message}[/red]")
            for error in errors or []:
                out.print(f"  - {error}")
        return False

    errors = validate_job_file(job_file)
    if errors:
        return fail("Validation errors", errors)

    try:
        batch_config = parse_job_file(job_file)
    except ValueError as e:
        return fail(f"Error parsing job file: {e}")

    if not batch_config.jobs:
        if json_output:
            print(json.dumps({"success": True, "total": 0, "cost_usd": 0.0}, indent=2))
        else:
            out.print("[yellow]No jobs to process[/yellow]")
        return True

    out.print(f"[blue]Processing {len(batch_config.jobs)} jobs ({generator.model})...[/blue]")
    result = BatchProcessor(
        generator=generator, output_dir=output_dir, delay=delay, out=out
    ).process(batch_config)
    ok = result.failed == 0 and not result.interrupted

    if json_output:
        print(
            json.dumps(
                {
                    "success": ok,
                    "model": generator.model,
                    "total": result.total,
                    "successful": result.successful,
                    "failed": result.failed,
                    "interrupted": result.interrupted,
                    "cost_usd": round(result.total_cost_usd, 4),
                    "images": [
                        {
                            "prompt": job.prompt,
                            "output_path": str(res.output_path) if res.output_path else None,
                            "aspect_ratio": job.aspect_ratio,
                            "resolution": job.resolution,
                            "quality": job.quality,
                            "size": res.size,
                            "success": res.success,
                            "cost_usd": res.cost_usd,
                            "error": res.error_message,
                        }
                        for job, res in result.results
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return ok

    out.print()
    if result.interrupted:
        out.print("[yellow]Batch interrupted[/yellow]")
    out.print(f"[green]Successful: {result.successful}[/green]")
    if result.failed > 0:
        out.print(f"[red]Failed: {result.failed}[/red]")
    if result.total_cost_usd:
        out.print(f"[dim]Total cost: ${result.total_cost_usd:.4f}[/dim]")
    return ok
