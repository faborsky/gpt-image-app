# OpenAI Image API — how it actually behaves

Field notes on the OpenAI Image API as used by this CLI. Verified against the official docs on **2026-07-25**; items found empirically are marked as such. This is the file to read when something breaks and the error message isn't enough.

## Models

Present on the API as of 2026-07-25 (verified via `client.models.list()`):

| Model ID | Sizes | Transparency | Notes |
|---|---|---|---|
| `gpt-image-2` | arbitrary WxH within limits | **no** | Flagship, the default here. Also exposed as `gpt-image-2-2026-04-21`. |
| `gpt-image-1.5` | 3 fixed | yes | Previous flagship. |
| `gpt-image-1-mini` | 3 fixed | yes | Cheapest. |
| `gpt-image-1` | 3 fixed | yes | Legacy; slated to retire 2026-10-23. |

`chatgpt-image-latest` also appears in the list but is the ChatGPT-surface model, not intended for this use. DALL·E was removed from the API in 2026-05.

The vision model for `describe` is `gpt-5.4-mini`. `gpt-5` (2025-08) still exists but no longer appears in the pricing tables and has been superseded several times over (`gpt-5.4`, `gpt-5.5`, `gpt-5.6-*`).

## Request shape

```python
client.images.generate(
    model="gpt-image-2",
    prompt=prompt,
    size="1424x800",        # concrete pixels, not a ratio
    quality="high",         # low | medium | high | auto
    background="auto",      # auto | opaque   (transparent NOT on gpt-image-2)
    output_format="png",    # png | jpeg | webp
    n=1,
)
```

With a reference image the call goes to `client.images.edit(image=fh, **same_params)` instead.

The API takes **pixel sizes, not aspect ratios**. Translating `-a 16:9 -r 2K` into a legal size is `aspect_res_to_size()`'s whole job.

## Size constraints — including one that isn't documented

For `gpt-image-2`:

- both edges must be **multiples of 16**
- **max edge 3840 px** (and the box is effectively 3840×2160)
- aspect ratio within **1:3 – 3:1**
- total pixels **655,360 – 8,294,400** per the docs
- **and a minimum pixel budget of roughly 1 MP** — sizes below it are rejected with *"below the current minimum pixel budget"*

That last one was **found in live testing, not in the docs**, and it's the reason `aspect_res_to_size()` sizes by **area rather than long edge**. The naive approach — take 1024 as the long edge for "1K" — produces 1024×576 for 16:9, which is 0.59 MP and gets rejected outright. Sizing by area gives 1424×800 (1.14 MP), which is legal and visually equivalent.

The test suite asserts all four constraints across every aspect-ratio × resolution combination, so this can't silently regress.

The other three models accept only `1024x1024`, `1536x1024`, `1024x1536` (or `auto`). `_snap_size_for_model()` maps the computed size to the nearest of those by ratio.

## Transparency

Per the docs, verbatim: *"gpt-image-2 doesn't currently support transparent backgrounds. Requests with `background: "transparent"` aren't supported for this model."*

`validate_background_for_model()` enforces this **locally, before the call**, and the error names the models that do support transparency. Two independent constraints are checked:

1. Model support — only `gpt-image-1` / `1.5` / `mini` can do it.
2. Container — transparency needs an alpha channel, so `jpeg` is impossible regardless of model.

> Not verified live: OpenAI's image endpoint was returning 500 for every model during this release's development, so the rejection is implemented from the documented behaviour rather than from an observed error. If the docs change, this guard is the first thing to revisit.

## Response shape

```python
response.data[0].b64_json   # always base64, never a URL
response.usage              # input_tokens / output_tokens, when present
```

Image bytes always arrive **base64-encoded** in `b64_json` — there is no URL mode to fall back on. `generator.py` decodes and writes them directly.

`usage` is what makes honest cost reporting possible; `estimate_cost()` prefers it and only falls back to the published per-image table when it's absent, labelling which source it used.

## Pricing mechanics

Images are billed as **tokens**: input (prompt text plus any reference image) and image output tokens.

