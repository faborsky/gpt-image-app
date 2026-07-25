# Changelog

All notable changes to this project are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/); versions follow [Semantic Versioning](https://semver.org/).

## [1.1.0] — 2026-07-25

### Added

- **Multiple reference images.** `-ref` can now be repeated (up to 16, the documented
  endpoint maximum), and batch jobs accept a list. This is what makes compositing
  possible — the canonical case being one image of a product plus one of the target
  scene, which a single reference cannot express.

  ```bash
  ./run.sh generate "Place the product from the first image onto the table from the \
    second image. Keep its shape and colour exactly. Match the scene's lighting." \
    -ref product.png -ref scene.png
  ```

  In batch files, `reference_path` accepts either a single string (unchanged, so
  existing job files keep working) or a list; `reference_paths` is the explicit plural.

- **`--input-fidelity` / `-if`** (`high` | `low`) — how strongly the model preserves
  detail from reference images. Guarded per model: `gpt-image-2` answers a `400`
  ("The model 'gpt-image-2' does not support the 'input_fidelity' parameter") because
  it always works at high fidelity, so the CLI rejects that combination locally and
  names the models that accept it. Also rejected when passed without any reference,
  where it has no meaning.

- **`reference_count` and `input_fidelity` in the `--json` payload**, so a caller can
  see how many references a result was built from.

- **Reference validation**: count against the 16-image maximum and size against the
  50 MB per-file limit, checked locally before a paid call.

- 29 further offline tests, including that a 1.0.x job file with a single
  `reference_path` string still parses identically.

### Costs to know before using this

Reference images are billed as **input image tokens**, so multi-reference calls are
markedly more expensive than text-only ones. Measured on the same 1024×1024 `low` run:

| Call | Input tokens | Cost |
|---|---|---|
| text only | 24 | $0.0063 |
| two reference images | 2365 | **$0.025** |

On models that accept it, `input_fidelity` is also a real cost lever — `high` used
4791 tokens against 618 for `low` on the same edit, roughly 8×.

### Note on fidelity

In a two-reference composite on `gpt-image-2`, an explicit instruction to preserve the
product's surface detail ("keep the ripeness spots exactly as they are") was not
followed — the output kept the shape and colour but dropped the fine markings. Since
`input_fidelity` cannot be raised on that model, an edit that depends on preserving
fine detail may do better on `gpt-image-1.5` with `--input-fidelity high`.

## [1.0.1] — 2026-07-25

### Fixed

- **`--json` no longer emits invalid JSON when a request is retried.** Retry
  notices from `generator.py` were printed to stdout, so any retried call
  interleaved human text with the JSON payload and broke parsing. They now go to
  stderr, where diagnostics belong — stdout stays a clean, parseable result.

  Found while an OpenAI-wide outage made every call retry, which is exactly the
  condition that triggers it. A regression test asserts the generator console
  writes to stderr.

### Verified against the live API

Once the outage lifted, everything the outage had blocked was confirmed end to end:

- **Cost is real, not estimated.** A `quality=low` 1024x1024 run reported
  `cost_source: "actual (24 in + 202 out tokens)"` → **$0.0063**, matching the published
  $0.006 for that tier.
- **The `--json` fix holds under real retries.** That same run came back with
  `attempts: 3` (two 500s, then success) and still produced valid, parseable JSON on
  stdout with the retry notices on stderr — the exact scenario that used to break it.
- **The transparency guard matches reality.** `gpt-image-2` rejects
  `background="transparent"` with a non-retryable `400 image_generation_user_error`
  ("Transparent background is not supported for this model"), and the documented
  workaround works: `gpt-image-1.5` returns a true RGBA image with transparent pixels.
- **`describe` works** on `gpt-5.4-mini`, returning a usable prompt-style description.
- **Size mapping is correct in practice:** `1:1 @ 1K` → `1072x1072`, above the ~1 MP minimum.

Operational note: the outage was neither uniform nor all-or-nothing. `models.list` recovered
while `images.generate` was still failing, and later the reverse. A health check on one
endpoint says nothing about another — probe the one you need.

## [1.0.0] — 2026-07-25

First production release. The tool stops being an internal A/B experiment and becomes a standalone image generation CLI: correct pricing, a guard against parameter combinations the API rejects, retry logic suited to an endpoint that really does return 500s, documented behaviour, and a bundled Claude Code skill.

### Added

- **Transparency guard** (`validate_background_for_model()`). `gpt-image-2` does not support transparent backgrounds; the CLI now catches that locally, before spending a call, and the error names the models that do support it. Also enforces that transparency needs an alpha-capable container (never `jpeg`).
- **`--json` output** for `generate` and `batch`. The result goes to stdout as JSON; human-readable output moves to stderr. Includes `cost_usd`, `cost_source`, the resolved pixel `size` and `attempts`.
- **`--version` / `-V`**, reporting the version and the default model.
- **Retry classification** (`is_retryable_error()`): 429 and 5xx plus network timeouts are retried; 400/401/403/404 fail immediately. Reads `.status_code` (the OpenAI SDK's `APIStatusError`) with a `.code` fallback.
- **Jitter on backoff** — `min(base * 2**attempt, 60) * uniform(0.5, 1.0)`, as OpenAI's guidance recommends, so parallel runs don't retry in lockstep after a shared rate limit.
- **Test suite** (`tests/`, offline, no API calls): every aspect-ratio × resolution combination asserted against all four documented `gpt-image-2` size constraints; pricing, transparency guard, retry classification, job parsing and filename rules. The official per-image price table is asserted, so a price change fails the suite rather than silently misreporting cost.
- **`docs/api-notes.md`** — request/response shape, the undocumented ~1 MP pixel budget, transparency rules, error codes, rate-limit tiers and IPM, pricing mechanics, and the known gaps in this CLI.
- **Bundled Claude Code skill** in `skill/` — `skill/gptimage/SKILL.md` plus a Czech install guide, covering commands, the quality/cost tradeoff, prompting rules and model limits.
- **Prompting guide** in README, based on OpenAI's official cookbook guide: prompt ordering, a DO/DON'T table, text-rendering rules, identity preservation and the iterate-in-small-steps lesson.
- **`jobs/example.json`** — a working three-job batch file.
- **LICENSE** (MIT).

### Changed

- **Reframed from a TEST-ONLY comparison harness into a standalone tool.** Removed the "sibling to nanobanana", "A/B only" and "do not integrate" framing from the package docstring, config, CLI help, README and metadata. The `gpt_` filename prefix stays, now justified as keeping outputs identifiable rather than as separation for a comparison.
- **`describe` now uses `gpt-5.4-mini`.** The previous `gpt-5` (2025-08) has been superseded and no longer appears in the pricing tables; `gpt-5.4-mini` is the current cheap vision model ($0.75/$4.50 per 1M).
- **Corrected the `gpt-image-2` fallback price table** to the officially published per-image figures — low $0.006, medium $0.053, high $0.211 at 1024². The previous values (high $0.125) understated `high` by about 40 %.
- **Removed the hardcoded CZK conversion** from cost output. The CLI reports USD, which is what the API bills in; currency conversion belongs to the caller.
- Enums moved from `(str, Enum)` to `StrEnum`.
- README rewritten as a full reference (setup, commands, models, pricing, transparency, prompting, rate limits, troubleshooting); CLAUDE.md rewritten as a lean signpost with a documentation map.
- Author metadata corrected in `pyproject.toml`; package classified as Production/Stable.
- Directory renamed from `gptimage-app` to `gpt-image-app`, matching the model naming (`gpt-image-2`).

### Fixed

- **Retries no longer burn quota on unretryable failures.** Previously every error got three attempts, so an invalid request or an unsupported parameter took three round-trips to surface.
- Batch progress output honours the injected console, so `--json` keeps stdout clean while the progress bar renders.
- Removed an unused `ConfigError` import in `generator.py`.

### Security

- `.env` is gitignored and contains only local credentials; `.env.example` carries no real key. No key, personal path or private reference appears anywhere in the tracked tree.

### Notes

An OpenAI-wide outage (status.openai.com: "Elevated error rates") ran through this release's
verification window. Everything was verified against the live API once it recovered — see 1.0.1.
