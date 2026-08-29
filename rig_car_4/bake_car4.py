# -*- coding: utf-8 -*-
"""Bake car4 layers — เสือขาวเสื้อแทร็ค (ตัวที่ 4)
ชิ้นส่วนใน ../2D_Craracter_4/ เป็น PNG เต็มผืน 1024x1536 จัดตำแหน่งมาแล้ว
ทุกชิ้น (ผู้ใช้จัดใน PSD เลเยอร์_โมเดล) — สคริปต์นี้แค่ก๊อป/ครอปเป็นสไปรต์
ที่ต้องหมุนได้ (หู หาง) + สร้าง mask ตา + ทำ preview ตรวจ
Run:  python bake_car4.py
"""
import os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import numpy as np
from PIL import Image, ImageFilter

RIG = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(RIG), "2D_Craracter_4")
W, H = 1024, 1536

def mat(name):
    return Image.open(os.path.join(SRC, name + ".png")).convert("RGBA")

def save(im, nm):
    im.save(os.path.join(RIG, nm))
    print("saved", nm)

# สไปรต์หมุนได้: (ไฟล์ต้นทาง, ชื่อออก, กรอบครอปตาม bbox จริง)
EAR_L_BOX = (207, 136, 384, 323)
EAR_R_BOX = (584, 145, 774, 341)
TAIL_BOX = (482, 450, 1018, 1474)

def assemble():
    # ----- ลำตัว (ฐานผิว อยู่ลึกสุดก่อนหาง): ใช้ body.png ที่ผู้ใช้วางในโฟลเดอร์ริก
    # ถ้าไม่มีค่อยใช้ ลำตัว.png จากโฟลเดอร์ต้นทาง
    local_body = os.path.join(RIG, "body.png")
    body = Image.open(local_body).convert("RGBA") if os.path.exists(local_body) \
        else mat("ลำตัว")
    save(body, "car4_body.png")

    # ----- ก๊อปตรง (เต็มผืน จัดตำแหน่งแล้ว)
    for out, src in {
        "car4_shirt.png": "เสื้อ",
        "car4_face.png": "ใบหน้า",
        "car4_hair.png": "ทรงผม",
        "car4_eyes_white.png": "ตาขาว",
        "car4_eyes_top.png": "ขอบตา",
        "car4_eyes_closed.png": "ตาปิด",
    }.items():
        save(mat(src), out)

    # ----- ตาดำ: ซ้าย+ขวารวมเป็นเลเยอร์เดียว (เลื่อนพร้อมกัน)
    pu = mat("ตาซ้าย")
    pu.alpha_composite(mat("ตาขวา"))
    save(pu, "car4_pupils.png")

    # ----- mask การเลื่อนตาดำ = รูปตาขาว
    wI = Image.fromarray(np.asarray(mat("ตาขาว"))[:, :, 3]).filter(ImageFilter.MaxFilter(3))
    wI = wI.filter(ImageFilter.GaussianBlur(1.0))
    mask = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    mask.putalpha(wI)
    save(mask, "car4_eyes_mask.png")

    # ----- ปาก 9 แบบ: 3 ระดับเสียง x 3 สระ (เต็มผืน ใช้ตรง ๆ)
    for lvl, th in ((1, "เบา"), (2, "กลาง"), (3, "ดัง")):
        for v in ("A", "B", "C"):
            save(mat(f"เสียง{th}{v}"), f"car4_mouth_{lvl}{v}.png")

    # ----- หู/หาง: ครอปเป็นสไปรต์หมุนได้
    for nm, src, box in (("car4_ear_L.png", "หูซ้าย", EAR_L_BOX),
                         ("car4_ear_R.png", "หูขวา", EAR_R_BOX),
                         ("car4_tail.png", "หาง", TAIL_BOX)):
        sp = mat(src).crop(box)
        save(sp, nm)
        print(f"  css: left={box[0]}px top={box[1]}px size={sp.width}x{sp.height}")

# ---------- previews ----------
def rigL(n):
    return Image.open(os.path.join(RIG, n)).convert("RGBA")

def preview(name, closed=False, pupil_dx=0, pupil_dy=0, mouth=None):
    c = Image.new("RGBA", (W, H), (34, 34, 34, 255))
    c.alpha_composite(rigL("car4_body.png"))
    c.alpha_composite(rigL("car4_tail.png"), (TAIL_BOX[0], TAIL_BOX[1]))
    c.alpha_composite(rigL("car4_ear_L.png"), (EAR_L_BOX[0], EAR_L_BOX[1]))
    c.alpha_composite(rigL("car4_ear_R.png"), (EAR_R_BOX[0], EAR_R_BOX[1]))
    c.alpha_composite(rigL("car4_face.png"))
    if closed:
        c.alpha_composite(rigL("car4_eyes_closed.png"))
    else:
        c.alpha_composite(rigL("car4_eyes_white.png"))
        p = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        p.alpha_composite(rigL("car4_pupils.png"), (pupil_dx, pupil_dy))
        pa = np.asarray(p).copy()
        pa[:, :, 3] = np.minimum(pa[:, :, 3], np.asarray(rigL("car4_eyes_mask.png"))[:, :, 3])
        c.alpha_composite(Image.fromarray(pa))
        c.alpha_composite(rigL("car4_eyes_top.png"))
    if mouth:
        c.alpha_composite(rigL(f"car4_mouth_{mouth}.png"))
    c.alpha_composite(rigL("car4_hair.png"))
    c.alpha_composite(rigL("car4_shirt.png"))
    c.convert("RGB").resize((W // 2, H // 2)).save(os.path.join(RIG, name))
    print("preview", name)

if __name__ == "__main__":
    assemble()
    preview("car4_preview_neutral.jpg")
    preview("car4_preview_closed.jpg", closed=True)
    preview("car4_preview_look.jpg", pupil_dx=9, pupil_dy=4)
    preview("car4_preview_talk.jpg", mouth="3B")
    for nm in ("car4_face.png", "car4_pupils.png", "car4_shirt.png", "car4_tail.png"):
        assert np.asarray(rigL(nm))[:, :, 3].max() > 0, nm + " is empty"
    print("DONE")
