# Rà soát chức năng backend — kết quả chạy thật

> Phiên: 2026-09-19. Người chạy: agent (Buffy), không dựa vào test — **gọi thật từng
> chức năng qua HTTP** rồi đo. Số liệu thô của cả **229 lượt gọi** nằm ở
> [`FEATURE-AUDIT-LOG.md`](FEATURE-AUDIT-LOG.md) (bảng theo nhóm + bảng đủ 110 tool)
> và [`FEATURE-AUDIT-LOG.json`](FEATURE-AUDIT-LOG.json) (log máy đọc được).

**Cách tái lập** (máy này, `.venv` sẵn có):

```bash
python scripts/feature_audit.py --port 8188 \
    --json docs/FEATURE-AUDIT-LOG.json --md docs/FEATURE-AUDIT-LOG.md
python scripts/feature_audit.py --groups vision,image,negative   # một nhóm bất kỳ
```

Script tự dựng server trên cổng trống, tự tạo fixture (ảnh test card, WAV giọng,
MP4 thật bằng ffmpeg, project + timeline), rồi gọi từng chức năng và ghi lại
thời gian + mã HTTP. Fixture nằm trong `storage/uploads/feature-audit/`
(gitignore) — không sửa gì khác trong cây nguồn. Log stderr của server:
`storage/feature-audit-server.log` (đây là nơi đọc traceback của mọi lỗi 500).

## 1. Tóm tắt điều hành

| Chỉ số | Số đo |
| :--- | ---: |
| Lượt gọi thật | **229** (107 tool qua `/tools/call` + 88 đường HTTP + 18 ca đầu vào sai) |
| Trả về đúng kỳ vọng | **198** |
| Sai | **31** — trong đó **21 lỗi HTTP 500 rỗng**, 4 × 422, 3 × 409, 1 × 404, 1 × 502 |
| Tổng thời gian các lượt gọi | 50,8 s |
| Chức năng chết hẳn (100% không dùng được) | **2 tool**: `research_project`, `ground_project` |
| Chức năng nhận dữ liệu rác mà vẫn báo thành công | **2 tool**: `youtube_download`, `download_audio_clip` |
| Tool chưa từng được nhắc trong `tests/` hoặc `scripts/` | **55 / 110** |
| Mục trong `library/media/index.json` sai so với file thật | **5 / 45** |

**Kết luận ngắn:** phần lõi (timeline/NLE, ảnh, âm thanh DSP, media, SEO, script)
chạy tốt và nhanh — 198/229 lượt đúng, hầu hết dưới 0,3 s. Toàn bộ lỗi nặng nằm ở
**hai chỗ**: (a) **lớp biên HTTP** — mọi lỗi nghiệp vụ biến thành 500 rỗng, và (b)
**hai tool bị nối sai chữ ký hàm** nên chết 100%, mà bộ test 1 087 ca vẫn xanh vì
không ca nào gọi chúng.

---

## 2. Ưu tiên #1 theo yêu cầu: các chức năng "cần AI vision"

Đây là phần dễ hiểu sai nhất, nên nói thẳng trước:

> **Trong cây nguồn hiện tại không tồn tại đường "AI vision" nào.** Toàn bộ chức
> năng hiểu ảnh/video đang chạy bằng **heuristic pixel/ffmpeg cục bộ**, và chúng
> chạy *tốt*. Không có chỗ nào gửi ảnh cho model.

Bằng chứng (đọc code, không phải suy đoán):

| Bằng chứng | Vị trí |
| :--- | :--- |
| Vision mặc định TẮT, backend `rule_based` | `config.py:151` `enable_vision: bool = False`, `config.py:152` `vision_backend = "rule_based"` |
| "Vision scorer" chỉ là `Protocol` (giao diện), **không có lớp cài đặt nào** | `vision.py:83` `class VisionSceneScorer(Protocol)`; `vision.py:237` chỉ dùng nếu `settings.enable_vision and vision_scorer is not None` |
| Tầng provider chỉ có **văn bản**: `generate_script(prompt: str)` — không tham số ảnh | `providers.py:69/121/193/257/318` |
| Không tool nào đăng ký một scorer/adapter | `grep -rn "vision_scorer\|register_adapter" src/` → chỉ có định nghĩa, không có chỗ gọi trong `agent_tools.py` |
| `/health` báo `providers: {local: closed, weak: closed}`; không có `.env` | lần chạy thật, cổng 8206 |

Nghĩa là: **muốn có AI vision thật thì phải viết mới** (một lớp multimodal + đăng ký
vào `vision_scorer`/adapter). Không phải "bật config lên là xong".

