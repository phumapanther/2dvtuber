# -*- coding: utf-8 -*-
"""PhumaPanther helper: broadcast global mic level + mouse position to the avatar.

Usage:  python helper.py           (default input device)
        python helper.py --dev 3   (pick device #3 from the printed list)
"""
import asyncio
import ctypes
import ctypes.wintypes
import http.server
import json
import os
import sys
import threading
import time
import urllib.parse

import numpy as np
import sounddevice as sd
import websockets

LEVEL = 0.0
LAST_PRINT = 0.0

# ---- อ่าน rig_studio/.env (STREAMLABS_SOCKET_TOKEN=..) ถ้ามี — ใช้เชื่อม Streamlabs Socket API ----
def load_env():
    env = {}
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    except FileNotFoundError:
        pass
    return env

STREAMLABS_TOKEN = load_env().get("STREAMLABS_SOCKET_TOKEN", "")

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

# ---- คีย์บอร์ดทั้งเครื่อง: นับจังหวะพิมพ์ + คีย์ลัดอีโมต Ctrl+Alt+1..9 + ปุ่มเมาส์ ----
GAK = u32.GetAsyncKeyState
MODS = {0x10, 0x11, 0x12, 0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0x5B, 0x5C}  # shift/ctrl/alt/win
MOUSE_VK = {0x01, 0x02, 0x04, 0x05, 0x06}
prev_keys = [0] * 256
typed = 0
emote_hot = 0

def poll_keys():
    global typed, emote_hot
    ctrl = GAK(0x11) & 0x8000
    alt = GAK(0x12) & 0x8000
    for vk in range(0x08, 0xFF):
        s = GAK(vk) & 0x8000
        if s and not prev_keys[vk]:
            if vk not in MODS and vk not in MOUSE_VK:
                typed += 1
            if ctrl and alt:
                if 0x31 <= vk <= 0x39:      # แถวเลข 1-9
                    emote_hot = vk - 0x30
                elif 0x61 <= vk <= 0x69:    # numpad 1-9
                    emote_hot = vk - 0x60
        prev_keys[vk] = s

CLIENTS = set()
DONATE = []  # คิวแจ้งเตือนโดเนทจากสะพาน HTTP
FX = []      # คิวปาของ (tomato/heart/rock) จากสะพาน HTTP
FX_KINDS = {"tomato", "heart", "rock"}

# ---- สะพานคำสั่ง HTTP (พอร์ต 8766): ให้ Stream Deck / Streamer.bot / สคริปต์อื่นสั่งอวตารได้ ----
#   http://127.0.0.1:8766/emote?n=3
#   http://127.0.0.1:8766/donate?name=สมชาย&amount=100&msg=สู้ๆ
#   http://127.0.0.1:8766/fx?type=tomato   (หรือ heart / rock — ผูกกับคำสั่งแชท เช่น !throw ใน Streamer.bot)
def start_http_bridge():
    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            global emote_hot
            u = urllib.parse.urlparse(self.path)
            q = urllib.parse.parse_qs(u.query)
            if u.path == "/emote":
                try:
                    n = int(q.get("n", ["0"])[0])
                except ValueError:
                    n = 0
                if 1 <= n <= 9:
                    emote_hot = n
                body = b"ok"
            elif u.path == "/donate":
                DONATE.append({"name": q.get("name", ["ผู้ใจดี"])[0],
                               "amount": q.get("amount", [""])[0],
                               "msg": q.get("msg", [""])[0]})
                body = b"ok"
            elif u.path == "/fx":
                kind = q.get("type", [""])[0]
                if kind in FX_KINDS:
                    FX.append(kind)
                    body = b"ok"
                else:
                    body = ("!! /fx?type= ต้องเป็น tomato / heart / rock\n").encode("utf-8")
            else:
                body = ("PhumaPanther bridge:\n"
                        "/emote?n=1-9\n"
                        "/donate?name=..&amount=..&msg=..\n"
                        "/fx?type=tomato|heart|rock\n").encode("utf-8")
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)
        def log_message(self, *a):
            pass
    try:
        srv = http.server.ThreadingHTTPServer(("127.0.0.1", 8766), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        print("สะพานคำสั่ง: http://127.0.0.1:8766/emote?n=3  หรือ  /donate?name=..&amount=..&msg=..")
    except OSError as e:
        print("!! เปิดพอร์ตสะพานคำสั่ง 8766 ไม่ได้:", e)

async def handler(ws):
    CLIENTS.add(ws)
    print(">> โมเดลเชื่อมต่อแล้ว ✓  (ทั้งหมด %d)" % len(CLIENTS))
    if STREAMLABS_TOKEN:
        try:
            await ws.send(json.dumps({"slToken": STREAMLABS_TOKEN}))
        except Exception:
            pass
    try:
        # รีเลย์: หน้าควบคุม (เบราว์เซอร์) ส่งอีโมต/ปาของ/เปลี่ยนอวตาร → ส่งต่อให้หน้าอื่นทุกตัว (OBS)
        async for raw in ws:
            for other in list(CLIENTS):
                if other is not ws:
                    try:
                        await other.send(raw)
                    except Exception:
                        CLIENTS.discard(other)
    finally:
        CLIENTS.discard(ws)
        print(">> โมเดลตัดการเชื่อมต่อ (เหลือ %d)" % len(CLIENTS))

async def broadcaster():
    global LEVEL, LAST_PRINT, typed, emote_hot
    while True:
        mx, my = cursor()
        poll_keys()
        msg_d = {"level": round(LEVEL, 4), "mx": mx, "my": my,
                 "vx": VX, "vy": VY, "vw": VW, "vh": VH,
                 "keys": typed, "mb": 1 if GAK(0x01) & 0x8000 else 0,
                 "emote": emote_hot}
        if DONATE:
            msg_d["donate"] = DONATE.pop(0)
        if FX:
            msg_d["fx"] = FX.pop(0)
        msg = json.dumps(msg_d)
        typed = 0
        emote_hot = 0
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
    if STREAMLABS_TOKEN:
        print("เชื่อม Streamlabs Socket API แล้ว (จะอ่านทิป/Superchat ให้อัตโนมัติถ้าเปิด 🗣️ ในเมนู)")
    else:
        print("ไม่พบ STREAMLABS_SOCKET_TOKEN ใน rig_studio/.env — จะไม่อ่านทิป/Superchat อัตโนมัติ")
    print("คีย์ลัดอีโมตทั้งเครื่อง: Ctrl+Alt+1..9 (พยักหน้า/ส่ายหน้า/ตกใจ/เอียงคอ/เด้ง/หมุน/สั่น/หลับ/ตื่นเต้น)")
    print("ปาของจากแชท/Stream Deck: http://127.0.0.1:8766/fx?type=tomato|heart|rock")
    start_http_bridge()
    print("พูดใส่ไมค์ดู: ต้องมีแถบ 'เสียง: ###' วิ่งขึ้นมา / ตอน OBS โหลดโมเดล ต้องขึ้น 'โมเดลเชื่อมต่อแล้ว ✓'")
    await broadcaster()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
