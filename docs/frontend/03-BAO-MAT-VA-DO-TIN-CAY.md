# 03 — Bảo mật & Độ tin cậy

Tài liệu này chia làm hai phần **khác nhau về bản chất**:

- **Phần A — Bảo mật:** rủi ro kỹ thuật khi hệ thống bị lộ ra ngoài localhost.
- **Phần B — Độ tin cậy:** UI đang khẳng định những điều không đúng, và một cổng duyệt con người thực tế **không thể vượt qua** từ bản Next.

> **Mô hình mối đe doạ (threat model) — đọc trước.**
> Đây là công cụ **một người vận hành, chạy trên máy cá nhân**. Đánh giá dưới đây **không** giả định hệ thống đã bị tấn công từ internet. Phần lớn "lỗ hổng" ở Phần A chỉ trở thành lỗ hổng thật khi cổng dịch vụ được mở ra ngoài — ví dụ bind `0.0.0.0`, hoặc deploy frontend Next lên một máy chủ công khai. Nếu bạn giữ nguyên "chỉ localhost", Phần A là **danh sách những gì cần khoá lại trước khi mở**, không phải sự cố đang xảy ra. Phần B thì **đang** xảy ra ngay lúc này, kể cả trên máy cá nhân.

---

# Phần A — Bảo mật

## A1. Backend không có xác thực (đã xác minh)

**Bằng chứng:** tìm `api_key`, `HTTPBearer`, `OAuth2`, `Depends(...auth...)`, `security` trong `src/content_factory/api/` → **không kết quả nào**.

`src/content_factory/api/app.py:72-90` đăng ký **18 router** và không có một `Depends` xác thực nào. Không có `add_middleware` nào được gọi trong toàn bộ `app.py`.

**Hệ quả khi bị lộ:** toàn bộ bề mặt API mở, bao gồm các thao tác có tác dụng phụ thật:
- `POST /media/from-url` — tải nội dung từ URL tuỳ ý (xem A3).
- `POST /ai-editor/edit`, `POST /projects/{id}/external/upload` — ghi tệp lên đĩa.
- Các route render/gọi ffmpeg — tiêu tốn CPU/GPU.
- `GET /audit`, `/cost/*` — đọc lịch sử kiểm toán.
- `GET /tools` + `POST /tools/call` — bề mặt công cụ cho agent (`src/content_factory/agent_tools.py`, hơn 1.200 dòng): nếu lộ ra, đây là cách gọn nhất để điều khiển toàn bộ hệ thống.

Điều này **nhất quán** với thiết kế local-first, nên tài liệu này không coi đó là lỗi. Nó là **giả định chưa được ghi thành ràng buộc kỹ thuật**: hiện không có gì *ngăn* ai đó bind ra `0.0.0.0`.

**Khuyến nghị (rẻ, làm ngay):**
1. Mặc định bind `127.0.0.1` và ghi rõ trong `README.md`/`scripts/dev.sh` rằng mở rộng ra ngoài cần thay đổi có ý thức.
2. Thêm một `Settings` kiểm tra: nếu `host != 127.0.0.1` **và** chưa cấu hình `CF_API_TOKEN` → từ chối khởi động kèm thông báo rõ. Đây là "fail-closed", không phải thêm tính năng xác thực nặng.
3. Khi thật sự cần truy cập từ xa, đặt sau reverse proxy có xác thực (Tailscale/Cloudflare Access/`caddy` + basic auth) thay vì tự viết auth trong FastAPI.

## A2. Không có CORS — và điều đó vô hiệu hoá chính đoạn mã "gọi backend thật"

**Bằng chứng:** tìm `cors` trong toàn bộ `src/` → **không kết quả nào**. `app.py` không gọi `CORSMiddleware`.

Điều này **tốt** cho bảo mật (mặc định CORS chặt) nhưng lại là lời giải thích cho lỗi L5 ở `02`:

