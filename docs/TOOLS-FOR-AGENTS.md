# Tools for AI Agents (`/tools`)

Mọi AI agent bên ngoài (Claude Code, Codex CLI, DeepSeek, Gemini CLI, script
Python tùy ý...) có thể vận hành **toàn bộ pipeline** của factory thông qua
hai endpoint. Không cần đọc source — manifest tự mô tả.

## Endpoint

| Endpoint | Mục đích |
|---|---|
| `GET /tools` | Manifest: danh sách tool, mô tả, schema args, ghi chú cách dùng |
| `POST /tools/call` | Thực thi 1 tool: `{"tool": "<name>", "args": {...}}` |

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
-> generate_voiceover -> start_generation
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

Skill cho Claude: `.claude/skills/edit-video-tools/SKILL.md`.
