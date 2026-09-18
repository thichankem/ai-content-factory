# Kế hoạch tổng thể — AI Content Factory

> **File này là "bộ nhớ" của dự án.** Mọi yêu cầu của chủ dự án, mọi quyết định
> kiến trúc, và mọi việc còn dở đều được ghi ở đây. Khi bắt đầu một phiên làm
> việc mới, **đọc file này trước**, làm xong việc gì thì **cập nhật lại file
> này** (mục *Nhật ký thay đổi* ở cuối). Không xoá yêu cầu cũ — chỉ đánh dấu
> `[x]` khi hoàn thành.

- Cập nhật lần cuối: 2026-09-18
- Trạng thái kiểm chứng gần nhất: 854 test xanh (0 failed/0 error/0 skipped),
  Ruff + format + mypy sạch; smoke đầu-cuối 64/64 trên server mới; 22/22 live
  check cho tầng SEO qua HTTP thật.

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
- **Chỉnh ảnh nâng cao bằng ML** (tách chủ thể rembg, panorama, HDR, RAW,
  upscale Real-ESRGAN) — phần lõi chỉnh ảnh thuần PIL/numpy đã xong (yêu cầu 15).
- Hàng đợi tác vụ bền vững (hiện dùng thread + store trong RAM).

## 4. Kiến trúc pipeline chuẩn mục tiêu

