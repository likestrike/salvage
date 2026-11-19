// GIF 를 Playwright(Chromium)에서 프레임 단위로 풀어 한 장씩 늘어놓고 캡처한다.
//   node tools/gif_frames.cjs <out.png> <gif> [halves]
//   halves = 전후 비교 GIF(왼쪽 = 처음 시트, 오른쪽 = 지금)를 반으로 나눠 따로 잰다
// 프레임마다: 번호, 그림, 첫 프레임의 정수리 높이에 그은 가로선, 잰 값(정수리 y · 머리의 왼쪽 끝 x)을 함께 보여 준다.
// before_after GIF(왼쪽 = 처음 시트, 오른쪽 = 지금)는 반으로 나눠 따로 잰다.
const path = require('path');
const fs = require('fs');
const os = require('os');
// Playwright 를 찾는다: 프로젝트에 설치된 것 → PLAYWRIGHT_PATH → gstack 에 들어 있는 것
let chromium = null;
for (const m of ['playwright', process.env.PLAYWRIGHT_PATH, path.join(os.homedir(), '.claude/skills/gstack/node_modules/playwright')].filter(Boolean)) {
  try { ({ chromium } = require(m)); break; } catch (e) { /* 다음 후보 */ }
}
if (!chromium) { console.error('Playwright 를 찾지 못했다. npm i playwright 를 하거나 PLAYWRIGHT_PATH 로 위치를 알려 준다.'); process.exit(1); }

(async () => {
  const [, , out, gifPath, halves] = process.argv;
  const b64 = fs.readFileSync(gifPath).toString('base64');
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1900, height: 1000 } });
  // ImageDecoder(WebCodecs)는 보안 컨텍스트에서만 쓸 수 있어서, 가짜 https 주소로 빈 페이지를 내준다 (밖으로 나가는 요청은 없다)
  await page.route('https://frames.local/**', (route) => route.fulfill({ contentType: 'text/html; charset=utf-8',
    body: '<html><body style="margin:0;background:#101014;color:#ddd;font:13px monospace"><div id="root"></div></body></html>' }));
  await page.goto('https://frames.local/index.html');
  const info = await page.evaluate(async ({ b64, name, halves }) => {
    const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
    const dec = new ImageDecoder({ data: bytes, type: 'image/gif' });
    await dec.tracks.ready;
    const n = dec.tracks.selectedTrack.frameCount;
    const root = document.getElementById('root');
    const title = document.createElement('div');
    title.textContent = name + '  —  ' + n + ' 프레임';
    title.style.cssText = 'padding:6px 8px;color:#7ff5ee';
    root.appendChild(title);
    const wrap = document.createElement('div');
    wrap.style.cssText = 'display:flex;flex-wrap:wrap;gap:6px;padding:0 8px 8px';
    root.appendChild(wrap);
    const BG = [38, 36, 48], GROUND = [77, 73, 89];
    const isFig = (d, i) => !((d[i] === BG[0] && d[i + 1] === BG[1] && d[i + 2] === BG[2]) || (d[i] === GROUND[0] && d[i + 1] === GROUND[1] && d[i + 2] === GROUND[2]));
    const rows = [];
    let first = null;
    for (let k = 0; k < n; k++) {
      const { image } = await dec.decode({ frameIndex: k });
      const w = image.displayWidth, h = image.displayHeight;
      const c = document.createElement('canvas');
      c.width = w; c.height = h;
      const ctx = c.getContext('2d');
      ctx.drawImage(image, 0, 0);
      const d = ctx.getImageData(0, 0, w, h).data;
      // 반쪽마다 잰다: 정수리 y, 정수리에서 80px(확대된 px) 안의 왼쪽 끝과 오른쪽 끝, 발바닥 y
      const parts = halves ? [[0, w / 2], [w / 2, w]] : [[0, w]];
      const m = parts.map(([x0, x1]) => {
        let top = -1, bot = -1;
        for (let y = 0; y < h && top < 0; y++) for (let x = x0; x < x1; x++) if (isFig(d, (y * w + x) * 4)) { top = y; break; }
        for (let y = h - 1; y >= 0 && bot < 0; y--) for (let x = x0; x < x1; x++) if (isFig(d, (y * w + x) * 4)) { bot = y; break; }
        let l = 1e9, r = -1;
        for (let y = top; y < top + 80; y++) for (let x = x0; x < x1; x++) if (isFig(d, (y * w + x) * 4)) { if (x < l) l = x; if (x > r) r = x; }
        return { top, bot, l: l - x0, r: r - x0 };
      });
      if (!first) first = m;
      // 첫 프레임의 정수리 높이와 머리의 왼쪽 · 오른쪽 끝에 선을 긋는다 → 선에서 벗어난 만큼이 움직인 양이다
      parts.forEach(([x0, x1], j) => {
        ctx.fillStyle = 'rgba(255,80,80,0.9)'; ctx.fillRect(x0, first[j].top - 1, x1 - x0, 1);
        ctx.fillStyle = 'rgba(255,210,80,0.7)'; ctx.fillRect(x0 + first[j].r + 1, 0, 1, 120);
      });
      const cell = document.createElement('div');
      const cap = document.createElement('div');
      cap.textContent = '#' + k + '  ' + m.map((v, j) => (halves ? (j ? '지금 ' : '처음 ') : '') + '정수리 ' + (v.top - first[j].top >= 0 ? '+' : '') + (v.top - first[j].top) + ' 머리앞 ' + (v.r - first[j].r >= 0 ? '+' : '') + (v.r - first[j].r)).join(' | ');
      cap.style.cssText = 'padding:2px 0';
      cell.appendChild(cap); cell.appendChild(c); wrap.appendChild(cell);
      rows.push(m.map((v, j) => ({ top: v.top - first[j].top, front: v.r - first[j].r, bot: v.bot - first[j].bot })));
      image.close();
    }
    return { n, rows, h: document.documentElement.scrollHeight };
  }, { b64, name: path.basename(gifPath), halves: halves === 'halves' });
  await page.setViewportSize({ width: 1900, height: Math.min(4000, info.h + 10) });
  await page.screenshot({ path: out, fullPage: true });
  await browser.close();
  // 숫자는 확대된 px 이다 (도구의 GIF 는 4배) → 4로 나누면 게임의 px
  const z = 4;
  const side = (j) => info.rows.map((r) => r[j]);
  const show = (label, a) => console.log('  ' + label + '  정수리 ' + a.map((v) => (v.top / z)).join(' ') + '   머리 앞끝 ' + a.map((v) => (v.front / z)).join(' ') + '   발바닥 ' + a.map((v) => (v.bot / z)).join(' '));
  console.log(path.basename(gifPath) + ' — ' + info.n + ' 프레임 (게임 px, 첫 프레임과의 차이)');
  if (halves === 'halves') { show('처음', side(0)); show('지금', side(1)); } else show('    ', side(0));
})().catch((e) => { console.error('ERROR', e.message); process.exit(1); });
