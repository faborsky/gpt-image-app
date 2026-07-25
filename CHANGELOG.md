# Changelog

All notable changes to this project are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/); versions follow [Semantic Versioning](https://semver.org/).

## [1.0.1] — 2026-07-25

### Fixed

- **`--json` no longer emits invalid JSON when a request is retried.** Retry
  notices from `generator.py` were printed to stdout, so any retried call
  interleaved human text with the JSON payload and broke parsing. They now go to
  stderr, where diagnostics belong — stdout stays a clean, parseable result.

  Found while an OpenAI-wide outage made every call retry, which is exactly the
  condition that triggers it. A regression test asserts the generator console
  writes to stderr.

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

OpenAI's image endpoint was returning `500` for every model — and for `chat.completions` as well — throughout the final verification window for this release. Consequently the transparency rejection and the `usage`-based cost path are implemented from the documented behaviour rather than from a live observation. Both are covered by offline tests; the first live run should confirm `cost_source` reports `actual (…)`.
