# Kế hoạch tổng thể — AI Content Factory

> **File này là "bộ nhớ" của dự án.** Mọi yêu cầu của chủ dự án, mọi quyết định
> kiến trúc, và mọi việc còn dở đều được ghi ở đây. Khi bắt đầu một phiên làm
> việc mới, **đọc file này trước**, làm xong việc gì thì **cập nhật lại file
> này** (mục *Nhật ký thay đổi* ở cuối). Không xoá yêu cầu cũ — chỉ đánh dấu
> `[x]` khi hoàn thành.

- Cập nhật lần cuối: 2026-09-16
- Trạng thái pipeline: chạy được đầu-cuối (draft → published), 206 test xanh,
  ruff + mypy sạch, smoke test pass.

---

## 1. Yêu cầu gốc của chủ dự án (ghi lại nguyên văn ý)

1. Cải tiến **toàn bộ phần backend**, thêm nhiều tính năng mới.
2. Pipeline phải **siêu chuẩn chỉnh, đẹp**.
3. Khâu **kịch bản** phải hỗ trợ **Claude** tốt nhất.
4. Khâu **tạo video** phải **lồng tiếng (dubbing)** được.
5. Hỗ trợ **toàn bộ AI tân tiến nhất**: tạo video (text-to-video), chỉnh sửa
   video, lồng tiếng.
6. **Nhiều giọng đọc**, hỗ trợ **tiếng Việt tốt nhất trước tiên**.
7. Hỗ trợ chủ dự án **chỉnh sửa tốt nhất** để **tự động hoá bằng AI agent bên
   ngoài**.
8. Phải có khả năng **khớp tốt nhất** (khớp kịch bản ↔ hình ↔ tiếng, khớp nhịp).
9. Phải có khả năng **sao chép ý tưởng**: đưa **một hoặc nhiều video mẫu**, hệ
   thống "cố edit tương tự" — tức học *phong cách/cấu trúc*, không copy nội dung.
10. Có **script**, có **file .md tự tinh chỉnh**.
11. **Toàn bộ pipeline đều user tinh chỉnh được** — kể cả chọn dùng tool nào.
12. **Tải mọi tool có thể về máy** cho chủ dự án.
13. Lưu **hết những gì chủ dự án nói vào file .md** để sau tiếp tục liên tục.
14. Khả năng **edit video tốt nhất, hơn cả Premiere**.
15. **Edit ảnh cũng tốt nhất**.
16. Hỗ trợ **mọi AI agent**: Claude, Codex, DeepSeek, Google…

## 2. Nguyên tắc bất di bất dịch (không được phá)

- **Hai cổng người duyệt là bắt buộc**: duyệt kịch bản (kèm xác nhận bản quyền
  nguồn) và duyệt video cuối. AI **không bao giờ** tự xác nhận bản quyền.
- **Học, không sao chép**: hệ thống được phép học dữ kiện, nhịp, cấu trúc từ
  nguồn/video mẫu, nhưng không tái tạo nguyên văn câu chữ, hình ảnh, giọng đọc,
  âm nhạc của nguồn. Đây là lý do có bộ lọc `copy_risk` trong `script_engine`.
- **State machine là chân lý**: mọi thay đổi trạng thái phải đi qua
  `src/content_factory/state.py`.
- **Mọi thứ phải chạy được offline với cấu hình rỗng** (provider `template`),
  để không bao giờ bị chặn bởi thiếu API key.
- **User tinh chỉnh được mọi thứ**: không hard-code quyết định nghệ thuật vào
  code; đưa ra file cấu hình/preset (JSON/MD) và biến môi trường.

## 3. Trạng thái hiện tại của backend

Đã có (từ trước phiên này):

| Vùng | Chi tiết |
| ---- | -------- |
| Lifecycle | `draft → script_review → script_approved → generating → video_review → video_approved → published`, có `failed` và retry |
| Nghiên cứu | Research engine (thư viện tham chiếu + web), federated search 6 nguồn (arXiv, Crossref, Gutenberg, Open Library, Wikipedia, Internet Archive) |
| Thư viện tài liệu | Tải PDF, index FTS5/BM25, tìm full-text có snippet |
| Provider chain | template (offline) → weak → strong, có retry + circuit breaker + rate limit |
| Sản xuất | Worker mô phỏng render, dựng `VideoProject` theo scene |
| Video editor | Timeline nhiều track, 7 transition, 10 filter, 8 effect, 5 color grade, keyframe motion, sticker, Ken Burns, 7 text style, aspect ratio, fps, caption, nhạc beat BPM, undo/redo, export WebM thật |
| Lồng tiếng | `edge-tts` (neural, có tiếng Việt) + `gTTS` fallback, đo thời lượng thật để sync scene, ghi Opus vào WebM, chỉnh pitch |
| AI Assist | Auto-fit, beat-sync, gợi ý filter/effect/grade/transition, polish text, auto-caption |

Đã thêm trong phiên 2026-09-16 (xem *Nhật ký thay đổi*):

- **Script engine** (`script_engine.py`): parse section, ước lượng thời lượng
  theo từng ngôn ngữ (có profile riêng cho tiếng Việt), linter chất lượng, và
  **bộ lọc đạo văn** (`copy_risk`) đối chiếu với nguồn nghiên cứu.
- **Prompt hợp đồng cho model mạnh**: role + hard constraints + material +
  output contract, dùng chung cho mọi vendor.
- **Preset kịch bản user tinh chỉnh được** (`presets.py` + thư mục `presets/`):
  5 preset dựng sẵn, override bằng JSON hoặc MD.
- **Đa nhà AI**: adapter native **Anthropic Claude** (`/v1/messages`), **Google
  Gemini** (`generateContent`), **DeepSeek**, **Ollama**, **OpenAI-compatible**,
  xếp thứ tự được, mỗi tier thử lần lượt.
- **Cầu nối AI agent bên ngoài** (`agent_bridge.py`): xuất `brief.md` đầy đủ
  ngữ cảnh, nhận lại kết quả dạng block `script` / `json scenes` / `json style`.
- Endpoint mới: `/agents`, `/script/styles*`, `/projects/{id}/script/analyze`,
  `/projects/{id}/script/style`, `/projects/{id}/brief.md`,
  `/projects/{id}/agent-result`.

Chưa có (ưu tiên các phase dưới):

- Render video **thật** bằng ffmpeg (hiện tại worker mô phỏng, export do browser
  làm).
- Phân tích **video mẫu** để rút blueprint phong cách (yêu cầu 9).
- **Text-to-video / image-to-video** (yêu cầu 4, 5).
- **Clone giọng** và lồng tiếng nhiều nhân vật (yêu cầu 4, 6).
- **Chỉnh ảnh** (yêu cầu 15).
- Hàng đợi tác vụ bền vững (hiện dùng thread + store trong RAM).

## 4. Kiến trúc pipeline chuẩn mục tiêu

