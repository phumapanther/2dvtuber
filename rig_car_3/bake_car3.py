# -*- coding: utf-8 -*-
"""Bake car3 layers (rev 2 — user layout): the layers in ชิ้นส่วน/ were
positioned by the user in the PSD เลเยอร์อวาต้าต้นไม้ (canvas 1536x2304 = 1.5x
of the rig's 1024x1536, so PSD coords / 1.5 = rig coords).
- full-canvas 1024x1536 PNGs are used as-is
- หน้า/ตาขาว/ขอบตา/ตา are separate-resolution exports, placed onto the PSD
  layer boxes (hard-coded below from the PSD)
- blink needs no closed art: หน้า.png has sculpted shut eyelids — hiding the
  open-eye set reveals them
- mouths + falling leaves are still cut from the AI sheet in ../2D_Craracter_3/
Run:  python bake_car3.py
"""
import os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import numpy as np
from PIL import Image, ImageFilter

RIG = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(RIG), "2D_Craracter_3")
MAT = os.path.join(RIG, "ชิ้นส่วน")
PARTS = os.path.join(RIG, "parts")
os.makedirs(PARTS, exist_ok=True)
W, H = 1024, 1536

SHEET = "Gemini_Generated_Image_xp5x9bxp5x9bxp5x.jpg"
_sheet = None
def sheet():
    global _sheet
    if _sheet is None:
        _sheet = Image.open(os.path.join(SRC, SHEET)).convert("RGB")
    return _sheet

def mat(name):
    return Image.open(os.path.join(MAT, name + ".png")).convert("RGBA")

# ---------- sheet extraction (cream bg) — ใช้แค่ปากกับใบไม้ร่วง ----------
def flood_from_border(floodable):
    m = np.zeros_like(floodable)
    m[0, :] = floodable[0, :]; m[-1, :] = floodable[-1, :]
    m[:, 0] = floodable[:, 0]; m[:, -1] = floodable[:, -1]
    while True:
        g = m.copy()
        g[1:, :] |= m[:-1, :]; g[:-1, :] |= m[1:, :]
        g[:, 1:] |= m[:, :-1]; g[:, :-1] |= m[:, 1:]
        g &= floodable
        if (g == m).all():
            return m
        m = g

def dilate(mask, px):
    im = Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(px * 2 + 1))
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

def components(mask, min_px=400):
    out = []
    todo = mask.copy()
    while todo.any():
        ys, xs = np.nonzero(todo)
        comp = blob_from(mask, (ys[0], xs[0]))
        if comp.sum() >= min_px:
            out.append(comp)
        todo &= ~comp
    return out

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

def pick(box, largest=False, ring=12, name=""):
    im = sheet().crop(box)
    a = np.asarray(im, np.float32)
    lum = a.mean(axis=2)
    sat = a.max(axis=2) - a.min(axis=2)
    edge = np.concatenate([a[0, :, :3], a[-1, :, :3], a[:, 0, :3], a[:, -1, :3]])
    bgc = np.median(edge, axis=0)
    bg_like = np.abs(a[:, :, :3] - bgc).max(axis=2) < 30
    bg = flood_from_border(bg_like)
    white_ring = (lum > 235) & (sat < 25) & dilate(bg, ring) & ~bg
    alpha = np.where(bg | white_ring, 0, 255).astype(np.uint8)
    if largest:
        comps = components(alpha > 32, 50)
        best = max(comps, key=lambda c: c.sum())
        alpha[~dilate(best, 3)] = 0
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

# ---------- layout (จาก PSD เลเยอร์อวาต้าต้นไม้ ÷1.5) ----------
FACE_BOX = (415, 953, 614, 1217)     # กล่องวางใบหน้า
EYES_X, EYES_CY = 435, 1058          # ตาขาว/ขอบตา: ซ้ายสุด + กึ่งกลางแนวตั้ง
EYES_TARGET_W = 156                  # ความกว้างคู่ตาบนแคนวาส
PUPIL_X, PUPIL_CY, PUPIL_W = 435, 1065, 137
MOUTH_POS = (515, 1135)              # จุดกึ่งกลางปาก (ไป index.html ด้วย)
MOUTH_W = 66
MOUTH_BOX = (170, 130)
APPLE_MIN = 400                      # แยกลูกแอปเปิ้ลจากเลเยอร์รวม (px ขั้นต่ำ)
LEAF_W = 34

def canvas():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))

def save(im, nm):
    im.save(os.path.join(RIG, nm))
    print("saved", nm)

def place_content(im, box):
    """scale ให้ content bbox ของ im พอดีกับ box บนแคนวาส (บีบตามแกนได้เล็กน้อย)"""
    bb = im.getbbox()
    sp = im.crop(bb)
    sc = sp.resize((box[2] - box[0], box[3] - box[1]), Image.LANCZOS)
    c = canvas()
    c.alpha_composite(sc, (box[0], box[1]))
    return c

