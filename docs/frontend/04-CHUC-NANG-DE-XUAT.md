# 04 — Chức năng đề xuất

Danh sách này bổ sung cho danh sách lỗi ở `02`. Ở đây là **những việc nên *thêm***, xếp theo tỉ lệ giá trị/chi phí.

Thang đánh giá: 🔥 tác động cao · ⚙️ chi phí (1 = nhỏ, 3 = lớn).

---

## Nhóm 1 — Biến "xuất video" thành thật

### F1. Xuất video bằng WebCodecs + WebGPU ngay trong trình duyệt 🔥🔥🔥 ⚙️3

**Hiện trạng:** `README.md` quảng cáo "canvas-to-WebM export" ở bản vanilla (`editor.js`), nhưng đó là cách nén qua canvas + MediaRecorder: chỉ WebM, chất lượng thấp, không kiểm soát được bitrate/GOP, và với bản Next thì chưa có gì.

**Đề xuất:** `VideoEncoder`/`AudioEncoder` của **WebCodecs** cho encode phần cứng, ghép khung bằng **WebGPU** (hoặc WebGL2 làm fallback), rồi mux ra MP4/WebM.

Theo tài liệu kỹ thuật 2025–2026, WebCodecs cho lợi thế tốc độ rõ rệt so với ffmpeg.wasm (vốn bị giới hạn CPU, đơn luồng) — hợp lý để thay ffmpeg.wasm cho bước encode; còn WebGPU cho phép ghép lớp và hiệu ứng realtime mà không rời khỏi client.

**Kiến trúc đề xuất — "hai tầng render", đừng chọn một:**

| | Tầng 1 — Preview client | Tầng 2 — Final server |
| :--- | :--- | :--- |
| Công nghệ | WebCodecs + WebGPU | ffmpeg (đã có: `resolve_hardware_encoder()`, NVENC) |
| Mục đích | Phát lại mượt, xuất nhanh để duyệt | Bản render chuẩn để publish |
| Độ trung thực | Xấp xỉ, có thể bỏ bớt hiệu ứng | Tuyệt đối, khớp render plan |
| Thời gian | ~realtime | Theo `reports/` benchmark |

Cả hai tầng **phải** đọc cùng một `GET /projects/{id}/render-plan` (đã có, trả absolute time slots + keyframes + audio layers). Đây là điểm mấu chốt: nếu client tự diễn giải timeline theo cách riêng, preview sẽ lệch bản final và người duyệt Gate 2 sẽ duyệt một thứ khác với thứ được publish.

**Cảnh báo kèm theo:** WebCodecs `VideoEncoder` hiện chạy tốt nhất trên Chromium; Safari/Firefox có độ phủ không đều. Vì vậy phải có **feature detection và thoái lui** về MediaRecorder (chất lượng thấp, vẫn xuất được) — không được để nút Xuất bị vô hiệu trên trình duyệt không hỗ trợ.

---

### F2. Hợp đồng "render plan" có kiểm chứng bằng golden frame 🔥🔥 ⚙️2

**Vấn đề:** khi có hai tầng render ở F1, sai lệch giữa preview và final là **không thể tránh** về mặt kỹ thuật. Không đo được nghĩa là không kiểm soát được.

**Đề xuất:** một quy trình kiểm tra khung hình vàng:
1. Chọn N mốc thời gian cố định trong render plan (ví dụ tại mỗi điểm bắt đầu scene + giữa scene).
2. Client render khung tại các mốc đó → gửi `POST` các PNG (hoặc hash tri giác, ví dụ dHash/aHash).
3. Server render **cùng** khung từ ffmpeg → so sánh bằng ngưỡng sai khác tri giác.
4. Khung nào lệch quá ngưỡng thì ghi vào một báo cáo "fidelity drift".

Lợi ích: biến "preview khác final" từ một lỗi mơ hồ thành một **con số theo dõi được**, và tự động phát hiện khi thêm hiệu ứng mới làm hai tầng tách rời. Đây cũng là thứ duy nhất khiến hai tầng render ở F1 an toàn để tồn tại lâu dài.

---

## Nhóm 2 — Sửa các lời hứa chưa được thực hiện

### F3. Undo/Redo thật bằng command stack 🔥🔥🔥 ⚙️2

**Hiện trạng:** `README.md` liệt kê `Ctrl + Z / Shift+Z — Undo or Redo nondestructive editing operations` trong bảng phím tắt. Trong bản Next **không có ngăn xếp undo nào**. Người dùng bấm Ctrl+Z và không có gì xảy ra (hoặc trình duyệt hoàn tác ô nhập văn bản).

