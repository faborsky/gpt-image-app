# GPT Image

CLI for AI image generation using OpenAI's **GPT Image** models (`gpt-image-2` and siblings). Single images or batches, reference-image editing, image analysis — designed to be driven both by a human and by an AI agent like Claude Code.

Ships with a **[Claude Code skill](skill/INSTALL.md)** so your agent knows the pricing, the quality tiers, the prompting rules, and what the models can and cannot do.

```bash
./run.sh generate "Photorealistic product shot of a matte ceramic mug on pale oak, morning window light, shallow depth of field" -a 16:9 -r 1K -q medium
```

- **Real cost reporting** — the price comes from the API's own token usage, not a guess.
- **Aspect-ratio vocabulary** (`-a 16:9 -r 2K`) instead of raw pixel sizes, mapped to whatever each model accepts.
- **Machine-readable `--json`** on stdout, human output on stderr.
- **Retries only what's worth retrying** — rate limits and the 500s this endpoint really does return, with exponential backoff and jitter.
- **Impossible parameter combinations are caught before you pay** — for example transparency on a model that doesn't support it.

---

## Contents

- [Setup](#setup)
- [Commands](#commands)
- [Models](#models)
- [Pricing](#pricing)
- [Transparency](#transparency)
- [Batch job format](#batch-job-format)
- [JSON output](#json-output)
- [Prompting guide](#prompting-guide)
- [Rate limits and reliability](#rate-limits-and-reliability)
- [Claude Code skill](#claude-code-skill)
- [Development](#development)
- [Troubleshooting](#troubleshooting)

---

## Setup

**Requirements:** Python 3.11+ and an OpenAI API key.

```bash
git clone https://github.com/faborsky/gpt-image-app.git
cd gpt-image-app
./setup.sh
```

Then add your API key:

```bash
cp .env.example .env
# open .env and paste your key
```

```
OPENAI_API_KEY=your-api-key-here
```

Get a key at **[platform.openai.com/api-keys](https://platform.openai.com/api-keys)**. Image generation needs credit on the account.

> `.env` is gitignored. Never commit your key, and never paste it into code.

Verify the install without spending anything:

```bash
./run.sh --version
./run.sh validate jobs/example.json
```

---

## Commands

| Command | What it does | Costs money |
|---|---|---|
| `generate` | Generate one image from a prompt | yes |
| `batch` | Generate many images from a JSON job file | yes |
| `validate` | Check a job file for errors, offline | no |
| `describe` | Analyse an existing image and get a prompt back | yes (cheap) |

### generate

```bash
./run.sh generate "PROMPT" [options]
```

| Flag | Default | Description |
|---|---|---|
| `-a`, `--aspect` | `1:1` | Aspect ratio |
| `-r`, `--resolution` | `1K` | `1K`, `2K`, `4K` — mapped to concrete pixels |
| `-q`, `--quality` | `high` | `low`, `medium`, `high`, `auto` — **the main cost lever** |
| `-m`, `--model` | `gpt-image-2` | See [Models](#models) |
| `-b`, `--background` | `auto` | `auto`, `transparent`, `opaque` |
| `-f`, `--format` | `png` | `png`, `webp`, `jpeg` |
| `-o`, `--output` | `./output` | Output directory |
| `-n`, `--name` | derived from prompt | Custom filename, no extension |
| `-ref`, `--reference` | — | Reference image (uses the edit endpoint) |
| `--json` | off | Machine-readable result on stdout |

```bash
# Cheap draft first
./run.sh generate "a red bicycle against a white wall" -q low

# Then the real thing
./run.sh generate "a red bicycle against a white wall" -q high -r 2K

# Wide, on the cheapest model
./run.sh generate "abstract gradient background, deep teal to amber" -a 21:9 -m gpt-image-1-mini -q low

# Edit an existing image
./run.sh generate "Replace the background with a seamless deep navy studio backdrop. Keep the product, its label and the lighting exactly the same." -ref product.png
```

Filenames are `gpt_<base>_<ratio>_<resolution>_<timestamp>.<ext>`. The `gpt_` prefix keeps outputs identifiable when several image tools write into the same folder.

### batch

```bash
./run.sh batch jobs/example.json [-o ./images] [-m gpt-image-2] [-d 1.0] [--json]
```

Runs jobs sequentially with a progress bar, reports failures as they happen, and prints the **total cost** at the end. `Ctrl+C` finishes the current image and stops cleanly. The job file is validated before the first API call, so a typo costs nothing.

### validate

```bash
./run.sh validate jobs/example.json
```

Checks structure, enum values and reference paths. **No API calls, no cost.**

### describe

```bash
./run.sh describe image.jpg              # short description
./run.sh describe image.jpg --detailed   # full prompt-ready description
```

Analyses an image with `gpt-5.4-mini` and returns text you can feed back into `generate`.

---

## Models

| Model | Sizes | Transparency | Notes |
|---|---|---|---|
| **`gpt-image-2`** (default) | any WxH within limits | **no** | Flagship. Best quality and editing. |
| `gpt-image-1.5` | 3 fixed sizes | yes | Previous flagship. |
| `gpt-image-1-mini` | 3 fixed sizes | yes | Cheapest — good for drafts and volume. |
| `gpt-image-1` | 3 fixed sizes | yes | Legacy. |

`gpt-image-2` accepts arbitrary dimensions: both edges multiples of 16, max edge 3840 px, ratio within 1:3–3:1, and a **minimum pixel budget of roughly 1 MP**. That last constraint is undocumented and was found in live testing — it's why `-a`/`-r` are mapped by *area* rather than long edge. Sizing 16:9 @ 1K by long edge would give 1024×576 (0.59 MP), which the API rejects outright.

The other models accept only `1024x1024`, `1536x1024` and `1024x1536`; requests are snapped to the nearest of those automatically.

---

## Pricing

Images are billed as **tokens**, so the CLI reports the **real cost from the API's `usage` field** after every call. When usage is missing it falls back to the published per-image table.

Published per-image prices for `gpt-image-2` ([source](https://developers.openai.com/api/docs/guides/image-generation), verified 2026-07-25):

| Quality | 1024×1024 | 1024×1536 / 1536×1024 |
|---|---|---|
| `low` | **$0.006** | $0.005 |
| `medium` | **$0.053** | $0.041 |
| `high` | **$0.211** | $0.165 |

Token rates per 1M tokens:

| Model | Input | Output |
|---|---|---|
| `gpt-image-2` | $8.00 | $30.00 |
| `gpt-image-1.5` | $8.00 | $32.00 |
| `gpt-image-1-mini` | $2.50 | $8.00 |
| `gpt-image-1` | $10.00 | $40.00 |

**Quality is the dominant cost lever — `high` is roughly 35× `low`.** Iterate on `low`, then render the winner on `high`. Bigger non-square sizes can cost slightly *less* than square ones, because output tokens track shape as well as area.

`describe` runs on `gpt-5.4-mini` ($0.75/1M in, $4.50/1M out) — a fraction of a cent per image.

---

## Transparency

**`gpt-image-2` does not support transparent backgrounds.** Requests with `background: transparent` are rejected by the API with a `400`:

```
Transparent background is not supported for this model.
```

The CLI catches this *before* making the call and tells you the two ways forward:

1. Use a model that supports it: `-m gpt-image-1.5` (or `-1-mini`, `-1`) with `-f png` or `-f webp`.
2. Generate on a flat, uniform background and remove it afterwards in an image editor.

Transparency also requires an alpha-capable container, so `-f jpeg` is rejected regardless of model.

---

## Batch job format

```json
{
  "defaults": {
    "aspect_ratio": "16:9",
    "resolution": "1K",
    "quality": "medium",
    "format": "png"
  },
  "jobs": [
    {
      "prompt": "Photorealistic product shot of a matte ceramic pour-over dripper on pale oak, morning window light",
      "output_name": "coffee_dripper"
    },
    {
      "prompt": "Editorial illustration of a city at dusk as layered paper cut-outs, deep teal and amber",
      "output_name": "paper_city",
      "quality": "high",
      "aspect_ratio": "4:5"
    }
  ]
}
```

`defaults` is optional and applies to every job. Each job **must** have `prompt`; `output_name`, `aspect_ratio`, `resolution`, `quality`, `background`, `format` and `reference_path` are optional overrides. A working example is in [`jobs/example.json`](jobs/example.json).

---

## JSON output

`--json` puts a parseable result on **stdout** and moves human-readable output to **stderr**.

```bash
./run.sh generate "a lake at dawn" --json | jq -r '.cost_usd'
```

```json
{
  "success": true,
  "output_path": "/path/to/output/gpt_a_lake_at_dawn_1x1_1K_20260725_120000.png",
  "model": "gpt-image-2",
  "aspect_ratio": "1:1",
  "resolution": "1K",
  "size": "1072x1072",
  "quality": "high",
  "format": "png",
  "background": "auto",
  "cost_usd": 0.2113,
  "cost_source": "actual (32 in + 7040 out tokens)",
  "attempts": 1
}
```

`cost_source` tells you whether the figure came from real token usage (`actual (…)`) or the fallback table (`estimate (…)`). Batch adds totals plus a per-image array.

---

## Prompting guide

Based on OpenAI's [GPT Image prompting guide](https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide).

**Order your prompt: background/scene → subject → key details → constraints.** For anything complex, use short labelled segments or line breaks rather than one long paragraph — think skimmable template, not prose.

### DO and DON'T

| DO | DON'T |
|---|---|
| Be concrete about materials, shapes, textures, medium (photo, watercolour, 3D render) | Leave the medium to chance |
| Say **"photorealistic"** explicitly when you want realism | Assume realism is the default |
| Ask for real texture — "pores, fabric wear, wood grain" | Expect lifelike surfaces unprompted |
| Put exact copy in **quotes** or ALL CAPS and demand verbatim rendering | Hope the text comes out right |
| Spell tricky brand names **letter by letter** | Assume unusual spellings survive |
| For edits: "change only X" + "keep everything else the same" | Describe only what changes |
| Repeat the preserve-list on **every** iteration | Assume the model remembers what to protect |
| Iterate with small single-change follow-ups | Cram everything into one overloaded prompt |
| Name the intended use (ad, UI mock, infographic) to set the polish level | Leave the register ambiguous |
| Use camera language for high-level look only | Over-specify lens and body specs |

**The one lesson that matters most:** iterate in small, single-change steps from a clean base prompt. Overloaded prompts and wholesale rewrites are the fastest way to lose the parts that already worked.

### Text inside images

The docs are candid about it: *"Although significantly improved, the model can still struggle with precise text placement and clarity."*

So when text matters:

1. Quote the exact string and say **verbatim, no extra characters**.
2. Spell unusual words letter by letter.
3. Use `-q medium` or `-q high` — `low` degrades small text badly.
4. Keep the layout simple and the word count low.

### Identity and compositing

For edits that must preserve a likeness, state exclusions and invariants explicitly and repeat them each round. When compositing, be explicit about which element moves where. Note that `input_fidelity` does not apply to `gpt-image-2` — its output is already high fidelity by default.

### Known weaknesses

- Precise text placement and clarity, especially small or dense text.
- No transparency on `gpt-image-2` (see [Transparency](#transparency)).
- Content moderation can refuse a prompt; the `moderation` parameter (`auto`/`low`) is not currently exposed by this CLI.

---

## Rate limits and reliability

Limits are per usage tier (Free → Tier 5, advanced by cumulative spend) and are metered in **RPM**, **TPM** and — for image models — **IPM (images per minute)**. Response headers carry `x-ratelimit-remaining-requests` and friends.

How this CLI behaves:

- **429 and 5xx** → retried up to 3 times with exponential backoff **plus jitter**, capped at 60 s. OpenAI explicitly recommends jitter, and the image endpoint genuinely does return sporadic 500s — during development of this release it returned 500 for every model for a sustained period.
- **400 / 401 / 403 / 404** → failed immediately. Retrying an invalid request or a bad key wastes time and quota.
- **Moderation refusals** → reported as `Content filtered`, never retried.
- **Impossible parameter combinations** (transparency on `gpt-image-2`, transparent JPEG) → rejected locally, before any call is made.
- **Batch** waits `--delay` seconds between images. Raise it if you hit IPM limits.

---

## Claude Code skill

[`skill/`](skill/) contains a Claude Code skill that teaches your agent this tool: commands, pricing, quality tiers, prompting rules and model limits. Install instructions (in Czech): **[skill/INSTALL.md](skill/INSTALL.md)**.

```bash
mkdir -p ~/.claude/skills
cp -R skill/gptimage ~/.claude/skills/gptimage
# then replace <GPT_IMAGE_APP_DIR> in the skill with the path to this repo
```

---

## Development

```bash
source .venv/bin/activate
python -m pytest tests/ -q     # offline tests, no API calls
ruff check gptimage/           # lint
```

| File | Responsibility |
|---|---|
| `gptimage/config.py` | Models, pricing, `aspect_res_to_size()`, validators, transparency guard, retry classification |
| `gptimage/generator.py` | `images.generate` / `images.edit`, base64 decode, real cost from usage, retry/backoff |
| `gptimage/batch.py` | Job file parse/validate, sequential runner, cost totals |
| `gptimage/cli.py` | Typer commands, human and `--json` output |
| `gptimage/utils.py` | Filename sanitising and generation |

See **[CLAUDE.md](CLAUDE.md)** for the architecture notes an AI agent needs, and **[docs/api-notes.md](docs/api-notes.md)** for how the OpenAI Image API actually behaves.

---

## Troubleshooting

**`Missing API key`** — copy `.env.example` to `.env` and paste your key.

**`does not support transparent backgrounds`** — see [Transparency](#transparency).

**`below the current minimum pixel budget`** — a size under ~1 MP reached the API. The `-a`/`-r` mapping prevents this; if you see it, the size came from somewhere else.

**500 errors on every request** — an OpenAI-side outage, not your setup. The CLI retries with backoff; check [status.openai.com](https://status.openai.com).

**`429`** — rate limit or spend cap. Raise `--delay` for batches, or check your tier.

**`Content filtered`** — moderation refused the prompt. Rephrase; retrying identical wording won't help.

**`Virtual environment not found`** — run `./setup.sh`.

---

## License

MIT — see [LICENSE](LICENSE).