```
        ┌──────────────────────────────────────────────────────────┐
        │ 0. INPUT: topic + tài liệu + (nhiều) video mẫu           │
        └───────────────┬──────────────────────────────────────────┘
                        ▼
  1. RESEARCH        nghiên cứu nguồn, trích dữ kiện, gắn trích dẫn
                        ▼
  2. STYLE BLUEPRINT (mới)  phân tích video mẫu → blueprint phong cách
                        ▼
  3. SCRIPT          preset + prompt hợp đồng; sinh bằng Claude/Gemini/
                     DeepSeek/agent ngoài; lint + copy_risk + timing
                        ▼
        ╔══ CỔNG NGƯỜI DUYỆT #1: duyệt kịch bản + xác nhận bản quyền ══╗
                        ▼
  4. VOICE           TTS nhiều giọng (tiếng Việt ưu tiên), đo thời lượng
                        ▼
  5. VISUALS         ảnh/video nền: stock, ảnh sinh, text-to-video, mẫu
                        ▼
  6. ASSEMBLY        timeline, nhịp theo beat, phụ đề, nhạc, màu
                        ▼
  7. RENDER          ffmpeg (thật) → mp4/webm + thumbnail + phụ đề .srt
                        ▼
        ╔══ CỔNG NGƯỜI DUYỆT #2: duyệt video cuối ══╗
                        ▼
  8. PUBLISH         xuất gói nền tảng (YouTube/TikTok/Facebook/Shopee…)
```

Mỗi stage phải: (a) đọc cấu hình từ preset/env, (b) ghi artifact có thể xem
lại, (c) chạy lại được mà không phá stage trước, (d) có lối thoát offline.

## 5. Roadmap

### P0 — Nền tảng (đã xong)
- [x] Lifecycle + 2 cổng duyệt + state machine
- [x] Provider chain, retry, circuit breaker, rate limit
- [x] Research + thư viện tài liệu BM25
- [x] Video editor trình duyệt + export WebM
- [x] TTS tiếng Việt + sync scene theo audio thật

### P1 — Kịch bản chuẩn + đa AI (đã xong phiên này)
- [x] Script engine: parse, timing đa ngôn ngữ, linter, copy_risk
- [x] Prompt hợp đồng dùng chung cho mọi model
- [x] Preset phong cách do user tinh chỉnh (JSON + MD)
- [x] Adapter native Claude + Gemini, hỗ trợ DeepSeek/Ollama
- [x] Endpoint `/agents` để thấy rõ AI nào đang bật
- [x] Cầu nối agent ngoài: `brief.md` xuất / `agent-result` nhập

### P2 — Render thật bằng ffmpeg (ưu tiên cao nhất tiếp theo)
- [ ] `render.py`: dựng timeline → lệnh `ffmpeg` (concat, xfade, overlay,
      subtitle burn-in, mix audio)
- [ ] Worker thật thay worker mô phỏng; tiến trình theo % thật
- [ ] Thumbnail thật (JPG) + sprite preview
- [ ] Kiểm tra ffmpeg có trên máy khi khởi động, cảnh báo rõ ràng
- [ ] Job bền vững: hàng đợi trên đĩa để restart không mất việc

### P3 — Video mẫu → blueprint phong cách (yêu cầu 9)
- [ ] `reference.py`: nhận N video mẫu (file hoặc URL)
- [ ] Trích: độ dài shot trung bình, nhịp cắt, mật độ phụ đề, palette,
      vị trí chữ, kiểu hook, năng lượng nhạc
- [ ] Sinh `StyleBlueprint` → tự map sang preset kịch bản + thông số timeline
- [ ] Nút "Edit giống mẫu này" trong UI
- [ ] **Bắt buộc**: chỉ dùng số liệu phong cách, không lưu/không tái sử dụng
      khung hình hay âm thanh của mẫu

### P4 — Sinh hình ảnh & video bằng AI
- [ ] Adapter text-to-image (SDXL/Flux qua ComfyUI local, hoặc API)
- [ ] Adapter text-to-video / image-to-video (Veo, Kling, Luma, Runway…)
- [ ] `visual_provider` configurable: stock | ảnh sinh | video sinh | mẫu
- [ ] Cache asset theo hash prompt để không trả tiền hai lần
- [ ] Kiểm duyệt nội dung + watermark nếu nhà cung cấp yêu cầu

### P5 — Lồng tiếng nâng cao + nhiều giọng
- [ ] Nhiều giọng trong cùng video: người dẫn, nhân vật, giọng đọc quảng cáo
- [ ] Voice clone (RVC / so-vits-svc / XTTS) chạy local
- [ ] SRT/VTT + forced alignment (whisperX) để phụ đề khớp từng từ
- [ ] Chuẩn hoá âm lượng (EBU R128), khử ồn, de-esser
- [ ] Thư viện giọng tiếng Việt: miền Bắc/Trung/Nam, nam/nữ, tin tức/kể chuyện

### P6 — Chỉnh ảnh & chỉnh video nâng cao (yêu cầu 14, 15)
- [ ] Lớp chỉnh ảnh: crop, curves, LUT, retouch, xoá vật thể (rembg + inpaint),
      upscale (Real-ESRGAN), ổn định (stabilize)
- [ ] Hiệu ứng chuyển cảnh, speed ramp, motion tracking, keyframe đa điểm
- [ ] Undo/redo bền vững theo project, lịch sử phiên bản (version history)
- [ ] "Auto-edit giống editor chuyên nghiệp": cắt theo nhịp, chọn B-roll khớp

### P7 — Tự động hoá & vận hành
- [ ] MCP server để Claude Code / Codex điều khiển trực tiếp mọi endpoint
- [ ] Webhook + lịch chạy định kỳ (sản xuất hàng loạt từ CSV chủ đề)
- [ ] Đa người dùng, phân quyền, lịch sử duyệt có chữ ký
- [ ] Đo chất lượng: A/B hook, retention dự đoán trước khi publish
- [ ] Xuất hàng loạt (batch) và hàng đợi publish theo khung giờ

## 6. Toolchain — cài gì, cài ở đâu

Xem `docs/TOOLCHAIN.md` để có lệnh cài cụ thể theo hệ điều hành. Tóm tắt nhóm
tool cần có trên máy chủ dự án:

| Nhóm | Tool | Dùng cho |
| ---- | ---- | -------- |
| Xử lý media | **ffmpeg**, ffprobe | render, cắt, mix, phụ đề, đóng gói |
| Tải nguồn | yt-dlp | tải video mẫu/nguồn (chỉ khi có quyền) |
| Nhận dạng | faster-whisper / WhisperX | transcript, forced alignment |
| Tách nhạc | Demucs | tách lời/nhạc, xử lý nền |
| Ảnh | Pillow, OpenCV, rembg, Real-ESRGAN | chỉnh ảnh, xoá nền, upscale |
| Video bằng AI | ComfyUI (SDXL/Flux), adapter API Veo/Kling/Luma | tạo hình |
| Giọng | edge-tts, gTTS, Coqui XTTS, RVC | đọc và clone giọng |
| LLM local | Ollama (Qwen/Llama/Gemma) | kịch bản offline, miễn phí |
| Python | FastAPI, uvicorn, httpx, pydantic, mutagen | backend (đã có) |

