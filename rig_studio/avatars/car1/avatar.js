// อวตาร: เสือฮู้ด — ริก rev 2 (2026-10-03) จากอาร์ตใน แมว/ (ของเดิมอยู่ เก่า-v6/)
// c1_*.png = ไฟล์ที่ bake_car1.py สร้าง (ห้ามแก้ตรง ๆ) — แก้รูปใน แมว/ แล้วรัน python bake_car1.py
// node แบบ img:   {part:"ชื่อ", src:"ไฟล์", pos:[left,top]?, w:กว้าง?, origin:[x,y]?, motion:"แบบขยับ"?, k:แรง?}
// node แบบกลุ่ม: {id:"ชื่อ", origin:[x,y], motion:"แบบขยับ", children:[...]}
// motion: none | head | face | sway | wiggle | pendulum | bob | float | blush
window.AVATAR_DEF = {
  name: "เสือฮู้ด",
  rev: 2, // เปลี่ยนเลขเมื่อเปลี่ยนชุดรูป → ค่าจัดชิ้นเก่าในเบราว์เซอร์ถูกเก็บเป็นพรีเซ็ท "ก่อนริก rev N" แล้วเริ่มใหม่
  layers: [
    { part: "หาง", src: "c1_tail.png", origin: [540, 1475], motion: "pendulum" },
    { part: "พื้นในฮู้ด", src: "c1_hood_fill.png" },
    { part: "เงาในฮู้ด", src: "v6_jacket_in.png" },
    { part: "ขอบฮู้ดหลัง", src: "c1_hood_in.png" },
    { part: "คอ", src: "c1_neck.png" },
    { id: "head", origin: [478, 880], motion: "head", children: [
      { part: "หน้า", src: "c1_face.png" },
      { id: "face", origin: [494, 514], motion: "face", children: [
        { special: "eyesC", part: "ตาหลับ", src: "c1_eyes_closed.png" },
        { id: "eyesOpen", origin: [494, 514], children: [
          { part: "ตาขาว", src: "c1_eyes_white.png" },
          { special: "pupils", part: "ตาดำ", src: "c1_pupils.png" },
          { part: "ขนตา", src: "c1_lashes.png" },
        ]},
        { part: "คิ้ว", src: "c1_brows.png" }, // นอก eyesOpen — คิ้วไม่ยุบตามตอนกะพริบ
        { part: "จมูก", src: "c1_nose.png" },
        { special: "mouth" },
      ]},
      { part: "ผม", src: "c1_hair.png", origin: [490, 300], motion: "sway" },
    ]},
    { part: "ฮู้ด", src: "v6_jacket_out.png" },
    { part: "ขอบฮู้ดหน้า", src: "c1_hood_out.png" },
    { part: "หูซ้าย", src: "v6_ear_L.png", pos: [204, 152], origin: [87, 192], motion: "wiggle" },
    { part: "หูขวา", src: "v6_ear_R.png", pos: [628, 141], origin: [91, 212], motion: "wiggle" },
  ],
  // ปากตามสระที่ตัวช่วย (helper.py) ฟังได้ — [ปกติ, ตอนพูดดัง]; ไม่มีตัวช่วย = สุ่มสลับทรง
  mouth: { type: "vowel", closed: "c1_mouth_closed.png", vowels: {
    A: ["c1_mouth_A.png", "c1_mouth_A2.png"],
    E: ["c1_mouth_E.png", "c1_mouth_E2.png"],
    I: ["c1_mouth_I.png"],
    O: ["c1_mouth_O.png"],
    U: ["c1_mouth_U.png", "c1_mouth_U2.png"],
  }},
  blink: { style: "squash" },
  pupils: { mask: "c1_eyes_white.png", range: [10, 6] },
};