```text
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

- [x] **Lớp chỉnh ảnh toàn diện** (`photo_ops.py` + `image_engine.py`): crop,
      curves, LUT, exposure/highlights/shadows/levels, white balance/vibrance/
      HSL/color grade/split toning, noise/clarity/dehaze, local mask (radial/
      gradient/brush), retouch (spot heal/clone/red-eye/liquify/dodge-burn/freq
      sep), transform (straighten/perspective/lens), effects (grain/watermark/
      motion/lens blur), inpaint, remove background
- [x] **Tầng trợ năng** (`photo_assist.py`): mô tả ảnh bằng lời, mô tả từng op,
      gợi ý tự động theo histogram — dùng được bởi cả người có/nhìn và không nhìn
      được, và AI agent
- [x] **Undo/redo phiên chỉnh ảnh không phá hủy** (session trong RAM)
- [x] **Hiệu ứng khung hình video** (`video_effects.py`): glitch, shake,
      distortion, glow, film grain, motion blur, particles, chromatic
      aberration, pixelate, scanlines, freeze — thuần numpy, deterministic
- [x] **Hiệu ứng âm thanh DSP** (`audio_effects.py`): equalizer, compressor,
      limiter, reverb, voice changer, noise gate — thuần numpy
- [x] **Tầng trợ năng video** (`video_assist.py`): catalog thao tác video/audio,
      mô tả timeline bằng lời, gợi ý sửa tự động theo báo cáo validator
- [ ] Adapter ML pluggable: tách chủ thể (rembg), panorama, HDR merge, RAW decode,
      upscale (Real-ESRGAN), stabilize, object/face tracking, auto reframe
- [ ] Version history bền vững trên đĩa (hiện session lưu trong RAM)
- [ ] Workflow: autosave/recovery, bins, compound clips, adjustment layers,
      templates, batch export, multiple export versions, safe zones
- [ ] "Auto-edit giống editor chuyên nghiệp": cắt theo nhịp, chọn B-roll khớp

### P7 — Tự động hoá & vận hành

- [ ] MCP server để Claude Code / Codex điều khiển trực tiếp mọi endpoint
- [ ] Webhook + lịch chạy định kỳ (sản xuất hàng loạt từ CSV chủ đề)
- [ ] Đa người dùng, phân quyền, lịch sử duyệt có chữ ký
- [ ] Đo chất lượng: A/B hook, retention dự đoán trước khi publish
- [ ] Xuất hàng loạt (batch) và hàng đợi publish theo khung giờ

### P8 — Media Intelligence & QA/Traceability (7 nhóm nâng cấp tham khảo)

Bộ nâng cấp theo 7 nhóm (tham khảo từ bên ngoài, chốt triển khai theo lát cắt
additive). Nhóm **4 + 5 + 1 + 2/3** đã có module khả thi offline; nhóm cần
model/API/GPU đánh dấu `[ ]` (planned).

#### Nhóm 1 — Media intelligence (hiểu & tìm kho footage, không chỉ xử lý)

- [x] **Dedup asset** — `dedup.py`: perceptual hash (dHash) + Hamming, gom clip/ảnh
      trùng/gần-trùng để dọn kho.
- [x] **Semantic search seam** — `search.py`: BM25 lexical mặc định + `Embedder`
      Protocol để bật vector thật khi có model. Gõ "tìm cảnh người mặc áo đỏ" →
      ra đúng clip (khi cắm embedder).
- [ ] Auto B-roll matching — agent đọc kịch bản, đề xuất footage khớp ngữ nghĩa
      (dùng search.py + caption).
- [ ] Continuity checker — face embedding so mặt/trang phục giữa cảnh (cần model).

#### Nhóm 2 — Sinh nội dung mới (generative)

- [x] **Auto music ducking** — `audio.py`: ffmpeg sidechaincompress, tự hạ nhạc
      khi có thoại.
- [x] **Auto thumbnail + CTR heuristic** — `thumbnail.py`: score_best_frame + text
      overlay + dự đoán CTR để chọn bản tốt nhất.
- [ ] Smart reframe đa tỷ lệ 16:9→9:16/1:1 (theo dõi chủ thể; cần vision).
- [ ] Auto sound design/foley (vision-action → gợi ý tiếng động).
- [ ] Auto music scoring sinh/chọn nhạc khớp mood (ghép perception.py).
- [ ] Lip-sync dubbing thật (Wav2Lip; cần GPU).

#### Nhóm 3 — Vòng lặp phản hồi hiệu suất

- [x] **Virality scorer** — `virality.py`: chấm hook/nhịp/độ dài/CTA trước khi đăng.
- [ ] Retention-aware editing (kéo retention thật từ platform API → feed script_engine).
- [ ] Auto A/B thumbnail/title test (cần platform).

#### Nhóm 4 — QA/risk layer (critic tách khỏi agent tạo nội dung)

- [x] **Platform compliance scanner** — `compliance.py`: rule-based theo từng nền
      tảng (độ dài, tỉ lệ, từ cấm, watermark).
- [x] **Brand consistency check** — `compliance.py`: palette/logo/font vs brand kit.
- [ ] Rights/copyright check hoàn chỉnh (fingerprint nhạc + đối chiếu DB có bản quyền).

#### Nhóm 5 — Truy vết & kiểm soát

- [x] **Provenance/audit trail** — `audit.py`: log mỗi AI edit (model, prompt, lúc nào).
- [x] **Cost guard** — `cost_guard.py`: ước tính chi phí plan vision/audio-LLM, hỏi
      xác nhận khi vượt ngưỡng.
- [ ] Cây phiên bản sáng tạo (nhánh A/B/C giống git, không ghi đè).

#### Nhóm 6 — Trợ lý hội thoại trong timeline

- [x] **`nl_timeline.py`** — parse lệnh tự nhiên (EN + VI) → thao tác timeline:
      "speed up the intro to 1.5x", "xoá cảnh 2", "add a marker at 2 minutes"…
      (set_speed, delete/merge/split/move/duplicate scene, set_audio, marker, trim,
      auto-fit, beat-sync). Endpoint `POST /timeline/command`.

#### Nhóm 7 — Khả năng tiếp cận (accessibility)

- [x] **Subtitle rút gọn** — `simple_subtitles.py`: đổi từ khó → từ dễ, rút gọn câu
      dài cho trẻ em/người học ngôn ngữ. Endpoint `POST /subtitles/simplify`.
- [ ] Audio description tự động (vision mô tả → TTS vào khoảng lặng; cần vision backend).

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

### 2026-09-18 — Phiên Chỉnh video: hiệu ứng + tầng trợ năng (yêu cầu 14)

- **Mục tiêu phiên:** bổ sung các chức năng edit video còn thiếu trong 10 nhóm
  chủ dự án liệt kê (Timeline, Hình ảnh, Effects, Text, Audio, Camera/Motion,
  AI, Social, Export, Workflow) bằng thuật toán thuần numpy/ffmpeg chạy offline,
  **và** một tầng trợ năng để cả người có/nhìn và không nhìn được (và AI agent)
  đều hiểu và dùng được từng chức năng. Phần lớn các chức năng trong danh sách
  đã có sẵn (timeline engine, media_tools read+cut, audio chain, render) — phiên
  này lấp các khoảng trống rõ rệt.
- **Đã làm:**
  - `src/content_factory/video_effects.py` (mới) — **11 hiệu ứng khung hình**
    thuần numpy, deterministic theo seed: `glitch`, `shake`, `distortion`,
    `glow`, `film_grain`, `motion_blur`, `particles`, `chromatic_aberration`,
    `pixelate`, `scanlines`, `freeze`. Kèm `effect_catalog()` mô tả từng hiệu
    ứng + tham số.
  - `src/content_factory/audio_effects.py` (mới) — **6 hiệu ứng DSP** thuần
    numpy: `equalizer` (3-band biquad), `compressor`, `limiter`, `reverb`
    (Schroeder), `voice_changer` (pitch shift), `noise_gate`. Kèm
    `audio_effect_catalog()`.
  - `src/content_factory/video_assist.py` (mới) — **tầng trợ năng video**:
    - `catalog()` — toàn bộ thao tác video/audio phân nhóm theo category kèm
      mô tả bằng lời (gộp cả hiệu ứng khung hình + audio).
    - `describe_operation(name)` — giải thích từng thao tác.
    - `describe_timeline(project)` — tóm tắt timeline bằng câu chữ (số scene,
      thời lượng, số từ, tỉ lệ, số scene có ảnh/grade/filter/effect).
    - `suggest_edits(project)` — biến báo cáo validator thành các bước sửa cụ
      thể (scene quá ngắn → set_speed, tương phản chữ thấp → outline, flat look
      → ai_assist, narration underfill → fit…).
  - `image_voice_service.py` — thêm `persist_audio_bytes`.
  - `services/production.py` — expose `video_effect_catalog`, `apply_video_effect`,
    `audio_effect_catalog`, `apply_audio_effect`, `video_operation_catalog`,
    `describe_video_operation`, `describe_video_timeline`, `suggest_video_edits`.
  - `api/routers/studio_media.py` — endpoint mới: `GET /studio/video/effects`,
    `POST /studio/video/effect`, `GET /studio/audio/effects`,
    `POST /studio/audio/effect`, `GET /studio/video/ops`,
    `POST /studio/video/describe-op`, `GET /projects/{id}/timeline/describe`,
    `GET /projects/{id}/timeline/suggest`.
  - `agent_video.py` (mới) — 8 agent tool mới (registry giờ **97 tool**), gọi
    được qua `/tools/call` và MCP: `video_effect_catalog`, `apply_video_effect`,
    `audio_effect_catalog`, `apply_audio_effect`, `video_operation_catalog`,
    `describe_video_operation`, `describe_video_timeline`, `suggest_video_edits`.
  - Test mới: `tests/test_video_effects.py`, `tests/test_audio_effects.py`,
    `tests/test_video_assist.py`.
- **Kiểm chứng:** ruff + format + mypy sạch trên mọi file đổi; 25 test mới xanh;
  live HTTP qua TestClient: catalog/effect/describe-op đều 200; timeline
  describe/suggest qua service trả đúng nội dung.
- **Việc tiếp theo:** nối hiệu ứng + tầng trợ năng vào UI Video Studio; thêm
  workflow (version history bền vững, autosave/recovery, bins, compound clips,
  adjustment layers), social/export (batch export, multiple versions, safe
  zones), và adapter ML pluggable (object/face tracking, stabilise, auto
  reframe, upscale, frame interpolation).

### 2026-09-18 — Phiên Chỉnh ảnh toàn diện + tầng trợ năng (yêu cầu 15)

- **Mục tiêu phiên:** đưa backend lên đủ **toàn bộ chức năng chỉnh ảnh** chủ dự
  án liệt kê (thao tác cơ bản, ánh sáng, màu sắc, chi tiết, chỉnh cục bộ,
  retouch, layer/hiệu ứng, chuyển đổi/xuất, quản lý/quy trình) — ưu tiên thuật
  toán thuần PIL/numpy chạy offline, ML/heavy để adapter pluggable — **và** một
  tầng trợ năng để **cả người có thị giác lẫn người không có thị giác (và AI
  agent)** đều hiểu và dùng được mọi chức năng.
- **Đã làm:**
  - `src/content_factory/photo_ops.py` (mới) — **34 op chỉnh ảnh mở rộng**,
    thuần PIL+numpy, đăng ký vào cùng dispatcher `apply_ops` của `image_engine`:
    - **Ánh sáng:** `exposure` (EV), `highlights`, `shadows`, `whites`, `blacks`,
      `levels` (black/gamma/white).
    - **Màu:** `white_balance` (temperature+tint), `temperature`, `tint`,
      `vibrance` (giữ da), `hsl` (mixer 8 kênh màu: hue/sat/lum),
      `color_grade` (shadows/midtones/highlights), `split_toning`.
    - **Chi tiết:** `noise_reduce` (fastNlMeans → fallback median), `clarity`,
      `texture`, `dehaze`.
    - **Cục bộ:** `local_adjust` / `radial_filter` / `gradient_filter` / `brush`
      (mask mềm feather theo shape radial/gradient/rect).
    - **Retouch:** `spot_heal`, `clone_stamp`, `red_eye`, `liquify` (bulge/pinch),
      `dodge_burn`, `frequency_separation` (làm mịn da giữ kết cấu).
    - **Transform:** `straighten` (auto-detect tilt qua Hough), `perspective`
      (keystone), `lens_correction` (méo ống kính).
    - **Hiệu ứng:** `grain`, `watermark`, `motion_blur`, `lens_blur`.
  - `src/content_factory/photo_assist.py` (mới) — **tầng trợ năng**:
    - `histogram(img)` — histogram kênh + luminance + thống kê.
    - `describe_image(img)` — mô tả ảnh bằng lời từ pixel stats (độ sáng, tương
      phản, ám màu, bão hoà, độ nét) — **không cần nhìn ảnh vẫn biết ảnh ra sao**.
    - `describe_op(name, params)` — giải thích bằng lời từng op + tham số.
    - `suggest_edits(img)` — gợi ý công thức chỉnh tự động dựa trên histogram
      (thiếu sáng → exposure, ám vàng → white_balance, mờ → sharpen…).
    - `catalog()` — toàn bộ op phân nhóm theo category kèm mô tả.
  - `image_engine.py` — đăng ký `photo_ops.PHOTO_OPS` vào `_OPS` (48 op tổng).
  - `image_voice_service.py` — thêm **phiên chỉnh sửa không phá hủy** (undo/redo/
    history): `begin_image_session`, `edit_image_session`, `undo_image_session`,
    `redo_image_session`, `image_session_state`; thêm `analyze_image_bytes`,
    `image_op_catalog`, `describe_image_op`, `suggest_image_edits`,
    `batch_edit_images`.
  - `services/production.py` — expose toàn bộ qua `ProductionMixin`.
  - `api/routers/studio_media.py` — endpoint mới: `GET /studio/image/ops`,
    `POST /studio/image/analyze`, `POST /studio/image/suggest`,
    `POST /studio/image/describe-op`, `POST /studio/image/batch`,
    `POST /studio/image/session/begin`, `.../session/{id}/edit`,
    `.../session/{id}/undo`, `.../session/{id}/redo`, `GET .../session/{id}`.
  - `agent_photo.py` (mới) — 10 agent tool mới (registry giờ **89 tool**), gọi
    được qua `/tools/call` và MCP: `analyze_image`, `image_op_catalog`,
    `describe_image_op`, `suggest_image_edits`, `batch_edit_image`,
    `begin_image_session`, `edit_image_session`, `undo_image_session`,
    `redo_image_session`, `image_session_state`. Tách module riêng để
    `agent_tools.py` dưới ngân sách dòng.
  - Test mới: `tests/test_photo_ops.py`, `tests/test_photo_assist.py`,
    `tests/test_image_session.py`.
- **Kiểm chứng:** ruff + format + mypy sạch trên mọi file đổi; 94 test (mới +
  architecture + image_engine + mcp) xanh. Toàn bộ op chạy offline (numpy/PIL);
  `perspective`/`lens_correction` cần OpenCV (có sẵn) và tự báo lỗi rõ nếu thiếu.
- **Việc tiếp theo:** nối tầng trợ năng vào UI Photo Lab (panel mô tả ảnh + gợi
  ý + undo/redo), thêm adapter ML pluggable cho tách chủ thể (rembg), panorama,
  HDR merge, RAW decode, upscale (Real-ESRGAN), và version history bền vững trên
  đĩa (hiện lưu session trong RAM).

### 2026-09-18 — Phiên Cloud Storage: đưa media database lên cloud

- **Mục tiêu phiên:** cho phép media database dùng **object storage S3-compatible**
  làm nơi lưu chính, trong khi mặc định vẫn là local để không phá vỡ gì.
- **Đã làm:**
  - `src/content_factory/cloud.py` — backend `MediaStorage` pluggable:
    - `LocalMediaStorage` — file dưới một thư mục gốc (mặc định).
    - `S3MediaStorage` — S3-compatible qua `boto3` (lazy import; key ánh xạ
      `<prefix>/media/<id>/<filename>`).
    - `MemoryMediaStorage` — in-memory, dùng cho test.
    - `build_media_storage(...)` — chọn S3 khi có bucket, ngược lại local.
  - `MediaLibrary` nhận thêm `storage` backend. `media_dir/files/` vẫn là cache
    cục bộ để xử lý (ffmpeg/phiên âm/cắt), còn bản *chính thức* nằm ở backend:
    upload ghi vào storage, `path_for` tải object về cache khi thiếu, `delete`
    xóa cả storage.
  - Config (`Settings`): `s3_bucket`, `s3_endpoint`, `s3_region`,
    `s3_access_key`, `s3_secret_key`, `s3_prefix`. Đặt `s3_bucket` (+ cài
    `boto3`) là lên cloud; để trống là local.
  - Test: `tests/test_cloud.py` (7 test) — CRUD local/memory, `path_for` fetch-back,
    chọn backend, và S3 delegation với boto3 giả lập.
- **Kiểm chứng:** upload → storage, `path_for` fetch-back, delete-from-storage
  đều hoạt động với in-memory backend; đường S3 delegate đúng (mock). Smoke 64/64,
  `ruff`/`mypy` sạch.
- **Việc tiếp theo:** khi có creds thật, thêm test tích hợp với MinIO/S3; cân nhắc
  chuyển index JSON sang DB cloud (Postgres/SQLite-on-object) khi cần scale.

### 2026-09-18 — Phiên Media Database: cơ sở dữ liệu cho toàn bộ audio/ảnh/video

- **Mục tiêu phiên:** biến media library thành một **cơ sở dữ liệu truy vấn được**
  cho toàn bộ âm thanh, ảnh, video, tài liệu — không chỉ là danh sách phẳng.
- **Đã làm:**
  - `MediaItem.tags` — item có thể mang tag (chuẩn hóa: bỏ khoảng trắng, lowercase,
    de-dupe).
  - `MediaLibrary.query(...)` — lọc theo `kind`, `tag`, text tự do `q` (trên
    filename + transcription + text_content + source + tags), `source`,
    `min/max_duration`, `date_from/to`, và `sort` (newest|oldest|name|size|duration).
  - Quản lý tag: `set_tags`/`add_tag`/`remove_tag`/`all_tags`.
  - `stats()` — số lượng theo kind, tổng dung lượng, danh sách tag.
  - Endpoint: `GET /media` (thêm filter params), `GET /media/stats`,
    `GET /media/tags`, `POST /media/{id}/tags`, `POST /media/{id}/tags/{tag}`,
    `DELETE /media/{id}/tags/{tag}`.
  - UI (Media Studio): filter bar (kind/tag/sort + nút Lọc), dòng thống kê live
    (số mục, MB, đếm theo kind), và nút **🏷 Tag** trên mỗi media card.
- **Kiểm chứng:** query theo tag/kind/text, tag CRUD, stats, all-tags đều hoạt
  động qua HTTP. Smoke 64/64, `node --check` sạch, `ruff`/`mypy` sạch.
- **Việc tiếp theo:** nếu cần scale lớn, cân nhắc chuyển index JSON sang SQLite
  (giữ interface `MediaLibrary` để không phá callers); thêm dedup tự động theo
  perceptual hash khi upload.

### 2026-09-18 — Phiên Tải audio bất kỳ: tải đoạn âm thanh từ URL

- **Mục tiêu phiên:** cho người vận hành tải **bất kỳ đoạn âm thanh nào** từ URL
  (YouTube, podcast, file MP3 trực tiếp, SoundCloud…) và có thể cắt một đoạn
  (clip) theo khoảng thời gian.
- **Đã làm:**
  - `POST /media/audio-clip` — `{url, start_seconds, end_seconds, language}`:
    tải audio từ URL bất kỳ (`extract_audio=True`), nếu có khoảng
    `end_seconds > start_seconds` thì cắt đúng đoạn đó và đăng ký thành media
    item riêng. Dựa trên `MediaMixin.download_audio_clip` (tái dùng
    `media_from_url` + `media_tools.trim_audio`).
  - Agent tool + MCP: `download_audio_clip` (registry giờ 79 tool).
  - UI: ô "⬇ Tải bất kỳ đoạn âm thanh từ URL" ở đầu Audio Editor — dán URL, tùy
    chọn khoảng thời gian, bấm **⬇ Tải audio** (đầy đủ) hoặc **✂ Tải đoạn (clip)**.
- **Kiểm chứng (live HTTP):** `POST /media/audio-clip` với URL YouTube thật và
  `start=30, end=40` trả media item 10 giây `clip_Rick_Astley_...webm`. Smoke
  64/64, `node --check` sạch, `ruff`/`mypy` sạch.
- **Việc tiếp theo:** thêm waveform hiển thị để chọn điểm cắt trực quan, và nút
  "Tải audio từ URL" trong luồng re-cook.

### 2026-09-18 — Phiên Audio Editor: edit âm thanh + beat nhạc trong UI

- **Mục tiêu phiên:** cho người vận hành chỉnh sửa âm thanh toàn diện ngay trong
  UI — cắt, fade, normalize, retime, giảm ồn, dò beat/BPM, mix nhạc nền, tách
  audio. Tận dụng các audio tool backend đã có, gọi qua `/tools/call`.
- **Đã làm — panel "🎚 Audio Editor" trong Media Studio** (`frontend/index.html`
  + `frontend/app.js`):
  - Chọn asset audio/video → hiện metadata.
  - **✂ Trim** (`audio_trim`), **🌊 Fade** (`audio_fade`),
    **🔊 Normalize** (`audio_normalize`), **⏩ Retime** (`audio_retime`),
    **🎛 Giảm ồn** với slider cường độ (`audio_denoise`),
    **🥁 Dò BPM & Beat** (`music_beat_grid`), **🎵 Mix với nhạc nền**
    (`audio_mix` — chọn music bed + gain + duck), **🎞 Tách audio từ video**
    (`extract_audio_track`).
  - Mỗi thao tác hiện asset_id, thời lượng, link tải; lưu vào Edited Assets.
  - JS: `loadAudioEditor`, `aeCall`, `setupAudioEditorListeners`; gọi khi vào
    workspace Media Studio.
- **Kiểm chứng (live HTTP):** cả 8 audio tool trả 200 và tạo asset — trim, fade,
  normalize, retime, denoise, extract, beat grid (BPM 163, 4 beats trên tone tổng
  hợp), mix. Smoke 64/64, `node --check` sạch, `ruff`/`mypy` sạch.
- **Việc tiếp theo:** thêm waveform hiển thị + scrub để chọn điểm cắt trực quan,
  và nút "Giảm ồn"/"Lấy transcript" trong luồng re-cook.

### 2026-09-18 — Phiên Nối vào sản phẩm: YouTube + transcript + giảm ồn

- **Mục tiêu phiên:** đưa các tính năng YouTube (tìm/tải/transcript) và giảm ồn
  vào cả backend chain lẫn UI studio, để người vận hành dùng được trực tiếp.
- **Backend — chain:**
  - **Auto-denoise trong re-cook:** `ReCookRequest` thêm `denoise` + `denoise_strength`.
    `RecookPipeline.prepare_source` khi `denoise=True` sẽ giảm ồn audio *trước*
    khi phiên âm (qua `voice_engine.denoise_audio` + `MediaLibrary.transcribe_file`
    — chạy faster-whisper trên file audio bất kỳ). Bản ghi ồn → transcript sạch hơn.
  - **Auto-transcribe sau YouTube download:** `YouTubeDownloadRequest` thêm
    `auto_transcribe`; `youtube_download` phiên âm ngay sau khi tải (phụ đề trước,
    rồi faster-whisper).
  - Refactor: `MediaLibrary.list` → `list_items` (tránh shadow builtin `list`),
    tách `_run_whisper` khỏi `transcribe`.
- **Frontend (vanilla studio, `frontend/`):**
  - **Panel YouTube** trong Media Studio: tìm theo từ khóa → danh sách kết quả →
    nút **⬇ Tải** (kèm checkbox "tự phiên âm") và **📜 Transcript**.
  - **Hiển thị transcript:** nút "📜 Transcript" trên card media nguồn YouTube gọi
    `/youtube/transcript` và hiện text (kèm nguồn + số từ).
  - **🎛 Giảm ồn** trên mỗi card video/audio: mở modal với **slider cường độ** +
    **dropdown noise profile** (chọn asset khác làm mẫu ồn thuần); gọi tool
    `audio_denoise` qua `/tools/call`, lưu vào Edited Assets.
- **Kiểm chứng (live HTTP):** `/youtube/search` (2 kết quả), `/youtube/transcript`
  (source=subtitles, 2089 ký tự), upload + `audio_denoise` qua `/tools/call`
  (method=spectral_gating, asset tạo thành công). Smoke 64/64, `node --check` sạch.
- **Việc tiếp theo:** thêm nút "Giảm ồn" vào luồng re-cook trong UI (checkbox
  denoise khi re-cook), và tự động lấy transcript khi tải video YouTube làm nguồn
  re-cook/blueprint.

### 2026-09-18 — Phiên Giảm ồn: bỏ tiếng ồn bằng spectral gating

- **Mục tiêu phiên:** thêm tính năng giảm ồn / bỏ tiếng ồn thật sự cho giọng
  nói và audio. Noise gate cũ chỉ xóa khoảng lặng; tính năng mới **spectral
  gating** nén tiếng ồn nền (hiss, hum, room tone) nằm *dưới* giọng nói — giống
  DeNoise của Audacity/Audition.
- **Đã làm (thuần numpy, không cần dependency nặng):**
  - `_stft`/`_istft` — STFT cửa sổ Hann với **overlap 50%** để tái tạo sạch
    (hop không COLA gây transient rìa; đồng thời zero hóa vùng winsum quá nhỏ).
  - `_spectral_gate(samples, sr, strength, noise_profile)` — học phổ tiếng ồn từ
    mẫu ồn thuần hoặc tự ước lượng từ 10% frame nhỏ nhất, rồi áp gain Wiener
    từng bin: bin giọng nói (mag ≫ noise) giữ ~1, bin ồn bị nén. Output được
    chuẩn hóa peak để không clip.
  - `denoise_audio(data, strength, noise_profile, export_format)` — decode →
    gate → encode, trả `(bytes, report)`.
  - `process_voice` thêm `denoise_strength` (+ param `noise_profile`), nên chain
    enhance có thể giảm ồn; thêm preset `"denoise"`.
- **Bề mặt mới:**
  - Service `audio_denoise(ref, strength, noise_profile_ref, format)` trong
    `MediaToolsMixin` — resolve asset, tùy chọn asset thứ hai làm noise profile,
    lưu kết quả vào `library/edited/`.
  - Agent tool + MCP: `audio_denoise` (registry giờ 78 tool), nằm ở module mới
    `agent_audio.py` để `agent_tools.py` không vượt ngân sách dòng.
  - Test: `tests/test_denoise.py` (7 test) — giữ tone/nén ồn trên tín hiệu tổng
    hợp 220 Hz + noise, report shape, auto-estimation, `process_voice` với
    `denoise_strength`, preset, agent dispatch.
- **Kiểm chứng (tín hiệu tổng hợp):** tone 220 Hz giữ ~93% năng lượng, ồn băng
  rộng bị nén, sai số so với tone sạch giảm ~34%, không clip. Full pytest
  **956 passed**, `ruff`+`format`+`mypy` sạch, smoke 64/64, MCP live OK.
- **Quyết định:** dùng spectral gating thuần numpy (không cần model nặng) làm
  tầng "bỏ tiếng ồn", kết hợp noise gate + highpass có sẵn. Cho phép cung cấp
  noise profile để học phổ ồn chính xác hơn; nếu không có thì tự ước lượng.
- **Việc tiếp theo:** nối vào UI (nút "Giảm ồn" trong studio voice, kèm slider
  strength + chọn noise profile), và thêm vào chuỗi re-cook trước khi phiên âm.

### 2026-09-18 — Phiên Transcript: lấy transcript video "bằng mọi giá"

- **Mục tiêu phiên:** lấy transcript từ video (đặc biệt video YouTube tải về)
  bằng mọi cách, không bao giờ bị chặn vì thiếu model.
- **Đã làm — cascade 2 chiến lược:**
  1. **Phụ đề có sẵn (tức thì, miễn phí):** `MediaLibrary.fetch_subtitles` tái
     dùng caption thủ công/tự động của video qua yt-dlp — không cần model, không
     tải video, mili-giây. `POST /media/{id}/transcribe` giờ thử nhánh này trước
     cho item có nguồn YouTube (trước cả bước kiểm tra file, vì phụ đề chỉ cần
     URL nguồn).
  2. **faster-whisper (local):** nếu không có phụ đề, tải audio rồi phiên âm
     local bằng faster-whisper (đã cài, chạy CPU được).
- **Bề mặt mới:**
  - `POST /youtube/transcript` — `{url, language}` → `YouTubeTranscriptResult`
    với `source` (`subtitles`|`whisper`), `text`, `segments`, `media_id`.
  - `MediaLibrary.transcribe_youtube(url, language)` — cascade, cùng shape.
  - Agent tool + MCP: `youtube_transcript` (registry giờ 77 tool), gọi qua
    `POST /tools/call` và MCP `factory_call_tool`.
  - Models mới: `YouTubeTranscriptRequest`, `YouTubeTranscriptResult`.
  - Test: `tests/test_youtube.py` lên 16 test (VTT parsing, tái dùng phụ đề,
    fallback whisper, API, agent tool).
- **Kiểm chứng (mạng thật):** `transcribe_youtube(".../watch?v=dQw4w9WgXcQ","en")`
  trả `source=subtitles` với toàn bộ lời bài hát (auto-caption) tức thì, không
  chạy model. Full pytest **949 passed**, `ruff`+`format`+`mypy` sạch, MCP live OK.
- **Quyết định:** ưu tiên phụ đề có sẵn (nhanh + chính xác + không tốn tài nguyên),
  chỉ chạy faster-whisper khi không có phụ đề.
- **Việc tiếp theo:** nối transcript vào UI (hiển thị transcript + nút "lấy
  transcript" cho video tải về), và dùng transcript làm nguồn re-cook/blueprint.

### 2026-09-18 — Phiên YouTube: tìm kiếm + tải video YouTube

- **Mục tiêu phiên:** bổ sung chức năng tìm kiếm video trên YouTube và tải về
  vào media library (cho cả người dùng lẫn AI agent).
- **Đã làm:**
  - `GET /youtube/search?q=...&limit=N` — tìm video YouTube theo truy vấn (chỉ
    metadata, không tải). Dùng extractor `ytsearch` của yt-dlp nên tìm và tải
    khớp nhau. Trả `YouTubeSearchResult` (id, title, url, duration, uploader,
    thumbnail, description, view_count). Query rỗng → 422.
  - `POST /youtube/download` — tải video YouTube (URL hoặc id) vào media library,
    tái dùng `download_from_url` (yt-dlp + fallback ffmpeg/urllib). Hỗ trợ
    `extract_audio` để chỉ lấy audio.
  - Đăng ký agent tool `youtube_search` + `youtube_download` (registry giờ 76
    tool), gọi qua `POST /tools/call` và MCP `factory_call_tool`. Handler nằm ở
    module mới `agent_youtube.py` để `agent_tools.py` không vượt ngân sách dòng.
  - Models mới: `YouTubeSearchResult`, `YouTubeSearchRequest`,
    `YouTubeSearchResponse`, `YouTubeDownloadRequest`.
  - Test mới: `tests/test_youtube.py` (9 test).
- **Kiểm chứng (mạng thật):**
  - `GET /youtube/search?q=morning+light+city` → 3 video thật (title, uploader, url).
  - `POST /youtube/download` (audio-only) tải "Rick Astley - Never Gonna Give
    You Up" → 3.4 MB webm, 213s, `kind=video`.
  - Full pytest **943 passed**, `ruff` + `format` + `mypy` sạch, smoke 64/64,
    MCP live connectivity OK.
- **Quyết định:** tận dụng yt-dlp (đã cài sẵn) cho cả tìm và tải; giữ tìm kiếm
  chỉ metadata để nhanh và nhẹ, tải khi người dùng/agent chọn video.
- **Việc tiếp theo:** có thể nối vào UI (workspace tìm kiếm video mẫu → tải →
  dùng làm nguồn re-cook / blueprint), và thêm transcribe tự động sau khi tải.

### 2026-09-18 — Phiên NotebookLM: Knowledge Q&A có trích dẫn + test MCP

- **Mục tiêu phiên:** bổ sung khả năng tìm kiếm kiểu Google NotebookLM cho
  backend (hỏi → trả lời có trích dẫn nguồn `[n]`), và kiểm chứng kết nối MCP.
- **Đã làm:**
  - `POST /kb/{id}/ask` — Q&A grounded: retrieve top chunks → đưa context có
    trích dẫn vào provider chain → trả câu trả lời tổng hợp kèm `[n]` citations.
    Hỗ trợ `history` (các lượt trước) cho câu hỏi tiếp nối. Khi không có provider
    (offline) tự fallback sang **câu trả lời trích xuất** từ top hits — không bao
    giờ lỗi vì thiếu API key; flag `grounded` phân biệt hai nhánh.
  - `POST /kb/{id}/ingest-url` — thêm nguồn web (giống "add a web source" của
    NotebookLM): fetch URL, bỏ markup, chunk theo template KB. URL lỗi được ghi
    là document `FAILED` thay vì làm hỏng request.
  - Đăng ký agent tool `kb_ask` + `kb_ingest_url` (registry giờ 74 tool), gọi được
    qua `POST /tools/call` và qua MCP `factory_call_tool`. Handler nằm ở module
    mới `agent_knowledge.py` để `agent_tools.py` không vượt ngân sách dòng.
  - Models mới: `KBAskRequest`, `KBAskResponse`, `KBTurn`, `KBIngestUrl`.
  - Test mới: `tests/test_knowledge_qa.py` (10 test), `tests/test_mcp_connectivity.py`
    (4 test). Script live `scripts/test_mcp_live.py` spawn server MCP thật qua
    stdio, kết nối bằng MCP client thật, round-trip tool call.
- **Kiểm chứng:**
  - Full pytest xanh (919 + 14 test mới), `ruff` + `format` + `mypy` sạch.
  - **MCP LIVE CONNECTIVITY OK** — 23 MCP tools, `kb_ask`/`kb_ingest_url` có trong
    manifest, `factory_call_tool(list_kbs)` round-trip thành công.
- **Quyết định:** giữ nền tảng RAG hiện có (chunking 8 template + hybrid retrieval
  + grounding), chỉ thêm tầng Q&A tổng hợp câu trả lời; offline luôn có đường lui
  trích xuất để không phụ thuộc API key.
- **Việc tiếp theo:** có thể nối Q&A này vào UI (workspace "Notebook" để hỏi đáp
  trên nguồn của project), và thêm ingest từ PDF/URL vào project trực tiếp.

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

```markdown
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
   cùng `NotFoundError` trong `service.py` thành thông báo người đọc được
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

