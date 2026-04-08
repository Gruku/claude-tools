import { GoogleGenAI } from "@google/genai";
import OpenAI from "openai";
import { writeFileSync, readFileSync, mkdirSync, existsSync, unlinkSync } from "node:fs";
import { dirname, resolve, extname, join } from "node:path";
import { parseArgs } from "node:util";
import { tmpdir } from "node:os";
import { extractAlpha } from "./extract-alpha.mjs";

// --- Parse CLI args ---
const { values } = parseArgs({
  options: {
    prompt:      { type: "string", short: "p" },
    output:      { type: "string", short: "o" },
    input:       { type: "string", short: "i" },
    model:       { type: "string", short: "m" },
    aspect:      { type: "string", short: "a", default: "1:1" },
    size:        { type: "string", short: "s", default: "1K" },
    backend:     { type: "string", short: "b", default: "gemini" },
    transparent: { type: "boolean", short: "t", default: false },
    quality:     { type: "string", short: "q", default: "medium" },
  },
  strict: true,
});

if (!values.prompt) {
  console.error("Error: --prompt is required");
  process.exit(1);
}

const backend = values.backend.toLowerCase();
if (!["gemini", "openai"].includes(backend)) {
  console.error("Error: --backend must be 'gemini' or 'openai'");
  process.exit(1);
}

// --- Resolve default model per backend ---
const defaultModels = {
  gemini: "gemini-3.1-flash-image-preview",
  openai: "gpt-image-1.5",
};
const model = values.model || defaultModels[backend];

// --- Validate API key ---
if (backend === "gemini" && !process.env.GEMINI_API_KEY) {
  console.error("Error: GEMINI_API_KEY environment variable is not set");
  process.exit(1);
}
if (backend === "openai" && !process.env.OPENAI_API_KEY) {
  console.error("Error: OPENAI_API_KEY environment variable is not set");
  process.exit(1);
}

// --- Build output path ---
const outputPath = resolve(values.output || `./assets/generated/image-${Date.now()}.png`);
const outputDir = dirname(outputPath);
if (!existsSync(outputDir)) {
  mkdirSync(outputDir, { recursive: true });
}

// ============================================================
// GEMINI BACKEND
// ============================================================
async function generateGemini() {
  const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });

  async function callGemini(prompt, inputPath) {
    const parts = [{ text: prompt }];

    if (inputPath) {
      const ext = extname(inputPath).toLowerCase();
      const mimeMap = { ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp" };
      const mimeType = mimeMap[ext] || "image/png";
      const imageData = readFileSync(inputPath).toString("base64");
      parts.push({ inlineData: { mimeType, data: imageData } });
    }

    const response = await ai.models.generateContent({
      model,
      contents: parts,
      config: {
        responseModalities: ["TEXT", "IMAGE"],
        imageConfig: {
          aspectRatio: values.aspect,
          imageSize: values.size,
        },
      },
    });

    let imageBuffer = null;
    let textResponse = "";

    for (const part of response.candidates[0].content.parts) {
      if (part.inlineData) {
        imageBuffer = Buffer.from(part.inlineData.data, "base64");
      }
      if (part.text) {
        textResponse += part.text;
      }
    }

    return { imageBuffer, textResponse };
  }

  if (values.transparent && !values.input) {
    // Two-pass alpha extraction
    const basePrompt = values.prompt;
    const whitePrompt = `${basePrompt}. Place the subject on a plain solid white background (#FFFFFF). No shadows, no gradients, only pure white background.`;
    const blackPrompt = `${basePrompt}. Place the subject on a plain solid black background (#000000). No shadows, no gradients, only pure black background.`;

    const tmpWhite = join(tmpdir(), `imagegen-white-${Date.now()}.png`);
    const tmpBlack = join(tmpdir(), `imagegen-black-${Date.now()}.png`);

    try {
      // Generate both passes in parallel
      const [whiteResult, blackResult] = await Promise.all([
        callGemini(whitePrompt),
        callGemini(blackPrompt),
      ]);

      if (!whiteResult.imageBuffer || !blackResult.imageBuffer) {
        console.error("Error: Two-pass generation failed — one or both passes returned no image");
        process.exit(1);
      }

      writeFileSync(tmpWhite, whiteResult.imageBuffer);
      writeFileSync(tmpBlack, blackResult.imageBuffer);

      // Extract alpha
      await extractAlpha(tmpWhite, tmpBlack, outputPath);

      return {
        text: whiteResult.textResponse || blackResult.textResponse || null,
        method: "gemini-two-pass-alpha",
      };
    } finally {
      // Clean up temp files
      try { unlinkSync(tmpWhite); } catch {}
      try { unlinkSync(tmpBlack); } catch {}
    }
  } else {
    // Standard single-pass generation (or editing with input)
    const inputPath = values.input ? resolve(values.input) : null;

    if (inputPath && !existsSync(inputPath)) {
      console.error(`Error: Input file not found: ${inputPath}`);
      process.exit(1);
    }

    const result = await callGemini(values.prompt, inputPath);

    if (!result.imageBuffer) {
      console.error("Error: No image was returned by the API");
      if (result.textResponse) console.error("API response text:", result.textResponse);
      process.exit(1);
    }

    writeFileSync(outputPath, result.imageBuffer);
    return { text: result.textResponse || null, method: "gemini-standard" };
  }
}

// ============================================================
// OPENAI BACKEND
// ============================================================
async function generateOpenAI() {
  const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

  // Map aspect ratio to OpenAI size
  const sizeMap = {
    "1:1": "1024x1024",
    "3:2": "1536x1024",
    "2:3": "1024x1536",
    "16:9": "1536x1024",
    "9:16": "1024x1536",
    "4:3": "1536x1024",
    "3:4": "1024x1536",
  };
  const openaiSize = sizeMap[values.aspect] || "1024x1024";

  const params = {
    model,
    prompt: values.prompt,
    n: 1,
    size: openaiSize,
    quality: values.quality,
    output_format: "png",
  };

  if (values.transparent) {
    params.background = "transparent";
  }

  const result = await openai.images.generate(params);

  const imageBase64 = result.data[0].b64_json;
  if (!imageBase64) {
    console.error("Error: No image data returned by OpenAI API");
    process.exit(1);
  }

  const buffer = Buffer.from(imageBase64, "base64");
  writeFileSync(outputPath, buffer);

  return {
    text: null,
    method: values.transparent ? "openai-transparent" : "openai-standard",
  };
}

// ============================================================
// MAIN
// ============================================================
try {
  const result = backend === "gemini" ? await generateGemini() : await generateOpenAI();

  console.log(JSON.stringify({
    status: "success",
    outputPath,
    backend,
    model,
    aspect: values.aspect,
    size: values.size,
    transparent: values.transparent,
    method: result.method,
    hadInput: !!values.input,
    text: result.text,
  }));
} catch (err) {
  console.error(JSON.stringify({
    status: "error",
    message: err.message || String(err),
  }));
  process.exit(1);
}