**Đề xuất:** mẫu command + nghịch đảo. Backend đã có sẵn các thao tác thuần, xác định (`split_scene`, `duplicate_scene`, `move_scene`, `merge_scene`, `bulk_update` trong `timeline.py`) — nghĩa là **nửa việc đã xong**: mỗi thao tác là một hàm thuần trên timeline.

```ts
type Command = {
  id: string;
  label: string;                 // "Cắt Scene 3 tại 00:00:12:04"
  apply(t: VideoProject): VideoProject;
  invert(): Command;             // ← đã có hàm nghịch đảo từ server
};
```

Điểm cần chú ý: undo phải gắn với **`revision` do server sở hữu** (xem NLE doc mục 2.2: mọi thay đổi timeline tăng `revision`, client phải gửi revision hiện tại để tránh race). Undo trong bộ nhớ rồi ghi đè mù lên server sẽ phá cơ chế đó.

**Giá trị phụ:** có command stack thì có luôn **lịch sử thao tác** để hiển thị, và mỗi mục là một dòng audit trail có ngữ nghĩa ("Cắt Scene 3 tại ...") thay vì "TIMELINE_COMMAND_APPLIED" chung chung.

### F4. Xử lý xung đột theo `revision` 🔥🔥 ⚙️1

**Hiện trạng:** frontend `PUT /projects/{id}/video-project` không gửi `revision`. Hai tab (hoặc hai người) cùng sửa → thao tác sau âm thầm ghi đè thao tác trước.

**Đề xuất:** gửi `revision` kèm mọi ghi; khi server trả `409`, hiện UI hợp nhất đơn giản: "Timeline đã thay đổi ở nơi khác — [Tải lại] [Ghi đè]". Chi phí thấp vì server đã đếm revision.

### F5. Autosave + phiên bản kịch bản 🔥🔥 ⚙️2

**Hiện trạng:** kịch bản chỉ nằm trong `useState` và (xem lỗi B2) **chưa bao giờ được lưu**. Kiểu `ChatbotMessage` trong `types/script.ts` đã có `diffBefore`, `diffAfter`, `applied`, `canUndo` — tức mô hình dữ liệu cho việc này **đã được thiết kế nhưng chưa dùng**.

**Đề xuất:**
1. Autosave có debounce (2–3 giây) đẩy kịch bản lên `PUT /projects/{id}/script`.
2. Lưu từng bản thành revision; hiện danh sách phiên bản cạnh trình soạn thảo.
3. Hoàn thiện **chế độ xem diff** đã có sẵn kiểu dữ liệu: mỗi thay đổi của chatbot hiển thị trước/sau, có nút "Chấp nhận" / "Hoàn tác".

Đây là tính năng có tỉ lệ giá trị/chi phí tốt nhất trong danh sách, vì cả backend lẫn kiểu dữ liệu đều đã sẵn sàng — chỉ thiếu phần nối.

### F6. Đồng bộ hai chiều Kịch bản ↔ Timeline 🔥🔥🔥 ⚙️2

**Hiện trạng:** `README.md` mục 6 quảng cáo *"Descript Script-Driven Editing: Bi-directional synchronization between script text and timeline scenes; changing script dialogue directly auto-recalculates durations, speech rates, and subtitle cues."* Backend có `scenes.py` (script → editable scenes) và `script_engine.py` (timing). Trong UI bản Next **không có** sự đồng bộ này — sửa kịch bản không hề ảnh hưởng timeline.

**Đề xuất:** khi người dùng sửa một dòng trong `ScriptEditorView`, gọi `script/analyze` để tính lại thời lượng ước tính, rồi cập nhật scene tương ứng; ngược lại, kéo dài một scene trên timeline thì hiển thị cảnh báo nếu tốc độ đọc vượt ngưỡng (backend đã có luật "reading-speed overflow" trong 15 luật validator của `timeline.py`).

Đây là **điểm khác biệt thật** so với CapCut/Premiere: không NLE nào làm được việc này vì chúng không sở hữu kịch bản. Đáng ưu tiên cao.

---

## Nhóm 3 — Tính bền vững của phiên làm việc

### F7. Chịu mất kết nối (offline-first) 🔥🔥 ⚙️2

**Hiện trạng:** đã nêu ở `02` (L7): không có `localStorage`, không persist, F5 là mất hết. Tệ hơn: backend có thể chết giữa chừng khi render ffmpeg, và mọi thao tác đang gõ sẽ mất.

