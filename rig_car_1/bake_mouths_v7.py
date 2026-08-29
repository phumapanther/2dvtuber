# -*- coding: utf-8 -*-
"""v7 mouth upgrade for the tiger rig: cut 4 talking mouths from the viseme
sheet in ../2D_Craracter_1/ and bake them into the SAME sprite geometry the
rig already uses (172x100 box, ellipse mask, css .mouth left:386 top:695) —
index.html needs no changes. Old sprites are backed up to ../สำรอง-กู้คืน/.
Run:  python bake_mouths_v7.py
"""
import os, sys, shutil
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import numpy as np
from PIL import Image, ImageFilter, ImageDraw

RIG = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(RIG), "2D_Craracter_1",
                   "Gemini_Generated_Image_asnef7asnef7asne.jpg")
BACKUP = os.path.join(os.path.dirname(RIG), "สำรอง-กู้คืน")

BOX_W, BOX_H = 172, 100                 # กล่องสไปรต์เดิมของ rig
BOX_POS = (386, 695)                    # ตำแหน่ง css .mouth บนแคนวาส
# (state, mouth center on sheet, scale, ellipse "เฉพาะช่องปาก" (cx,cy,rx,ry))
# ฐานของสไปรต์ทุกสถานะ = ผิวหน้าจริงจาก v6_face_noeyes → ขอบตรงเสมอ
# แล้ววางแค่ช่องปากด้วยวงรีแคบ ๆ → crossfade เปลี่ยนเฉพาะริมฝีปาก ลื่นไม่กระพริบ
STATES = [
    (1, (280, 1978), 0.50, (77, 40, 42, 16)),   # section 3: เสียงเบา (แง้ม)
    (2, (447, 1279), 0.50, (77, 40, 34, 22)),   # O เบา (อ้ากลมเล็ก)
    (3, (806, 1965), 0.50, (77, 40, 58, 28)),   # section 3: ดังขึ้น (เห็นฟัน)
    (4, (1373, 1953), 0.41, (77, 38, 66, 34)),  # section 3: ดังสุด (คำราม)
]

sheet = Image.open(SRC).convert("RGB")
os.makedirs(BACKUP, exist_ok=True)
for i in range(1, 5):
    src = os.path.join(RIG, f"v6_mouth_{i}.png")
    dst = os.path.join(BACKUP, f"v6_mouth_{i}_ก่อนปรับปากv7.png")
    if os.path.exists(src) and not os.path.exists(dst):
        shutil.copy2(src, dst)
        print("backup ->", os.path.basename(dst))

# ---------- ฐานสไปรต์ = ผิวหน้าจริงตรงบริเวณปาก (ขอบตรงกับหน้าเสมอ) ----------
face_im = Image.open(os.path.join(RIG, "v6_face_noeyes.png")).convert("RGBA")
base = face_im.crop((BOX_POS[0], BOX_POS[1], BOX_POS[0] + BOX_W, BOX_POS[1] + BOX_H))
ba = np.asarray(base, np.float32).copy()
_ok = (ba[:, :, 3] > 128) & (ba[:, :, :3].mean(axis=2) > 170)
FACE_WHITE = np.median(ba[:, :, :3][_ok], axis=0)
print("face white:", FACE_WHITE.astype(int))
# ลบ "เฉพาะเส้นปากปิด" ออกจากฐาน (กรอบแคบ ไม่โดนร่องจมูก/เส้นคาง)
# เติมด้วยขนจริงจากแถวล่างของเส้น แทนที่จะเป็นสีแบน จะได้ไม่เป็นรอยขาว
line_rect = np.zeros(ba.shape[:2], bool)
line_rect[14:34, 15:125] = True
dark_line = line_rect & (ba[:, :, 3] > 128) & (ba[:, :, :3].mean(axis=2) < 150)
fur_below = np.roll(ba[:, :, :3], -16, axis=0)     # ขนใต้เส้น 16px
ba[:, :, :3][dark_line] = fur_below[dark_line]
zone = Image.fromarray((dark_line * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5))
zone = zone.filter(ImageFilter.GaussianBlur(2))
clean = Image.fromarray(np.clip(ba, 0, 255).astype(np.uint8))
soft = clean.filter(ImageFilter.GaussianBlur(2))
base = Image.composite(soft, clean, zone)

for i, (cx, cy), s, ell in STATES:
    mask = Image.new("L", (BOX_W, BOX_H), 0)
    ImageDraw.Draw(mask).ellipse([ell[0] - ell[2], ell[1] - ell[3],
                                  ell[0] + ell[2], ell[1] + ell[3]], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(4))
    # crop กรอบรอบปากให้จุดกึ่งกลางปากไปตกที่ศูนย์วงรีของสไปรต์
    left = int(cx - ell[0] / s)
    top = int(cy - ell[1] / s)
    box = sheet.crop((left, top, left + int(BOX_W / s), top + int(BOX_H / s)))
    art = box.resize((BOX_W, BOX_H), Image.LANCZOS).convert("RGBA")
    # จูนขนสว่างรอบริมฝีปากให้ตรงสีหน้าเดิม (บี้เงา 65%)
    a = np.asarray(art, np.float32)
    lum = a[:, :, :3].mean(axis=2)
    lightsel = lum > 170
    if lightsel.any():
        med = np.median(a[:, :, :3][lightsel], axis=0)
        w = np.clip((lum - 170) / 40, 0, 1)[:, :, None]
        corrected = FACE_WHITE + (a[:, :, :3] - med) * 0.35
        a[:, :, :3] = a[:, :, :3] * (1 - w) + corrected * w
    # เงากลาง ๆ (เทา) ใกล้ริมวงรี → ดันเข้าหาสีขนหน้า (กันเงาแก้มติดมุมปากคำราม)
    yy, xx = np.mgrid[0:BOX_H, 0:BOX_W]
    r = np.sqrt(((xx - ell[0]) / ell[2]) ** 2 + ((yy - ell[1]) / ell[3]) ** 2)
    rimw = np.clip((r - 0.68) / 0.30, 0, 1) * np.clip((200 - lum) / 60, 0, 1) \
        * np.clip((lum - 95) / 30, 0, 1)
    a[:, :, :3] = a[:, :, :3] * (1 - rimw[:, :, None] * 0.75) \
        + FACE_WHITE * (rimw[:, :, None] * 0.75)
    art = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    sp = base.copy()
    sp.paste(art, (0, 0), mask)         # เฉพาะช่องปากลงบนฐานหน้าจริง
    sp.save(os.path.join(RIG, f"v6_mouth_{i}.png"))
    print(f"saved v6_mouth_{i}.png (center {cx},{cy} scale {s})")

# ---------- preview: muzzle zoom on the real face stack ----------
face = Image.new("RGBA", (1024, 1536), (34, 34, 34, 255))
for n in ("v6_head_base.png", "v6_face_noeyes.png"):
    face.alpha_composite(Image.open(os.path.join(RIG, n)).convert("RGBA"))
tiles = []
for i in range(0, 5):
    c = face.copy()
    if i > 0:
        c.alpha_composite(Image.open(os.path.join(RIG, f"v6_mouth_{i}.png")), (386, 695))
    tiles.append(c.crop((330, 620, 630, 830)).resize((300, 210)))
strip = Image.new("RGB", (300 * 5, 210))
for k, t in enumerate(tiles):
    strip.paste(t.convert("RGB"), (300 * k, 0))
strip.save(os.path.join(RIG, "dev_mouths_v7.jpg"))
print("saved dev_mouths_v7.jpg  (ปิด/1/2/3/4)")
