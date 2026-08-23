---
name: gptimage
description: Generate images with OpenAI's GPT Image models (gpt-image-2 and siblings) — single images or batches, from a text prompt or by editing/compositing reference images. Knows the real cost mechanics, the model differences, the official prompting rules, and the measured limits. Use when the user asks to create, generate or edit images with OpenAI / GPT Image, to composite a product into a scene, or to analyse an existing image into a reusable prompt.
argument-hint: <image description or task>
allowed-tools: Bash, Read, Write, Glob
---

# GPT Image — image generation via OpenAI

Drives the GPT Image CLI at `<GPT_IMAGE_APP_DIR>`. Default model: **`gpt-image-2`**.

> If a command fails with "Missing API key", the user needs `OPENAI_API_KEY` in `<GPT_IMAGE_APP_DIR>/.env` (template in `.env.example`, key from [platform.openai.com/api-keys](https://platform.openai.com/api-keys), account needs credit). Tell them — don't work around it.

## Three things to do before your first prompt

1. **Read [Prompting](#prompting) and [Reference images](#reference-images-and-compositing) first.** GPT Image wants a different prompt order than other image models (scene → subject → details → constraints). A prompt written in another model's style measurably underperforms here.
2. **Use the built-in `batch` and `validate`.** The CLI already does batches, per-job references and real cost reporting. Don't wrap `generate` in your own one-image-at-a-time loop — you lose `validate`, which is free.
3. **Never budget from the price table.** It is a *lower bound* (text-only, 1024×1024). Generate **one** image, read the real `cost_usd`, and budget from that.

## Before you generate

**Quality is the expensive lever.** On a plain 1024² the published `high`/`low` ratio is ~35×; on a real 2K edit with a reference it measured **~17×**. Either way:

1. **Draft on `-q low`** while the composition is unsettled. Then render the winner on `high`.
2. **Measure one, then budget.** Read `cost_usd` from the first image and multiply. A table-based estimate came out **2× under** on a real batch.
3. **Agree a ceiling and report progress out loud.** Report the running total after each batch; stop and ask before exceeding it.
4. **Never silently regenerate.** Propose the prompt change and get agreement.

## Workflow

### Output location

Save into `./generated_images/` in the user's **current project directory** (`./generated_images/jobs/` for batch files). Create the directories first. Outputs are prefixed `gpt_`.

### Single image

```bash
mkdir -p ./generated_images
<GPT_IMAGE_APP_DIR>/run.sh generate "<prompt>" \
  -a <aspect> -r <resolution> -q <quality> -f <format> -o ./generated_images --json
```

### Batch (2 or more images)

```bash
mkdir -p ./generated_images/jobs
<GPT_IMAGE_APP_DIR>/run.sh validate ./generated_images/jobs/<name>.json
<GPT_IMAGE_APP_DIR>/run.sh batch ./generated_images/jobs/<name>.json -o ./generated_images --json
```

**Always `validate` first** — free, offline, and it catches a typo before several paid images fail.

### Run generation in the background

Generation is slow, especially at `high`. Use `run_in_background: true` and collect with `TaskOutput`.

### Use `--json`

Result on stdout, prose on stderr. Read `cost_usd` and `cost_source` — `cost_source` says whether the figure is **real** (`actual (…)`, from the API's token usage) or a fallback `estimate (…)`. Report the real one.

### After generating

1. Report which files were written and where.
2. Report the **actual cost** from the JSON, plus the running total.
3. Show the image with the Read tool so the user can judge it.

### Don't pass verdicts on image quality

**Describe what the image contains — don't rate whether it's good.** Model judgement of images runs systematically softer than a human client's: what reads as publishable to you often gets rejected outright.

| ✅ Describe (input for the user) | ❌ Don't (verdict) |
|---|---|
| "the wordmark is legible, the frame is red, the kickstand is not deployed" | "ad-grade, looks like an official press shot" |
| "the diacritics in the headline are correct, the logo shape differs from the original" | "flawless, brand colours correct, publishable" |

Words like *good, usable, publishable, ad-grade* belong to the user. When comparing variants, present them **unlabelled** and let the user pick before revealing which is which.

### One sample is not behaviour

**Before concluding "this model does X", run a second sample of the same prompt.** Variance between runs is large here, so a single image can succeed or fail by luck. Claims need **≥2 samples**. The API exposes no seed, so a second sample just means a second run — and if the two disagree, "inconsistent across runs" is the honest finding.

## Defaults

| Parameter | Default | When to change |
|---|---|---|
| Model | `gpt-image-2` | `gpt-image-1-mini` for cheap volume; `gpt-image-1.5` for forced input fidelity |
| Quality | `high` | **`low` for drafts** |
| Resolution | `1K` | `2K`/`4K` for print or large display |
| Aspect | `1:1` | match the destination: `16:9` covers, `9:16` stories, `4:5` posters |
| Format | `png` | `webp` for web, `jpeg` for photos |

## Costs

> ⚠️ **The price table is a LOWER BOUND, not what you will pay.** It covers 1024×1024 **without references**. Add a reference or a 2K output and the cost rises several-fold — billing is per token, and a reference image is input tokens.

**Published** per-image, `gpt-image-2` @ 1024×1024, no reference ([source](https://developers.openai.com/api/docs/guides/image-generation)):

| Quality | Per image |
|---|---|
| `low` | $0.006 |
| `medium` | $0.053 |
| `high` | $0.211 |

**What it actually costs** (real `cost_usd` from API usage):

| Call | Table | Real | Difference |
|---|---|---|---|
| `low`, 1024², text only | $0.006 | $0.0063 | matches |
| `low`, 1024², **two references** | $0.006 | **$0.025** | **4×** |
| `low`, 2K, 1 reference | $0.006 | $0.024 | 4× |
| `high`, 2K, 1 reference, 1:1 | $0.211 | $0.421 | 2× |
| `high`, 2K, 1 reference, **16:9** | — | $0.238 | **−44 % vs 1:1** |

**Three rules that follow:**

1. **Budget from measurement, not the table.** A table-based estimate was 2× under on a real batch.
2. **Non-square is materially cheaper** at the same "2K" — shape changes the output token count, not just area. Given a free choice of ratio, go landscape.
3. **`low` is not almost-free** once references are involved — it's cheap, not negligible.

Token rates per 1M: `gpt-image-2` $8 in / $30 out, `gpt-image-1.5` $8/$32, `gpt-image-1-mini` $2.50/$8, `gpt-image-1` $10/$40. `describe` runs on `gpt-5.4-mini` ($0.75/$4.50) — a fraction of a cent.

**Unused lever:** OpenAI has a real **Batch API at roughly half price** (queued, asynchronous). This CLI does *not* use it — its `batch` is a sequential loop over the standard endpoint at full price. For a large non-urgent job, mention it as an option, not as a feature.

## What it can and cannot do

**Strong at:** photorealism, branded banners and graphics with text (brand fidelity — logos and colours — is a relative strength), short headlines including non-English diacritics, illustration, UI mockups, infographics, background replacement and style transfer.

**Weak or unable:**

- **🔴 Placing a product into a NEW scene so that it sits physically right.** The hardest measured limit. Typical failures: a motorbike with no kickstand deployed, an object "pasted into" space and intersecting the scene geometry, a mug balanced on a laptop edge, a deformed product in flat-lay. It fails **systematically, not randomly** — more attempts don't help. Say so rather than burning budget.
- **Large run-to-run variance** on complex edits: the same prompt gives different results. Never build a claim on one sample.
- **Transparency in JPEG** is impossible anywhere (no alpha channel) — `-b transparent` needs `-f png` or `-f webp`. The CLI catches this **before** you pay.
- **Precise text placement and clarity** — the docs concede this. Short text, simple layout, `medium`/`high` (`low` shreds small text).
- **Sizes below ~1 MP** are rejected by `gpt-image-2`; the `-a`/`-r` mapping already avoids that.
- Exact logos, specific real people, and data-accurate charts are unreliable and often refused.
- Moderation can refuse a prompt. That's a verdict, not a transient error — rephrase.

## Parameters

**Aspect:** `1:1`, `2:3`, `3:2`, `3:4`, `4:3`, `4:5`, `5:4`, `9:16`, `16:9`, `21:9`
**Resolution:** `1K`, `2K`, `4K` (mapped to concrete pixels)
**Quality:** `low`, `medium`, `high`, `auto`
**Model:** `gpt-image-2`, `gpt-image-1.5`, `gpt-image-1-mini`, `gpt-image-1`
**Background:** `auto`, `transparent` (all models since 2026-08-20; needs `-f png`/`-f webp`), `opaque`
**Format:** `png`, `webp`, `jpeg`
**Reference:** `.jpg`, `.jpeg`, `.png`, `.webp` — `-ref` can be **repeated, up to 16×**
**Input fidelity:** `-if high` / `-if low` — only on `gpt-image-1/1.5/mini`

Set the ratio with `-a`. **Never write the ratio or pixel size into the prompt text.**

## Reference images and compositing

Pass a reference to edit instead of generating from scratch. **Repeat `-ref` for several** — up to 16, each under 50 MB.

Several references is what makes *product + target scene* expressible:

```bash
<GPT_IMAGE_APP_DIR>/run.sh generate "Place the product from the first image onto the table from the \
  second image. Keep its shape and colour exactly as they are. Match the scene's lighting and add a \
  soft contact shadow." -ref product.png -ref scene.png -q low -o ./generated_images --json
```

Refer to inputs by position ("the first image", "the second image") and **list what must not change**. In batch jobs use either `"reference_path": "one.png"` or `"reference_paths": ["product.png", "scene.png"]`.

⚠️ **References are billed as input tokens.** Two references took the same image from $0.0063 to **$0.025** (~4×). Measure before committing to a composite batch.

> Set expectations honestly: more references is a **tool, not a guarantee**. Even with two references, `gpt-image-2` may not hold fine product detail that the prompt explicitly demands, and physically convincing placement into a new scene remains the model's weak spot. Offer compositing as an attempt, not a solution.

### input_fidelity — older models only

`-if high` / `-if low` controls how strongly reference detail is preserved. **`gpt-image-2` rejects it** (`400`) because it always works at high fidelity; the CLI catches that locally. On `gpt-image-1.5` it works and is a **cost lever** — the same edit ran ~8× more expensive at `high` than at `low`.

Reach for it when **detail fidelity matters** and `gpt-image-2` is losing it: `-m gpt-image-1.5 -if high`.

## Prompting

From OpenAI's [official prompting guide](https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide).

### Prompt order

```
background/scene → subject → key details → constraints
```

For anything complex use **short labelled segments or line breaks**, not one long paragraph. Naming the intended use ("an ad creative", "a UI mockup", "an infographic") sets the register.

### DO and DON'T

| DO | DON'T |
|---|---|
| Be concrete — materials, shapes, textures, medium (photo, watercolour, 3D render) | Leave the medium to chance |
| Say **"photorealistic"** explicitly for realism | Assume realism is the default |
| Ask for real texture — "pores, worn fabric, wood grain" | Expect lifelike surfaces unprompted |
| Exact copy in **quotes** + "verbatim, no extra characters" | Hope the text comes out right |
| Spell unusual names **letter by letter** | Assume odd spellings survive |
| For edits: "change only X" + "keep everything else the same" | Describe only what changes |
| Repeat the preserve-list **every iteration** | Assume the model remembers what to protect |
| **Change one thing per round** | Rewrite the whole prompt each round |
| Camera language for overall look only | Over-specify lens and body |
| Describe a UI mockup as if it already exists | Use vague concept-art language for UI |

### The single most important lesson

**Start from a clean base prompt and change one thing per round.** Overloaded prompts and wholesale rewrites are the fastest way to lose what already worked — this matters more than any keyword.

### Text inside images

1. Exact string in quotes + "verbatim, no extra characters".
2. Name the typography ("a heavy geometric sans-serif").
3. Spell unusual or non-English words letter by letter, and check the result.
4. Use `-q medium` or `high`; `low` breaks small text.
5. Few words, simple layout.

### Editing from a reference

State both halves — what changes and what must stay:

> "Replace the background with a seamless deep navy studio backdrop. Keep the product, its label, and the lighting exactly the same."

Repeat the preserve-list in every follow-up.

## Commands

```bash
APP=<GPT_IMAGE_APP_DIR>

# One image
$APP/run.sh generate "<prompt>" -a 16:9 -r 1K -q high -o ./generated_images --json

# Cheap draft
$APP/run.sh generate "<prompt>" -q low -o ./generated_images --json

# Transparent background — works on the default model, png/webp only
$APP/run.sh generate "<prompt>" -b transparent -f png -o ./generated_images --json

# Edit a reference
$APP/run.sh generate "<what changes> Keep everything else identical." -ref img.png -o ./generated_images --json

# Composite: product into a scene (two references)
$APP/run.sh generate "Place the product from the first image onto the table from the second image. Keep its shape and colour exactly." -ref product.png -ref scene.png -o ./generated_images --json

# When detail fidelity matters — older model with fidelity forced high
$APP/run.sh generate "<what changes> Keep the product identical." -ref product.png -m gpt-image-1.5 -if high -o ./generated_images --json

# Batch
$APP/run.sh validate ./generated_images/jobs/job.json
$APP/run.sh batch ./generated_images/jobs/job.json -o ./generated_images --json

# Analyse an image into a prompt
$APP/run.sh describe img.png --detailed
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
      "prompt": "Scene, subject, details, constraints",
      "output_name": "optional_name",
      "quality": "high",
      "aspect_ratio": "4:5",
      "reference_paths": ["product.png", "scene.png"],
      "input_fidelity": "high"
    }
  ]
}
```

`defaults` is optional; every job needs `prompt`; everything else is an optional override.

## Errors

| Error | Meaning | What to do |
|---|---|---|
| `Missing API key` | no `OPENAI_API_KEY` in `.env` | tell the user to add it |
| `Transparent background requires png or webp` | `-b transparent` with `-f jpeg` | switch to `-f png` or `-f webp` |
| `does not support input_fidelity` | `-if` on `gpt-image-2` | drop `-if`, or `-m gpt-image-1.5` |
| `Too many reference images` | more than 16 references | trim — 16 is the endpoint limit |
| `Content filtered` | moderation refused | rephrase; retrying identical wording won't help |
| `500` repeatedly | OpenAI-side outage (this endpoint does return them) | the CLI retries with backoff; if it persists, check status.openai.com |
| `429` | rate limit or spend cap | raise `-d` for batches; never add parallel calls |

Image models are metered in **images per minute (IPM)** as well as requests and tokens, so a batch can hit 429 while under the request limit. The fix is a longer `--delay`.
