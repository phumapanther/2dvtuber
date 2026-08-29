# -*- coding: utf-8 -*-
"""Bake โมเดลตัวที่ 6 — chibi เสือขาว (bust ไม่มีหาง ตามดีไซน์ผู้ใช้)

ต้นทางหลัก: ../2D_Craracter_Chibi/Model_PNG_Tuber (ไฟล์ PSD 1536x2304 = 1.5x ริก)
  ผู้ใช้จัดวางครบแล้ว 12 กลุ่ม (แต่ละกลุ่มชื่อ 'Mask' = ชิ้นเดียวถูก mask ไว้):
  ลำตัว, หูซ้าย/ขวา, หัว, ตาหลับซ้าย/ขวา, ตาขาวซ้าย/ขวา, ตาดำซ้าย/ขวา, ขอบตาซ้าย/ขวา
ปาก 5 แบบ + แก้มบลัช 2 สถานะ: crop พื้นขาวใน ../2D_Craracter_Chibi/ (วางตำแหน่งที่นี่)
ต้องมี: pip install psd-tools aggdraw   (mask ในไฟล์เป็น vector)
Run:  python bake_chibi.py
"""
import os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import numpy as np
from PIL import Image, ImageFilter
from psd_tools import PSDImage

RIG = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(RIG), "2D_Craracter_Chibi")
PSD = os.path.join(SRC, "Model_PNG_Tuber")
PARTS = os.path.join(RIG, "parts")
os.makedirs(PARTS, exist_ok=True)
W, H = 1024, 1536
PW, PH = 1536, 2304   # แคนวาส PSD
S = W / PW            # 1/1.5

# ---------- tunables ----------
MOUTH_SCALE = 1.05    # สเกลปากจาก crop -> ริก
CHEEK_SCALE = 0.60    # สเกลแก้ม
CHEEK_DX = 95         # แก้มห่างศูนย์ตาแนวนอน (ออกด้านนอก)
CHEEK_DY = 190        # แก้มต่ำลงจากศูนย์ตา
# กรอบเส้นปากปิด+หนวดบนหน้า (พิกัดไฟล์ หัว.png 2000x2000 — วัดจาก grid)
# ขอบบน 1280 = ใต้ตัววีจมูก (จมูกจบ ~1270) แต่เก็บปุ่มหนวดที่โค้งขึ้นถึง ~1285
# ขอบล่าง 1372 = เหนือเงาคาง (ห้ามลึกกว่านี้ เดี๋ยว fill กินเงาเป็นแถบ)
LB2000 = (735, 1280, 1165, 1372)
HB2000 = (245, 318, 1700, 1584)   # bbox ของหัวในไฟล์ หัว.png (ไว้แปลงพิกัดสู่ PSD)

# ---------- PSD: 12 กลุ่ม mask เรียงล่าง->บน ----------
psd = PSDImage.open(PSD)
art = psd[0]
groups = [l for l in art if l.is_group()]
assert len(groups) == 12, f"คาด 12 กลุ่มในไฟล์ PSD ได้ {len(groups)} — โครงไฟล์เปลี่ยน ตรวจ mapping ใหม่"
NAMES = ["body", "ear_L", "ear_R", "head", "lid_L", "lid_R",
         "white_L", "white_R", "pupil_L", "pupil_R", "rim_L", "rim_R"]
part = {}
for name, g in zip(NAMES, groups):
    cv = g.composite(viewport=(0, 0, PW, PH)).convert("RGBA")
    part[name] = cv
    print(f"{name}: bbox {cv.getbbox()}")
    cv.crop(cv.getbbox()).save(os.path.join(PARTS, name + ".png"))

def to_rig(im_psd):
    """เลเยอร์เต็มผืน PSD -> เลเยอร์เต็มผืนริก (ย่อ 1.5x)"""
    return im_psd.resize((W, H), Image.LANCZOS)

def save(img, name):
    img.save(os.path.join(RIG, name + ".png"))
    print(f"saved {name}.png")

def merged(*names):
    out = Image.new("RGBA", (PW, PH), (0, 0, 0, 0))
    for n in names:
        out.alpha_composite(part[n])
    return out

