# Phase 12 - Báo cáo lưu trữ hiện tại

## Database

- Tên thực tế: `atg_pc_audit_master.db`.
- Đường dẫn mặc định hiện tại: `%PROGRAMDATA%\ATG_PC_AUDIT\data\atg_pc_audit_master.db`.
- Fallback: `%LOCALAPPDATA%\ATG_PC_AUDIT\data\atg_pc_audit_master.db`.
- Máy kiểm tra hiện có database tại `C:\ProgramData\ATG_PC_AUDIT\data\atg_pc_audit_master.db`.
- SQLite dùng WAL, `foreign_keys=ON`, `synchronous=NORMAL`.

## Config và resource

- Config nguồn hiện tại: `config/app_config.json` cạnh source; khi build onefile nằm trong `sys._MEIPASS`.
- Một số thao tác đang cố ghi trực tiếp vào resource config. Trong EXE onefile, thay đổi có thể mất sau khi thoát.
- Asset và CPU support list là resource chỉ đọc trong source hoặc `_MEIPASS`.

## Log

- Hiện tại: `%USERPROFILE%\ATG_PC_AUDIT\logs\atg_pc_audit.log`.
- Chưa thống nhất cùng data root/database.

## Xác thực Tổng hợp

- Project không có bảng `users` trong SQLite.
- Mật khẩu quản trị được lưu trong `%PROGRAMDATA%\ATG_PC_AUDIT\security\admin_auth.json`, fallback `%LOCALAPPDATA%`.
- Các trường: `version`, `algorithm`, `iterations`, `salt_base64`, `password_hash_base64`, `created_at`, `updated_at`.
- Hash hiện tại: PBKDF2-HMAC-SHA256, salt 32 byte, 300.000 vòng; so sánh bằng `hmac.compare_digest`.
- Session chỉ nằm trong bộ nhớ của tiến trình, không có token session lưu lâu dài.

## Nguy cơ trước Phase 12

- Config người dùng có thể nằm trong `_MEIPASS` và không bền vững.
- Backup cũ sao chép file `.db` trực tiếp vào ZIP, không dùng SQLite Backup API nên không bảo đảm nhất quán khi WAL đang hoạt động.
- Không có bootstrap cố định để xác định database/config khi chuyển máy.
- Restore cũ chưa có SHA-256, `quick_check`, kiểm tra schema hoặc khôi phục config.
- Database và log dùng các nguồn đường dẫn khác nhau.

## Debug và EXE

- Debug: resource từ thư mục project; dữ liệu ghi được ưu tiên ProgramData.
- EXE: resource giải nén tạm vào `_MEIPASS`; database vẫn ở ProgramData nhờ `_writable_path`.
- Phase 12 phải giữ database cũ, không tự tạo database trắng khi đường dẫn đã cấu hình bị mất.
