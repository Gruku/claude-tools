---
name: ue5-ui-shader-antialiasing
description: Essential antialiasing techniques for Unreal Engine 5 UI shaders, materials, and custom shader code. Use this skill whenever working on UI shaders, material functions, custom HLSL nodes, or shader-based UI elements - even when antialiasing is not explicitly mentioned. Covers derivative calculations (ddx/ddy), smoothstep formulas, SDF workflows, MSDF fonts, texture settings, and compositing best practices. ALWAYS apply these principles to UI shader work to ensure production-quality visuals.
---

# UE5 UI Shader Antialiasing

This skill ensures all UI shaders follow proper antialiasing practices for production-quality visuals. Apply these principles to every UI shader, whether explicitly asked or not.

## Core Antialiasing Formula

**The fundamental AA formula for any gradient/SDF:**

```hlsl
// Calculate pixel width derivative (AA value)
float AA = abs(ddx(gradient)) + abs(ddy(gradient));

// Apply antialiasing with smoothstep
float mask = 1.0 - smoothstep(value - AA, value + AA, SDF);
```

**Critical rules:**
- ALWAYS use `value - AA` for the minimum (lower bound)
- ALWAYS use `value + AA` for the maximum (upper bound)
- Calculate AA from the SPECIFIC gradient/SDF you're working with, not a different one
- NEVER use `step()` or `if()` for visible edges - they cause aliasing

## Material Editor Implementation

### Node-Based AA Calculation

```
[Gradient/SDF] ──┬─→ [DDX] ─→ [Abs] ──┬─→ [Add] ─→ AA value
                 └─→ [DDY] ─→ [Abs] ──┘

[Value] ──┬─→ [Subtract AA] ─→ [Min input of Smoothstep]
          └─→ [Add AA] ─────→ [Max input of Smoothstep]

[SDF] ─────────────────────→ [Value input of Smoothstep]

[Smoothstep Result] ─→ [OneMinus] ─→ Final Mask
```

### Custom Node (HLSL)

```hlsl
// Input: float SDF
float AA = abs(ddx(SDF)) + abs(ddy(SDF));
return 1.0 - smoothstep(threshold - AA, threshold + AA, SDF);
```

**Alternative using fwidth (equivalent):**
```hlsl
float AA = fwidth(SDF);  // Same as abs(ddx) + abs(ddy)
return 1.0 - smoothstep(threshold - AA, threshold + AA, SDF);
```

## Working with SDFs and MSDF

### Standard SDF Workflow

1. **Generate/sample SDF** - Distance field where inside = negative, outside = positive
2. **Calculate AA** from the SDF gradient: `float AA = abs(ddx(SDF)) + abs(ddy(SDF))`
3. **Create mask** with smoothstep: `1.0 - smoothstep(-AA, AA, SDF)`
4. **Apply to color and alpha** separately with proper compositing order

### MSDF for Text (Multi-channel Signed Distance Field)

**Unpacking MSDF texture:**
```hlsl
// Input: float3 MSDF (RGB channels from texture)
float dist = max(min(MSDF.r, MSDF.g), min(max(MSDF.r, MSDF.g), MSDF.b));
```

**Range conversion to proper SDF:**
```hlsl
float SDF = (dist - 0.5) * 2.0;  // Convert [0,1] to [-1,1] range
```

**Then apply standard AA workflow:**
```hlsl
float AA = abs(ddx(SDF)) + abs(ddy(SDF));
float mask = 1.0 - smoothstep(-AA, AA, SDF);
```

### Creating Outlines from SDF

**Technique:** Use two thresholds to create an outline ring

```hlsl
// Outer edge
float AA_outer = abs(ddx(SDF)) + abs(ddy(SDF));
float outer_mask = 1.0 - smoothstep(outerThreshold - AA_outer, outerThreshold + AA_outer, SDF);

// Inner edge (for cutting out center)
float AA_inner = abs(ddx(SDF)) + abs(ddy(SDF));
float inner_mask = 1.0 - smoothstep(innerThreshold - AA_inner, innerThreshold + AA_inner, SDF);

// Outline = outer minus inner
float outline_mask = outer_mask * (1.0 - inner_mask);
```

## Critical Rules for Proper Antialiasing

### 1. Calculate AA from the Correct Gradient

**WRONG:**
```hlsl
float AA = abs(ddx(digit_SDF)) + abs(ddy(digit_SDF));  // Calculated from digit
float star_mask = smoothstep(0.0 - AA, 0.0 + AA, star_SDF);  // Applied to star
// Result: Artifacts! Different SDFs have different pixel derivatives
```

**CORRECT:**
```hlsl
float AA_star = abs(ddx(star_SDF)) + abs(ddy(star_SDF));  // From star SDF
float star_mask = smoothstep(0.0 - AA_star, 0.0 + AA_star, star_SDF);
```

### 2. Recalculate After UV Transforms

When scaling, rotating, or skewing UVs, ALWAYS recalculate AA after the transform:

```hlsl
// Transform UVs
float2 transformed_UV = rotate(UV, angle) * scale;

// Sample with transformed UVs
float SDF = SampleSDF(transformed_UV);

// Calculate AA AFTER transform (derivatives will be different)
float AA = abs(ddx(SDF)) + abs(ddy(SDF));
```

