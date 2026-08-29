# -*- coding: utf-8 -*-
"""PhumaPanther helper: broadcast global mic level + mouse position to the avatar.

Usage:  python helper.py           (default input device)
        python helper.py --dev 3   (pick device #3 from the printed list)
"""
import asyncio
import ctypes
import ctypes.wintypes
import json
import sys
import time

import numpy as np
import sounddevice as sd
import websockets

LEVEL = 0.0
LAST_PRINT = 0.0

def audio_cb(indata, frames, t, status):
    global LEVEL
    rms = float(np.sqrt(np.mean(indata.astype(np.float32) ** 2)))
    LEVEL = max(LEVEL * 0.6, rms)

def cursor():
    pt = ctypes.wintypes.POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y

u32 = ctypes.windll.user32
VX, VY = u32.GetSystemMetrics(76), u32.GetSystemMetrics(77)
VW, VH = u32.GetSystemMetrics(78), u32.GetSystemMetrics(79)

CLIENTS = set()

async def handler(ws):
    CLIENTS.add(ws)
    print(">> โมเดลเชื่อมต่อแล้ว ✓  (ทั้งหมด %d)" % len(CLIENTS))
    try:
        await ws.wait_closed()
    finally:
        CLIENTS.discard(ws)
        print(">> โมเดลตัดการเชื่อมต่อ (เหลือ %d)" % len(CLIENTS))

async def broadcaster():
    global LEVEL, LAST_PRINT
    while True:
        mx, my = cursor()
        msg = json.dumps({"level": round(LEVEL, 4), "mx": mx, "my": my,
                          "vx": VX, "vy": VY, "vw": VW, "vh": VH})
        for ws in list(CLIENTS):
            try:
                await ws.send(msg)
            except Exception:
                CLIENTS.discard(ws)
        # live meter so you can SEE the mic working
        now = time.time()
        if LEVEL > 0.01 and now - LAST_PRINT > 0.25:
            LAST_PRINT = now
            print("เสียง: " + "#" * min(40, int(LEVEL * 300)))
        LEVEL *= 0.9
        await asyncio.sleep(1 / 30)

async def main():
    print("=== รายชื่ออุปกรณ์ไมค์ในเครื่อง ===")
    for i, d in enumerate(sd.query_devices()):
        if d["max_input_channels"] > 0:
            print(f"  [{i}] {d['name']}")
    dev = None
    if "--dev" in sys.argv:
        dev = int(sys.argv[sys.argv.index("--dev") + 1])
    try:
        stream = sd.InputStream(device=dev, channels=1, samplerate=16000,
                                blocksize=512, callback=audio_cb)
        stream.start()
        name = sd.query_devices(dev if dev is not None else sd.default.device[0])["name"]
        print(f"ใช้ไมค์: {name}")
        print("(ถ้าไมค์ไม่ใช่ตัวที่พูดจริง ปิดหน้าต่างนี้แล้วรันใหม่: python helper.py --dev <เลข>)")
    except Exception as e:
        print("!! ไมค์เปิดไม่ได้ (ปากจะไม่ขยับ):", e)
    try:
        server = await websockets.serve(handler, "127.0.0.1", 8765)
    except OSError as e:
        print("!! เปิดพอร์ต 8765 ไม่ได้ — อาจมีตัวช่วยเปิดซ้ำอยู่แล้ว:", e)
        return
    print("ตัวช่วยทำงานแล้ว (ws://127.0.0.1:8765) — เปิดค้างไว้ตอนสตรีม")
    print("พูดใส่ไมค์ดู: ต้องมีแถบ 'เสียง: ###' วิ่งขึ้นมา / ตอน OBS โหลดโมเดล ต้องขึ้น 'โมเดลเชื่อมต่อแล้ว ✓'")
    await broadcaster()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
