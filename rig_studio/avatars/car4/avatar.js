// อวตาร: เสือขาว (จาก rig_car_4) — ปาก 3 ระดับเสียง x 3 สระ
window.AVATAR_DEF = {
  name: "เสือขาว",
  layers: [
    { part: "ตัว", src: "car4_body.png" },
    { part: "หาง", src: "car4_tail.png", pos: [482, 450], origin: [78, 950], motion: "pendulum" },
    { id: "head", origin: [484, 900], motion: "head", children: [
      { part: "หูซ้าย", src: "car4_ear_L.png", pos: [207, 136], origin: [130, 165], motion: "wiggle" },
      { part: "หูขวา", src: "car4_ear_R.png", pos: [584, 145], origin: [60, 175], motion: "wiggle" },
      { part: "หน้า", src: "car4_face.png" },
      { id: "face", origin: [484, 560], motion: "face", children: [
        { special: "eyesC", part: "ตาหลับ", src: "car4_eyes_closed.png" },
        { id: "eyesOpen", origin: [484, 512], children: [
          { part: "ตาขาว", src: "car4_eyes_white.png" },
          { special: "pupils", part: "ตาดำ", src: "car4_pupils.png" },
          { part: "ขอบตา", src: "car4_eyes_top.png" },
        ]},
        { special: "mouth" },
      ]},
      { part: "ผม", src: "car4_hair.png" },
    ]},
    { part: "เสื้อ", src: "car4_shirt.png" },
  ],
  mouth: { type: "grid", files: [
    ["car4_mouth_1A.png", "car4_mouth_1B.png", "car4_mouth_1C.png"],
    ["car4_mouth_2A.png", "car4_mouth_2B.png", "car4_mouth_2C.png"],
    ["car4_mouth_3A.png", "car4_mouth_3B.png", "car4_mouth_3C.png"],
  ]},
  blink: { style: "swap" },
  pupils: { mask: "car4_eyes_mask.png", range: [10, 5] },
};
