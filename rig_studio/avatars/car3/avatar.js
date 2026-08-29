// อวตาร: ต้นไม้ปราชญ์ (จาก rig_car_3) — มีใบไม้ร่วงออโต้
window.AVATAR_DEF = {
  name: "ต้นไม้ปราชญ์",
  layers: [
    { id: "canopyB", origin: [512, 700], motion: "head", k: 1.3, children: [
      { part: "พุ่มใบหลัง", src: "car3_canopy_back.png" },
    ]},
    { part: "ผนังโพรง", src: "car3_hollow_back.png" },
    { id: "headBase", origin: [515, 1085], motion: "face", k: 0.9, children: [
      { part: "หน้า", src: "car3_face.png" },
    ]},
    { part: "ลำต้น", src: "car3_trunk.png" },
    { id: "headFeat", origin: [515, 1085], motion: "face", k: 0.9, children: [
      { id: "eyesOpen", origin: [513, 1058], children: [
        { part: "ตาขาว", src: "car3_eyes_white.png" },
        { special: "pupils", part: "ตาดำ", src: "car3_pupils.png" },
        { part: "ขอบตา", src: "car3_eyes_top.png" },
      ]},
      { special: "mouth" },
    ]},
    { id: "canopyF", origin: [512, 700], motion: "head", k: 1.3, children: [
      { part: "พุ่มใบหน้า", src: "car3_canopy_front.png" },
      { part: "แอปเปิ้ล1", src: "car3_apple_1.png", pos: [68, 621], origin: [58, 6], motion: "pendulum", k: 0.45 },
      { part: "แอปเปิ้ล2", src: "car3_apple_2.png", pos: [320, 592], origin: [36, 6], motion: "pendulum", k: 0.45 },
      { part: "แอปเปิ้ล3", src: "car3_apple_3.png", pos: [573, 511], origin: [45, 6], motion: "pendulum", k: 0.45 },
      { part: "แอปเปิ้ล4", src: "car3_apple_4.png", pos: [708, 766], origin: [45, 6], motion: "pendulum", k: 0.45 },
      { part: "แอปเปิ้ล5", src: "car3_apple_5.png", pos: [814, 753], origin: [59, 6], motion: "pendulum", k: 0.45 },
    ]},
    { special: "leaves" },
  ],
  mouth: { type: "frames", posLT: [430, 1070], closed: "car3_mouth_0.png",
           frames: ["car3_mouth_1.png", "car3_mouth_2.png", "car3_mouth_3.png", "car3_mouth_4.png"] },
  blink: { style: "swap" }, // ไม่มีภาพตาหลับแยก — ซ่อนชุดตาเปิดแล้วเห็นเปลือกตาที่วาดบนหน้า
  pupils: { mask: "car3_eyes_mask.png", range: [6, 3] },
  leaves: { srcs: ["car3_leaf_1.png", "car3_leaf_2.png", "car3_leaf_3.png", "car3_leaf_4.png"] },
};
