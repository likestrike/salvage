// MonoPix 의 Clean 과 같은 처리: fast-pixelizer 의 pixelate(mode: 'clean') 로 칸마다 정해진 해상도로 줄인다 (칸마다 가장 많은 색).
// 사용: node monopix_clean.mjs <투명 배경 시트.png> <출력.png> <열> <행> <칸 해상도> [clean|detail]
import { readFileSync, writeFileSync } from 'node:fs';
import { PNG } from 'pngjs';
import { pixelate } from 'fast-pixelizer';
const [, , inPath, outPath, colsS, rowsS, resS, mode] = process.argv;
const src = PNG.sync.read(readFileSync(inPath));
const C = Number(colsS), R = Number(rowsS), N = Number(resS), cw = src.width / C, ch = src.height / R;
const out = new PNG({ width: C * N, height: R * N });
for (let r = 0; r < R; r++) for (let c = 0; c < C; c++) {
  const data = new Uint8ClampedArray(cw * ch * 4);
  for (let y = 0; y < ch; y++) { const s = ((r * ch + y) * src.width + c * cw) * 4; data.set(src.data.subarray(s, s + cw * 4), y * cw * 4); }
  const px = pixelate({ data, width: cw, height: ch }, { resolution: { cols: N, rows: N }, mode: mode || 'clean', output: 'resized' });
  for (let y = 0; y < N; y++) out.data.set(px.data.subarray(y * N * 4, (y + 1) * N * 4), ((r * N + y) * out.width + c * N) * 4);
}
writeFileSync(outPath, PNG.sync.write(out));
console.log(`[saved] ${outPath} ${out.width}x${out.height} (칸 ${cw}x${ch} → ${N}x${N}, ${mode || 'clean'})`);