**Đề xuất — ba lớp tăng dần:**
1. **Persist store client** (`zustand/middleware` `persist`) cho `useUIStore`, `usePlayerStore`, `usePhotoStore`, `useVideoFXStore`. Rẻ, làm ngay.
2. **Bản nháp cục bộ** cho kịch bản/brief (10 chiều briefing là rất nhiều công gõ — mất nó là mất niềm tin vào công cụ).
3. **Hàng đợi mutation** (TanStack Query `persistQueryClient` + một hàng đợi ngoại tuyến): thao tác khi mất mạng được xếp lại và gửi khi có kết nối, kèm chỉ báo "3 thay đổi đang chờ đồng bộ".

### F8. Chỉ báo trạng thái backend 🔥 ⚙️1

**Hiện trạng:** không có gì cho biết backend còn sống hay không. Người dùng gõ 10 phút rồi mới phát hiện mọi thao tác đều thất bại (và do lỗi L3, có thể còn được báo là *thành công*).

**Đề xuất:** đã có router health (`src/content_factory/api/routers/health.py`) → một chỉ báo ở góc thanh bên: xanh (đã kết nối, kèm phiên bản + trạng thái GPU), vàng (đang thử lại), đỏ (mất kết nối). Thanh bên hiện đã có pill "AI Harness — Online" nhưng nó **cứng**, luôn hiện "Online" — cần nối vào health thật.

---

## Nhóm 4 — Chất lượng dựng phim (nghiệp vụ)

### F9. Truy vết nguồn gốc trên từng clip (provenance) 🔥🔥🔥 ⚙️2

Đây là đề xuất tôi cho là **khác biệt cạnh tranh mạnh nhất** của dự án.

**Điều đã có:** `audit.py` (SHA-256), `POST /qa/copyright` (fingerprint), `ExternalAssetRecord` (attribution), thư viện media, và một luận điểm sản phẩm cốt lõi về bản quyền.

**Điều còn thiếu:** inspector không cho biết một clip cụ thể đến từ đâu.

**Đề xuất:** trong `PropertiesInspector`, mỗi scene hiển thị một thẻ **"Nguồn gốc"**: model/tool sinh ra (Kling 1.5 / Veo / Midjourney v6.1 / Wikimedia Commons / tải thủ công), giấy phép, tác giả/attribution, hash SHA-256, thời điểm nạp. Cho phép xuất toàn bộ dưới dạng một tệp "provenance manifest" đi kèm video.

Giá trị: biến yêu cầu tuân thủ (vốn phải làm thủ công) thành **sản phẩm xuất được**. Và vì Gate 2 là cổng duyệt cuối, người duyệt nhìn thấy ngay mọi thành phần chưa có nguồn gốc.

### F10. Caption theo từng từ (word-level) cho karaoke 🔥🔥 ⚙️3

**Hiện trạng:** `tts.py` đã dùng Edge-TTS; caption hiện chia theo câu với mốc thời gian thô.

**Đề xuất:** lấy **word boundary** từ engine TTS (Edge-TTS trả về `WordBoundary`), hoặc forced alignment khi cần, để có mốc thời gian từng từ. Từ đó làm caption "highlight theo từ đang nói" — hiệu ứng giữ chân mạnh nhất trên TikTok/Shorts hiện nay. Nếu chính engine TTS tạo ra mốc thời gian thì **không cần** bước alignment riêng — rẻ hơn nhiều so với chạy Whisper.

### F11. Tường thuật bằng waveform + chỉnh sửa theo dạng sóng 🔥 ⚙️2

Nối `GET /projects/{id}/voiceover/{scene_id}` (trả MP3) vào một waveform tương tác, cho phép kéo cắt khoảng lặng. Backend đã có dữ liệu để làm (validator đã phát hiện "dead air") — nên hiển thị luôn các khoảng lặng như vùng có thể bấm để cắt. Vẽ waveform nên dùng canvas, không dùng DOM (xem F13).

---

## Nhóm 5 — Khả năng tiếp cận & vận hành

### F12. Bàn phím là công cụ chính, không phải phụ kiện 🔥🔥 ⚙️2

Trong phần mềm dựng phim chuyên nghiệp, biên tập viên **không dùng chuột** cho các thao tác cốt lõi. Hiện tại `Ctrl+K` được xử lý, nhưng nhiều thao tác then chốt chỉ có thể bấm.

