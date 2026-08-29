// อวตาร: เสือขาวชุดสูท (จาก rig_car_5) — หัว/ตัวนิ่ง ขยับแค่ หู ตา หาง ปาก
// ถอด/ใส่ชุดสูท: ติ๊ก "ชุดสูท" ในแผง 🧩 ชิ้นส่วน
window.AVATAR_DEF = {
  name: "เสือขาวชุดสูท",
  layers: [
    { part: "หาง", src: "car5_tail.png", pos: [483, 536], origin: [78, 930], motion: "pendulum" },
    { part: "หูซ้าย", src: "car5_ear_L.png", pos: [226, 128], origin: [130, 165], motion: "wiggle" },
    { part: "หูขวา", src: "car5_ear_R.png", pos: [614, 136], origin: [60, 175], motion: "wiggle" },
    { part: "ตัว", src: "car5_base.png" },
    { special: "eyesC", part: "ตาหลับ", src: "car5_eyes_closed.png" },
    { id: "eyesOpen", origin: [512, 506], children: [
      { part: "ตาขาว", src: "car5_eyes_white.png" },
      { special: "pupils", part: "ตาดำ", src: "car5_pupils.png" },
      { part: "ขอบตา", src: "car5_eyes_top.png" },
    ]},
    { special: "mouth" },
    { part: "ผม", src: "car5_hair.png" },
    { part: "ชุดสูท", src: "suit.png" },
  ],
  mouth: { type: "grid", files: [
    ["car5_mouth_1A.png", "car5_mouth_1B.png", "car5_mouth_1C.png"],
    ["car5_mouth_2A.png", "car5_mouth_2B.png", "car5_mouth_2C.png"],
    ["car5_mouth_3A.png", "car5_mouth_3B.png", "car5_mouth_3C.png"],
  ]},
  blink: { style: "swap" },
  pupils: { mask: "car5_eyes_mask.png", range: [11, 5] },
};