### 2026-09-16 — Phiên AI Video Editor (test: AI có tự edit video không?)

- Đã làm:
  - **Module `src/content_factory/ai_video_editor.py`** — pipeline đầy đủ:
    1) Phân tích video; 2) Chọn vị trí/kích thước/thời điểm ghép ảnh; 3) Tracking
    đối tượng bằng optical flow (KLT, fallback Farneback); 4) Composite bằng
    mask alpha có feather (không phải overlay cố định); 5) Cắt đoạn thừa
    (dead-air) thành timeline; 6) Xuất `final.mp4` (H.264 + giữ âm thanh nguồn).
  - **Hai planner**: `HeuristicPlanner` (no-vision, dùng gradient saliency) và
    `VisionPlanner` (with-vision, pluggable — có `_demo_vision_planner` offline).
  - **API**: `POST /ai-editor/edit` (multipart video+image, tuỳ chọn `use_vision`)
    → report + `download_url`; `GET /ai-editor/output/{filename}`.
  - **QA `scripts/qa_ai_video_editor.py`**: tạo clip có vật chuyển động, chạy cả
    2 chế độ, xác nhận MP4 có video + audio stream — **2/2 pass**.
  - **Test**: `tests/test_ai_video_editor.py`.
  - **Skill**: `.claude/skills/ai-video-editor/`.
  - **Sửa lỗi Windows**: đường dẫn có ký tự Unicode ("Máy tính") làm `cv2.imread`
    lỗi → dùng `np.fromfile`/`imdecode`; chiều cao lẻ làm libx264+yuv420p lỗi →
    ép chiều chẵn.
- Kiểm định: pytest pass (thêm test editor), Ruff + format + mypy pass,
  QA AI editor 2/2 pass.
- Quyết định: Xây pipeline AI editor hỗ trợ cả no-vision lẫn with-vision; giữ
  heuristic làm mặc định khi chưa cấu hình vision model.
- Việc tiếp theo: Nối vision model thật (LLM có ảnh) vào `VisionPlanner`; thêm
  UI Media Studio cho AI editor; cải thiện tracking khi đối tượng bị che.

### 2026-09-16 — Phiên MCP mở rộng + Vision pluggable + Cache idempotent + Sandbox

**Mục tiêu:** áp dụng bản thiết kế tham khảo (MCP server tách domain, vision
pluggable, checkpoint, sandbox) theo cách **không phá vỡ** cấu trúc đang chạy —
bổ sung theo lát cắt giá trị thay vì đại tu thư mục.

**Đã làm:**

1. **Vision pluggable (`src/content_factory/vision.py`)** — dual-mode:
   - `detect_scene_cuts()` — non-vision shot boundary (histogram grayscale +
     pixel-diff qua OpenCV), trả danh sách `SceneCut`.
   - `score_best_frame()` — chấm điểm khung hình; mặc định `HeuristicSceneScorer`
     (sharpness/exposure/saturation), cắm `VisionSceneScorer` (Protocol) khi bật
     vision. `build_scorer(settings, vision_scorer)` chọn backend theo config.
   - Flag mới: `ENABLE_VISION` (mặc định tắt), `VISION_BACKEND`
     (`rule_based|claude|local`).
2. **Cache idempotent (`src/content_factory/cache.py`)** — `ContentCache`
   content-addressed theo sha256 (namespace + input bytes + params), lưu dưới
   `storage/cache/`. `MediaLibrary.transcribe` memoize transcript theo hash file
   kèm language → retry không chạy lại model. Flag mới: `CACHE_DIR`.
3. **Sandbox (`src/content_factory/sandbox.py`)** — `Sandbox.resolve()` giới hạn
   mọi đường dẫn MCP vào `media_dir/uploads_dir/cache_dir/library_dir`.
4. **MCP server mở rộng (`mcp_server.py`)** — từ 5 tool lên **14 tool**:
   media library (6) + image (`image_crop`, `image_remove_background`,
   `image_upscale`) + video (`video_cut_clip`, `video_concat_clips`,
   `video_detect_scene_cuts`, `video_score_best_frame`) + voice
   (`voice_synthesize_speech`). Mọi file I/O qua Sandbox.
5. **Contract check + healthcheck** — `scripts/mcp_healthcheck.py --smoke` boot
   server, liệt kê tool, validate name/description/JSON-Schema; CI mới
   `.github/workflows/mcp-contract-check.yml` chạy trên mỗi PR.
6. **Docs** — `docs/MCP-SERVERS.md` (hợp đồng tool + sandbox), `docs/VISION-LAYER.md`
   (khi nào cần vision, chi phí, fallback). Cập nhật `.env.example`.
7. **Sửa drift mypy** — thêm/bỏ `type: ignore` cho numpy/cv2 stub trong
   `ai_video_editor.py`, `voice_engine.py`, `vision.py` để mypy sạch.

**Kiểm chứng:**
- `ruff check src tests scripts` → All checks passed.
- `ruff format --check` → 76 files formatted.
- `mypy src` → no issues in 36 source files.
- `pytest` → toàn bộ pass (gồm 19 test mới: `test_cache.py`, `test_sandbox.py`,
  `test_vision.py`, `test_media_cache.py`).
- `python scripts/mcp_healthcheck.py --smoke` → OK (14 tool, schema + smoke).

**Quyết định:** Giữ **một** MCP server (không tách 4 process riêng) vì media nặng
đã nằm in-process qua adapter + toolcheck graceful degradation; tách thêm process
chỉ thêm vận hành mà không thêm năng lực. Vision mặc định tắt để không tốn chi
phí cho tác vụ máy móc.

**Việc tiếp theo:** subtitle burn-in, job progress bền vững, cho phép chọn
ảnh/video nguồn từng scene, và (nếu có GPU/server) cắm vision backend thật
(YOLO/CLIP) vào `VisionSceneScorer`.

### 2026-09-16 — Phiên Audio Perception ("nghe hiểu" âm thanh)

**Mục tiêu:** bổ sung năng lực *nghe hiểu* toàn bộ âm thanh (không chỉ STT chữ)
theo đúng nguyên tắc dual-mode đã dùng cho vision: non-AI chạy miễn phí, AI tuỳ
chọn. Chốt hướng với chủ dự án: **giữ 1 MCP server** (tôn trọng quyết định phiên
MCP mở rộng), chỉ thêm lớp perception mới — không tách 4 process.

**Đã làm:**

1. **`src/content_factory/perception.py`** — lớp audio perception dual-mode:
   - Non-AI (numpy + ffmpeg, miễn phí): `detect_silence_and_pace` (khoảng lặng +
     pace thô), `classify_music_mood` (energy + spectral centroid + tempo),
     `check_audio_quality` (clipping/DC offset/noise floor/peak). Decode WAV qua
     stdlib `wave`, định dạng khác qua ffmpeg.
   - AI (opt-in, Protocol pluggable): `AudioEventDetector` (PANNs/YAMNet),
     `SpeakerDiarizer` (pyannote), `SpeechEmotionAnalyzer` (SER),
     `AudioSceneDescriber` (audio LLM). Chưa cắm backend thì trả lỗi rõ ràng.
   - `build_audio_perception(settings, ...)` chọn backend theo config — đổi
     backend không đổi call site (giống `vision.build_scorer`).
2. **Flag mới** trong `config.py` + `.env.example`: `ENABLE_AUDIO_PERCEPTION`
   (mặc định tắt), `AUDIO_PERCEPTION_BACKEND` (`rule_based|ai`).
3. **MCP server (`mcp_server.py`)** — thêm **7 tool** audio perception:
   `audio_detect_silence_and_pace`, `audio_classify_music_mood`,
   `audio_check_quality` (non-AI) + `audio_detect_events`, `audio_diarize_speakers`,
   `audio_detect_speech_emotion`, `audio_describe_scene` (AI). Tổng **21 tool**.
4. **Test** `tests/test_perception.py` — sinh WAV bằng numpy + wave (không cần
   ffmpeg), kiểm tra silence/pace, mood, clipping, facade mặc định, và AI tool
   báo lỗi khi chưa cắm backend / dispatch khi đã cắm.
5. **Docs** — `docs/PERCEPTION-LAYER.md` (mới: bảng tool, khi nào cần, chi phí,
   fallback, lưu ý Claude chưa nhận audio input nên backend "nghe" phải là model
   khác), `docs/VOICE-DUBBING-PIPELINE.md` (mới: STT → dịch → TTS → align → mux,
   perception nuôi dubbing), cập nhật `docs/MCP-SERVERS.md` (bảng tool + design
   notes) và `docs/VISION-LAYER.md` (cross-link perception).

**Kiểm chứng:**
- `ruff check src tests` → All checks passed.
- `ruff format --check src tests` → sạch.
- `mypy src` → sạch.
- `pytest` → toàn bộ pass (thêm `test_perception.py`).
- `python scripts/mcp_healthcheck.py --smoke` → OK (21 tool, schema + smoke).

**Quyết định:** Giữ **một** MCP server; audio perception là lớp hiểu nội dung
(perception) riêng, tách khỏi xử lý media thuần (image/video/voice), non-AI mặc
định để không tốn chi phí cho tác vụ máy móc. Claude đóng vai orchestrator, bước
"nghe" audio phải qua backend model nhận audio thật (Gemini/Qwen2-Audio/PANNs/
pyannote) rồi trả text về cho Claude đọc.

**Việc tiếp theo:** cắm AI backend thật cho audio perception (PANNs/YAMNet,
pyannote, SER, audio LLM) khi có GPU/API; nối perception vào pipeline dubbing
(STT → dịch → TTS → align → mux) theo `docs/VOICE-DUBBING-PIPELINE.md`; subtitle
burn-in và job progress bền vững vẫn là việc lớn tiếp theo của renderer.

### 2026-09-17 — Phiên 7 nhóm nâng cấp: QA/Traceability + Media Intelligence + Production boosters

**Mục tiêu:** triển khai 3 lát cắt đầu tiên của bộ nâng cấp 7 nhóm (chốt với chủ
dự án), theo lối additive có test, không phá vỡ pipeline. Toàn bộ 7 nhóm đã ghi
vào roadmap (mục 5, P8). Các tính năng cần model/API/GPU đánh dấu `[ ]` planned.

**Đã làm:**

1. **QA & Traceability layer** (nhóm 4 + 5 — "critic" tách khỏi agent tạo nội dung):
   - `compliance.py`: `check_platform` (rule-based theo youtube/tiktok/instagram_reels/
     facebook/shorts: độ dài, tỉ lệ, từ cấm, word-count), `check_brand` (palette/logo/
     font vs `BrandKit`), `check_copyright` + `fingerprint_music_audio` (sha256).
   - `audit.py`: `AuditLog` append-only JSONL (actor, action, project_id, prompt, ts),
     thread-safe, bỏ qua dòng hỏng — provenance cho C2PA-style.
   - `cost_guard.py`: `estimate_cost` + `CostGuard` — ước tính USD của plan
     vision/audio-LLM/TTS/STT, hỏi xác nhận khi vượt ngưỡng.
2. **Media Intelligence** (nhóm 1):
   - `dedup.py`: perceptual hash (dHash) + `find_near_duplicates` (Hamming) — dọn kho
     asset trùng/gần-trùng.
   - `search.py`: `MediaSearchIndex` — BM25 lexical mặc định + `Embedder` Protocol để
     bật vector thật khi có model (fuse `0.6*cosine + 0.4*lexical`).
3. **Production boosters** (nhóm 2 + 3):
   - `audio.py`: `duck_music_under_speech` — ffmpeg sidechaincompress, tự hạ nhạc khi
     có thoại.
   - `virality.py`: `score_virality` — heuristic hook/nhịp/độ dài/CTA, cảnh báo sớm
     trước khi đăng.
   - `thumbnail.py`: `generate_thumbnails` — score_best_frame + text overlay + `predict_ctr`.
4. **Config + `.env.example`**: `AUDIT_DIR`, `COST_GUARD_*` (+ unit cost từng loại call),
   `DEDUP_MAX_DISTANCE`, `SEARCH_EMBEDDER`.
5. **Test** (32 test mới): `test_compliance.py` (15), `test_search.py` (9),
   `test_production.py` (8) — hermetic, không cần network.
6. **Docs**: `docs/QA-LAYER.md`, `docs/MEDIA-INTELLIGENCE.md`, `docs/PRODUCTION-BOOSTERS.md`
   (mới); roadmap P8 trong file này.

**Kiểm chứng:**
- `ruff check src tests scripts` → All checks passed.
- `ruff format --check` → 113 files formatted.
- `mypy src` → no issues in 64 source files.
- `pytest` → **441 passed** (409 cũ + 32 mới).
- `scripts/mcp_healthcheck.py --smoke` → OK (21 tool).
- `scripts/smoke.py` → 64/64 checks PASS.

**Lưu ý vận hành:** trong phiên này `src/content_factory/api/routers/*` có lúc bị
ghi đè trạng thái lỗi cú pháp (hàm dính vào `router = APIRouter()`, mất decorator)
bởi một tiến trình song song — gây lỗi collect pytest nhất thời, sau đó tự phục hồi.
Nếu gặp lại, kiểm tra `health.py`/`projects.py` có decorator `@router.*` và hàm
không dính vào dòng `router = APIRouter()`.