# ---------- หัว: ลบตาขาวที่วาดติดมา (กันโผล่ขอบตอนกะพริบ) ----------
head = np.asarray(part["head"]).copy()
for side in ("L", "R"):
    wh = np.asarray(part["white_" + side])
    blob = wh[..., 3] > 60                       # รูปตาขาวทั้งชิ้น (รวมขอบสติกเกอร์) = โซนตาบนหัว
    grow = np.asarray(Image.fromarray((blob * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(9))) > 128
    ys, xs = np.where(grow)
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    ring = np.zeros_like(grow); ring[y0:y1 + 1, x0:x1 + 1] = True
    ring &= ~grow
    skin = np.median(head[ring & (head[..., 3] > 200)][:, :3], axis=0)
    zone = head[y0:y1 + 1, x0:x1 + 1]
    m = grow[y0:y1 + 1, x0:x1 + 1]
    zone[m, 0], zone[m, 1], zone[m, 2] = skin.astype(np.uint8)
    # เกลี่ยรอยต่อ
    blur = np.asarray(Image.fromarray(zone).filter(ImageFilter.GaussianBlur(6)))
    edge = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(4)))[..., None] / 255.0
    zone[...] = (zone * (1 - edge) + blur * edge).astype(np.uint8)
    head[y0:y1 + 1, x0:x1 + 1] = zone

# ---------- ตัดเส้นปากปิด+หนวดออกจากหน้า -> สไปรต์ mouth_0 + เติมผิวปิดรอย ----------
hbp = part["head"].getbbox()
sx = (hbp[2] - hbp[0]) / (HB2000[2] - HB2000[0])
sy = (hbp[3] - hbp[1]) / (HB2000[3] - HB2000[1])
lb = (int(hbp[0] + (LB2000[0] - HB2000[0]) * sx), int(hbp[1] + (LB2000[1] - HB2000[1]) * sy),
      int(hbp[0] + (LB2000[2] - HB2000[0]) * sx), int(hbp[1] + (LB2000[3] - HB2000[1]) * sy))