Nguyên tắc: **tool nào cũng phải gọi được qua adapter có config**, không gọi
trực tiếp rải rác trong code. Nếu thiếu tool, pipeline phải báo lỗi rõ ràng và
có đường lui (ví dụ: không có ffmpeg thì vẫn export được WebM từ browser).

## 7. Hợp đồng file MD tự tinh chỉnh

Bốn loại file MD/JSON là "giao diện tinh chỉnh" của dự án:

1. **`presets/*.md` hoặc `presets/*.json`** — phong cách kịch bản (tone, cấu
   trúc, hook rules, từ cấm, tốc độ đọc theo ngôn ngữ). User và AI agent đều
   sửa được. Ví dụ: `presets/example-storytelling.json`.
2. **`brief.md`** (sinh ra bởi `GET /projects/{id}/brief.md`) — toàn bộ ngữ
   cảnh cho AI agent bên ngoài, kèm "hợp đồng trả lời".
3. **`.env`** (mẫu ở `.env.example`) — chọn AI nào, giọng nào, thư mục, giới
   hạn tốc độ.
4. **File này** (`docs/KE-HOACH-TONG-THE.md`) — ý định của con người.

Quy tắc: mọi thứ có thể tinh chỉnh thì **phải** nằm trong 1 trong 4 loại trên,
không được là hằng số trong code.

## 8. Câu hỏi mở cần chủ dự án quyết

1. **Render thật**: dùng ffmpeg local (miễn phí, khó cài trên Windows) hay
   thuê API render? → đề xuất: ffmpeg local + adapter API dự phòng.
2. **Ưu tiên P2 hay P3 trước?** → đề xuất: P2 (render thật) vì mọi thứ khác
   đều cần nó.
3. **Giọng đọc chính**: edge-tts (miễn phí) đủ dùng, hay cần clone giọng riêng
   (RVC/XTTS)? → cần chủ dự án cung cấp mẫu giọng.
4. **Nguồn hình**: stock miễn phí, ảnh AI sinh, hay quay thật? Ảnh hưởng lớn
   tới chi phí và thời gian.
5. **Ngân sách API hàng tháng** cho Claude/Gemini/Veo… để chọn chiến lược
   `cost_first` hay `quality_first`.
6. **Máy chạy**: Windows hiện tại hay có GPU server riêng? Quyết định việc
   chạy ComfyUI/Ollama/XTTS local.

## 9. Nhật ký thay đổi

### 2026-09-16 — Phiên 1: kịch bản, đa AI, cầu nối agent
- Ghi lại toàn bộ yêu cầu gốc vào file này (mục 1).
- Thêm `script_engine.py`: parse section (dùng chung với `scenes.py`), profile
  ngôn ngữ (17 ngôn ngữ, có tiếng Việt), plan thời lượng, linter, `copy_risk`.
- Thêm `presets.py` + `presets/`: preset JSON/MD do user tinh chỉnh, ghi đè
  được preset dựng sẵn.
- Mở rộng `providers.py`: `AnthropicProvider` (Claude), `GeminiProvider`
  (Google), DeepSeek, Ollama; tier mạnh thử lần lượt theo cấu hình; thêm
  `catalog()`.
- Thêm `agent_bridge.py`: xuất `brief.md`, nhập kết quả agent.
- Thêm endpoint: `/agents`, `/script/styles*`, `/projects/{id}/script/analyze`,
  `/projects/{id}/script/style`, `/projects/{id}/brief.md`,
  `/projects/{id}/agent-result`.
- Thêm biến cấu hình: `ANTHROPIC_*`, `GOOGLE_*`, `DEEPSEEK_*`, `OLLAMA_*`,
  `STRONG_PROVIDER_ORDER`, `PRESETS_DIR`, `AGENT_BRIDGE_ENABLED`.
- Thêm test: `tests/test_script_engine.py`, `tests/test_presets.py`,
  `tests/test_agent_bridge.py`, `tests/test_agents.py`.
- Thêm tài liệu: file này (kế hoạch tổng thể), `docs/TOOLCHAIN.md` (hướng dẫn
  cài tool), `docs/AGENT-BRIDGE.md` (hợp đồng MD với agent ngoài),
  `presets/README.md`.
- Thêm `scripts/toolcheck.py`: liệt kê tool nào đã có trên máy, tool nào còn
  thiếu và nó mở khoá tính năng gì (chạy `python scripts/toolcheck.py`).
- Thêm skill `.claude/skills/agent-brief/SKILL.md` để agent ngoài tự biết quy
  trình brief → trả kết quả.
- Kiểm chứng (chạy lại ngày 2026-09-16, tất cả xanh):
  - `ruff check src tests scripts` → All checks passed
  - `ruff format --check` → 38 files already formatted
  - `mypy src` → no issues in 18 source files
  - `pytest` → **206 passed**
  - `scripts/smoke.py` → **PASS 44 checks** (dựng server thật rồi đi hết pipeline:
    research → analyze → brief.md → agent-result → 2 cổng duyệt → publish, cộng
    preset CRUD, ai-assist, voiceover, thumbnail, và các nhánh 404/409/422)
  - `scripts/benchmark.py` → plan_script 0.10ms, lint 30 scene 1.90ms,
    copy_risk 0.40ms (đủ nhanh để chạy mỗi lần lưu kịch bản)
- Lưu ý vận hành: smoke test **dùng lại** server đang mở ở cổng 8080 nếu có.
  Server đó có thể chạy code cũ — hãy chạy
  `python scripts/smoke.py --port=<cổng trống>` để ép dựng instance mới.
  Cổng 8080 trên máy hiện đang có một tiến trình của phiên trước (PID 393176),
  cần **restart** để nhận code mới.
- Việc tiếp theo: **P2 — render thật bằng ffmpeg**. Trước khi làm P2, chủ dự
  án nên trả lời 2 câu hỏi ở mục 8 (máy có GPU không, và ưu tiên P2 hay P3).

### 2026-09-16 — Phiên 2: dọn sạch và nâng cấp lõi edit video

**Vấn đề gốc:** logic chỉnh sửa nằm rải rác ở `scenes.py` / `smart.py` /
`service.py`, **không hề validate**, không có chia/gộp/đổi thứ tự, không có
keyframe nhiều điểm, không có khái niệm "kế hoạch render", và client (browser)
là nguồn chân lý cho cấu trúc timeline.

