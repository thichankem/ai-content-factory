# Báo cáo kiểm thử tính năng backend — bảng 3 cột

> Phiên: 2026-09-19. Người chạy: agent (Buffy) — **gọi thật 230 lượt** qua HTTP + tool
> dispatch trên một server thật, không dựa vào unit test. Bổ sung cho
> [`FEATURE-AUDIT.md`](FEATURE-AUDIT.md) (danh sách lỗi đã sửa ở các vòng trước).
>
> Số liệu thô: `storage/fa-baseline.json` (trước khi sửa), `storage/fa-final.json` (sau khi
> sửa), bản người đọc được `storage/fa-final.md`. Cả hai đều gitignore.

**Cách tái lập:**

```bash
PATH="$PWD/storage/bin:$PATH" python scripts/feature_audit.py \
    --json storage/fa-final.json --md storage/fa-final.md
PATH="$PWD/storage/bin:$PATH" python scripts/smoke.py     # 64 phép thử tầng HTTP
```

Kết quả tổng: **220/229 → 230/230** lượt trả đúng mã; tổng thời gian **68.9s → 51.0s**.

## Bảng 3 cột

| Tính năng | Vấn đề | Benchmark |
| :--- | :--- | :--- |
| **Audio** (35 lượt): effect, mastering, stems, duck, enhance, loudness, silence, SFX, beat grid, mix, denoise, trim, fade, loop, normalize, retime + 11 endpoint studio | 0 lỗi chức năng. `dub_audio` / `voice_clone` trả **503 đúng thiết kế** (chưa có ML adapter) — kỳ vọng của harness mới là cái sai, đã sửa. | **35/35**, 4.2s. Nặng nhất `apply_audio_effect` 0.74s |
| **Image / Photo** (25): edit, batch, collage, compose, session undo/redo, contact sheet, extract frame, op catalog, presets | 0 lỗi. 2 phép thử 422 là chủ ý (đầu vào xấu). | **25/25**, 1.1s. Nặng nhất `media_contact_sheet` 0.61s |
| **Timeline / NLE** (25): 13 lệnh scene, auto-cut-to-beat, report, render-plan, describe, normalize, suggest, `/timeline/command` | 0 lỗi. 2 phép thử 404 là chủ ý (scene/project không tồn tại). | **25/25**, 0.2s. Nặng nhất `auto_cut_to_beat` 0.10s |
| **Media library** (7): inspect, get, cut ×2, split, join, upload | 0 lỗi ở tầng gọi. **Nhưng rà soát index phát hiện lỗi thật**: mọi entry ghi `width/height = null` (xem mục 2 bên dưới). | **7/7**, 0.7s. Nặng nhất `split_media` 0.23s |
| **Production / render** (14): generation, approve stage, voiceover, render, publish, thumbnail, sensitivity, cost ×2, audit ×2 | Baseline: `publish_project` + `POST /publish` trả **409** vì harness chưa duyệt stage video. Đã sửa harness thành luồng thật: duyệt video → publish → **200**. | **14/14**, 15.2s. Nặng nhất `render_video` **15.17s** — chậm nhất toàn hệ thống |
| **Vision / perception** (12): analyze image, suggest image edits, describe op, describe media, scene cuts, palette, suggest video edits, ai_assist + 2 endpoint studio | 0 lỗi. Ngoài ra đã kiểm chứng bằng "mắt" 47 ảnh — xem mục 1. | **12/12**, 0.1s. Nặng nhất `media_scene_cuts` 0.06s |
| **SEO** (12): score, optimize, keywords, AB plan, AB evaluate, calibrate + 5 endpoint HTTP | 0 lỗi. | **12/12**, <0.1s. Nặng nhất `GET /seo/rules` 0.02s |
| **Network / research / KB** (15): YouTube search + transcript, KB ingest/ask, research, ground, documents search, history ×2, KB CRUD | 0 lỗi. `kb_ingest_url` 404 là chủ ý (URL không tải được). Phụ thuộc mạng ngoài. | **15/15**, 15.5s. Nặng nhất `research_project` 5.17s |
| **Script** (5): analyze, update, export brief, analyze endpoint, `brief.md` | `update_script` 409 là chủ ý (sai stage). | **5/5**, <0.05s |
| **Catalog** (20): toàn bộ catalog tĩnh + `resource_status`, `resource_explain` | 0 lỗi. | **20/20**, 2.6s. Nặng nhất `resource_status` 2.55s (đọc profile máy) |
| **QA / negative** (18): op–effect–preset sai, bytes rác, session lạ, thiếu tham số, ref sai | Toàn bộ trả **4xx/503 kèm thông báo**, không có 500 nào. | **18/18**, 0.6s |
| **HTTP / hệ thống** (42): health, tools, projects, video-project, workflow, research, campaign, graphics, external, facts, media, library, resources, qa, subtitles, agents | **1 lỗi thật: `POST /media/{id}/transcribe` trả 500** khi thiếu `faster-whisper` (phải là 503 — thiếu phụ thuộc tùy chọn). 4 phép thử còn lại gọi sai hợp đồng (enum `asset_type`, thiếu `pdf_url`, thiếu query `kind`, `captions` dạng object). | **42/42**, 10.7s. Nặng nhất `POST /workflow/run` 10.42s |
| **TỔNG** | 9 lượt sai ở baseline → 0 (1 lỗi sản phẩm + 8 kỳ vọng harness) | **230/230**, **51.0s** |

