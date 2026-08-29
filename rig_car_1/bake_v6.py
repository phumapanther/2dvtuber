# -*- coding: utf-8 -*-
"""Bake v6 layers (rev 2 — single-source): all face/hair pixels come from หัว.png,
the die-cut หน้า.png / ผม.png act only as region masks, so layers line up perfectly
at rest (no cross-generation ghosting).  Zoomed eye parts are template-fitted onto หัว.
Run:  python bake_v6.py
"""
import os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import numpy as np
from PIL import Image, ImageFilter, ImageDraw

RIG = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.dirname(RIG)
W, H = 1024, 1536

MOUTH_SCALE = 0.91          # mouth sprites came from the older, wider-mouthed face
MOUTH_LINE_IN_SPRITE = (72, 15.5)   # closed-line center inside the 190x110 crop
MOUTH_ELL = (85, 38, 70, 36)        # opening ellipse (sprite coords) masks off old jaw art

def load(name, base=SRC):
    return Image.open(os.path.join(base, name)).convert("RGBA")

def arr(im): return np.asarray(im, dtype=np.float32)
def gray(a): return a[:, :, :3].mean(axis=2) * (a[:, :, 3] / 255.0)

def edges(g):
    gx = np.zeros_like(g); gy = np.zeros_like(g)
    gx[:, 1:-1] = g[:, 2:] - g[:, :-2]
    gy[1:-1, :] = g[2:, :] - g[:-2, :]
    e = np.hypot(gx, gy)
    return e - e.mean()

def xcorr_peak(img_e, tpl_e):
    ih, iw = img_e.shape; th, tw = tpl_e.shape
    fh, fw = ih + th, iw + tw
    F = np.fft.rfft2(img_e, (fh, fw))
    T = np.fft.rfft2(tpl_e[::-1, ::-1], (fh, fw))
    c = np.fft.irfft2(F * T, (fh, fw))
    c = c[th - 1: th - 1 + ih - th + 1, tw - 1: tw - 1 + iw - tw + 1]
    iy, ix = np.unravel_index(np.argmax(c), c.shape)
    return float(c[iy, ix]), int(iy), int(ix)

def fit_template(target_im, tpl_im, scales, crop=None):
    tim = target_im.crop(crop) if crop else target_im
    img_e = edges(gray(arr(tim)))
    tb = tpl_im.getbbox()
    tpl_c = tpl_im.crop(tb)
    best = None
    for s in scales:
        tw = max(8, int(tpl_c.width * s)); th = max(8, int(tpl_c.height * s))
        te = edges(gray(arr(tpl_c.resize((tw, th), Image.LANCZOS))))
        if te.shape[0] >= img_e.shape[0] or te.shape[1] >= img_e.shape[1]:
            continue
        score, ty, tx = xcorr_peak(img_e, te)
        score /= np.sqrt((te * te).sum())
        if best is None or score > best[0]:
            best = (score, s, tx, ty)
    score, s, tx, ty = best
    ox = (crop[0] if crop else 0) + tx - tb[0] * s
    oy = (crop[1] if crop else 0) + ty - tb[1] * s
    return s, ox, oy, score

def place(tpl_im, s, ox, oy):
    scaled = tpl_im.resize((max(1, int(tpl_im.width * s)), max(1, int(tpl_im.height * s))), Image.LANCZOS)
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    out.alpha_composite(scaled, (int(round(ox)), int(round(oy))))
    return out

def grow(mask_im, px):
    return mask_im.filter(ImageFilter.MaxFilter(px * 2 + 1)) if px > 0 else mask_im
def shrink(mask_im, px):
    return mask_im.filter(ImageFilter.MinFilter(px * 2 + 1)) if px > 0 else mask_im

