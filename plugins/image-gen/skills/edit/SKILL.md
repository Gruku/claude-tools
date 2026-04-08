---
name: edit
description: "Edit an existing image using a text prompt and Gemini."
---

# Image Gen — Edit

Modify an existing image based on a text description.

## Process

1. **Identify the input image** — Get the path to the image the user wants to edit. Verify it exists using the Read tool.

2. **Craft the edit prompt** — Describe what changes to make. Be specific:
   - Good: "Change the background from blue to a sunset gradient with orange and purple"
   - Bad: "Make it look better"

3. **Choose output path** — Save as a new file to preserve the original. Use a descriptive suffix like `-edited`, `-v2`, or describe the change: `sword-blue.png` -> `sword-red.png`.

4. **Run the script:**
```bash
node "${SKILL_DIR}/../../src/generate.mjs" \
  --prompt "<edit description>" \
  --input "<input-image-path>" \
  --output "<output-path>.png" \
  --aspect "<ratio>" \
  --size "<size>"
```

5. **View the result** — Use the Read tool to view both the original and edited images.

6. **Report back** — Show both images, describe what changed, ask if the user wants further adjustments.

## Tips

- The edit prompt should describe the desired end state, not the diff
- Aspect ratio and size should match the input image unless the user wants to change them
- For subtle edits, be very explicit about what to preserve: "Keep the character exactly the same but change the background to..."
- For style transfer: "Render this image in pixel art style while preserving the composition"

## Supported Input Formats

PNG (.png), JPEG (.jpg, .jpeg), WebP (.webp)
