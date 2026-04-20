# Individual Report – Nguyễn Anh Hào

**Student ID:** 2A202600131  
**Group:** C401 – Table E1  
**Repo:** https://github.com/N0VA554/Lab_13_C401_Table_E1  
**Role:** Logging Structure · Request Correlation · Context Enrichment

---

## 1. Phần việc đảm nhận

### 1.1 Khung định danh Request (Correlation ID)

Thiết kế và triển khai `app/middleware.py` để đảm bảo tính nhất quán của dữ liệu quan sát trên toàn bộ hệ thống.

**Các tính năng đã triển khai:**
- **Request ID Generation**: Tự động trích xuất `x-request-id` từ Header hoặc tạo mới theo định dạng `req-<8-char-hex>` nếu thiếu.
- **Context Management**: Sử dụng `structlog.contextvars.clear_contextvars()` ở đầu mỗi request để ngăn chặn rò rỉ dữ liệu log giữa các phiên làm việc khác nhau.
- **Response Headers**: Đính kèm `x-request-id` và `x-response-time-ms` vào Header trả về cho Client để hỗ trợ việc đối chiếu lỗi phía người dùng.

**Kết quả validate:**
- Log file ghi nhận trường `correlation_id` cho 100% các sự kiện.
- Response header trả về chính xác mã định danh request.

---

## 1.2 Làm giàu dữ liệu Log (Log Enrichment)

Cập nhật `app/main.py` để biến các log đơn thuần thành log có tính ngữ cảnh cao, phục vụ cho việc truy vấn chuyên sâu.

**Các thông tin được gắn vào Log:**
- `user_id_hash`: Sử dụng SHA-256 để ẩn danh hóa ID người dùng nhưng vẫn giữ được khả năng thống kê theo user.
- `session_id`: Theo dõi hành trình của một phiên chat cụ thể.
- `feature`: Phân loại log theo tính năng (Refund, Policy, Help...).
- `model`: Ghi nhận model AI đang sử dụng (vd: Claude-Sonnet-4-5).
- `env`: Ghi nhận môi trường thực thi (dev/prod).

```python
# Đoạn mã thực hiện gán ngữ cảnh trong app/main.py
bind_contextvars(
    user_id_hash=hash_user_id(body.user_id),
    session_id=body.session_id,
    feature=body.feature,
    model=agent.model,
    env=os.getenv("APP_ENV", "dev"),
)
```

---

## 2. Kết quả đạt được

| Hạng mục | Trạng thái | Ghi chú |
|---|---|---|
| **Correlation ID Presence** |  Pass | 100% logs mang ID duy nhất |
| **Header Propagation** |  Pass | Header có `x-request-id` |
| **Contextual Fields** |  Pass | Đầy đủ user_hash, feature, model |
| **Log Schema Validation** |  100/100 | Vượt qua script validate_logs.py |

---

## 3. Câu hỏi kỹ thuật có thể được hỏi

**Q: Tại sao phải gọi `clear_contextvars()` ở đầu middleware?**  
A: Vì `structlog` lưu context trong thread-local storage hoặc contextvars. Nếu không dọn dẹp, ID của request trước có thể bị "dính" vào request sau nếu server tái sử dụng thread, dẫn đến sai lệch dữ liệu quan sát.

**Q: Lợi ích của việc đưa `x-request-id` vào Response Header là gì?**  
A: Khi người dùng gặp lỗi, họ có thể chụp mã ID này cho bộ phận hỗ trợ. Kỹ thuật viên chỉ cần tìm kiếm ID này trong hệ thống Logging là có thể thấy toàn bộ dấu vết lỗi từ đầu đến cuối.

**Q: Tại sao Person A là "xương sống" của hệ thống Observability?**  
A: Nếu không có cấu trúc log chuẩn và ID liên kết, các công cụ của Person C (Tracing) và Person D (Alerting) sẽ không có sợi dây liên kết để xâu chuỗi sự kiện, khiến việc tìm nguyên nhân gốc rễ (Root Cause) trở nên bất khả thi.