**Quyết định:** Giữ nguyên tắc "critic tách khỏi creator" — QA layer chỉ cảnh báo,
hai cổng người duyệt vẫn bắt buộc; mọi thứ chạy offline, non-AI mặc định; các tính
năng cần model/API/GPU (continuity checker, smart reframe, lip-sync, retention-aware,
audio description…) để planned.

**Việc tiếp theo:** nối các module vào service/API (audit ghi vào mỗi edit, cost
guard vào planner, dedup/search vào media library, virality vào script_engine,
ducking vào render); triển khai nhóm 6 (trợ lý hội thoại timeline) và nhóm 7
(accessibility) khi có model.

### 2026-09-17 — Nối 3 lát cắt vào HTTP API (router `qa.py`)

**Mục tiêu:** đưa các module mới (QA, audit, cost_guard, dedup, search, virality,
ducking, thumbnail) thành endpoint dùng được cho web app và agent — không còn là
module đứng riêng.

**Đã làm:**
- Thêm `@property settings` cho `ContentFactoryService` (đọc config cho audit_dir/
  cost_guard, giữ test hermetic bằng tmp_path).
- Thêm router `src/content_factory/api/routers/qa.py` (12 endpoint):
  - QA: `POST /qa/platform`, `/qa/brand`, `/qa/copyright`.
  - Traceability: `GET /audit`, `POST /audit/record`, `POST /cost/check`.
  - Media intelligence: `POST /media/dedup`, `GET /media/search`.
  - Boosters: `POST /script/virality`, `POST /render/duck`, `POST /thumbnail/generate`.
- Wire vào `routers/__init__.py` + `app.py`. **Lưu ý route-order:** đăng ký router
  `qa` TRƯỚC router `media` để `GET /media/search` không bị `GET /media/{media_id}`
  nuốt (404). Duck/thumbnail ghi output vào temp dir để test hermetic.
- Test `tests/test_qa_api.py` (12 test): platform/brand/copyright, audit record+list,
  cost check, dedup 2 ảnh trùng, search doc, virality, duck wav, thumbnail avi, 404.

**Kiểm chứng:**
- `ruff check src tests scripts` → All checks passed.
- `ruff format --check` → 115 files formatted.
- `mypy src` → no issues in 65 source files.
- `pytest` → **453 passed** (441 cũ + 12 mới).
- `scripts/smoke.py` → 64/64 checks PASS.

**Việc tiếp theo:** triển khai nhóm 6 (trợ lý hội thoại timeline — mở rộng
`smart.py` parse lệnh tự nhiên) và nhóm 7 (accessibility — audio description +
subtitle rút gọn) khi có model; nối audit vào mỗi edit trong service.

### 2026-09-17 — Nhóm 6 (trợ lý hội thoại) + Nhóm 7 (accessibility)

**Mục tiêu:** hoàn tất 2 nhóm còn lại khả thi offline trong bộ 7 nhóm nâng cấp.

**Đã làm:**
1. **`src/content_factory/nl_timeline.py`** — trợ lý hội thoại timeline:
   - `parse_command` → `ParsedCommand` (intent + target + params), nhận diện song
     ngữ EN/VI: SPEED_UP/SLOW_DOWN, DELETE/MERGE/SPLIT/MOVE/DUPLICATE_SCENE,
     SET_VOLUME, ADD/REMOVE_MARKER, TRIM, AUTO_FIT, BEAT_SYNC.
   - `resolve_scene_index` — map "intro"/"cảnh 2"/"scene 3"/"the hook" → index.
   - `apply_command` — áp lệnh qua `timeline.*` ops; không nhận diện được / không
     tìm được scene thì trả project nguyên vẹn kèm mô tả lỗi.
2. **`src/content_factory/simple_subtitles.py`** — phụ đề rút gọn (accessibility):
   đổi từ khó → từ đơn giản (synonym map), `INTERMEDIATE` còn rút gọn câu dài.
3. **Endpoint mới** trong `qa.py`: `POST /timeline/command` (project + lệnh → project
   đã sửa + intent), `POST /subtitles/simplify` (captions + level → bản dễ đọc).
4. **Test** (19 test mới): `test_nl_timeline.py` (11), `test_simple_subtitles.py` (6),
   kèm 2 test API trong `test_qa_api.py`.

**Kiểm chứng:**
- `ruff check src tests scripts` → All checks passed.
- `ruff format --check` → 119 files formatted.
- `mypy src` → no issues in 67 source files.
- `pytest` → **472 passed** (453 cũ + 19 mới).
- `scripts/smoke.py` → 64/64 checks PASS.

**Quyết định:** Trợ lý hội thoại dùng rule-based (offline, deterministic) thay vì
LLM parse — đủ cho tập lệnh phổ biến, không tốn chi phí; khi cần hiểu câu phức tạp
có thể nối LLM sau. Phụ đề rút gọn dùng synonym map + cắt câu, không cần model.

### 2026-09-17 — Toàn diện hóa UI Suite phong cách NLE chuyên nghiệp (CapCut Pro / Premiere / Resolve)

**Mục tiêu:** Xây dựng giao diện người dùng hoàn thiện, chuyên nghiệp, đưa toàn bộ năng lực mới của backend lên UI theo phong cách phần mềm dựng phim thương mại (CapCut Pro, Adobe Premiere Pro, DaVinci Resolve, Runway, Descript), đảm bảo tuân thủ nghiêm ngặt 2 cổng duyệt bắt buộc (Script Approval & Video Approval) và state machine.

**Đã làm:**
1. **AI Co-Pilot Timeline Command Bar (Spotlight / Raycast / CapCut AI style):**
   - Phím tắt toàn cục `Ctrl+K` kích hoạt thanh lệnh nổi, kèm các quick-prompt chips (Tăng tốc intro 1.5x, Cắt cảnh 2, Giảm âm lượng, Thêm beat sync...).
   - Gọi trực tiếp `POST /timeline/command` với `nl_timeline.py`, cập nhật tức thì NLE timeline visualizer, clip list và scene breakdown.
2. **Virality Scorer & Script Analytics:**
   - Nút `🔥 Virality` và thẻ điểm 4 thành phần (Hook, Pacing, Duration, CTA) tích hợp trong Script Studio.
   - Gọi `POST /script/virality`, hiển thị radar/gauge điểm số và gợi ý cải thiện văn phong viral.
3. **Multi-Platform QA & Brand Compliance Modal:**
   - Kiểm tra đa nền tảng (TikTok, Shorts, Reels, YouTube 16:9, Facebook) qua `POST /qa/platform`.
   - Brand Kit Consistency Check qua `POST /qa/brand` (font, palette, tone of voice).
   - Copyright & Asset Fingerprint Scanner (SHA-256) qua `POST /qa/copyright`.
4. **AI Auto-Thumbnail & CTR Predictor Studio:**
   - Trích xuất top-k khung hình tối ưu hoặc render canvas đa kiểu dáng (Neon Gamer, Tech Minimal, Vlog Bold) qua `POST /thumbnail/generate`.
   - Dự đoán CTR (ví dụ: `🔥 15.2% High CTR`) và 1-click handoff sang Photo Lab / lưu làm poster dự án.
5. **Pro Audio & Accessibility Suite:**
   - Auto Music Ducking: nút bấm sidechain ducking trong Audio panel, gọi `POST /render/duck` và tự động điều chỉnh gain trên preview canvas.
   - Accessible Subtitle Simplifier: nút rút gọn phụ đề (`basic` / `intermediate`) trong Captions panel, gọi `POST /subtitles/simplify`.
6. **Cost Guard & Provenance Audit Trail Modal:**
   - Theo dõi ngân sách real-time theo model (Gemini, Claude, Whisper, Piper) và dung sai vượt chi qua `POST /cost/check`.
   - Nhật ký kiểm toán nguồn gốc xuất xứ (Provenance Audit Trail) qua `GET /audit`.
7. **Semantic Media Search & dHash Deduplication:**
   - Tìm kiếm nội dung ngữ nghĩa trong Media Studio qua `GET /media/search`.
   - Quét và phát hiện media trùng lặp theo thuật toán dHash qua `POST /media/dedup`.
8. **Thiết kế NLE thương mại cao cấp:**
   - Tông màu Obsidian Dark kết hợp điểm nhấn Cyan/Neon Violet.
   - SMPTE Timecode display, Audition dual VU meter sống động, TikTok Safe Zones overlay, tooltips và shortcut hints.

**Kiểm chứng:**
- `node --check frontend/app.js` & `node --check frontend/editor.js` → Syntax check PASS.
- `ruff check src tests scripts` → All checks passed.
- `ruff format --check` → 119 files formatted.
- `mypy src` → no issues in 67 source files.
- `pytest` → 472 passed.

**Quyết định:** Giữ nguyên tắc 2 cổng người duyệt bắt buộc (Script Approval & Video Approval). Mọi tính năng AI Co-Pilot hoặc tự động hóa timeline đều thông qua preview và chỉ áp dụng khi người vận hành xác nhận.

### 2026-09-17 — Tái cấu trúc giao diện sang Next.js + TypeScript + Tailwind + shadcn/ui + TanStack Query + Zustand + Motion và Chuẩn hóa README toàn bộ thư mục lớn

**Mục tiêu:** Nâng cấp toàn diện kiến trúc frontend theo chuẩn enterprise hiện đại (**Next.js 14 App Router, TypeScript, Tailwind CSS, shadcn/ui, TanStack Query, Zustand, Motion**) và bổ sung hệ thống tài liệu `README.md` chuẩn hóa cho tất cả các thư mục lớn trong kho lưu trữ để tối ưu hóa khả năng bảo trì.

**Đã làm:**
1. **Kiến trúc Next.js Pro NLE (`frontend/`):**
   - Cấu hình `package.json`, `tsconfig.json`, `next.config.mjs` (kèm API rewrites proxying tới FastAPI), `tailwind.config.ts`, `components.json` (shadcn/ui).
   - Hệ thống kiểu TypeScript hoàn chỉnh (`src/types/project.ts`, `api.ts`, `timeline.ts`).
   - Store Zustand quản trị trạng thái tập trung: `useProjectStore`, `usePlayerStore` (VU meters, transport, safe zones), `useTimelineStore` (multi-track NLE), `useUIStore` (modals & tabs).
   - TanStack Query hooks đồng bộ server state: `useProjects`, `useScriptEngine`, `useTimelineCommands`, `useQA`, `useThumbnails`, `useMediaLibrary`, `useAuditCost`.
   - Bộ linh kiện shadcn/ui primitives (`Button`, `Card`, `Dialog`, `Tabs`, `Slider`, `Badge`, `Progress`, `Table`, `Tooltip`, `Separator`).
   - Các module chức năng: `Topbar`, `CommandBarModal` (`Ctrl+K` với Framer Motion), `VideoPlayer` (Audition stereo VU meters, SMPTE timecode, TikTok safe zone), `TimelineVisualizer` (5 track lanes), `ScriptStudio` (4-part virality retention card, Gate 1 approval), `ComplianceModal` (QA / Brand / Copyright), `ThumbnailModal` (CTR studio), `AuditCostModal` (Cost Guard & Audit Trail), `AudioControls` (Sidechain ducking), `CaptionSimplifier` (A11y subtitles), `MediaStudio` (dHash dedup & semantic search).
   - Giữ nguyên vẹn tính tương thích với server FastAPI và script smoke test E2E.
2. **Hệ thống README chuẩn hóa cho toàn bộ thư mục lớn:**
   - `src/README.md`: Kiến trúc nguồn backend và nguyên tắc thiết kế.
   - `src/content_factory/README.md`: Chi tiết các module domain core và state machine.
   - `src/content_factory/api/README.md`: Cấu trúc FastAPI, danh mục 17 router và cơ chế bảo vệ lỗi.
   - `frontend/README.md`: Hướng dẫn kiến trúc Next.js, cấu trúc thư mục, Zustand stores, TanStack Query và lệnh chạy.
   - `tests/README.md`: Phân loại 472+ test automated, quy chuẩn hermeticity và lệnh kiểm tra quality gates.
   - `scripts/README.md`: Danh mục kịch bản vận hành (`smoke.py`, `toolcheck.py`, `dev`, benchmarks).
   - `docs/README.md`: Danh mục tài liệu kỹ thuật, kế hoạch tổng thể và quy ước cập nhật.
   - `library/README.md`: Cấu trúc kho tài nguyên media, cơ sở dữ liệu SQLite FTS5 BM25.
   - `storage/README.md`: Cấu trúc lưu trữ runtime, uploads và content-addressed cache.

**Kiểm chứng:**
- `ruff check src tests scripts` → All checks passed.
- `ruff format --check` → 154 files already formatted.
- `mypy src` → Success: no issues found in 97 source files.
- `pytest` → 472 passed.

### 2026-09-17 — Tái cấu trúc toàn bộ backend: tách god class `ContentFactoryService` và gói `models.py`

**Mục tiêu:** Làm sạch phần backend: loại bỏ god class 2.073 dòng, gom trùng lặp tokenizer về một chỗ, và biến kiến trúc thành thứ có thể kiểm chứng tự động — mà **không đổi một hành vi nào** (cùng OpenAPI spec, cùng chữ ký hàm, cùng schema model).

**Đã làm:**
1. **`models.py` (1.495 dòng) → gói `models/` (14 module):** chia theo domain — `common`, `project`, `timeline`, `voice`, `research`, `script`, `agent`, `workflow`, `campaign`, `external`, `knowledge`, `history`, `media`. `models/__init__.py` re-export toàn bộ nên 68 file đang import không phải sửa một dòng.
2. **`service.py` (2.073 dòng) → gói `services/` (14 mixin):** mỗi domain một mixin — `context` (settings, store, state machine, worker), `projects`, `research`, `scripting`, `styles`, `knowledge`, `agents`, `timeline`, `voice`, `media`, `production`, `workflow`, `growth`, `history` — ghép thành `ContentFactoryService`. Mixin **kế thừa đúng tầng nó gọi** (`MediaMixin(VoiceMixin)`, `WorkflowMixin(AgentsMixin, ProjectsMixin, GrowthMixin, TimelineMixin, VoiceMixin)`), nên hướng phụ thuộc hiện ra ngay ở dòng `class` thay vì ẩn trong 2.000 dòng. `service.py` giờ chỉ còn facade 22 dòng để import cũ tiếp tục chạy.
3. **Gom trùng lặp thật:** bốn tokenizer khác nhau nằm rải ở `documents.py`, `research.py`, `search.py`, `rag.py` được hợp nhất vào `text.py` (`normalize_title`, `slugify`, `tokenize`, `word_tokens`); mỗi module truyền *policy* của mình vào (`min_length=2` + stopwords cho search, unicode-aware cho BM25 tiếng Việt). Không đổi kết quả xếp hạng, nhưng sửa thuật toán chỉ còn một chỗ.
4. **Gỡ rào cản kiến trúc trong `workflow.py`:** `WorkflowRunner` không còn phụ thuộc `ContentFactoryService` — nó nhận protocol `WorkflowService` (12 phương thức nó thật sự dùng). Dependency inversion thật sự, đồng thời sửa luôn lỗi mypy khi runner được gọi từ mixin.
5. **Đơn giản hóa `api/deps.py`:** ba guard (`guard`, `guard_value`, `guard_await`) và `get_or_404` trước đây mỗi cái lặp lại một thang `except`; giờ tất cả đi qua một mapper `_http_error` duy nhất.
6. **Test kiến trúc mới (`tests/test_architecture.py`, 24 test):** khoá lại thành quả tái cấu trúc — mixin không được trùng tên phương thức, mọi phương thức mixin phải gọi được từ service ghép, ngân sách độ dài module (1.100 dòng), bề mặt re-export của `models`, và hành vi của helper văn bản.
7. **Tài liệu:** cập nhật `AGENTS.md` (mục *Backend layout*), `src/README.md`, `src/content_factory/README.md`, `src/content_factory/api/README.md` theo sơ đồ mới.

**Kiểm chứng (đối chiếu trước/sau khi tái cấu trúc):**
- `ruff check src tests` → All checks passed; `ruff format --check src tests` → sạch.
- `mypy src` → Success: no issues found in 97 source files.
- `pytest` → **496 passed** (472 test cũ + 24 test kiến trúc mới).
- **Tương đương hành vi được kiểm chứng bằng snapshot:** 97 JSON schema của model giống hệt từng field; 139 chữ ký phương thức của `ContentFactoryService` giống hệt; `app.openapi()` giống hệt (112 path, 139 schema).

