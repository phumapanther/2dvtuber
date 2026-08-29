# -*- coding: utf-8 -*-
"""Bake die-cut eye layers from eyeL_open/eyeR_open:
  eye*_base.png    - eye with the iris removed (clean sclera), lids/lashes intact
  iris*.png        - round die-cut iris (hidden parts synthesized) that can slide
  opening*_mask.png- white-on-black mask of the eye opening (clips the moving iris)
Run:  python bake_eye_layers.py   (re-run after retuning the polygons below)"""
import os
from PIL import Image, ImageDraw, ImageFilter, ImageChops, ImageStat

RIG = os.path.dirname(os.path.abspath(__file__))

# hand-traced on a 10px grid over the sprites
EYES = {
    "L": {
        "sprite": "eyeL_open.png",
        "opening": [(38, 64), (45, 53), (55, 50), (65, 47), (75, 43), (85, 38),
                    (95, 33), (102, 31), (106, 36), (107, 48), (105, 62), (98, 74),
                    (88, 82), (75, 87), (60, 86), (48, 80), (40, 72)],
        "iris": (88, 64, 23, 21),      # cx, cy, rx, ry
    },
    "R": {
        "sprite": "eyeR_open.png",
        "opening": [(55, 77), (62, 68), (72, 63), (85, 60), (100, 55), (115, 51),
                    (130, 46), (145, 41), (157, 39), (164, 44), (166, 52), (160, 63),
                    (150, 74), (138, 84), (124, 92), (108, 96), (90, 96), (74, 92),
                    (62, 86)],
        "iris": (116, 73, 28, 21),
    },
}

def poly_mask(size, pts, blur):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).polygon(pts, fill=255)
    return m.filter(ImageFilter.GaussianBlur(blur))

def ellipse_mask(size, cx, cy, rx, ry, blur):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=255)
    return m.filter(ImageFilter.GaussianBlur(blur))

for key, cfg in EYES.items():
    img = Image.open(os.path.join(RIG, cfg["sprite"])).convert("RGBA")
    w, h = img.size
    cx, cy, rx, ry = cfg["iris"]

    opening = poly_mask((w, h), cfg["opening"], 1.5)
    opening.save(os.path.join(RIG, f"opening{key}_mask.png"))

    # --- base: fill the whole opening with clean sclera ---
    # sclera color = median of the brightest 25% pixels in the opening minus the iris
    hard_open = opening.point(lambda a: 255 if a > 128 else 0)
    not_iris = ImageChops.subtract(hard_open, ellipse_mask((w, h), cx, cy, rx + 3, ry + 3, 0))
    px = [p for p, m in zip(img.convert("RGB").getdata(), not_iris.getdata()) if m]
    px.sort(key=sum, reverse=True)
    bright = px[: max(1, len(px) // 4)]
    r = sorted(p[0] for p in bright)[len(bright) // 2]
    g = sorted(p[1] for p in bright)[len(bright) // 2]
    b = sorted(p[2] for p in bright)[len(bright) // 2]
    fill = Image.new("RGBA", (w, h), (r, g, b, 255))
    # soft lid shadow along the top of the opening for depth
    shadow = Image.new("L", (w, h), 0)
    top_edge = opening.point(lambda a: 255 if a > 40 else 0)
    up = top_edge.transform((w, h), Image.AFFINE, (1, 0, 0, 0, 1, 8))  # shifted down
    rim = ImageChops.subtract(top_edge, up).filter(ImageFilter.GaussianBlur(4))
    shade = Image.new("RGBA", (w, h), (int(r * .72), int(g * .72), int(b * .72), 255))
    fill.paste(shade, (0, 0), rim.point(lambda a: int(a * 0.9)))
    base = img.copy()
    base.paste(fill, (0, 0), poly_mask((w, h), cfg["opening"], 1.0))
    base.save(os.path.join(RIG, f"eye{key}_base.png"))

    # --- iris: original pixels inside the opening, synthesized where hidden ---
    core = ellipse_mask((w, h), cx, cy, int(rx * .6), int(ry * .6), 0)
    dark = ImageStat.Stat(img.convert("RGB"), mask=core).median
    iris = Image.new("RGBA", (w, h), tuple(dark) + (255,))
    inside = opening.point(lambda a: 255 if a > 128 else 0).filter(ImageFilter.GaussianBlur(2))
    iris.paste(img, (0, 0), inside)          # real art where visible, dark fill elsewhere
    iris.putalpha(ellipse_mask((w, h), cx, cy, rx, ry, 2))
    iris.save(os.path.join(RIG, f"iris{key}.png"))
    print(f"eye{key}: base/iris/opening saved  sclera={r},{g},{b} iris_dark={dark}")