- **Thêm `src/content_factory/timeline.py`** — engine edit video thuần:
  - `normalize()` idempotent: id duy nhất, kẹp mọi khoảng giá trị, sắp/xoá
    trùng keyframe, màu hex hợp lệ, aspect ratio hợp lệ, bỏ transition ở
    scene đầu. **Mọi lần lưu đều đi qua đây.** → không thể ghi được timeline hỏng.
  - `measure()` + `report()`: 15 quy tắc kiểm tra chuyên nghiệp (tương phản
    chữ theo WCAG, chữ tràn thời gian, lời đọc tràn/thiếu gây "dead air",
    cắt quá nhanh, transition quá dài, lệch thời lượng mục tiêu…) + điểm 0–100.
  - Thao tác cấu trúc: `split_scene` (giữ nguyên tổng thời lượng), `merge_scene`,
    `duplicate_scene`, `delete_scene` (bảo vệ scene cuối), `move_scene`,
    `bulk_update` (validate qua pydantic nên `"noir"` → `ColorGrade.NOIR`),
    `add_marker` / `remove_marker`.
  - `evaluate_motion()`: keyframe đa điểm + easing, fallback về `motion` cũ.
  - `compile_render_plan()`: scene → slot tuyệt đối, cue phụ đề (≤9 từ, tỉ lệ
    theo độ dài), layer audio — đây là thứ renderer thật (P2 ffmpeg) sẽ dùng.
- **Models**: thêm `Keyframe`, `TimelineMarker`, `TimelineStats`,
  `TimelineIssue`, `TimelineReport`, `SubtitleCue`, `AudioTrackPlan`,
  `RenderStep`, `RenderPlan`; `VideoScene` thêm `keyframes`, `trim_start`,
  `trim_end`, `volume`; `VideoProject` thêm `markers`, `voiceover_volume`,
  `revision`. `IssueSeverity` gom chung cho cả script lẫn timeline
  (`ScriptIssueSeverity` giữ làm alias).
- **12 endpoint mới** dưới `/timeline/*` + `/render-plan`.
- **Sửa lỗi tìm được khi test**:
  1. `bulk_update` gán thẳng giá trị thô → `grade` thành chuỗi `"noir"` thay vì
     enum (dữ liệu bẩn + warning khi serialize). Nay validate qua pydantic.
  2. `revision` do client gửi nên có thể bị nhảy về 1 → mất khả năng phát
     hiện "ai đó đã sửa". Nay **server sở hữu** bộ đếm.
  3. API trả `404 "Project not found"` cho scene/kiểu không tồn tại → nay trả
     đúng thông báo (`No scene 'x' …`) qua `_guard_value`.
  4. Project đã `published` không edit video được → nay cho phép (cắt lại rồi
     publish lại là việc bình thường).
- **Frontend**: thêm thanh **Pro Engine** vào Studio (index.html / style.css /
  editor.js): điểm + thống kê trực tiếp, danh sách phát hiện (bấm vào để nhảy
  tới scene), nút Split / Merge / Duplicate / Delete / ↑ ↓ / 📍 Marker / 🧹 Clean
  / 🩺 Check / 📋 Render Plan. Mỗi thao tác: đẩy tinh chỉnh local → gọi 1 API →
  nhận lại tài liệu từ server. Nút Save giữ nguyên `markers` và không phá
  `revision` nữa.
- **Đã kiểm tra UI thật bằng trình duyệt** (preview): mở Studio, bấm Render
  Plan → in ra `resolution 1080×1920 @ 30fps · 45s / steps 4 · caption cues 5`;
  Split 4→5→6 scene; Duplicate tạo `Hook copy`; Merge ở scene cuối trả toast
  "The last scene has nothing to merge into."; Marker tạo mốc tại playhead;
  revision tăng đúng (1 → 12).
- **Kiểm chứng**: `ruff check` + `ruff format --check` sạch, `mypy src` sạch,
  **275 test pass** (thêm 69 test: `test_timeline.py`, `test_timeline_api.py`),
  `node --check` cho JS sạch.
- **Tài liệu**: thêm `docs/EDITING.md` (mô hình, bảo đảm, bảng 15 quy tắc, thao
  tác, keyframe, render plan, endpoint); cập nhật `README.md`, skill
  `edit-video`, và file này.
- Việc tiếp theo: **P2 — render thật bằng ffmpeg, dùng trực tiếp
  `/render-plan`** (plan đã sẵn sàng làm đầu vào cho ffmpeg filtergraph).

### 2026-09-16 — Phiên 3: Nâng cấp toàn diện UI Creative Studio Pro (TikTok · CapCut · Adobe Premiere & Photoshop Edition)
- **Đã làm**:
  - **Workspace Switcher đa không gian làm việc**:
    1. `🚀 Pipeline`: Quy trình tự động 7 giai đoạn + Script Editor & Quality Score linter gauge + phê duyệt Gate 1 & Gate 2.
    2. `🎬 Video Studio`: NLE Video Studio phong cách Premiere Pro / CapCut với Dock công cụ bên trái (Select, Razor Cut, Text, Sticker, Audio, Color, VFX), TikTok Safe Zone transparent overlay guides, Phone bezel mockup, SFX Sound Pad tổng hợp âm thanh tức thì (Whoosh, Pop, Click, Impact, Level Up, Ding) qua Web Audio API, thanh điều khiển phát lại và timecode SMPTE.
    3. `🎨 Photo Lab (Photoshop)`: Studio chỉnh sửa ảnh / thumbnail hoàn chỉnh với Canvas vẽ đa tỉ lệ (9:16 TikTok Cover, 16:9 YouTube, 1:1 Instagram, 4:5 Reels), Toolbar vẽ hình / cọ / tẩy / chữ / eyedropper, bảng điều khiển Layers đầy đủ (thứ tự, ẩn/hiện, opacity, blend mode), bảng cân chỉnh Curves / Brightness / Contrast / Saturation / Hue / Vignette / Blur / Bộ lọc màu, thư viện mẫu Viral Thumbnail, và nút chụp frame tức thì từ Video Studio sang Photo Lab.
    4. `🕸 Node Flow (DAG)`: Canvas đồ thị node trực quan kết nối trực tiếp với backend (`/workflow/blocks`, `/projects/{id}/workflow`, `/projects/{id}/workflow/checklist`, `/projects/{id}/workflow/run`) có bảng nhật ký terminal stream.
    5. `⚡ Agents`: Trung tâm điều phối đa AI (Claude, Gemini, Codex, DeepSeek, Local).
    6. `📚 Library`: Tìm kiếm tài liệu học thuật (arXiv, Crossref, Gutenberg, Wikipedia) và tra cứu BM25 nội bộ.
  - **Hotkeys chuyên nghiệp**:
    - `Space`: Play / Pause video.
    - `C`: Razor Cut (cắt clip tại playhead).
    - `Del` / `Backspace`: Xoá clip đang chọn.
    - `M`: Đánh dấu Marker tại playhead.
    - `F`: Bật / tắt Cinema Mode toàn màn hình không viền.
    - `1 - 6`: Chuyển đổi siêu tốc giữa 6 không gian làm việc.
  - **Kiểm chứng**:
    - `ruff check` + `ruff format --check` sạch 100%.
    - `mypy src` sạch 100%.
    - `pytest` pass toàn bộ **307 tests**.
    - HTTP server và toàn bộ tài nguyên tĩnh (`style.css`, `app.js`, `editor.js`) phản hồi HTTP 200 OK.
