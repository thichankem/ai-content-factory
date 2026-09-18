# Frontend Review: `docs/frontend/`

Bộ tài liệu này là **báo cáo đánh giá frontend** của AI Content Factory: kiến trúc hiện tại, tech debt, danh sách lỗi cụ thể, rủi ro bảo mật, và đề xuất chức năng.

> **Ngôn ngữ:** theo `AGENTS.md`, tài liệu trong `docs/` mặc định là tiếng Anh; ngoại lệ duy nhất là `KE-HOACH-TONG-THE.md` — giữ tiếng Việt *vì người vận hành viết tiếng Việt*. Bộ tài liệu này là **báo cáo gửi trực tiếp cho người vận hành** nên giữ tiếng Việt theo cùng lý do. Nếu muốn chuẩn hoá sang tiếng Anh, hãy ghi rõ trong `AGENTS.md` để tránh lệch quy ước.

---

## Mục lục

| Tệp | Nội dung | Mức độ ưu tiên |
| :--- | :--- | :--- |
| [`01-KIEN-TRUC-VA-TECH-DEBT.md`](./01-KIEN-TRUC-VA-TECH-DEBT.md) | Kiến trúc tổng thể, quan hệ với backend, các lớp state, dead code, nợ kỹ thuật | Đọc trước |
| [`02-DANH-SACH-LOI.md`](./02-DANH-SACH-LOI.md) | Danh sách lỗi cụ thể kèm `file:line`, nguyên nhân, cách sửa | Sửa được ngay |
| [`03-BAO-MAT-VA-DO-TIN-CAY.md`](./03-BAO-MAT-VA-DO-TIN-CAY.md) | Bảo mật, phơi nhiễm qua proxy, CVE của Next.js 14, và vấn đề "UI báo thành công giả" | Cao |
| [`04-CHUC-NANG-DE-XUAT.md`](./04-CHUC-NANG-DE-XUAT.md) | Đề xuất chức năng mới: WebCodecs/WebGPU, undo/redo, offline, cộng tác, a11y, i18n | Trung hạn |
| [`05-LO-TRINH-NANG-CAP-VA-KIEM-THU.md`](./05-LO-TRINH-NANG-CAP-VA-KIEM-THU.md) | Lộ trình nâng cấp Next/React, chiến lược kiểm thử, quality gate cho frontend | Dài hạn |

Thứ tự đọc đề xuất: `01` ➔ `02` ➔ `03` ➔ `05` ➔ `04`.

---

## Snapshot hiện trạng (tháng 9/2026)

### Số liệu đo được

| Hạng mục | Giá trị |
| :--- | :--- |
| Frontend #1 — Vanilla JS (production, FastAPI phục vụ) | `app.js` 4.003 + `editor.js` 1.974 + `flow.js` 1.030 + `index.html` 2.411 + `style.css` 6.228 = **15.646 dòng** |
| Frontend #2 — Next.js 14 (dev-only, cổng 3000) | `frontend/src/**` = **~11.000 dòng** |
| Tổng | **~26.600 dòng frontend** cho cùng một tập tính năng |
| Số "studio" trong bản Next | 11 studio + 8 modal toàn cục |
| Số component > 400 dòng | 10 (`ScriptBriefSettingsPanel` 887, `ContentEmpireStudio` 741, `AudioLabStudio` 697, `VideoMotionFXStudio` 608, `DualMonitorPlayer` 541, ...) |
| Số lần đúc `any` | 50 |
| Số tệp kiểm thử frontend | **0** |
| Cấu hình ESLint | **không có**, dù `package.json` khai báo `"lint": "next lint"` |
| Dependency không dùng | `@radix-ui/react-dropdown-menu`, `tailwindcss-animate` |
| Component chết | `src/components/layout/Topbar.tsx` (197 dòng, không nơi nào import) |
| `next/dynamic` / code-splitting | **0 chỗ** |
| `error.tsx` / `loading.tsx` / `not-found.tsx` | **không có** |

### ⚠️ Cây làm việc đang có refactor dở dang (không phải do bộ tài liệu này)

Tại thời điểm khảo sát, `git status` cho thấy có thay đổi **đang diễn ra** trong `frontend/src/types/` và `frontend/src/lib/` mà tài liệu này **không** tạo ra:

| Trạng thái | Tệp |
| :--- | :--- |
| Đã thêm (mới) | `lib/api/client.ts`, `types/agent.ts`, `types/campaign.ts`, `types/common.ts`, `types/external.ts`, `types/library.ts`, `types/research.ts`, `types/voice.ts`, `types/workflow.ts` |
| Đã xóa | `types/api.ts`, `types/project.ts` |
| Đã sửa | `types/script.ts`, `types/timeline.ts` |

**Trạng thái hiện tại đang không build được.** `types/api.ts` và `types/project.ts` đã bị xóa khỏi đĩa nhưng vẫn còn **13 tệp import chúng** (`ScriptStudio.tsx`, `useProjects.ts`, `useQA.ts`, `useScriptEngine.ts`, `useThumbnails.ts`, `useAuditCost.ts`, `useAgentBridge.ts`, `useTimelineCommands.ts`, `useWorkflowDAG.ts`, `useProjectStore.ts`, `useTimelineStore.ts`, …). Song song đó, `lib/api/client.ts` mới đã có nhưng **chưa tệp nào import nó**. Nghĩa là bước di chuyển đã đi được nửa đường: hợp đồng mới đã dựng xong, điểm nối chưa được chuyển.

