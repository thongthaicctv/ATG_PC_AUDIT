ATG PC AUDIT – HƯỚNG DẪN DỮ LIỆU VÀ KHÔI PHỤC ĐĂNG NHẬP

1. Vị trí hiện tại được lưu trong %PROGRAMDATA%\ATG_PC_AUDIT\bootstrap.json.
2. Trong Tổng hợp, mở QUẢN LÝ DỮ LIỆU VÀ SAO LƯU để xem database/config/log/backup.
3. Dùng SAO LƯU NGAY để tạo file .atgbackup đã có checksum và quick_check.
4. Khi chuyển máy, copy hai EXE và file .atgbackup; chọn Khôi phục từ backup trong thiết lập lần đầu.
5. Nếu quên mật khẩu, chạy ATG_PC_AUDIT_RECOVERY.exe bằng quyền Administrator.
6. Tool không thể xem, giải mã hoặc khôi phục mật khẩu cũ; chỉ đặt mật khẩu mới do quản trị tự nhập.
7. Nếu bootstrap bị mất, dùng CHỌN DATABASE và chọn đúng atg_pc_audit_master.db.
8. Log recovery nằm trong thư mục logs của data root.
9. Nếu ổ backup/USB/NAS bị mất, app vẫn chạy; chọn lại thư mục backup trong Tổng hợp.
10. Không đặt database SQLite trực tiếp trên NAS/UNC; dùng ổ nội bộ cho database và NAS cho backup.