### 2.1 Những gì đang gánh vai trò "hiểu nội dung" — và chúng chạy thế nào

| Chức năng | Thực tế chạy | Thời gian | Hoàn thiện | Khả năng thật |
| :--- | :--- | ---: | ---: | :--- |
| `analyze_image` (tool + `POST /studio/image/analyze`) | Thống kê điểm ảnh: histogram 256 bin, độ sáng/tương phản/cast/màu/nét | 0,02–0,03 s | 100 % | **Tốt.** Ảnh chụp màn hình 1024px → *"very dark / underexposed … muted / low saturation … sharp"* — đúng với ảnh nền tối. Không mô tả được *nội dung* ("có cái gì trong ảnh") |
| `suggest_image_edits` | Suy công thức sửa từ histogram | 0,02–0,04 s | 100 % | **Tốt trong phạm vi hẹp.** Trả 2 gợi ý kèm lý do số học (`exposure +0.7EV` vì "mean luminance 46"; `vibrance 0.5` vì "channel spread 2") |
| `media_palette` | K-means màu trên khung hình | 0,25 s | 100 % | **Chính xác.** Trên test card của tôi trả đúng 5 màu thật: `#0f1523 #eea726 #db3b3b #3bbc75 #3a80db` |
| `media_scene_cuts` | So histogram liên tiếp (không model) | 0,28 s | 100 % | **Đúng.** Video tĩnh 4 s → 1 cảnh duy nhất 0→4 s |
| `describe_media` | Gộp probe + loudness + silence + cuts + palette + beats + text(OCR) | **9,4 s** | 90 % | Báo cáo đầy đủ và đọc được; `include=["vision"]` (không có trong tài liệu) bị **bỏ qua im lặng** thay vì 422 |
| `analyze_audio` / `describe_audio` | RMS, phổ, noise floor, nhịp, phân loại | 0,10–0,12 s | 100 % | Trả câu mô tả tiếng người đọc được (*"balanced, mid-focused"*) |
| `suggest_audio_mastering` | Suy chain từ số đo | 0,09 s | 100 % | 1 gợi ý `audio_normalize -14 LUFS` kèm lý do |
| `suggest_video_edits` / `ai_assist` | Heuristic trên timeline | 0,003–0,02 s | 100 % | Đúng chức năng (gợi ý cắt/nhịp), **không** phải AI |
| `kb_ask` | RAG cục bộ trên KB đã nạp (không LLM) | 0,01–0,80 s | 100 % | Trả trích nguồn; khi KB rỗng trả *"No relevant knowledge found in the sources."* — trung thực |
| `seo_optimize` | Luật + trọng số xác định | 0,02–0,03 s | 100 % | Không cần provider, kết quả lặp lại được |

### 2.2 Những chức năng *quảng cáo là AI* nhưng đang chết hoặc không thể chạy

| Chức năng | Trạng thái đo được | Vấn đề |
| :--- | :--- | :--- |
| `dub_audio` | **HTTP 500, body rỗng** | Mô tả tool ghi rõ *"Fails with a clear error until an adapter is configured"* — nhưng client **không nhận được lỗi nào**. `AiAudioError` bị nuốt ở tầng HTTP (xem L3). Nội bộ raise đúng: *"'dub' needs an ML adapter. Register one via register_adapter()…"* |
| `voice_clone` | **HTTP 500, body rỗng** | Y hệt `dub_audio`. `ref_voice` được tài liệu hoá là *base64 reference sample* (không phải tên/ID) — dễ dùng sai |
| `research_project` | **HTTP 500** | `TypeError: Unable to serialize unknown type: <class 'coroutine'>` — handler gọi hàm `async` mà không `await`. 100 % hỏng (L1) |
| `ground_project` | **HTTP 500** | `TypeError: KnowledgeMixin.ground_project() missing 1 required positional argument: 'data'`. 100 % hỏng (L2) |

**Việc cần làm cho AI vision (đề xuất, theo thứ tự):**
1. Sửa L1/L2 trước — nếu không, mọi tích hợp AI sau này cũng vô nghĩa vì agent không
   gọi được 2 tool nền (research/ground).
2. Sửa L3 (map lỗi → 4xx) — để lỗi "chưa cấu hình adapter" đến được client.
3. Viết lớp multimodal thật (`VisionSceneScorer` + adapter cho 1 nhà cung cấp), gắn vào
   `describe_media`/`analyze_image` dưới cờ `CONTENT_FACTORY_ENABLE_VISION=true`.

---

## 3. Từng nhóm chức năng: đã kiểm gì, thời gian, mức hoàn thiện

