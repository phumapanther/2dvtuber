// อวตาร: จิบิเสือขาว (จาก rig_car_6) — ปาก 5 เฟรม + แก้มแดงตอนพูด
window.AVATAR_DEF = {
  name: "จิบิเสือขาว",
  layers: [
    { part: "ตัว", src: "chibi_body.png" },
    { id: "head", origin: [512, 1150], motion: "head", children: [
      { part: "หูซ้าย", src: "chibi_ear_L.png", pos: [0, 329], w: 394, origin: [197, 357], motion: "wiggle" },
      { part: "หูขวา", src: "chibi_ear_R.png", pos: [630, 331], w: 394, origin: [197, 365], motion: "wiggle" },
      { part: "หัว", src: "chibi_head.png" },
      { id: "face", origin: [512, 900], motion: "face", children: [
        { special: "eyesC", part: "ตาหลับ", src: "chibi_eyes_closed.png" },
        { id: "eyesOpen", origin: [512, 860], children: [
          { part: "ตาขาว", src: "chibi_eyes_white.png" },
          { special: "pupils", part: "ตาดำ", src: "chibi_pupils.png" },
          { part: "ขอบตา", src: "chibi_eyes_top.png" },
        ]},
        { part: "แก้ม", src: "chibi_cheeks_a.png" },
        { part: "แก้มแดง", src: "chibi_cheeks_b.png", motion: "blush" },
        { special: "mouth" },
      ]},
    ]},
  ],
  mouth: { type: "frames", posLT: [365, 1045], closed: "chibi_mouth_0.png",
           frames: ["chibi_mouth_1.png", "chibi_mouth_2.png", "chibi_mouth_3.png", "chibi_mouth_4.png", "chibi_mouth_5.png"] },
  blink: { style: "swap" },
  pupils: { mask: "chibi_eyes_mask.png", range: [30, 14] },
};
