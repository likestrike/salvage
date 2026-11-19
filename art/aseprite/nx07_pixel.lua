--[[
NX-07 픽셀 스프라이트 — Aseprite Lua 스크립트만으로 빈 캔버스에서 그린다.
사양: art/prompts/nx07_pixel_spec.txt

Aseprite 에서 실행:
  Aseprite.exe -b --script art/aseprite/nx07_pixel.lua
  → 같은 폴더에 nx07_pixel.aseprite, nx07_pixel_sheet.png, nx07_pixel.json
  애니메이션별 GIF: Aseprite.exe -b art/aseprite/nx07_pixel.aseprite --tag walk --scale 4 --save-as walk.gif

이미지 파일을 읽지 않는다. 모든 픽셀은 아래 코드가 계산한다:
  관절 각도(포즈) → 관절 위치 → 부위 도형(캡슐·타원)을 뒤에서 앞으로 칠함(3단 명암)
  → 1px 윤곽선 → 작은 디테일(눈, 엠블럼, 불빛) → 이펙트(불꽃, 섬광, 먼지, 불똥)
]]

local W, H = 96, 96
local GROUND = 88            -- 이 행부터 아래는 땅. 발바닥은 87행
local BASE_X = 44            -- 골반의 기본 x

-- ───────── 팔레트 (0 = 투명, 1~15 = 색) ─────────
local HEX = {
  "16161C", "2E2E37", "474752",              -- 1 윤곽선, 2 슈트 어둠, 3 슈트
  "4A4F37", "6F7457", "98A07A",              -- 4 국방 어둠, 5 국방, 6 국방 밝음
  "A9AAA6", "ECEBE6",                        -- 7 흰 판 그늘, 8 흰 판
  "2A9FA6", "61E2DD",                        -- 9 시안 어둠, 10 시안
  "C98F78", "F4D2B8",                        -- 11 피부 그늘, 12 피부
  "F08A2A", "FFE07A", "FFFFFF",              -- 13 주황, 14 노랑, 15 흰 빛
}
local OUT, SUIT_D, SUIT, OLV_D, OLV, OLV_L, WHT_D, WHT, CY_D, CY, SKN_D, SKN, ORG, YEL, HI =
  1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15

-- 명암 단계: { 어둠, 기본, 밝음 }
local R_OLV      = { OLV_D, OLV, OLV_L }
local R_OLV_FAR  = { OLV_D, OLV_D, OLV }
local R_WHT      = { WHT_D, WHT, HI }
local R_WHT_FAR  = { WHT_D, WHT_D, WHT }
local R_SUIT     = { SUIT_D, SUIT, SUIT }
local R_SUIT_FAR = { SUIT_D, SUIT_D, SUIT }
local R_SKIN     = { SKN_D, SKN, SKN }

-- 몸 치수 (px)
local TORSO, THIGH, SHIN, UPPER, FORE, CANNON = 17, 13, 13, 9, 9, 12
local LX, LY = -0.55, -0.83                      -- 빛 방향 (왼쪽 위)

local sin, cos, sqrt, floor, ceil, max, min, abs = math.sin, math.cos, math.sqrt, math.floor, math.ceil, math.max, math.min, math.abs
local function rad(d) return d * math.pi / 180 end

-- ───────── 그림판 ─────────
local function newbuf()
  local b = { c = {}, d = {}, g = {}, n = 0 }
  for y = 0, H - 1 do
    b.c[y], b.d[y], b.g[y] = {}, {}, {}
    for x = 0, W - 1 do b.c[y][x], b.d[y][x], b.g[y][x] = 0, 0, 0 end
  end
  return b
end

local function plot(b, x, y, col, layer, grp)
  if x < 0 or y < 0 or x >= W or y >= H or y >= GROUND then return end
  if layer >= b.d[y][x] then b.c[y][x], b.d[y][x], b.g[y][x] = col, layer, grp end
end

local function shade(ramp, nx, ny, edge)
  local s = nx * LX + ny * LY
  if edge > 0.42 and s > 0.38 then return ramp[3] end
  if edge > 0.30 and s < -0.22 then return ramp[1] end
  return ramp[2]
end

local function nextlayer(b) b.n = b.n + 1; return b.n end

-- 캡슐: a → b 를 잇는 굵은 막대 (반지름 ra → rb). opt.color(t, ex, ey, dist, r) 로 색을 바꾸고, opt.clip 으로 자른다.
local function capsule(b, ax, ay, bx, by, ra, rb, ramp, opt)
  opt = opt or {}
  local layer = nextlayer(b)
  local grp = opt.group or layer
  local R = max(ra, rb) + 1
  local dx, dy = bx - ax, by - ay
  local len2 = dx * dx + dy * dy
  for y = floor(min(ay, by) - R), ceil(max(ay, by) + R) do
    for x = floor(min(ax, bx) - R), ceil(max(ax, bx) + R) do
      local px, py = x + 0.5, y + 0.5
      local t = 0
      if len2 > 0 then t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / len2)) end
      local cx, cy = ax + dx * t, ay + dy * t
      local r = ra + (rb - ra) * t
      local ex, ey = px - cx, py - cy
      local dist = sqrt(ex * ex + ey * ey)
      if dist <= r and not (opt.clip and opt.clip(px, py, t, ex, ey)) then
        local col = opt.color and opt.color(t, ex, ey, dist, r)
        if not col then
          local nx, ny = 0, 0
          if dist > 0 then nx, ny = ex / dist, ey / dist end
          col = shade(ramp, nx, ny, dist / r)
        end
        plot(b, x, y, col, layer, grp)
      end
    end
  end
  return grp