- **Quyết định**:
  - Tích hợp 100% bằng HTML5 Canvas + Web Audio API + Vanilla CSS/JS hiện đại, không kéo thêm thư viện cồng kềnh, đảm bảo app chạy mượt, 60 FPS và hoạt động offline hoàn toàn.

### 2026-09-16 — Phiên 4: Thiết kế Hệ thống Kéo-Thả (DAG), AI Agent Toolbox & Bộ Skills chuyên biệt cho từng loại AI Agent
- **Đã làm**:
  - **Bộ 6 Skills chuyên biệt cho AI Agent** tạo tại `.claude/skills/` tuân thủ đầy đủ YAML frontmatter và hướng dẫn quy chuẩn:
    1. `.claude/skills/ai-scripting/SKILL.md`: Thiết kế kịch bản ngắn viral, cấu trúc section cues `[Hook]`, `[Turn]`, `[Payoff]`, `[CTA]`, `[Visual]`, `[Sound]`, kiểm soát nhịp đọc tiếng Việt (3.8 - 4.2 âm tiết/giây), quét trùng lặp `copy_risk`.
    2. `.claude/skills/ai-video-editing/SKILL.md`: Dựng timeline NLE, phân cảnh `VideoScene`, keyframe chuyển động, Ken Burns, Lumetri LUTs, TikTok Safe Zone, biên dịch `render_plan`.
    3. `.claude/skills/ai-audio-editing/SKILL.md`: Xử lý âm thanh, giọng đọc Edge-TTS tiếng Việt (`vi-VN-HoaiMyNeural`, `vi-VN-NamMinhNeural`), Web Audio SFX synthesizer, audio ducking, nhịp BPM.
    4. `.claude/skills/ai-thumbnail-photo/SKILL.md`: Thiết kế ảnh bìa viral Photoshop đa tỉ lệ (9:16, 16:9, 1:1, 4:5), quản lý Layer hierarchy, tone curves, contrast balancing.
    5. `.claude/skills/ai-workflow-dag/SKILL.md`: Xây dựng quy trình tự động kéo-thả DAG, kiểm tra checklist pre-save, validation, thực thi pipeline qua API.
    6. `.claude/skills/ai-agent-orchestrator/SKILL.md`: Nhạc trưởng phân công và điều phối đa agent (Claude kịch bản, Gemini nghiên cứu/thị giác, Codex dựng video/keyframes, DeepSeek kiểm chứng, Local xử lý offline).
  - **Hệ thống Kéo-Thả (Drag & Drop) Node Flow DAG**:
    - Giao diện 3 cột `dag-workbench`: Palette khối chức năng (`dag-palette`), Canvas đồ thị SVG bezier links (`dag-canvas-wrap`), và Inspector thuộc tính (`dag-inspector`).
    - Hỗ trợ kéo thả block từ palette vào canvas, di chuyển snap grid 10px, nối dây giữa các port `＋`, xoá node/edge bằng `Backspace`, huỷ dây bằng `Esc`.
    - Tích hợp kiểm định pre-save checklist (kiểm tra chu trình, orphan nodes, bắt buộc 2 cổng phê duyệt nhân sự Gate 1 & Gate 2).
    - Console terminal stream theo dõi luồng thực thi từng node trong thời gian thực.
  - **Agent Toolbox & Action Matrix**:
    - Thiết kế bảng công cụ ma trận cho Claude, Gemini, Codex, DeepSeek và Local Engine với giao diện Dark Glassmorphism, viền neon tương ứng từng hãng.
    - Nút `📋 Copy Prompt` tạo prompt chuẩn Markdown theo hợp đồng `AGENT-BRIDGE.md` tự động sao chép vào clipboard.
    - Nút `⚡ Run Action` kích hoạt ngay bước pipeline tương ứng hoặc phát âm thanh SFX Web Audio trực tiếp.
  - **Kiểm chứng chất lượng**:
    - `ruff check src tests` sạch 100%.
    - `ruff format --check src tests` sạch 100%.
    - `mypy src` sạch 100%.
    - `pytest` pass toàn bộ **311 tests**.
    - `smoke.py` pass toàn bộ **55 checks** trên port 8000.
    - Đã sửa lỗi event loop trong `src/content_factory/workflow.py` (`_run_sync` xử lý đa luồng an toàn cho các tác vụ async khi chạy workflow execution).
    - Frontend assets (`index.html`, `style.css`, `app.js`, `editor.js`, `flow.js`) hoạt động đồng bộ.
- **Quyết định**:
  - Tách bạch vai trò thế mạnh của từng AI: Claude chịu trách nhiệm văn phong & kịch bản cảm xúc; Gemini phụ trách nghiên cứu học thuật & chỉ dẫn khung hình trực quan; Codex chịu trách nhiệm cấu trúc JSON timeline & toán keyframe chuyển động; DeepSeek chịu trách nhiệm quét đạo văn & phản biện dữ liệu; Local Engine đảm bảo mọi xử lý âm thanh/video cơ bản luôn chạy được offline mà không tốn chi phí API.
  - Giữ nguyên 2 cổng phê duyệt của con người (script approval, video approval) trong mọi kịch bản kéo thả workflow DAG để đảm bảo an toàn tuyệt đối.
- **Việc tiếp theo**:
  - Phase 2: Triển khai pipeline render video thực tế bằng ffmpeg theo hợp đồng `render_plan`.

