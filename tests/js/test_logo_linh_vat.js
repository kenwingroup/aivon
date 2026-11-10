/* Kiểm tra logo thương hiệu AIVON, favicon và linh vật mặc định. */
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

check("linh vật mặc định là ROBOT AI", /var MAC_DINH = \{[^}]*shape: "robot"/.test(pet));
check("linh vật mặc định màu NGỌC TRAI", /var MAC_DINH = \{[^}]*palette: "pearl"/.test(pet));
check("nút Đặt lại trả về đúng robot ngọc trai",
  /P\.setCfg\(\{ shape: "robot", palette: "pearl",/.test(read("dashboard/console.js")));
check("logo.svg là SVG thương hiệu AIVON hợp lệ", svg.includes("<svg") && svg.includes("</svg>"));

for (const [ten, px] of [["logo.png", 512], ["icon-512.png", 512], ["icon-192.png", 192], ["favicon.png", 64]]) {
  const b = fs.readFileSync(path.join(ROOT, "dashboard", ten));
  const w = b.readUInt32BE(16), h = b.readUInt32BE(20), kieuMau = b[25];
  check(ten + " là PNG " + px + "x" + px + " có kênh trong suốt", b.toString("latin1", 1, 4) === "PNG" && w === px && h === px && kieuMau === 6,
    w + "x" + h + " kieu " + kieuMau);
}

console.log(fails.length ? "\nFAIL: " + fails.join(", ") : "\nTat ca OK");
process.exit(fails.length ? 1 : 0);