Thang điểm dưới đây là **đánh giá của tôi từ hành vi đo được**, không phải từ tài liệu.
"Hoàn thiện" = bao nhiêu % hợp đồng đã ghi trong manifest/schema là chạy được.

### 3.1 `vision` — 12/12 lượt đúng, 0,4 s

Đã kiểm: `analyze_image`×2, `suggest_image_edits`, `describe_image_op`, `describe_media`×2
(ảnh + video), `media_scene_cuts`, `suggest_video_edits`, `ai_assist`, `media_palette`,
`POST /studio/image/analyze`, `POST /studio/image/suggest`.
Hoàn thiện **100 %**, khả năng **trung bình** (heuristic, không hiểu nội dung — xem §2).

### 3.2 `catalog` — 20/20 lượt đúng, 4,3 s

Mọi catalogue trả đủ: 9 nhóm op ảnh + 6 preset, 11 effect video, 32 effect audio,
5 stem, 7 SFX, 6 preset giọng, 3 platform SEO, 4 loại resource, 45 media, 1 KB.

- `resource_status` = chậm nhất nhóm: 3,93 s trong lượt chạy audit, và khi tôi gọi
  liên tiếp 4 lần trên cùng một server: **6,49 s / 1,97 s / 1,35 s / 1,77 s** — tức có
  phần khởi động nguội nhưng mỗi lần gọi vẫn tốn ~1,4–2,0 s cho một truy vấn trạng thái
  (L13).
- `agent_catalog`, `list_script_styles` (11 style), `describe_*_operation` đều tức thời.
- Hoàn thiện **100 %**, khả năng **tốt**.

### 3.3 `image` — 23/25 lượt đúng, 1,4 s

Đã kiểm: `edit_image` (ops + preset + resize), `batch_edit_image` (2 ảnh),
`compose_images`, `collage_images` (2 ảnh từ library, caption), `apply_video_effect`,
`media_contact_sheet` (6 khung), `extract_frame_image`, **chuỗi session đầy đủ**
(`begin_image_session` → `edit` → `undo` → `redo` → `state`, `can_undo/can_redo` đúng),
`POST /studio/image/{edit,batch,session/begin,ops,presets,describe-op}`.

- Nhanh nhất cả hệ: pipeline 2 op = **0,021 s**; contact sheet 6 khung = 0,67 s.
- Session hoạt động đúng ngữ nghĩa undo/redo.
- Hoàn thiện **92 %** (2 lượt sai là ca đầu vào rác của tôi → xem L3, L8), khả năng **rất tốt**.
- **Ảnh hỏng trong library làm tool trả 500** (L7 phần phụ) — tôi phải tự lọc ảnh
  đọc được bằng Pillow thì `media_palette`/`collage_images` mới xanh.

### 3.4 `audio` — 33/35 lượt đúng, 5,7 s

Đã kiểm 20 tool + 6 endpoint studio: `analyze_audio`, `describe_audio`,
`apply_audio_effect` (band + time-domain + mọi effect trong catalogue),
`apply_audio_mastering` (+ `/studio/audio/mastering`), `separate_audio_stems`
(2 và 3 stem), `enhance_voice` (preset `podcast`), `duck_music`, `audio_trim/fade/loop/
normalize/retime/mix/denoise`, `music_beat_grid` (121 beat @120 BPM), `synthesize_sfx`
(`whoosh`), `media_loudness`, `media_silence`, `extract_audio_track`, `POST /studio/audio/*`.

- Thời gian 0,07–1,05 s; `apply_audio_effect` chậm nhất khi xuất WAV (1,05 s).
- `separate_audio_stems` trả đúng số stem theo `num` (2 → voice/instrumental, 3 → low/mid/high).
- Hoàn thiện **94 %** (2 lượt sai = `dub_audio`, `voice_clone` → §2.2), khả năng **rất tốt** — đây là nhóm hoàn thiện nhất.

### 3.5 `media` — 7/7 lượt đúng, 0,8 s

`inspect_media` (probe chính xác: h264/aac, 640×360, 25 fps, 4,0 s),
`get_media`, `cut_media` (copy **và** re-encode), `split_media` (3 phần),
`join_media` (2 clip). 0,08–0,31 s. Hoàn thiện **100 %**, khả năng **tốt**.

- Nhưng: `cut_media` **trên file "video" trong library thất bại 500** vì 4/45 mục
  được ghi là `video` nhưng thực chất chỉ có luồng audio (L7).

### 3.6 `timeline` (NLE) — 25/25 lượt đúng, 0,8 s

