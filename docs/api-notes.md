# OpenAI Image API — how it actually behaves

Field notes on the OpenAI Image API as used by this CLI. Verified against the official docs on **2026-07-25**, transparency re-verified **2026-08-23**; items found empirically are marked as such. This is the file to read when something breaks and the error message isn't enough.

## Models

Present on the API as of 2026-07-25 (verified via `client.models.list()`):

| Model ID | Sizes | Transparency | Notes |
|---|---|---|---|
| `gpt-image-2` | arbitrary WxH within limits | yes (preview, 2026-08-20) | Flagship, the default here. Also exposed as `gpt-image-2-2026-04-21`. |
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
    background="auto",      # auto | opaque | transparent   (transparent needs png/webp)
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

## Reference images: how many, and what they cost

The edit endpoint takes a **list** of files, and that list is the whole point — it is how
compositing is expressed:

```python
client.images.edit(
    model="gpt-image-2",
    image=[open("product.png", "rb"), open("scene.png", "rb")],
    prompt="Place the product from the first image onto the table from the second...",
    size="1024x1024", quality="low", n=1,
)
```

**Maximum 16 images** for GPT Image models, each png/webp/jpg under 50 MB (dall-e-2 took
exactly one, square png under 4 MB). If a mask is supplied it applies to the first image.
Source: OpenAI API reference. Verified live 2026-07-25 with a two-image composite.

**They are billed as input image tokens**, which dominates the cost of a small edit.
Measured on identical 1024×1024 `low` runs:

| Call | input_tokens | of which image_tokens | Cost |
|---|---|---|---|
| text only | 24 | 0 | $0.0063 |
| two references | 2365 | 2337 | **$0.025** |

So references cost roughly 4× the base image here. Reach for `low` while iterating on a
composite, and don't assume the published per-image table applies — it covers text-only
generation.

`generator.py` opens the handles inside an `ExitStack`, so every file closes even when the
call raises. That matters because a retry reopens them.

## input_fidelity

Controls how strongly the model preserves detail from input images. **Only on the older
models** — `gpt-image-1`, `gpt-image-1.5`, `gpt-image-1-mini`.

`gpt-image-2` rejects it with a non-retryable `400` (verified live 2026-07-25):

```
400 - {'error': {'message': "The model 'gpt-image-2' does not support the
                 'input_fidelity' parameter.",
                 'type': 'image_generation_user_error',
                 'param': 'input_fidelity', 'code': 'invalid_value'}}
```

The docs give the reason: *"For `gpt-image-2`, omit this parameter; the API doesn't allow
changing it because the model processes every image input at high fidelity automatically."*
`validate_input_fidelity_for_model()` enforces this locally.

On models that accept it, the setting is a **significant cost lever** — the same edit on
`gpt-image-1.5` used **4791** total tokens at `high` versus **618** at `low`, roughly 8×.

**Observed limit of "automatically high fidelity":** in a two-reference composite on
`gpt-image-2`, a prompt that explicitly demanded the product's fine surface markings be
preserved ("keep the ripeness spots exactly as they are") produced an output that kept
shape and colour but dropped the markings. The parameter cannot be raised on that model,
so for detail-critical edits `gpt-image-1.5` with `input_fidelity="high"` is the escape
hatch worth testing.

## Transparency

**This changed on 2026-08-20.** Changelog, verbatim: *"Transparent backgrounds are now available in preview for `gpt-image-2` and `gpt-image-2-2026-04-21`"* — in the Images API and in the Responses API image-generation tool, with `png` or `webp` output. The guide adds: *"jpeg isn't supported with transparent backgrounds."*

Before that, `gpt-image-2` answered `400 image_generation_user_error` ("Transparent background is not supported for this model") and the CLI blocked it locally. **That guard is gone** — `MODELS_WITHOUT_TRANSPARENCY` is now an empty set. Only one constraint is left in `validate_background_for_model()`:

- Container — transparency needs an alpha channel, so `jpeg` is impossible on every model.