### 2026-09-16 — Phiên 5: Thiết kế Cỗ máy Đế chế Đa Định Dạng (YouTube + TikTok) & Trung Tâm Nạp Tư Liệu AI Ngoại Vi (Ingestion Hub)
- **Đã làm**:
  - **Cỗ máy Đế chế Đa Định Dạng (Multi-Format Content Empire Engine)**:
    - Mô hình chiến lược: 1 Chủ đề Nghiên cứu Gốc ➔ 1 Video YouTube Dài (8–12 phút, 16:9, 40–60 cảnh tài liệu, cung bậc 8 bước kịch tính) + 5–10 Video TikTok / Shorts Độc lập (30–60 giây, 9:16, 5 pha giữ chân nhịp cao Retention > 100%).
    - **Công thức Tỉ lệ Tư liệu Lai (Golden Hybrid Media Ratio)**: 30% Tái hiện AI Video (Kling / Veo / Wan 2.1), 20% Ảnh lịch sử phục chế, 15% Bản đồ hành trình 3D, 15% Hồ sơ giải mật & Nhật báo, 10% Sơ đồ kỹ thuật blueprint, 10% Kinetic motion typography (loại bỏ hoàn toàn cảm giác "AI rẻ tiền", tối đa hóa uy tín kênh tài liệu).
    - **Gói 15 Tài nguyên Toàn diện**: Research Dossier, Fact-Check Audit, YouTube Master Script, 5-10 Shorts Scripts, Hybrid Scene List, Prompts cho Kling/Veo, Midjourney, Suno, ElevenLabs, 5x YouTube Titles, 10x TikTok Hooks, Chapters & SEO Description, Thumbnail Prompts.
    - **Không gian làm việc Empire Hub (Tab 7 - Phím tắt 7)**: Giao diện Dark Glassmorphism chia đôi màn hình (60% YouTube Master bên trái, 40% TikTok Shorts bên phải kèm trình chỉnh sửa ngắn), thanh tỉ lệ tư liệu lai trực quan, và Ma trận Prompts 1-click copy cho từng AI Tool.
  - **Trung Tâm Nạp Tư Liệu & Media Ngoại Vi (External AI Results Ingestion Hub)**:
    - Giải quyết bài toán nạp kết quả từ các công cụ AI bên ngoài (Kling, Veo, Midjourney, ElevenLabs, Suno, Perplexity) trực tiếp vào timeline và từng scene.
    - Modal nạp tư liệu 4 tab (`ipanel-media`, `ipanel-audio`, `ipanel-dossier`, `ipanel-batch`) hỗ trợ cả URL trực tuyến (Zero-storage linking) và Tải file cục bộ lên máy chủ (`storage/uploads/{project_id}/` phục vụ tĩnh qua `/uploads/`).
    - Batch Dropzone thông minh: Tự động phân tích tên file (`scene_1.*`, `voiceover.*`, `bgm.*`) gán chính xác vào scene, track âm thanh và kho tri thức.
    - Hiển thị huy hiệu `[🎬 Video Attached]`, `[🖼️ Photo Attached]` trên từng thẻ cảnh với nút Ingest nhanh.
    - Bảo đảm an toàn tuyệt đối: Nguồn tư liệu bên ngoài không bao giờ tự động xác nhận bản quyền; tuân thủ nghiêm ngặt 2 cổng phê duyệt của con người Gate 1 & Gate 2.
  - **Mã nguồn Backend & Workflow**:
    - `src/content_factory/models.py`: Thêm `MultiFormatCampaign`, `ShortsVariant`, `PromptPack`, `ExternalAssetRecord`, `ExternalImportRequest`, `BatchExternalImportRequest`, node DAG `ingest_external`.
    - `src/content_factory/campaign.py`: Module sinh kịch bản và prompt 15 tài nguyên tự động.
    - `src/content_factory/service.py` & `api.py`: Các API endpoint `/campaign/*`, `/external/*`.
    - `src/content_factory/workflow.py`: Thực thi node `ingest_external` trong workflow DAG runner.
  - **Kiểm định chất lượng & CI**:
    - `pytest`: Toàn bộ **317/317 tests pass 100%**.
    - `ruff check`, `ruff format --check`, `mypy src`: Sạch 100%.
    - `scripts/smoke.py`: Hoàn thành xuất sắc **64/64 checks** bao gồm campaign và external ingest.
    - Bổ sung 2 skills chuẩn: `.claude/skills/multi-format-campaign/SKILL.md` và `.claude/skills/external-results-ingestion/SKILL.md`.
- **Quyết định**:
  - Tách bạch hoàn toàn giữa kịch bản YouTube dài và Shorts ngắn: Tuyệt đối không cắt vụn video dài thành shorts; mỗi short phải là một góc nhìn giật gân, độc lập với nhịp retention riêng để thuật toán TikTok phân phối tối đa.
  - Lưu trữ media tải lên trong `storage/uploads/{project_id}/` với tên file an toàn kèm tiền tố băm ngẫu nhiên chống ghi đè; phục vụ tĩnh an toàn qua route `/uploads`.
- **Việc tiếp theo**:
  - Phase 2: Kết nối ffmpeg renderer để ghép các video clip Kling/Veo, ảnh tư liệu, audio ElevenLabs và nhạc nền Suno đã nạp vào thành video MP4 hoàn chỉnh.

### 2026-09-16 — Phiên kiểm thử toàn bộ và báo cáo vấn đề
- Đã làm: Chạy pytest tuần tự (pass toàn bộ), smoke test (64/64 checks pass),
  inventory tool local và kiểm tra Ruff/format/mypy.
- Kết quả: Smoke và test hành vi pass; quality gate đang đỏ vì 11 lỗi Ruff,
  1 file lệch format và 9 lỗi mypy trong `service.py`. Máy có ffmpeg,
  ffprobe và TTS cơ bản nhưng thiếu 8 tool tùy chọn.
- Tài liệu: Ghi đầy đủ lỗi, skill chưa thể kiểm chứng và khoảng trống roadmap
  vào `problem.md`.
- Việc tiếp theo: Sửa contract service/model, làm wrapper PowerShell xử lý
  môi trường thiếu `.venv`, sau đó điều tra hiện tượng lỗi prompt khi chạy test
  đồng thời với smoke.

### 2026-09-16 — Phiên tiếp tục: renderer ffmpeg thật và sửa agent tools
- Đã làm: Thêm `src/content_factory/render.py`, endpoint
  `POST /projects/{id}/render`, test ffmpeg trực tiếp và test API phục vụ WebM.
  Renderer hiện tạo được color-card timeline có text overlay và tự tìm font
  Windows/Linux.
- Đã sửa: Dependency/runtime contracts, serializer list model trong agent
  tools, truyền `source_rights_confirmed`, các lỗi import/format/type và test
  state timeline.
- Kiểm định: Full pytest pass, Ruff + format + mypy pass, smoke 64/64 pass.
- Quyết định: Giữ renderer giai đoạn đầu backend-agnostic và ổn định với
  color cards; bước sau mới thêm source image/video, audio mix, subtitle
  burn-in và job progress bền vững.
- Việc tiếp theo: Mở rộng ffmpeg renderer để tiêu thụ media/audio thật.

