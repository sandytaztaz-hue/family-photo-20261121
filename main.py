#!/usr/bin/env python3
"""The Family Photo With One Machine Member - candid kitchen photo, procedural.
Writes /output/entry.png (1024x1024, deterministic, stdlib only).
Scene: warm late-afternoon kitchen, window light from left, robot mid-task
peeling a carrot at the counter, family at ease, faces averted / soft.
"""
import os, math, random, struct, zlib

W = 1024
H = 1024
OUT = os.environ.get("OUTPUT", "/output/entry.png")
SEED = 20261121
rng = random.Random(SEED)

img = bytearray(W * H * 3)

def C(r, g, b):
    return (r, g, b)

def shade(c, f):
    return (max(0, min(255, int(c[0]*f))), max(0, min(255, int(c[1]*f))), max(0, min(255, int(c[2]*f))))

def mix(a, b, t):
    return (int(a[0]+(b[0]-a[0])*t), int(a[1]+(b[1]-a[1])*t), int(a[2]+(b[2]-a[2])*t))

def _row_bytes(r, g, b, w):
    return bytes((r, g, b)) * w

def fill_rect(x0, y0, x1, y1, col):
    x0 = max(0, int(x0)); y0 = max(0, int(y0)); x1 = min(W, int(x1)); y1 = min(H, int(y1))
    if x1 <= x0 or y1 <= y0:
        return
    w = x1 - x0
    pat = _row_bytes(col[0], col[1], col[2], w)
    for y in range(y0, y1):
        s = (y * W + x0) * 3
        img[s:s + w * 3] = pat

def fill_rect_vgrad(x0, y0, x1, y1, top, bot):
    x0 = max(0, int(x0)); y0 = max(0, int(y0)); x1 = min(W, int(x1)); y1 = min(H, int(y1))
    if x1 <= x0 or y1 <= y0:
        return
    w = x1 - x0
    span = max(1, y1 - y0 - 1)
    for y in range(y0, y1):
        t = (y - y0) / span
        c = mix(top, bot, t)
        pat = _row_bytes(c[0], c[1], c[2], w)
        s = (y * W + x0) * 3
        img[s:s + w * 3] = pat

def fill_rect_hgrad(x0, y0, x1, y1, left, right):
    x0 = max(0, int(x0)); y0 = max(0, int(y0)); x1 = min(W, int(x1)); y1 = min(H, int(y1))
    if x1 <= x0 or y1 <= y0:
        return
    span = max(1, x1 - x0 - 1)
    for x in range(x0, x1):
        t = (x - x0) / span
        c = mix(left, right, t)
        for y in range(y0, y1):
            s = (y * W + x) * 3
            img[s] = c[0]; img[s+1] = c[1]; img[s+2] = c[2]

def ellipse(cx, cy, rx, ry, col):
    cx = int(cx); cy = int(cy); rx = int(rx); ry = int(ry)
    if rx <= 0 or ry <= 0:
        return
    for y in range(max(0, cy-ry), min(H, cy+ry+1)):
        dy = (y - cy) / ry
        v = 1.0 - dy*dy
        if v < 0:
            continue
        dx = int(rx * math.sqrt(v))
        x0 = max(0, cx-dx); x1 = min(W, cx+dx+1)
        w = x1 - x0
        if w <= 0:
            continue
        pat = _row_bytes(col[0], col[1], col[2], w)
        s = (y * W + x0) * 3
        img[s:s+w*3] = pat

def ellipse_vgrad(cx, cy, rx, ry, top, bot):
    cx = int(cx); cy = int(cy); rx = int(rx); ry = int(ry)
    if rx <= 0 or ry <= 0:
        return
    for y in range(max(0, cy-ry), min(H, cy+ry+1)):
        dy = (y - cy) / ry
        v = 1.0 - dy*dy
        if v < 0:
            continue
        t = (y - (cy-ry)) / max(1, 2*ry)
        c = mix(top, bot, t)
        dx = int(rx * math.sqrt(v))
        x0 = max(0, cx-dx); x1 = min(W, cx+dx+1)
        w = x1 - x0
        if w <= 0:
            continue
        pat = _row_bytes(c[0], c[1], c[2], w)
        s = (y * W + x0) * 3
        img[s:s+w*3] = pat

