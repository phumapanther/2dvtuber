// อวตาร: เสือฮู้ด (จาก rig_car_1 v6)
// node แบบ img:   {part:"ชื่อ", src:"ไฟล์", pos:[left,top]?, w:กว้าง?, origin:[x,y]?, motion:"แบบขยับ"?, k:แรง?}
// node แบบกลุ่ม: {id:"ชื่อ", origin:[x,y], motion:"แบบขยับ", children:[...]}
// motion: none | head | face | sway | wiggle | pendulum | bob | float | blush
window.AVATAR_DEF = {
  name: "เสือฮู้ด",
  // Hood_*.png เป็นอาร์ตบนแคนวาสวาด 1476x2085 — วางลงริกด้วยสเกล 0.77: pos [-60, 38] + w 1137
  layers: [
    { part: "เงาในฮู้ด", src: "v6_jacket_in.png" },
    { part: "ขอบฮู้ดหลัง", src: "Hood_in.png", pos: [-60, 38], w: 1137 },
    { part: "คอ", src: "v6_neck.png" },
    { id: "head", origin: [490, 880], motion: "head", children: [
      { part: "หัว", src: "v6_head_base.png" },
      { id: "face", origin: [490, 520], motion: "face", children: [
        { part: "หน้า", src: "v6_face_noeyes.png" },
        { special: "eyesC", part: "ตาหลับ", src: "v6_eyes_closed.png" },
        { id: "eyesOpen", origin: [489, 546], children: [
          { part: "ตาขาว", src: "v6_eyes_white.png" },
          // ตาดำ: คาลิเบรตแยกจากฮู้ด — จุดศูนย์ถ่วงเนื้อตาขาว + ถ่างออกข้างละ 3px (จูนด้วยตา กันเหล่)
          { special: "pupils", part: "ตาดำ", src: "v6_pupils.png", pos: [-54, 46], w: 1123 },
          { part: "คิ้ว+ขนตา", src: "v6_eyes_top.png" },
        ]},
        { special: "mouth" },
      ]},
      { part: "ผม", src: "v6_hair.png", origin: [490, 300], motion: "sway" },
    ]},
    { part: "ฮู้ด", src: "v6_jacket_out.png" },
    { part: "ขอบฮู้ดหน้า", src: "Hood_out.png", pos: [-60, 38], w: 1137 },
    { part: "หูซ้าย", src: "v6_ear_L.png", pos: [204, 152], origin: [87, 192], motion: "wiggle" },
    { part: "หูขวา", src: "v6_ear_R.png", pos: [628, 141], origin: [91, 212], motion: "wiggle" },
  ],
  mouth: { type: "frames", posLT: [386, 695], frames: ["v6_mouth_1.png", "v6_mouth_2.png", "v6_mouth_3.png", "v6_mouth_4.png"] },
  blink: { style: "squash" },
  pupils: { mask: "v6_eyes_white.png", range: [10, 6] },
};
