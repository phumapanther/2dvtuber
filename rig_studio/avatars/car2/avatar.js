// อวตาร: สาวแมว (จาก rig_car_2)
window.AVATAR_DEF = {
  name: "สาวแมว",
  layers: [
    { part: "หาง", src: "car2_tail.png", pos: [717, 757], w: 307, origin: [100, 740], motion: "pendulum" },
    { part: "ผมหลัง", src: "car2_hair_back.png", origin: [512, 420], motion: "sway", k: 1.15 },
    { part: "คอเสื้อใน", src: "car2_shirt_in.png" },
    { part: "คอ", src: "car2_neck.png" },
    { part: "ตัว", src: "car2_body.png" },
    { id: "head", origin: [512, 720], motion: "head", children: [
      { part: "หน้าข้างซ้าย", src: "car2_side_L.png" },
      { part: "หน้าข้างขวา", src: "car2_side_R.png" },
      { part: "หน้า", src: "car2_face.png" },
      { id: "face", origin: [512, 580], motion: "face", k: 0.85, children: [
        { special: "eyesC", part: "ตาหลับ", src: "car2_eyes_closed.png" },
        { id: "eyesOpen", origin: [512, 590], children: [
          { part: "ตาขาว", src: "car2_eyes_white.png" },
          { special: "pupils", part: "ตาดำ", src: "car2_pupils.png" },
          { part: "ขนตา", src: "car2_eyes_top.png" },
        ]},
        { special: "mouth" },
      ]},
      { part: "หูซ้าย", src: "car2_ear_L.png", pos: [334, 300], w: 130, origin: [65, 135], motion: "wiggle" },
      { part: "หูขวา", src: "car2_ear_R.png", pos: [562, 300], w: 130, origin: [65, 133], motion: "wiggle" },
      { part: "ผมหน้า", src: "car2_bangs.png" },
    ]},
  ],
  mouth: { type: "frames", posLT: [427, 617], closed: "car2_mouth_0.png",
           frames: ["car2_mouth_1.png", "car2_mouth_2.png", "car2_mouth_3.png", "car2_mouth_4.png"] },
  blink: { style: "swap" },
  pupils: { mask: "car2_eyes_mask.png", range: [7, 4] },
};
