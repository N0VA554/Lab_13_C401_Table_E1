# Individual Report – Nguyễn Đức Mạnh

**Student ID:** 2A202600151  
**Group:** C401 – Table E1  
**Repo:** https://github.com/N0VA554/Lab_13_C401_Table_E1  
**Role:** Security & Privacy · Dashboard UI · Token Limit (per user & per query)

---

## 1. Phần việc đảm nhận

### 1.1 Security & Privacy – PII Scrubber

Thiết kế và triển khai module `app/pii.py` chịu trách nhiệm phát hiện và redact toàn bộ dữ liệu nhạy cảm trước khi ghi log.

**Các loại PII được bảo vệ:**

| Loại | Pattern | Ví dụ | Log ghi lại |
|---|---|---|---|
| Email | `[\w\.-]+@[\w\.-]+\.\w+` | `student@vinuni.edu.vn` | `[REDACTED_EMAIL]` |
| Số điện thoại VN | `(?:\+84\|0)\d{9,10}` | `0987654321` | `[REDACTED_PHONE_VN]` |
| Thẻ tín dụng | `\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}` | `4111 1111 1111 1111` | `[REDACTED_CREDIT_CARD]` |
| Hộ chiếu | `[A-Z]\d{7}` | `C9876543` | `[REDACTED_PASSPORT]` |
| CCCD | `\b\d{12}\b` | `001234567890` | `[REDACTED_CCCD]` |
| Địa chỉ | `\d+\s+Vinhomes Ocean Park` | `123 Vinhomes Ocean Park` | `[REDACTED_ADDRESS_OCEAN_PARK]` |
| Student ID | `(?i:vni)\d{6}` | `vni123456` | `[REDACTED_STUDENT_ID]` |
| User ID | SHA-256 (12 ký tự) | `u01` | `2055254ee30a` |

**Kết quả validate:**
```
Potential PII leaks detected: 0
Estimated Score: 100/100 ✅
```

**Test cases nâng cao** – bổ sung vào `data/sample_queries.jsonl`:
- `u14`: CCCD + số tài khoản ngân hàng Vietcombank + SSN dạng obfuscate
- `u15`: PII lồng trong JSON nested, JWT Bearer token, XML tags
- `u34`: PII viết biến thể – `[dot]`/`[at]`, số cách nhau bằng dấu `-`, base64, URL-encoded, mixed casing

---

### 1.2 Dashboard UI – Giao diện quan sát realtime

Xây dựng `dashboard/index.html` – Single-page dashboard cập nhật tự động mỗi 2 giây, gồm **7 panels**:

| Panel | Loại chart | Mô tả |
|---|---|---|
| Total Traffic | Sparkline | Tổng request + lịch sử |
| Average Quality Score | Sparkline | SLO target 0.85, màu động |
| Error Breakdown | Doughnut | Phân loại lỗi theo type |
| Latency Profile | Line (P50/P95/P99) | Theo dõi tail latency |
| Operation Costs | Area line | Tổng cost + limit indicator |
| Tokens Distribution | Bar | Input vs Output tokens |
| **Token Quota per User** | **Horizontal bar** | Top 10 users, màu xanh/vàng/đỏ theo % quota |

**Token Quota panel** – điểm nổi bật:
- Horizontal bar chart (Chart.js) thay cho table – dễ theo dõi hơn khi nhiều user
- Đường đứt đỏ tại giới hạn quota
- Badge realtime: **Active / Near (>80%) / Blocked**

---

### 1.3 Limit Token per User

**File:** `app/metrics.py`, `app/main.py`

- Giới hạn: **1000 tokens/user** (tính tổng `tokens_in + tokens_out`)
- Tracking: dict `USER_TOKENS[user_id_hash]` – dùng hashed ID, không lưu raw user ID
- Endpoint mới: `GET /metrics/users` trả về quota + usage từng user
- Khi vượt quota: HTTP **429 Too Many Requests**

```python
# Luồng kiểm tra trong main.py
exceeded, used = check_quota(uid_hash)
if exceeded:
    raise HTTPException(429, f"Token quota exceeded ({used} tokens used)")
```

**Test kết quả:**
```
Request 1-5: OK
Request 6:   BLOCKED – Token quota exceeded (1092 tokens used)  ✅
```

---

### 1.4 Limit Cost per Query

**File:** `app/metrics.py`, `app/main.py`

- Giới hạn: **$0.005/query**
- Normal query: ~$0.002 → pass ✅
- Khi bật `cost_spike` incident: ~$0.008 → bị chặn ✅
- Khi vượt giới hạn: HTTP **402 Payment Required** + ghi log `cost_limit_exceeded`
- Metrics tracking: `cost_violations` counter hiển thị trên dashboard

```python
if check_cost(result.cost_usd):
    record_cost_violation()
    raise HTTPException(402, f"Query cost ${result.cost_usd:.6f} exceeds limit $0.005000")
```

---

## 2. Commit Evidence

| Commit | Mô tả |
|---|---|
| [`d2c51f1`](https://github.com/N0VA554/Lab_13_C401_Table_E1/commit/d2c51f1) | feat: add per-user token quota and max cost per query enforcement |
| [`1c998b1`](https://github.com/N0VA554/Lab_13_C401_Table_E1/commit/1c998b1) | chore: Customize SLO targets and alerting rules |
| [`9469033`](https://github.com/N0VA554/Lab_13_C401_Table_E1/commit/9469033) | feat: Implement PII scrubber and update sample queries |

---

## 3. Kết quả đạt được

| Hạng mục | Kết quả |
|---|---|
| PII leaks trong log | **0** (validate_logs 100/100) |
| Token quota enforcement | HTTP 429 khi vượt 1000 tokens |
| Cost per query enforcement | HTTP 402 khi vượt $0.005 |
| Dashboard panels | **7 panels** (yêu cầu tối thiểu 6) |
| Realtime update | Mỗi 2 giây |
| Validate logs score | **100/100** |

---

## 4. Câu hỏi kỹ thuật có thể được hỏi

**Q: Tại sao dùng SHA-256 hash cho user_id thay vì lưu thẳng?**  
A: Hash một chiều – không thể reverse để lấy lại user_id gốc. Hệ thống vẫn theo dõi được quota per user mà không lưu PII trong memory hay logs.

**Q: Tại sao check cost sau khi agent chạy, không phải trước?**  
A: Cost phụ thuộc vào số token output thực tế, chỉ biết sau khi LLM generate xong. Pre-estimate có thể sai; post-check là chuẩn xác hơn và phù hợp với real-world billing.

**Q: Horizontal bar chart có lợi gì so với table?**  
A: So sánh trực quan giữa nhiều user cùng lúc, màu bar thể hiện ngay mức độ nguy hiểm (xanh/vàng/đỏ), không cần đọc từng số – phù hợp cho oncall monitor thời gian dài.