Token rates per 1M ([source](https://developers.openai.com/api/docs/pricing)):

| Model | Input | Cached input | Output |
|---|---|---|---|
| `gpt-image-2` | $8.00 | $2.00 | $30.00 |
| `gpt-image-1.5` | $8.00 | $2.00 | $32.00 |
| `gpt-image-1-mini` | $2.50 | $0.25 | $8.00 |
| `gpt-image-1` | $10.00 | — | $40.00 |

Published per-image prices for `gpt-image-2` ([source](https://developers.openai.com/api/docs/guides/image-generation)):

| Quality | 1024×1024 | 1024×1536 | 1536×1024 |
|---|---|---|---|
| low | $0.006 | $0.005 | $0.005 |
| medium | $0.053 | $0.041 | $0.041 |
| high | $0.211 | $0.165 | $0.165 |

Three things worth internalising:

1. **Quality dwarfs everything else.** `high` is ~35× `low` on the same size. Draft cheap, finalise expensive.
2. **Shape affects token count, not just area.** A larger non-square resolution can produce *fewer* output tokens than a smaller square one, which is why the 1024×1536 column is cheaper than 1024×1024.
3. **The fallback table is only a fallback.** Real cost comes from `usage`; the table exists for the case where the API returns none. The `FALLBACK_COST` entries for the non-flagship models are derived from token rates and are rough — the `gpt-image-2` row is the official one.

A Batch API also exists at roughly half these rates (queued, asynchronous). This CLI's `batch` command is a sequential loop over the standard endpoint and pays standard prices; migrating large non-urgent jobs to the real Batch API is the biggest cost optimisation left here.

## Errors and retry classification

The SDK raises `openai.APIStatusError` subclasses carrying `.status_code` — `RateLimitError` (429), `InternalServerError` (5xx), `BadRequestError` (400), and so on. `is_retryable_error()` reads `.status_code` first, then `.code`:

| Code | Meaning | Retried? |
|---|---|---|
| 429 | rate limit or spend cap | **yes** |
| 500, 502, 503, 504 | transient server-side failure | **yes** |
| 400 | invalid request (bad size, unsupported parameter) | no |
| 401 / 403 | bad or unauthorised key | no |
| 404 | unknown model | no |
| — | timeouts, connection resets (no code) | **yes**, matched on message |

**500s are a normal operating condition on this endpoint.** During the work on 1.0.0, `images.generate` returned 500 for `gpt-image-2`, `gpt-image-1-mini` *and* `chat.completions` across repeated attempts over an extended period — a genuine OpenAI-side outage. That is precisely why 5xx is retryable and why the CLI reports the underlying message instead of a generic failure.

**Backoff is exponential with jitter**, capped at 60 s: `min(base * 2**attempt, 60) * uniform(0.5, 1.0)`. OpenAI's own guidance recommends jitter explicitly — without it, parallel runs that hit the same limit retry in lockstep and collide again.

**Moderation refusals** are matched on the message ("content policy" / "moderation" / "safety") and never retried — the same words produce the same refusal. The API's `moderation` parameter (`auto` / `low`) is not currently exposed by this CLI.

## Rate limits

Limits are per usage tier, advanced automatically by cumulative spend:

| Tier | Requirement |
|---|---|
| Free | allowed geography |
| Tier 1 | $5 paid |
| Tier 2 | $50 paid |
| Tier 3 | $100 paid |
| Tier 4 | $250 paid |
| Tier 5 | $1,000 paid |

Metered in **RPM** (requests/minute), **TPM** (tokens/minute) and — for image models — **IPM (images per minute)**. Whichever budget runs out first triggers the limit, so a batch can be comfortably under the request limit and still hit 429 on IPM. The fix is a longer `--delay`, not more parallelism.

Responses carry `x-ratelimit-limit-requests`, `x-ratelimit-remaining-requests`, `x-ratelimit-reset-requests` and the token equivalents. This CLI doesn't currently read them — a possible improvement would be pacing batches proactively from `x-ratelimit-remaining-*` instead of reacting to 429s.

## Prompting behaviour

From OpenAI's [prompting guide](https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide):

- **Order matters:** background/scene → subject → key details → constraints. Short labelled segments beat one long paragraph.
- **Iterate in small single-change steps** from a clean base prompt; overloaded prompts are the main failure mode.
- **Text:** exact copy in quotes or ALL CAPS, demand verbatim rendering, spell tricky words letter by letter, use `medium`/`high`. The docs concede that *"the model can still struggle with precise text placement and clarity."*
- **Realism:** say "photorealistic" explicitly and ask for real texture; use camera language for high-level look only, not detailed body/lens specs.
- **Edits:** state exclusions and invariants explicitly and repeat the preserve-list every iteration.
- `input_fidelity` does **not** apply to `gpt-image-2` — output is already high fidelity, so the parameter should be omitted.

## Known gaps in this CLI

Documented so nobody rediscovers them as bugs:

- One reference image per job.
- `moderation` parameter not exposed.
- Rate-limit headers not read; pacing is reactive (retry on 429) rather than proactive.
- Uses the standard endpoint, not the ~50 % cheaper asynchronous Batch API.
- `batch` is strictly sequential by design, to stay clear of IPM limits.
- The transparency guard is implemented from documented behaviour, not from an observed API rejection (see above).
- `FALLBACK_COST` for the non-flagship models is derived from token rates, not officially published per-image figures.