def inpaint(a, hole):
    a = a.copy()
    valid = (a[:, :, 3] > 128) & ~hole
    rgb = a[:, :, :3].copy()
    todo = hole.copy()
    for _ in range(400):
        if not todo.any():
            break
        progressed = False
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            nb = np.roll(valid, (dy, dx), (0, 1))
            src = np.roll(rgb, (dy, dx), (0, 1))
            take = todo & nb
            if take.any():
                rgb[take] = src[take]
                valid |= take
                todo &= ~take
                progressed = True
        if not progressed:
            break
    a[:, :, :3] = rgb
    a[:, :, 3] = np.where(hole, 255, a[:, :, 3])
    return a

def clean_edges(im, median=True):
    """ตัดขอบดำ/หมอกจากไดคัท: ตัด haze จาง, ลบหนามขอบ, เกลี่ยรอยหยัก, ระบายสีขอบจากเนื้อใน"""
    a = np.asarray(im, np.uint8).copy()
    al = a[:, :, 3].copy()
    al[al < 50] = 0                                   # หมอกจางนอกเส้นขอบ
    aI = Image.fromarray(al)
    if median:
        aI = aI.filter(ImageFilter.MedianFilter(3))   # ตุ่ม/หนาม 1px ตามขอบ
    aI = aI.filter(ImageFilter.GaussianBlur(0.8))     # เกลี่ยรอยหยัก
    # defringe: ยืดสีจากโซนทึบออกไปคลุมขอบโปร่งแสง (กันสีดำ/เทาปนขอบ)
    opaque = a[:, :, 3] > 200
    rim = (~opaque) & (np.asarray(grow(Image.fromarray((opaque * 255).astype(np.uint8)), 4)) > 128)
    rgb = a[:, :, :3]
    filled = opaque.copy()
    todo = rim.copy()
    for _ in range(6):
        if not todo.any():
            break
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            nb = np.roll(filled, (dy, dx), (0, 1))
            src = np.roll(rgb, (dy, dx), (0, 1))
            take = todo & nb
            if take.any():
                rgb[take] = src[take]
                filled |= take
                todo &= ~take
    a[:, :, :3] = rgb
    a[:, :, 3] = np.asarray(aI)
    return Image.fromarray(a)

def sharpen(im, percent=70):
    """Mild unsharp on RGB only (never alpha — keeps edges halo-free)."""
    r, g, b, a = im.split()
    rgb = Image.merge("RGB", (r, g, b)).filter(
        ImageFilter.UnsharpMask(radius=1.6, percent=percent, threshold=2))
    out = rgb.convert("RGBA"); out.putalpha(a)
    return out

def save(im, name, sharp=True):
    (sharpen(im) if sharp else im).save(os.path.join(RIG, name))
    print("saved", name)

# ---------- load ----------
hua = load("หัว.png"); naa = load("หน้า.png"); phom = load("ผม.png")
kho = load("คอ.png"); suea = load("เสื้อ.png"); huu = load("หู.png")
eye_white = load("ตา-ตาขาว.png"); eye_pupil = load("ตา-ตาดำ.png")
eye_open = load("ตา-ลืมตา.png"); eye_closed = load("ตา-หลับตา.png")
masterC = load("หลับตา (1).png")
hua_a = np.asarray(hua, np.uint8)

# ---------- fit zoomed eye set onto หัว (single source of truth) ----------
face_box = naa.getbbox()
coarse = [x / 100 for x in range(30, 62, 2)]
s, ox, oy, _ = fit_template(hua, eye_open, coarse, crop=face_box)
s, ox, oy, _ = fit_template(hua, eye_open, [s + d / 1000 for d in range(-20, 21, 5)], crop=face_box)
print(f"open-eye fit on หัว: scale={s:.3f} offset=({ox:.1f},{oy:.1f})")
v6_eyes_open = place(eye_open, s, ox, oy)
v6_eyes_white = place(eye_white, s, ox, oy)
v6_pupils = place(eye_pupil, s, ox, oy)

