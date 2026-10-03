# ริกเสือฮู้ด (car1) จากอาร์ตใน แมว/ — แก้รูปใน แมว/ แล้วรัน:  python bake_car1.py
# อาร์ตทุกชิ้นวาดบนแคนวาส 1476x2085 (เฟรมเดียวกับ แมว/ตัวอย่าง.png) ย่อลงเฟรมริก 1024x1536
# สเกล/ตำแหน่ง หาจากการเทียบ v6_jacket_out.png (เฟรมริก) กับ ตัวอย่าง.png: x1476 = 1.4226*x_rig + 12, y1476 = 1.4226*y_rig - 120
from PIL import Image
import numpy as np, os

os.chdir(os.path.dirname(os.path.abspath(__file__)))
A, OX, OY = 1.4226325, 12, -120
SRC = "แมว/"


def load(f):
    im = Image.open(f).convert("RGBA")
    if im.width == 2952:  # บางไฟล์เซฟมาแคนวาส 2 เท่า
        im = im.resize((1476, 2085), Image.LANCZOS)
    return im


def shift(im, dx, dy):
    out = Image.new("RGBA", im.size)
    out.paste(im, (dx, dy))
    return out


def rows(im, y0, y1):
    """เก็บเฉพาะแถว y0 <= y < y1 (ที่เหลือโปร่งใส)"""
    a = np.asarray(im).copy()
    a[:y0, :, 3] = 0
    a[y1:, :, 3] = 0
    return Image.fromarray(a)


def save(im, out):
    w, h = round(im.width / A), round(im.height / A)
    rig = Image.new("RGBA", (1024, 1536))
    rig.alpha_composite(im.resize((w, h), Image.LANCZOS), (round(-OX / A), round(-OY / A)))
    rig.save(out, optimize=True)
    print(out, rig.getbbox())


for src, out in [
    ("Hood_in.png", "c1_hood_in.png"),
    ("Hood_out.png", "c1_hood_out.png"),
    (SRC + "v6_tail.png", "c1_tail.png"),
    (SRC + "คอ.png", "c1_neck.png"),
    (SRC + "ใบหน้าเปล่าๆ.png", "c1_face.png"),
    (SRC + "ตาขาว.png", "c1_eyes_white.png"),  # ใช้เป็น mask ตาดำด้วย
    (SRC + "ตาดำ.png", "c1_pupils.png"),
    (SRC + "ขนตา.png", "c1_lashes.png"),
    (SRC + "ไม่มีชื่อ 62_20260820214005.png", "c1_brows.png"),
    (SRC + "v6_eyes_closed.png", "c1_eyes_closed.png"),
    (SRC + "ผม.png", "c1_hair.png"),
    # ปากตามสระ: ชื่อไฟล์ต่อท้าย _สระ (เลข 2 = ตอนพูดดัง)
    (SRC + "v6_mouth_0_A.png", "c1_mouth_A.png"),
    (SRC + "car5_mouth_1A_E.png", "c1_mouth_E.png"),
    (SRC + "v6_mouth_4_I.png", "c1_mouth_I.png"),
    (SRC + "v6_mouth_3_o.png", "c1_mouth_O.png"),
    (SRC + "car5_mouth_2B_U.png", "c1_mouth_U.png"),
    (SRC + "v6_mouth_1_U2.png", "c1_mouth_U2.png"),
]:
    save(load(src), out)

# พื้นในฮู้ด: ฮู้ดใหม่แคบกว่า v6_jacket_in (ทำไว้กับฮู้ดเก่า) เลยมีช่องโปร่งระหว่างขอบฮู้ดกับเงา
# → เติมสีเงาเต็มช่องในวงฮู้ด (ขอบฮู้ด+เสื้อปิดเป็นวง) วางล่างสุด ซ่อนใต้ขอบ ไม่โผล่ขอบนอก
from scipy import ndimage
ring = (np.asarray(Image.open("c1_hood_out.png"))[..., 3] > 128) | (np.asarray(Image.open("v6_jacket_out.png"))[..., 3] > 128)
filled = ndimage.binary_fill_holes(ring)
fill = ndimage.binary_dilation(filled & ~ring, iterations=6) & ndimage.binary_erosion(filled, iterations=4)
a = np.zeros((1536, 1024, 4), np.uint8)
a[fill] = (19, 19, 19, 255)  # = สีกลางของ v6_jacket_in
Image.fromarray(a).save("c1_hood_fill.png", optimize=True)
print("c1_hood_fill.png", Image.fromarray(a).getbbox())

# จมูก+ร่องจมูก แยกจากเส้นปากปิด (แถว 877 = รอยต่อร่องจมูกกับเส้นปาก) — จมูกโชว์ตลอด, ปากปิดหายตอนพูด
nm = load(SRC + "ปากกับจมุกแบบธรรมดา.png")
save(rows(nm, 0, 877), "c1_nose.png")
save(rows(nm, 877, 2085), "c1_mouth_closed.png")

# สองไฟล์นี้วาดสูงไปทับจมูก — เลื่อนลงให้ขอบบนตรงร่องจมูกเหมือนปากอื่น (ยอดบน ~y866 กลาง x~688)
save(shift(rows(load(SRC + "v6_mouth_2_E2.png"), 0, 850), 0, 170), "c1_mouth_E2.png")  # ตัดเศษจาง ๆ แถว 891+ ทิ้ง
save(shift(load(SRC + "car5_mouth_3A_A2.png"), -32, 192), "c1_mouth_A2.png")
