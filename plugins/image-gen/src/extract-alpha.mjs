import sharp from "sharp";

/**
 * Two-pass alpha extraction: generate the same image on white and black
 * backgrounds, then compute true alpha from the pixel difference.
 */
export async function extractAlpha(imgOnWhitePath, imgOnBlackPath, outputPath) {
  const { data: dataWhite, info: meta } = await sharp(imgOnWhitePath)
    .ensureAlpha()
    .raw()
    .toBuffer({ resolveWithObject: true });

  const { data: dataBlack } = await sharp(imgOnBlackPath)
    .ensureAlpha()
    .raw()
    .toBuffer({ resolveWithObject: true });

  if (dataWhite.length !== dataBlack.length) {
    throw new Error("Dimension mismatch: images must be identical size");
  }

  const outputBuffer = Buffer.alloc(dataWhite.length);
  const bgDist = Math.sqrt(3 * 255 * 255); // ~441.67

  for (let i = 0; i < meta.width * meta.height; i++) {
    const offset = i * 4;

    const rW = dataWhite[offset], gW = dataWhite[offset + 1], bW = dataWhite[offset + 2];
    const rB = dataBlack[offset], gB = dataBlack[offset + 1], bB = dataBlack[offset + 2];

    const pixelDist = Math.sqrt((rW - rB) ** 2 + (gW - gB) ** 2 + (bW - bB) ** 2);

    let alpha = Math.max(0, Math.min(1, 1 - pixelDist / bgDist));

    let rOut = 0, gOut = 0, bOut = 0;
    if (alpha > 0.01) {
      rOut = rB / alpha;
      gOut = gB / alpha;
      bOut = bB / alpha;
    }

    outputBuffer[offset]     = Math.round(Math.min(255, rOut));
    outputBuffer[offset + 1] = Math.round(Math.min(255, gOut));
    outputBuffer[offset + 2] = Math.round(Math.min(255, bOut));
    outputBuffer[offset + 3] = Math.round(alpha * 255);
  }

  await sharp(outputBuffer, {
    raw: { width: meta.width, height: meta.height, channels: 4 },
  })
    .png()
    .toFile(outputPath);
}
