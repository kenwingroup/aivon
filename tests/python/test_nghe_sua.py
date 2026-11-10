"""Sửa chữ nghe nhầm theo ngữ cảnh (nghe_sua.sua) và gợi ý hotwords cho Whisper.

    python tests/run.py nghe_sua

Vì sao file này tồn tại (0.59.24): người dùng nói lẫn Việt - Anh, máy nghe chép "Aivon" thành
"David", "Aivon", "Gia vít"... rồi Aivon trả lời bám nghĩa đen. Lớp này sửa theo ÂM và NGỮ
CẢNH trước khi câu đi vào bộ não. Ranh giới quan trọng: không đổi tên người thứ ba ("nhắn cho
David"), không đổi tên riêng hai chữ ("David Beckham"), không đụng câu không liên quan, và
không sửa gì thì trả y nguyên.
"""
from _paths import ROOT, SERVER  # noqa: E402,F401

import nghe_sua  # noqa: E402

_fails = []


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        _fails.append(name)


TV = ["Aivon"]
S = lambda s, tv=TV: nghe_sua.sua(s, tv)   # noqa: E731

# ---- 1. Khoá âm: những cách máy nghe hay chép "Aivon" phải về cùng một khoá ----
for w in ("Aivon", "David", "Davis", "Aivon", "Gia vít", "Ja vịt", "Đa vít", "aivont"):
    check(f"khoá âm của {w!r} trùng Aivon", nghe_sua.khoa_am(w) == nghe_sua.khoa_am("Aivon"))
check("Java KHÔNG trùng khoá Aivon", nghe_sua.khoa_am("Java") != nghe_sua.khoa_am("Aivon"))

# ---- 2. Gọi tên: sửa ở mọi vị trí khi trùng âm hoàn toàn ----
check("đầu câu: David -> Aivon", S("David mở trang việc giúp anh") == "Aivon mở trang việc giúp anh")
check("hey David", S("hey David, doanh thu hôm nay bao nhiêu") == "hey Aivon, doanh thu hôm nay bao nhiêu")
check("cuối câu: cảm ơn David", S("cảm ơn David") == "cảm ơn Aivon")
check("Aivon -> Aivon", S("Aivon ơi mở lịch") == "Aivon ơi mở lịch")
check("bị tách hai tiếng: Gia vít ơi", S("Gia vít ơi, tóm tắt email") == "Aivon ơi, tóm tắt email")
check("Ja vịt giữa câu (trùng hoàn toàn)", S("hôm nay ja vịt thấy sao") == "hôm nay Aivon thấy sao")
check("Đa vít", S("Đa vít cho anh xem lịch") == "Aivon cho anh xem lịch")
check("sửa nhiều chỗ trong một câu",
      S("David ơi, David nghe rõ không") == "Aivon ơi, Aivon nghe rõ không")
check("giữ nguyên xuống dòng và dấu câu quanh chỗ sửa",
      S("Ok David.\nMở trang cài đặt!") == "Ok Aivon.\nMở trang cài đặt!")

# ---- 3. Trùng vừa phải: CHỈ sửa ở vị trí gọi tên ----
check("Gia vị ơi (gọi tên) -> Aivon", S("Gia vị ơi, mấy giờ rồi") == "Aivon ơi, mấy giờ rồi")
check("cho gia vị vào nồi (giữa câu) giữ nguyên",
      S("cho gia vị vào nồi rồi đun") == "cho gia vị vào nồi rồi đun")
check("Cha vít đầu câu -> Aivon", S("Cha vít, đọc tin mới") == "Aivon, đọc tin mới")

# ---- 4. Không sửa bừa ----
GIU = [
    "nhắn cho David là tôi đến muộn",           # người thứ ba
    "gặp David lúc 3 giờ",
    "David Beckham đá bóng hay",                 # tên riêng hai chữ
    "học Java với anh Nam",                      # Java không phải Aivon
    "đọc file README.md và mở https://github.com/x",
    "doanh thu tháng này bao nhiêu",
    "",
]
for s in GIU:
    check(f"giữ nguyên: {s[:40]!r}", S(s) == s)
