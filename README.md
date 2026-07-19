# ATG PC AUDIT

## Phase 11 – Đồng bộ Google Apps Script

Ứng dụng gửi một payload JSON qua HTTPS tới Google Apps Script Web App, có DEVICE_ID, device secret bảo vệ bằng Windows DPAPI, request chống phát lại, SHA-256 dữ liệu, queue ngoại tuyến và đồng bộ gia tăng `change_seq` về SQLite. CSV vẫn là phương án dự phòng.

Hướng dẫn triển khai server nằm tại `server/google_apps_script/README.md`. URL production `/exec` được cấu hình trong `config/app_config.json` tại `google_sync.web_app_url`; không lưu Google credential hoặc device secret trong file cấu hình.

Ứng dụng sử dụng bộ nhận diện trong `assets/logo.png`; icon cửa sổ và file EXE nằm tại `assets/app.ico`. Script `build_exe.bat` tự nhúng icon, logo, cấu hình và metadata phiên bản Windows vào bản onefile.

Ứng dụng Windows nội bộ để thu thập thông tin máy tính trước khi cài lại hệ điều hành và phục vụ quy hoạch IP. Bản hiện tại hoàn thành **Phase 1 đến Phase 7** theo tài liệu yêu cầu.

## Phase 7 - License tính năng Tổng hợp

Chỉ tab **Tổng hợp** yêu cầu license; quét máy và xuất CSV gửi quản trị vẫn hoạt động độc lập. DEVICE_ID được tạo ổn định bằng SHA-256 từ UUID, BIOS Serial, Mainboard Serial và ProcessorId, không phụ thuộc IP, MAC hay Computer Name. License được đọc từ `license.api_url` duy nhất trong `config/app_config.json`; cache ngoại tuyến được mã hóa bằng Windows DPAPI và có hiệu lực tối đa 30 ngày.

Khi ứng dụng khởi động, việc kiểm tra license chạy ẩn trên worker thread. Nếu có Internet, ứng dụng ưu tiên dữ liệu mới nhất từ Google Sheet và cập nhật cache DPAPI. Nếu không kết nối được Internet, ứng dụng tự tải cache còn hạn để mở tính năng Tổng hợp; giao diện ghi rõ nguồn `Google Sheet` hoặc `cache ngoại tuyến`.

Google Sheet cần trang `Sheet1` với các cột: `device_id`, `product_code`, `feature_code`, `company`, `license_name`, `status`, `expire_date`, `max_import_records`, `created_at`, `updated_at`, `note`.

Quy trình cấp quyền: người dùng sao chép DEVICE_ID trong tab Tổng hợp; quản trị thêm một dòng có `product_code=ATG_PC_AUDIT`, `feature_code=AGGREGATE`, `status=ACTIVE`, ngày hết hạn dạng `yyyy-MM-dd` hoặc `PERMANENT`; sau đó người dùng bấm **KIỂM TRA KÍCH HOẠT**. Để khóa dùng `BLOCKED` hoặc `REVOKED`; để gia hạn sửa `expire_date`.

## Chức năng Phase 1

- Giao diện PyQt5 tiếng Việt, mặc định 1200 x 720; có thể thu nhỏ đến 960 x 640 và dùng thanh cuộn để thao tác trên màn hình nhỏ.
- Nhập mã tài sản, người sử dụng, phòng ban, vị trí, người kiểm tra, ngày và ghi chú.
- Nhận biết quyền Administrator; có thể khởi động lại bằng `ShellExecuteW(..., "runas", ...)` hoặc tiếp tục chế độ giới hạn.
- Quét nền bằng `QThread`, không khóa giao diện.
- Thu thập thông tin máy, CPU, từng thanh RAM và Windows bằng WMI/Registry/psutil; không dùng `wmic.exe`.
- Mỗi nhóm thu thập tự bắt lỗi để nhóm khác vẫn tiếp tục.

Phase 7 (kiểm thử đóng gói và nghiệm thu cuối) chưa được tính là đã triển khai.

## Chức năng Phase 2

- Thu thập BIOS, mainboard, từng ổ vật lý, loại bus/media, MBR/GPT và dung lượng.
- Đọc Firmware Mode, TPM Present/Enabled/Ready/Spec Version và Secure Boot.
- Đánh giá riêng từng điều kiện Windows 11 với trạng thái Đạt, Không đạt hoặc Chưa xác định.
- Không kết luận máy đạt nếu CPU chưa được xác nhận trong `config/supported_cpu_windows11.json`.
- Sinh khuyến nghị cho RAM dưới 8 GB, ổ HDD, ổ C dưới 30 GB, TPM/Secure Boot chưa bật và máy không đạt.
- Không thay đổi BIOS, TPM, Secure Boot, phân vùng hoặc cấu hình hệ thống.

## Chức năng Phase 3

- Thu thập tên card, loại, trạng thái, tốc độ, MAC, IPv4/IPv6, subnet, gateway, DNS, DHCP, interface index, hãng và driver.
- Phân biệt Ethernet/Wi-Fi vật lý với Bluetooth, VPN, VMware, VirtualBox, Hyper-V, WSL, loopback và tunnel.
- Tự chọn MAC chính từ card vật lý đang kết nối, có IPv4 và gateway; ưu tiên Ethernet trước Wi-Fi.
- Cho phép người dùng chọn lại card mạng chính bằng combobox.
- Nhập VLAN, IP/Prefix/Gateway/DNS dự kiến, switch, cổng switch và ổ cắm mạng.
- Kiểm tra IP/Gateway đúng định dạng và cùng subnet.
- Chỉ ghi nhận kế hoạch; ứng dụng không chạy lệnh thay đổi IP.

## Chức năng Phase 4 và 5 – Bản quyền

