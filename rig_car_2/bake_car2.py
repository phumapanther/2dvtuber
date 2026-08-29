# -*- coding: utf-8 -*-
"""Bake car2 layers (rev 2 — user layout): the die-cut layers in วัสดุ/ are
full-canvas 1024x1536 PNGs already positioned by the user (from their PSD
เลเยอร์การจัดวาง), so they are used as-is. This script only:
  - splits ด่วงตา.png into sliding iris vs static lashes (+ white backing/mask)
  - re-places the closed-eye + mouth sprites (cut from the AI sheets in
    ../2D_Craracter_2/) onto the new eye/mouth positions
  - crops the tail into a rotatable sprite
Run:  python bake_car2.py
"""
import os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import numpy as np
from PIL import Image, ImageFilter

RIG = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(RIG), "2D_Craracter_2")
MAT = os.path.join(RIG, "วัสดุ")
PARTS = os.path.join(RIG, "parts")
os.makedirs(PARTS, exist_ok=True)
W, H = 1024, 1536

SHEETS = {
    "V": "Gemini_Generated_Image_vxcaj1vxcaj1vxca.jpg",   # mouths / closed eye
}
_sheet_cache = {}
def sheet(k):
    if k not in _sheet_cache:
        _sheet_cache[k] = Image.open(os.path.join(SRC, SHEETS[k])).convert("RGB")
    return _sheet_cache[k]

def mat(name):
    return Image.open(os.path.join(MAT, name + ".png")).convert("RGBA")

# ---------- sheet extraction (same method as rev 1) ----------
def flood_from_border(floodable):
    m = np.zeros_like(floodable)
    m[0, :] = floodable[0, :]; m[-1, :] = floodable[-1, :]
    m[:, 0] = floodable[:, 0]; m[:, -1] = floodable[:, -1]
    while True:
        grown = m.copy()
        grown[1:, :] |= m[:-1, :]; grown[:-1, :] |= m[1:, :]
        grown[:, 1:] |= m[:, :-1]; grown[:, :-1] |= m[:, 1:]
        grown &= floodable
        if (grown == m).all():
            return m
        m = grown

def dilate(mask, px):
    im = Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(px * 2 + 1))
    return np.asarray(im) > 128

def erode(mask, px):
    im = Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(px * 2 + 1))
    return np.asarray(im) > 128

def blob_from(mask, seed_yx):
    comp = np.zeros_like(mask); comp[seed_yx] = True
    while True:
        g = comp.copy()
        g[1:, :] |= comp[:-1, :]; g[:-1, :] |= comp[1:, :]
        g[:, 1:] |= comp[:, :-1]; g[:, :-1] |= comp[:, 1:]
        g &= mask
        if (g == comp).all():
            return comp
        comp = g

def keep_largest(mask):
    best = None
    todo = mask.copy()
    while todo.any():
        ys, xs = np.nonzero(todo)
        comp = blob_from(mask, (ys[0], xs[0]))
        if best is None or comp.sum() > best.sum():
            best = comp
        todo &= ~comp
    return best if best is not None else mask

def defringe(a):
    opaque = a[:, :, 3] > 200
    rim = (~opaque) & dilate(opaque, 4)
    rgb = a[:, :, :3]
    filled = opaque.copy(); todo = rim.copy()
    for _ in range(6):
        if not todo.any():
            break
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            nb = np.roll(filled, (dy, dx), (0, 1))
            src = np.roll(rgb, (dy, dx), (0, 1))
            take = todo & nb
            if take.any():
                rgb[take] = src[take]; filled |= take; todo &= ~take
    a[:, :, :3] = rgb
    return a

def pick(sk, box, largest=False, ring=12, white_thr=225, name=""):
    im = sheet(sk).crop(box)
    a = np.asarray(im, np.float32)
    lum = a.mean(axis=2)
    sat = a.max(axis=2) - a.min(axis=2)
    bg_like = (sat < 26) & (lum > 105)
    bg = flood_from_border(bg_like)
    white_ring = (lum > white_thr) & (sat < 30) & dilate(bg, ring) & ~bg
    cut = bg | white_ring
    alpha = np.where(cut, 0, 255).astype(np.uint8)
    if largest:
        solid = keep_largest(alpha > 32)
        alpha[~dilate(solid, 3)] = 0
    aI = Image.fromarray(alpha).filter(ImageFilter.MedianFilter(3))
    aI = aI.filter(ImageFilter.GaussianBlur(1.0))
    out = np.dstack([a.astype(np.uint8), np.asarray(aI)])
    out = defringe(out)
    sp = Image.fromarray(out)
    bb = sp.getbbox()
    sp = sp.crop(bb) if bb else sp
    sp.save(os.path.join(PARTS, name + ".png"))
    print(f"part {name}: {sp.width}x{sp.height}")
    return sp