end

-- 회전한 타원: rx 는 앞뒤(u), ry 는 위아래(v) 반지름, rot 은 시계 방향 각도
local function ellipse(b, cx, cy, rx, ry, rot, ramp, opt)
  opt = opt or {}
  local layer = nextlayer(b)
  local grp = opt.group or layer
  local c, s = cos(rad(rot)), sin(rad(rot))
  local R = max(rx, ry) + 1
  for y = floor(cy - R), ceil(cy + R) do
    for x = floor(cx - R), ceil(cx + R) do
      local px, py = x + 0.5 - cx, y + 0.5 - cy
      local u, v = px * c + py * s, -px * s + py * c
      local q = (u / rx) ^ 2 + (v / ry) ^ 2
      if q <= 1 then
        local nu, nv = u / rx, v / ry
        local nx, ny = nu * c - nv * s, nu * s + nv * c
        local l = sqrt(nx * nx + ny * ny)
        if l > 0 then nx, ny = nx / l, ny / l end
        plot(b, x, y, (opt.color and opt.color(u, v)) or shade(ramp, nx, ny, sqrt(q)), layer, grp)
      end
    end
  end
  return grp
end

-- 점과 선분 사이 거리, 선분 위 위치
local function segdist(px, py, ax, ay, bx, by)
  local dx, dy = bx - ax, by - ay
  local t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
  local ex, ey = px - (ax + dx * t), py - (ay + dy * t)
  return sqrt(ex * ex + ey * ey), t
end

-- 머리: 머리 중심 기준 좌표 (u = 얼굴 쪽, v = 아래쪽). rot 만큼 시계 방향으로 기울인다.
local function head(b, hx, hy, rot)
  local layer = nextlayer(b)
  local c, s = cos(rad(rot)), sin(rad(rot))
  for y = floor(hy - 10), ceil(hy + 10) do
    for x = floor(hx - 10), ceil(hx + 10) do
      local px, py = x + 0.5 - hx, y + 0.5 - hy
      local u, v = px * c + py * s, -px * s + py * c
      local col
      local hu, hv = u / 6.8, (v + 0.7) / 6.4                       -- 헬멧
      local q = hu * hu + hv * hv
      local face = u > 0.5 and v > 0.0 and ((u - 1.2) / 4.9) ^ 2 + ((v - 1.3) / 4.8) ^ 2 <= 1
      local fd, ft = segdist(u, v, -3.0, -0.5, -8.2, -4.3)          -- 귀 장치에서 뒤로 뻗은 핀
      local fin = fd <= 1.75 - 0.7 * ft
      local ed = sqrt((u + 2.3) ^ 2 + (v - 1.2) ^ 2)                  -- 귀 장치
      if face and not (ed <= 2.4) then
        col = (v < 1.6 or u < 1.6) and SKN_D or SKN                   -- 헬멧 아래 그늘
      elseif ed <= 2.4 then
        col = (ed <= 1.2) and SUIT or ((u + 2.3) + (v - 1.2) * 0.6 < 0 and WHT or WHT_D)
      elseif q <= 1 then
        if v > -1.5 and v < -0.1 and u > -0.6 then
          col = SUIT_D                                                -- 바이저 띠
        else
          local nx, ny = hu * c - hv * s, hu * s + hv * c
          local l = sqrt(nx * nx + ny * ny); if l > 0 then nx, ny = nx / l, ny / l end
          col = shade(R_OLV, nx, ny, sqrt(q))
        end
      elseif fin then
        col = (ft < 0.5) and WHT or WHT_D
      end
      if col then plot(b, x, y, col, layer, layer) end
    end
  end
  return layer
end