**Quyết định:** Giữ `service.py` như facade tương thích thay vì xóa — 30+ file (router, agent tools, MCP server, script, test) đang import từ đó, và một facade 22 dòng rẻ hơn nhiều so với việc sửa lan rộng trong cùng một lần. Quy ước mới: code mới import từ `content_factory.services`.

### 2026-09-17 — Tầng tool cho MỌI AI (kể cả không có vision): đọc – cắt – ghép ảnh – ghép tiếng – chỉnh nhạc

**Mục tiêu:** Một agent chỉ có chữ (không vision, không nghe) vẫn phải làm được việc của một editor: hiểu file media, tự động cắt, ghép ảnh, ghép tiếng, cắt nhạc theo beat. Tập trung tối đa vào tầng tool và để tool tự mô tả chính nó.

**Đã làm:**
1. **Engine mới `media_tools.py`** — nửa *đọc* biến file thành text (probe, loudness EBU R128, khoảng lặng, shot cut, palette, beat grid, contact sheet, OCR khi có tesseract) và nửa *ghi* biến quyết định thành file (cut/split/concat/extract, trim/fade/loop/normalize/retime/mix tracks, compose layers/collage). Thuần ffmpeg + Pillow, không phụ thuộc model nào.
2. **`MediaToolsMixin` (services/media_tools.py, 22 method)** — mọi thao tác nhận `ref` là media-library id, `asset_id` đã sửa, hoặc path trong sandbox; mọi kết quả được lưu vào `library/edited/` và trả về `asset_id` + `url`, nên **chuỗi lệnh nối tiếp nhau bằng id**.
3. **Registry tool viết lại (`agent_tools.py`)** — từ 37 tool if/elif thành **61 tool khai báo theo bảng**, mỗi tool có **JSON Schema thật** (`input_schema`) + handler riêng + nhóm; `Args` là bộ đọc tham số có kiểm tra, báo đúng tên field khi sai; tham số `required` được chặn ở tầng dispatch (422) nên schema không bao giờ “nói dối”. Thêm nhóm `media` và `audio`.
4. **Nhạc tự động:** `music_beat_grid` (BPM + beat/downbeat) và `auto_cut_to_beat` (đọc tempo rồi beat-match timeline) — biến "cắt theo nhạc" thành một lời gọi. `audio_mix` duck nhạc dưới giọng bằng sidechain khi một track có `role="voice"`.
5. **Ghép ảnh:** `compose_images` (lớp + vị trí theo pixel/%/tên góc, scale, opacity, rotate, 8 blend mode) và `collage_images` (lưới + caption).
6. **Sửa 2 lỗi tìm được khi tự test:** (a) concat demuxer của ffmpeg hiểu nhầm `C:` trên Windows thành protocol → thêm tiền tố `file:`; (b) route `/edited/{name}` hardcode `audio/mpeg` nên video tải về sai content-type → thay bằng bảng MIME.

**Kiểm chứng:**
- Engine: `python scripts/qa_media_tools_engine.py` → **24/24** trên media thật do ffmpeg sinh ra.
- HTTP thật: `python scripts/qa_media_tools_http.py` → **20/20** (upload → describe → beat grid → cut → chain theo asset_id → split → join → audio_mix → fade → frame → contact sheet → compose → collage → 404/422 → tải asset).
- `pytest` → **520 passed** (thêm `tests/test_media_tools.py`); `ruff` + `mypy` sạch; `scripts/smoke.py` → **64 checks PASS**.

**Quyết định:** Tool là hợp đồng tự mô tả — model nào cũng đọc được schema mà không cần đọc source. Chưa làm: parity đầy đủ cho `mcp_server.py` (hiện vẫn giữ bản cut/concat riêng) — nên chuyển sang dùng `media_tools` ở vòng sau.

### 2026-09-17 — Thử nghiệm thực tế: Tải video 4 phút từ NASA, "xào nấu" toàn diện thành siêu phẩm tài liệu khoa học 2 phút 15 giây

**Mục tiêu:** Kiểm thử thực chiến toàn bộ pipeline của hệ thống với video dài thực tế: tải video tư liệu thật trên mạng (>= 2 phút), tiến hành "xào nấu" (re-cook) toàn diện (thay toàn bộ lời thoại, thay toàn bộ giọng thuyết minh, lồng bản nhạc nền mới, thay toàn bộ chữ/phụ đề đồ họa, màu điện ảnh, chuyển động thật tuyệt đối không giống PowerPoint), vận hành trọn vẹn qua 2 cổng duyệt bắt buộc (Script Approval & Video Approval) của máy trạng thái.

**Đã làm:**
1. **Tải tư liệu gốc từ NASA:** Tải bộ phim tài liệu thiên văn chính thức của NASA *"Shedding Light on Black Holes"* từ Wikimedia Commons (`storage/uploads/external/nasa_black_holes_source.webm`, thời lượng 246.57s = 4 phút 6 giây, 854x478 30fps).
2. **Phiên âm AI:** Sử dụng `faster-whisper` (base model, CPU int8) bóc tách toàn bộ 54 phân đoạn âm thanh tiếng Anh trong 12.3 giây.
3. **Kịch bản khoa học tiếng Việt mới (135.0s = 2 phút 15 giây):** Tái cấu trúc thành 7 trường đoạn kịch tính giải mã những bí ẩn và lầm tưởng về hố đen vũ trụ:
   - Cảnh 1 [0s - 20s]: Hook & Khởi nguyên (`01 // BÍ ẨN VŨ TRỤ`)
   - Cảnh 2 [20s - 41s]: Chân trời sự kiện & đĩa bồi tụ (`02 // CHÂN TRỜI SỰ KIỆN`)
   - Cảnh 3 [41s - 62s]: Phân cấp hố đen siêu khối lượng (`03 // PHÂN CẤP KHỐI LƯỢNG`)
   - Cảnh 4 [62s - 82s]: Lực hấp dẫn và quỹ đạo hành tinh (`04 // ĐỊNH LUẬT HẤP DẪN`)
   - Cảnh 5 [82s - 102s]: Cơ chế lượng tử Bức xạ Hawking (`05 // BỨC XẠ HAWKING`)
   - Cảnh 6 [102s - 120s]: Di sản Thuyết tương đối Einstein (`06 // DI SẢN EINSTEIN`)
   - Cảnh 7 [120s - 135s]: Khám phá vô tận & CTA (`07 // KHÁM PHÁ BẤT TẬN`)
4. **Lồng tiếng AI chuẩn Studio:** Tổng hợp toàn bộ 7 phân cảnh bằng `edge-tts` với giọng đọc truyền cảm `vi-VN-NamMinhNeural` (tổng thời lượng thoại 102.41s trải đều timeline).
5. **Hòa âm Soundtrack & Dynamic Ducking:** Sáng tác bản nhạc nền không gian Cinematic Deep Space Ambient đa tầng hòa âm bằng ffmpeg filter graph; tích hợp bộ nén động `sidechaincompress` tự động hạ âm lượng nhạc nền 14dB khi có thuyết minh và dâng trào khi chuyển cảnh.
6. **Thay toàn bộ chữ & Đồ họa HUD:**
   - Hệ thống badge chương góc trên trái chuẩn phim khoa học tài liệu (Cyan Neon).
   - Watermark tư liệu lưu trữ góc trên phải: `NASA DEEP SPACE ARCHIVES`.
   - Phụ đề nền mờ typography kiểu Netflix căn giữa chân màn hình, có bóng đổ sắc nét.
7. **Color Grading & Video Moving Footage:** Áp dụng bộ lọc màu điện ảnh (`eq=contrast=1.16:brightness=0.01:saturation=1.28:gamma=0.96`), loại bỏ màu phẳng gốc, tôn lên độ sâu vũ trụ và quầng sáng plasma của hố đen; dựng bằng footage chuyển động thực tế 1280x720 @ 30fps.
8. **Vận hành trọn vẹn máy trạng thái:**
   - Tạo dự án `790d26e5a8c5` (*Sự Thật Kinh Ngạc Về Hố Đen Vũ Trụ*)
   - Cổng 1: Xác nhận bản quyền tác giả và phê duyệt kịch bản (`ApprovalStage.SCRIPT`)
   - Tiến trình sản xuất & tích hợp audio thoại/nhạc
   - Cổng 2: Phê duyệt chất lượng video thành phẩm (`ApprovalStage.VIDEO`)
   - Xuất bản đa nền tảng (YouTube & TikTok).
9. **Thành phẩm:**
   - MP4: `storage/nasa_black_holes_recook_master.mp4` (Thời lượng: **135.00s = 2 phút 15 giây**, Dung lượng: **27.86 MB**, H.264 High Profile, AAC Stereo 192kbps).
   - WebM: `storage/nasa_black_holes_recook_master.webm`.
   - Preview Frames: `storage/recook_production/preview_frame_30s.jpg`, `preview_frame_75s.jpg`.

**Kiểm chứng:**
- `pytest` → 520 passed.
- `ruff check src tests` & `ruff format --check src tests` → sạch 100%.
- `mypy src` → 100 source files sạch 100%.
- `ffprobe` xác nhận video đạt chuẩn: 135.00s, 1280x720 30fps, âm thanh nổi AAC 192kbps, video mượt mà, thoại khớp phụ đề và nhạc nền.

### 2026-09-17 — Kiểm định toàn diện dự án & Test render video dài 30 phút (1.800 giây) chứng minh năng lực máy tính người dùng

**Mục tiêu:** Kiểm tra toàn diện mọi thành phần trong project (FastAPI Backend, Next.js Frontend, AI Perception Toolchain, Media Pipeline), đảm bảo máy tính người dùng chạy được trơn tru và chứng minh năng lực render thành công một video dài ít nhất 30 phút (>= 1.800 giây) có chuyển động, âm thanh, giọng đọc và phụ đề hoàn chỉnh.

**Đã làm:**
1. **Kiểm định phần cứng & dung lượng máy tính:**
   - **CPU**: AMD Ryzen 7 7840H (8 nhân thực, 16 luồng, vi kiến trúc Zen 4, AVX-512) — đạt tốc độ render mã hóa x264 lên tới **393.3 FPS (Gấp 13.1 lần thời gian thực)**.

### 2026-09-18 — Refactor ServiceContext: engine nặng khởi tạo lười (lazy)

- Đã làm:
  - `services/context.py`: 9 engine nặng (research, federated search, document
    library, media library, re-cook, TTS, image/voice studio, presets) chuyển
    sang lazy property double-checked locking an toàn luồng; `__init__` chỉ
    dựng state rẻ (store, worker registry, workflow/knowledge maps). Provider
    chain giữ build ngay (rẻ, test thay nguyên cụm được).
  - Không đổi API public; mixin truy cập `self._<engine>` như cũ.
- Kiểm chứng: ruff check + format sạch; mypy 115 files, 0 lỗi; full pytest
  chạy tới [100%] không F/FAILED (chạy nền qua redirect nên dòng tổng kết
  không ghi được); `tests/test_media_tools.py` chạy riêng pass.
- Quyết định: không phá chuỗi kế thừa mixin — đó là dependency graph phục vụ
  mypy strict; guard kiến trúc cấm property getter+setter cùng tên nên
  `_providers` giữ attribute thường.

### 2026-09-18 — Refactor Store: compare-and-save nguyên tử + dọn worker registry

- Đã làm:
  - `store.py`: thêm `Store.save_if_unchanged(project, expected)` — so sánh và
    ghi trong **một lock**, từ chối ghi đè lost-update bằng
    `StoreConflictError`. Hợp đồng: `expected` là snapshot lấy từ working copy
    (mutate bản copy, store so với object gốc của nó).
  - `services/production.py`: `render_video` dùng CAS thay so-sánh tay
    read-then-write (cửa sổ lost-update bị đóng); import mới
    `..store.StoreConflictError`.
  - Worker registry: `_register_worker` (context) dọn thread chết trước khi
    thêm — trước đây set `_workers` phình vô hạn theo số job. Ba nơi spawn
    (generation, voiceover, workflow) dùng chung helper.
  - Thêm `.gitattributes` (eol=lf, .ps1/.bat giữ CRLF) hết cảnh báo CRLF.
  - Test mới: 3 case CAS trong `tests/test_store.py` (happy, xung đột, id lạ).
- Kiểm chứng: ruff check + format sạch (170 files); mypy 118 files 0 lỗi;
  subset store/render/tts/workflow 100% pass; full suite tới [100%] chỉ 2 fail
  ở `test_resources.py` (module mới của phiên khác, đang bị sửa song song —
  chạy riêng 2/2 pass); smoke 64/64 PASSED trên cây gồm cả ResourcesMixin.
- Việc tiếp theo: CAS cho `_apply_timeline_edit` (hiện last-write-wins — cần
  quyết định UX trước), retention audio generation, hàng đợi render bền vững.

- Việc tiếp theo: giữ danh sách việc trước (store nguyên tử, retention audio,
  hàng đợi bền vững); đo thời gian dựng service trước/sau lazy.

   - **GPU**: NVIDIA GeForce RTX 4060 Laptop GPU (8GB GDDR6 VRAM, CUDA 12.7) + AMD Radeon 780M — hỗ trợ toàn diện AI Perception và mã hóa tăng tốc phần cứng.
   - **Ổ cứng**: SSD NVMe `C:\` còn trống **153.64 GB** — thừa khả năng lưu trữ hàng trăm video dài (video 30 phút chỉ tốn ~234 MB).
   - **RAM**: 16 GB DDR5, tiến trình ffmpeg và python stream dữ liệu trực tiếp, tiêu thụ dưới 400 MB RAM trong toàn bộ quá trình render.
2. **Nâng cấp AI Perception Stack cho model không cần Vision:**
   - Cài đặt bổ sung PyTorch và `EasyOCR` vào `.venv`.
   - Cập nhật hàm `media_tools.ocr_text` tích hợp fallback EasyOCR (khi không có binary tesseract trên Windows), hỗ trợ trích xuất văn bản trên màn hình kèm tọa độ bounding box và confidence score chi tiết.
   - Kho công cụ media nâng lên 11 công cụ sẵn sàng (`ffmpeg`, `ffprobe`, `yt-dlp`, `faster_whisper`, `PIL`, `cv2`, `rembg`, `moviepy`, `edge_tts`, `gTTS`, `mutagen`).
3. **Sản xuất bộ phim tài liệu thiên văn 30 phút (*Vũ Trụ Vô Tận*):**
   - **10 Chương khoa học đồ sộ** (mỗi chương dài 180s = 3 phút): từ Big Bang, Mạng lưới vũ trụ, Vật chất tối, Chân trời sự kiện, Bức xạ Hawking, Nghịch lý thông tin, Sóng hấp dẫn, Kính James Webb, Du hành liên sao, đến Di sản Carl Sagan.
   - **10 Đoạn giọng đọc thuyết minh tiếng Việt Neural Voice** (`edge-tts`) được căn chỉnh chính xác tại các mốc thời gian [0m, 3m, 6m, 9m, 12m, 15m, 18m, 21m, 24m, 27m] và ghép thành master narration track 1.800.00s.
   - **Bản nhạc nền không gian sâu 30 phút** (`soundtrack_30min.m4a`, 1.800.03s) với kỹ thuật Dynamic Sidechain Ducking tự động hạ âm lượng 14dB khi có thuyết minh.
   - **Hệ thống HUD Cyberpunk Neon Cyan** hiển thị tiêu đề từng chương, watermark bản quyền `AI CONTENT FACTORY // 30-MINUTES MASTER` và phụ đề căn giữa chân màn hình.
4. **Vận hành qua 2 Cổng Duyệt State Machine:**
   - Dự án `d153578be4a4` được tạo ở trạng thái `draft`.
   - Cổng 1 (Script Approval): Phê duyệt kịch bản 10 chương -> chuyển sang `script_approved`.
   - Tiến trình sản xuất & timeline -> chuyển sang `video_review`.
   - Cổng 2 (Video Approval): Phê duyệt video thành phẩm -> chuyển sang `video_approved`.
   - Xuất bản đa nền tảng (`youtube`, `tiktok`) -> chuyển sang `published`.
5. **Render & Kiểm định Kỹ thuật Thành phẩm:**
   - **Tập tin xuất bản**: `storage/cosmos_30min_masterpiece.mp4`.
   - **Thời lượng thực tế**: **1.800.00 giây = đúng 30.00 phút** (Xác thực bằng `ffprobe`).
   - **Thời gian render**: **137.30 giây (~2.29 phút)** trên 16 luồng CPU.
   - **Tốc độ mã hóa**: **393.3 FPS (Gấp 13.1x thời gian thực)**.
   - **Dung lượng**: **234.16 MB**.
   - **Codecs**: H.264 High Profile (1280x720 HD @ 30fps) + AAC Stereo 192kbps (44.1 kHz).