**Vấn đề kèm theo (a11y thực sự):**

| Vấn đề | Bằng chứng | Hệ quả |
| :--- | :--- | :--- |
| `div` gắn `onClick` thay cho `button` | `SidebarWorkflowNav.tsx` — pill "AI Harness" | Không focus được bằng Tab, không kích hoạt bằng Enter/Space, trình đọc màn hình không thấy |
| Nút chỉ có icon, không `aria-label` | nhiều nút trong `SidebarWorkflowNav.tsx` | Trình đọc màn hình đọc là "button" |
| Cỡ chữ 9–10px rất phổ biến | `text-[9px]`, `text-[10px]` xuất hiện hàng trăm lần | Dưới ngưỡng đọc thoải mái; không tôn trọng thiết lập phóng to của người dùng |
| Trạng thái chỉ phân biệt bằng màu | badge Gate 1/Gate 2 dùng `amber`, checklist dùng `emerald`/`amber` | Người mù màu không phân biệt được; cần thêm icon/chữ |
| Không tôn trọng `prefers-reduced-motion` | rất nhiều `animate-pulse`, `animate-ping`; `framer-motion` | Người bị rối loạn tiền đình không tắt được chuyển động |
| `alert()` chặn luồng | `page.tsx:229` | Không kiểm soát được focus |

**Đề xuất:** thêm `eslint-plugin-jsx-a11y`, một hook `useHotkeys` dùng chung (đừng để mỗi component tự gắn `window.addEventListener` như `SidebarWorkflowNav` + `Topbar` đang làm), `aria-live="polite"` cho mọi thông báo trạng thái AI, và một khối CSS `@media (prefers-reduced-motion: reduce)`.

**Lợi ích kép:** làm đúng a11y ở đây **chính là** làm đúng bàn phím chuyên nghiệp. Cùng một công việc.

### F13. Ảo hoá timeline và lưới media 🔥🔥 ⚙️2

**Vấn đề:** timeline render mọi clip thành DOM. Với một documentary 8–12 phút chia thành hàng trăm cảnh × 5 track, số nút DOM sẽ làm sập khả năng cuộn mượt. Waveform và VU meter cũng vậy.

**Đề xuất:**
- Ảo hoá danh sách clip theo viewport cho các track (chỉ render clip giao với khung nhìn).
- Vẽ waveform/đường keyframe/route map SVG bằng **canvas** thay vì DOM.
- Lưới Media Bin ảo hoá theo hàng.
- Chỉ số cần theo dõi: thời gian render frame khi cuộn timeline với 500 clip.

### F14. Đa ngôn ngữ có bảng thuật ngữ 🔥 ⚙️2

**Hiện trạng:** chuỗi tiếng Việt viết cứng khắp nơi, trộn lẫn tiếng Anh ngay trong cùng một câu: `"STEP 01"` / `"Pre-flight Checklist"` / `"100% Unique Verified"` cạnh `"Xây dựng Kịch bản"` / `"Chạy Workflow Nền"`. Dự án còn có mục tiêu phục vụ cả tiếng Việt và tiếng Anh (`target_language: "vi"`, `presets/vietnamese-short.json`).

**Đề xuất:** `next-intl` hoặc một catalog đơn giản (dự án đã có tiền lệ `presets/*.md` người dùng tự sửa được — một tệp `locales/vi.json` + `en.json` cùng tinh thần đó). Kèm **bảng thuật ngữ NLE** để dịch nhất quán: `razor`, `ripple`, `slip`, `keyframe`, `gain`, `ducking` — dịch mỗi nơi một kiểu sẽ khiến người dùng không dạy được phản xạ. Một tệp `docs/GLOSSARY.md` làm nguồn duy nhất.

Kèm theo: một luật lint chặn chuỗi tiếng Việt literal trong JSX (regex ký tự có dấu), buộc mọi chuỗi mới phải vào catalog.

### F15. Command palette đầy đủ (Raycast-style) 🔥🔥 ⚙️1

**Hiện trạng:** `CommandBarModal` (`Ctrl+K`) hiện là một ô nhập một dòng gửi sang `/timeline/command` để dịch ngôn ngữ tự nhiên thành thao tác timeline. Tốt, nhưng nó chỉ có một chức năng.

**Đề xuất:** biến nó thành palette **hai chế độ**:
- **Chế độ lệnh:** mọi hành động trong ứng dụng (chuyển studio, đổi tỉ lệ khung, chạy pre-flight, xuất, tạo dự án, mở inspector, chuyển scene, …) đều đăng ký thành một lệnh có tên; tìm kiếm mờ.
- **Chế độ AI:** nguyên như hiện tại.

