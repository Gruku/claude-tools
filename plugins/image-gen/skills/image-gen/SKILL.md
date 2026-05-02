---
name: image-gen
description: "Generate, edit, or refine images using Gemini or OpenAI. Auto-detects intent from context."
---

# Image Gen — Router

You have access to image generation via a Node.js script. Supports two backends: **Gemini** (default) and **OpenAI** (GPT Image 2, with GPT Image 1.5 retained for transparency).

## Intent Detection

Analyze the user's request and route:

| Signal | Action |
|--------|--------|
| No existing image referenced | **Generate** — invoke `image-gen:generate` |
| User references an existing image file path | **Edit** — invoke `image-gen:edit` |
| User says "refine", "iterate", "adjust", or references a previously generated image from this session | **Refine** — invoke `image-gen:refine` |

## Backend Selection

| Need | Backend | Why |
|------|---------|-----|
| General image generation | `gemini` (default) | Fast, free tier, good quality |
| Transparent backgrounds (game assets, sprites, icons) | `openai` with `--transparent` | Auto-uses `gpt-image-1.5` (native alpha). `gpt-image-2` does not support transparency — script falls back automatically. |
| Transparent + Gemini style | `gemini` with `--transparent` | Two-pass alpha extraction (slower, 2 API calls) |
| Highest quality generation | `openai` with `--quality high` | `gpt-image-2` is the new state-of-the-art default |

## Prerequisites

- **Gemini backend:** `GEMINI_API_KEY` environment variable
- **OpenAI backend:** `OPENAI_API_KEY` environment variable
- Node.js must be available
- Dependencies installed: run `npm install --prefix "${SKILL_DIR}/../../src"` if `node_modules` doesn't exist

## Quick Reference

**Script location:** `${SKILL_DIR}/../../src/generate.mjs`

**Full usage:**
```bash
node "${SKILL_DIR}/../../src/generate.mjs" \
  --prompt "..." \
  [--output path] \
  [--input path] \
  [--backend gemini|openai] \
  [--model name] \
  [--aspect ratio] \
  [--size size] \
  [--transparent] \
  [--quality low|medium|high]
```

**Defaults:** backend=gemini, model=auto (gemini-3.1-flash-image-preview or gpt-image-2), aspect=1:1, size=1K, quality=medium

**Gemini models:**
- `gemini-3.1-flash-image-preview` — Fast, good for iteration (default)
- `gemini-3-pro-image-preview` — Highest quality, use for final/polished assets
- `gemini-2.5-flash-image` — High-volume, low-latency

**OpenAI models:**
- `gpt-image-2` — State-of-the-art, fastest, supports flexible sizes up to 3840px and `quality=auto` (default).
- `gpt-image-1.5` — Retained for **transparent backgrounds**. `gpt-image-2` does not support `background=transparent`, so the script auto-falls-back to `gpt-image-1.5` whenever `--transparent` is set. You can also pin it explicitly with `--model gpt-image-1.5`.

**Aspect ratios:** 1:1, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9

**Gemini sizes:** 512px, 1K, 2K, 4K
**OpenAI sizes:** Mapped from aspect ratio (1024x1024, 1536x1024, 1024x1536)

**OpenAI quality (1024x1024):**
- `gpt-image-2`: low ~$0.005, medium ~$0.041, high ~$0.211, `auto` (default for the model)
- `gpt-image-1.5`: low $0.009, medium $0.034, high $0.133

After routing, invoke the appropriate sub-skill. Do NOT generate images directly from this router — always delegate to a sub-skill.
