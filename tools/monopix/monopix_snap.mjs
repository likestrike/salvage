// MonoPix 의 Snap 과 같은 처리: fast-pixelizer 의 snap() 으로 격자를 찾아 고른 격자로 다시 그리고, 칸마다 한 픽셀로 줄인다.
// 사용: node monopix_snap.mjs <입력.png> <출력.png> [colorVariety=32]
import { readFileSync, writeFileSync } from 'node:fs';
import { PNG } from 'pngjs';
import { snap } from 'fast-pixelizer';

const [, , inPath, outPath, cv] = process.argv;
const src = PNG.sync.read(readFileSync(inPath));
const input = { data: new Uint8ClampedArray(src.data.buffer, src.data.byteOffset, src.data.length), width: src.width, height: src.height };
const t0 = Date.now();
const snapped = snap(input, { colorVariety: Number(cv || 32), output: 'original' });

// mono-pix/src/workers/pixelate.worker.ts 의 collapseToGrid 와 같은 방식: 칸마다 가장 많은 색
const { colCuts, rowCuts } = snapped;
const cols = colCuts.length - 1, rows = rowCuts.length - 1;
const out = new PNG({ width: cols, height: rows });
for (let r = 0; r < rows; r++) {
  for (let c = 0; c < cols; c++) {
    const freq = new Map();
    for (let y = rowCuts[r]; y < rowCuts[r + 1]; y++) {
      for (let x = colCuts[c]; x < colCuts[c + 1]; x++) {
        const i = (y * snapped.width + x) * 4;
        const k = ((snapped.data[i] << 24) | (snapped.data[i + 1] << 16) | (snapped.data[i + 2] << 8) | snapped.data[i + 3]) >>> 0;
        freq.set(k, (freq.get(k) || 0) + 1);
      }
    }
    let best = 0, n = 0;
    for (const [k, v] of freq) if (v > n) { best = k; n = v; }
    const o = (r * cols + c) * 4;
    out.data[o] = (best >>> 24) & 255; out.data[o + 1] = (best >>> 16) & 255; out.data[o + 2] = (best >>> 8) & 255; out.data[o + 3] = best & 255;
  }
}
writeFileSync(outPath, PNG.sync.write(out));
const widths = colCuts.slice(1).map((v, i) => v - colCuts[i]), heights = rowCuts.slice(1).map((v, i) => v - rowCuts[i]);
const uniq = (a) => [...new Set(a)].sort((x, y) => x - y).join('/');
console.log(JSON.stringify({ input: [src.width, src.height], output: [cols, rows], detectedResolution: snapped.detectedResolution,
  cellW: uniq(widths), cellH: uniq(heights), rawPerPixel: [(src.width / cols).toFixed(2), (src.height / rows).toFixed(2)],
  preservedSourceColors: snapped.preservedSourceColors, ms: Date.now() - t0 }));
