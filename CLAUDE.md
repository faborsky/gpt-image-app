# GPT Image — CLI for OpenAI GPT Image models

Python CLI that generates images through OpenAI's Image API (`gpt-image-2` and siblings). Built to be driven by a human **and** by an AI agent: `--json` I/O, parseable errors, real cost from the API's token usage, and retry logic that distinguishes transient failures from hard ones.

## Setup

```bash
./setup.sh                    # finds Python 3.11+, creates .venv, installs the package
./run.sh <command> [flags]    # activates .venv and runs the CLI from any directory
```

`OPENAI_API_KEY` lives in `.env` (gitignored, template in `.env.example`).

## Code structure

| File | Responsibility |
|---|---|
| `gptimage/config.py` | Model IDs, **pricing**, `aspect_res_to_size()`, validators, **transparency guard**, **retry classification** |
| `gptimage/generator.py` | `images.generate` / `images.edit`, base64 decode, real cost from `usage`, retry/backoff with jitter |
| `gptimage/batch.py` | Job file parse/validate, sequential runner, cost totals |
| `gptimage/cli.py` | Typer commands (`generate`, `batch`, `validate`, `describe`), human + `--json` output |
| `gptimage/utils.py` | Filename sanitising, `gpt_` prefix, timestamped naming |

## Commands

**Full flag reference + worked examples: [README.md](README.md).**

- `generate "PROMPT"` — one image. `-a` ratio, `-r` resolution, `-q` quality, `-m` model, `-b` background, `-f` format, `-o` dir, `-n` name, `-ref` reference, `--json`
- `batch <job.json>` — many images sequentially. `-m`, `-o`, `-d` delay, `--json`
- `validate <job.json>` — offline structural check, **no API calls, no cost**
- `describe <image>` — analyse an image into a reusable prompt. `--detailed`

## Models

```python
MODEL_NAME = "gpt-image-2"              # default; arbitrary sizes + transparency (preview)
DESCRIBE_MODEL_NAME = "gpt-5.4-mini"    # vision model behind `describe`
```

Also selectable: `gpt-image-1.5`, `gpt-image-1-mini` (cheapest), `gpt-image-1` (legacy). All four verified present via `models.list()` on 2026-07-25.

## ⚠️ Critical for automation (read before scripting)

- **Transparency now works on every model, `gpt-image-2` included** — it shipped there **in preview on 2026-08-20** and was verified live on 2026-08-23 (RGBA on `generate` and on `-ref` edits, PNG and WebP). The old "route transparency to `gpt-image-1.5`" workaround is obsolete; don't reintroduce it. `MODELS_WITHOUT_TRANSPARENCY` is now empty but the guard stays as a mechanism. What `validate_background_for_model()` still enforces: **transparency never fits in a JPEG** (no alpha channel) — caught locally, API answers `400 invalid_transparent_background_output_format`.
- **`gpt-image-2` has an undocumented ~1 MP minimum pixel budget.** Sizes below it fail with "below the current minimum pixel budget" — found in live testing, absent from the docs. This is why `aspect_res_to_size()` sizes by **AREA, not long edge**: 16:9 @ 1K by long edge would be 1024×576 = 0.59 MP and would be rejected. Do not "simplify" that function.
- **Quality is the dominant cost lever: `high` ≈ 35× `low`** ($0.211 vs $0.006 at 1024²). Draft on `low`, final on `high`. This matters far more than resolution.
- **Cost comes from the API's real `usage` when available**, falling back to a published per-image table. `cost_source` in the JSON says which — `actual (…)` vs `estimate (…)`. Report the actual figure, not the estimate.
- **`--json` writes only the result to stdout; all prose goes to stderr.** On failure: `{"success": false, "error": …}` plus non-zero exit.
- **Retry classification lives in `is_retryable_error()`.** 429 + 5xx and network timeouts retry with exponential backoff **plus jitter** (capped 60 s); 400/401/403/404 fail immediately. It reads `.status_code` (OpenAI SDK's `APIStatusError`) and falls back to `.code`.
- **This endpoint really does return 500s.** During the 1.0.0 work OpenAI returned 500 for every model and both the image and chat endpoints for a sustained stretch. Sporadic 500s are normal operation, not a bug in the caller — which is exactly why 5xx is retryable.
- **Non-gpt-image-2 models take only 3 fixed sizes**; `_snap_size_for_model()` snaps to the nearest square/landscape/portrait.
- **Run `validate` before any large batch.** Free and offline.
- **Image models are metered in IPM (images per minute)** as well as RPM/TPM. If a batch hits 429, raise `--delay` rather than adding parallelism.

## Prompting rules that change output quality

Full guide in [README.md](README.md#prompting-guide); the essentials:

1. **Order: background/scene → subject → key details → constraints.** Short labelled segments beat one long paragraph.
2. **Iterate in small single-change steps** from a clean base prompt — the single most valuable habit with these models.
3. **Text needs help:** exact copy in quotes, "verbatim, no extra characters", tricky words spelled letter by letter, and `medium`/`high` quality. The docs admit text placement is still imperfect.
4. **Edits need invariants:** "change only X" + "keep everything else the same", repeated every round.

## Testing

```bash
python -m pytest tests/ -q   # offline: size mapping, pricing, transparency guard, retry, job parsing
ruff check gptimage/
```

No API calls. Notable coverage: every aspect-ratio × resolution combination is asserted against all four documented `gpt-image-2` size constraints, and the official per-image price table is asserted so a price change fails the suite instead of silently misreporting cost.

## Release checklist

Bump `__version__` in `gptimage/__init__.py` and `version` in `pyproject.toml` → update README (pricing/models if changed), this file, `CHANGELOG.md` (new `## [x.y.z] — YYYY-MM-DD` entry) and the bundled skill in `skill/gptimage/` → run `pytest` + `ruff` → commit → tag `vX.Y.Z` → **GitHub Release from the tag** (`gh release create vX.Y.Z --latest`).

## Documentation map

- **[README.md](README.md)** — full command reference, models, pricing, transparency, prompting guide, troubleshooting.
- **[docs/api-notes.md](docs/api-notes.md)** — how the OpenAI Image API actually behaves: request/response shape, the pixel-budget constraint, error codes, rate limit tiers, pricing mechanics, known gaps.
- **[CHANGELOG.md](CHANGELOG.md)** — version history.
- **`skill/gptimage/`** — the bundled Claude Code skill (`/gptimage`). `skill/INSTALL.md` is the Czech install guide.