-- 윤곽선: 투명과 맞닿거나, 다른 부위의 뒤쪽 픽셀과 맞닿은 앞쪽 부위의 가장자리를 1px 선으로
local function outline(b)
  local mark = {}
  for y = 0, H - 1 do
    for x = 0, W - 1 do
      if b.c[y][x] ~= 0 then
        local d, g = b.d[y][x], b.g[y][x]
        for _, o in ipairs({ { 1, 0 }, { -1, 0 }, { 0, 1 }, { 0, -1 } }) do
          local nx, ny = x + o[1], y + o[2]
          local edge
          if nx < 0 or ny < 0 or nx >= W or ny >= H or ny >= GROUND then
            edge = ny >= GROUND and false or true                   -- 땅에 닿은 바닥 줄도 선이 된다 (아래 처리)
            if ny >= GROUND then edge = true end
          elseif b.c[ny][nx] == 0 then
            edge = true
          elseif b.g[ny][nx] ~= g and b.d[ny][nx] < d then
            edge = true
          end
          if edge then mark[#mark + 1] = { x, y }; break end
        end
      end
    end
  end
  for _, p in ipairs(mark) do b.c[p[2]][p[1]] = OUT end
end

-- 디테일: 지정한 부위의 픽셀 위에만 칠한다 (윤곽선 위에는 칠하지 않는다)
local function paint(b, x, y, col, grp)
  x, y = floor(x), floor(y)
  if x < 0 or y < 0 or x >= W or y >= H then return end
  if b.g[y][x] == grp and b.c[y][x] ~= OUT and b.c[y][x] ~= 0 then b.c[y][x] = col end
end

-- 이펙트: 윤곽선 없이 맨 앞에 칠한다
local FX = 100000
local function fxplot(b, x, y, col)
  x, y = floor(x), floor(y)
  if x < 0 or y < 0 or x >= W or y >= H or y >= GROUND then return end
  b.c[y][x], b.d[y][x], b.g[y][x] = col, FX, -1
end
local function fxdisc(b, cx, cy, r, col)
  for y = floor(cy - r), ceil(cy + r) do
    for x = floor(cx - r), ceil(cx + r) do
      if (x + 0.5 - cx) ^ 2 + (y + 0.5 - cy) ^ 2 <= r * r then fxplot(b, x, y, col) end
    end
  end
end
local function fxline(b, ax, ay, bx, by, r, col)
  local n = ceil(max(abs(bx - ax), abs(by - ay)) * 2) + 1
  for i = 0, n do
    local t = i / n
    fxdisc(b, ax + (bx - ax) * t, ay + (by - ay) * t, r, col)
  end
end

-- ───────── 포즈 → 관절 ─────────
local function ik(hx, hy, tx, ty, l1, l2)
  -- 2관절 IK. 무릎은 앞(+x)으로 굽는다.
  local dx, dy = tx - hx, ty - hy
  local d = sqrt(dx * dx + dy * dy)
  d = min(d, l1 + l2 - 0.01)
  local a = math.atan(dy, dx)
  local k = math.acos(max(-1, min(1, (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d))))
  local k1x, k1y = hx + cos(a + k) * l1, hy + sin(a + k) * l1
  local k2x, k2y = hx + cos(a - k) * l1, hy + sin(a - k) * l1
  if k2x > k1x then return k2x, k2y end
  return k1x, k1y
end

local function joints(P)
  local J = {}
  local t = rad(P.torso)
  J.up = { sin(t), -cos(t) }                -- 골반 → 목
  J.fw = { cos(t), sin(t) }                 -- 몸의 앞쪽
  J.pel = { P.x, P.y }
  local function at(base, f, u) return { base[1] + J.fw[1] * f + J.up[1] * u, base[2] + J.fw[2] * f + J.up[2] * u } end
  J.at = at
  J.neck = at(J.pel, 0.4, TORSO)
  J.hipj = at(J.pel, 0.0, -1.8)
  J.shN = at(J.pel, 0.8, TORSO - 3.2)
  J.shF = at(J.pel, -1.2, TORSO - 3.6)
  local hr = P.head or P.torso * 0.5
  J.headrot = hr
  J.head = { J.neck[1] + sin(rad(hr)) * 7.6 + (P.hx or 0), J.neck[2] - cos(rad(hr)) * 7.6 + (P.hy or 0) }
  for _, side in ipairs({ "nl", "fl" }) do
    local L = P[side]
    local k, a = {}, {}
    if L.ax then
      k[1], k[2] = ik(J.hipj[1], J.hipj[2], L.ax, L.ay, THIGH, SHIN)
      a = { L.ax, L.ay }
    else
      local th = rad(L.thigh)
      k = { J.hipj[1] + sin(th) * THIGH, J.hipj[2] + cos(th) * THIGH }
      local sh = rad(L.thigh - L.knee)
      a = { k[1] + sin(sh) * SHIN, k[2] + cos(sh) * SHIN }
    end
    J[side] = { knee = k, ankle = a, foot = L.foot or 0 }
  end
  for _, side in ipairs({ "na", "fa" }) do
    local A = P[side]
    local s0 = (side == "na") and J.shN or J.shF
    local a1, a2 = rad(A.sh), rad(A.sh + A.el)
    local e = { s0[1] + sin(a1) * UPPER, s0[2] + cos(a1) * UPPER }
    local len = (side == "na") and CANNON or FORE
    local w = { e[1] + sin(a2) * len, e[2] + cos(a2) * len }
    J[side] = { sh = s0, elbow = e, wrist = w, dir = { sin(a2), cos(a2) } }
  end
  return J
end

-- ───────── 캐릭터 그리기 (뒤 → 앞) ─────────
local function boot(b, ankle, footdeg, ramp)
  local f = rad(footdeg)
  local fd = { cos(f), sin(f) }
  local dn = { -sin(f), cos(f) }
  local c0 = { ankle[1] + dn[1] * 2.0, ankle[2] + dn[2] * 2.0 }
  local heel = { c0[1] - fd[1] * 2.4, c0[2] - fd[2] * 2.4 }
  local toe = { c0[1] + fd[1] * 5.0, c0[2] + fd[2] * 5.0 }
  return capsule(b, heel[1], heel[2], toe[1], toe[2], 3.7, 3.3, ramp, {
    clip = function(px, py) return (px - c0[1]) * dn[1] + (py - c0[2]) * dn[2] > 2.3 end,   -- 평평한 밑창
  })
end

local function leg(b, J, side, far)
  local L = J[side]
  local rs, ro, rw = far and R_SUIT_FAR or R_SUIT, far and R_OLV_FAR or R_OLV, far and R_WHT_FAR or R_WHT
  local g = {}
  g.thigh = capsule(b, J.hipj[1], J.hipj[2], L.knee[1], L.knee[2], 3.2, 2.7, rs)
  if not far then g.hip = ellipse(b, J.pel[1] + J.fw[1] * 0.6, J.pel[2] + J.fw[2] * 0.6 - 0.4, 2.7, 2.5, 0, rw) end
  g.shin = capsule(b, L.knee[1], L.knee[2], L.ankle[1], L.ankle[2], 2.8, 3.8, ro)
  g.boot = boot(b, L.ankle, L.foot, ro)
  g.knee = ellipse(b, L.knee[1] + 0.5, L.knee[2], 2.7, 2.5, 0, rw)
  return g
end

local function draw_character(b, P)
  local J = joints(P)
  local G = { J = J }
  -- 먼 팔
  local fa = J.fa
  capsule(b, fa.sh[1], fa.sh[2], fa.elbow[1], fa.elbow[2], 2.2, 2.0, R_SUIT_FAR)
  capsule(b, fa.elbow[1], fa.elbow[2], fa.wrist[1], fa.wrist[2], 2.5, 2.8, R_WHT_FAR)
  ellipse(b, fa.wrist[1] + fa.dir[1] * 1.4, fa.wrist[2] + fa.dir[2] * 1.4, 2.8, 2.8, 0, R_SUIT_FAR)
  -- 먼 다리
  G.fl = leg(b, J, "fl", true)
  -- 배낭, 목, 몸통
  local bp = J.at(J.pel, -5.6, 11.0)
  G.pack = ellipse(b, bp[1], bp[2], 2.8, 4.6, P.torso, R_OLV_FAR)
  G.packpos = bp
  local hb = { J.neck[1] + J.up[1] * 2.5, J.neck[2] + J.up[2] * 2.5 }
  capsule(b, J.neck[1], J.neck[2], hb[1], hb[2], 2.1, 2.0, R_SUIT)
  local p0, p1 = J.at(J.pel, 0, 1.5), J.at(J.pel, 0.2, 9.0)
  capsule(b, p0[1], p0[2], p1[1], p1[2], 4.1, 3.8, R_SUIT)
  ellipse(b, J.pel[1], J.pel[2], 4.9, 3.4, P.torso, R_SUIT)
  local ch = J.at(J.pel, 1.0, 11.2)
  G.chest = ellipse(b, ch[1], ch[2], 6.0, 6.8, P.torso, R_OLV)
  G.chestpos = ch
  -- 가까운 다리
  G.nl = leg(b, J, "nl", false)
  -- 머리
  G.head = head(b, J.head[1], J.head[2], J.headrot)
  -- 가까운 팔: 위팔 → 주포 → 어깨 장갑
  local na = J.na
  capsule(b, na.sh[1], na.sh[2], na.elbow[1], na.elbow[2], 2.5, 2.4, R_SUIT)
  G.cannon = capsule(b, na.elbow[1], na.elbow[2], na.wrist[1], na.wrist[2], 3.2, 3.4, R_OLV, {
    color = function(t, ex, ey, dist, r)
      if (t > 0.10 and t < 0.22) or (t > 0.60 and t < 0.70) then
        local s = (ex * LX + ey * LY) / max(dist, 0.01)
        return (s < -0.2 and dist / r > 0.3) and WHT_D or WHT                -- 흰 고리
      end
      if t > 0.93 then return SUIT end                                       -- 포구 테
    end,
  })
  local sp = J.at(na.sh, -0.3, 0.8)
  ellipse(b, sp[1], sp[2], 4.3, 4.0, P.torso, R_OLV)
  return G
end

-- ───────── 디테일 ─────────
local function details(b, P, G)
  local J = G.J
  -- 머리: 눈, 엠블럼, 귀 장치 불빛
  local c, s = cos(rad(J.headrot)), sin(rad(J.headrot))
  local hx, hy = J.head[1], J.head[2]
  for y = floor(hy - 9), ceil(hy + 9) do
    for x = floor(hx - 9), ceil(hx + 9) do
      local px, py = x + 0.5 - hx, y + 0.5 - hy
      local u, v = px * c + py * s, -px * s + py * c
      if u > 2.7 and u < 4.3 and v > 0.4 and v < 2.7 then              -- 눈
        local col = (P.eye == "closed") and ((v < 1.6) and SUIT_D or SKN)
                 or (P.eye == "off") and ((v < 1.6) and SUIT or SUIT_D)
                 or ((v < 1.5) and CY or CY_D)
        paint(b, x, y, col, G.head)
      end
      local ev = -3.6
      if v > ev - 1.3 and v < ev + 1.6 then                             -- 이마의 역삼각 엠블럼
        local half = 1.9 * (ev + 1.6 - v) / 2.9
        if abs(u - 3.4) <= half then paint(b, x, y, (v < ev - 0.2) and CY or CY_D, G.head) end
      end
      if (u + 2.3) ^ 2 + (v - 1.2) ^ 2 <= 0.7 then paint(b, x, y, (P.eye == "off") and SUIT_D or CY, G.head) end
    end
  end
  -- 가슴 코어
  local cc = J.at(G.chestpos, 3.0, 0.8)
  for _, o in ipairs({ { 0, 0 }, { 0, 1 } }) do paint(b, cc[1] + o[1], cc[2] + o[2], (P.eye == "off") and SUIT or CY, G.chest) end
  -- 배낭 불빛
  local pc = J.at(G.packpos, -1.0, 0.5)
  paint(b, pc[1], pc[2], CY, G.pack)
  -- 주포: 옆 줄과 포구
  local na = J.na
  for i = 0, 5 do
    local t = 0.33 + i * 0.04
    paint(b, na.elbow[1] + (na.wrist[1] - na.elbow[1]) * t, na.elbow[2] + (na.wrist[2] - na.elbow[2]) * t, CY, G.cannon)
  end
  local m = { na.wrist[1] - na.dir[1] * 0.6, na.wrist[2] - na.dir[2] * 0.6 }
  paint(b, m[1], m[2], (P.eye == "off") and SUIT_D or CY, G.cannon)
  -- 가까운 무릎·부츠 불빛
  local k = J.nl.knee
  paint(b, k[1] + 0.6, k[2] + 0.2, CY, G.nl.knee)
  local a = J.nl.ankle
  paint(b, a[1] + 1.5, a[2] + 2.0, CY, G.nl.boot)
end

-- ───────── 이펙트 ─────────
local function hash(n) local v = sin(n * 12.9898) * 43758.5453; return v - floor(v) end

local function effects(b, P, G)
  local J = G.J
  for _, e in ipairs(P.fx or {}) do
    if e[1] == "flame" and e[2] > 0 then                               -- 배낭 추진 불꽃 (뒤쪽 아래로)
      local o = J.at(G.packpos, -1.8, -2.0)
      local dx, dy = -J.fw[1] * 0.92 + J.up[1] * -0.38, -J.fw[2] * 0.92 + J.up[2] * -0.38
      local L = e[2]
      for i = 0, ceil(L) do
        local t = i / L
        fxdisc(b, o[1] + dx * i, o[2] + dy * i, max(0.6, 2.8 * (1 - t)), CY_D)
      end
      for i = 0, ceil(L * 0.75) do
        local t = i / (L * 0.75)
        fxdisc(b, o[1] + dx * i, o[2] + dy * i, max(0.5, 1.9 * (1 - t)), CY)
      end
      fxline(b, o[1], o[2], o[1] + dx * L * 0.4, o[2] + dy * L * 0.4, 0.7, HI)
    elseif e[1] == "muzzle" then                                        -- 포구 섬광
      local na = J.na
      local mx, my = na.wrist[1] + na.dir[1] * 1.5, na.wrist[2] + na.dir[2] * 1.5
      local S = e[2]
      local base = math.atan(na.dir[2], na.dir[1])
      for i, ang in ipairs({ -60, -30, 0, 30, 60 }) do
        local L = S * ({ 0.55, 0.8, 1.0, 0.8, 0.55 })[i]
        local a = base + rad(ang)
        fxline(b, mx, my, mx + cos(a) * L, my + sin(a) * L, 0.55, CY)
      end
      fxdisc(b, mx + na.dir[1] * 1.0, my + na.dir[2] * 1.0, S * 0.32, HI)
    elseif e[1] == "bullet" then
      local na = J.na
      local bx, by = na.wrist[1] + na.dir[1] * 13, na.wrist[2] + na.dir[2] * 13
      fxline(b, bx - na.dir[1] * 2, by - na.dir[2] * 2, bx + na.dir[1] * 2, by + na.dir[2] * 2, 1.7, CY)
      fxline(b, bx - na.dir[1] * 1.5, by - na.dir[2] * 1.5, bx + na.dir[1] * 1.5, by + na.dir[2] * 1.5, 0.8, HI)
    elseif e[1] == "smoke" then
      local na = J.na
      local mx, my = na.wrist[1] + na.dir[1] * 2, na.wrist[2] + na.dir[2] * 2
      fxdisc(b, mx + 1, my - 2, 1.6, WHT_D)
      fxdisc(b, mx + 3, my - 4, 1.2, WHT_D)
      fxplot(b, mx + 0.5, my - 3, WHT)
    elseif e[1] == "dust" then                                          -- 발밑 먼지: { "dust", 기준(nl/fl), 크기, 쪽(-1 뒤, 1 앞) }
      local a = J[e[2]].ankle
      local S, side = e[3], e[4] or 1
      local gx, gy = a[1] + side * 5, GROUND - 1.6
      fxdisc(b, gx, gy, 1.9 * S, WHT_D)
      fxdisc(b, gx + side * 3.2 * S, gy - 0.8, 1.4 * S, WHT_D)
      fxdisc(b, gx + side * 5.6 * S, gy - 0.2, 1.0 * S, WHT_D)
      fxplot(b, gx - 0.6, gy - 1.2 * S, WHT)
    elseif e[1] == "speed" then                                         -- 속도선 (몸 뒤로 가는 흰 선 몇 줄)
      for i = 1, 3 do
        local y = J.pel[2] - 8 + i * 4
        local x0 = J.pel[1] - 12 - i * 2
        fxline(b, x0 - 6 + i, y, x0, y, 0.45, WHT)
      end
    elseif e[1] == "sparks" then                                        -- 불똥
      local c = G.chestpos
      for k = 1, e[2] do
        local a = hash(k * 7 + e[3]) * math.pi * 2
        local r0 = 3 + hash(k * 13 + e[3]) * 6
        local L = 2 + hash(k * 3 + e[3]) * 2
        local x0, y0 = c[1] + cos(a) * r0, c[2] + sin(a) * r0
        fxline(b, x0, y0, x0 + cos(a) * L, y0 + sin(a) * L, 0.45, ORG)
        fxplot(b, x0 + cos(a) * (L + 1), y0 + sin(a) * (L + 1), YEL)
      end
    end
  end
end

-- ───────── 한 프레임 ─────────
local function bottom_row(b)
  for y = H - 1, 0, -1 do
    for x = 0, W - 1 do if b.c[y][x] ~= 0 then return y end end
  end
  return GROUND - 1
end

local function render(P)
  -- 1차: 발(가장 낮은 곳)이 87행에 닿도록 몸 전체의 높이를 정수 픽셀만큼 옮긴다
  local probe = newbuf()
  local saveG = GROUND
  GROUND = H + 50
  draw_character(probe, P)
  GROUND = saveG
  local dy = (GROUND - 1) - bottom_row(probe)
  local Q = {}
  for k, v in pairs(P) do Q[k] = v end
  Q.y = P.y + dy
  for _, side in ipairs({ "nl", "fl" }) do
    if P[side].ax then Q[side] = { ax = P[side].ax, ay = P[side].ay + dy, foot = P[side].foot } end
  end
  -- 2차: 그리기 → 윤곽선 → 디테일 → (번쩍임) → 이펙트
  local b = newbuf()
  local G = draw_character(b, Q)
  outline(b)
  details(b, Q, G)
  if Q.flash then
    for y = 0, H - 1 do for x = 0, W - 1 do
      local c = b.c[y][x]
      if c ~= 0 and c ~= OUT then b.c[y][x] = HI end
    end end
  end
  effects(b, Q, G)
  return b
end

-- ───────── 포즈 ─────────
local function pose(t)
  local p = {
    x = BASE_X, y = 55.5, torso = 4, head = nil,
    nl = { ax = BASE_X + 8, ay = 84 }, fl = { ax = BASE_X - 9, ay = 84 },
    na = { sh = 22, el = 62 }, fa = { sh = -6, el = 40 },
    fx = {}, eye = "open", flash = false,
  }
  for k, v in pairs(t or {}) do p[k] = v end
  return p
end

local ANIMS = {}
local function anim(name, frames) ANIMS[#ANIMS + 1] = { name = name, frames = frames } end

-- 1 대기: 숨쉬기 (발은 제자리, 몸이 1px 오르내림)
do
  local fr = {}
  for i, k in ipairs({ 0, 1, 1, 0 }) do
    fr[i] = { dur = 0.2, P = pose({ y = 55.5 + k, head = 2 + k, na = { sh = 22 + k * 2, el = 62 - k }, fa = { sh = -6 + k, el = 40 - k * 4 } }) }
  end
  anim("idle", fr)
end

-- 2 걷기: 8프레임 (가까운 다리 기준 접지 · 내려앉음 · 지나감 · 올라섬 · 반대 접지 …)
do
  local N = { { 24, 6, -10 }, { 15, 16, 0 }, { 0, 8, 0 }, { -14, 12, 10 }, { -24, 10, 22 }, { -18, 36, 14 }, { 10, 60, 8 }, { 24, 32, -4 } }
  local fr = {}
  for i = 1, 8 do
    local n, f = N[i], N[((i + 3) % 8) + 1]
    local sw = f[1]
    fr[i] = { dur = 0.09, P = pose({
      y = 55.5, torso = 7, head = 4,
      nl = { thigh = n[1], knee = n[2], foot = n[3] }, fl = { thigh = f[1], knee = f[2], foot = f[3] },
      na = { sh = 26, el = 60 }, fa = { sh = -sw * 0.9, el = 30 },
    }) }
  end
  anim("walk", fr)
end

-- 3 대시: 웅크림 → 돌진 2 → 급제동 (배낭에서 추진 불꽃)
anim("dash", {
  { dur = 0.08, P = pose({ torso = 18, head = 8, nl = { thigh = 34, knee = 52, foot = -5 }, fl = { thigh = -26, knee = 40, foot = 20 },
                           na = { sh = 48, el = 40 }, fa = { sh = -30, el = 40 }, fx = { { "flame", 5 } } }) },
  { dur = 0.07, P = pose({ torso = 30, head = 14, nl = { thigh = 48, knee = 72, foot = 6 }, fl = { thigh = -50, knee = 18, foot = 30 },
                           na = { sh = 64, el = 24 }, fa = { sh = -46, el = 30 }, fx = { { "flame", 13 } } }) },
  { dur = 0.07, P = pose({ torso = 31, head = 14, nl = { thigh = 50, knee = 72, foot = 6 }, fl = { thigh = -52, knee = 16, foot = 30 },
                           na = { sh = 64, el = 24 }, fa = { sh = -48, el = 30 }, fx = { { "flame", 16 } } }) },
  { dur = 0.10, P = pose({ torso = 8, head = 2, nl = { thigh = 32, knee = 16, foot = -10 }, fl = { thigh = -14, knee = 40, foot = 18 },
                           na = { sh = 40, el = 45 }, fa = { sh = -10, el = 40 }, fx = { { "flame", 3 }, { "dust", "nl", 1.0, 1 } } }) },
})

-- 4 회피: 회피용 짧은 대시. 불꽃 없음, 어깨부터 낮게 파고들고 주포는 가슴에 접는다
anim("dodge", {
  { dur = 0.06, P = pose({ torso = 16, head = 18, nl = { thigh = 26, knee = 44 }, fl = { thigh = -14, knee = 40, foot = 14 },
                           na = { sh = 12, el = 118 }, fa = { sh = 30, el = 30 } }) },
  { dur = 0.06, P = pose({ torso = 40, head = 34, nl = { thigh = 52, knee = 74 }, fl = { thigh = -42, knee = 22, foot = 24 },
                           na = { sh = 22, el = 118 }, fa = { sh = 62, el = 10 }, fx = { { "speed" } } }) },
  { dur = 0.08, P = pose({ torso = 56, head = 48, nl = { thigh = 64, knee = 96 }, fl = { thigh = -58, knee = 30, foot = 40 },
                           na = { sh = 28, el = 116 }, fa = { sh = 84, el = 0 }, fx = { { "speed" }, { "dust", "fl", 1.0, -1 } } }) },
  { dur = 0.07, P = pose({ torso = 36, head = 28, nl = { thigh = 40, knee = 64 }, fl = { thigh = -28, knee = 56, foot = 20 },
                           na = { sh = 20, el = 110 }, fa = { sh = 50, el = 20 }, fx = { { "dust", "fl", 0.7, -1 } } }) },
  { dur = 0.09, P = pose({ torso = 12, head = 6, nl = { thigh = 30, knee = 20, foot = -8 }, fl = { thigh = -12, knee = 46, foot = 16 },
                           na = { sh = 24, el = 80 }, fa = { sh = 10, el = 40 }, fx = { { "dust", "nl", 1.0, 1 } } }) },
  { dur = 0.12, P = pose({ torso = 5, head = 2 }) },
})

-- 5 공격: 조준 → 발사 → 반동 → 복귀
do
  local stance = function(t)
    t.nl = { ax = BASE_X + 8, ay = 84 }; t.fl = { ax = BASE_X - 9, ay = 84 }
    return pose(t)
  end
  anim("attack", {
    { dur = 0.08, P = stance({ y = 56, torso = 2, head = 0, na = { sh = 64, el = 26 }, fa = { sh = -20, el = 50 } }) },
    { dur = 0.06, P = stance({ y = 56, torso = 2, head = 0, na = { sh = 64, el = 26 }, fa = { sh = -20, el = 50 }, fx = { { "muzzle", 9 }, { "bullet" } } }) },
    { dur = 0.08, P = stance({ x = BASE_X - 1, y = 56, torso = -3, head = -3, na = { sh = 60, el = 27 }, fa = { sh = -24, el = 50 }, fx = { { "smoke" } } }) },
    { dur = 0.12, P = stance({ y = 56, torso = 1, head = 0, na = { sh = 63, el = 27 }, fa = { sh = -20, el = 50 } }) },
  })
end

-- 6 피격: 뒤로 젖혀짐 → 흰색 번쩍임 → 회복
do
  local hitp = { x = BASE_X - 2, y = 57, torso = -14, head = -16, na = { sh = 0, el = 40 }, fa = { sh = -40, el = 30 }, eye = "closed" }
  local flash = {}; for k, v in pairs(hitp) do flash[k] = v end; flash.flash = true
  anim("hit", {
    { dur = 0.08, P = pose(hitp) },
    { dur = 0.06, P = pose(flash) },
    { dur = 0.12, P = pose({ x = BASE_X - 1, y = 56.5, torso = -6, head = -6, na = { sh = 14, el = 50 }, fa = { sh = -20, el = 35 } }) },
  })
end

-- 7 사망: 비틀 → 무릎 꺾임 → 무릎 꿇음 → 앞으로 쓰러짐 → 엎드림 → 정지
anim("death", {
  { dur = 0.12, P = pose({ x = BASE_X - 2, y = 58, torso = -12, head = -20, na = { sh = -5, el = 15 }, fa = { sh = -30, el = 20 },
                           eye = "closed", fx = { { "sparks", 3, 1 } } }) },
  { dur = 0.12, P = pose({ x = BASE_X, y = 64, torso = 10, head = 18, na = { sh = 5, el = 5 }, fa = { sh = 5, el = 10 },
                           eye = "off", fx = { { "sparks", 4, 2 } } }) },
  { dur = 0.15, P = pose({ x = BASE_X + 2, y = 66, torso = 20, head = 28, nl = { thigh = 82, knee = 150, foot = 70 }, fl = { thigh = 72, knee = 140, foot = 70 },
                           na = { sh = 10, el = 0 }, fa = { sh = 15, el = 0 }, eye = "off", fx = { { "sparks", 3, 3 } } }) },
  { dur = 0.12, P = pose({ x = BASE_X + 4, y = 66, torso = 58, head = 62, nl = { thigh = 60, knee = 110, foot = 60 }, fl = { thigh = 50, knee = 100, foot = 60 },
                           na = { sh = 40, el = 0 }, fa = { sh = 50, el = 0 }, eye = "off" }) },
  { dur = 0.20, P = pose({ x = BASE_X, y = 70, torso = 90, head = 92, nl = { thigh = -88, knee = 4, foot = 92 }, fl = { thigh = -92, knee = 8, foot = 92 },
                           na = { sh = -84, el = 0 }, fa = { sh = -95, el = 0 }, eye = "off", fx = { { "sparks", 2, 4 } } }) },
  { dur = 0.60, P = pose({ x = BASE_X, y = 70, torso = 90, head = 92, nl = { thigh = -88, knee = 4, foot = 92 }, fl = { thigh = -92, knee = 8, foot = 92 },
                           na = { sh = -84, el = 0 }, fa = { sh = -95, el = 0 }, eye = "off" }) },
})

-- ───────── 모든 프레임 그리기 ─────────
local RESULT = { W = W, H = H, palette = HEX, ground = GROUND - 1, anims = {} }
for _, a in ipairs(ANIMS) do
  local out = { name = a.name, frames = {} }
  for i, f in ipairs(a.frames) do
    local b = render(f.P)
    out.frames[i] = { buf = b, dur = f.dur }
  end
  RESULT.anims[#RESULT.anims + 1] = out
end

-- ───────── Aseprite 로 내보내기 ─────────
if app ~= nil and app.apiVersion ~= nil then
  local here = (debug.getinfo(1, "S").source:match("^@(.*[/\\])")) or "./"
  local spr = Sprite(W, H, ColorMode.INDEXED)
  local pal = Palette(16)
  pal:setColor(0, Color { r = 0, g = 0, b = 0, a = 0 })
  for i, hx in ipairs(HEX) do
    pal:setColor(i, Color { r = tonumber(hx:sub(1, 2), 16), g = tonumber(hx:sub(3, 4), 16), b = tonumber(hx:sub(5, 6), 16), a = 255 })
  end
  spr:setPalette(pal)
  spr.transparentColor = 0
  local layer = spr.layers[1]
  layer.name = "NX-07"
  local frameNo, maxF, images = 0, 0, {}
  for _, a in ipairs(RESULT.anims) do
    local from = frameNo + 1
    for _, f in ipairs(a.frames) do
      frameNo = frameNo + 1
      local fr = (frameNo == 1) and spr.frames[1] or spr:newEmptyFrame()
      fr.duration = f.dur
      local img = Image(W, H, ColorMode.INDEXED)
      for y = 0, H - 1 do for x = 0, W - 1 do
        local c = f.buf.c[y][x]
        if c ~= 0 then img:drawPixel(x, y, c) end
      end end
      local cel = layer:cel(fr)
      if cel then cel.image = img; cel.position = Point(0, 0) else spr:newCel(layer, fr, img, Point(0, 0)) end
      images[#images + 1] = img
    end
    local tag = spr:newTag(from, frameNo)
    tag.name = a.name
    maxF = max(maxF, #a.frames)
  end
  spr:saveAs(here .. "nx07_pixel.aseprite")
  -- 시트: 한 줄에 애니메이션 하나
  local sheet = Image(W * maxF, H * #RESULT.anims, ColorMode.INDEXED)
  local k = 0
  for r, a in ipairs(RESULT.anims) do
    for i = 1, #a.frames do
      k = k + 1
      sheet:drawImage(images[k], Point((i - 1) * W, (r - 1) * H))
    end
  end
  sheet:saveAs { filename = here .. "nx07_pixel_sheet.png", palette = pal }
  local js = { '{"cell":[' .. W .. ',' .. H .. '],"baseline":' .. (GROUND - 1) .. ',"anims":[' }
  for r, a in ipairs(RESULT.anims) do
    local durs = {}
    for i, f in ipairs(a.frames) do durs[i] = string.format("%.2f", f.dur) end
    js[#js + 1] = string.format('%s{"name":"%s","row":%d,"frames":%d,"durations":[%s]}', r > 1 and "," or "", a.name, r - 1, #a.frames, table.concat(durs, ","))
  end
  js[#js + 1] = "]}"
  local fh = io.open(here .. "nx07_pixel.json", "w")
  fh:write(table.concat(js)); fh:close()
end

-- Aseprite 밖(미리보기)에서 돌릴 때는 픽셀 데이터를 돌려준다
local PACK = { W = W, H = H, palette = HEX, ground = GROUND - 1, anims = {} }
for _, a in ipairs(RESULT.anims) do
  local fr = {}
  for i, f in ipairs(a.frames) do
    local row = {}
    for y = 0, H - 1 do for x = 0, W - 1 do row[#row + 1] = string.char(f.buf.c[y][x]) end end
    fr[i] = { px = table.concat(row), dur = f.dur }
  end
  PACK.anims[#PACK.anims + 1] = { name = a.name, frames = fr }
end
return PACK