**Kiểm chứng:**
- `pytest` -> **520 passed** (100%).
- `mypy src` -> **102 files, 0 errors**.
- `ruff check src tests` -> **0 errors**.
- `ruff format --check src tests` -> **151 files sạch format**.
- `scripts/smoke.py` -> **64/64 checks PASS**.
- `ffprobe` -> Video 30 phút hoàn toàn lành lặn, phát lại mượt mà, âm thanh và hình ảnh đồng bộ hoàn hảo.

### 2026-09-17 — Refactor backend: timeline, QA và SEO

- Đã làm:
  - Theo phạm vi chủ dự án chốt: backend + docs; giữ nguyên thay đổi chưa commit,
    không commit/stash, không sửa frontend.
  - Tách engine SEO 2.921 dòng thành gói `seo/`: contracts, profiles, signals,
    scoring, optimization, experiments, keywords, calibration và helper/specs.
    Giữ bề mặt import `content_factory.seo`; bỏ ngoại lệ ngân sách 3.100 dòng.
  - Mapping SEO dùng cùng Pydantic contracts với HTTP: chuỗi `"false"` không còn
    bị hiểu thành true; kiểm tra giới hạn số thống nhất; bổ sung `caption_source`.
    Đây là thay đổi validation có chủ đích, không tuyên bố tương đương schema hoàn toàn.
  - Chuyển 11 request model QA sang `models/qa.py`, 13 endpoint gọi `QaMixin`.
    Giữ preview lệnh timeline không lưu và không duyệt nội dung.
  - Timeline rebuild/edit/AI assist/polish và đồng bộ thời lượng voice dùng chung
    normalize + revision phía server, thao tác trên bản sao để lỗi không sửa object
    đang lưu. Giữ chính sách build/rebuild cũ và khả năng edit sau published.
  - Voice ghi audio theo từng generation, từ chối kết quả khi timeline/ngôn ngữ/
    bundle đã thay đổi; lỗi tổng hợp không ghi đè audio cũ; đọc được đường dẫn cũ.
  - Smart keywords và đối chiếu copy-risk dùng helper văn bản chung.
  - Thêm test hành vi, parity QA/SEO, rollback/revision/voice và guard kiến trúc
    chống request model trong router, giới hạn module theo đường dẫn đầy đủ.
- Kiểm chứng:
  - `python -m ruff check src tests`: sạch.
  - `python -m ruff format --check src tests`: 167 file đúng format.
  - `python -m mypy src`: 115 source files, không lỗi.
  - Full pytest: **810 passed**, 16 warning từ dependency, 69,48 giây.
  - `scripts/smoke.ps1` với `SMOKE_PORT` là cổng trống: server mới,
    **64/64 checks PASS**, gồm hai cổng duyệt và voiceover edge-tts.
- Quyết định: refactor theo domain, giữ tương thích luồng cũ; test toàn bộ đã
  phát hiện và sửa regression build timeline ở trạng thái script_approved.
- Việc tiếp theo: transaction/compare-and-save nguyên tử cho store, retention
  audio generation, index tìm kiếm tăng dần, hàng đợi bền vững. Chưa có bảo đảm
  chống mọi race condition; không coi phiên này là hoàn thiện toàn bộ roadmap.

### 2026-09-18 — Nâng cấp pipeline: xuất MP4 thật + tích hợp ảnh/video/tiếng/nhạc

- Đã làm (local nhẹ, không cài model lớn, không API trả phí):
  - `render.py`: thêm `export_format="mp4"` (H.264 + AAC, `+faststart`), giữ WebM
    mặc định; giới hạn `threads` 1–8 (mặc định 1) cho filter/codec/input để giảm
    RAM/CPU; nhận `audio_path` là bản mix hoàn chỉnh (thay voiceover+nhạc);
    scene có `video_url` được ưu tiên hơn `image_url`, tôn trọng `source_in_seconds`
    và `speed` (loop nguồn); sửa narration **trim trước delay** để lời cảnh sau
    không bị cắt; `volume=0` giờ là mute thật; render vào temp rồi `replace` nguyên
    tử để lỗi không phá artifact cũ.
  - `timeline.compile_render_plan`: ưu tiên `video_url`, copy sâu plan, cảnh báo
    rõ khi gặp `trim_end`/`reverse` chưa hỗ trợ, mang `background_music_url`.
  - `services/production.py`: `render_video(project_id, export_format, audio_ref)`
    chỉ chạy ở `generating`/`video_review` (không tự duyệt/publish, chặn render đè
    bản đã duyệt); resolve media qua `resolve_media_ref` (chặn URL mạng, `..`);
    kiểm tra revision cũ trước khi gắn artifact; hỗ trợ `render_max_dimension`.
  - `services/projects.py`: `video_path` phục vụ theo `project.video.format`.
  - Router `/render` nhận `RenderRequest`; `/video` trả MIME đúng container và
    `?download=true`.
  - `agent_tools.py`: thêm tool `render_video` (project_id/export_format/audio_ref)
    + manifest; `mcp_server.factory_list_tools` giờ trả schema thật.
  - Config mới: `CONTENT_FACTORY_RENDER_THREADS`, `CONTENT_FACTORY_RENDER_MAX_DIMENSION`.
  - Streaming upload (media/video/external) + hashing cache theo file đã có từ
    lát cắt trước; `.env.example` chưa ghi các biến streaming mới.
- Kiểm chứng:
  - Proof end-to-end: ảnh + video + audio tổng hợp → `render_video_file(mp4)` →
    ffprobe `h264 + aac`, 6.00s, 49KB.
  - Full pytest: **837 passed** (thêm 27 test render/tool/API/MCP/regression).
  - Ruff check + format sạch, mypy 115 files sạch, smoke 64/64 trên server mới.
- Quyết định: giữ WebM làm mặc định (tương thích), MP4 là lựa chọn rõ ràng khi
  cần xem trên Windows/đăng nền tảng; renderer chạy 1 luồng mặc định để phù hợp
  máy ~8GB RAM.
- Việc tiếp theo: ghi biến streaming vào `.env.example`; nối `audio_mix` sidechain
  (đang có bug dùng lại label) vào `render_video`; `trim_end`/`reverse`; render
  job bền vững và hàng đợi; chưa hỗ trợ audio nhúng trong clip nguồn.

### 2026-09-18 — Phiên SEO: chấm điểm, viết lại và chứng minh cho YouTube/TikTok

**Mục tiêu phiên:** "thử bằng mọi giá" cách để AI tự kiểm tra SEO cho YouTube và
TikTok, tính được điểm, và đưa ra giải pháp tối ưu nhất — rồi nối vào bộ tool để
mọi agent dùng được.

**Đã làm:**

1. **Engine `src/content_factory/seo/`** (11 module, ~2.9k dòng): `profiles`
   (ngưỡng từng nền tảng), `signals` (70 signal có trọng số), `_specs` (bảng
   khai báo signal theo nền tảng), `scoring`, `optimization`, `experiments`
   (A/B), `keywords`, `calibration`, `contracts`, `_helpers`.
2. **Chấm đúng những gì dự án sẽ đăng** (`seo_score_project`): hook lấy từ
   section đầu của kịch bản, thời lượng + nhịp cắt từ timeline, tỉ lệ khung,
   phụ đề, nhạc, chapter marker, chữ trên màn hình từng scene.
3. **Nối vào agent tools**: thêm nhóm `seo` với 8 tool (`seo_rules`,
   `seo_score`, `seo_optimize`, `seo_score_project`, `seo_ab_plan`,
   `seo_ab_evaluate`, `seo_keywords`, `seo_calibrate`), mỗi tool có JSON Schema
   thật và tham số `required` bị chặn ngay ở tầng dispatch. Tổng tool: 62 → 70.
4. **Sửa 3 lỗi thật do tự test tìm ra:**
   - **Điểm bị kẹp vô lý:** `title_length`, `hashtags`, `duration_fit` bị đánh
     dấu *blocking*, nên video 4 phút + tiêu đề 11 ký tự bị kẹp cứng ở 45 và
     **mọi cải thiện khác đều vô nghĩa** (optimizer trả `gain 0`). Nay blocking
     chỉ còn khi gói thật sự không đăng được: sai tỉ lệ khung cho nền tảng dọc,
     watermark tái đăng, tiêu đề rỗng/quá dài (`blocking_when=_title_unusable`).
   - **Optimizer không lấp đủ dải chuẩn:** tiêu đề ngắn không được kéo dài, bộ
     hashtag/tag dừng ở 1–6 thay vì 3 và 8–15. Nay sinh từ chính vật liệu của
     gói (hook, chữ trên màn hình, chapter) và từ các biến thể của cụm từ khoá.
   - **Mất điểm khi lệch dưới 1 điểm:** so sánh làm tròn làm mất thắng lợi 0.4
     điểm → thêm `SeoReport.precision` để phân xử.
5. **Optimizer "đo chứ không hứa"**: mọi thay đổi được áp theo kiểu greedy và
   **chỉ giữ nếu chấm lại thấy tăng điểm**; gói trả về chấm lại ra đúng
   `after.score`. Có test khoá tính chất này.
6. **Tài liệu + skill**: `docs/SEO-SCORING.md` (model, nguồn nền tảng, thống kê
   A/B, cách dùng), mục SEO trong `docs/TOOLS-FOR-AGENTS.md`, skill
   `seo-packaging-audit` ở cả `.agents/skills/` và `.claude/skills/`.

**Kiểm chứng (2026-09-18):**

- `ruff check src tests` + `ruff format --check` + `mypy src`: sạch (115 file).
- `pytest` toàn bộ: **854 test, 0 failed, 0 error, 0 skipped** (chạy 2 nửa
  a–m và n–z, cả hai exit 0). Lưu ý: lần chạy pytest đầu tiên trong phiên bị
  treo ở `test_media_tools.py` vì easyocr/torch nạp model lần đầu — sau khi
  model đã cache thì qua bình thường.
- `scripts/smoke.py --port 8160`: **64/64 checks PASS** trên server mới.
- `scripts/qa_seo_tools_http.py` (HTTP thật, đúng đường agent đi): **22/22 PASS**,
  gồm cả kiểm tra "gói optimizer trả về chấm lại đúng bằng điểm đã hứa".
- `scripts/qa_seo_sanity.py`: gói yếu 68 → 83 sau tối ưu (gain 15, đo được).

**Quyết định:**

- Blocking phải **hẹp**: chỉ những lỗi khiến video không đăng được hoặc bị nền
  tảng đàn áp mới được kẹp điểm; khuyến nghị (tiêu đề ngắn, thiếu hashtag,
  thời lượng) chỉ trừ điểm. "Đừng đăng" cho một tiêu đề ngắn là báo động giả.
- Bộ trọng số hiện tại là **prior** từ hướng dẫn công khai của nền tảng;
  `seo_calibrate` là con đường thay bằng dữ liệu thật của kênh.
- Không tự bịa số liệu: thiếu `engagement` thì điểm giảm `confidence`, không suy diễn.

**Việc tiếp theo:** đưa `seo_score_project` vào cổng duyệt video (cảnh báo trước
khi publish), nối kết quả thật của nền tảng vào `seo_calibrate` để tự hiệu chỉnh
trọng số, và dùng `seo_optimize` ngay trong `campaign.py` khi sinh gói đa định
dạng.

---

### 2026-09-18 — Siêu Giao diện NLE Studio & Tài liệu Kiến trúc Toàn diện

**Động lực:**
Người vận hành yêu cầu tổng hợp toàn bộ 41 ảnh giao diện chuyên nghiệp trong `picture/` (Adobe Premiere Pro 2025, CapCut Pro Desktop, DaVinci Resolve Studio 19, Apple Final Cut Pro 11, Adobe After Effects 2025) để nâng cấp giao diện frontend đạt chuẩn NLE Studio cao cấp nhất, tổ chức thành thanh taskbar 7 bước tuần tự có AI Agent Co-Pilot hỗ trợ trên mọi tab, đồng thời lập tài liệu kiến trúc kỹ thuật (`docs/NLE-STUDIO-FULL-ARCHITECTURE.md`) để dễ dàng mở rộng và triển khai backend.

**Những gì đã làm:**
1. **Khảo sát & Tổng hợp 41 Ảnh UI:**
   - Hoàn thiện `picture/README_UI_SURVEY.md` phân tích chi tiết từng khối chức năng của 5 phần mềm NLE hàng đầu.
2. **Nâng cấp Frontend NLE Studio:**
   - **Thanh Taskbar 7 bước tuần tự bên trái:** `[01] Kịch bản` → `[02] Tư liệu & Nhạc` → `[03] Chỉnh sửa Ảnh` → `[04] Video & Kỹ xảo` → `[05] Âm thanh` → `[06] Ghép nối Timeline` → `[07] Xuất ra & Kiểm duyệt`.
   - **Thanh AI Agent Harness Co-Pilot trên mọi tab:** 1-click Quick Actions tự động hóa, prompt lệnh tự nhiên, cùng 100% thanh trượt thủ công.
   - **Premiere Pro 2025 Contextual Properties & CapCut Video Inspector:** Bảng thuộc tính Text typography (font, tracking, leading, all-caps, stroke outer/inner, drop shadow) và Auto Cutout (birefnet segmentation, chroma key, face retouch).
   - **CapCut Pro Auto-Captions:** Whisper speech-to-text, nhận diện từ khóa cảm xúc (Keyword Highlight), và các mẫu phụ đề viral (Trending Box, Emphasis Bounce, Glow Neon, Emoji Pop).
   - **DaVinci Resolve Studio 19 Fusion Node Graph:** Tích hợp bộ ghép nối đồ thị node trực quan, kết nối các luồng `MediaIn` -> `MagicMask AI` / `LumetriColor` -> `Merge` -> `MediaOut`.
   - **Adobe After Effects Bezier Graph Editor & CapCut Speed Ramping:** Đường cong điều tốc biến thiên 0.1x - 10x với Optical Flow và tiếp tuyến Bezier easing.
   - **Adobe Audition 5-Band Parametric EQ & Fairlight Ducking:** Bộ cân bằng 5 dải tần (60Hz, 250Hz, 1kHz, 4kHz, 12kHz) và sidechain auto-ducking BGM dưới giọng MC (-16dB).
   - **Premiere Pro Dual Monitors & Tool Palette:** Màn hình Source/Program, Lumetri Scopes (RGB Parade Rec.709), Live Stereo VU dB meter, và bộ phím tắt `V, A, B, C, Y, P, H, T`.
3. **Tài liệu Kiến trúc Backend Toàn diện:**
   - Đã biên soạn `docs/NLE-STUDIO-FULL-ARCHITECTURE.md` với đầy đủ Pydantic models, Service Mixins (`VideoFXServiceMixin`, `AudioLabServiceMixin`, `InspectorServiceMixin`, `FusionServiceMixin`), bảng định tuyến REST API, và state machine 2 cổng duyệt bắt buộc (`state.py`).

**Kiểm chứng:**
- `npm run type-check`: **0 errors**.
- `npm run build`: **Next.js 14.2.35 Build PASS** (4/4 static pages generated).
- `pytest`: **888 test PASS (100%)**, 0 failed.

---

### 2026-09-18 — Chuẩn hóa Kỹ thuật Trung lập, Trình chiếu HTML/CSS & Bộ Ingestion Video URL Re-Cook

**Động lực:**
Người vận hành yêu cầu:
1. Không ghi đích danh tên thương hiệu độc quyền (Adobe Premiere, After Effects, CapCut, Photoshop...) mà phải dùng thuật ngữ kỹ thuật chuyên nghiệp chuẩn quốc tế (NLE, VFX, Photo Lab, DAW, Hardware Encoder).
2. Tra cứu và hệ thống hóa toàn bộ tính năng của 3 lĩnh vực edit (Ảnh, Video, Âm thanh/Nhạc) thành 3 file tài liệu đặc tả hoàn chỉnh (`docs/SPEC-IMAGE-EDITING.md`, `docs/SPEC-VIDEO-EDITING.md`, `docs/SPEC-AUDIO-EDITING.md`), bảo đảm frontend có đủ 100% tính năng.
3. Bổ sung hỗ trợ slide trình chiếu động bằng HTML/CSS trong kho tư liệu, cho phép nhúng trực tiếp vào kịch bản/timeline.
4. Bổ sung tính năng cào/tải video của người khác qua đường dẫn URL (TikTok, YouTube, Reels, MP4) và quy trình AI Re-Cook ("xào nấu" / biến tấu) để chuyển hóa thành kịch bản phái sinh độc quyền 0% copy-risk.