> Tài liệu này **không** đánh giá hay sửa các tệp đó — chúng thuộc về luồng công việc khác. Ghi chú ở đây chỉ để tránh nhầm lẫn về nguồn gốc thay đổi.

**Ảnh hưởng tới các phát hiện trong bộ tài liệu:**

| Phát hiện | Ảnh hưởng | Hành động |
| :--- | :--- | :--- |
| `01`-3.10 (không validate runtime) | Refactor **chưa giải quyết**: client mới vẫn `response.json() as Promise<T>` — vẫn là ép kiểu mù | Giữ nguyên, đổi đường dẫn sang `lib/api/client.ts` |
| `02`-L12 (`AbortSignal`) | **Đã cải thiện một nửa**: `RequestOptions extends Omit<RequestInit, ...>` nên `signal` đi qua được tới `fetch`; nhưng không hook nào truyền vào | Hạ nhẹ mức độ, sửa lại mô tả |
| `02`-L13 (`any`) | Client mới VIẾT BẰNG TIẾNG ANH có kiểu đầy đủ, dùng `unknown` thay `any` — đúng hướng | Cập nhật: đây là mẫu tốt để noi theo |
| `02`-L6 (timecode 30 fps) | **Trở nên dễ sửa hơn**: `VideoProject.fps` giờ đã có trong hợp đồng, nhưng `formatTimecode` vẫn bỏ qua nó | Giữ nguyên, bổ sung lưu ý |
| `04`-F4 (xung đột `revision`) | **Được xác nhận**: `types/timeline.ts` ghi rõ `revision` để client phát hiện sửa đồng thời | Giữ nguyên |
| `02`-L7 (không persist) | Một phần: `ProjectStatus` giờ có thêm `"failed"` — cần phản ánh ở store | Mở rộng |
| `01`-3.9 (trùng lặp/dead code) | **Phát sinh thêm**: `lib/api-client.ts` cũ và `lib/api/client.ts` mới cùng tồn tại | Bổ sung vào danh sách dọn dẹp |

**Khuyến nghị:** hoàn tất refactor đó trước, rồi chạy `npm run type-check` để xác nhận cây đã xanh. Mọi công việc theo bộ tài liệu này nên bắt đầu từ một baseline build được.

### Phiên bản thư viện so với bản mới nhất

| Thư viện | Đang dùng | Mới nhất (9/2026) | Ghi chú |
| :--- | :--- | :--- | :--- |
| Next.js | `^14.2.15` — lockfile ghim **14.2.35** | **16.3.4** | Bản ghim **đã vá** CVE-2025-29927 (vá từ 14.2.25), nhưng 14.x đã xa bản mới nhất — xem `03`, mục A5 |
| React | `^18.3.1` | 19.2 | Next 16 dùng React Canary kèm các tính năng 19.2 |
| React Compiler | chưa dùng | **stable 1.0** (từ 10/2025) | Xoá phần lớn `useMemo`/`useCallback` thủ công |
| TanStack Query | `^5.59.16` | v5.x (React) | v6 hiện chỉ có cho Svelte — React vẫn v5, không cần vội |
| Zustand | `^5.0.0` | v5.x | Ổn định |
| Tailwind CSS | `^3.4.14` | v4 | v4 đổi engine cấu hình, cần lộ trình riêng |

---

## Hiện trạng nằm ở đâu — đọc cái này trước

Điểm quan trọng nhất, và là nguồn gốc của phần lớn vấn đề còn lại:

> **Có hai frontend độc lập cho cùng một sản phẩm.** FastAPI phục vụ bản vanilla JS tại `/` (`frontend/index.html`, xem `src/content_factory/api/routers/index.py:18`), và đó là bản **đang chạy thật**. Bản Next.js trong `frontend/src/` chạy ở cổng 3000 như một dev server riêng, **không** được backend phục vụ và không có trong CI.

Hệ quả trực tiếp:

1. Mọi tính năng mới phải làm hai lần, hoặc bản này lệch bản kia.
2. `README.md` gốc và `frontend/README.md` mô tả hai kiến trúc khác nhau cho cùng dự án — tài liệu đã mâu thuẫn.
3. Quality gate (pytest, ruff, mypy, smoke test 64 checks) chỉ phủ backend. Bản vanilla 15k dòng và bản Next 11k dòng **không có test nào**.
4. Không rõ đâu là source of truth khi có tranh chấp hành vi.

Quyết định cần đưa ra (xem `01-KIEN-TRUC-VA-TECH-DEBT.md`, mục 2) là **giữ một, gộp hoặc chôn cái còn lại** — trước khi đầu tư thêm bất kỳ tính năng nào.

---

## Cách dùng bộ tài liệu này

- Mỗi phát hiện đều kèm **bằng chứng `file:line`** để kiểm tra lại được, và **ít nhất một cách sửa**.
- Không có mục nào là suy đoán: những gì chưa xác minh đều được ghi rõ là *giả thuyết cần đo*.
- Khung mức độ: `P0` chặn phát hành / sai dữ liệu, `P1` lỗi rõ ràng, `P2` nợ kỹ thuật, `P3` cải thiện.
- Khi hoàn thành một mục, hãy ghi lại vào `docs/KE-HOACH-TONG-THE.md` (mục 9 — Nhật ký thay đổi) theo mẫu sẵn có.