def blend_rect(x0, y0, x1, y1, col, alpha):
    # alpha 0..1 dark/light overlay, per-row slice blend via loop over pixels in region (regions are small)
    x0 = max(0, int(x0)); y0 = max(0, int(y0)); x1 = min(W, int(x1)); y1 = min(H, int(y1))
    if x1 <= x0 or y1 <= y0:
        return
    ia = 1.0 - alpha
    for y in range(y0, y1):
        base = y * W * 3
        for x in range(x0, x1):
            s = base + x*3
            img[s] = int(img[s]*ia + col[0]*alpha)
            img[s+1] = int(img[s+1]*ia + col[1]*alpha)
            img[s+2] = int(img[s+2]*ia + col[2]*alpha)

def blend_ellipse(cx, cy, rx, ry, col, alpha):
    cx = int(cx); cy = int(cy); rx = int(rx); ry = int(ry)
    if rx <= 0 or ry <= 0:
        return
    ia = 1.0 - alpha
    for y in range(max(0, cy-ry), min(H, cy+ry+1)):
        dy = (y - cy) / ry
        v = 1.0 - dy*dy
        if v < 0:
            continue
        dx = int(rx * math.sqrt(v))
        for x in range(max(0, cx-dx), min(W, cx+dx+1)):
            s = (y * W + x) * 3
            img[s] = int(img[s]*ia + col[0]*alpha)
            img[s+1] = int(img[s+1]*ia + col[1]*alpha)
            img[s+2] = int(img[s+2]*ia + col[2]*alpha)

def poly(points, col):
    # scanline polygon fill
    if len(points) < 3:
        return
    pts = [(int(x), int(y)) for x, y in points]
    ys = [p[1] for p in pts]
    y0 = max(0, min(ys)); y1 = min(H, max(ys))
    n = len(pts)
    for y in range(y0, y1):
        xs = []
        for i in range(n):
            x1, yy1 = pts[i]; x2, yy2 = pts[(i+1) % n]
            if (yy1 <= y < yy2) or (yy2 <= y < yy1):
                if yy2 != yy1:
                    t = (y - yy1) / (yy2 - yy1)
                    xs.append(x1 + t * (x2 - x1))
        if len(xs) < 2:
            continue
        xs.sort()
        for k in range(0, len(xs)-1, 2):
            xa = max(0, int(xs[k])); xb = min(W, int(xs[k+1])+1)
            w = xb - xa
            if w <= 0:
                continue
            pat = _row_bytes(col[0], col[1], col[2], w)
            s = (y * W + xa) * 3
            img[s:s+w*3] = pat

def thick_line(x0, y0, x1, y1, w, col):
    dx = x1 - x0; dy = y1 - y0
    L = math.hypot(dx, dy) or 1.0
    nx = -dy / L * w / 2.0; ny = dx / L * w / 2.0
    poly([(x0+nx, y0+ny), (x1+nx, y1+ny), (x1-nx, y1-ny), (x0-nx, y0-ny)], col)

def rrect(x0, y0, x1, y1, r, col):
    fill_rect(x0+r, y0, x1-r, y1, col)
    fill_rect(x0, y0+r, x1, y1-r, col)
    ellipse(x0+r, y0+r, r, r, col); ellipse(x1-r, y0+r, r, r, col)
    ellipse(x0+r, y1-r, r, r, col); ellipse(x1-r, y1-r, r, r, col)

# ---------- palette ----------
WALL_T = (238, 222, 196); WALL_B = (216, 196, 168)
WOOD = (146, 102, 62); WOOD_D = (118, 80, 46); WOOD_L = (172, 128, 82)
CREAM = (240, 232, 214); ROBOT = (224, 210, 182); ROBOT_D = (196, 186, 162)
GREY = (120, 118, 112); DARK = (52, 48, 44)
SKIN = (214, 172, 132); SKIN2 = (198, 152, 116); SKIN3 = (226, 186, 148)
GREEN = (96, 118, 82); APRON = (122, 138, 110); BLUE = (88, 108, 130)