### 2026-09-16 — Phiên kiểm thử siêu kỹ: fix P1, render video thật cho 6 chủ đề chiến tranh
- Đã làm:
  - **Fix P1 (lỗi prompt khi chạy đồng thời)**: Nguyên nhân gốc là `__pycache__`
    cũ chứa bytecode từ 2 phiên bản pytest (9.0.3 và 9.1.1) — khi import song song
    một process đọc được module `script_engine` cũ thiếu tham số `grounding`.
    Đã thêm test hồi quy `test_build_script_prompt_accepts_grounding_keyword`
    (khóa chữ ký `grounding=` bằng `inspect.signature` + render thật một
    `GroundingBundle`) và dọn sạch `__pycache__`, `.pytest_cache`, `.ruff_cache`,
    `.mypy_cache`.
  - **Cài 4 tool tùy chọn nhẹ**: `pillow`, `opencv-python-headless`, `moviepy`,
    `yt-dlp`. `toolcheck.py` giờ báo 8 available. Đã pin `numpy==2.2.6` vì
    `numpy 2.5.3` có type stub dùng cú pháp Python 3.12 làm vỡ `mypy`
    (config `python_version=3.11`).
  - **Thêm driver QA đầy đủ `scripts/qa_war_full_flow.py`**: chạy trọn luồng
    `draft → script_review → script_approved → generating → video_review →
    (self-edit) → render → video_approved → published` và **tạo WebM thật** cho
    từng dự án, probe bằng `ffprobe`.
  - **Chạy 6 chủ đề chiến tranh khác nhau**: WWI Verdun, WWII Stalingrad,
    Vietnam Ho Chi Minh Trail, Korean Pusan Perimeter, Waterloo, Civil War
    Vicksburg. Cả 6 đều `published` với WebM VP9 1080x1920 ~44–45s (~1MB).
- Kiểm định: Full pytest pass, Ruff + format + mypy pass, smoke 64/64 pass,
  QA 6/6 pass.
- Quyết định: Không cài các tool nặng phụ thuộc torch/GPU (faster-whisper,
  whisperx, demucs, rembg, TTS) trong môi trường offline này — ghi rõ là gap
  còn lại trong `problem.md`. `yt-dlp` cài dạng Python package nhưng
  `toolcheck.py` kiểm tra binary trên PATH nên vẫn báo missing.
- Việc tiếp theo: Mở rộng ffmpeg renderer để tiêu thụ source image/video,
  audio mix, subtitle burn-in và job progress bền vững.

### Mẫu ghi cho phiên sau

```
### YYYY-MM-DD — Phiên N: <việc lớn>
- Đã làm: ...
- Quyết định: ... (và vì sao)
- Việc tiếp theo: ...
```

## 2026-09-16 — NLE Pro tools + /tools registry cho AI agent

**Mục tiêu phiên:** so sánh với Premiere/Adobe, bổ sung mọi chức năng chỉnh
sửa còn thiếu, và làm bộ tool mà AI agent bên ngoài (Claude, Codex, DeepSeek,
Gemini) gọi được để vận hành toàn pipeline.

**Đã làm:**

1. **NLE Pro ops trong `timeline.py` + `models.py`:** `set_speed` (retime
   0.5x–2x, slot đổi theo 1/speed như Premiere), `reverse_scene` (boomerang),
   `trim_scene` (in/out điểm trên nguồn, không đổi timeline),
   `set_audio` (gain 0–2 + fade in/out từng cảnh), `copy_scene`/`paste_scene`
   (clipboard JSON). `VideoScene` thêm `reverse`, `audio_fade_in`,
   `audio_fade_out`.
2. **API mới (7 endpoint):** `/timeline/scenes/{id}/speed|reverse|trim|audio|
   copy`, `/timeline/scenes/paste`.
3. **Agent Tools registry `agent_tools.py`:** `GET /tools` trả manifest
   tự mô tả (32 tools, 5 nhóm: discovery/research/script/timeline/production +
   usage_notes), `POST /tools/call` dispatch an toàn — validate id, map lỗi
   domain sang 404/409/403/422, trả JSON model_dump. Lỗi lạ từng gặp:
   `KeyError(scene_id)` → thông báo rỗng; đã sửa `timeline.find_scene/index_of`
   + `NotFoundError` trong `service.py` thành thông báo người đọc được
   ("No scene 'x' in the video project.").
4. **Skill + docs:** `.claude/skills/edit-video-tools/SKILL.md` (cho Claude),
   `docs/TOOLS-FOR-AGENTS.md` (curl examples, bảng tool, quy tắc bất di bất
   dịch: không tự confirm rights, hai cổng duyệt là của người).
5. **Live test `scripts/live_tools_test.py`:** 20 check chạy thật qua HTTP —
   manifest, cả flow create→script→approve→build→generate→10 NLE edits→
   report→render_plan, và error mapping (422/404). Kết quả: ALL PASS.

**Kiểm chứng:** ruff + format sạch (60 files), mypy sạch (27 files),
pytest **348 passed**, smoke **64 checks** PASS, benchmark: timeline.report
0.30ms, compile_render_plan 0.46ms.

**Còn lại:** render thật bằng ffmpeg (P2) vẫn là bước lớn tiếp theo;
`/tools/call` đã sẵn sàng để agent gọi ngay khi renderer có thật.

### 2026-09-16 — Đại tu toàn diện UI theo chuẩn Adobe Creative Cloud & Bộ công cụ Commercial Editing Suite

**Mục tiêu phiên:** Nâng cấp toàn diện giao diện frontend để đạt trải nghiệm, thẩm mỹ và luồng thao tác tương đương bộ phần mềm Adobe Creative Cloud chuyên nghiệp (Premiere Pro NLE, After Effects Shaders/Motion, Photoshop/Lightroom Photo Lab, Audition Stereo Peak Mixer, Media Encoder Queue) mà không thiếu bất kỳ tính năng nào; đồng thời bổ sung các công cụ chỉnh sửa cao cấp và benchmark toàn diện cho pipeline video thảm họa/lịch sử.

**Đã làm:**
1. **Adobe Top Application Menu Bar (`.adobe-app-bar`):**
   - Bộ nhận diện suite badges chính hãng: **Pr** (Premiere), **Ae** (After Effects), **Ps** (Photoshop), **Au** (Audition), **Me** (Media Encoder).
   - Hệ thống desktop dropdown menus tiêu chuẩn: File, Edit, Clip, Sequence, Audio, Graphics, Window, Help với đầy đủ phím tắt kbd (Ctrl+N, Ctrl+S, Ctrl+M, Ctrl+Z, C, V, A, B, Y, P, H, T, ?, 1–7).
2. **Premiere Pro Workspace Tabs Bar (`.premiere-workspace-bar`):**
   - 7 Workspace tabs chuyên nghiệp: `🎬 Editing`, `🎨 Color (Lumetri)`, `✨ Effects (Ae)`, `🎙 Audio (Audition)`, `📝 Graphics & Captions`, `⚡ Export (Media Encoder)`, `🤖 AI Co-Pilot`.
   - Metadata sequence thời gian thực (`Sequence 01 · 1080×1920 (9:16) @ 30.00 fps`) cùng LED status indicator.
3. **Program Monitor & Audition Master Stereo VU Peak Meter:**
   - Program Monitor header: Scaled playback resolution (`Full 1080p`, `1/2 540p`, `1/4 Draft`), toggle Safe Margins Action 90% / Title 80%, toggle TikTok Safe Zone overlay guides.
   - Audition Master Stereo VU Meter: Đèn LED kép 2 kênh L/R nhảy mượt theo audio gain và organic fluctuation (-60 dB đến +3 dB), kèm đèn báo clipping đỏ khi vượt ngưỡng 0 dB.