**Verified live (2026-08-23)** on `gpt-image-2`, `quality=low`:

| Call | `output_format` | Result |
|---|---|---|
| `images.generate` | `png` | **OK** — 1024×1024 PNG colour type 6 (RGBA) |
| `images.generate` | `webp` | **OK** — RGBA |
| `images.generate` | `jpeg` | `400 invalid_transparent_background_output_format` |
| `images.edit` (1 reference) | `png` | **OK** — RGBA, transparency survives an edit round |
| CLI `generate -b transparent -f png` | `png` | **OK** at 1072×1072 — arbitrary size *and* transparency in one call |

The transparency is real, not a nominal alpha channel: on the CLI output, alpha extrema were `(0, 254)`, all four corners `alpha=0`, subject centre `alpha=253`. Note the max is 254 rather than 255 — the subject is a hair short of fully opaque, irrelevant for compositing but worth knowing if you assert on exact alpha values.

The JPEG rejection is a `400`, not a `5xx`, so `is_retryable_error()` correctly refuses to retry it — and the local guard means the request never leaves the machine anyway:

```
400 - {'error': {'message': 'Transparent background is not supported for JPEG output format',
                 'type': 'image_generation_user_error',
                 'param': None, 'code': 'invalid_transparent_background_output_format'}}
```

**Preview status is the caveat.** The feature is labelled preview by OpenAI, so behaviour may change without a version bump on our side. The guard is data-driven: if a model loses support, add its ID to `MODELS_WITHOUT_TRANSPARENCY` and the CLI catches it again before spending a call.

Pricing is unaffected — a transparent `low` 1024² call billed `20 in + 202 out` tokens ($0.0062), the same as an opaque one.

## Response shape

```python
response.data[0].b64_json   # always base64, never a URL
response.usage              # input_tokens / output_tokens, when present
```

Image bytes always arrive **base64-encoded** in `b64_json` — there is no URL mode to fall back on. `generator.py` decodes and writes them directly.

`usage` is what makes honest cost reporting possible; `estimate_cost()` prefers it and only falls back to the published per-image table when it's absent, labelling which source it used.

## Pricing mechanics

Images are billed as **tokens**: input (prompt text plus any reference image) and image output tokens.

**Verified live (2026-07-25):** a `quality=low` 1024x1024 call returned
`input_tokens=24, output_tokens=202`, which at the rates below is **$0.0063** — matching
the published $0.006 per-image figure for that tier. So `usage` is real, it is returned on
image calls, and computing cost from it is accurate rather than a guess.

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

**500s are a normal operating condition on this endpoint.** During the work on 1.0.0 there was a genuine OpenAI-side outage (confirmed on status.openai.com as "Elevated error rates" across APIs, ChatGPT and Codex) in which `images.generate`, `models.list` *and* `chat.completions` all returned 500 for over an hour.

Two things learned from it, both worth knowing before you write your own client:

1. **An outage is not all-or-nothing, and it is not uniform across endpoints.** At one point `models.list` recovered (125 models) while `images.generate` still failed; twenty minutes later the reverse was true — image generation worked while `models.list` and `chat.completions` were down. So a health check against one endpoint tells you nothing reliable about another. Probe the endpoint you actually need.
2. **Retrying genuinely rescues calls during this.** The first successful verification run came back with `attempts: 3` — two 500s, then a success. Without retry that image would simply have failed. Also seen mid-outage: `503 {'error': 'Too many concurrent requests'}`, i.e. overload stacked on top of the outage.

That is why 5xx is retryable, why backoff carries jitter, and why the CLI surfaces the underlying provider message instead of a generic failure.

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

- `moderation` parameter not exposed.
- Rate-limit headers not read; pacing is reactive (retry on 429) rather than proactive.
- Uses the standard endpoint, not the ~50 % cheaper asynchronous Batch API.
- `batch` is strictly sequential by design, to stay clear of IPM limits.
- `FALLBACK_COST` for the non-flagship models is derived from token rates, not officially published per-image figures.