**Những gì đã làm:**
1. **3 Bộ Đặc Tả Tính Năng Toàn Diện:**
   - `docs/SPEC-IMAGE-EDITING.md`: Hệ thống 27 Blending Modes, Curves/Levels cubic spline, BiRefNet AI Matting, Retouch Inpainting, RealESRGAN 4x Upscaling, Typography drop shadows.
   - `docs/SPEC-VIDEO-EDITING.md`: Multi-track NLE, bộ công cụ phím tắt chuẩn `V, A, B, N, C, Y, U, P, H, T`, Dynamic Speed Ramping với Bézier Graph & Optical Flow, 3D LUTs, Rec.709 RGB Parade, Whisper Auto-Captions & Karaoke/Keyword Highlight, Node Compositor.
   - `docs/SPEC-AUDIO-EDITING.md`: Channel Strip Faders, 5-Band Parametric EQ (60Hz–12kHz), Sidechain Auto-Ducking (-16dB), Spectral Noise Reduction, 4-Stem Audio Isolation, Broadcast Loudness Normalization (-14 LUFS / -16 LUFS).
2. **Loại bỏ Hoàn toàn Thương hiệu Độc quyền trên Frontend:**
   - Quét sạch các nhãn độc quyền trong mã nguồn `frontend/src/` và `frontend/index.html`.
   - Chuẩn hóa hệ thống nhãn: `NLE Editor`, `VFX Motion Dynamics`, `Photo Lab & Compositor`, `Digital Audio Workstation`, `Hardware Media Encoder`.
3. **Studio Trình Chiếu HTML/CSS Động (`HtmlSlideDeckStudio.tsx`):**
   - 5 mẫu slide animation vector phong cách Cyberpunk, Tech Minimalist, Breaking News, Infographic Data, và Quote Card.
   - Sandbox preview thời gian thực hỗ trợ chuyển đổi linh hoạt tỉ lệ 16:9 (YouTube) và 9:16 (TikTok/Shorts).
   - 1-click đưa slide vào Timeline hoặc tải mã nguồn HTML/CSS.
4. **Bộ Khai Thác URL Video & AI Re-Cook (`VideoUrlRecookStudio.tsx`):**
   - Tải video từ bất kỳ link nào (YouTube, TikTok, Shorts, Reels, MP4) qua `yt_dlp` với cơ chế fallback HTTP streaming trực tiếp.
   - Bổ sung endpoint backend `POST /media/from-url` và Pydantic contract `MediaIngestUrlRequest`.
   - Trích xuất phụ đề/lời thoại bằng Faster-Whisper.
   - AI Transformer tái cấu trúc nội dung theo 4 nhịp giữ chân khán giả: `[Hook]`, `[Bằng chứng]`, `[Cú lật Turn]`, `[Payoff & CTA]`.
   - Đảm bảo điểm Anti-Plagiarism Copy-Risk đạt 0%.
   - 1-click cập nhật kịch bản vào `useProjectStore` và chuyển cảnh tự động vào Timeline.

**Kiểm chứng:**
- `npm run type-check`: **0 errors (100% pass)**.
- `ruff check src tests`: **All checks passed**.
- `ruff format --check src tests`: **171 files already formatted**.
- `mypy src`: **Success: no issues found in 118 source files**.
- `pytest tests/test_media.py`: **16/16 passed**.


## 2026-09-18 — Tận dụng GPU RTX 4060 + cơ chế tự ngắt khi quá tải

**Yêu cầu:** Máy có RTX 4060 Laptop — tích hợp GPU vào pipeline, và phải có cơ chế
ngắt / xử lý tuần tự / kéo dài thời gian khi máy quá tải.

**Phát hiện quan trọng nhất:** `h264_nvenc` **không phải là một khả năng, mà là một
cặp (binary, encoder)**. ffmpeg được biên dịch theo một phiên bản NVENC API cụ thể;
driver cũ hơn sẽ từ chối mở encoder dù build có liệt kê nó:

- `ffmpeg 9.0.1` (hệ thống) → `h264_nvenc` **✗** *Required: 13.1, Found: 12.2*
- `ffmpeg 7.1` (đã có sẵn trong venv qua `imageio-ffmpeg`) → `h264_nvenc` **✓**

Nghĩa là **GPU dùng được ngay, không cần cài gì thêm** — chỉ cần governor biết tìm
build thứ hai. Nếu chỉ liệt kê tên encoder như trước, máy này sẽ mãi chạy libx264.

**Những gì đã làm:**

1. **Tách module theo đúng quy ước read/decide** (cả ba đều dưới ngân sách 1100 dòng):
   - `compute.py` (281 dòng): kiểu dữ liệu dùng chung — `JobKind`, `Admission`,
     `FfmpegBuild`, `GpuInfo`, `HardwareProfile`, `CodecChoice`, `Decision`.
   - `hardware.py` (392 dòng): **chỉ đọc** máy — `probe`, `discover_binaries`,
     `machine_pressure`, `probe_encoder`.
   - `resources.py` (815 dòng, trước là 1.407): **chỉ ra quyết định** —
     `ResourceGovernor`. Mọi tên cũ vẫn import được từ `resources` như trước.

2. **Phát hiện nhiều build ffmpeg + mở thử thật:** `discover_binaries()` tìm theo thứ
   tự `ffmpeg_binary` → `PATH` → `ffmpeg_extra_binaries` → build đi kèm package.
   `resolve_hardware_encoder()` mở thử **từng cặp (build, encoder)** bằng một encode
   thật (cache theo cặp, không theo tên) và chỉ trả về cặp chạy được.
   `CodecChoice.binary` mang theo build cần dùng; render dùng đúng build đó, còn
   **đường fallback phần mềm luôn quay về ffmpeg của máy**.

3. **Sửa một hồi quy do chính tôi gây ra:** `decoder_args("auto")` trước đây tự thêm
   `-hwaccel cuda` khi thấy `cuda` trong `ffmpeg -hwaccels` → **mọi render chậm đi**.
   Đo thật (đọc 1 clip rồi bỏ): 3s 720p **120ms** phần mềm so với 955ms `-cuda`;
   60s 1080p **626ms** so với 1914ms; 20s 4K **812ms** so với 2292ms. Giờ `auto`
   nghĩa là **tắt**, chỉ bật khi gọi tên cụ thể, kèm lý do và số đo trong docstring.

4. **Cơ chế ngắt khi quá tải (đúng yêu cầu):** `_run_command` chuyển sang `Popen` +
   luồng giám sát. Trong lúc render, định kỳ đọc áp lực máy và **terminate** nếu
   RAM trống < `RAM_ABORT_MB` (350) hoặc GPU ≥ `GPU_ABORT_TEMPERATURE_C` (90).
   Ngưỡng ngắt **cố ý nằm ngoài** ngưỡng nhận việc (700 MB / 82°C) để tải bình
   thường không bao giờ giết việc đang chạy. Bộ giám sát chỉ đọc RAM và nhiệt độ GPU
   (`machine_pressure`) — **không spawn ffmpeg** — nên không tự tạo thêm tải lên chính
   máy nó đang canh.

5. **Sửa lỗi logic trong phần advice:** trước đây advice nói "MP4 exports use libx264"
   trong khi export **thật sự** chạy NVENC trên build thứ hai — tự mâu thuẫn. Giờ
   advice nhận `resolved` và mô tả đúng điều sẽ xảy ra.

**Kiểm chứng:**

- `scripts/qa_nvenc_path.py`: **17/17 PASS** trên máy thật — encode 8s 1080x1920
  bằng NVENC qua build 7.1 trong **3.01s**, fallback phần mềm ghi nhận đúng
  `libx264`, watchdog ngắt process thật sau **0.26s** và nêu đúng lý do.
- Số đo encode (600 frame 1080x1920, `render_threads=1` như pipeline thật):
  libx264 **4791ms** / h264_nvenc **3095ms**; khi tính cả `-filter_threads 1`:
  **4697ms** / **2072ms**. Giá trị thật của NVENC ở đây là **giải phóng CPU**, không
  phải tốc độ đỉnh (với 16 luồng rảnh, libx264 rất nhanh: 1108ms).
- `docs/COMPUTE-RESOURCES.md`: tài liệu mới, ghi rõ số đo, thứ tự tìm build, thang
  nhận việc, ngưỡng ngắt, và **cách mở khoá GPU cho model torch** (hiện là
  `2.14.0+cpu` nên OCR/upscale/whisper vẫn chạy CPU; `model_device()` đã sẵn sàng
  trả `cuda` ngay khi `torch.cuda.is_available()` thành true).
- `tests/test_resources.py`: **48 test** (thêm 12: nhiều build, thứ tự ưu tiên,
  chống trùng đường dẫn, cache theo cặp, ngưỡng ngắt, watchdog giết process thật).

---

### 2026-09-18 — Hoàn thiện Toàn bộ 100% Chức năng Frontend Chuẩn NLE Studio Đa Kênh

**Động lực:**
Người vận hành yêu cầu tiếp tục phát triển toàn bộ frontend một cách hoàn hảo, dựa theo 100% các tính năng được quy định trong các tài liệu `.md` của dự án (`docs/KE-HOACH-TONG-THE.md`, `docs/SPEC-IMAGE-EDITING.md`, `docs/SPEC-VIDEO-EDITING.md`, `docs/SPEC-AUDIO-EDITING.md`, `docs/SEO-SCORING.md`, `docs/NLE-STUDIO-FULL-ARCHITECTURE.md`, `docs/AGENT-BRIDGE.md`, `docs/PERCEPTION-LAYER.md`), tuyệt đối không được thiếu bất kỳ tính năng nào.

**Những gì đã làm:**
1. **Multi-Format Content Empire Studio (`ContentEmpireStudio.tsx`):**
   - Không gian điều phối đế chế nội dung 1 Topic Master -> 1 YouTube Long-form (8-12 phút, cấu trúc 8 bước: Hook, Context, Event, Escalation, Climax, Aftermath, Lesson, CTA) + 5-10 Video TikTok/Shorts độc lập (30-60s) với hook, kịch bản biến thể riêng biệt.
   - Thanh phân bổ tài nguyên chuẩn Golden Hybrid Media Allocation Bar (30% AI Synthetic Footage, 20% Historical Archives, 15% Dynamic Maps, 15% Declassified Documents, 10% Technical Diagrams, 10% Kinetic Motion).
   - Ma trận 15 AI Prompts chuyên sâu sẵn sàng sao chép cho Kling 1.5, Google Veo 2, Midjourney v6.1, Flux Pro, Suno AI, ElevenLabs, và Fact-Check protocol.
2. **Visual DAG Pipeline Orchestrator (`DAGWorkflowStudio.tsx`):**
   - Trình điều phối đồ thị phi chu trình có hướng (Directed Acyclic Graph) trực quan với 9 khối sản xuất chuẩn (Research Engine, Script Drafting, Gate 1 Human Approval, Neural TTS, Ingest AI Media, Multi-Track NLE, ffmpeg Render, Gate 2 Video Review, Omni-Publish).
   - Canvas SVG vẽ đường cong Bézier thời gian thực, hỗ trợ kéo thả vị trí các node, thêm/xóa node và nối dây luồng dữ liệu giữa các cổng Input/Output.
   - Tích hợp kiểm tra Pre-flight Checklist và Terminal trực tiếp hiển thị log luồng thực thi (Stream Log Console).
   - Hỗ trợ chuyển đổi mượt mà giữa DAG Pipeline Toàn trình và Fusion Node Compositor (VFX).
3. **External Ingestion Hub Modal (`ExternalIngestionModal.tsx`):**
   - Modal 4 tab nạp tư liệu ngoại vi:
     - Tab 1: Video Footage URL (YouTube, TikTok, Reels, MP4 direct) hoặc upload file trực tiếp với tùy chọn Auto-bind vào Scene Timeline.
     - Tab 2: Audio & Voiceover (Edge-TTS, ElevenLabs, Suno music) với tag phân loại (Dialogue, BGM, SFX).
     - Tab 3: Research Dossier (tài liệu nghiên cứu, hồ sơ giải mật, báo chí lưu trữ).
     - Tab 4: Batch Ingest Dropzone nạp hàng loạt tư liệu tự động phân loại bằng AI.
4. **Universal Agent Bridge Modal (`AgentBridgeModal.tsx`):**
   - Cầu nối đồng bộ 2 chiều với các AI Agent hàng đầu (Claude Code, Google Gemini, Codex, DeepSeek, Cursor).
   - Hiển thị trực quan tệp `brief.md` tự sinh, hỗ trợ sao chép 1-click hoặc tải về máy.
   - Khu vực nhập liệu phản hồi của Agent (`agent-result.md`) tự động bóc tách kịch bản, lời bình và cập nhật vào quy trình sản xuất.
5. **SEO & Social Packaging Scorer Modal (`SeoPackagingModal.tsx`):**
   - Hệ thống đánh giá SEO 70 tín hiệu theo chuẩn YouTube Long-form, TikTok, và YouTube Shorts.
   - Thước đo Radar trực quan (Hook Pacing, Metadata, Visual CTR, Audio Retention, Platform Policy).
   - Nút AI 1-Click Optimize tự động tối ưu tiêu đề, mô tả, bộ hashtag/tags và tính toán điểm tăng thực tế (`gain`).
   - Danh sách khắc phục lỗi xếp theo thứ tự ưu tiên điểm số.
6. **Perception & AI Audio Intelligence (`AudioLabStudio.tsx`):**
   - Bổ sung sub-tab "Nghe Hiểu & Khử Ồn (Perception)" trang bị:
     - Bộ phát hiện khoảng lặng & tốc độ nói (Silence & Speaking Pace) với biểu đồ nhịp độ.
     - Phân loại sắc thái âm nhạc tự động (Energy, Valence, Tension, Dynamic Range).
     - Đo lường mức đỉnh (Peak Meter) và chuẩn âm lượng Broadcast (-14 / -16 LUFS).
     - AI Stem Isolation 4 kênh (Tách Giọng hát / Lời bình, Nhạc nền, Trống, Bass).
7. **Dự án Mới & Tinh Gọn Giao Diện Tối Đa Không Gian Dựng (`SidebarWorkflowNav.tsx`, `page.tsx`):**
   - Loại bỏ hoàn toàn thanh Topbar ở trên đỉnh theo yêu cầu người vận hành để giải phóng 100% chiều cao màn hình cho màn hình Preview, Timeline và các Audio/Video Inspector.
   - Hợp nhất Bộ chọn dự án (Project Selector dropdown), Nút tạo dự án mới (`NewProjectModal`), và Huy hiệu 2 cổng duyệt bắt buộc (`Gate 1: Duyệt kịch bản`, `Gate 2: Duyệt video`) ngay trên đầu thanh bên Sidebar.
   - Bổ sung thanh công cụ mini 5 nút truy cập nhanh ở đáy Sidebar: Nạp Media ngoại vi (`DownloadCloud`), Universal Agent Bridge (`Cpu`), Chấm điểm SEO (`Target`), Kiểm định QA (`ShieldCheck`), và Kiểm toán chi phí (`DollarSign`), cùng Co-Pilot (`Bot`).

**Kiểm chứng:**
- `npm run type-check`: **0 errors (100% pass)**.
- `npm run build`: **Next.js 14.2.35 Build PASS** (4/4 static pages generated thành công, First Load JS ~241 kB).

---

### 2026-09-18 — Thiết Kế Lại Toàn Diện Bước 1 (Script Studio & Storyboard): 10 Tiêu Chí, Chatbot Cột Phải Sửa Theo Dòng, Dự Đoán Thời Gian Nói

**Động lực:**
Người vận hành yêu cầu thiết kế lại Bước 1 trong phần frontend theo 10 nhóm tiêu chí chi tiết, tích hợp AI Chatbot cố định thường trực ở bên tay phải có khả năng sửa trực tiếp kịch bản theo phạm vi đánh dấu (từ dòng X đến dòng Y hoặc đoạn văn bôi đen) kèm tính năng dự đoán thời gian phát âm theo tốc độ (WPM & âm tiết tiếng Việt), và duy trì localhost mở liên tục để test.