check("không có gì sửa thì trả CÙNG đối tượng", S("xin chào") == "xin chào")
check("đã đúng Aivon thì không đổi gì", S("Aivon ơi mở lịch") == "Aivon ơi mở lịch")
check("chạy hai lần ra cùng kết quả (idempotent)",
      S(S("David ơi Gia vít nghe không")) == S("David ơi Gia vít nghe không"))
check("bộ từ vựng rỗng: trả y nguyên", nghe_sua.sua("David ơi", []) == "David ơi")

# ---- 5. Từ vựng người dùng khai: nhiều từ, cụm hai tiếng ----
TV2 = ["Aivon", "OpenRouter", "Pancake"]
check("Open Router (tách) -> OpenRouter",
      S("đổi bộ não sang open router đi", TV2) == "đổi bộ não sang OpenRouter đi")
check("Pan cake -> Pancake", S("xem đơn trên pan cake", TV2) == "xem đơn trên Pancake")
check("Bánh kếp không thành Pancake", S("ăn bánh kếp", TV2) == "ăn bánh kếp")

# ---- 6. Rút bộ từ vựng từ settings + gợi ý cho Whisper ----
cfg = {"voice": {"hotwords": "OpenRouter, Pancake\n aivon ; Zalo,, Pancake"}}
tv = nghe_sua.vocabulary(cfg)
check("Aivon luôn đứng đầu, không nhân đôi dù người dùng gõ 'aivon'", tv[0] == "Aivon" and tv.count("Aivon") == 1
      and not any(t.lower() == "aivon" for t in tv[1:]))
check("tách bằng phẩy, chấm phẩy, xuống dòng; bỏ trùng", tv == ["Aivon", "OpenRouter", "Pancake", "Zalo"])
check("không có cài đặt vẫn có Aivon", nghe_sua.vocabulary({}) == ["Aivon"])
check("gợi ý Whisper là danh sách ngăn phẩy, khép dấu chấm",
      nghe_sua.goi_y_whisper(tv, ky_thuat=()) == "Aivon, OpenRouter, Pancake, Zalo.")
check("gợi ý rỗng khi không có từ", nghe_sua.goi_y_whisper([], ky_thuat=()) == "")

# ---- 7. Mồi thêm từ tiếng Anh hay nói xen (0.64.67: "GitHub Actions" thành "huyết áp Action") ----
gy = nghe_sua.goi_y_whisper(tv)
check("mặc định mồi kèm từ tiếng Anh thông dụng", "GitHub Actions" in gy and "deploy" in gy)
check("từ người dùng khai đứng CUỐI (Whisper chỉ giữ phần cuối prompt)",
      gy.endswith("Aivon, OpenRouter, Pancake, Zalo."))
gy2 = nghe_sua.goi_y_whisper(["Aivon", "github"])
check("không nhân đôi từ người dùng đã khai (không phân biệt hoa thường)",
      [x.strip(" .").lower() for x in gy2.split(",")].count("github") == 1 and gy2.endswith("Aivon, github."))
dai = ["Tu%02d dai dai dai dai" % i for i in range(20)]      # ~460 ký tự, chừa chỗ cho vài từ mồi
gy3 = nghe_sua.goi_y_whisper(dai)
check("quá trần thì bỏ bớt từ mồi chung, giữ nguyên từ người dùng",
      gy3.endswith(", ".join(dai) + ".") and len(gy3) <= nghe_sua.MAX_GOI_Y
      and gy3.startswith("GitHub") and "email" not in gy3)
check("vừa trần thì nằm trong MAX_GOI_Y", len(nghe_sua.goi_y_whisper(tv)) <= nghe_sua.MAX_GOI_Y)
check("từ mồi chung KHÔNG đi vào lớp sửa mờ", "GitHub" not in nghe_sua.vocabulary(cfg))

if _fails:
    print("\nFAIL:", len(_fails), _fails)
    raise SystemExit(1)
print("\nOK - nghe_sua")
