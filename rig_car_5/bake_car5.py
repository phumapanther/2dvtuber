# -*- coding: utf-8 -*-
"""Bake car5 layers — เสือขาวร่างไม่ใส่เสื้อ (ตัวที่ 5, ร่างเปลือยของ car4)
ชิ้นส่วนใน ../2D_Craracter_5/ เป็น PNG เต็มผืน 1024x1536 จัดตำแหน่งแล้วทุกชิ้น
หัว+ตัวรวมเป็นชิ้นเดียว (ตัวและหน้า.png) เพราะโมเดลนี้ "หัวกับตัวไม่ขยับ" —
ขยับแค่ หู ตา หาง (+ ปากตามเสียง)
Run:  python bake_car5.py
"""
import os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import numpy as np
from PIL import Image, ImageFilter

RIG = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(RIG), "2D_Craracter_5")
W, H = 1024, 1536

def mat(name):
    return Image.open(os.path.join(SRC, name + ".png")).convert("RGBA")

def save(im, nm):
    im.save(os.path.join(RIG, nm))
    print("saved", nm)

EAR_L_BOX = (226, 128, 403, 315)
EAR_R_BOX = (614, 136, 805, 333)
TAIL_BOX = (483, 536, 1019, 1536)

# ปากของตัว 5 = อาร์ตชุดเดียวกับ car4 (ขนาดตรงกันทุกไฟล์) แค่เลื่อนตำแหน่ง
MOUTH_MAP = {  # car5_mouth_{level}{vowel} <- ไฟล์ต้นทาง
    "1A": "ปาก", "1B": "ปาก (1)", "1C": "ปาก (2)",
    "2A": "ปาก (3)", "2B": "ปาก (4)", "2C": "ปาก (5)",
    "3A": "ปาก (6)", "3B": "ปาก (7)", "3C": "ปาก (8)",
}

def assemble():
    for out, src in {
        "car5_base.png": "ตัวและหน้า",       # หัว+ตัว ชิ้นเดียว (นิ่ง)
        "car5_hair.png": "ทรงผม",
        "car5_eyes_white.png": "ตาขาว",
        "car5_eyes_top.png": "ขอบตา",
        "car5_eyes_closed.png": "ตาหลับ",
        "car5_pupils.png": "ตาดำ",
    }.items():
        save(mat(src), out)

    # mask การเลื่อนตาดำ = รูปตาขาว
    wI = Image.fromarray(np.asarray(mat("ตาขาว"))[:, :, 3]).filter(ImageFilter.MaxFilter(3))
    wI = wI.filter(ImageFilter.GaussianBlur(1.0))
    mask = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    mask.putalpha(wI)
    save(mask, "car5_eyes_mask.png")

    for key, src in MOUTH_MAP.items():
        save(mat(src), f"car5_mouth_{key}.png")

    for nm, src, box in (("car5_ear_L.png", "หูซ้าย", EAR_L_BOX),
                         ("car5_ear_R.png", "หูขวา", EAR_R_BOX),
                         ("car5_tail.png", "หาง", TAIL_BOX)):
        sp = mat(src).crop(box)
        save(sp, nm)
        print(f"  css: left={box[0]}px top={box[1]}px size={sp.width}x{sp.height}")

# ---------- previews ----------
def rigL(n):
    return Image.open(os.path.join(RIG, n)).convert("RGBA")

def preview(name, closed=False, pupil_dx=0, pupil_dy=0, mouth=None):
    c = Image.new("RGBA", (W, H), (34, 34, 34, 255))
    c.alpha_composite(rigL("car5_tail.png"), (TAIL_BOX[0], TAIL_BOX[1]))
    c.alpha_composite(rigL("car5_ear_L.png"), (EAR_L_BOX[0], EAR_L_BOX[1]))
    c.alpha_composite(rigL("car5_ear_R.png"), (EAR_R_BOX[0], EAR_R_BOX[1]))
    c.alpha_composite(rigL("car5_base.png"))
    if closed:
        c.alpha_composite(rigL("car5_eyes_closed.png"))
    else:
        c.alpha_composite(rigL("car5_eyes_white.png"))
        p = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        p.alpha_composite(rigL("car5_pupils.png"), (pupil_dx, pupil_dy))
        pa = np.asarray(p).copy()
        pa[:, :, 3] = np.minimum(pa[:, :, 3], np.asarray(rigL("car5_eyes_mask.png"))[:, :, 3])
        c.alpha_composite(Image.fromarray(pa))
        c.alpha_composite(rigL("car5_eyes_top.png"))
    if mouth:
        c.alpha_composite(rigL(f"car5_mouth_{mouth}.png"))
    c.alpha_composite(rigL("car5_hair.png"))
    c.convert("RGB").resize((W // 2, H // 2)).save(os.path.join(RIG, name))
    print("preview", name)

if __name__ == "__main__":
    assemble()
    preview("car5_preview_neutral.jpg")
    preview("car5_preview_closed.jpg", closed=True)
    preview("car5_preview_look.jpg", pupil_dx=9, pupil_dy=4)
    preview("car5_preview_talk.jpg", mouth="3B")
    for nm in ("car5_base.png", "car5_pupils.png", "car5_tail.png"):
        assert np.asarray(rigL(nm))[:, :, 3].max() > 0, nm + " is empty"
    print("DONE")