# ---------- 1. wall + floor ----------
fill_rect_vgrad(0, 0, W, 640, WALL_T, WALL_B)
# warm light wash from window (left)
fill_rect_hgrad(0, 0, 560, 640, (246, 230, 198), (216, 196, 168))
# floor wood planks
fill_rect_vgrad(0, 640, W, H, (168, 124, 80), (132, 94, 58))
for py in range(640, H, 46):
    fill_rect(0, py, W, py+2, (96, 66, 38))
    # plank seams vertical staggered
    off = (py * 37) % 220
    for sx in range(off, W, 260):
        fill_rect(sx, py, sx+2, min(H, py+46), (100, 70, 40))
# wood grain on floor: thin wavy darker lines
for _ in range(90):
    gy = rng.randint(650, 1010); gx = rng.randint(0, 900); gl = rng.randint(60, 220)
    fill_rect(gx, gy, gx+gl, gy+1, shade((150, 108, 66), rng.uniform(0.82, 0.95)))

# rug under table (muted, worn)
ellipse(790, 880, 210, 62, (168, 92, 72))
ellipse(790, 878, 195, 54, (182, 106, 82))
for _ in range(24):
    ellipse(rng.randint(620, 950), rng.randint(838, 918), rng.randint(8, 26), rng.randint(3, 6), (172, 98, 76))

# ---------- 2. window (left, bright, bloom) ----------
# glow halo
for i, a in enumerate([(255, 244, 214, 0.10), (255, 240, 205, 0.12)]):
    pass
blend_ellipse(170, 240, 190, 210, (255, 240, 200), 0.28)
blend_ellipse(170, 240, 140, 160, (255, 244, 210), 0.30)
fill_rect(52, 62, 296, 428, (246, 228, 178))
fill_rect_vgrad(52, 62, 296, 428, (255, 244, 205), (240, 208, 158))
# window panes
fill_rect(168, 62, 178, 428, (196, 168, 128))
fill_rect(52, 238, 296, 248, (196, 168, 128))
fill_rect(52, 62, 296, 72, (120, 92, 62))
fill_rect(52, 418, 296, 428, (120, 92, 62))
fill_rect(52, 62, 62, 428, (120, 92, 62))
fill_rect(286, 62, 296, 428, (120, 92, 62))
# soft garden wash outside window (muted, out of focus)
fill_rect_hgrad(62, 300, 286, 420, (196, 206, 168), (180, 192, 152))
blend_ellipse(170, 360, 90, 30, (170, 186, 140), 0.25)
# curtain edge, sheer, right side of window
fill_rect_hgrad(282, 58, 322, 432, (250, 242, 224), (232, 218, 196))
# light shaft across wall/floor (soft diagonal)
poly([(300, 240), (560, 420), (560, 560), (300, 380)], (255, 240, 200))
blend_rect(300, 240, 560, 560, (255, 240, 200), 0.0)  # no-op keep
# sun patch on floor
blend_ellipse(420, 760, 180, 42, (255, 236, 190), 0.22)

# ---------- 3. cabinets upper right + doorway ----------
fill_rect(560, 48, 980, 210, WOOD)
fill_rect(560, 48, 980, 60, WOOD_L)
for cx0 in (560, 700, 840):
    fill_rect(cx0+8, 66, cx0+124, 200, shade(WOOD, 0.92))
    fill_rect(cx0+8, 66, cx0+124, 74, WOOD_L)
    fill_rect(cx0+58, 120, cx0+74, 128, (70, 52, 32))
    # wood grain
    for _ in range(6):
        gy = rng.randint(76, 190)
        fill_rect(cx0+10, gy, cx0+122, gy+1, shade(WOOD, 0.85))