zone = head[lb[1]:lb[3], lb[0]:lb[2]]
lum = zone[..., :3].astype(int).mean(2)
stroke_a = np.clip((165 - lum) / 30 * 255, 0, 255).astype(np.uint8)   # เหลือเฉพาะเส้นเข้ม
mouth0 = Image.fromarray(np.dstack([zone[..., :3], stroke_a]))
m0bb = mouth0.getbbox()
mouth0 = mouth0.crop(m0bb)
# กึ่งกลางชุดปากทั้งหมด = กึ่งกลางเส้นปากเดิม (px ริก)
mpx = (lb[0] + (m0bb[0] + m0bb[2]) / 2) * S
mpy = (lb[1] + (m0bb[1] + m0bb[3]) / 2) * S
# เติมผิว: ทาสีผิวรอบข้างทับเส้น แล้วเกลี่ยรอยต่อ
# mask เติมกว้างกว่าเส้นจริง (lum<210) เก็บขอบ antialias จาง ๆ ของเส้นให้หมด
strokes = np.asarray(Image.fromarray(((lum < 205) * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(11))) > 128
skin = np.median(zone[~strokes & (zone[..., 3] > 200)][:, :3], axis=0).astype(np.uint8)
zone[strokes, 0], zone[strokes, 1], zone[strokes, 2] = skin
blur = np.asarray(Image.fromarray(zone).filter(ImageFilter.GaussianBlur(9)))
edge = np.asarray(Image.fromarray((strokes * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(9)))[..., None] / 255.0
zone[...] = (zone * (1 - edge) + blur * edge).astype(np.uint8)
head[lb[1]:lb[3], lb[0]:lb[2]] = zone
save(to_rig(Image.fromarray(head)), "chibi_head")

# ---------- ลำตัว ----------
save(to_rig(part["body"]), "chibi_body")

# ---------- หู: สไปรต์แยก หมุนได้ ----------
ear_css = {}
for side in ("L", "R"):
    p = part["ear_" + side]
    bb = p.getbbox()
    sp = p.crop(bb)
    sw, sh = int(round(sp.width * S)), int(round(sp.height * S))
    sp = sp.resize((sw, sh), Image.LANCZOS)
    save(sp, "chibi_ear_" + side)
    ear_css[side] = (bb[0] * S, bb[1] * S, sw, sh)
    print(f"  ear_{side} css: left {bb[0]*S:.0f}px top {bb[1]*S:.0f}px width {sw}px; origin {sw//2}px {int(sh*0.82)}px")

# ---------- ตา ----------
save(to_rig(merged("white_L", "white_R")), "chibi_eyes_white")
save(to_rig(merged("pupil_L", "pupil_R")), "chibi_pupils")
save(to_rig(merged("rim_L", "rim_R")), "chibi_eyes_top")
save(to_rig(merged("lid_L", "lid_R")), "chibi_eyes_closed")

# mask = เนื้อขาวด้านในของตาขาว (กันตาดำเลื่อนหลุด) — หดขอบเล็กน้อยแล้วเบลอ
eye_centers = []
mask = Image.new("L", (PW, PH), 0)
for side in ("L", "R"):
    a = np.asarray(part["white_" + side])
    lum = a[..., :3].astype(int).mean(2)
    inner = (a[..., 3] > 200) & (lum > 205)
    inner = np.asarray(Image.fromarray((inner * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(11))) > 128
    ys, xs = np.where(inner)
    eye_centers.append(((xs.min() + xs.max()) / 2 * S, (ys.min() + ys.max()) / 2 * S))
    mask = Image.fromarray(np.maximum(np.asarray(mask), (inner * 255).astype(np.uint8)))
    print(f"  eye_{side}: inner {xs.min()*S:.0f},{ys.min()*S:.0f}..{xs.max()*S:.0f},{ys.max()*S:.0f} (rig)")
mask = mask.resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(1.5))
save(Image.merge("RGBA", (mask, mask, mask, mask)), "chibi_eyes_mask")
ecx = (eye_centers[0][0] + eye_centers[1][0]) / 2
ecy = (eye_centers[0][1] + eye_centers[1][1]) / 2
print(f"  eye centers rig: L {eye_centers[0][0]:.0f},{eye_centers[0][1]:.0f}  R {eye_centers[1][0]:.0f},{eye_centers[1][1]:.0f}")

# ---------- ปาก 5 สถานะ (เรียงความอ้า) ----------
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

def dilate(mask_, px):
    return np.asarray(Image.fromarray((mask_ * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(px * 2 + 1))) > 128

def blob_from(mask_, seed_yx):
    comp = np.zeros_like(mask_); comp[seed_yx] = True
    while True:
        g = comp.copy()
        g[1:, :] |= comp[:-1, :]; g[:-1, :] |= comp[1:, :]
        g[:, 1:] |= comp[:, :-1]; g[:, :-1] |= comp[:, 1:]
        g &= mask_
        if (g == comp).all():
            return comp
        comp = g

def keep_largest(mask_):
    best = None
    todo = mask_.copy()
    while todo.any():
        ys, xs = np.nonzero(todo)
        comp = blob_from(mask_, (ys[0], xs[0]))
        if best is None or comp.sum() > best.sum():
            best = comp
        todo &= ~comp
    return best if best is not None else mask_

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

def cut_white(fname):
    """crop RGB พื้นขาว -> ไดคัทเฉพาะกราฟิกปาก
    (ขอบสติกเกอร์ขาวกลืนกับพื้น — ตัดทิ้งทั้งวง ไม่งั้นเหลือวงเทา antialias ลอยเป็นผี)
    เก็บ: พิกเซลเข้ม/มีสี ก้อนใหญ่สุด + รูปิดด้านใน (แสงเงาขาวในปาก)"""
    a = np.asarray(Image.open(os.path.join(SRC, fname)).convert("RGB"), np.float32)
    lum = a.mean(axis=2); sat = a.max(axis=2) - a.min(axis=2)
    core = keep_largest((lum < 205) | (sat > 28))
    enclosed = ~core & ~flood_from_border(~core)   # ช่องว่างที่ถูกล้อม = ส่วนในปาก
    core |= enclosed
    alpha = np.where(dilate(core, 2), 255, 0).astype(np.uint8)
    aI = Image.fromarray(alpha).filter(ImageFilter.MedianFilter(3)).filter(ImageFilter.GaussianBlur(1.0))
    out = defringe(np.dstack([a.astype(np.uint8), np.asarray(aI)]))
    sp = Image.fromarray(out)
    sp = sp.crop(sp.getbbox())
    sp.save(os.path.join(PARTS, "cut_" + fname))
    print(f"  cut {fname}: {sp.width}x{sp.height}")
    return sp

# สถานะ 0 = เส้นปากปิดที่ตัดจากหน้า / 1-5 แง้ม -> ยิ้มเปิด -> เปิด+ลิ้น -> อ้ากว้าง -> โอ (ตะโกน)
mouth0_rig = mouth0.resize((int(mouth0.width * S), int(mouth0.height * S)), Image.LANCZOS)
mouths = [cut_white(f) for f in ["ปาก4.png", "ปาก1.png", "ปากสอง.png", "ปากสาม.png", "ปาก5.png"]]
mouths = [m.resize((int(m.width * MOUTH_SCALE), int(m.height * MOUTH_SCALE)), Image.LANCZOS) for m in mouths]
mouths = [mouth0_rig] + mouths
MW = max(m.width for m in mouths) + 4
MH = max(m.height for m in mouths) + 4
for i, m in enumerate(mouths):
    box = Image.new("RGBA", (MW, MH), (0, 0, 0, 0))
    box.paste(m, ((MW - m.width) // 2, (MH - m.height) // 2), m)
    save(box, f"chibi_mouth_{i}")
print(f"MOUTH: box {MW}x{MH}  ->  const MOUTH_POS = [{mpx:.0f}, {mpy:.0f}]; MOUTH_HALF = [{MW//2}, {MH//2}]")

# ---------- แก้มบลัช 2 สถานะ ----------
def cut_blush(fname):
    """ชมพูจางบนพื้นขาว -> matte จากความอิ่มสี"""
    a = np.asarray(Image.open(os.path.join(SRC, fname)).convert("RGB"), np.float32)
    sat = a.max(axis=2) - a.min(axis=2)
    alpha = np.clip((sat - 12) * 6, 0, 255).astype(np.uint8)   # -12 กันม่านขาวจางทับลายเสือ
    aI = Image.fromarray(alpha).filter(ImageFilter.GaussianBlur(1.2))
    sp = Image.fromarray(np.dstack([a.astype(np.uint8), np.asarray(aI)]))
    bb = sp.getbbox()
    return sp.crop(bb) if bb else sp

for files, name in ((("แก้มซ้าย1.png", "แก้มขวา1.png"), "chibi_cheeks_a"),
                    (("แก้มซ้าย2.png", "แก้มขวา2.png"), "chibi_cheeks_b")):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for f, (cx, cy), sd in zip(files, eye_centers, (-1, 1)):
        sp = cut_blush(f)
        cw, ch = int(sp.width * CHEEK_SCALE), int(sp.height * CHEEK_SCALE)
        spr = sp.resize((cw, ch), Image.LANCZOS)
        layer.paste(spr, (int(cx + sd * CHEEK_DX - cw / 2), int(cy + CHEEK_DY - ch / 2)), spr)
    save(layer, name)

# ---------- preview 4 ท่า ----------
def rig_img(name):
    return Image.open(os.path.join(RIG, name + ".png")).convert("RGBA")

def preview(name, blink=False, look=(0, 0), talk=0):
    cv = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    cv.alpha_composite(rig_img("chibi_body"))
    for side in ("L", "R"):
        x, y, _, _ = ear_css[side]
        e = rig_img("chibi_ear_" + side)
        tmp = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        tmp.paste(e, (int(x), int(y)), e)
        cv.alpha_composite(tmp)
    cv.alpha_composite(rig_img("chibi_head"))
    if blink:
        cv.alpha_composite(rig_img("chibi_eyes_closed"))
    else:
        cv.alpha_composite(rig_img("chibi_eyes_white"))
        pup = rig_img("chibi_pupils")
        if look != (0, 0):
            moved = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            moved.paste(pup, look, pup)
            pup = moved
        msk = rig_img("chibi_eyes_mask").split()[3]
        masked = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        masked.paste(pup, (0, 0), msk)
        cv.alpha_composite(masked)
        cv.alpha_composite(rig_img("chibi_eyes_top"))
    cv.alpha_composite(rig_img("chibi_cheeks_b" if talk else "chibi_cheeks_a"))
    m = rig_img(f"chibi_mouth_{talk}")
    tmp = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    tmp.paste(m, (int(mpx - MW / 2), int(mpy - MH / 2)), m)
    cv.alpha_composite(tmp)
    cv.convert("RGB").save(os.path.join(RIG, f"chibi_preview_{name}.jpg"), quality=88)
    print(f"preview {name}")

preview("neutral")
preview("closed", blink=True)
preview("look", look=(26, 14))
preview("talk", talk=4)
print("เสร็จ — ตรวจ chibi_preview_*.jpg ทั้ง 4 ภาพ แล้วอัปเดตเลข CSS ใน index.html ตามที่พิมพ์ไว้ข้างบน")
