"""Tests for batch job parsing/validation and filename helpers. No API calls."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from gptimage.batch import parse_job_file, validate_job_file
from gptimage.utils import generate_filename, sanitize_filename


def write_job(tmp_path: Path, payload: object) -> Path:
    job_file = tmp_path / "job.json"
    job_file.write_text(json.dumps(payload), encoding="utf-8")
    return job_file


class TestValidateJobFile:
    def test_accepts_minimal_valid_file(self, tmp_path: Path) -> None:
        assert validate_job_file(write_job(tmp_path, {"jobs": [{"prompt": "a lake"}]})) == []

    def test_accepts_full_defaults_block(self, tmp_path: Path) -> None:
        job_file = write_job(
            tmp_path,
            {
                "defaults": {
                    "aspect_ratio": "16:9",
                    "resolution": "2K",
                    "quality": "medium",
                    "background": "opaque",
                    "format": "webp",
                },
                "jobs": [{"prompt": "a lake"}],
            },
        )
        assert validate_job_file(job_file) == []

    def test_reports_invalid_json(self, tmp_path: Path) -> None:
        job_file = tmp_path / "bad.json"
        job_file.write_text("{nope", encoding="utf-8")
        assert "Invalid JSON" in validate_job_file(job_file)[0]

    def test_requires_jobs_array(self, tmp_path: Path) -> None:
        assert validate_job_file(write_job(tmp_path, {})) == ["Missing required 'jobs' array"]

    def test_rejects_top_level_array(self, tmp_path: Path) -> None:
        assert validate_job_file(write_job(tmp_path, [])) == ["Job file must be a JSON object"]

    def test_requires_non_empty_prompt(self, tmp_path: Path) -> None:
        job_file = write_job(tmp_path, {"jobs": [{"prompt": "  "}]})
        assert any("non-empty string" in e for e in validate_job_file(job_file))

    def test_flags_the_offending_job_number(self, tmp_path: Path) -> None:
        job_file = write_job(tmp_path, {"jobs": [{"prompt": "ok"}, {"output_name": "x"}]})
        assert any("Job 2" in e for e in validate_job_file(job_file))

    def test_rejects_invalid_enum_values(self, tmp_path: Path) -> None:
        job_file = write_job(
            tmp_path,
            {
                "jobs": [
                    {
                        "prompt": "x",
                        "aspect_ratio": "7:3",
                        "resolution": "8K",
                        "quality": "ultra",
                        "background": "rainbow",
                        "format": "gif",
                    }
                ]
            },
        )
        errors = validate_job_file(job_file)
        for field in ("aspect_ratio", "resolution", "quality", "background", "format"):
            assert any(field in e for e in errors), f"{field} should be reported"

    def test_rejects_missing_reference_image(self, tmp_path: Path) -> None:
        job_file = write_job(tmp_path, {"jobs": [{"prompt": "x", "reference_path": "nope.png"}]})
        assert any("reference image not found" in e for e in validate_job_file(job_file))

    def test_accepts_existing_reference_image(self, tmp_path: Path) -> None:
        ref = tmp_path / "ref.png"
        ref.write_bytes(b"fake")
        job_file = write_job(tmp_path, {"jobs": [{"prompt": "x", "reference_path": str(ref)}]})
        assert validate_job_file(job_file) == []

    def test_validation_never_touches_the_network(self, tmp_path: Path, monkeypatch) -> None:
        # Guard the promise that `validate` is a free, offline dry run.
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        assert validate_job_file(write_job(tmp_path, {"jobs": [{"prompt": "x"}]})) == []


class TestParseJobFile:
    def test_jobs_inherit_defaults(self, tmp_path: Path) -> None:
        job_file = write_job(
            tmp_path,
            {
                "defaults": {"aspect_ratio": "21:9", "resolution": "4K", "quality": "low"},
                "jobs": [{"prompt": "a dune"}],
            },
        )
        job = parse_job_file(job_file).jobs[0]
        assert (job.aspect_ratio, job.resolution, job.quality) == ("21:9", "4K", "low")

    def test_per_job_values_override_defaults(self, tmp_path: Path) -> None:
        job_file = write_job(
            tmp_path,
            {
                "defaults": {"quality": "low"},
                "jobs": [{"prompt": "a dune", "quality": "high"}],
            },
        )
        assert parse_job_file(job_file).jobs[0].quality == "high"

    def test_library_defaults_apply_without_a_defaults_block(self, tmp_path: Path) -> None:
        job = parse_job_file(write_job(tmp_path, {"jobs": [{"prompt": "x"}]})).jobs[0]
        assert (job.aspect_ratio, job.resolution, job.quality, job.output_format) == (
            "1:1",
            "1K",
            "high",
            "png",
        )

    def test_raises_on_missing_prompt(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="missing required 'prompt'"):
            parse_job_file(write_job(tmp_path, {"jobs": [{"output_name": "x"}]}))


class TestFilenames:
    def test_outputs_are_prefixed_to_stay_identifiable(self) -> None:
        assert generate_filename("a lake", "1:1", "1K").startswith("gpt_")

    def test_embeds_ratio_and_resolution(self) -> None:
        assert "_16x9_2K_" in generate_filename("a lake", "16:9", "2K")

    def test_jpeg_maps_to_jpg(self) -> None:
        assert generate_filename("x", "1:1", "1K", output_format="jpeg").endswith(".jpg")

    def test_strips_diacritics(self) -> None:
        assert sanitize_filename("Příšerně žluťoučký") == "priserne_zlutoucky"

    def test_custom_name_wins_over_prompt(self) -> None:
        assert generate_filename("long prompt", "1:1", "1K", custom_name="hero").startswith(
            "gpt_hero_"
        )


class TestMultiReferenceJobs:
    """reference_path stays backward compatible; lists enable compositing."""

    def test_single_string_still_works(self, tmp_path: Path) -> None:
        # Job files written for 1.0.x must keep parsing unchanged.
        ref = tmp_path / "ref.png"
        ref.write_bytes(b"fake")
        job_file = write_job(tmp_path, {"jobs": [{"prompt": "x", "reference_path": str(ref)}]})
        assert validate_job_file(job_file) == []
        assert parse_job_file(job_file).jobs[0].reference_paths == [ref]

    def test_list_under_reference_path(self, tmp_path: Path) -> None:
        refs = []
        for name in ("product.png", "scene.png"):
            p = tmp_path / name
            p.write_bytes(b"fake")
            refs.append(p)
        job_file = write_job(
            tmp_path, {"jobs": [{"prompt": "x", "reference_path": [str(r) for r in refs]}]}
        )
        assert validate_job_file(job_file) == []
        assert parse_job_file(job_file).jobs[0].reference_paths == refs

    def test_plural_key_works_too(self, tmp_path: Path) -> None:
        refs = []
        for name in ("a.png", "b.png"):
            p = tmp_path / name
            p.write_bytes(b"fake")
            refs.append(p)
        job_file = write_job(
            tmp_path, {"jobs": [{"prompt": "x", "reference_paths": [str(r) for r in refs]}]}
        )
        assert validate_job_file(job_file) == []
        assert parse_job_file(job_file).jobs[0].reference_paths == refs

    def test_no_reference_gives_empty_list(self, tmp_path: Path) -> None:
        job = parse_job_file(write_job(tmp_path, {"jobs": [{"prompt": "x"}]})).jobs[0]
        assert job.reference_paths == []

    def test_rejects_over_the_limit(self, tmp_path: Path) -> None:
        refs = []
        for i in range(17):
            p = tmp_path / f"r{i}.png"
            p.write_bytes(b"fake")
            refs.append(str(p))
        job_file = write_job(tmp_path, {"jobs": [{"prompt": "x", "reference_paths": refs}]})
        assert any("too many reference images" in e for e in validate_job_file(job_file))

    def test_rejects_non_string_list_items(self, tmp_path: Path) -> None:
        job_file = write_job(tmp_path, {"jobs": [{"prompt": "x", "reference_paths": [1, 2]}]})
        assert any("must contain strings" in e for e in validate_job_file(job_file))

    def test_reports_a_missing_file_inside_a_list(self, tmp_path: Path) -> None:
        good = tmp_path / "good.png"
        good.write_bytes(b"fake")
        job_file = write_job(
            tmp_path,
            {"jobs": [{"prompt": "x", "reference_paths": [str(good), str(tmp_path / "no.png")]}]},
        )
        assert any("reference image not found" in e for e in validate_job_file(job_file))


class TestInputFidelityJobs:
    def test_accepted_per_job_and_from_defaults(self, tmp_path: Path) -> None:
        job_file = write_job(
            tmp_path,
            {
                "defaults": {"input_fidelity": "low"},
                "jobs": [{"prompt": "a"}, {"prompt": "b", "input_fidelity": "high"}],
            },
        )
        assert validate_job_file(job_file) == []
        jobs = parse_job_file(job_file).jobs
        assert jobs[0].input_fidelity == "low"
        assert jobs[1].input_fidelity == "high"

    def test_defaults_to_none(self, tmp_path: Path) -> None:
        job = parse_job_file(write_job(tmp_path, {"jobs": [{"prompt": "x"}]})).jobs[0]
        assert job.input_fidelity is None

    def test_rejects_invalid_value(self, tmp_path: Path) -> None:
        job_file = write_job(tmp_path, {"jobs": [{"prompt": "x", "input_fidelity": "medium"}]})
        assert any("input_fidelity" in e for e in validate_job_file(job_file))