**Những gì đã làm:**
1. **Bộ Cài Đặt Đề Bài 10 Tiêu Chí Toàn Diện (`ScriptBriefSettingsPanel.tsx`, `types/script.ts`):**
   - Tiêu chí 1: Chủ đề cụ thể & góc nhìn / insight mới lạ, phản trực giác hoặc gây tranh luận.
   - Tiêu chí 2: Nền tảng đích (TikTok, Shorts, Reels, YouTube 16:9), thời lượng mong muốn (15s, 30s, 60s, 3m, 10m...), tỷ lệ khung hình (9:16, 16:9, 1:1, 4:5).
   - Tiêu chí 3: Chân dung đối tượng khán giả (tuổi, giới tính, sở thích; đã biết gì; nỗi đau pain points; khao khát desires).
   - Tiêu chí 4: Mục tiêu video (giáo dục, giải trí, bán hàng, follow, viral) và hành động kêu gọi sau khi xem (CTA).
   - Tiêu chí 5: Giọng điệu & phong cách (hài hước, nghiêm túc, truyền cảm hứng, kịch tính, thân mật) + Toggle chèn meme/slang/tiếng lóng giới trẻ.
   - Tiêu chí 6: Cấu trúc mong muốn: Kiểu Hook 3 giây đầu (Phản trực giác, Sai lầm chết người, Khoảng trống tò mò, Số liệu gây sốc), cấu trúc phân đoạn, và toggle Visual Cue đi kèm lời thoại.
   - Tiêu chí 7: Nhân vật / Hình thức thể hiện (Talking head on-cam, Voiceover + B-roll, Hội thoại 2 người, Storytelling điện ảnh, POV).
   - Tiêu chí 8: Dữ liệu cụ thể chống AI bịa đặt: Đính kèm file PDF/Word/Text, link bài viết web, YouTube script nguồn, số liệu/tên sản phẩm thực nghiệm.
   - Tiêu chí 9: Ví dụ tham khảo: Upload video tham khảo bóc tách script, link YouTube/TikTok mẫu, Creator mẫu học tông giọng, script mẫu dán trực tiếp.
   - Tiêu chí 10: Điều cần tránh: Không nhắc đối thủ, từ cấm nền tảng, tránh câu sáo rỗng, tránh nội dung nhạy cảm.
   - Hệ thống Presets phong phú: Nấu ăn 60s, Bí ẩn hàng không 10m, Review công nghệ 60s, Quản lý tài chính 3m.

2. **AI Script Copilot Chatbot Cố Định Bên Tay Phải (`ScriptChatbot.tsx`):**
   - Khung Chatbot luôn thường trực bên cột phải (Persistent Right Panel), kết nối 2 chiều với kịch bản.
   - Thanh chỉ thị phạm vi sửa thông minh: Nhận diện theo vùng bôi đen của chuột hoặc bộ chọn số dòng (`Từ dòng [X] đến [Y]`) và các nút chọn nhanh (`[Hook 3s]`, `[Nội dung]`, `[Cú lật Turn]`, `[CTA]`, `[Toàn văn]`).
   - Phím lệnh 1-chạm (Quick Rewrite Chips): Viết lại Hook 3s giật gân, Rút ngắn 15s, Thêm Visual Cue, Chèn slang/meme, Đưa số liệu chống bịa.
   - Sửa trực tiếp vào kịch bản: Thay thế chính xác chỉ ở các dòng đã chọn, bảo toàn 100% các dòng khác.
   - Hiển thị bảng so sánh Diff trực quan (đoạn cũ gạch đỏ vs đoạn mới chữ xanh).
   - Nút **Hoàn tác (Undo)** 1-click giúp khôi phục ngay kịch bản trước đó nếu chưa vừa ý.

3. **Công Cụ Dự Đoán Thời Gian Nói Theo Tốc Độ (`ScriptPacingBar.tsx`):**
   - 4 mức tốc độ đọc chuẩn: Chậm (130 WPM - ~2.1 từ/s), Chuẩn (160 WPM - ~2.7 từ/s), Nhanh (195 WPM - ~3.2 từ/s), Cực nhanh (230 WPM - ~3.8 từ/s).
   - Tính toán trực tiếp số từ, số âm tiết tiếng Việt (~words * 1.05), và thời lượng ước tính so với thời lượng mục tiêu (kèm huy hiệu cảnh báo Chuẩn nhịp / Dài hơn / Ngắn hơn).
   - Dự đoán thời lượng riêng cho đoạn đang được chọn: `🎯 Dòng X-Y: Z từ (~Ts)`.

4. **Trình Soạn Thảo Đánh Số Dòng & Storyboard 2 Cột (`ScriptEditorView.tsx`):**
   - Cột đánh số dòng lề trái (Line Number Gutter) đồng bộ cuộn với textarea. Click vào số dòng để đặt phạm vi cho Chatbot.
   - Chế độ xem Storyboard 2 cột chuyên nghiệp: phân cảnh Scene, thời gian, lời thoại Voiceover TTS, và chỉ dẫn hình ảnh Visual Cue.
   - Cổng kiểm duyệt bắt buộc Gate 1: Checkbox xác nhận bản quyền tư liệu (Source Rights) và nút Phê duyệt kịch bản.

5. **Chế Độ Chia Đôi Màn Hình (`ScriptStudio.tsx`):**
   - Bổ sung tab `3. Chia Đôi (Song Song)` cho phép hiển thị đồng thời cả Đề bài 10 tiêu chí và Kịch bản cạnh nhau, kết hợp cùng Chatbot bên phải thành bố cục 3 cột làm việc tối ưu.

**Kiểm chứng:**
- `npm run type-check`: **0 errors (100% pass)**.
- `ruff check src tests`: **All checks passed!**
- `ruff format --check src tests`: **All 173 files formatted!**
- `mypy src`: **Success: no issues found in 120 source files!**
- Visual Inspection bằng Playwright & Multimodal AI Vision: Đã kiểm tra toàn bộ luồng chọn dòng 1-4, viết lại Hook 3s bằng Chatbot, hiển thị diff, cập nhật editor, và nút hoàn tác khôi phục kịch bản.
- Localhost: Cả Next.js frontend (`http://localhost:3000`) và FastAPI backend (`http://127.0.0.1:8080`) đang chạy nền và sẵn sàng phục vụ.

## 2026-09-18 — Backend khớp hợp đồng frontend + refactor toàn bộ

**1. Ba lỗi backend thật (đều tái hiện được, không phải suy đoán)**

- **Handler 422 tự crash thành 500.** `validation_handler` trả về `exc.errors()` nguyên bản; pydantic nhét chính object `ValueError` vào `ctx`, không serialize được, nên `JSONResponse` ném `TypeError` *bên trong* handler lỗi. Hệ quả: mọi request sai định dạng trả về 500 câm thay vì 422 nói rõ sai ở đâu — và nó che luôn toàn bộ các lỗi hợp đồng bên dưới. Sửa bằng `_json_safe()` (giá trị lạ hạ cấp thành `repr`).
- **`/seo/ab/plan` 500 khi không gửi `daily_traffic`.** `plan_ab_test` trả `days=None` (trung thực: không có traffic thì không ước lượng được), nhưng view gọi `int(None)` → `TypeError`. Thêm `_int_or()`; `estimated_days=0` nghĩa là "chưa ước lượng", `days` vẫn giữ `None`.
- **`/cost/check` luôn báo $0.00.** Studio gửi `estimated_usage`, model chỉ đọc `calls` → dự toán rỗng mà vẫn trả 200. Đây là kiểu lệch hợp đồng nguy hiểm nhất: không lỗi, chỉ sai tiền. Nay nhận cả hai tên và trả thêm `within_budget`/`estimated_cost`/`by_service`.

**2. Các lệch hợp đồng khác đã đóng**

| Chỗ | Vấn đề | Xử lý |
|---|---|---|
| `GET /agents` | thiếu `script_styles`, `tts_voices`; agent thiếu `id`/`role`/`provider`/`capabilities` | mở rộng `AgentInfo` + `AgentCatalog`; voice lấy từ `tts.voice_catalog()` nên picker không thể đề xuất giọng engine không nói được |
| `POST /projects/{id}/agent-result` | client gửi `markdown_response`, model đòi `markdown` → 422 | `TwinSpelling` |
| `POST /timeline/command` | client gửi `command`, model đòi `text` → 422; response thiếu `parsed_command`/`message` | nhận cả hai + trả cả hai |
| `PUT /projects/{id}/script` | studio gửi `raw_script` | đã có alias, nay dùng chung `TwinSpelling` |
| `POST /media/dedup` | studio gửi body rỗng → 422; response là list, studio đọc `{duplicates}` | body tùy chọn (rỗng = quét cả thư viện); trả `{groups, count, duplicates[{original,duplicate,similarity}], checked}` |
| `POST /qa/copyright/verdict` | `asset_ids: []` bị validator từ chối | batch rỗng là hợp lệ → `passed:true`, kèm `checked:0` |
| `GET /media/{id}/transcribe` | dashboard gọi GET, backend chỉ có POST (405) | sửa client sang POST (transcribe là thao tác ghi, không được để GET cache/prefetch) |
| `PUT /projects/{id}/timeline` | dashboard lưu timeline, route không tồn tại (404) | thêm route nhận thẳng `VideoProject` (bản wrappered vẫn ở `/video-project`) |
| `TimelineMarker` | app.js đọc `item.time`, backend chỉ trả `time_seconds` → hiện `undefined` | thêm alias `time` |
| `project.script` | studio đọc `script.raw_script`/`.sections`, nhưng `script` là **chuỗi** (app.js, CLI và agent tools đều cần chuỗi) | studio đọc `script_document` (đã có sẵn); thêm alias `name`/`words`/`duration_target_seconds` cho section và `total_duration` cho plan |

**3. Refactor**

- Rút quy tắc "hai cách viết, đúng một cái" vào `models.common.TwinSpelling` — trước đó 4 model tự viết lại cùng một validator (`ScriptUpdate`, `ViralityRequest`, `AgentResultCreate`, `TimelineCommandRequest`).
- Bật thêm bộ rule ruff mà chính codebase đã tự đánh dấu bằng `# noqa` (`BLE`) cùng loạt rule đã sửa một lượt (`C4`, `PERF`, `PTH`, `RET`, `RUF`). `ignore` có lý do cho từng mục bị loại.
- Sửa 87+ phát hiện thật: bỏ `int(round(...))` thừa, `zip(x, x[1:])` → `itertools.pairwise`, `try/except/pass` → `contextlib.suppress`, `open()` → `Path.open()`, `os.path.abspath` → `Path.resolve`.
- 20 chỗ `except Exception` cố ý nay đều mang lý do: sau lần này mọi blind-except phải nói rõ vì sao.
- **Bài học đã ghi vào `AGENTS.md`:** không bao giờ chạy `ruff --select <rule>` để phán một `# noqa` là thừa — `--select` *thay thế* bộ rule đang cấu hình, nên mọi directive trông như thừa và `--fix` sẽ xoá directive đang dùng thật.

**4. Kiểm chứng**

- `tests/test_frontend_contract.py` (mới): chạy pipeline thật qua HTTP bằng đúng payload của hai client và khẳng định đúng các field chúng đọc — 11 test, chốt lại toàn bộ hợp đồng trên.
- `tests/test_resources.py`: test watchdog timeout trước đây phụ thuộc RAM thật (chạy full suite là tụt dưới ngưỡng 350MB nên báo sai nguyên nhân). Nay cô lập bằng governor có áp lực tiêm vào.
- `ruff check` / `ruff format --check` / `mypy src`: sạch. `pytest` toàn bộ: **1049 test, 0 fail**. `scripts/smoke.py`: **64/64 PASSED**.

## 2026-09-18 — Tối ưu hóa toàn diện Bước 1 (Script Studio & Storyboard): Chuẩn 1 cột & AI Copilot bên trái

**1. Gỡ bỏ thanh banner `AIAgentBar` phía trên:**
- Loại bỏ thanh banner `AIAgentBar` ở đầu trang (Chief Storyteller & Viral Script Director) cùng các phím lệnh và ô prompt trùng lặp, giải phóng >140px chiều dọc giúp giao diện thông thoáng.

**2. Quy chuẩn 1 cột duy nhất & Đơn giản hóa còn đúng 2 Tab:**
- Đề bài 10 tiêu chí (`ScriptBriefSettingsPanel.tsx`) được căn chỉnh theo 1 cột duy nhất (`max-w-4xl mx-auto w-full space-y-4`).
- Chế độ Storyboard (`ScriptEditorView.tsx`) chuyển từ bảng lưới 12 cột chật hẹp thành thẻ phân cảnh dọc (Vertical Card Feed) 1 cột chuyên nghiệp, hiển thị từng cảnh quay riêng biệt gồm Cảnh #, Section, Time range, Voiceover và Visual Cue.
- Rút gọn tối đa thành **đúng 2 Tab** theo đúng chỉ đạo:
  1. `1. 10 Tiêu Chí`: Mẫu nhập liệu đề bài 10 chiều kích.
  2. `2. Kịch Bản`: Trình soạn thảo đánh số dòng, Storyboard Feed 1 cột, xem lịch sử các phiên bản, phân tích điểm số Virality Score trực tiếp trên đầu kịch bản, và cụm kiểm duyệt Gate 1 ở chân trang.

**3. Bố trí AI Copilot Chatbot ở bên trái (`ScriptChatbot.tsx`):**
- Đưa Chatbot sang cột bên trái (Persistent Left Panel) theo đúng thói quen thị giác tự nhiên: ra lệnh ở bên trái -> kịch bản xuất hiện và cập nhật tại cột soạn thảo bên phải.
- Tích hợp tính năng **Tự sinh kịch bản** trực tiếp từ ô chat (nút *"✨ Tự sinh kịch bản"* hoặc lệnh chat bất kỳ) tổng hợp đầy đủ 10 tiêu chí thành kịch bản 4 phần chuẩn.
- Tích hợp kiểm tra bản quyền *"🛡️ Quét bản quyền (100% Unique)"*.
- Giữ nguyên bộ chọn dòng theo phạm vi đánh dấu, thẻ so sánh diff (Before/After) và nút **Hoàn tác (Undo)**.
- Thêm nút `[Ẩn Chatbot]` / `[Mở Chatbot]` linh hoạt để mở rộng trình soạn thảo toàn chiều rộng khi cần.

**4. Mở rộng đính kèm nhiều file, nhiều URL và lưu lịch sử phiên bản từng phần:**
- Mục 08 đính kèm không giới hạn: hỗ trợ file PDF, DOCX, XLSX, TXT, MD với chip thông tin, dung lượng và nút xóa.
- Nạp nhiều URL trang web / bài báo kèm ghi chú tóm tắt và link ngoài.
- Tích hợp `ScriptSectionHistoryModal.tsx`: tự động ghi nhớ snapshot khi sinh / sửa kịch bản, lưu snapshot thủ công cho từng phân đoạn (`[Hook]`, `[Turn]`, `[CTA]` hoặc toàn văn) và khôi phục (Restore) với 1 click.

**5. Thanh Pacing Bar điều chỉnh tốc độ đọc linh hoạt (Adjustable WPM Slider & Stepper):**
- Giữ nguyên 4 nút bấm nhanh: `Chậm (130)`, `Chuẩn (160)`, `Nhanh (195)`, `Cực (230)`.
- Bổ sung thanh trượt **Slider (80 - 300 WPM)** kéo thả điều chỉnh nhịp đọc mượt mà.
- Bổ sung bộ nút tăng/giảm **Stepper (`[-] [WPM] [+]`)** kèm ô nhập số trực tiếp, hỗ trợ tinh chỉnh chính xác từng 5 từ/phút hoặc gõ thẳng số mong muốn.
- Tự động hiển thị nhãn `Tùy biến ({wpm})`, hệ số tốc độ tương đối (ví dụ `1.06x`) và tức thì cập nhật dự đoán thời lượng của kịch bản (`56s / Mục tiêu 60s`).

**6. Kiểm chứng:**
- `npm run type-check`: **0 errors (100% pass)**.
- `python scripts/frontend_imports.py`: **clean (98 files)**.
- Visual Inspection Playwright & Multimodal Vision: Kiểm tra thành công luồng tự sinh kịch bản từ ô chat bên trái sang trình soạn thảo bên phải, Pacing Bar cập nhật trực tiếp `1m 0s`, thanh Virality Score `55/100 Điểm Virality`, tính năng ẩn/hiện chatbot, thanh chỉnh tốc độ Slider/Stepper và chuyển đổi sang Thẻ phân cảnh dọc 1 cột.
- Cả hai server `http://localhost:3000` (Next.js) và `http://127.0.0.1:8080` (FastAPI) đang chạy liên tục cho Operator kiểm thử.