Đã kiểm 17 tool + 6 endpoint: `build_video_project`, `timeline_report` (điểm 88, 3 issue),
`render_plan` (1080×1920@30, 3 step, 5 phụ đề), `describe_video_timeline`,
`set_scene_speed`, `reverse_scene`, `trim_scene`, `set_scene_audio`, `split_scene`,
`duplicate_scene`, `move_scene`, `bulk_update_scenes`, `set_keyframes`, `add_marker`,
`merge_scene`, `delete_scene`, `auto_cut_to_beat` (0,37 s), `/timeline/normalize`,
`/timeline/command` (hiểu câu lệnh), `/timeline/suggest`, `/timeline/report|describe`,
`GET /render-plan`; cộng 2 ca âm (`scene` chết → 404 có thông báo người đọc được).

- Tất cả 0,001–0,03 s. Hoàn thiện **100 %**, khả năng **rất tốt**.
- **Cảnh báo cho agent:** `build_video_project` **đổi toàn bộ scene id**. Trong lần chạy
  thật, id đã đổi giữa lúc fixture và lúc sửa (`[[scenes]] … (ids changed since build)`)
  và 12 lượt sửa đầu tiên trả 404. Agent nào cache `scene_id` sẽ hỏng (L6).

### 3.7 `script` — 5/5 lượt đúng, 0,1 s

`update_script` (200 khi còn ở giai đoạn kịch bản, **409 kèm thông báo** khi đã generate
— đúng máy trạng thái), `analyze_script` (điểm 80, 4 issue), `export_brief` (Markdown),
`POST /script/analyze`, `GET /brief.md`. Hoàn thiện **100 %**, khả năng **tốt**.

### 3.8 `seo` — 12/12 lượt đúng, 0,2 s

`seo_score` (41 = hạng F cho pack cố tình dở), `seo_optimize` (5 thay đổi),
`seo_score_project` (56), `seo_keywords`, `seo_ab_plan`, `seo_ab_evaluate`,
`seo_calibrate`, `seo_rules`, và 4 endpoint `/seo/*`. Hoàn thiện **100 %**, khả năng **tốt**.

- `seo_ab_evaluate` với 2 arm của tôi trả `winner=None, lift=0.0` — chưa rõ ngưỡng ý nghĩa
  thống kê mà tool yêu cầu; cần đọc `seo/` trước khi tin kết quả.

### 3.9 `production` — 10/13 lượt đúng, 10,9 s (chậm nhất)

Đã kiểm: `start_generation`, `approve_stage`, `generate_voiceover`, `render_video`,
`publish_project`, `POST /render`, `/publish`, `/thumbnail` (SVG), `/sensitivity/audit`,
`/cost/check`, `/cost/estimate`, `/audit/record`, `GET /audit`.

**Đường đi đúng đã kiểm riêng (thí nghiệm 2 bước):**

```
create → update_script → approvals(script) → build_video_project
   → start_generation                       (0,0 s, status=generating)
   → render_video NGAY LẬP TỨC             → 409 sau 6,2 s  ✗ (bỏ toàn bộ công đã render)
   → chờ pipeline lắng (3,1 s, status=video_review)
   → render_video                           → 200 trong 3,8 s ✓
   → POST /approvals (video)                → 200, status=video_approved
   → POST /publish                          → 200, status=published, platforms=[youtube,tiktok]
```

- Nghĩa là hệ **publish được thật**, nhưng thứ tự tự nhiên mà agent hay làm
  (generate → render) **mất 3,8–6,2 s rồi trả 409 khó hiểu** (L5).
- `render_video` là chức năng chậm nhất: 3,8 s (khi lắng) / 6,9 s (qua HTTP `/render`).
- Hoàn thiện **77 %** theo lượt đo (3 × 409), thực chất **~90 %** vì đường đúng vẫn chạy;
  khả năng **khá**, nhưng phụ thuộc thứ tự gọi.

### 3.10 `research` / `discovery` / `network` — 12/15 lượt đúng, 11,0 s

Chạy tốt: `create_project` (0,26 s), `youtube_search` (1,1 s, 3 kết quả),
`youtube_transcript` (2,4 s), `attach_kb`, `kb_ingest_url` (1,3–1,9 s, nạp
Wikipedia thật), `kb_ask` (0,8 s, trả trích nguồn), `list_kbs`, `list_projects`,
`list_media`, `GET /documents/search` (4,6–8,3 s — chậm nhất, phụ thuộc mạng),
`GET /history/search`, `GET /kb`, `POST /kb`.

Chết: `research_project` ×2 (L1) và `ground_project` (L2). Hoàn thiện **80 %**.

