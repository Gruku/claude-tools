---
name: generate
description: "Generate a new image from a text prompt using Gemini or OpenAI."
---

# Image Gen — Generate

Create a new image from a text description.

## Process

1. **Craft the prompt** — Transform the user's request into a detailed image generation prompt. Be specific about style, composition, colors, lighting, and subject matter. The more detail, the better the result.

2. **Choose backend and parameters** — Based on the use case:
   - **Transparent background needed?** Use `--backend openai --transparent` (native alpha) or `--backend gemini --transparent` (two-pass extraction, slower)
   - **Aspect ratio:** Match the intended use (1:1 for icons/avatars, 16:9 for backgrounds, 9:16 for mobile, 3:2 for game cards, etc.)
   - **Size:** 1K for drafts/iteration, 2K for production assets, 4K for hero images
   - **Model:** Default (flash) for iteration, `--model gemini-3-pro-image-preview` for final quality, `--backend openai --quality high` for best OpenAI quality

3. **Choose output path** — Name the file descriptively based on what it depicts. Place in `./assets/generated/` by default, or in a project-appropriate location (e.g., `./public/images/`, `./src/assets/`).

4. **Run the script:**
```bash
# Standard generation (Gemini)
node "${SKILL_DIR}/../../src/generate.mjs" \
  --prompt "<detailed prompt>" \
  --output "<output-path>.png" \
  --aspect "<ratio>" \
  --size "<size>"

# Transparent background (OpenAI — recommended)
node "${SKILL_DIR}/../../src/generate.mjs" \
  --backend openai \
  --transparent \
  --prompt "<detailed prompt>" \
  --output "<output-path>.png"

# Transparent background (Gemini two-pass — slower, 2 API calls)
node "${SKILL_DIR}/../../src/generate.mjs" \
  --transparent \
  --prompt "<detailed prompt>" \
  --output "<output-path>.png"
```

5. **View the result** — Use the Read tool to view the generated image file.

6. **Report back** — Show the user the image path and describe what was generated. Ask if they want adjustments.

## Transparency Decision

| Scenario | Recommendation |
|----------|---------------|
| Game sprites, icons, UI elements | `--backend openai --transparent` |
| Transparent + specific Gemini style | `--backend gemini --transparent` (two-pass) |
| Backgrounds, photos, art | No `--transparent` needed |

**Important:** Gemini cannot produce true alpha channels. When `--transparent` is used with Gemini, the script generates the image twice (on white and black backgrounds) and computes alpha mathematically. This uses 2 API calls and may have artifacts on complex edges.

## Prompt Crafting Tips

- Include art style: "pixel art", "photorealistic", "watercolor", "flat vector", "3D rendered"
- Include composition: "centered", "top-down view", "isometric", "side profile"
- For transparent images: DO NOT say "transparent background" in the prompt (the flag handles it). Instead describe only the subject.
- For game assets: specify "game asset", "sprite", "tileable texture", "UI element"
- Avoid ambiguity: "a red sword with a golden hilt and blue gems" not "a cool sword"

## Error Handling

- If `GEMINI_API_KEY` is not set, tell the user to set it: `export GEMINI_API_KEY=your-key`
- If `OPENAI_API_KEY` is not set for OpenAI backend: `export OPENAI_API_KEY=your-key`
- If the API returns no image, report the text response — it may explain why (content policy, etc.)
- If the script fails, check that dependencies are installed: `npm install --prefix "${SKILL_DIR}/../../src"`
