# UE5 HLSL Conventions for Custom Nodes

Best practices for HLSL code in UE5.5 Material Editor custom nodes.

## Code Formatting

### Line Endings
Use `\r\n` for all line breaks in the Code property:
```
Code="float x = 1.0;\r\nfloat y = 2.0;\r\nreturn x + y;"
```

### Comment Header
Always document inputs and outputs at the top:
```hlsl
// NodeName - Brief description
// Inputs:
//   ParamA : float   - Description
//   ParamB : float2  - Description
// Output: float - Description
// Additional Outputs:
//   ExtraOut : float2 - Description
```

## UE5 Intrinsic Functions

### Preferred Functions
| Use This | Instead Of | Reason |
|----------|-----------|--------|
| `saturate(x)` | `clamp(x, 0, 1)` | Optimized intrinsic |
| `lerp(a, b, t)` | `a + t * (b - a)` | Clearer, optimized |
| `step(edge, x)` | `x >= edge ? 1 : 0` | Branchless |
| `smoothstep(a, b, x)` | Manual cubic | Anti-aliased edges |
| `frac(x)` | `x - floor(x)` | Optimized intrinsic |
| `rsqrt(x)` | `1.0 / sqrt(x)` | Single instruction |
| `rcp(x)` | `1.0 / x` | Single instruction |
| `mad(a, b, c)` | `a * b + c` | Fused multiply-add |

### Available Math Functions
```hlsl
// Trigonometry
sin, cos, tan, asin, acos, atan, atan2
sincos(angle, out s, out c)  // Computes both

// Exponential
pow, exp, exp2, log, log2, log10
sqrt, rsqrt

// Rounding
floor, ceil, round, trunc, frac

// Comparison
min, max, clamp, saturate
step, smoothstep

// Interpolation
lerp, fmod

// Vector
length, normalize, distance
dot, cross (3D only)
reflect, refract

// Matrix
mul, transpose
```

## Antialiasing — Material Function Approach

**Do NOT apply AA inside Custom HLSL nodes.** Output raw SDF values instead.

AA is handled by the `MF_UI_SDF_AntiAliasedStep` Material Function node placed after Custom nodes in the graph. See `antialiasing-reference.md` for full details and node structure.

```hlsl
// CORRECT: Output raw SDF as additional output
SDFMask = length(uv - 0.5) - radius;  // Raw SDF, no AA

// WRONG: Don't do this in HLSL
// float aa = fwidth(sdf);
// float mask = 1.0 - smoothstep(-aa, aa, sdf);
```

## Animation Patterns

### Time-Triggered Animation
```hlsl
// StartTime = -1 means inactive
// Set StartTime = CurrentTime to begin

if (StartTime < 0.0) return initialValue;

float elapsed = CurrentTime - StartTime;
float t = saturate(elapsed / Duration);
return lerp(startValue, endValue, t);
```

### Interruptible Enter/Exit
```hlsl
float state = MidValue;

float enterT = EnterStart + Delay;
float exitT  = ExitStart + Delay;

// Exit takes priority when active
if (ExitStart > -0.5 && CurrentTime >= exitT)
{
    float t = saturate((CurrentTime - exitT) / Duration);
    state = lerp(MidValue, EndValue, easeOut(t));
}
else if (EnterStart > -0.5 && CurrentTime >= enterT)
{
    float t = saturate((CurrentTime - enterT) / Duration);
    state = lerp(StartValue, MidValue, easeOut(t));
}
else if (EnterStart > -0.5)
{
    state = StartValue;  // Before enter
}

return state;
```

### Easing Functions
```hlsl
// Ease Out Quad
float easeOutQuad(float t) {
    return 1.0 - (1.0 - t) * (1.0 - t);
}

// Ease Out Cubic
float easeOutCubic(float t) {
    float tm1 = t - 1.0;
    return 1.0 + tm1 * tm1 * tm1;
}

// Ease Out with Overshoot (Back easing)
float easeOutBack(float t, float overshoot) {
    float c1 = 1.70158 * overshoot;
    float c3 = c1 + 1.0;
    float tm1 = t - 1.0;
    return 1.0 + c3 * tm1 * tm1 * tm1 + c1 * tm1 * tm1;
}

// Ease In with Overshoot
float easeInBack(float t, float overshoot) {
    float c1 = 1.70158 * overshoot;
    float c3 = c1 + 1.0;
    return c3 * t * t * t - c1 * t * t;
}
```