### 3. Avoid step() and if() for Visible Edges

**NEVER use for visible edges:**
```hlsl
// WRONG - Creates aliasing
float mask = step(0.5, gradient);
float mask = (gradient > 0.5) ? 1.0 : 0.0;
```

**Performance note:** `step()` is faster than `smoothstep()` - use it ONLY when:
- Edge is hidden/occluded
- No AA needed (e.g., internal calculations)
- Performance is critical and aliasing is acceptable

## Compositing Multiple Masks

### Order Matters

When compositing multiple elements, order affects the final result:

**Color compositing:**
```hlsl
float3 color = background;
color = lerp(color, layer1_color, layer1_mask);
color = lerp(color, layer2_color, layer2_mask);
color = lerp(color, layer3_color, layer3_mask);
```

**Alpha compositing:**
```hlsl
float alpha = 0.0;
alpha = max(alpha, mask1);  // Usually max for combining
alpha = max(alpha, mask2);
alpha = max(alpha, mask3);

// Special cases: multiply for cutting out
alpha = mask1 * (1.0 - mask2);  // Subtract mask2 from mask1
```

### Pre-multiplication for Correct Alpha

Prevent edge artifacts by pre-multiplying color:

```hlsl
// WRONG - Can show incorrect colors on edges
Output.RGB = color;
Output.A = mask;

// CORRECT - Pre-multiply color by alpha
Output.RGB = color * mask;
Output.A = mask;
```

## Texture Settings for UI Shaders

### Compression Settings

**For single-channel distance fields:**
- Use `BC4` (Grayscale) or `G8` compression
- Set to **Masks (no sRGB)** or **Distance Field Font**
- Significantly smaller file size vs. RGB

**For multi-channel (MSDF):**
- Use `BC7` for high quality
- Keep all RGB channels

### Color Space (CRITICAL)

**ALWAYS disable sRGB for:**
- Distance fields
- Gradients
- Masks
- Any texture used for math operations

**Why:** sRGB applies a power curve that corrupts gradient linearity

**Setting:** Texture Properties → sRGB → **UNCHECK**

### Mip Maps

**Enable mip maps when:**
- Texture will be displayed at multiple sizes
- Used in icons that scale dynamically
- UI elements that zoom in/out

**Disable mip maps only when:**
- Texture is ALWAYS displayed at exact size
- Memory savings are critical
- You control all use cases

**Without mip maps:** Severe artifacts when downscaled by texture samplers

## Common Patterns and Best Practices

### Pattern: Glow Effect

```hlsl
// Main shape
float AA_main = abs(ddx(SDF)) + abs(ddy(SDF));
float main_mask = 1.0 - smoothstep(-AA_main, AA_main, SDF);

// Glow (wider threshold, softer)
float glow_mask = 1.0 - smoothstep(-glowWidth, glowWidth, SDF);

// Composite
float3 final_color = lerp(backgroundColor, glowColor, glow_mask);
final_color = lerp(final_color, mainColor, main_mask);
```

### Pattern: Smooth SDF Union

For combining shapes smoothly (not sharp intersection):

```hlsl
// Smooth minimum function (for custom nodes)
float smin(float a, float b, float k) {
    float h = max(k - abs(a - b), 0.0) / k;
    return min(a, b) - h * h * k * 0.25;
}

// Usage: combines two SDFs with rounded corners
float combined = smin(SDF1, SDF2, smoothRadius);
```

### Pattern: Complete MSDF Text Shader

```hlsl
// Sample MSDF texture
float3 msdf = tex2D(MSDFTexture, UV).rgb;

// Unpack to distance
float dist = max(min(msdf.r, msdf.g), min(max(msdf.r, msdf.g), msdf.b));
float SDF = (dist - 0.5) * 2.0;

// Calculate AA
float AA = abs(ddx(SDF)) + abs(ddy(SDF));

// Create mask
float mask = 1.0 - smoothstep(-AA, AA, SDF);

// Output with pre-multiplication
return float4(textColor.rgb * mask, mask);
```

## Workflow Integration

### When Starting Any UI Shader Work:

1. **Plan masks first** - Identify all shapes/elements needed
2. **Calculate each mask** with proper AA from its own gradient
3. **Composite in order** - Colors first, then alpha
4. **Check texture settings** - No sRGB for gradients/SDFs
5. **Test at different scales** - Verify no artifacts when transformed

### Quality Checklist:

- [ ] All gradients/SDFs use smoothstep (not step)
- [ ] AA calculated from the correct gradient for each mask
- [ ] AA recalculated after UV transforms
- [ ] Textures have sRGB disabled where appropriate
- [ ] Colors pre-multiplied by alpha
- [ ] Mip maps enabled for scalable elements
- [ ] Tested at edges of screen (where derivatives are largest)
- [ ] No visible aliasing on any edges

## Performance Notes

- `smoothstep()` has minimal performance cost on modern GPUs
- `step()` is faster but only use when aliasing is acceptable
- Pre-calculate AA once and reuse for multiple thresholds on same SDF
- MSDF textures are more expensive to unpack but worth it for text quality
