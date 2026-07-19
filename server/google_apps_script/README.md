# ATG PC AUDIT – Google Apps Script Web App

## Triển khai production

1. Tạo Google Sheet tên `Quản lý máy tính nội bộ` và giữ quyền truy cập ở **Bị hạn chế**. Không bật Publish to web và không chia sẻ Sheet bằng liên kết công khai.
2. Mở Extensions → Apps Script, tạo các file `.gs` theo đúng tên trong thư mục này và dán nội dung tương ứng.
3. Trong Project Settings → Script Properties, thêm `SPREADSHEET_ID` bằng ID của Google Sheet. Không nhập `SERVER_PEPPER`; hàm thiết lập sẽ tự tạo bí mật này.
4. Chạy thủ công `setupProject()` một lần và cấp quyền cho script. Hàm tạo các sheet còn thiếu, header, màu và bộ lọc mà không xóa dữ liệu hiện có.
5. Chạy `validateSheetSchema()` và xác nhận kết quả `SCHEMA_OK`.
6. Deploy → New deployment → Web app. Chọn **Execute as: Me** và **Who has access: Anyone**.
7. Sao chép URL production kết thúc bằng `/exec`; không dùng URL `/dev`.
8. Mở `config/app_config.json` của mini app và điền URL vào `google_sync.web_app_url`, sau đó build lại EXE.

Khi sửa Apps Script, tạo deployment version mới và kiểm tra lại URL production.

## Máy nhân viên gửi dữ liệu

1. Máy nhân viên quét và bấm **CẬP NHẬT CHO QUẢN TRỊ**.
2. Lần đầu, script tự thêm DEVICE_ID vào `THIET_BI` với `role=SUBMIT`, `status=ACTIVE` và ghi audit ngay, không cần quản trị phê duyệt.
3. Các thiết bị `SUBMIT/PENDING` được tạo bởi phiên bản cũ sẽ tự chuyển thành `ACTIVE` ở lần gửi tiếp theo nếu device secret hợp lệ.
4. Dùng `BLOCKED` để khóa tạm thời; dùng `REVOKED` để thu hồi vĩnh viễn. Hai trạng thái này không được tự động mở khóa.

Máy Tổng hợp phải có license `feature_code=AGGREGATE`, `status=ACTIVE` trong `LICENSES`. Thiết bị này được tự đăng ký `role=AGGREGATE`, `status=ACTIVE` sau khi license hợp lệ.

## Script Properties

- `SPREADSHEET_ID`: bắt buộc, nhập thủ công.
- `SERVER_PEPPER`: tạo tự động, không xem hoặc sao chép ra Sheet.
- `API_VERSION`: mặc định `1`.
- `CURRENT_CHANGE_SEQ`: mặc định `0`.
- `MAX_CLOCK_SKEW_SECONDS`: mặc định `300`.
- `DEFAULT_PAGE_SIZE`: mặc định `200`.
- `MAX_PAGE_SIZE`: mặc định `500`.
- `TEST_MODE`: chỉ đặt `TRUE` trên spreadsheet test riêng; không bật trên production.

## Action API

`REGISTER_DEVICE`, `SUBMIT_AUDIT`, `CHECK_SUBMIT_STATUS`, `CHECK_LICENSE`, `SYNC_SUMMARY`, `SYNC_CHANGES`, `GET_AUDIT_DETAIL`, `LIST_CONFLICTS`. `doGet` chỉ cung cấp `HEALTH`.

Không lưu device secret dạng rõ, mật khẩu quản trị, full product key hoặc Google credential trong EXE/Sheet/log.