def place_by_width(im, left, cy, width):
    bb = im.getbbox()
    sp = im.crop(bb)
    s = width / sp.width
    sc = sp.resize((width, max(1, int(sp.height * s))), Image.LANCZOS)
    c = canvas()
    c.alpha_composite(sc, (left, int(cy - sc.height / 2)))
    return c

def assemble():
    # ----- straight copies (จัดตำแหน่งมาแล้วเต็มผืน 1024x1536)
    for out, src in {
        "car3_hollow_back.png": "โผลงไม้ด้านหลัง",
        "car3_trunk.png": "ต้นไม้ด้านหน้า",
        "car3_canopy_back.png": "ผุ่มใบใม้ด้านหลัง",
        "car3_canopy_front.png": "ผ้มใบใม้ด้านหน้า",
    }.items():
        save(mat(src), out)

    # ----- face into its PSD box (มีเปลือกตาหลับปั้นในตัว = สถานะกะพริบ)
    save(place_content(mat("หน้า"), FACE_BOX), "car3_face.png")

    # ----- eyes: ตาขาว (backing + mask), ตา (เลื่อน), ขอบตา (ทับบน)
    ew = place_by_width(mat("ตาขาว"), EYES_X, EYES_CY, EYES_TARGET_W)
    save(ew, "car3_eyes_white.png")
    aI = Image.fromarray(np.asarray(ew)[:, :, 3]).filter(ImageFilter.MaxFilter(3))
    aI = aI.filter(ImageFilter.GaussianBlur(1.0))
    mask = canvas(); mask.putalpha(aI)
    save(mask, "car3_eyes_mask.png")
    save(place_by_width(mat("ขอบตา"), EYES_X, EYES_CY, EYES_TARGET_W), "car3_eyes_top.png")

    # ตาดำ: วาง "รายข้าง" กึ่งกลางตาขาวข้างนั้นพอดี — วางทั้งคู่ด้วยสเกลรวม
    # แล้วระยะห่างระหว่างดวงจะเพี้ยน (ไฟล์ตา export คนละสเกลกับตาขาว) ทำให้ตาเหล่
    wa = np.asarray(ew)[:, :, 3]
    ys, xs = np.nonzero(wa > 64)
    midw = (xs.min() + xs.max()) / 2
    white_c = []
    for sel in (xs < midw, xs >= midw):
        white_c.append((float(xs[sel].mean()), float(ys[sel].mean())))
    pu = mat("ตา")
    bb = pu.getbbox(); pu = pu.crop(bb)
    s_pu = PUPIL_W / pu.width
    pus = pu.resize((PUPIL_W, max(1, int(pu.height * s_pu))), Image.LANCZOS)
    pa2 = np.asarray(pus)[:, :, 3]
    ys2, xs2 = np.nonzero(pa2 > 64)
    midp = (xs2.min() + xs2.max()) / 2
    c2 = canvas()
    for (wx, wy), sel in zip(white_c, (xs2 < midp, xs2 >= midp)):
        x0, x1 = xs2[sel].min(), xs2[sel].max() + 1
        y0, y1 = ys2[sel].min(), ys2[sel].max() + 1
        half = pus.crop((x0, y0, x1, y1))
        c2.alpha_composite(half, (int(wx - half.width / 2), int(wy + 2 - half.height / 2)))
        print(f"pupil placed at ({wx:.0f},{wy:.0f})")
    save(c2, "car3_pupils.png")

    # ----- apples: แยกลูกจากเลเยอร์รวม -> สไปรต์เดี่ยว แกว่งเองใน index
    ap = mat("แอปเปิ้น")
    aa = np.asarray(ap)
    comps = components(np.asarray(ap)[:, :, 3] > 64, APPLE_MIN)
    comps.sort(key=lambda c: np.nonzero(c)[1].min())
    apple_pos = []
    for i, comp in enumerate(comps, 1):
        ys, xs = np.nonzero(comp)
        x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
        piece = aa.copy()
        piece[:, :, 3] = np.where(dilate(comp, 2), aa[:, :, 3], 0)
        sp = Image.fromarray(piece).crop((x0, y0, x1, y1))
        save(sp, f"car3_apple_{i}.png")
        apple_pos.append((int(x0), int(y0)))
        print(f"apple css: #apple{i} left={x0}px top={y0}px "
              f"origin=({(x1-x0)//2}px 6px)")
    print(f"apples: {len(comps)}")

    # ----- mouths (จากแผ่น AI เหมือนเดิม) + ใบไม้ร่วง
    M = {}
    M["mouth0"] = pick((1998, 1112, 2251, 1168), largest=True, name="mouth0")
    M["mouthA"] = pick((1949, 1300, 2085, 1397), largest=True, name="mouthA")
    M["mouthI"] = pick((2092, 1307, 2232, 1390), largest=True, name="mouthI")
    M["mouthU"] = pick((2237, 1300, 2380, 1397), largest=True, name="mouthU")
    M["mouthO"] = pick((2538, 1290, 2697, 1402), largest=True, name="mouthO")
    from PIL import ImageDraw
    bw, bh = MOUTH_BOX
    for key, i in (("mouth0", 0), ("mouthA", 1), ("mouthI", 2), ("mouthU", 3), ("mouthO", 4)):
        sp = M[key]
        em = Image.new("L", sp.size, 0)
        ImageDraw.Draw(em).ellipse([sp.width * 0.06, sp.height * 0.04,
                                    sp.width * 0.94, sp.height * 0.96], fill=255)
        em = em.filter(ImageFilter.GaussianBlur(3))
        spm = np.asarray(sp, np.uint8).copy()
        spm[:, :, 3] = np.minimum(spm[:, :, 3], np.asarray(em))
        if i > 0:   # ปากเปิด: ลบสีผิวซีดรอบปาก (จะไปทับหนวดเครา)
            f32 = spm[:, :, :3].astype(np.float32)
            lum2 = f32.mean(axis=2)
            skin = ((f32[:, :, 0] > 190) & (f32[:, :, 1] > 140) & (f32[:, :, 2] > 110)
                    & (lum2 > 165) & (lum2 < 228) & ((f32[:, :, 0] - f32[:, :, 2]) < 95))
            kill = Image.fromarray((skin * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.5))
            spm[:, :, 3] = (spm[:, :, 3].astype(np.float32)
                            * (1 - np.asarray(kill, np.float32) / 255)).astype(np.uint8)
        sp = Image.fromarray(spm)
        s3 = (MOUTH_W * (0.8 if i == 0 else 1.0)) / sp.width
        sc = sp.resize((max(1, int(sp.width * s3)), max(1, int(sp.height * s3))), Image.LANCZOS)
        box = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
        box.alpha_composite(sc, (int(bw / 2 - sc.width / 2), int(bh / 2 - sc.height / 2)))
        save(box, f"car3_mouth_{i}.png")
    print(f"MOUTH_POS = [{MOUTH_POS[0]}, {MOUTH_POS[1]}]")

    for i, box in enumerate(((2330, 645, 2405, 765), (2410, 640, 2485, 765),
                             (2580, 640, 2665, 760), (2665, 635, 2765, 765)), 1):
        sp = pick(box, largest=True, name=f"leaf{i}")
        s6 = LEAF_W / sp.width
        save(sp.resize((max(1, int(sp.width * s6)), max(1, int(sp.height * s6))), Image.LANCZOS),
             f"car3_leaf_{i}.png")
    return apple_pos