- `youtube_transcript` trả `segments=0` nhưng có `text` (lời bài hát) — bất nhất: có
  text mà không có segment nào (L12), nên không dùng được để canh phụ đề.

### 3.11 `http` — 37/42 lượt đúng, 13,7 s

Đã gọi 42 đường khác nhau (kể cả `GET /`, `/health`, `/tools`, `/projects*`,
`/workflow*`, `/campaign*`, `/graphics/{infographic,map}` → SVG thật, `/external/*`,
`/media*`, `/library*`, `/resources*`, `/qa/{brand,copyright,platform}`,
`/agents`, và 4 ca âm có chủ đích).

- **Lỗi thật:** `/projects/{id}/documents` → **502** *"Download failed: No downloadable
  URL for …"* (dùng tên tài liệu làm URL), xem L16.2.
- `/workflow/run` = **10,6 s** (chạy cả workflow), `GET /resources` = 2,5–4,6 s.
- 4 ca 422 còn lại là do **schema ngầm khác tài liệu** (tôi đoán sai payload —
  xem L16.1), không phải lỗi backend.

### 3.12 `negative` — 2/18 lượt đúng ⇒ **đây là phát hiện lớn nhất**

18 ca đầu vào sai (tên op lạ, byte ảnh/âm thanh rác, format lạ, preset lạ, session id sai,
stem ngoài dải, dub/voice-clone không có adapter…):

- **16 ca trả HTTP 500 với body rỗng** — client không biết mình sai chỗ nào.
- Đúng: "thiếu tham số bắt buộc" → 422 kèm tên tham số; "ref không tồn tại" → 404.
- **`separate_audio_stems num=9` trả 200** và lặng lẽ trả 3 dải (L9).

Vì `/studio/*` (multipart) *có* map `ValueError` → 422, cùng một đầu vào sai cho **422 ở
`/studio/image/edit` nhưng 500 ở `/tools/call`** — tức hợp đồng lỗi không nhất quán giữa hai
cửa vào. Đây là L3.

---

## 4. Danh sách lỗi (đã tái hiện, có vị trí code)

Mức độ: **P0** = không dùng được / mất dữ liệu, **P1** = chặn luồng làm việc,
**P2** = sai lệch/khó dùng, **P3** = vệ sinh.

### L1 — `research_project` chết 100 % (P0) ✅ đã tái hiện, có traceback
`agent_tools.py:355` `_h_research_project` (hàm **sync**) gọi `service.research(...)` là
`async def` (`services/research.py:20`) ⇒ trả *coroutine* ⇒
`PydanticSerializationError: Unable to serialize unknown type: <class 'coroutine'>` → 500.
Đây là handler **duy nhất** trong `agent_tools.py` gọi hàm async mà không `await`
(đã kiểm toàn bộ 7 hàm async của `services/`).
**Sửa:** cho tool chạy qua cầu async (như router đã làm) hoặc thêm bản sync trong service.

### L2 — `ground_project` chết 100 % (P0) ✅ đã tái hiện
`agent_tools.py:369` gọi `service.ground_project(project_id)`; chữ ký thật là
`knowledge.py:359` `ground_project(self, project_id: str, data: GroundRequest)` ⇒
`TypeError: missing 1 required positional argument: 'data'` → 500.
**Sửa:** dựng `GroundRequest()` từ `args` (schema tool nên bổ sung `query`, `top_k`).

### L3 — Mọi lỗi nghiệp vụ thành HTTP 500 rỗng (P1, lan rộng nhất)
`api/routers/tools.py` chỉ bắt `ToolError / NotFoundError / StateConflictError /
RightsNotConfirmedError`. Còn `ImageError`, `AudioEffectError`, `SfxError`,
`VideoEffectError`, `VoiceError` (đều là `ValueError`) và `MediaToolError`,
`AiAudioError` **thoát ra ngoài** → Starlette trả 500 + body `"Internal Server Error"`.
**16/18 ca đầu vào sai** rơi vào đây, và cả `dub_audio`/`voice_clone` (L§2.2) — tức lỗi
*"chưa cấu hình adapter"* đúng nghĩa bị biến thành 500.
**Sửa gợi ý:** trong `tools_call` thêm
`except ValueError as exc: 422` và `except (MediaToolError, RuntimeError)` → 422/500 **có
`detail`**; hoặc gom vào `deps._http_error` như các router khác. Sau đó thêm test khẳng
định 4 nhóm đầu vào sai phải trả 4xx.

