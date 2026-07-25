---
name: gptimage
description: Generate images with OpenAI's GPT Image models (gpt-image-2 and siblings) — single images or batches, from a text prompt or by editing a reference image. Knows the per-quality pricing, the model differences, the official prompting rules, and what the models can and cannot do. Use when the user asks to create, generate or produce images, graphics, illustrations, covers or visual content with OpenAI / GPT Image, or to analyse an existing image into a reusable prompt.
argument-hint: <image description or task>
allowed-tools: Bash, Read, Write, Glob
---

# GPT Image — image generation via OpenAI

Drives the GPT Image CLI at `<GPT_IMAGE_APP_DIR>`. Default model: **`gpt-image-2`**.

> If a command fails with "Missing API key", the user needs `OPENAI_API_KEY` in `<GPT_IMAGE_APP_DIR>/.env` (template in `.env.example`, key from [platform.openai.com/api-keys](https://platform.openai.com/api-keys), account needs credit). Tell them — don't try to work around it.

## Before you generate

**Quality is the cost lever and the spread is huge: `high` costs about 35× `low`** ($0.211 vs $0.006 per image). So:

1. **Draft on `-q low` first** when the composition is still uncertain. Show it, get agreement, then render the winner on `-q high`.
2. **State the expected cost** before generating more than ~3 images at `high`.
3. **Confirm the brief once** if anything material is unstated (subject, format, where it will be used). Don't ask twice.
4. **Never silently regenerate.** Propose the prompt change and confirm before spending again.

## Workflow

### Output location

Save into `./generated_images/` in the user's **current project directory**:

- Images: `./generated_images/`
- Batch job files: `./generated_images/jobs/`

Create the directories before running anything.

### Single image

```bash
mkdir -p ./generated_images
<GPT_IMAGE_APP_DIR>/run.sh generate "<prompt>" \
  -a <aspect> -r <resolution> -q <quality> -f <format> -o ./generated_images --json
```

### Batch (2 or more images)

```bash
mkdir -p ./generated_images/jobs
# write the job file first, then:
<GPT_IMAGE_APP_DIR>/run.sh validate ./generated_images/jobs/<name>.json
<GPT_IMAGE_APP_DIR>/run.sh batch ./generated_images/jobs/<name>.json -o ./generated_images --json
```

**Always `validate` first** — free, offline, and it catches a typo that would otherwise fail mid-batch after several paid images.

### Run generation in the background

Generation is slow, especially at `high`. Use `run_in_background: true` on the Bash tool and collect the result with `TaskOutput`.

### Use `--json`

`--json` puts the result on stdout and all prose on stderr. Read `cost_usd` and `cost_source` from it — `cost_source` tells you whether the figure is the **real** cost from the API's token usage (`actual (…)`) or a fallback estimate. Report the actual figure.

### After generating

1. Report which files were written and where.
2. Report the **actual cost** from the JSON.
3. Show the image with the Read tool if the user will want to judge it.

## Defaults

| Parameter | Default | When to change it |
|---|---|---|
| Model | `gpt-image-2` | `gpt-image-1-mini` for cheap volume; `gpt-image-1.5` when you need transparency |
| Quality | `high` | **`low` for drafts and iteration** — 35× cheaper |
| Resolution | `1K` | `2K`/`4K` for print or large display |
| Aspect ratio | `1:1` | Match the destination: `16:9` covers, `9:16` stories, `4:5` posters |
| Format | `png` | `webp` for smaller web files, `jpeg` for photos |

## Pricing

Billed as tokens; the CLI reports the real cost from the API. Published per-image prices for `gpt-image-2` at 1024×1024 ([source](https://developers.openai.com/api/docs/guides/image-generation), verified 2026-07-25):

| Quality | Per image | 10 images |
|---|---|---|
| `low` | **$0.006** | $0.06 |
| `medium` | **$0.053** | $0.53 |
| `high` | **$0.211** | $2.11 |

`gpt-image-1-mini` is materially cheaper across the board. Non-square sizes can cost slightly *less* than square ones. `describe` runs on `gpt-5.4-mini` and costs a fraction of a cent.

## What it can and cannot do

**Good at:**

- Photorealistic scenes and product shots, especially with explicit texture instructions.
- Editing an existing image from a reference — background swaps, style transfer, compositing.
- Illustration, UI mockups, infographics, logos.

**Cannot / struggles:**

- **No transparent background on `gpt-image-2`.** The API rejects it outright. Either switch to `-m gpt-image-1.5` (with `-f png` or `-f webp`), or generate on a flat background and remove it afterwards. The CLI catches this before charging you.
- **Precise text placement and clarity** — the docs admit this is still imperfect. Keep text short and layouts simple, and use `medium`/`high` (`low` mangles small text).
- **Transparency in JPEG** is impossible in any model — no alpha channel.
- **Sizes below ~1 MP** are rejected by `gpt-image-2`; the CLI's `-a`/`-r` mapping already avoids this.
- Exact brand logos, real people's likenesses and data-accurate charts are unreliable and often refused.
- Moderation can refuse a prompt. That's a verdict, not a transient error — rephrase rather than retry.

## Parameters

**Aspect ratios:** `1:1`, `2:3`, `3:2`, `3:4`, `4:3`, `4:5`, `5:4`, `9:16`, `16:9`, `21:9`
**Resolutions:** `1K`, `2K`, `4K` (mapped to concrete pixel sizes automatically)
**Quality:** `low`, `medium`, `high`, `auto`
**Models:** `gpt-image-2`, `gpt-image-1.5`, `gpt-image-1-mini`, `gpt-image-1`
**Background:** `auto`, `transparent` (not on `gpt-image-2`), `opaque`
**Formats:** `png`, `webp`, `jpeg`
**Reference formats:** `.jpg`, `.jpeg`, `.png`, `.webp`

Set the ratio with `-a`. **Never write the aspect ratio or pixel size into the prompt text.**

## Prompting guide

From OpenAI's [official GPT Image prompting guide](https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide).

### Prompt order

```
background/scene → subject → key details → constraints
```

For anything complex, use **short labelled segments or line breaks**, not one long paragraph. Think skimmable template rather than prose. Naming the intended use ("an ad creative", "a UI mockup", "an infographic") sets the register and polish level.

### DO and DON'T

| DO | DON'T |
|---|---|
| Be concrete — materials, shapes, textures, medium (photo, watercolour, 3D render) | Leave the medium to chance |
| Say **"photorealistic"** explicitly for realism | Assume realism is the default |
| Ask for real texture — "pores, fabric wear, wood grain" | Expect lifelike surfaces unprompted |
| Put exact copy in **quotes**, demand verbatim rendering | Hope the text comes out right |
| Spell tricky brand names **letter by letter** | Assume unusual spellings survive |
| For edits: "change only X" + "keep everything else the same" | Describe only what changes |
| Repeat the preserve-list **every** iteration | Assume the model remembers what to protect |
| **Iterate in small single-change steps** | Rewrite the whole prompt each round |
| Use camera language for high-level look | Over-specify lens and camera body |
| Describe a UI mockup as if it already exists | Use vague concept-art language for UI |

### The single most important lesson

**Start from a clean base prompt and change one thing at a time.** Overloaded prompts and wholesale rewrites are the fastest way to lose the parts that already worked. This matters more with these models than any single keyword.

### Text inside images

1. Quote the exact string and say **"verbatim, no extra characters"**.
2. Name the typography — *"a heavy geometric sans-serif"*.
3. Spell unusual or non-English words letter by letter.
4. Use `-q medium` or `-q high`; `low` degrades small text badly.
5. Keep the word count low and the layout simple.

### Editing from a reference

State both halves — what changes and what must not:

> "Replace the background with a seamless deep navy studio backdrop. Keep the product, its label, and the lighting exactly the same."

Repeat the preserve-list on every follow-up. `input_fidelity` does not apply to `gpt-image-2` — it's already high fidelity by default.

## Commands

```bash
# One image
<GPT_IMAGE_APP_DIR>/run.sh generate "<prompt>" -a 16:9 -r 1K -q high -o ./generated_images --json

# Cheap draft
<GPT_IMAGE_APP_DIR>/run.sh generate "<prompt>" -q low -o ./generated_images --json

# Transparent background (needs a model that supports it)
<GPT_IMAGE_APP_DIR>/run.sh generate "<prompt>" -m gpt-image-1.5 -b transparent -f png -o ./generated_images --json

# Edit a reference image
<GPT_IMAGE_APP_DIR>/run.sh generate "<what changes> Keep everything else identical." -ref path/to/img.png -o ./generated_images --json

# Batch
<GPT_IMAGE_APP_DIR>/run.sh validate ./generated_images/jobs/job.json
<GPT_IMAGE_APP_DIR>/run.sh batch ./generated_images/jobs/job.json -o ./generated_images --json

# Analyse an image into a prompt
<GPT_IMAGE_APP_DIR>/run.sh describe path/to/image.png --detailed
```

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
      "prompt": "Full description, scene first then subject then details then constraints",
      "output_name": "optional_filename",
      "quality": "high",
      "aspect_ratio": "4:5",
      "reference_path": "path/to/reference.png"
    }
  ]
}
```

`defaults` is optional and applies to all jobs. Every job **must** have `prompt`; everything else is an optional override.

## Errors

| Error | Meaning | What to do |
|---|---|---|
| `Missing API key` | no `OPENAI_API_KEY` in `.env` | tell the user to add it |
| `does not support transparent backgrounds` | transparency asked of `gpt-image-2` | switch to `-m gpt-image-1.5`, or flatten and remove later |
| `Content filtered` | moderation refused the prompt | rephrase; retrying identical wording won't help |
| `500` on every attempt | OpenAI-side outage — this endpoint does return sporadic 500s | the CLI retries with backoff; if it persists, check status.openai.com and tell the user |
| `429` | rate limit or spend cap | for batches raise `-d`; never add parallel calls |
| `below the current minimum pixel budget` | size under ~1 MP reached the API | shouldn't happen via `-a`/`-r`; report it |

Image models are metered in **images per minute (IPM)** as well as requests and tokens, so a batch can hit 429 while well under the request limit. The fix is a longer `--delay`.