# ---------- previews ----------
def rigL(n):
    return Image.open(os.path.join(RIG, n)).convert("RGBA")

def preview(name, apple_pos, closed=False, pupil_dx=0, pupil_dy=0, mouth=None):
    c = Image.new("RGBA", (W, H), (34, 34, 34, 255))
    c.alpha_composite(rigL("car3_canopy_back.png"))
    c.alpha_composite(rigL("car3_hollow_back.png"))
    c.alpha_composite(rigL("car3_face.png"))
    c.alpha_composite(rigL("car3_trunk.png"))
    if not closed:
        c.alpha_composite(rigL("car3_eyes_white.png"))
        p = canvas()
        p.alpha_composite(rigL("car3_pupils.png"), (pupil_dx, pupil_dy))
        pa = np.asarray(p).copy()
        pa[:, :, 3] = np.minimum(pa[:, :, 3], np.asarray(rigL("car3_eyes_mask.png"))[:, :, 3])
        c.alpha_composite(Image.fromarray(pa))
        c.alpha_composite(rigL("car3_eyes_top.png"))
    mp = (int(MOUTH_POS[0] - MOUTH_BOX[0] / 2), int(MOUTH_POS[1] - MOUTH_BOX[1] / 2))
    c.alpha_composite(rigL("car3_mouth_0.png"), mp)
    if mouth:
        c.alpha_composite(rigL(f"car3_mouth_{mouth}.png"), mp)
    c.alpha_composite(rigL("car3_canopy_front.png"))
    for i, (ax, ay) in enumerate(apple_pos, 1):
        c.alpha_composite(rigL(f"car3_apple_{i}.png"), (ax, ay))
    c.convert("RGB").resize((W // 2, H // 2)).save(os.path.join(RIG, name))
    print("preview", name)

if __name__ == "__main__":
    n = assemble()
    preview("car3_preview_neutral.jpg", n)
    preview("car3_preview_closed.jpg", n, closed=True)
    preview("car3_preview_look.jpg", n, pupil_dx=8, pupil_dy=4)
    preview("car3_preview_talk.jpg", n, mouth=4)
    for nm in ("car3_trunk.png", "car3_face.png", "car3_pupils.png", "car3_canopy_front.png"):
        assert np.asarray(rigL(nm))[:, :, 3].max() > 0, nm + " is empty"
    print("DONE")
