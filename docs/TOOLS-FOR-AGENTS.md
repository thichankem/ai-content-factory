# Tools for AI Agents (`/tools`)

Mọi AI agent bên ngoài (Claude Code, Codex CLI, DeepSeek, Gemini CLI, script
Python tùy ý...) có thể vận hành **toàn bộ pipeline** của factory thông qua
hai endpoint. Không cần đọc source — manifest tự mô tả.

## Endpoint

| Endpoint | Mục đích |
|---|---|
| `GET /tools` | Manifest: danh sách tool, mô tả, schema args, ghi chú cách dùng |
| `GET /tools/{name}` | Schema đầy đủ của **một** tool |
| `GET /skills` | Index skill (tên, mục đích, tool, số bước) |
| `GET /skills/{name}` | Công thức đầy đủ: bước, tham số, cổng người, guardrails |
| `POST /tools/call` | Thực thi 1 tool: `{"tool": "<name>", "args": {...}}` |

## Tìm tool và skill (đừng nạp cả catalog vào context)

Một việc cần ba tool không đáng phải trả giá bằng toàn bộ manifest:

| Cách | Dùng khi nào |
|---|---|
| `GET /tools?q=duck+music&limit=5` | có một câu mô tả công việc, cần biết tool nào làm |
| `GET /tools?detail=index` | cần nhìn toàn cảnh, mỗi tool một dòng |
| `GET /tools?category=seo` | chỉ quan tâm một nhóm |
| tool `search_tools` | như trên nhưng qua `POST /tools/call` (agent chỉ có MCP) |
| tool `list_skills` / `read_skill` | công thức nhiều bước, hai mức như skill của Claude |

Mọi câu trả lời đều có `total` và `has_more`, nên một trang ngắn không bị hiểu nhầm
thành cả catalog. Tìm kiếm khớp theo tên tool trước, rồi tới bảng từ khóa
(`keywords` trong manifest — "storyboard", "lower the music", "how loud"...),
rồi mới tới mô tả; từ ngắn (≤3 ký tự) chỉ khớp trọn từ, để "one" không kéo về
`voice_clone`.

### Skill được kiểm chứng bằng test

Skill là **tài liệu mà agent thực thi**, nên nó được test như code
(`tests/test_agent_skills.py`): mọi bước phải trỏ tới tool có thật, điền đủ tham số
`required`, không bịa tham số nào, và mọi skill có `approve_stage` phải khai báo
cổng người. Đổi tên tool hay siết schema mà quên skill là test đỏ ngay — không phải
lỗi hiện ra giữa log của một agent lúc 2 giờ sáng.

Bảy công thức hiện có:

| Skill | Việc nó làm |
|---|---|
| `topic-to-published-video` | từ chủ đề tới publish, dừng ở cả hai cổng duyệt |
| `read-a-clip-without-eyes` | biến clip/ảnh thành text để agent suy luận |
| `cut-on-the-beat` | đọc tempo, cắt theo beat, duck nhạc dưới lời |
| `narration-over-music` | mix voice + nhạc tới mức loudness đo được |
| `repair-a-timeline` | sửa đúng thứ timeline_report phàn nàn |
| `qc-before-approval` | gom bằng chứng cho người duyệt |
| `seo-launch-pack` | chấm, viết lại, lên kế hoạch A/B, rồi đo thật |

## Ví dụ nhanh (curl)

```bash
# Khám phá
curl -s http://127.0.0.1:8080/tools | jq '.tools[].name'

# Tạo project
curl -s http://127.0.0.1:8080/tools/call \
  -H 'Content-Type: application/json' \
  -d '{"tool":"create_project","args":{"name":"Titanic","topic":"Chìm tàu Titanic","target_language":"vi","duration_target_seconds":45}}'
```

## Trình tự pipeline chuẩn (usage_notes trong manifest)

```
create_project -> research_project -> attach_kb + ground_project
-> update_script -> analyze_script -> approve_stage(script)   [CỔNG NGƯỜI]
-> build_video_project -> (các tool chỉnh timeline)
-> timeline_report -> render_plan
-> gắn image_url/video_url từng cảnh (media library / /media/{id}/download
   / /edited/{name} / đường dẫn cục bộ) + background_music_url
-> generate_voiceover (TTS mạng) HOẶC audio_mix rồi truyền audio_ref
-> render_video (export_format=webm|mp4)  [xuất MP4 H.264/AAC thật]
-> approve_stage(video)                                        [CỔNG NGƯỜI]
-> publish_project
```

