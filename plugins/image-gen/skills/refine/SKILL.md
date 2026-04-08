---
name: refine
description: "Iteratively refine a previously generated image through multi-turn conversation."
---

# Image Gen — Refine

Iteratively improve a previously generated or edited image.

## Process

1. **Identify the previous image** — This should be an image generated or edited earlier in the session. Use the most recent output path.

2. **Understand the refinement** — What does the user want changed? Common refinements:
   - Style adjustments: "make it more vibrant", "add more contrast"
   - Detail changes: "add a shadow", "remove the background element"
   - Composition tweaks: "zoom in on the character", "add more space on the left"

3. **Craft the refinement prompt** — Reference the existing image and describe the specific changes. Be precise about what to keep and what to change.

4. **Run the script** (same as edit — refine passes the previous output as input):
```bash
node "${SKILL_DIR}/../../src/generate.mjs" \
  --prompt "<refinement description>" \
  --input "<previous-output-path>" \
  --output "<new-output-path>.png" \
  --aspect "<ratio>" \
  --size "<size>"
```

5. **View and compare** — Use the Read tool to view the new version. Compare with the previous version.

6. **Continue or finish** — Ask the user if they're satisfied or want further refinement. Keep iterating until they're happy.

## Refinement Loop

For multi-step refinement, track the iteration chain:

```
sword-v1.png  (initial generation)
  -> sword-v2.png  (added glow effect)
    -> sword-v3.png  (made handle longer)
      -> sword-final.png  (user approved)
```

Use incrementing version numbers or descriptive suffixes. Always pass the most recent version as `--input`.

## Tips

- Small, focused refinements work better than large sweeping changes
- If refinement isn't working well, consider regenerating from scratch with a better prompt
- After 3-4 refinement rounds with poor results, suggest switching to `--model gemini-3-pro-image-preview` for higher quality
- Keep the same aspect ratio and size unless the user specifically wants to change them