# for the closed set keep the masterC fit, then shift by how far the open set moved
sN, oxN, oyN, _ = fit_template(naa, eye_open, [s + d / 1000 for d in range(-15, 16, 5)], crop=face_box)
dx, dy = ox - oxN, oy - oyN
s2, ox2, oy2, _ = fit_template(masterC, eye_closed, coarse, crop=face_box)
s2, ox2, oy2, _ = fit_template(masterC, eye_closed, [s2 + d / 1000 for d in range(-20, 21, 5)], crop=face_box)
print(f"closed-eye fit: scale={s2:.3f} offset=({ox2:.1f},{oy2:.1f}) shift=({dx:.1f},{dy:.1f})")
v6_eyes_closed = place(eye_closed, s2, ox2 + dx, oy2 + dy)

# ---------- eyes_white_filled: flat-fill the die-cut pupil holes ----------
wa = np.asarray(v6_eyes_white, np.uint8).copy()
white_px = (wa[:, :, 3] > 200) & (wa[:, :, :3].mean(axis=2) > 185)
sclera = np.median(wa[:, :, :3][white_px], axis=0).astype(np.uint8)
pupil_hole = np.asarray(grow(v6_pupils.split()[3].point(lambda p: 255 if p > 8 else 0), 2)) > 128
fill_here = pupil_hole & (wa[:, :, 3] < 200)
wa[:, :, :3][fill_here] = sclera
wa[:, :, 3][fill_here] = 255
white_filled = Image.fromarray(wa)
white_filled = Image.composite(
    white_filled.filter(ImageFilter.GaussianBlur(1.2)), white_filled,
    grow(Image.fromarray((fill_here * 255).astype(np.uint8)), 1).filter(ImageFilter.GaussianBlur(1)))
save(white_filled, "v6_eyes_white.png")

# ---------- eyes_top: brows (ลืมตา strokes outside ตาขาว) + lashes, above pupils ----------
pm_all = np.asarray(v6_pupils)[:, :, 3] > 8
pys, pxs = np.where(pm_all)
y_thr = int(pys.min()) + 10
wo = np.asarray(v6_eyes_white, np.float32)
oo = np.asarray(v6_eyes_open, np.float32)
lum_o = oo[:, :, :3].mean(axis=2)
yy = np.arange(H)[:, None]
brow_w = (np.clip((170 - lum_o) / 50, 0, 1) * (oo[:, :, 3] / 255)
          * (wo[:, :, 3] < 30) * (yy < y_thr))
lum_w = wo[:, :, :3].mean(axis=2)
lash_w = np.clip((150 - lum_w) / 40, 0, 1) * (wo[:, :, 3] / 255)
top = np.zeros((H, W, 4), np.uint8)
aw = np.maximum(brow_w, lash_w)
top[:, :, :3] = np.where(brow_w[..., None] >= lash_w[..., None], oo[:, :, :3], wo[:, :, :3]).astype(np.uint8)
top[:, :, 3] = (aw * 255).astype(np.uint8)
top_im = Image.fromarray(top).filter(ImageFilter.GaussianBlur(0.4))
save(top_im, "v6_eyes_top.png")

# ---------- pupils completed to full ellipses ----------
pa = np.asarray(v6_pupils, np.uint8)
full = Image.new("RGBA", (W, H), (0, 0, 0, 0))
draw = ImageDraw.Draw(full)
for tag, sel in (("L", pxs < 512), ("R", pxs >= 512)):
    x0, x1 = int(pxs[sel].min()), int(pxs[sel].max())
    y1 = int(pys[sel].max())
    rx = (x1 - x0) / 2
    ry = rx * 0.92
    cx, cy = (x0 + x1) / 2, y1 - ry
    side = np.zeros_like(pm_all); side[:, :512] = tag == "L"; side[:, 512:] = tag == "R"
    dark = pa[:, :, :3][pm_all & side]
    sel_dark = dark.mean(axis=1) < 90
    col = tuple(int(v) for v in np.median(dark[sel_dark] if sel_dark.any() else dark, axis=0))
    draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=col + (255,))
full = full.filter(ImageFilter.GaussianBlur(1.0))
full.alpha_composite(v6_pupils)
v6_pupils = full
save(v6_pupils, "v6_pupils.png")