## Tool chỉnh sửa video (chuẩn NLE)

| Tool | Tác dụng |
|---|---|
| `split_scene` / `merge_scene` | Cắt/gộp cảnh giữ nguyên tổng thời lượng |
| `duplicate_scene` / `delete_scene` / `move_scene` | Cấu trúc timeline |
| `set_scene_speed` | Retime 0.5x (slow-mo) .. 2x (fast-forward) |
| `reverse_scene` | Đảo ngược phát media (boomerang) |
| `trim_scene` | Đặt in/out điểm trên nguồn (không đổi timeline) |
| `set_scene_audio` | Gain 0..2 + fade in/out từng cảnh |
| `bulk_update_scenes` | Áp một look (grade/filter/transition) cho nhiều cảnh |
| `set_keyframes` | Track keyframe chuyển động nhiều điểm |
| `add_marker` / `ai_assist` | Marker, auto-fit lời đọc + beat-match BPM |
| `render_video` | Xuất video thật bằng ffmpeg: `export_format=webm\|mp4`, tùy chọn `audio_ref` (bản mix sẵn thay cho voiceover+nhạc) |

`render_video` chỉ chạy ở trạng thái `generating`/`video_review`; không tự duyệt
hay publish. Muốn render lại bản đã duyệt/xuất bản thì phải đưa project về review
qua state machine, không render đè.

## Mapping lỗi

| HTTP | Ý nghĩa |
|---|---|
| 404 | Project/scene không tồn tại |
| 409 | Trạng thái không cho phép (ví dụ approve sai thứ tự) |
| 403 | Source rights chưa được người thật xác nhận |
| 422 | Tool không tồn tại hoặc args sai hình thức |

## Quy tắc bất di bất dịch

1. **Không bao giờ** tự set `source_rights_confirmed: true` — chỉ khi có người
   thật xác nhận. Hai cổng duyệt (script, video) luôn là quyết định người.
2. Sau mỗi chỉnh sửa, gọi `timeline_report` để lấy điểm 0–100 và danh sách
   lỗi; sửa hết lỗi trước khi yêu cầu cổng duyệt tiếp theo.
3. Scene id luôn lấy từ response của `get_project` / `build_video_project`.

Skill cho Google Antigravity:
- `.agents/skills/antigravity-vision-director/SKILL.md` (AI Vision Director & Visual QA)
- `.agents/skills/universal-agent-bridge/SKILL.md` (Protocol đa Agent & 61 Tools)
- Cấu hình MCP: `mcp_config.json` và `.agents/mcp_config.json`

Skill cho Claude Code:
- `.claude/skills/antigravity-vision-director/SKILL.md`
- `.claude/skills/universal-agent-bridge/SKILL.md`
- `.claude/skills/edit-video-tools/SKILL.md`

Hỗ trợ MCP Server (Model Context Protocol):
- Chạy qua stdio hoặc SSE (`python mcp_server.py`)
- Expose 23+ core tools kèm `factory_list_tools` & `factory_call_tool` gọi trực tiếp mọi tool trong registry.

---

## Bộ tool đọc/cắt/ghép media (JSON Schema)

`GET /tools` giờ trả về **input_schema thật** (JSON Schema draft-07 subset) cho từng
tool, nên mọi lớp tool-calling của model đọc được mà không cần người dịch. Số tool
lấy từ `count` của manifest (đừng chép số vào tài liệu — nó đã lệch một lần rồi).
Mười nhóm: `discovery` (kể cả 3 tool registry: `search_tools`, `list_skills`,
`read_skill`), `research`, `script`, `timeline`, `media`, `audio`, `image`, `voice`,
`seo`, `production`.

### Đọc media mà không cần vision

| Tool | Trả về |
|---|---|
| `inspect_media` | duration, stream, codec, fps, kích thước |
| `describe_media` | tất cả những thứ trên + loudness (EBU R128), khoảng lặng, shot cut, palette hex, tempo/beat, và OCR nếu có `tesseract` |
| `media_loudness` | LUFS tích hợp, true peak, gain cần để đạt target |
| `media_silence` | các khoảng lặng kèm mốc thời gian (để siết một take) |
| `media_scene_cuts` | ranh giới cảnh (histogram, không cần model) |
| `media_palette` | màu chủ đạo dạng hex |
| `media_contact_sheet` | một ảnh gồm N khung hình + mốc thời gian của chúng |

### Cắt, nối, tách