## 9 lượt sai ở baseline và cách xử lý

| # | Lượt gọi | Loại | Xử lý |
| :--- | :--- | :--- | :--- |
| 1 | `POST /media/{id}/transcribe` → **500** | **Lỗi sản phẩm** | Thêm loại lỗi "thiếu phụ thuộc tùy chọn" trong `media.py` + ánh xạ 503 trong `api/errors.py`; test hồi quy trong `test_audit_regressions.py` |
| 2 | `tool:dub_audio` → 503 | Kỳ vọng sai | 503 **có thông báo** là hợp đồng đúng khi chưa đăng ký ML adapter; harness cập nhật kỳ vọng |
| 3 | `tool:voice_clone` → 503 | Kỳ vọng sai | Như trên |
| 4 | `tool:publish_project` → 409 | Kỳ vọng sai | Harness chưa duyệt stage; nay duyệt video rồi publish (200) |
| 5 | `POST /projects/{id}/publish` → 409 | Kỳ vọng sai | Như trên |
| 6 | `POST /projects/{id}/external/import` → 422 | Kỳ vọng sai | Harness gửi `asset_type` không thuộc enum; nay dùng `research_dossier` |
| 7 | `POST /projects/{id}/documents` → 422 | Kỳ vọng sai | Harness chỉ gửi title; nay gửi kèm `pdf_url`/`landing_url` |
| 8 | `GET /resources/explain` → 422 | Kỳ vọng sai | Thiếu query bắt buộc `kind`; nay gửi `kind=render` |
| 9 | `POST /subtitles/simplify` → 422 | Kỳ vọng sai | Hợp đồng là `captions: list[str]`; harness gửi đúng + `level` hợp lệ |

Điểm chung của 8 lượt "kỳ vọng sai": **API trả mã đúng và có thông báo**, chỉ có harness gọi sai
hợp đồng. Số lượt gọi tăng 229 → 230 vì luồng publish được chạy thật (thêm bước duyệt).

## Phát hiện thêm 1: kiểm chứng perception bằng mắt — khớp 47/47

Bài kiểm tra không tin câu chữ của API: agent tự đo **47 ảnh** trong `library/` và
`storage/uploads/feature-audit/` bằng Pillow (luminance trung bình, độ lệch chuẩn σ để suy ra
contrast, palette 3 màu chiếm chỗ), rồi đối chiếu với câu mô tả của `photo_assist.describe_image`.

| Ảnh | Số đo độc lập | API nói | Kết luận |
| :--- | :--- | :--- | :--- |
| `edited/23ad1edaf1ca.png` | lum 74.6, σ 71.5 | "dark / moody with high contrast" | ✓ khớp ngưỡng |
| `edited/1eafb75356c3.png` | lum 59.3, σ 53.1 | "very dark / underexposed with moderate contrast" | ✓ khớp ngưỡng |
| `edited/8b10b4a833ea.png` (contact sheet) | lum 25.9, σ 14.8 | "very dark / underexposed with flat / low contrast" | ✓ khớp ngưỡng |
| `storage/.../shot.png` | lum 14.4, σ 8.0 | "very dark / underexposed with flat / low contrast" | ✓ khớp ngưỡng |

**0 sai lệch trên 47 ảnh** — bảng ngưỡng trong `photo_assist.py` (brightness theo lum, contrast
theo σ, cast theo lệch kênh) phản ánh đúng ảnh thật. Kết quả này cũng bác bỏ một nghi ngờ ban
đầu của tôi (một ảnh σ≈8 bị cho là "high contrast") — ảnh đó là **fixture tự tạo bị phẳng**
(1 màu `30,40,90` trên toàn bộ 640×360), không phải lỗi của sản phẩm.

## Phát hiện thêm 2: metadata media luôn null — lỗi thật, đã sửa