# ---------- region masks from the die-cuts (shape only, pixels come from หัว) ----------
naaM = np.asarray(naa.split()[3].point(lambda p: 255 if p > 128 else 0))
phomM = np.asarray(phom.split()[3].point(lambda p: 255 if p > 128 else 0))
hua_alpha_bin = np.asarray(hua)[:, :, 3] > 128
yy_g = np.arange(H)[:, None]
# ผมเต็มหัว: ปอยหน้า (ผม.png) + โดมผมด้านบนทั้งหมดจาก หัว (เหนือแนวคิ้ว) — ผู้ใช้ขอเติมด้านบนให้เต็ม
hair_mask = (np.asarray(grow(Image.fromarray(phomM), 8)) > 128) | (hua_alpha_bin & (yy_g < 480))
# หน้ายื่นใต้ผม 6px — ถ้าตัดชนกันเป๊ะ ขอบ feather ของสองชั้นจะบางพร้อมกัน เกิดเส้นโปร่งแสง
hair_core = np.asarray(shrink(Image.fromarray((hair_mask * 255).astype(np.uint8)), 6)) > 128
face_mask = (np.asarray(grow(Image.fromarray(naaM), 14)) > 128) & ~hair_core
hua_alpha = hua_a[:, :, 3]

def cut_from_head(mask, blur):
    m = Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(blur))
    out = hua_a.copy()
    out[:, :, 3] = (hua_alpha.astype(np.float32) * np.asarray(m, np.float32) / 255).astype(np.uint8)
    return out

# face patch: หัว pixels in face region, eyes punched + inpainted
face_px = cut_from_head(face_mask, 3)
eye_mask = np.asarray(grow(v6_eyes_open.split()[3].point(lambda p: 255 if p > 40 else 0), 5)) > 128
face_ne = inpaint(face_px, eye_mask & (face_px[:, :, 3] > 0))
face_ne[:, :, 3] = face_px[:, :, 3]
face_ne_im = Image.fromarray(face_ne)
blur_zone = Image.fromarray((eye_mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2))
face_ne_im = Image.composite(face_ne_im.filter(ImageFilter.GaussianBlur(2.5)), face_ne_im, blur_zone)
save(clean_edges(face_ne_im, median=False), "v6_face_noeyes.png")   # median=False ถนอมหนวดเส้นบาง

# hair patch: หัว pixels in hair region
save(clean_edges(Image.fromarray(cut_from_head(hair_mask, 2.5))), "v6_hair.png")

# base: หัว with the covered interior punched out, smear ring stays inside coverage
punch_src = face_mask | hair_mask
punch = np.asarray(shrink(Image.fromarray((punch_src * 255).astype(np.uint8)), 6)) > 128
ring = (np.asarray(grow(Image.fromarray((punch * 255).astype(np.uint8)), 4)) > 128) & ~punch
head_fill = inpaint(hua_a, ring & (hua_a[:, :, 3] > 0))
head_fill[:, :, 3] = np.where(punch, 0, hua_alpha)
save(clean_edges(Image.fromarray(head_fill), median=False), "v6_head_base.png")

save(clean_edges(kho), "v6_neck.png")

# ---------- jacket: erase the leftover ear sliver baked in beside the right hood point ----------
sa = np.asarray(suea, np.uint8).copy()
ys_, xs_ = np.mgrid[0:H, 0:W]
sliver = ((xs_ >= 755) & (xs_ <= 850) & (ys_ >= 300) & (ys_ <= 430)
          & (sa[:, :, :3].mean(axis=2) < 115) & (sa[:, :, 3] > 8))
sa[:, :, 3] = np.where(sliver, 0, sa[:, :, 3])
suea_clean = clean_edges(Image.fromarray(sa))
save(suea_clean, "v6_jacket.png")