# ---------- layout tunables (canvas coords) ----------
# เส้นปากปิดที่วาดในใบหน้าอยู่ที่ (512, 658) — จุดกึ่งกลางสไปรต์ต้องต่ำกว่านั้น
# เพื่อให้ปากอ้า "ลงล่าง" จากริมฝีปากบน ไม่ลอยขึ้นไปกลางหน้า
# (ขอบล่าง: คางอยู่ ~718 — CY เกิน ~690 ปากล่างจะทะลุคาง)
# ตำแหน่งจริงตอนใช้งานคุมที่ MOUTH_POS ใน index.html — ค่านี้ใช้แค่ทำ preview
MOUTH_CX, MOUTH_CY, MOUTH_W = 504, 686, 58
MOUTH_BOX = (170, 130)                        # css: left=CX-85 top=CY-65
EAR_W = 130
EARL_X, EARL_Y = 334, 300                     # css sprite top-left
EARR_X, EARR_Y = 562, 300
TAIL_BOX = (717, 757, 1024, 1518)             # css: left/top = box[0]/box[1]
IRIS_ERODE = 9                                # px: kills lash strokes, keeps iris discs
SCLERA = (250, 245, 242)                      # backing behind the sliding iris

def canvas():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))

def save(im, nm):
    im.save(os.path.join(RIG, nm))
    print("saved", nm)

def centers_lr(alpha):
    """per-eye (cx, cy, w) of the left/right halves of a pair layer."""
    ys, xs = np.nonzero(alpha > 64)
    mid = (xs.min() + xs.max()) / 2
    out = []
    for sel in (xs < mid, xs >= mid):
        out.append((float(xs[sel].mean()), float(ys[sel].mean()),
                    float(xs[sel].max() - xs[sel].min())))
    return out