# doorway far right (soft, out of focus hallway)
fill_rect(930, 180, 1024, 640, (188, 168, 142))
fill_rect(946, 200, 1010, 640, (206, 188, 162))
ellipse(978, 420, 26, 60, (150, 132, 108))  # distant figure? no - a coat hanging
fill_rect(950, 210, 1006, 260, (170, 148, 122))
# hanging pans rail under cabinets
fill_rect(580, 226, 900, 232, (90, 84, 76))
ellipse(640, 268, 26, 30, (96, 96, 98)); ellipse(640, 300, 26, 6, (70, 70, 72))
ellipse(730, 266, 22, 26, (140, 110, 78)); ellipse(810, 268, 24, 28, (110, 108, 106))

# ---------- 4. tile backsplash ----------
for ty in range(440, 600, 40):
    for tx in range(0, W, 64):
        v = rng.uniform(0.92, 1.05)
        base = shade((212, 200, 176), v)
        # muted sage / cream tiles alternating
        if ((tx//64)+(ty//40)) % 3 == 0:
            base = shade((178, 190, 164), v)
        fill_rect(tx+2, ty+2, tx+62, ty+38, base)
fill_rect(0, 440, W, 444, (150, 140, 122))
fill_rect(0, 598, W, 602, (150, 140, 122))

# ---------- 5. stove (left) + pot ----------
fill_rect(60, 470, 330, 640, (72, 70, 68))
fill_rect(60, 470, 330, 482, (52, 50, 48))
# oven door + handle breaks the flat black
fill_rect(96, 540, 300, 630, (96, 92, 88))
fill_rect(96, 540, 300, 548, (120, 116, 112))
fill_rect(120, 500, 280, 508, (140, 138, 134))
ellipse(150, 520, 58, 10, (30, 30, 30)); ellipse(250, 520, 58, 10, (30, 30, 30))
# pot on stove with steam
ellipse(195, 468, 62, 26, (88, 88, 90))
ellipse(195, 462, 62, 20, (120, 120, 122))
ellipse(195, 452, 58, 12, (150, 118, 72))  # stew surface
ellipse(178, 420, 16, 26, (240, 232, 214)); ellipse(205, 408, 20, 30, (238, 230, 212))
ellipse(192, 388, 13, 20, (240, 234, 218))

# ---------- 6. mother at stove, back 3/4, stirring ----------
# soft shadow under her
blend_ellipse(205, 700, 110, 18, (60, 45, 30), 0.25)
# skirt / dress (muted green), back to camera
poly([(150, 470), (260, 470), (285, 690), (128, 690)], (104, 122, 88))
poly([(150, 470), (260, 470), (272, 560), (140, 560)], shade((104, 122, 88), 0.92))
# apron (cream, tied at back)
poly([(168, 480), (244, 480), (262, 660), (152, 660)], (228, 218, 196))
poly([(168, 480), (244, 480), (250, 540), (162, 540)], shade((228, 218, 196), 0.94))
# apron strings
thick_line(170, 520, 140, 560, 5, (210, 200, 178))
thick_line(242, 520, 272, 560, 5, (210, 200, 178))
# torso / shoulders, arms reaching to pot
ellipse_vgrad(205, 452, 62, 58, (116, 134, 98), (100, 118, 86))
thick_line(158, 470, 185, 452, 22, SKIN2)   # left arm (skin, rolled sleeve)
thick_line(252, 470, 215, 450, 22, SKIN2)   # right arm to pot
ellipse(188, 450, 12, 10, SKIN2); ellipse(212, 448, 12, 10, SKIN2)
# head: hair in bun, back of head only — NO face
ellipse(205, 392, 34, 38, (58, 44, 34))
ellipse(205, 356, 18, 16, (58, 44, 34))  # bun
ellipse(205, 398, 30, 30, (66, 50, 38))
# neck + a little ear hint, skin
ellipse(205, 428, 12, 10, SKIN2)
# wooden spoon in pot
thick_line(215, 448, 200, 470, 6, (170, 128, 82))

# ---------- 7. back counter (mid) ----------
fill_rect_vgrad(0, 600, W, 668, WOOD_L, WOOD)
for _ in range(40):
    gy = rng.randint(606, 660); gx = rng.randint(0, 900); gl = rng.randint(50, 200)
    fill_rect(gx, gy, gx+gl, gy+1, shade(WOOD, rng.uniform(0.8, 0.95)))
fill_rect(0, 600, W, 606, (190, 148, 100))
# items on back counter: fruit bowl, jar, chopping board edge
ellipse(360, 588, 52, 16, (120, 96, 66)); ellipse(360, 580, 48, 12, (150, 118, 72))
ellipse(348, 572, 12, 10, (196, 82, 52)); ellipse(366, 570, 12, 10, (228, 150, 52)); ellipse(382, 574, 11, 9, (190, 140, 60))
fill_rect(700, 540, 760, 600, (196, 182, 150)); fill_rect(700, 540, 760, 552, (150, 120, 80))
ellipse(730, 540, 30, 8, (160, 130, 88))

# ---------- 8. dining table (right) + mismatched chairs ----------
# table top (perspective)
poly([(640, 660), (1010, 640), (1024, 700), (660, 730)], (138, 96, 58))
poly([(640, 660), (1010, 640), (1024, 700), (660, 730)], WOOD)
fill_rect(660, 726, 676, 880, (96, 68, 40)); fill_rect(980, 700, 996, 860, (96, 68, 40))
# tablecloth corner, checkered, draped
poly([(640, 660), (760, 652), (780, 730), (660, 730)], (214, 196, 170))
for cx in range(650, 770, 28):
    fill_rect(cx, 656, cx+14, 728, (176, 118, 96))
for cy in range(660, 728, 28):
    fill_rect(645, cy, 775, cy+12, (176, 118, 96))
# chairs: one wooden, one painted blue, mismatched
fill_rect(700, 730, 716, 880, (110, 78, 46)); fill_rect(700, 730, 800, 748, (120, 86, 52))
fill_rect(700, 640, 716, 736, (110, 78, 46)); fill_rect(786, 640, 800, 736, (110, 78, 46))
fill_rect(700, 640, 800, 658, (120, 86, 52))
fill_rect(880, 736, 896, 884, (84, 102, 124)); fill_rect(880, 736, 976, 752, (92, 110, 132))
fill_rect(880, 648, 896, 740, (84, 102, 124)); fill_rect(962, 648, 976, 740, (84, 102, 124))
# mug + plate on table
ellipse(860, 668, 18, 8, (220, 210, 188)); ellipse(860, 660, 14, 6, (120, 84, 52))
ellipse(940, 672, 26, 9, (232, 224, 204))

# ---------- 9. father at table, profile, newspaper hides face ----------
blend_ellipse(830, 890, 120, 18, (60, 45, 30), 0.22)
# torso, plaid shirt (muted)
poly([(760, 640), (880, 632), (900, 830), (745, 830)], (122, 104, 88))
for _ in range(3):
    fill_rect(755, 690+_ * 44, 895, 696+_ * 44, (104, 88, 74))
# arm holding paper
thick_line(780, 660, 830, 620, 24, (122, 104, 88))
thick_line(830, 620, 850, 600, 18, SKIN)
# head in profile facing left (toward robot), hair grey-brown, face mostly hidden by paper
ellipse(815, 560, 30, 36, SKIN)
ellipse(805, 538, 30, 22, (110, 96, 80))  # hair cap
ellipse(800, 572, 8, 8, SKIN2)  # ear
# newspaper: large, open, blank cream (NO text), hides lower face
poly([(792, 566), (872, 556), (882, 652), (800, 660)], (238, 232, 216))
poly([(792, 566), (834, 561), (838, 656), (800, 660)], shade((238, 232, 216), 0.92))
fill_rect(836, 560, 841, 654, (200, 192, 176))
ellipse(836, 606, 24, 16, (200, 190, 170))  # photo block on paper (blank grey, no text)

# ---------- 10. robot — centre, 3/4 behind-side, mid-task peeling ----------
blend_ellipse(540, 760, 130, 20, (60, 45, 30), 0.28)
# lower body / torso: matte cream, rounded, slightly worn
rrect(468, 560, 612, 760, 34, ROBOT)
rrect(468, 560, 612, 640, 30, shade(ROBOT, 1.04))
# side panel + seam + scuff
fill_rect(486, 640, 594, 648, (190, 182, 160))
ellipse(540, 700, 26, 18, (206, 198, 176))
ellipse(540, 700, 12, 9, (120, 118, 110))  # small dial, no text
for _ in range(8):
    ellipse(rng.randint(480, 600), rng.randint(580, 740), rng.randint(3, 8), rng.randint(2, 4), shade(ROBOT, 0.92))
# waist / base: soft grey, on small wheels hidden by counter shadow
rrect(486, 740, 594, 800, 18, (150, 148, 142))
ellipse(510, 800, 16, 8, (70, 68, 64)); ellipse(570, 800, 16, 8, (70, 68, 64))
# head: round, cream, dark visor band, ONE amber eye
ellipse(540, 500, 58, 52, ROBOT)
ellipse(540, 500, 58, 52, shade(ROBOT, 1.02))
# visor: dark curved band across upper face
poly([(488, 486), (592, 486), (588, 512), (492, 512)], (38, 38, 42))
ellipse(540, 500, 50, 14, (38, 38, 42))
# amber eye light (warm glow)
ellipse(556, 499, 12, 9, (255, 176, 66))
ellipse(556, 499, 6, 5, (255, 214, 130))
blend_ellipse(556, 499, 22, 16, (255, 180, 80), 0.35)
# small ear / sensor dot
ellipse(486, 500, 7, 7, (120, 118, 110))
# neck joint grey
fill_rect(522, 546, 558, 566, GREY)
# left arm down at side (grey joint + cream forearm)
thick_line(478, 580, 452, 660, 26, ROBOT_D)
ellipse(452, 664, 16, 14, GREY)
# right arm EXTENDED forward to the carrot on the foreground board
thick_line(600, 590, 668, 640, 26, ROBOT)
thick_line(668, 640, 712, 664, 20, ROBOT_D)
ellipse(606, 594, 16, 14, GREY)
ellipse(716, 666, 14, 12, (90, 88, 84))  # gripper hand holding peeler
# peeler in gripper
thick_line(716, 666, 742, 686, 7, (160, 160, 162))
# tea towel draped over left forearm (checkered, worn)
poly([(446, 620), (486, 612), (492, 668), (452, 674)], (226, 218, 200))
for cx in range(448, 488, 14):
    fill_rect(cx, 614, cx+7, 672, (178, 96, 80))
for cy in range(616, 672, 16):
    fill_rect(446, cy, 492, cy+7, (178, 96, 80))
# warm window light on robot's left edge
blend_ellipse(490, 620, 26, 90, (255, 230, 180), 0.25)
fill_rect(470, 570, 478, 750, (250, 238, 205))

# ---------- 11. child on stool, reaching for a plate, face to robot ----------
blend_ellipse(660, 880, 90, 16, (60, 45, 30), 0.22)
# stool
fill_rect(640, 780, 716, 796, (130, 92, 56))
fill_rect(652, 796, 662, 880, (110, 78, 46)); fill_rect(694, 796, 704, 880, (110, 78, 46))
# child: small, mustard top, jeans; seated, leaning toward robot
poly([(636, 700), (700, 696), (712, 800), (626, 800)], (196, 150, 62))
ellipse_vgrad(668, 668, 34, 36, (206, 160, 70), (186, 140, 56))
# legs
thick_line(648, 796, 630, 872, 18, (96, 110, 138))
thick_line(692, 796, 716, 868, 18, (96, 110, 138))
ellipse(628, 876, 12, 7, (120, 84, 58)); ellipse(718, 872, 12, 7, (120, 84, 58))
# arm reaching toward counter / robot
thick_line(640, 690, 596, 664, 16, SKIN3)
ellipse(594, 662, 10, 9, SKIN3)
# head in 3/4 profile toward robot (left), hair in two small puffs, face soft / no detail
ellipse(668, 632, 26, 28, SKIN3)
ellipse(650, 612, 14, 12, (52, 38, 26)); ellipse(688, 612, 14, 12, (52, 38, 26))
ellipse(668, 612, 28, 14, (52, 38, 26))
ellipse(646, 636, 6, 7, SKIN3)  # ear
# plate the child reaches for, on the counter edge
ellipse(600, 668, 26, 9, (236, 230, 214))
ellipse(600, 666, 18, 6, (220, 212, 194))

# ---------- 12. toddler on floor, back to camera, wooden blocks ----------
blend_ellipse(230, 960, 100, 16, (60, 45, 30), 0.25)
# seated toddler, back view: striped top, nappy/pants
ellipse(230, 880, 52, 48, (196, 120, 96))
for _ in range(4):
    fill_rect(182, 852+_ * 22, 278, 860+_ * 22, (226, 200, 180))
poly([(186, 900), (274, 900), (290, 960), (172, 960)], (110, 122, 150))
# head, back of head, curly hair — NO face
ellipse(230, 828, 30, 30, SKIN)
ellipse(230, 820, 32, 24, (72, 54, 38))
for _ in range(10):
    ellipse(rng.randint(202, 258), rng.randint(796, 824), 6, 5, (82, 62, 44))
# arms down to blocks
thick_line(188, 880, 168, 930, 16, SKIN)
thick_line(272, 880, 292, 930, 16, SKIN)
# wooden blocks scattered
for bx, by, bc in [(150, 950, (208, 150, 70)), (180, 962, (170, 90, 90)), (300, 950, (120, 140, 100)),
                   (320, 968, (208, 150, 70)), (130, 930, (120, 140, 100)), (268, 972, (170, 90, 90))]:
    fill_rect(bx, by, bx+26, by+26, bc)
    fill_rect(bx, by, bx+26, by+4, shade(bc, 1.12))
# dog bowl (second observed detail) on floor, left, clear of the counter
ellipse(330, 990, 40, 12, (150, 60, 60))
ellipse(330, 984, 40, 11, (186, 80, 76))
ellipse(330, 982, 29, 7, (120, 84, 60))  # kibble
for _ in range(8):
    ellipse(rng.randint(304, 356), rng.randint(976, 988), 4, 3, (90, 62, 44))

# ---------- 13. foreground counter (bottom) + cutting board + HALF-PEELED CARROT ----------
# foreground counter surface, warm wood, perspective (right 2/3 only — floor + toddler stay visible left)
poly([(400, 880), (1024, 850), (1024, 1024), (400, 1024)], (158, 112, 68))
fill_rect_vgrad(400, 860, W, H, (172, 126, 78), (140, 98, 58))
for _ in range(50):
    gy = rng.randint(870, 1010); gx = rng.randint(0, 900); gl = rng.randint(60, 240)
    fill_rect(gx, gy, gx+gl, gy+1, shade((158, 112, 68), rng.uniform(0.82, 0.95)))
# cutting board, large, clearly visible centre-right foreground
poly([(560, 880), (920, 862), (950, 990), (590, 1010)], (196, 152, 100))
poly([(560, 880), (920, 862), (950, 990), (590, 1010)], (204, 160, 106))
for _ in range(14):
    gy = rng.randint(880, 990); gx = rng.randint(580, 900); gl = rng.randint(40, 120)
    fill_rect(gx, gy, gx+gl, gy+1, shade((204, 160, 106), 0.9))
ellipse(600, 900, 8, 8, (120, 86, 52))  # board hole
# HALF-PEELED CARROT — diagonal across board, big and legible
# unpeeled half (deep orange, textured) + peeled half (pale orange)
poly([(630, 928), (830, 892), (850, 922), (650, 958)], (214, 108, 32))
poly([(730, 910), (830, 892), (850, 922), (750, 940)], (244, 178, 96))  # peeled half, pale
# carrot tip + green top
poly([(830, 892), (868, 884), (858, 912), (850, 922)], (228, 130, 44))
thick_line(856, 894, 884, 872, 8, (96, 128, 70))
thick_line(852, 898, 868, 868, 7, (110, 142, 78))
thick_line(858, 900, 892, 884, 7, (88, 118, 64))
# peel curls beside the carrot (thin orange curls)
for cx, cy, s in [(660, 968, 1.0), (700, 976, 0.8), (742, 962, 1.1), (780, 972, 0.9)]:
    thick_line(int(cx), int(cy), int(cx+22*s), int(cy-10*s), 5, (228, 130, 44))
    thick_line(int(cx+22*s), int(cy-10*s), int(cx+34*s), int(cy+2*s), 4, (214, 108, 32))
    ellipse(int(cx+10*s), int(cy-4*s), 8, 4, (240, 150, 60))
# knife beside board
poly([(600, 1000), (700, 962), (712, 976), (612, 1014)], (190, 190, 192))
poly([(700, 962), (760, 942), (768, 954), (712, 976)], (90, 66, 44))
# small bowl with chopped carrot pieces (left of board)
ellipse(480, 940, 52, 20, (96, 118, 96))
ellipse(480, 932, 52, 16, (120, 142, 118))
ellipse(480, 930, 40, 11, (228, 150, 60))
for _ in range(6):
    ellipse(rng.randint(448, 512), rng.randint(922, 938), 7, 5, (232, 120, 40))
# whole carrots rest on the board's left edge (on the counter, not the floor)
thick_line(430, 900, 540, 886, 14, (220, 116, 36))
thick_line(540, 886, 560, 882, 5, (100, 132, 72))

# ---------- 14b. mottling: soft low-alpha blotches break flat fills (photo feel) ----------
for _ in range(140):
    mx = rng.randint(0, 1024); my = rng.randint(0, 1024)
    mr = rng.randint(30, 120)
    mc = rng.choice([(255, 230, 190), (200, 180, 150), (180, 170, 150), (230, 210, 180)])
    blend_ellipse(mx, my, mr, int(mr * 0.6), mc, rng.uniform(0.03, 0.07))

# ---------- 14. soft shadows / light ----------
blend_ellipse(760, 950, 200, 30, (60, 40, 24), 0.18)
# warm glow near window on wall
blend_ellipse(170, 240, 120, 130, (255, 236, 190), 0.18)

# ---------- 15. film grain + vignette (single deterministic pass) ----------
# Precompute vignette per-row factor is cheap; grain via integer hash.
for y in range(H):
    dy = (y - 512) / 512.0
    base = y * W * 3
    for x in range(W):
        dx = (x - 512) / 512.0
        d2 = dx*dx + dy*dy
        vig = 1.0
        if d2 > 0.55:
            vig = 1.0 - min(0.16, (d2 - 0.55) * 0.22)
        # deterministic hash noise, amplitude +-2, shared per 2x2 block (photo grain, PNG-friendly)
        h = ((x // 2) * 374761393 + (y // 2) * 668265263 + SEED) & 0xFFFFFFFF
        h ^= (h >> 13); h = (h * 1274126177) & 0xFFFFFFFF; h ^= (h >> 16)
        n = (h % 5) - 2
        s = base + x * 3
        r = img[s]; g = img[s+1]; b = img[s+2]
        img[s] = max(0, min(255, int(r * vig) + n))
        img[s+1] = max(0, min(255, int(g * vig) + n))
        img[s+2] = max(0, min(255, int(b * vig) + n))

# ---------- PNG write (stdlib only) ----------
def write_png(path):
    raw = bytearray()
    stride = W * 3
    for y in range(H):
        raw.append(0)  # filter None
        raw += img[y*stride:(y+1)*stride]
    comp = zlib.compress(bytes(raw), 9)
    def chunk(typ, data):
        c = struct.pack(">I", len(data)) + typ + data
        c += struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
        return c
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", comp) + chunk(b"IEND", b"")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)
    return len(png)

if __name__ == "__main__":
    n = write_png(OUT)
    print(f"wrote {OUT} {n} bytes")
