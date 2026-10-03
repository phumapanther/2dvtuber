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

FS = 16000
BUF = np.zeros(1024, np.float32)  # เสียงล่าสุด ~64ms ไว้วิเคราะห์สระ

def audio_cb(indata, frames, t, status):
    global LEVEL, BUF
    x = indata[:, 0].astype(np.float32)
    rms = float(np.sqrt(np.mean(x ** 2)))
    LEVEL = max(LEVEL * 0.6, rms)
    BUF = np.concatenate((BUF, x))[-1024:]

# ---- สระจากเสียงพูด: หา F1/F2 (ฟอร์แมนต์) ด้วย LPC แล้วเทียบสระที่ใกล้สุด → หน้าอวตารเลือกรูปปากตามสระ ----
# ค่ากลาง F1/F2 (Hz) ของแต่ละสระ: ใช้ของผู้พูดเองจาก vowels.json (ตั้งค่าเสียงสระ.bat) ถ้ามี — แม่นสุด ไม่ต้องเดา
# ไม่มีก็ใช้ค่ามาตรฐาน + จำสเกลเสียงผู้พูดแบบช้ามาก (~1 นาที, จำกัด ±25%) — ถ้าปรับเร็ว ร้องสระค้าง
# จุดกลางจะไหลตามจนจับเป็นสระข้าง ๆ (อีค้าง→เอ, อาค้าง→เอ, อูค้าง→โอ)
VOWELS = {"A": (780, 1300), "E": (480, 1900), "I": (300, 2250), "O": (480, 880), "U": (350, 780)}  # อู F1 ตามที่ LPC วัดได้จริง (ประเมินสูงกว่าตำรานิดหน่อย)
THAI = {"A": "อา", "E": "เอ", "I": "อี", "O": "โอ", "U": "อู"}
PROFILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vowels.json")
REF_C = np.mean([np.log(f) for f in VOWELS.values()], axis=0)
SHIFT = 0.0         # log ของสเกลเสียงผู้พูดเทียบค่ามาตรฐาน (ใช้เฉพาะตอนไม่มี vowels.json)
ADAPT = 0.0005      # ต่อเฟรม (30 เฟรม/วิ)
VOWEL_GATE = 0.004  # เบากว่านี้ = เงียบ ไม่ต้องเดาสระ
PROFILE, PROFILE_MT, LOGREF = {}, None, {}

def load_profile():
    """โหลด vowels.json ใหม่เมื่อไฟล์เปลี่ยน (ตั้งค่าเสร็จแล้วใช้ได้เลย ไม่ต้องปิดเปิดตัวช่วย)"""
    global PROFILE, PROFILE_MT, LOGREF
    try:
        mt = os.path.getmtime(PROFILE_PATH)
    except OSError:
        mt = None
    if mt == PROFILE_MT and LOGREF:
        return
    PROFILE_MT = mt
    try:
        with open(PROFILE_PATH, encoding="utf-8") as f:
            PROFILE = json.load(f)
        print("ใช้เสียงสระที่ตั้งค่าไว้:", PROFILE)
    except (OSError, ValueError):
        PROFILE = {}
    LOGREF = {v: np.log(PROFILE.get(v, f)) for v, f in VOWELS.items()}

def formants(x, order=14):
    x = np.append(x[0], x[1:] - 0.97 * x[:-1]) * np.hamming(len(x))  # pre-emphasis + window
    r = np.correlate(x, x, "full")[len(x) - 1:len(x) + order]
    if r[0] <= 1e-9:
        return None
    R = r[np.abs(np.subtract.outer(np.arange(order), np.arange(order)))]
    a = np.linalg.solve(R + np.eye(order) * r[0] * 1e-6, r[1:])
    roots = np.roots(np.concatenate(([1.0], -a)))
    roots = roots[roots.imag > 0]
    f = np.angle(roots) * FS / (2 * np.pi)
    bw = -np.log(np.abs(roots)) * FS / np.pi
    f = np.sort(f[(f > 200) & (f < 3500) & (bw < 500)])
    return f if len(f) >= 2 else None

