# -*- coding: utf-8 -*-
"""dev tool: contact sheet of extracted parts + gridded sheet crops for box tuning"""
import os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from PIL import Image, ImageDraw
RIG = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RIG)
from bake_car2 import sheet, PARTS

def checker(w, h, s=16):
    im = Image.new("RGB", (w, h), (90, 90, 90))
    d = ImageDraw.Draw(im)
    for y in range(0, h, s):
        for x in range(0, w, s):
            if (x // s + y // s) % 2:
                d.rectangle([x, y, x + s, y + s], fill=(130, 130, 130))
    return im

def contact(names, out, cell=260):
    cols = 4
    rows = (len(names) + cols - 1) // cols
    c = checker(cols * cell, rows * (cell + 18))
    d = ImageDraw.Draw(c)
    for i, n in enumerate(names):
        p = Image.open(os.path.join(PARTS, n + ".png")).convert("RGBA")
        s = min((cell - 8) / p.width, (cell - 8) / p.height, 1.5)
        p = p.resize((max(1, int(p.width * s)), max(1, int(p.height * s))))
        x = (i % cols) * cell; y = (i // cols) * (cell + 18)
        c.paste(p, (x + 4, y + 16), p)
        d.text((x + 4, y + 2), n, fill=(255, 255, 0))
    c.save(os.path.join(RIG, out))
    print("saved", out)

def grid_crop(sk, box, out, step=50):
    im = sheet(sk).crop(box).convert("RGB")
    d = ImageDraw.Draw(im)
    for x in range(0, im.width, step):
        d.line([x, 0, x, im.height], fill=(255, 0, 0), width=1)
        d.text((x + 2, 2), str(box[0] + x), fill=(255, 0, 0))
    for y in range(0, im.height, step):
        d.line([0, y, im.width, y], fill=(0, 160, 255), width=1)
        d.text((2, y + 2), str(box[1] + y), fill=(0, 160, 255))
    im.save(os.path.join(RIG, out))
    print("saved", out)

contact(["face", "eyeswhite", "pupils", "lashes",
         "wink", "bangs", "sideL", "sideR",
         "hairback", "earL", "earR", "tail"], "dev_parts1.jpg")
grid_crop("W", (620, 660, 1280, 1100), "dev_hairears.jpg")