`components/media/VideoUrlRecookStudio.tsx:89` gọi `fetch("http://127.0.0.1:8000/media/from-url")` từ origin `localhost:3000`. Đây là **cross-origin** (khác cả cổng lẫn origin). Không có `Access-Control-Allow-Origin`, trình duyệt sẽ **chặn** ở tầng CORS. Thêm nữa cổng `8000` cũng sai (backend mặc định **8080**, `scripts/dev.sh`).

⇒ Đoạn mã duy nhất trong bản Next cố gọi backend thật **không thể thành công vì hai lý do độc lập**, và nó rơi xuống nhánh mô phỏng giả (`dòng 104-118`) mà không báo gì. Người dùng luôn thấy dữ liệu bịa và tưởng đó là kết quả thật.

**Sửa:** dùng `fetchApi` qua proxy `/api` (xem `01`, mục 3.7) — như vậy request cùng origin, không cần CORS, và cổng lấy từ `NEXT_PUBLIC_API_BASE_URL`.

## A3. Bề mặt SSRF tại `/media/from-url` (cần xác minh thêm)

**Bằng chứng:** `src/content_factory/api/routers/media.py:44-53` → `service.media_from_url(payload.url, ...)` → `services/media.py:31-37` → `media.py:346` `download_from_url(url, ...)`.

Hàm tải nội dung từ URL do người gọi cung cấp, có `urlparse` và dùng `yt_dlp`/`urllib.request`. Ở phần đầu hàm **không thấy** allowlist host hay chặn dải địa chỉ nội bộ (`127.0.0.0/8`, `169.254.0.0/16`, `10/8`, `192.168/16`, `::1`).

> **Đánh dấu trung thực:** tôi chỉ đọc được ~25 dòng đầu của `download_from_url`. Cần đọc hết hàm để kết luận. Nếu thật sự không có kiểm tra host, đây là **SSRF cổ điển**: kẻ tấn công có thể khiến máy chủ tải `http://169.254.169.254/...` (metadata endpoint của cloud) hoặc quét dịch vụ nội bộ trong LAN.

**Khuyến nghị:** thêm một hàm `assert_safe_url()` dùng chung — chỉ cho `http`/`https`, phân giải DNS rồi **từ chối** địa chỉ private/loopback/link-local, và chặn redirect tới các dải đó. Đây cũng là cách đúng để giữ tính năng "nạp video từ URL ngoài" mà không mở lỗ.

## A4. Upload không giới hạn kích thước (đã xác minh)

**Bằng chứng:** `src/content_factory/api/routers/external.py:47-49`

```python
content = await file.read()      # ← đọc toàn bộ tệp vào RAM, không có trần
```

Không có giới hạn số byte, không kiểm tra `Content-Length`, không giới hạn theo `asset_type`.

**Đánh giá:** rủi ro DoS ở mức thấp (một người vận hành, localhost), nhưng lại **dễ sửa và nên sửa** vì Media Bin sẽ được dùng để thả cả thư mục render video 4K.

**Ghi nhận điểm đã làm đúng:** `services/growth.py:254` **có** làm sạch tên tệp đúng cách:

```python
clean_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", filename).strip("_") or "file"
file_path = save_dir / f"{uuid.uuid4().hex[:6]}_{clean_name}"
```

Lọc ký tự lạ + tiền tố UUID ⇒ **không có lỗ path traversal** ở đây. Đây là ví dụ tốt để giữ nguyên khi sửa các chỗ khác.

**Sửa:** chặn theo kích thước (ví dụ `MAX_UPLOAD_MB`), kiểm tra magic bytes/đuôi tệp theo `asset_type`, và trả `413` khi vượt trần.

## A5. Phiên bản Next.js — đã vá CVE đã biết, nhưng đã lạc hậu nhiều bản

**Kiểm chứng thực tế:** `frontend/package-lock.json` ghim `next@14.2.35`.

Điều này quan trọng cần nói chính xác, vì dễ kết luận sai:

| CVE | Phiên bản được vá | Trạng thái ở `14.2.35` |
| :--- | :--- | :--- |
| CVE-2025-29927 (middleware auth bypass) | 12.3.5 / 13.5.9 / 14.2.25 / 15.2.3 | **Đã vá** (14.2.35 ≥ 14.2.25) |
| Các advisory công bố sau đó (ví dụ CVE-2025-66478, và các CVE-2026-27978 / CVE-2026-29057 có PoC công khai) | các bản 15.x/16.x | **Chưa xác định — cần kiểm tra** |

