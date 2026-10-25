# GPT Image

**🇬🇧 English** · [🇨🇿 Čeština](README.cs.md) · [🇪🇸 Español](i18n/README.es.md) · [🇧🇷 Português](i18n/README.pt-BR.md) · [🇩🇪 Deutsch](i18n/README.de.md) · [🇫🇷 Français](i18n/README.fr.md) · [🇨🇳 简体中文](i18n/README.zh-CN.md) · [🇯🇵 日本語](i18n/README.ja.md) · [🇸🇪 Svenska](i18n/README.sv.md) · [🇳🇴 Norsk](i18n/README.nb.md) · [🇩🇰 Dansk](i18n/README.da.md)

A CLI for generating images with OpenAI's **GPT Image** models (`gpt-image-2` and siblings). Single images or batches, edits from reference images, image analysis. Built to be driven by a human or by an AI agent like Claude Code. For anyone who generates images from the terminal or through an AI agent and wants to know what each image cost.

It ships with a **[Claude Code skill](skill/INSTALL.md)**, so your agent knows the pricing, the quality tiers, the prompting rules and what the models can and can't do.

Author: [Jindřich Fáborský](https://www.faborsky.com)

```bash
./run.sh generate "Photorealistic product shot of a matte ceramic mug on pale oak, morning window light, shallow depth of field" -a 16:9 -r 1K -q medium
```

- **Real cost reporting:** the price comes from the tokens the API actually used, not from an estimate.
- **Aspect ratios instead of pixels** (`-a 16:9 -r 2K`), mapped to whatever each model accepts.
- **Machine-readable `--json`** on stdout, human output on stderr.
- **Retries only what's worth retrying:** rate limits and the 500s this endpoint does return. With exponential backoff and jitter.
- **Impossible parameter combinations are caught before you pay:** for example transparency in a JPEG, which has no alpha channel.

> [!TIP]
> **The app is free and it's yours.** Clone it, use it, rebuild it your way.
>
> Want to build tools like this for your own marketing? That's what I teach: **[faborsky.com](https://www.faborsky.com)**.

---

## Contents

- [Setup](#setup)
- [Commands](#commands)
- [Models](#models)
- [Pricing](#pricing)
- [Reference images and compositing](#reference-images-and-compositing)
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

**What you need:** Python 3.11+ and an OpenAI API key.

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

> `.env` is gitignored. Never commit your key and never paste it into code.

Check the install without spending anything:

```bash
./run.sh --version
./run.sh validate jobs/example.json
```

---

## Commands

| Command | What it does | Costs money |
|---|---|---|
| `generate` | Generates one image from a prompt | yes |
| `batch` | Generates several images from a JSON file | yes |
| `validate` | Checks a job file for errors, offline | no |
| `describe` | Analyses an existing image and returns a prompt | yes (cheap) |

### generate

```bash
./run.sh generate "PROMPT" [options]
```

| Flag | Default | Description |
|---|---|---|
| `-a`, `--aspect` | `1:1` | Aspect ratio |
| `-r`, `--resolution` | `1K` | `1K`, `2K`, `4K`, mapped to concrete pixels |
| `-q`, `--quality` | `high` | `low`, `medium`, `high`, `auto`. **The main cost lever** |
| `-m`, `--model` | `gpt-image-2` | See [Models](#models) |
| `-b`, `--background` | `auto` | `auto`, `transparent`, `opaque` |
| `-f`, `--format` | `png` | `png`, `webp`, `jpeg` |
| `-o`, `--output` | `./output` | Output folder |
| `-n`, `--name` | derived from the prompt | Custom file name, no extension |
| `-ref`, `--reference` | none | Reference image. **Repeat it for several** (max 16) |
| `-if`, `--input-fidelity` | none | `high` / `low`, how much detail is kept from the references (not on `gpt-image-2`) |
| `--json` | off | Machine-readable result on stdout |

```bash
# Cheap draft first
./run.sh generate "a red bicycle against a white wall" -q low

# Then the final version
./run.sh generate "a red bicycle against a white wall" -q high -r 2K

# Wide format on the cheapest model
./run.sh generate "abstract gradient background, deep teal to amber" -a 21:9 -m gpt-image-1-mini -q low

# Edit an existing image
./run.sh generate "Replace the background with a seamless deep navy studio backdrop. Keep the product, its label and the lighting exactly the same." -ref product.png

# Composite: product into a target scene (two references)
./run.sh generate "Place the product from the first image onto the table from the second image. Keep its shape and colour exactly as they are. Match the scene's lighting and add a soft contact shadow." -ref product.png -ref scene.png
```

Files are named `gpt_<base>_<ratio>_<resolution>_<timestamp>.<ext>`. The `gpt_` prefix keeps outputs recognisable when several image tools write into the same folder.

### batch

```bash
./run.sh batch jobs/example.json [-o ./images] [-m gpt-image-2] [-d 1.0] [--json]
```

Runs the jobs in order, shows a progress bar, reports errors as they happen and prints the **total cost** at the end. `Ctrl+C` finishes the image in progress and exits cleanly. The job file is validated before the first API call, so a typo costs nothing.

### validate

```bash
./run.sh validate jobs/example.json
```

Checks the structure, allowed values and reference paths. **No API calls, no cost.**

### describe

```bash
./run.sh describe image.jpg              # short description
./run.sh describe image.jpg --detailed   # full description, ready to use as a prompt
```

Analyses the image with `gpt-5.4-mini` and returns text you can pass straight to `generate`.

---

## Models

| Model | Sizes | Transparency | Notes |
|---|---|---|---|
| **`gpt-image-2`** (default) | any width×height within limits | yes (preview, since 2026-08-20) | Flagship. Best quality and editing. |
| `gpt-image-1.5` | 3 fixed sizes | yes | Previous flagship. |
| `gpt-image-1-mini` | 3 fixed sizes | yes | Cheapest, good for drafts and volume. |
| `gpt-image-1` | 3 fixed sizes | yes | Legacy. |

`gpt-image-2` takes arbitrary dimensions: both sides a multiple of 16, longest edge max 3840 px, ratio between 1:3 and 3:1, and a **minimum budget of roughly 1 MP**. That last condition isn't in the documentation anywhere; it only showed up in live testing. That's why `-a`/`-r` are mapped by *area*, not by the long edge. If 16:9 at 1K were sized by the long edge, you'd get 1024×576 (0.59 MP), which the API rejects outright.

The other models accept only `1024x1024`, `1536x1024` and `1024x1536`. A request is rounded to the nearest of them automatically.

---

## Pricing

Images are billed as **tokens**, so after every call the CLI reports the **real cost from the `usage` field the API returns**. When `usage` is missing, it falls back to the published per-image price table.

Published per-image prices for `gpt-image-2` ([source](https://developers.openai.com/api/docs/guides/image-generation), verified 2026-07-25):

| Quality | 1024×1024 | 1024×1536 / 1536×1024 |
|---|---|---|
| `low` | **$0.006** | $0.005 |
| `medium` | **$0.053** | $0.041 |
| `high` | **$0.211** | $0.165 |

Rates per 1M tokens:

| Model | Input | Output |
|---|---|---|
| `gpt-image-2` | $8.00 | $30.00 |
| `gpt-image-1.5` | $8.00 | $32.00 |
| `gpt-image-1-mini` | $2.50 | $8.00 |
| `gpt-image-1` | $10.00 | $40.00 |

**Quality is the main cost lever: `high` costs roughly 35× more than `low`.** Iterate on `low` and render the winner on `high`. Larger non-square formats can cost a little *less* than square ones, because output tokens follow the shape as well as the area.

`describe` runs on `gpt-5.4-mini` ($0.75/1M input, $4.50/1M output), a fraction of a cent per image.

---

## Reference images and compositing

When you pass a reference, the image is edited instead of generated from scratch. **Repeat `-ref` if you want several references.** The maximum is **16**, as documented for the endpoint, each file png/webp/jpg up to 50 MB.

Multiple references are what make compositing possible to describe at all. The typical case is *product + target scene*:

```bash
./run.sh generate "Place the product from the first image onto the wooden table from the second image. \
  Keep its shape and colour exactly as they are. Match the scene's morning lighting and add a soft contact shadow." \
  -ref product.png -ref scene.png
```

Refer to the inputs by position ("the first image", "the second image") and say explicitly what must stay unchanged.

Batch jobs accept both forms:

```json
{ "prompt": "...", "reference_path": "single.png" }
{ "prompt": "...", "reference_paths": ["product.png", "scene.png"] }
```

### References cost real money

Reference images are billed as **input image tokens**, so compositing is far from free. Measured on the same 1024×1024 run at `low`:

| Call | Input tokens | Cost |
|---|---|---|
| text only | 24 | $0.0063 |
| two references | 2365 | **$0.025** |

Plan for it: a batch of twenty composites is closer to $0.50 than to $0.13, and that's at `low`.

### input_fidelity

`-if high` / `-if low` controls how strongly detail from the reference is preserved. It only works on `gpt-image-1`, `gpt-image-1.5` and `gpt-image-1-mini`. **`gpt-image-2` rejects it** (`400`), because it always processes inputs at high fidelity. The CLI catches this locally and tells you.

On the models that accept it, it's also a cost lever: `high` used **4791** tokens against **618** for `low` on the same edit.

In a two-reference composite on `gpt-image-2`, the model ignored an explicit instruction to keep fine surface detail ("keep the ripeness spots exactly as they are"). Shape and colour survived, the fine markings didn't. Fidelity can't be raised on this model, so edits that depend on keeping fine detail may turn out better on `gpt-image-1.5` with `-if high`.

---

## Transparency

**All current models can produce transparent backgrounds**, including `gpt-image-2`. It gained transparency **in preview on 2026-08-20** ([changelog](https://developers.openai.com/api/docs/changelog)). Until then it was the one thing the flagship couldn't do. That limitation is gone.

```bash
# A cut-out asset you can place on any background
./run.sh generate "A single glossy red apple, centered, studio product shot, no shadow" -b transparent -f png
```

**Transparency needs a format with an alpha channel**, so only `-f png` or `-f webp`. `-f jpeg` is rejected, locally, before any call goes out:

```
Transparent background requires png or webp output (jpeg has no alpha channel).
```

If it were sent anyway, the API would return `400 invalid_transparent_background_output_format`.

**Verified live on 2026-08-23** on `gpt-image-2`: PNG and WebP both come back as genuine RGBA with fully transparent pixels (alpha 0 in the corners, opaque subject), for `generate` and for `-ref` edits alike. And because `gpt-image-2` also takes arbitrary dimensions, you can now get transparency *and* a non-standard size in one call, for example 1072×1072 or 16:9 at 2K. The older models can't do that.

For automation, remember it's still a preview: the behaviour may change. That's why the CLI's guard is data-driven (`MODELS_WITHOUT_TRANSPARENCY` in `config.py`), in case a model loses support.

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

`defaults` is optional and applies to every job. Each job **must** have a `prompt`. Optional overrides are `output_name`, `aspect_ratio`, `resolution`, `quality`, `background`, `format` and `reference_path`. A working example is in [`jobs/example.json`](jobs/example.json).

---

## JSON output

`--json` puts a parseable result on **stdout** and moves the human-readable output to **stderr**.

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

`cost_source` tells you whether the figure came from actual token usage (`actual (…)`) or from the fallback table (`estimate (…)`). Batch adds totals and an array with per-image details.

---

## Prompting guide

Based on OpenAI's [GPT Image prompting guide](https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide).

**Build the prompt in this order: background/scene → subject → key details → constraints.** For anything more complex, use short labelled blocks or line breaks instead of one long paragraph. A template you can skim works better than continuous prose.

### Do and don't

| Do | Don't |
|---|---|
| Be concrete about materials, shapes, textures and medium (photo, watercolour, 3D render) | Leave the medium to chance |
| Say **"photorealistic"** explicitly when you want realism | Assume realism is the default |
| Ask for real texture: "pores, fabric wear, wood grain" | Expect lifelike surfaces without asking |
| Put the exact wording of any text in **quotes** or ALL CAPS and require it rendered verbatim | Hope the text comes out right |
| Spell tricky brand names **letter by letter** | Trust that unusual spellings survive |
| For edits: "change only X" + "keep everything else the same" | Describe only what changes |
| Repeat the list of things that must not change in **every** iteration | Assume the model remembers what to protect |
| Iterate in small steps, one change per round | Cram everything into one overloaded prompt |
| Say what it's for (ad, UI mock, infographic) so the model knows how much polish it needs | Leave the register unclear |
| Use photographic language only for the overall look | Over-specify lens and camera body |

**Iterate in small steps, one change at a time, always from a clean base prompt.** Overloaded prompts and rewriting everything at once are the fastest way to lose what already worked.

### Text inside images

The documentation says it plainly: *"Although significantly improved, the model can still struggle with precise text placement and clarity."*

So when the text matters:

1. Give the exact string in quotes and write **verbatim, no extra characters**.
2. Spell unusual words letter by letter.
3. Use `-q medium` or `-q high`. On `low`, small text falls apart.
4. Keep the layout simple and the word count low.

### Identity and compositing

For edits where a likeness must be preserved, list explicitly what must not change and repeat it every round. For compositing, say clearly which element moves where. Note that `input_fidelity` doesn't apply to `gpt-image-2`; its output is high fidelity by design.

### Known weaknesses

- Precise text placement and legibility, especially with small or dense text.
- Transparency on `gpt-image-2` is still a **preview** (see [Transparency](#transparency)).
- Content moderation can reject a prompt. This CLI doesn't expose the `moderation` parameter (`auto`/`low`) yet.

---

## Rate limits and reliability

Limits depend on the usage tier (Free → Tier 5, moving up with cumulative spend) and are measured in **RPM**, **TPM** and, for image models, also **IPM (images per minute)**. Response headers include `x-ratelimit-remaining-requests` and related values.

How this CLI behaves:

- **429 and 5xx** → retried up to 3 times with exponential backoff **plus jitter**, capped at 60 s. OpenAI explicitly recommends jitter, and the image endpoint does return occasional 500s. During development of this version it returned 500 for every model for an extended period.
- **400 / 401 / 403 / 404** → immediate error. Retrying an invalid request or a wrong key only burns time and quota.
- **Moderation refusals** → reported as `Content filtered` and never retried.
- **Impossible parameter combinations** (transparent JPEG, `input_fidelity` on `gpt-image-2`) → rejected locally, before any call goes out.
- **Batch** waits `--delay` seconds between images. Raise it if you hit IPM limits.

---

## Claude Code skill

The [`skill/`](skill/) folder contains a Claude Code skill that teaches your agent this tool: commands, pricing, quality tiers, prompting rules and model limits. Installation guide (in Czech): **[skill/INSTALL.md](skill/INSTALL.md)**.

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

| File | Responsible for |
|---|---|
| `gptimage/config.py` | Models, pricing, `aspect_res_to_size()`, validators, transparency guard, retry classification |
| `gptimage/generator.py` | `images.generate` / `images.edit`, base64 decoding, real cost from usage, retry and backoff |
| `gptimage/batch.py` | Job file parsing and validation, sequential runner, cost totals |
| `gptimage/cli.py` | Typer commands, human and `--json` output |
| `gptimage/utils.py` | File name sanitising and generation |

Architecture notes an AI agent needs are in **[CLAUDE.md](CLAUDE.md)**. How the OpenAI Image API behaves in practice is described in **[docs/api-notes.md](docs/api-notes.md)**.

---

## Troubleshooting

**`Missing API key`**: copy `.env.example` to `.env` and paste your key into it.

**`Transparent background requires png or webp output`**: `-b transparent` together with `-f jpeg`. Change the format, see [Transparency](#transparency).

**`below the current minimum pixel budget`**: a size under ~1 MP reached the API. The `-a`/`-r` mapping prevents this, so if you see it, the size came from somewhere else.

**500 errors on every request**: an outage on OpenAI's side, not your setup. The CLI retries with backoff; check the status at [status.openai.com](https://status.openai.com).

**`429`**: rate limit or spending cap. For batches, raise `--delay`, or check your tier.

**`Content filtered`**: moderation rejected the prompt. Rephrase it; repeating the same wording won't help.

**`Virtual environment not found`**: run `./setup.sh`.

---

## License

MIT, see [LICENSE](LICENSE).

## Author

[Jindřich Fáborský](https://www.faborsky.com), marketer and educator from Prague. I teach marketers to build their own tools with AI.