# ---------- ears: crop from หู.png + clean the ragged cut edges ----------
ha_im = huu
a = ha_im.split()[3]
solid = a.point(lambda p: 255 if p > 100 else 0)
solid = grow(shrink(solid, 2), 2)            # binary open: kill speckle/haze at the cut
cleaned = np.asarray(ha_im, np.uint8).copy()
cleaned[:, :, 3] = np.minimum(cleaned[:, :, 3], np.asarray(solid))
# (โค้ดไสแถบดำหูซ้ายถูกถอดออก — อาร์ตหูใหม่ของผู้ใช้ 2026-08-17 ตัดมาสะอาดแล้ว)
huu_clean = Image.fromarray(cleaned)
huu_clean = huu_clean.filter(ImageFilter.GaussianBlur(0)).copy()
ca = np.asarray(huu_clean)
ys2, xs2 = np.where(ca[:, :, 3] > 8)
def fill_enclosed_holes(im):
    """อุดรูโปร่งที่อยู่ 'ข้างใน' สไปรต์ (ไดคัททะลุ) ด้วย inpaint จากรอบรู"""
    a = np.asarray(im, np.uint8).copy()
    al = a[:, :, 3] > 64
    hh, ww = al.shape
    from collections import deque
    outside = np.zeros_like(al); dq = deque()
    for x in range(ww): dq.append((0, x)); dq.append((hh - 1, x))
    for y in range(hh): dq.append((y, 0)); dq.append((y, ww - 1))
    while dq:
        y, x = dq.popleft()
        if 0 <= y < hh and 0 <= x < ww and not outside[y, x] and not al[y, x]:
            outside[y, x] = True
            dq.extend([(y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)])
    holes = ~al & ~outside
    if holes.any():
        print(f"  filled {int(holes.sum())} enclosed hole px")
        a = inpaint(a, holes)
    return Image.fromarray(a)

for tag, selE in (("L", xs2 < 512), ("R", xs2 >= 512)):
    bx = (int(xs2[selE].min()), int(ys2[selE].min()), int(xs2[selE].max()) + 1, int(ys2[selE].max()) + 1)
    crop = clean_edges(fill_enclosed_holes(huu_clean.crop(bx)))
    save(crop, f"v6_ear_{tag}.png")
    print(f"ear{tag} left={bx[0]} top={bx[1]} size={bx[2]-bx[0]}x{bx[3]-bx[1]}")

# ---------- mouth: find หัว's closed-mouth line by matching หน้า's line patch ----------
line_tpl = naa.crop((405, 690, 505, 735))     # tight patch around หน้า's mouth line (center 455,711)
ms_, mx_, my_, msc_ = fit_template(hua, line_tpl, [x / 100 for x in range(90, 111, 2)],
                                   crop=(360, 650, 620, 790))
line_cx = mx_ + (455 - 405) * ms_
line_cy = my_ + (711 - 690) * ms_
if abs(line_cx - 455) > 25 or abs(line_cy - 711) > 25:
    print(f"mouth match rejected ({line_cx:.0f},{line_cy:.0f}) — fallback to หน้า coords")
    line_cx, line_cy = 455, 711
MOUTH_LEFT = int(round(line_cx - MOUTH_LINE_IN_SPRITE[0] * MOUTH_SCALE))
MOUTH_TOP = int(round(line_cy - MOUTH_LINE_IN_SPRITE[1] * MOUTH_SCALE))
print(f"mouth line on หัว: ({line_cx:.0f},{line_cy:.0f}) → sprite at ({MOUTH_LEFT},{MOUTH_TOP})")

mw, mh = int(190 * MOUTH_SCALE), int(110 * MOUTH_SCALE)
cxe, cye, rxe, rye = [v * MOUTH_SCALE for v in MOUTH_ELL]
ell = Image.new("L", (mw, mh), 0)
ImageDraw.Draw(ell).ellipse([cxe - rxe, cye - rye, cxe + rxe, cye + rye], fill=255)
ell = ell.filter(ImageFilter.GaussianBlur(6))
for i in range(5):
    m = Image.open(os.path.join(RIG, f"mouth_{i}.png")).convert("RGBA").resize((mw, mh), Image.LANCZOS)
    am = np.asarray(m, np.uint8).copy()
    am[:, :, 3] = np.minimum(am[:, :, 3], np.asarray(ell))
    save(Image.fromarray(am), f"v6_mouth_{i}.png")