### L4 — `youtube_download` / `download_audio_clip` lưu HTML thành "video" và báo 200 (P0, dữ liệu rác)
`media.py:367` `download_from_url`: khi yt-dlp lỗi (`except Exception: target_file = None`),
code **fallback tải thô URL bằng urllib** rồi lưu vào file `.mp4`.
Đo thật: `youtube_download` → 200 trong 2,6 s, tạo bản ghi `53c167418d6e`,
`kind=video, mime=video/mp4, duration_seconds=null`, nhưng nội dung file là
`<!DOCTYPE html>…` (795 KB trang YouTube), `ffprobe` **không thấy luồng nào**.
`download_audio_clip` → 200 trong 1,7 s, cùng kiểu (803 KB HTML, không có luồng audio).
**Sửa:** kiểm magic-byte/Content-Type (`video/*` hoặc `audio/*`) trước khi lưu; nếu yt-dlp
lỗi thì trả lỗi có thông báo thay vì tải HTML; ghi `kind` từ luồng thật.

### L5 — `render_video` bị 409 khi pipeline còn chạy, mất cả công đã render (P1)
Khi `start_generation` chạy nền (10 bước × 0,3 s), render bắt đầu rồi bị
*"Project changed during rendering; export discarded."* — **sau 6,2 s** công render.
Hết nền (status ổn định) thì render 3,8 s thành công. Cả tool và `POST /render` đều vậy.
**Sửa:** render nên **chờ** project lắng (hoặc giữ lock) và/hoặc thông báo
*"generation đang chạy, thử lại sau ~3 s"* kèm `Retry-After`.

### L6 — Scene id bị đổi khi rebuild/pipeline tiến (P1 với agent)
`build_video_project` sinh lại scene id; pipeline nền cũng dựng lại. Agent cache id →
12 lượt sửa liên tiếp trả 404 *"No scene '…' in the video project."*
**Sửa:** giữ id ổn định (nguồn gốc là chỉ số cảnh), hoặc trả `scenes[]` mới kèm cảnh báo
trong chính response sửa.

### L7 — `library/` lệch giữa index và file thật (P1)
Quét toàn bộ 45 mục: **40 tốt, 5 hỏng** — 4 "video" chỉ có luồng audio
(`accd19bb7dea`, `7369070b7083`, `654c5e38567e`, `7b4571949798`) và 1 "image" 108 byte
không giải mã được (`86c3ceddef9c`). Nguyên nhân gốc: `detect_kind` (`media.py:86`) phân
loại **theo đuôi file**, nên `.webm`/`.mp4` chứa audio vẫn được đăng ký là `video`.
Hệ quả: `cut_media` (re-encode) trên mục đó → 500; `media_palette`/`collage_images` với
ảnh 108 byte → 500.
**Sửa:** lấy `kind` từ luồng ffprobe thật (đã có `probe_media`), thêm script dọn index.

### L8 — `compose_images` trả 404 kèm ~300 ký tự base64 (P2)
`base` nhận **ref** (đúng như tài liệu), nhưng khi người gọi đưa base64 thì thông báo là
`Nothing named 'iVBORw0KGgo…'` — dài, khó hiểu, không nói "tham số này cần ref, dùng
`edit_image` nếu có base64".
**Sửa:** nhận diện chuỗi trông như base64/`data:` và trả 422 kèm gợi ý.

### L9 — `separate_audio_stems` nhận `num` ngoài dải mà không báo (P2)
`num=9` → **200**, trả 3 dải low/mid/high (tài liệu chỉ nói 2 hoặc 3).
**Sửa:** 422 kèm `{2,3}` khi `num` khác.

### L10 — `describe_media` bỏ qua section không hợp lệ (P2)
`include=["vision"]` (không có trong tài liệu) → 200, trả báo cáo mặc định, không cảnh báo.
**Sửa:** 422 liệt kê section hợp lệ.

### L11 — Session id sai → 500 thay vì 404 (P2)
`edit_image_session`/`undo_image_session` với id lạ → 500 (cùng nhóm L3, nhưng nên là 404
"session không tồn tại hoặc đã hết hạn").

### L12 — `youtube_transcript` trả `segments=0` kèm `text` (P2)
Đo trên video có phụ đề: `segments=0`, `text="[♪♪♪] ♪ We're no strangers to love ♪ …"` —
có text nhưng không có mốc thời gian ⇒ không dùng được cho phụ đề/canh nhịp.
**Sửa:** nếu chỉ lấy được text không timestamp thì đặt cờ `has_timestamps: false`.