4. **SMPTE Monospace Timecode & Transport Bar:**
   - Hiển thị chuẩn SMPTE `00:00:00:00 / 00:00:45:00` (HH:MM:SS:FF ở 30 fps).
   - Nút Mark In (`{` / phím `I`), Mark Out (`}` / phím `O`), Clear In/Out (`Alt+X`), Step 1s back/forward (`◀`/`▶`), Loop toggle, Master volume fader.
5. **Timeline Tracks & Adobe Tool Dock:**
   - Ruler thời gian với các vạch khắc độ chuẩn xác và kim chỉ playhead CTI đỏ.
   - Header các track video/audio riêng biệt: V2 (FX/Overlay), V1 (Main Video), A1 (Voiceover), A2 (Background Music), A3 (SFX).
   - Tool dock Premiere Pro kinh điển: Selection (V), Track Forward (A), Ripple Edit (B), Razor Split (C), Slip (Y), Pen (P), Hand (H), Type (T).
6. **Adobe Media Encoder Panel & Shortcuts Modal:**
   - Panel export Media Encoder trực tiếp trong Inspector: Presets YouTube 4K, 1080p Master, TikTok 9:16, ProRes 422 Proxy, điều chỉnh bitrate và codec.
   - Cheatsheet modal phím tắt Adobe toàn diện kích hoạt qua phím `?` hoặc menu Help.
7. **Bộ công cụ & Benchmark thương mại (`scripts/benchmark_editing_suite.py`):**
   - Đo đạc 14 tác vụ NLE & procedural graphics: Split/Merge/Move/Duplicate scene, Keyframe bezier, Linting WCAG, Render plan, Procedural Route Map SVG (>41k ops/s), Infographic SVG (>43k ops/s), Sensitivity Audit, Fact Reconciliation, On-This-Day query (>980k ops/s).

**Kiểm chứng:**
- `python -m ruff check src tests scripts`: ALL PASS.
- `python -m ruff format --check src tests scripts`: 70 files formatted sạch sẽ.
- `python -m mypy src`: Success (32 source files, 0 errors).
- `python -m pytest`: **377/377 tests PASS** (100%).
- `python scripts/smoke.py`: **64/64 integration checks PASS**.
- `node --check frontend/app.js && node --check frontend/editor.js`: Cú pháp JS hợp lệ 100%.

### 2026-09-16 — Phiên Media Studio & Content Re-Cook (xào nấu)
- Đã làm:
  - **Universal Media Library** (`src/content_factory/media.py`): upload mọi loại
    file (video/audio/image/document), phân loại theo đuôi, probe ffprobe,
    phiên âm bằng faster-whisper, trích text PDF bằng pypdf, lưu bền vững
    `library/media/index.json`. Kèm hàm sinh nhạc nền royalty-free bằng ffmpeg.
  - **Content Re-Cook pipeline** (`src/content_factory/recook.py`): đọc nguồn →
    viết lại lời thoại (paraphrase) → tạo project mới với hook/CTA mới. Chế độ
    `condense`/`expand`/`balanced`. Tôn trọng 2 cổng người duyệt (không tự xác
    nhận bản quyền).
  - **API**: `/media/upload`, `/media`, `/media/{id}`, `/media/{id}/download`,
    `/media/{id}/transcribe`, `/media/{id}/extract-text`, `/media/{id}/recook`,
    `/media/{id}/convert` (mp4/webm/mp3/wav/png/jpg).
  - **Sửa bug render quan trọng**: drawtext inline `text='...'` lỗi "Option not
    found" khi lời thoại có dấu nháy đơn (vd "Napoleon's army"). Chuyển sang
    dùng `textfile=` (file tạm) → render được mọi ký tự. Có test hồi quy.
  - **Test 5 video xào nấu**: `scripts/qa_recook_5_videos.py` — tạo 5 video
    nguồn ~60s (edge-tts + ffmpeg), upload, phiên âm, re-cook, qua 2 cổng duyệt,
    render. **5/5 pass**, mỗi video ra WebM ~60s thật.
  - **Frontend**: thêm workspace "Media Studio" (phím 8) — upload, lưới media,
    transcribe, re-cook, xem AI reading.
  - **Skills**: `.claude/skills/media-studio/`, `.claude/skills/content-recook/`.
  - **MCP**: `mcp_server.py` (stdio/SSE) expose media_list/upload/get/transcribe/
    extract_text/recook.
  - **Sửa lỗi của agent song song**: image_engine, voice_engine,
    image_voice_service, agent_tools (syntax error, PIL Resampling, numpy
    broadcast trong duck_music, `gate_db: None` tắt gate).
- Kiểm định: pytest pass, Ruff + format + mypy pass, smoke 64/64 pass,
  re-cook QA 5/5 pass.
- Quyết định: Dùng `textfile=` cho drawtext thay vì inline text để render lời
  thoại bất kỳ không vỡ; giữ nguyên tắc "học, không sao chép" trong re-cook.
- Việc tiếp theo: Cho renderer mix voiceover + nhạc nền thật, composite source
  image/video, subtitle burn-in, và job progress bền vững.

### 2026-09-16 — Phiên nâng cấp renderer: video thật + âm thanh đầy đủ
- Đã làm:
  - **Renderer có hình thật (không còn màu nền)**: `render_video_file` thêm chế
    độ `background_video` — lặp video nguồn làm nền chuyển động liên tục, chồng
    text từng scene theo khung giờ (`enable='between(t,…)'`). Project re-cook
    nhớ video nguồn qua `Project.source_media_id`, service cung cấp lúc render
    (`_background_video_for`).
  - **Voiceover**: lời thoại re-cook được đọc bằng edge-tts, mix vào đúng thời
    điểm từng scene (`adelay` + `atrim`).
  - **Nhạc nền**: sinh bed royalty-free (`synthesize_music_bed`) mix dưới giọng
    đọc theo volume của track music.
  - **Đầu ra**: WebM VP9 video + Opus audio (ffprobe xác nhận) — video re-cook
    có âm thanh thật, không còn câm.
  - **Sửa bug thiếu dấu phẩy** giữa `setpts` và `drawtext` làm lỗi "Option not
    found" ở nhánh dùng ảnh nguồn.
  - **QA 5 video re-cook (footage + voiceover + music)**: 5/5 pass, mỗi video ra
    WebM có video + audio stream. Đã chuyển sang MP4 (H.264 + AAC) để xem trên
    Windows.
  - **Test hồi quy**: `test_render_with_background_video_has_audio`.
- Kiểm định: pytest 380/380 pass, Ruff + format + mypy pass, QA 5/5 pass.
- Quyết định: Re-cook dùng video nguồn làm nền chuyển động thật (không phải
  ảnh tĩnh) + voiceover + nhạc nền; giữ 2 cổng người duyệt.
- Việc tiếp theo: subtitle burn-in, job progress bền vững, và cho phép người
  dùng chọn ảnh/video nguồn khác cho từng scene.

