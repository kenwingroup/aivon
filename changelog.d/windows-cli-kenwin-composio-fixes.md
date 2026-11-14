---
bump: patch
title: Fix Windows agent tools, Kenwin quotations, and Facebook connection guidance
---
## vi
### Sửa lỗi
- Ưu tiên bản Codex có đủ Code Mode host khi trùng phiên bản; cải thiện nhận diện Claude trên Windows.
- Cập nhật bảng giá và mẫu báo giá Kenwin, thông tin đại lý, ảnh cửa có fix và quy trình thử bot không gửi dữ liệu thật.
- Cải thiện gọi Zalo CLI nội bộ và tránh nhận nhầm tiếng vọng của file báo giá là chủ tiếp quản hội thoại.
- Công cụ Facebook tích hợp phân biệt kho tài khoản riêng với Composio, tránh yêu cầu nối Messenger khi chỉ đăng qua Composio.
- CI tải đúng các commit lịch sử từ kho upstream để chạy đầy đủ kiểm tra rollback trên repo Aivon.
- Sửa lỗi CI có sẵn sau đổi thương hiệu: font PDF đa nền tảng, kiểm tra giao diện hiện tại, snapshot API và bằng chứng lịch sử đúng SHA-256.
### Cải thiện
- Hỗ trợ chuẩn hóa gói và danh mục tương thích, bổ sung tài nguyên Zalo CLI đi kèm và bỏ qua dữ liệu chạy cục bộ trong Git.

## en
### Fixed
- Prefer Codex distributions with the Code Mode host on version ties and improve Claude discovery on Windows.
- Update Kenwin pricing, dealer forms, fixed-panel images, and isolated chatbot quotation trials.
- Improve local Zalo CLI execution and prevent quotation file echoes from triggering owner takeover.
- Distinguish built-in Facebook accounts from Composio instead of requiring Messenger for Composio publishing.
- Fetch pinned historical commits from upstream so rollback checks run on the Aivon repository.
- Repair existing CI failures after rebranding: portable PDF fonts, current UI contracts, API snapshots, and SHA-256 verified historical receipts.
### Improved
- Support compatible pack and catalog normalization, bundle Zalo CLI resources, and exclude local runtime state from Git.