def assemble():
    # ----- straight copies: user already positioned these on the 1024x1536 canvas
    copies = {
        "car2_hair_back.png": "ผมด้านหลัง",
        "car2_shirt_in.png": "เสื้อด้านในหลังคอ",
        "car2_neck.png": "คอและลำตัว",
        "car2_body.png": "เสื้อด้านนอก",
        "car2_side_L.png": "ผมหางม้าด้านซ้าย",
        "car2_side_R.png": "ผมหางม้าด้านขวา",
        "car2_eyes_top.png": "ขอบตา",
        "car2_bangs.png": "ผมด้านหน้า",
    }
    for out, src in copies.items():
        save(mat(src), out)

    # face: cut the painted closed-mouth line OUT of the face and ship it as
    # sprite car2_mouth_0 instead — the whole mouth (closed + talking) is then
    # positioned by ONE knob: MOUTH_POS in index.html (no rebake to nudge it)
    from PIL import ImageDraw
    face = mat("ใบหน้า")
    lb = (480, 646, 546, 670)                      # box around the painted line (center 512,658)
    patch = face.crop(lb)
    fm = Image.new("L", patch.size, 0)
    ImageDraw.Draw(fm).rounded_rectangle(
        [3, 3, patch.width - 4, patch.height - 4], radius=8, fill=255)
    fm = fm.filter(ImageFilter.GaussianBlur(3))
    skin = face.crop((lb[0], 670, lb[2], 670 + (lb[3] - lb[1])))      # clean chin skin
    face.paste(skin, (lb[0], lb[1]), fm)           # erase line from the face
    save(face, "car2_face.png")
    bw, bh = MOUTH_BOX
    m0 = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    pa = patch.copy(); pa.putalpha(fm)
    m0.alpha_composite(pa, (bw // 2 - (512 - lb[0]), bh // 2 - (658 - lb[1])))
    save(m0, "car2_mouth_0.png")

    # ----- eyes: split ด่วงตา into sliding iris discs vs static lash strokes
    eyes = np.asarray(mat("ด่วงตา"), np.uint8).copy()
    solid = eyes[:, :, 3] > 64
    core = erode(solid, IRIS_ERODE)            # discs survive, lash strokes vanish
    ys, xs = np.nonzero(core)
    mid = (xs.min() + xs.max()) / 2
    iris_mask = np.zeros_like(solid)
    for sel in (xs < mid, xs >= mid):          # largest blob per eye = the iris disc
        side = np.zeros_like(solid)
        side[ys[sel], xs[sel]] = True
        iris_mask |= keep_largest(side)
    iris_mask = dilate(iris_mask, IRIS_ERODE) & solid

    iris = eyes.copy(); iris[:, :, 3] = np.where(iris_mask, eyes[:, :, 3], 0)
    lash = eyes.copy(); lash[:, :, 3] = np.where(iris_mask, 0, eyes[:, :, 3])
    save(Image.fromarray(iris), "car2_pupils.png")
    # lash remainder merges into the static rim layer, above the sliding iris
    top = mat("ขอบตา")
    top.alpha_composite(Image.fromarray(lash))
    save(top, "car2_eyes_top.png")

    # slide window + white backing: clean ellipse per eye, sized to tuck just
    # under the lash rim (ขอบขนตา) — smooth round edge, no morphology bumps
    from PIL import ImageDraw
    win_im = Image.new("L", (W, H), 0)
    dr = ImageDraw.Draw(win_im)
    ys, xs = np.nonzero(iris_mask)
    mid = (xs.min() + xs.max()) / 2
    for sel in (xs < mid, xs >= mid):
        x0, x1 = xs[sel].min(), xs[sel].max()
        y0, y1 = ys[sel].min(), ys[sel].max()
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        rx = (x1 - x0) / 2 * 1.12
        ry = (y1 - y0) / 2 * 1.06
        dr.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=255)
        print(f"eye ellipse: center=({cx:.0f},{cy:.0f}) r=({rx:.0f},{ry:.0f})")
    wI = win_im.filter(ImageFilter.GaussianBlur(1.5))
    mask = canvas(); mask.putalpha(wI)
    save(mask, "car2_eyes_mask.png")
    back = canvas()
    back.paste(SCLERA + (255,), (0, 0, W, H), wI)
    save(back, "car2_eyes_white.png")
    scl_c = centers_lr(np.asarray(wI))
    print("eye centers:", [(round(x), round(y), round(w)) for x, y, w in scl_c])

    # ----- closed eyes: sheet sprite (right-eye art) mirrored onto both eye centers.
    # keep only the dark lash/crease strokes — the sprite carries a square-ish
    # skin patch from the sheet cut that reads as a rectangle over the face
    closed1 = pick("V", (1628, 933, 1815, 1042), largest=True, name="closed1")
    ca = np.asarray(closed1, np.float32)
    lum = ca[:, :, :3].mean(axis=2)
    stroke = np.clip((165 - lum) / 35, 0, 1)
    ca[:, :, 3] = ca[:, :, 3] * stroke
    closed1 = Image.fromarray(ca.astype(np.uint8))
    bb = closed1.getbbox()
    if bb:
        closed1 = closed1.crop(bb)
    c = canvas()
    for i, (sx, sy, sw) in enumerate(scl_c):
        sp = closed1.transpose(Image.FLIP_LEFT_RIGHT) if i == 0 else closed1
        s = 2.6 * sw / sp.width                # window is the iris socket; lids span the full eye
        sc = sp.resize((max(1, int(sp.width * s)), max(1, int(sp.height * s))), Image.LANCZOS)
        c.alpha_composite(sc, (int(sx - sc.width / 2), int(sy - sc.height * 0.5)))
    save(c, "car2_eyes_closed.png")

    # ----- mouths: sheet sprites re-scaled to the new (smaller) face
    P = {}
    P["mouthA"] = pick("V", (70, 1104, 267, 1245), name="mouthA")
    P["mouthI"] = pick("V", (288, 1119, 500, 1245), name="mouthI")
    P["mouthU"] = pick("V", (70, 1287, 267, 1428), name="mouthU")
    P["mouthO"] = pick("V", (288, 1287, 492, 1428), name="mouthO")
    bw, bh = MOUTH_BOX
    for key, i in (("mouthI", 1), ("mouthU", 2), ("mouthA", 3), ("mouthO", 4)):
        sp = P[key]
        s = MOUTH_W / sp.width
        sc = sp.resize((max(1, int(sp.width * s)), max(1, int(sp.height * s))), Image.LANCZOS)
        box = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
        box.alpha_composite(sc, (int(bw / 2 - sc.width / 2), int(bh / 2 - sc.height / 2)))
        save(box, f"car2_mouth_{i}.png")
    print(f"mouth css: left={MOUTH_CX - bw // 2}px top={MOUTH_CY - bh // 2}px")

    # ----- ears: full sprites, no crop / no side fades (ตัวหูครบไม่แหว่ง) —
    # only a long soft fade on the lower part so the rectangular crop bottom
    # (old-hair pixels) melts into the new hair instead of showing a seam
    for nm, src in (("car2_ear_L.png", "earL"), ("car2_ear_R.png", "earR")):
        sp = mat(src)
        s = EAR_W / sp.width
        sc = sp.resize((int(sp.width * s), int(sp.height * s)), Image.LANCZOS)
        a = np.asarray(sc, np.uint8).copy()
        n0 = int(sc.height * 0.58)
        fade = np.ones(sc.height, np.float32)
        fade[n0:] = np.linspace(1, 0, sc.height - n0)
        a[:, :, 3] = (a[:, :, 3] * fade[:, None]).astype(np.uint8)
        save(Image.fromarray(a), nm)
        print(f"{nm}: {sc.width}x{sc.height}")

    # ----- tail: positioned crop -> rotatable sprite
    save(mat("หาง").crop(TAIL_BOX), "car2_tail.png")
    print(f"tail css: left={TAIL_BOX[0]}px top={TAIL_BOX[1]}px "
          f"size={TAIL_BOX[2]-TAIL_BOX[0]}x{TAIL_BOX[3]-TAIL_BOX[1]}")
    return scl_c

# ---------- previews ----------
def rigL(n):
    return Image.open(os.path.join(RIG, n)).convert("RGBA")

def preview(name, closed=False, pupil_dx=0, pupil_dy=0, mouth=None):
    c = Image.new("RGBA", (W, H), (34, 34, 34, 255))
    c.alpha_composite(rigL("car2_tail.png"), (TAIL_BOX[0], TAIL_BOX[1]))
    c.alpha_composite(rigL("car2_hair_back.png"))
    c.alpha_composite(rigL("car2_shirt_in.png"))
    c.alpha_composite(rigL("car2_neck.png"))
    c.alpha_composite(rigL("car2_body.png"))
    c.alpha_composite(rigL("car2_side_L.png"))
    c.alpha_composite(rigL("car2_side_R.png"))
    c.alpha_composite(rigL("car2_face.png"))
    if closed:
        c.alpha_composite(rigL("car2_eyes_closed.png"))
    else:
        c.alpha_composite(rigL("car2_eyes_white.png"))
        p = canvas()
        p.alpha_composite(rigL("car2_pupils.png"), (pupil_dx, pupil_dy))
        pa = np.asarray(p).copy()
        pa[:, :, 3] = np.minimum(pa[:, :, 3], np.asarray(rigL("car2_eyes_mask.png"))[:, :, 3])
        c.alpha_composite(Image.fromarray(pa))
        c.alpha_composite(rigL("car2_eyes_top.png"))
    mpos = (MOUTH_CX - MOUTH_BOX[0] // 2, MOUTH_CY - MOUTH_BOX[1] // 2)
    c.alpha_composite(rigL("car2_mouth_0.png"), mpos)
    if mouth:
        c.alpha_composite(rigL(f"car2_mouth_{mouth}.png"), mpos)
    c.alpha_composite(rigL("car2_ear_L.png"), (EARL_X, EARL_Y))
    c.alpha_composite(rigL("car2_ear_R.png"), (EARR_X, EARR_Y))
    c.alpha_composite(rigL("car2_bangs.png"))  # ผมหน้าอยู่หน้าหู
    c.convert("RGB").resize((W // 2, H // 2)).save(os.path.join(RIG, name))
    print("preview", name)

if __name__ == "__main__":
    assemble()
    preview("car2_preview_neutral.jpg")
    preview("car2_preview_closed.jpg", closed=True)
    preview("car2_preview_look.jpg", pupil_dx=8, pupil_dy=4)
    preview("car2_preview_talk.jpg", mouth=3)
    for nm in ("car2_face.png", "car2_pupils.png", "car2_body.png", "car2_tail.png"):
        assert np.asarray(rigL(nm))[:, :, 3].max() > 0, nm + " is empty"
    print("DONE")