- Đọc trạng thái Windows từ WMI `SoftwareLicensingProduct` và `SoftwareLicensingService`.
- Phân loại Retail, OEM_DM, OEM_COA, Volume MAK, KMS Client/Host và Evaluation.
- Chỉ giữ 5 ký tự cuối; không hiển thị, log hoặc lưu full product key.
- Phát hiện Office MSI/Click-to-Run ở cả Registry 32-bit và 64-bit, bao gồm Microsoft 365, Visio và Project.
- Office Volume/perpetual chỉ chạy `OSPP.VBS /dstatusall`; Microsoft 365 chỉ chạy `vnextdiag.ps1 -action list`.
- Không chạy lệnh kích hoạt, nhập/xóa key, rearm hoặc xóa token.
- Email/Tenant Microsoft 365 chỉ hiển thị cục bộ và mặc định không xuất file.

## Chức năng Phase 6 – Xuất và tổng hợp

- Máy nhân viên xuất một CSV UTF-8 BOM gồm một dòng dữ liệu, có `schema_version`, `audit_id`, `export_id` và SHA-256.
- CSV chống Formula Injection, không chứa full key, email Microsoft 365, Tenant ID hoặc token.
- Có thể tự động xuất CSV sau khi quét; thư mục mặc định là `KetQuaThuThap` cạnh ứng dụng hoặc Documents khi không có quyền ghi.
- Menu Tổng hợp được bảo vệ bằng mật khẩu PBKDF2-SHA256 300.000 vòng, khóa sau 5 lần sai và session 15 phút.
- Import một file, nhiều file hoặc cả thư mục; luôn xem trước và kiểm tra schema/hash/JSON/MAC/IP trước khi ghi.
- SQLite lưu máy, lịch sử kiểm tra, RAM, ổ đĩa, mạng, bản quyền và nhật ký import; bản mới nhất trở thành trạng thái hiện tại.
- Phát hiện xung đột mã tài sản, Serial, UUID, MAC vật lý và IP dự kiến.
- Báo cáo toàn công ty `.xlsx` có 12 sheet, Times New Roman 13, filter, freeze panes và màu trạng thái.
- Hỗ trợ sao lưu ZIP và khôi phục database; file xác thực mật khẩu không nằm trong backup dữ liệu.

### Thiết lập quản trị lần đầu

1. Mở tab **Tổng hợp**.
2. Chọn **THIẾT LẬP MẬT KHẨU LẦN ĐẦU**.
3. Nhập mật khẩu tối thiểu 8 ký tự, có chữ và số.
4. Sau khi lưu, đăng nhập để mở chức năng quản trị.

### Quy trình nhân viên và quản trị

Nhân viên nhập hồ sơ, quét máy, mở tab **Xuất dữ liệu** và chọn **XUẤT CSV GỬI QUẢN TRỊ**. Quản trị viên đăng nhập tab **Tổng hợp**, chọn CSV, bấm **XEM TRƯỚC**, sau đó **XÁC NHẬN IMPORT**. Dùng **XUẤT BÁO CÁO EXCEL** để tạo báo cáo toàn công ty.

## Cài đặt và chạy

Yêu cầu đúng Python 3.10.11 64-bit:

```powershell
cd "D:\PYTHON\ATG PC AUDIT\atg_pc_audit"
C:\Python310\python.exe -m pip install -r requirements.txt
C:\Python310\python.exe main.py
```

Ứng dụng vẫn mở nếu người dùng từ chối UAC; một số dữ liệu có thể không đọc được.

## Kiểm thử Phase 1

```powershell
cd "D:\PYTHON\ATG PC AUDIT\atg_pc_audit"
C:\Python310\python.exe -m unittest discover -s tests -v
```

Checklist thủ công:

1. Mở không có quyền quản trị, kiểm tra banner vàng và nút xin quyền.
2. Từ chối UAC, kiểm tra ứng dụng tiếp tục hoạt động.
3. Bấm **QUÉT MÁY TÍNH**, kiểm tra UI không treo và tiến trình cập nhật.
4. Kiểm tra tab Tổng quan, Phần cứng, Windows có dữ liệu máy hiện tại.
5. Bấm **QUÉT LẠI**, kiểm tra dữ liệu được làm mới.
6. Thử trên máy thiếu quyền WMI; ứng dụng phải hoàn tất các phần còn lại và không hiện traceback.
7. Kiểm tra bảng Windows 11 hiển thị đủ giá trị thực tế, yêu cầu, trạng thái và ghi chú.
8. Kiểm tra TPM 1.2, Legacy BIOS hoặc Secure Boot tắt phải không được kết luận đạt.
9. Kiểm tra card VMware/VPN không được chọn làm MAC chính.
10. Sao chép IP hiện tại sang kế hoạch, sau đó kiểm tra IP và Gateway cùng subnet.

## Build EXE

```powershell
cd "D:\PYTHON\ATG PC AUDIT\atg_pc_audit"
C:\Python310\python.exe -m pip install pyinstaller
.\build_exe.bat
```

Kết quả: `dist\ATG_PC_AUDIT.exe`.

## Phase 8 - Gửi dữ liệu cho quản trị

Nút **GỬI DỮ LIỆU QUẢN TRỊ** cung cấp ba phương thức: lưu bản sao CSV, chuẩn bị gửi qua Zalo Desktop hoặc mở Gmail trong trình duyệt mặc định. Ứng dụng tự tạo CSV khi cần, chuẩn hóa số điện thoại Việt Nam, kiểm tra email cơ bản, chọn sẵn file trong Explorer và lưu lịch sử chuẩn bị gửi cục bộ. Ứng dụng không tự chọn người nhận khi không chắc chắn, không tự đính kèm trên Gmail Web và tuyệt đối không tự bấm Gửi.