Giá trị: cùng một cơ chế phục vụ cả a11y bàn phím (F12) và khả năng khám phá tính năng, và tạo một điểm đăng ký duy nhất để mọi tính năng mới tự động "có mặt" trong palette.

---

## Nhóm 6 — Vận hành

### F16. Cost Guard thành cổng chặn thật 🔥 ⚙️1

`POST /cost/check` đã tồn tại (`useAuditCost.costCheckMutation`). Hiện UI chỉ hiển thị số cứng (`$5.00` / `$0.42`, xem `02`-L8).

**Đề xuất:** trước mỗi thao tác tốn kém (render final, voiceover toàn bộ, gọi model mạnh), gọi `/cost/check` để lấy ước tính và **yêu cầu xác nhận nếu vượt ngân sách**. Kèm đó: bảng chi phí thật theo từng nhà cung cấp, đọc từ audit trail.

### F17. Cảnh báo sử dụng tài nguyên khi render 🔥 ⚙️2

Backend đã có `ResourceGovernor`, `HardwareProfile`, và một thang "admission" cho GPU (xem `docs/COMPUTE-RESOURCES.md`). Nếu UI không biết, người dùng sẽ khởi động ba render cùng lúc rồi tự hỏi vì sao máy đứng.

**Đề xuất:** đọc trạng thái tài nguyên và hiển thị: encoder khả dụng (NVENC qua bản build nào), VRAM/RAM còn trống, các job đang chạy. Vô hiệu hoá nút render khi vượt ngưỡng "overload abort", kèm giải thích.

---

## Bảng ưu tiên tổng hợp

| # | Chức năng | Tác động | Chi phí | Ghi chú |
| :--- | :--- | :--- | :--- | :--- |
| F5 | Autosave + phiên bản kịch bản | 🔥🔥 | 2 | Kiểu dữ liệu đã có sẵn |
| F6 | Đồng bộ Kịch bản ↔ Timeline | 🔥🔥🔥 | 2 | Lợi thế khác biệt, backend đã có |
| F9 | Truy vết nguồn gốc từng clip | 🔥🔥🔥 | 2 | Biến tuân thủ thành sản phẩm xuất được |
| F12 | Bàn phím + a11y | 🔥🔥 | 2 | Yêu cầu chuyên nghiệp, không phải trang trí |
| F1 | WebCodecs/WebGPU export | 🔥🔥🔥 | 3 | Cần F2 đi kèm để an toàn |
| F3 | Undo/Redo | 🔥🔥🔥 | 2 | README đã hứa |
| F4 | Xử lý xung đột `revision` | 🔥🔥 | 1 | Server đã đếm revision |
| F7 | Chịu mất kết nối | 🔥🔥 | 2 | Làm lớp 1 trước, rất rẻ |
| F15 | Command palette đầy đủ | 🔥🔥 | 1 | Nền tảng đã có |
| F2 | Golden frame fidelity | 🔥🔥 | 2 | Điều kiện để F1 tồn tại lâu dài |
| F8 | Chỉ báo trạng thái backend | 🔥 | 1 | Router health đã có |
| F13 | Ảo hoá timeline/media | 🔥🔥 | 2 | Cần khi cảnh tăng lên hàng trăm |
| F10 | Caption từng từ | 🔥🔥 | 3 | Edge-TTS trả word boundary |
| F14 | i18n + bảng thuật ngữ | 🔥 | 2 | Làm trước khi chuỗi tăng thêm |
| F16/F17 | Cost Guard & tài nguyên thành cổng chặn | 🔥 | 1–2 | Backend đã có |
| F11 | Waveform tường thuật | 🔥 | 2 | |

**Thứ tự đề xuất thực hiện:** F5 → F6 → F9 → F12 → F3 (đều chi phí 2, giá trị cao, dùng hạ tầng đã có) → rồi mới tới F1+F2 (đầu tư lớn).

**Nguyên tắc chung rút ra từ danh sách này:** gần như mọi đề xuất ở đây đều **nối vào những gì backend đã có** (`render-plan`, `revision`, `analyze`, `cost/check`, `health`, `audit`, word boundary của Edge-TTS). Đây là dấu hiệu tốt: backend đã đi trước, và giá trị lớn nhất nằm ở việc **nối dây đúng**, không phải xây thêm.