### L13 — `resource_status` tốn ~1,5–2 s cho một truy vấn trạng thái (P3)
Đo 4 lần liên tiếp trên cùng server: 6,49 / 1,97 / 1,35 / 1,77 s; trong lượt audit 3,93 s;
`GET /resources` 2,5–4,6 s. Có phần giảm sau lần đầu nhưng vẫn không rẻ cho dữ liệu gần
như tĩnh (phần cứng, encoder khả dụng).
**Sửa:** cache TTL (10–30 s) và/hoặc chỉ mở thử encoder khi thật sự chuẩn bị render.

### L14 — Hai hợp đồng song song cho cùng chức năng (P2, dễ gây lỗi tích hợp)
`/tools/call` nhận **base64 trong JSON**; `/studio/*` nhận **multipart** (`file=`, `ops` là
**chuỗi JSON**). Ngoài ra method không nhất quán cho thao tác chỉ-đọc:
`GET /studio/image/ops` nhưng `POST /studio/video/describe-op`; `GET /studio/audio/effects`
nhưng `POST /studio/audio/describe`.
**Sửa:** ghi rõ trong manifest + đổi hết endpoint chỉ-đọc thành `GET`.

### L15 — Nửa bề mặt tool không có bất kỳ tham chiếu tự động nào (P1 về quy trình)
Grep toàn bộ `tests/` + `scripts/`: **55/110 tên tool không xuất hiện một lần nào**
(danh sách đầy đủ ở §5). `research_project`/`ground_project` chết 100 % mà `pytest` vẫn
**1 087 passed** — nguyên nhân: `tests/test_agent_tools.py:90` chỉ kiểm *tên* có trong
manifest, không `dispatch` chúng.
**Sửa:** thêm một test dispatch mọi tool với tham số tối thiểu và chỉ khẳng định
"không được trả 500" (smoke kiểu này sẽ bắt ngay L1, L2, L3).

### L16 — Những chỗ tôi không kết luận được (cần người quyết)
1. `/cost/check` (`calls` phải là **dict**), `/media/{id}/tags` (body phải là **list**
   trần, không phải `{"tags": ...}`), `/subtitles/simplify` (`captions` là **list[str]**),
   `/resources/explain` (cần `?kind=`) — OpenAPI mô tả không khớp body thực.
   Có thể chỉ cần **sửa tài liệu**, nhưng cũng có thể là dấu hiệu model bị lệch schema.
2. `POST /projects/{id}/documents` → **502** khi truyền `{id,title}` không kèm `pdf_url`
   (`Download failed: No downloadable URL for '2004 Indian Ocean tsunami'`) — endpoint nên
   trả 422 nói rõ "cần pdf_url/landing_url", không phải 502 (lỗi gateway).
3. `seo_ab_evaluate`: 2 arm của tôi → `winner=None, lift=0.0`; cần biết ngưỡng ý nghĩa
   thống kê mà thiết kế mong đợi.
4. `/projects/{id}/facts/reconcile` là **POST** (GET cũng tồn tại) — chưa rõ chủ đích.

---

## 5. ĐÃ KIỂM vs CHƯA KIỂM

### 5.1 Đã kiểm thật
- **110/110 tool** của `/tools/call` (107 qua harness + `create_project`,
  `youtube_download`, `download_audio_clip` chạy tay ở §3.10/L4).
- **88 đường HTTP** (trong 185 endpoint OpenAPI) — tập trung vào mọi nhóm: projects,
  timeline, studio, media, KB, workflow, campaign, graphics, resources, qa, seo, cost,
  audit, external, documents, history, subtitles, agents, `tools`, `health`, `/`.
- **18 ca đầu vào sai** (bảng §3.12).
- **Kiểm tra chéo hạ tầng:** 45 mục library (ffprobe/Pillow); 220 file `src`+`tests`
  qua `ruff format --check`, 149 file qua `mypy`, 1 087 test qua `pytest` — đều xanh
  trên cây này, tức các lỗi ở §4 **không** phải do cây đang hỏng. Frontend ngoài phạm vi.

### 5.2 CHƯA kiểm (và vì sao) — phần này quan trọng để chia việc
1. **97 endpoint HTTP còn lại** (185 − 88): toàn bộ CRUD chi tiết của KB
   (`/kb/{id}/chunks*`, `documents`), `graphics` biến thể, `campaign/shorts`, `external`
   upload/batch, `ai-editor/edit` (multipart), `media/{id}/recook|convert|extract-text|
   tags/{tag}`, `projects/{id}/external/upload`, `workflow/checklist` POST, `projects/{id}/video/upload`…