⇒ Đừng hoảng vì "Next 14 có CVE". Kết luận đúng là: **bản ghim hiện tại đã vá lỗi nổi tiếng nhất, nhưng Next 14 đã xa bản mới nhất (16.3.x), và không có gì đảm bảo nó nhận được bản vá các advisory mới.** Next.js 14 đã hết chu kỳ hỗ trợ chính.

**Hành động bắt buộc:** chạy `npm audit` trong `frontend/` (tài liệu này **chưa** chạy vì không có `node_modules`) và ghi kết quả vào `docs/KE-HOACH-TONG-THE.md`. Nếu có advisory ảnh hưởng `14.2.35`, việc nâng cấp chuyển từ "nên làm" thành "phải làm".

## A6. Sandbox của iframe xem trước slide — hiện đúng, nhưng dễ bị phá

**Bằng chứng:** `components/media/HtmlSlideDeckStudio.tsx:389-394`

```tsx
<iframe
  title="Slide Preview"
  srcDoc={fullDoc}
  sandbox="allow-scripts"
  className="w-full h-full border-0 pointer-events-auto"
/>
```

Đây là **HTML/CSS do người dùng tự nhập** — bề mặt XSS tiềm năng. Cấu hình hiện tại **đúng**:

- `srcDoc` chứ không phải URL ⇒ nội dung nằm trong tài liệu con.
- Có `allow-scripts` để slide động chạy được, nhưng **cố ý không** có `allow-same-origin` ⇒ iframe nằm ở origin mờ (opaque origin): không đọc được cookie, `localStorage`, DOM của ứng dụng cha.
- Kết hợp `allow-scripts` **+** `allow-same-origin` mới là cấu hình nguy hiểm, vì script có thể gỡ bỏ chính thuộc tính sandbox.

**Lưu ý trung thực:** ngay ở cấu hình hiện tại, script trong slide **vẫn** gửi được request mạng ra ngoài (beacon/fetch) và hiển thị UI giả. Với công cụ một người dùng, rủi ro ở mức thấp; nhưng đừng coi sandbox này là "đã an toàn tuyệt đối".

**Khuyến nghị:**
1. Thêm comment cảnh báo ngay tại dòng đó: *"KHÔNG thêm `allow-same-origin` — sẽ vô hiệu hoá sandbox."*
2. Nếu slide không cần JavaScript, bỏ luôn `allow-scripts`. Nếu cần, cân nhắc thêm `allow-forms=false` (mặc định đã chặn) và một CSP qua `srcDoc` prefix.

**Ghi nhận điểm đã làm đúng:** không có `dangerouslySetInnerHTML` nào trong toàn bộ `frontend/src/` — đây là kỷ luật tốt, nên giữ.

## A7. Không có bí mật nào trong frontend

**Bằng chứng:** tìm `api_key`, `apikey`, `secret`, `bearer`, `authorization` trong `frontend/src/` → chỉ ra các **chuỗi giao diện** (`"Kiểm toán chi phí Token"`, `"THE SECRET"` là text captions), không có giá trị bí mật nào.

Đây là điều **đúng** và quan trọng: mọi khoá nhà cung cấp AI (Anthropic, Gemini, Kling, ElevenLabs) nằm ở backend. Cần giữ nguyên quy tắc: **chỉ biến `NEXT_PUBLIC_*` mới được xuất hiện ở frontend**, và `NEXT_PUBLIC_API_BASE_URL` là biến duy nhất hợp lệ.

---

# Phần B — Độ tin cậy

Đây là phần nghiêm trọng hơn. Toàn bộ giá trị của dự án nằm ở **hai cổng duyệt con người** ("AI scripts never auto-confirm intellectual property rights", `AGENTS.md`). Một cổng duyệt chỉ có giá trị nếu UI **không thể** hiển thị sai trạng thái của nó.

Hiện tại UI có thể — và đang làm vậy.