Rà soát `library/media/index.json` sau khi audit xanh cho thấy **4/4 entry có
`width/height = null`**, kể cả video. Hai nguyên nhân độc lập:

1. **Ảnh không bao giờ được probe.** `MediaLibrary.upload_stream` (và `convert`) chỉ đo metadata
   khi `kind in (VIDEO, AUDIO)`, nên ảnh vào thư viện là mất kích thước thước vĩnh viễn.
2. **Probe cứng vào binary `ffprobe`.** `media.probe_media` gọi `resolve_ffprobe()` trực tiếp;
   máy chỉ có `ffmpeg` (đúng kịch bản README mô tả) thì mọi upload đều không đo được gì — kéo
   theo `resolve_kind` mất nhánh suy luận theo stream thật.

Đã sửa:

- `media.probe_media` nay **uỷ quyền cho `media_probe`** — nơi dùng `ffprobe` khi có, và đọc
  `ffmpeg -i` khi không có — rồi giữ nguyên hợp đồng `streams_known` / `has_video` / `has_audio`.
- Thêm `PROBED_KINDS` (video + audio + **image**) dùng chung cho cả upload và convert.
- `scripts/media_reindex.py` nay **backfill** cả `width/height` lẫn `duration_seconds` cho index cũ.

Bằng chứng (chạy thật trên máy **chỉ có ffmpeg**):

```
$ python -m pytest -v tests/test_media.py -k "pixel_size or missing_file"
2 passed, 15 deselected        # 2 test này chạy thật, không skip

$ python scripts/media_reindex.py            # dry run
  [meta]    47adb26fb7be voice.wav: 3.0s
  [meta]    4af029d3c1c8 audit_clip.mp4: 640x360 4.0s
  [meta]    6acdb636f4fb shot.png: 320x200
  [meta]    a140343e4ff9 chart.png: 640x360
Would correct: 0 kind(s), fill 4 size(s).
```

## Kiểm chứng cuối cùng

| Cổng | Kết quả |
| :--- | :--- |
| `ruff check src tests` | sạch |
| `ruff format --check src tests` | 233 file đã đúng định dạng |
| `mypy src` | đúng 5 lỗi **có sẵn** (thiếu `onnxruntime`/`easyocr` trong môi trường này), không phát sinh lỗi mới |
| `pytest` (toàn bộ) | 6 fail — **trùng đúng bộ fail môi trường ở baseline**: `test_mcp_connectivity` (thiếu package `mcp`) + 5 test `test_voice_engine` (fixture tự gọi `ffmpeg` ngoài PATH) |
| `scripts/smoke.py` | **64/64** check |
| `scripts/feature_audit.py` | **230/230** lượt đúng mã |

## Giới hạn môi trường (không đo được ở đây, không phải lỗi)

- **Không có `ffprobe`**: mọi đường đọc đi qua nhánh dự phòng `ffmpeg -i` (đã thêm trong phiên
  này, có test riêng). Máy có `ffprobe` sẽ đi đường ffprobe như cũ.
- **Không có `torch`/`onnxruntime`/`easyocr`/`faster-whisper`**: các tool ML (`dub_audio`,
  `voice_clone`, `transcribe`) trả **503 kèm hướng dẫn cài** — đúng hợp đồng.
- **Không có package `mcp`**: 1 test connectivity bị bỏ qua/không chạy được.
- **Phụ thuộc mạng**: nhóm `network` (YouTube, tải tài liệu) chạy thật nhưng thời gian dao động
  15.3s → 23.1s giữa các lần; số liệu trong bảng là lần chạy cuối.

## File đã đổi trong vòng này

| File | Thay đổi |
| :--- | :--- |
| `src/content_factory/media_probe.py` | nhánh dự phòng ffprobe→ffmpeg; `streams_known` trong `probe()` |
| `src/content_factory/media.py` | 503 cho thiếu phụ thuộc tùy chọn; uỷ quyền probe; `PROBED_KINDS` gồm ảnh |
| `src/content_factory/api/errors.py` | ánh xạ loại lỗi phụ thuộc thiếu → 503 |
| `src/content_factory/ai_video_editor.py` | dùng đường phân giải binary của app thay vì gọi thẳng `"ffprobe"` |
| `scripts/feature_audit.py` | sửa 8 kỳ vọng sai + chạy thật luồng publish |
| `scripts/media_reindex.py` | backfill `width/height/duration` |
| `tests/test_media_probe.py` (mới) | test cho nhánh dự phòng (không cần binary) |
| `tests/test_media.py` | test kích thước ảnh; bỏ điều kiện skip đã lỗi thời |
| `tests/test_audit_regressions.py` | test hồi quy 503 cho `transcribe` |