# ---------- geometry ----------
pw2 = np.asarray(v6_pupils)[:, :, 3] > 8
ys3, xs3 = np.where(pw2)
for tag, sel3 in (("L", xs3 < 512), ("R", xs3 >= 512)):
    print(f"pupil{tag} center=({(xs3[sel3].min()+xs3[sel3].max())//2},{(ys3[sel3].min()+ys3[sel3].max())//2})")
ys4, xs4 = np.where(np.asarray(white_filled)[:, :, 3] > 8)
print("eyes_white bbox", (xs4.min(), ys4.min(), xs4.max(), ys4.max()))
print(f"blink origin suggestion: ({(xs4.min()+xs4.max())//2}px {int(ys4.max())-12}px)")

# ---------- previews ----------
def rigL(n): return Image.open(os.path.join(RIG, n)).convert("RGBA")
JACKET_SPLIT = os.path.exists(os.path.join(RIG, "v6_jacket_in.png"))  # ผู้ใช้แยกเสื้อเอง: in=เงาในฮู้ด(หลังหัว) out=ตัวเสื้อ(หน้าหัว)
def preview(name, closed=False, pupil_dx=0, pupil_dy=0, mouth=None, face_dx=0):
    c = Image.new("RGBA", (W, H), (34, 34, 34, 255))
    if JACKET_SPLIT:
        c.alpha_composite(rigL("v6_jacket_in.png"))
    c.alpha_composite(rigL("v6_neck.png"))
    c.alpha_composite(rigL("v6_head_base.png"))
    fgroup = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fgroup.alpha_composite(rigL("v6_face_noeyes.png"))
    if closed:
        fgroup.alpha_composite(rigL("v6_eyes_closed.png"))
    else:
        wf = rigL("v6_eyes_white.png")
        fgroup.alpha_composite(wf)
        p = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        p.alpha_composite(rigL("v6_pupils.png"), (pupil_dx, pupil_dy))
        pa2 = np.asarray(p).copy()
        pa2[:, :, 3] = np.minimum(pa2[:, :, 3], np.asarray(wf)[:, :, 3])
        fgroup.alpha_composite(Image.fromarray(pa2))
        fgroup.alpha_composite(rigL("v6_eyes_top.png"))
    if mouth:
        fgroup.alpha_composite(rigL(f"v6_mouth_{mouth}.png"), (MOUTH_LEFT, MOUTH_TOP))
    c.alpha_composite(fgroup, (face_dx, 0))
    c.alpha_composite(rigL("v6_hair.png"), (face_dx, 0))
    c.alpha_composite(rigL("v6_jacket_out.png" if JACKET_SPLIT else "v6_jacket.png"))
    c.alpha_composite(rigL("v6_ear_L.png"), (earLx, earLy))
    c.alpha_composite(rigL("v6_ear_R.png"), (earRx, earRy))
    c.convert("RGB").resize((W // 2, H // 2)).save(os.path.join(RIG, name))
    print("preview", name)

# ear placements captured above
ca2 = np.asarray(huu_clean)
ys5, xs5 = np.where(ca2[:, :, 3] > 8)
earLx, earLy = int(xs5[xs5 < 512].min()), int(ys5[xs5 < 512].min())
earRx, earRy = int(xs5[xs5 >= 512].min()), int(ys5[xs5 >= 512].min())
print(f"ear positions: L=({earLx},{earLy}) R=({earRx},{earRy})")

preview("v6_preview_neutral.jpg")
preview("v6_preview_closed.jpg", closed=True)
preview("v6_preview_look.jpg", pupil_dx=10, pupil_dy=5)
preview("v6_preview_lookdown.jpg", pupil_dx=0, pupil_dy=6)
preview("v6_preview_talk.jpg", mouth=3)
preview("v6_preview_shift.jpg", face_dx=4)
print("DONE")