def classify(x):
    global SHIFT
    f = formants(x)
    if f is None:
        return ""
    lf = np.log(f[:2])
    if not PROFILE:
        SHIFT = float(np.clip(SHIFT + (np.mean(lf - REF_C) - SHIFT) * ADAPT, -0.22, 0.22))
    return min(LOGREF, key=lambda v: np.sum((lf - (0 if PROFILE else SHIFT) - LOGREF[v]) ** 2))

def vowel_formants(x):
    """F1/F2 กลาง (median) ของเสียงสระที่ร้องค้าง — ใช้ตอนตั้งค่า; คืน (ค่า หรือ None ถ้าเสียงน้อยไป, จำนวนช่วงที่ใช้ได้)"""
    fs = [f[:2] for i in range(0, len(x) - 640, 160)
          if np.sqrt(np.mean(x[i:i + 640] ** 2)) > VOWEL_GATE and (f := formants(x[i:i + 640])) is not None]
    if len(fs) < 15:
        return None, len(fs)
    return [round(float(v)) for v in np.exp(np.median(np.log(fs), axis=0))], len(fs)

def calibrate(dev):
    """ร้อง อา เอ อี โอ อู ทีละสระ → vowels.json (+ เก็บเสียงไว้ที่ calib/*.wav เผื่อวิเคราะห์ภายหลัง)"""
    import wave
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calib")
    os.makedirs(out, exist_ok=True)
    prof, rec = {}, {}
    print("=== ตั้งค่าเสียงสระ: ร้องแต่ละสระค้างไว้ ด้วยเสียงพูดปกติของตัวเอง (ไม่ต้องตะโกน) ===")
    for v, th in THAI.items():
        input(f"\nกด Enter แล้วร้อง '{th}' ยาว ๆ ...")
        print("  ● กำลังฟัง 3 วินาที", flush=True)
        x = sd.rec(3 * FS, samplerate=FS, channels=1, dtype="float32", device=dev)
        sd.wait()
        rec[v] = x = x[:, 0]
        with wave.open(os.path.join(out, v + ".wav"), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(FS)
            w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
        f, n = vowel_formants(x[FS // 3:])  # ตัดช่วงเริ่มออกเสียง
        if f is None:
            print(f"  !! เสียงเบาหรือสั้นไป (ใช้ได้ {n} ช่วง) — สระนี้ใช้ค่ามาตรฐาน รันใหม่ได้")
        else:
            prof[v] = f
            print(f"  ได้แล้ว F1={f[0]} F2={f[1]} Hz")
    with open(PROFILE_PATH, "w", encoding="utf-8") as fh:
        json.dump(prof, fh)
    load_profile()
    print("\n=== ลองจับสระจากเสียงที่เพิ่งร้อง (ยิ่งใกล้ 100% ยิ่งนิ่ง) ===")
    for v, x in rec.items():
        got = [classify(x[i:i + 640]) for i in range(FS // 3, len(x) - 640, 533)
               if np.sqrt(np.mean(x[i:i + 640] ** 2)) > VOWEL_GATE]
        got = [g for g in got if g]
        miss = ", ".join(f"{THAI[k]} {got.count(k)}" for k in THAI if k != v and got.count(k))
        if got:
            print(f"  {THAI[v]}: ตรง {100 * got.count(v) // len(got)}%" + (f"  (พลาดไปเป็น {miss})" if miss else ""))
    print("\nบันทึกแล้ว:", PROFILE_PATH, "— ตัวช่วยที่เปิดอยู่จะใช้ค่าใหม่เองภายใน 1 วินาที")

VOWEL, HIST = "", []

def update_vowel():
    """โหวตเสียงข้างมาก 4 เฟรมล่าสุด (~130ms) กันรูปปากกระพริบ"""
    global VOWEL
    load_profile()
    HIST.append(classify(BUF[-640:]) if LEVEL > VOWEL_GATE else "")
    del HIST[:-4]
    VOWEL = vote(HIST)

def vote(hist):
    return max(set(hist), key=hist.count)

def selftest():
    """สังเคราะห์สระ (พัลส์เสียง + เรโซแนนซ์ F1/F2/F3) เสียงต่ำ/สูง แล้วเช็คว่าจับสระถูก:  python helper.py --selftest"""
    def synth(f1, f2, f0, n=FS // 2):
        y = np.zeros(n)
        y[::FS // f0] = 1.0
        for fc, bw in ((f1, 80), (f2, 110), (2600, 160)):
            rr = np.exp(-np.pi * bw / FS)
            b1, b2 = 2 * rr * np.cos(2 * np.pi * fc / FS), -rr * rr
            out = np.zeros(n)
            for i in range(n):
                out[i] = y[i] + b1 * out[i - 1] + b2 * out[i - 2]
            y = out
        return (y / np.abs(y).max() * 0.3).astype(np.float32)
    global SHIFT, PROFILE, LOGREF
    win = lambda s, i: s[4000 + i % 50 * 7:4640 + i % 50 * 7]
    bad = []
    for f0, k in ((110, 0.95), (160, 1.05), (220, 1.18)):  # เสียงต่ำ / กลาง / สูง (ฟอร์แมนต์สูงตาม)
        true = {"A": (780, 1300), "E": (480, 1900), "I": (300, 2250), "O": (480, 880), "U": (320, 780)}  # ตามตำรา
        sig = {v: synth(f1 * k, f2 * k, f0) for v, (f1, f2) in true.items()}
        # ไม่ได้ตั้งค่า (ค่ามาตรฐาน + จำสเกลช้า ๆ) — รับประกันแค่เสียงต่ำ/กลาง
        # ตั้งค่าแล้ว (vowels.json จากเสียงตัวเอง) — ต้องถูกทุกเสียง
        modes = [("calibrated", {v: vowel_formants(s)[0] for v, s in sig.items()})]
        if f0 < 200:
            modes.insert(0, ("default", {}))
        for mode, prof in modes:
            PROFILE = prof
            LOGREF = {v: np.log(prof.get(v, f)) for v, f in VOWELS.items()}
            SHIFT = 0.0
            if not prof:
                for i in range(400):  # พูดคละสระสักพัก (~65 วิ) ให้จำสเกลเสียงนี้
                    for s in sig.values():
                        classify(win(s, i))
            got = {v: classify(s[4000:4640]) for v, s in sig.items()}
            print(f"  F0={f0} {mode}: {got}")
            bad += [(f0, mode, v, g) for v, g in got.items() if g != v]
            for v, s in sig.items():  # ร้องค้างสระเดียว 8 วิ (240 เฟรม) ต้องไม่ไหลไปสระอื่น
                s0 = SHIFT
                raw = [classify(win(s, i)) for i in range(240)]
                drift = [g for i in range(4, 240) if (g := vote(raw[i - 4:i])) != v]  # ผลหลังโหวตแบบที่ใช้จริง
                SHIFT = s0
                if drift:
                    bad.append((f0, mode, v, "sustain", len(drift), drift[0]))
    assert not bad, bad
    print("selftest ok")

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
        update_vowel()
        msg_d = {"level": round(LEVEL, 4), "vowel": VOWEL, "mx": mx, "my": my,
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
            print("เสียง: " + "#" * min(40, int(LEVEL * 300)) + "  " + VOWEL)
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
        stream = sd.InputStream(device=dev, channels=1, samplerate=FS,
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
    if "--selftest" in sys.argv:
        selftest()
        sys.exit()
    if "--calibrate" in sys.argv:
        calibrate(int(sys.argv[sys.argv.index("--dev") + 1]) if "--dev" in sys.argv else None)
        sys.exit()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
