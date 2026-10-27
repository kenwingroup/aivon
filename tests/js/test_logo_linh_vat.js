/* Logo, favicon và linh vật mặc định theo bộ nhận diện thương hiệu AIVON.

       node tests/js/test_logo_linh_vat.js

   KHÔNG dùng ký tự em dash. */
const fs = require("fs");
const path = require("path");
const ROOT = path.resolve(__dirname, "..", "..");
const read = (p) => fs.readFileSync(path.join(ROOT, p), "utf8");
const fails = [];
function check(name, cond, extra) {
  console.log((cond ? "ok   " : "FAIL ") + name + (cond || extra === undefined ? "" : "  [" + extra + "]"));
  if (!cond) fails.push(name);
}

const pet = read("dashboard/pet.js");
const svg = read("dashboard/logo.svg");

check("linh vật mặc định là NGÔI SAO", /var MAC_DINH = \{[^}]*shape: "star"/.test(pet));
check("linh vật mặc định màu XANH AIVON (thanhthien)", /var MAC_DINH = \{[^}]*palette: "thanhthien"/.test(pet));
check("nút Đặt lại trả về đúng ngôi sao xanh AIVON",
  /P\.setCfg\(\{ shape: "star", palette: "thanhthien",/.test(read("dashboard/console.js")));
check("logo.svg là biểu tượng chữ A của AIVON", /AIVON Official Brand Mark/.test(svg) && /#38bdf8/i.test(svg));

// Các PNG phải là ảnh vuông đúng cỡ (đọc thẳng header PNG, khỏi cần thư viện ảnh).
for (const [ten, px] of [["logo.png", 512], ["icon-512.png", 512], ["icon-192.png", 192], ["favicon.png", 64]]) {
  const b = fs.readFileSync(path.join(ROOT, "dashboard", ten));
  const w = b.readUInt32BE(16), h = b.readUInt32BE(20), kieuMau = b[25];
  check(ten + " là PNG " + px + "x" + px + " có kênh trong suốt", b.toString("latin1", 1, 4) === "PNG" && w === px && h === px && kieuMau === 6,
    w + "x" + h + " kieu " + kieuMau);
}

console.log(fails.length ? "\nFAIL: " + fails.join(", ") : "\nTat ca OK");
process.exit(fails.length ? 1 : 0);