## B1. `source_rights_confirmed` là boolean chỉ tồn tại ở trình duyệt

**Bằng chứng:**

```
stores/useProjectStore.ts:29-34   confirmSourceRights() → chỉ set state, KHÔNG gọi API
components/script/ScriptStudio.tsx:325,355   onConfirmSourceRights={confirmSourceRights}
components/script/ScriptEditorView.tsx:337-338   checkbox onChange={onConfirmSourceRights}
```

Người dùng tích ô "xác nhận bản quyền nguồn" → chỉ Zustand đổi. **Không có request nào được gửi.**

**Backend thì cưỡng chế thật** — `src/content_factory/services/projects.py:70-73`:

```python
and not project.source_rights_confirmed
...
"source_rights_confirmed must be true before approving the script."
```

⇒ **Bất biến được bảo vệ đúng ở phía server (điểm cộng kiến trúc).** Vấn đề nằm ở client.

## B2. Gate 1 **không thể** vượt qua từ bản Next (lỗi P0)

**Bằng chứng — đây là chuỗi nhân quả đã được xác minh:**

1. `hooks/useScriptEngine.ts:23-28` định nghĩa `updateScriptMutation` → `PUT /projects/{id}/script`, với payload `{ raw_script, source_rights_confirmed? }`. **Đây là đường duy nhất** để nói với server rằng quyền nguồn đã được xác nhận.
2. Tìm toàn bộ `frontend/src` cho `updateScriptMutation` → **chỉ có 2 kết quả, cả hai đều trong chính định nghĩa**: khai báo (dòng 23) và trả về (dòng 39). **Không nơi nào gọi nó.**
3. Không có `onSave` nào trong `ScriptStudio.tsx` hay `ScriptEditorView.tsx`; cũng không có lời gọi `PUT .../script` nào khác trong toàn bộ frontend.
4. `ScriptStudio.tsx:65` giữ kịch bản trong `useState` cục bộ; `handleGenerateFromBrief` (dòng 84-113) chỉ gọi `setScriptText(...)`. **Kịch bản chưa bao giờ được lưu lên server.**

**Hệ quả, theo đúng thứ tự người dùng trải nghiệm:**

| Bước | Người dùng thấy | Thực tế ở server |
| :--- | :--- | :--- |
| Viết/sinh kịch bản | Kịch bản hiện ra đầy đủ | `script.raw_script` vẫn rỗng |
| Tích "xác nhận bản quyền nguồn" | Ô chuyển xanh, badge "Đã xác nhận" | `source_rights_confirmed = false` |
| Bấm "Phê Duyệt Kịch Bản (Pass Gate 1)" | Nút **đã bật** (`ScriptStudio.tsx:478`), bấm được | — |
| Server phản hồi | — | **422/400: "source_rights_confirmed must be true before approving the script."** — và vì L4, lỗi này không được hiển thị |

⇒ **Bước 1 của quy trình 7 bước không thể hoàn thành trên bản Next.** Không có Gate 1 ⇒ theo thiết kế (`state.py`), không có `generating`, không có video, không có Gate 2, không có publish. Toàn bộ chuỗi sau Gate 1 là bất khả thi.

Đây gần như chắc chắn là lý do `page.tsx:76-77` tiêm một dự án giả với `status: "video_review"` và `source_rights_confirmed: true`: để demo được các màn hình *sau* cổng, người ta đã tạo một trạng thái giả thay vì nối dây còn thiếu. Triệu chứng được xử lý, nguyên nhân thì không.

**Sửa (theo thứ tự):**
1. Nối nút "Lưu kịch bản" vào `updateScriptMutation`.
2. Cho `confirmSourceRights` gửi `PUT /projects/{id}/script` với `source_rights_confirmed: true` — **và** đặt lại thành `false` ở mọi đường sửa đổi nội dung kịch bản (server đã làm vậy: `recook.py:289`, `services/agents.py:95`, `services/scripting.py:30`).
3. Bỏ `confirmSourceRights` khỏi store, hoặc giữ nhưng chỉ như bản sao đọc từ server — cổng phải do server sở hữu.
4. Sau đó xoá nhánh demo giả ở `page.tsx:66-80` (lỗi L2).