`cut_media` (cắt một khoảng), `split_media` (cắt tại nhiều mốc), `join_media` (nối lại),
`extract_audio_track`, `extract_frame_image`.

### Nhạc và tiếng

`music_beat_grid` (BPM + mốc beat/downbeat), `audio_trim`, `audio_fade`, `audio_loop`,
`audio_normalize`, `audio_retime` (đổi tốc độ không đổi cao độ), `audio_mix`
(nhiều track + gain + offset + loop, tự duck nhạc dưới giọng khi một track có
`role: "voice"`), và `auto_cut_to_beat` (đọc tempo rồi beat-match cả timeline).

### Ghép ảnh

`compose_images` (xếp lớp: `x`/`y` theo pixel/phần trăm/tên góc như `bottom-right`,
`scale`, `opacity`, `rotate`, `blend` = normal/multiply/screen/overlay/hard_light/soft_light),
`collage_images` (lưới ảnh kèm caption từng ô).

### Xuất MP4 thật (luồng ảnh + video + tiếng + nhạc)

1. Gắn visual từng cảnh: `image_url`/`video_url` (asset media library,
   `/media/{id}/download`, `/edited/{name}`, hoặc đường dẫn cục bộ trong sandbox).
2. Tiếng: `generate_voiceover` (Edge-TTS/gTTS, cần mạng) hoặc tạo bản mix bằng
   `audio_mix` rồi truyền `audio_ref`.
3. Nhạc: đặt `background_music_url` trên project (được ưu tiên hơn nhạc sinh).
4. `render_video` với `export_format="mp4"` → H.264 + AAC, có `+faststart`.
5. `GET /projects/{id}/video?download=true` để tải file.

Renderer chạy 1 luồng mặc định (giảm RAM/CPU), có thể tăng qua
`CONTENT_FACTORY_RENDER_THREADS` (1–8); `CONTENT_FACTORY_RENDER_MAX_DIMENSION`
giới hạn độ phân giải khi cần tiết kiệm tài nguyên.

### Quy ước chuỗi

Mọi tool media trả về `asset_id` + `url`; bất kỳ tool media nào cũng nhận
`asset_id` đó làm `ref`, nên một quy trình nhiều bước chỉ là một cuộc hội thoại.
Các tham số được khai báo `required` trong schema sẽ bị **chặn ở tầng dispatch**
(HTTP 422 kèm tên field), nên agent luôn biết mình thiếu gì.

### SEO và xuất bản (điểm số + bản viết lại + kiểm chứng)

`seo_rules` (mọi ngưỡng và trọng số của model), `seo_score` (chấm một gói
tiêu đề/mô tả/tag/hashtag cho `youtube` | `youtube_shorts` | `tiktok` | `all`),
`seo_optimize` (viết lại gói đó và trả **mức tăng đã đo được**),
`seo_score_project` (chấm đúng những gì dự án sẽ thật sự đăng: hook lấy từ
kịch bản, thời lượng và nhịp cắt lấy từ timeline, tỉ lệ khung, phụ đề, nhạc,
chapter, chữ trên màn hình), `seo_ab_plan` (cần bao nhiêu impression cho một
A/B test có ý nghĩa), `seo_ab_evaluate` (p-value + lift + phán quyết thắng/thua),
`seo_keywords` (xếp hạng nhu cầu so với cạnh tranh), `seo_calibrate` (học trọng
số từ kết quả thật của kênh).

Ba quy tắc khi agent dùng nhóm này:

1. **Không bịa số liệu.** Muốn chấm theo hiệu suất thật thì truyền `engagement`
   (impressions, views, likes, comments, shares, saves, follows, watch time).
   Không có thì điểm sẽ giảm `confidence` chứ không tự suy diễn.
2. **Chỉ báo cáo mức tăng đã đo.** `changes` của `seo_optimize` chỉ liệt kê những
   thay đổi đã được chấm lại và chứng minh là tăng điểm; gói `pack` trả về chấm
   lại ra đúng `after.score`.
3. **Hai cổng người duyệt không đổi.** Chấm SEO là bước trước khi đăng, không
   thay thế cổng duyệt kịch bản và cổng duyệt video.

`blocking` là danh sách duy nhất có thể kẹp điểm (sai tỉ lệ khung trên nền tảng
dọc, watermark tái đăng, tiêu đề rỗng/quá dài). Còn lại — tiêu đề ngắn, thiếu
hashtag, video 4 phút — chỉ mất điểm, **không** bị coi là "đừng đăng".