## Float4 Packing

### Grouping Strategy
Pack parameters by logical category:
```hlsl
// Good: Related parameters together
float4 SectorParams;  // (StartAngle, ArcAngle, Radius, Thickness)
float4 AnimParams;    // (EnterStart, ExitStart, Duration, Magnitude)

// Bad: Unrelated parameters
float4 MiscParams;    // (Radius, Duration, IconIndex, BorderWidth)
```

### Unpacking Pattern
```hlsl
// At the top of the custom node
float StartAngle = In1_Sector.x;
float ArcAngle   = In1_Sector.y;
float Radius     = In1_Sector.z;
float Thickness  = In1_Sector.w;
```

## UV Space Conventions

### Standard UE5 UV
- Origin: Top-left (0, 0)
- X: Left to right (0 → 1)
- Y: Top to bottom (0 → 1)

### Y-Axis Direction (CRITICAL)

UE5 UV Y-axis is inverted compared to standard math conventions:

| Visual Direction | UV Direction | Y Value |
|-----------------|-------------|---------|
| Up on screen | Negative Y | Decreasing |
| Down on screen | Positive Y | Increasing |

This affects ALL directional calculations:
- **Gravity** pulling down = positive Y delta
- **Launch/velocity** going up = negative Y component
- **Particle motion** upward = subtract from Y
- **Light coming from above** = negative Y direction

```hlsl
// CORRECT: Particle launching upward then falling with gravity
float2 velocity = float2(launchDirX, -abs(launchDirY));  // Negative Y = up
float2 gravity = float2(0.0, gravityStrength);            // Positive Y = down
float2 pos = startPos + velocity * t + 0.5 * gravity * t * t;

// WRONG: Standard math convention (Y-up)
// float2 velocity = float2(launchDirX, abs(launchDirY));  // Would go DOWN
// float2 gravity = float2(0.0, -gravityStrength);          // Would pull UP
```

**Self-review requirement:** After writing any shader with directional motion, explicitly verify Y-axis directions are correct for UE5's top-down UV space.

### Polar Coordinates
```hlsl
// 0° = top, clockwise
// Y-down UV space needs negated Y for standard math
float2 centered = Position - 0.5;
float angle = atan2(centered.x, -centered.y);  // Note: -y
float angleDeg = degrees(angle);
```

### Direction from Angle
```hlsl
// 0° top, clockwise, Y-down UV
float2 dir = float2(sin(radians(angleDeg)), -cos(radians(angleDeg)));
```

## Branching Guidelines

### Avoid Dynamic Branching When Possible
```hlsl
// Bad: Dynamic branch
if (condition > 0.5) {
    result = expensiveA();
} else {
    result = expensiveB();
}

// Better: Branchless with lerp (if both paths are cheap)
result = lerp(expensiveB(), expensiveA(), step(0.5, condition));
```

### When Branches Are Acceptable
```hlsl
// OK: Early-out saves significant work
if (mask < 0.001) return float4(0, 0, 0, 0);

// OK: Uniform branching (same path for all pixels in a group)
if (AnimationEnabled > 0.5) {
    // Animation logic
}
```

## Precision Considerations

### Avoid Division by Zero
```hlsl
float safeDiv = value / max(divisor, 1e-4);
float dur = max(Duration, 0.001);
```

### Normalize When Needed
```hlsl
// Only normalize if the vector could be zero-length
float2 dir = centered;
float len = length(dir);
if (len > 1e-4) {
    dir /= len;
}
```

## Additional Output Assignment

Assign additional outputs before the return statement:
```hlsl
// ... calculations ...

// Assign additional outputs
OutputMask = mask;
OutputUV = uv;
OutputSize = size;

// Main return value
return mainResult;
```

## Debug Patterns

### Visualize Values
```hlsl
// Show value as grayscale
return float4(value.xxx, 1);

// Show vector as RGB
return float4(normalize(vec) * 0.5 + 0.5, 1);

// Show sign (negative = red, positive = green)
return float4(saturate(-value), saturate(value), 0, 1);
```

### Step Through Ranges
```hlsl
// Visualize where value falls
if (value < 0.25) return float4(1, 0, 0, 1);  // Red
if (value < 0.50) return float4(1, 1, 0, 1);  // Yellow
if (value < 0.75) return float4(0, 1, 0, 1);  // Green
return float4(0, 0, 1, 1);  // Blue
```