## B3. Checklist QC hiển thị "pass" cho trạng thái chưa được xác nhận

**Bằng chứng:** `components/export/ExportReviewStudio.tsx:58`

```tsx
{ label: "Bản quyền Nguồn tư liệu (Source Rights)",
  status: currentProject?.source_rights_confirmed ? "pass" : "warning",
  detail: currentProject?.source_rights_confirmed ? "Đã người vận hành xác nhận hợp pháp" : "..." }
```

Dòng này đọc cờ **client** ở B1. Nghĩa là màn hình "Pre-flight QC" trước khi xuất bản có thể in ra dòng chữ **"Đã người vận hành xác nhận hợp pháp"** trong khi server chưa hề nhận được xác nhận nào.

Với một sản phẩm mà luận điểm cốt lõi là chống đạo văn và truy vết bản quyền, việc UI tự khẳng định điều đó dựa trên một biến trong bộ nhớ trình duyệt là rủi ro **danh tiếng/pháp lý**, không chỉ là lỗi hiển thị.

**Sửa:** mọi dòng QC phải lấy từ phản hồi server (project trả về từ API), không từ store cục bộ; và nếu chưa đọc được, hiển thị `unknown` — **không bao giờ** mặc định là `pass`.

## B4. Nhật ký kiểm toán có thể hiển thị mục bịa

Đã nêu ở `02` (L8), nhắc lại ở đây vì đây là vấn đề tin cậy: `components/audit/AuditCostModal.tsx:29`

```tsx
const auditData = auditQuery.data && auditQuery.data.length > 0 ? auditQuery.data : mockAuditLogs;
```

Khi API rỗng (hoặc **lỗi**), màn hình "Provenance Audit Trail" hiển thị 4 bản ghi bịa — bao gồm cả `SOURCE_RIGHTS_CONFIRMED` — kèm mã SHA-256 giả trông rất thật.

**Sửa:** xoá `mockAuditLogs`. Rỗng thì hiển thị "Chưa có bản ghi kiểm toán"; lỗi thì hiển thị lỗi. Một audit trail nói dối thì tệ hơn không có audit trail.

## B5. Tổng hợp mức độ

| Vấn đề | Mức | Loại |
| :--- | :--- | :--- |
| Gate 1 bất khả thi trên bản Next (B2) | **P0** | Chức năng — chặn toàn bộ quy trình |
| `source_rights_confirmed` chỉ ở client (B1) | **P0** | Tin cậy |
| Checklist QC báo "pass" sai (B3) | **P0** | Tin cậy / pháp lý |
| Audit trail hiển thị mục bịa (B4) | **P0** | Tin cậy / tuân thủ |
| `catch` báo thành công (lỗi L3) | **P0** | Tin cậy |
| Không giới hạn kích thước upload (A4) | P2 | Bảo mật |
| SSRF tiềm năng `/media/from-url` (A3) | P1 *nếu lộ ra ngoài* | Bảo mật |
| Không có xác thực (A1) | Chấp nhận được khi localhost | Bảo mật |
| CORS vắng mặt (A2) | Đúng | Bảo mật |
| Sandbox iframe (A6) | Đúng, cần ghi chú | Bảo mật |
| Không có bí mật ở frontend (A7) | Đúng | Bảo mật |

**Nhận xét tổng thể:** nền bảo mật backend **tốt hơn** so với ấn tượng ban đầu — bất biến quyền nguồn được cưỡng chế ở server (`services/projects.py:70-73`), tên tệp được làm sạch đúng, sandbox iframe cấu hình đúng, không có bí mật ở frontend. Vấn đề thật nằm ở **tầng tin cậy của UI**: giao diện tự tạo ra một thực tại song song (dự án giả, quyền nguồn giả, thao tác thành công giả, audit log giả) và mất kết nối với nguồn sự thật duy nhất là server.

Đó cũng là một tin tốt về mặt sửa chữa: **không cần thay đổi kiến trúc backend** để khắc phục — chỉ cần nối UI vào những API đã tồn tại và xoá các đường tắt giả.