2. **Provider thật:** chưa từng có API key ⇒ mọi nhánh `strong_llm/anthropic/google/
   deepseek/ollama` **chưa được kiểm hành vi** (kể cả chất lượng prompt, fallback, chi phí).
   Muốn kiểm cần `.env` + key.
3. **ML adapter:** `dub_audio`, `voice_clone`, `separate_audio_stems` bản demucs
   (chưa cài `demucs`), `voice_clone` (chưa có XTTS) — mới kiểm đường *báo lỗi*, chưa kiểm
   đường chạy.
4. **Vision layer thật:** không tồn tại để kiểm (§2) — cần viết.
5. **TTS đa giọng / SSML:** mới kiểm `generate_voiceover` trả 200; chưa so chất lượng
   từng `tts_voice`, chưa kiểm `edge_tts` khi mạng lỗi giữa chừng.
6. **Render dài / nhiều scene:** mới render timeline 3 cảnh (~4 s). Chưa kiểm 30 phút,
   chưa kiểm NVENC (script `qa_nvenc_path.py` tồn tại), chưa kiểm `export_format=webm`.
7. **Transcode lớn:** `media_contact_sheet`/`describe_media` mới chạy trên clip 4 s và webm
   213 s (audio-only); chưa chạy trên video 1080p thật.
8. **Đồng thời:** chưa kiểm 2 request nặng song song (governor), chưa kiểm khi hết đĩa/quyền.
9. **`scripts/`** (253 finding `ruff`, ngoài CI) và **frontend Next.js** (không endpoint nào
   phục vụ nó).

### 5.3 55 tool không xuất hiện trong `tests/` hay `scripts/` (ưu tiên viết test)
`agent_catalog`, `list_script_styles`, `list_media`, `get_media`, `resource_status`,
`resource_explain`, `research_project`, `attach_kb`, `export_brief`, `analyze_script`,
`delete_scene`, `move_scene`, `set_keyframes`, `auto_cut_to_beat`, `media_silence`,
`media_palette`, `extract_audio_track`, `audio_trim`, `audio_loop`, `audio_retime`,
`download_audio_clip`, `image_presets`, `edit_image`, `analyze_image`, `image_op_catalog`,
`describe_image_op`, `suggest_image_edits`, `batch_edit_image`, `begin_image_session`,
`edit_image_session`, `undo_image_session`, `redo_image_session`, `image_session_state`,
`video_effect_catalog`, `apply_video_effect`, `audio_effect_catalog`,
`video_operation_catalog`, `describe_video_operation`, `describe_video_timeline`,
`suggest_video_edits`, `sfx_catalog`, `synthesize_sfx`, `audio_operation_catalog`,
`describe_audio_operation`, `describe_audio`, `suggest_audio_mastering`,
`apply_audio_mastering`, `ai_audio_catalog`, `dub_audio`, `stem_catalog`,
`separate_audio_stems`, `voice_presets`, `enhance_voice`, `duck_music`, `publish_project`.

---

## 6. Thứ tự đề xuất cho người/agent tiếp theo

1. **L1, L2** — sửa 2 tool chết (mỗi cái vài dòng) + test dispatch chúng (L15).
2. **L3** — map lỗi nghiệp vụ → 4xx trong `api/routers/tools.py`; đây là sửa một chỗ
   nhưng cải thiện 16+ ca và biến 500 rỗng thành thông báo dùng được.
3. **L4** — validate nội dung tải về trước khi lưu (chống dữ liệu rác vào library).
4. **L7** — lấy `kind` từ ffprobe + script dọn lại 45 mục library hiện có.
5. **L5, L6** — ổn định hoá render/rebuild (chờ pipeline; giữ scene id) để agent tự động
   chạy được toàn luồng.
6. **L15** — test "mọi tool không được trả 500": rẻ, và là lưới chặn cho mọi lỗi ở trên.
7. Viết Vision layer thật (§2) khi 1–6 xong.

---

### Phụ lục — cách đọc file log

`docs/FEATURE-AUDIT-LOG.md` có 3 phần: bảng tổng hợp theo nhóm, bảng chi tiết từng lượt
gọi (kèm `needs` = phụ thuộc cần có), và **bảng đủ 110 tool** với mã HTTP + thời gian +
ghi chú. `docs/FEATURE-AUDIT-LOG.json` là cùng dữ liệu ở dạng máy đọc (mỗi bản ghi có
`group`, `name`, `target`, `needs`, `status`, `seconds`, `outcome`, `detail`, `note`) —
dùng để so sánh giữa các lần chạy, ví dụ:

```bash
python scripts/feature_audit.py --json /tmp/after.json
# rồi diff hai file theo (target, status) để biết lỗi nào đã hết
```
