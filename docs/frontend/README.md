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
| [`05-LO-TRINH-VA-KIEM-THU.md`](./05-LO-TRINH-VA-KIEM-THU.md) | Lộ trình nâng cấp Next/React, chiến lược kiểm thử, quality gate cho frontend | Dài hạn |

Thứ tự đọc đề xuất: `01` ➔ `02` ➔ `03` ➔ `05` ➔ `04`.

---

## ⚠️ Bộ tài liệu này mô tả thời điểm **trước** lần refactor — đọc mục dưới đây trước

Toàn bộ phần còn lại của bộ tài liệu được viết khi bản Next.js **chưa từng được biên dịch** (không có Node.js trên máy, `types/api.ts` vừa bị xóa, 62 lỗi TypeScript, 50 chỗ `any`). Kể từ đó frontend đã được refactor xong và **lần đầu tiên build được**. Các phát hiện bên dưới vẫn đúng về *nguyên nhân*, nhưng nhiều mục **đã được sửa**; đừng đọc chúng như danh sách việc còn tồn.

### Kết quả refactor (đo lại sau khi hoàn tất)

| Chỉ số | Trước | Sau |
| :--- | :--- | :--- |
| `tsc --noEmit` | **62 lỗi** | **0 lỗi** |
| `next build` | chưa từng chạy | ✓ biên dịch thành công, `/` = 158 kB route / 264 kB first load (đo lại 19/09/2026) |
| Số chỗ `any` | 50 | **0** |
| `alert()` báo việc chưa làm | 10 | **0** |
| Dữ liệu bịa trong UI (audit, SEO, media bin, thumbnail, kịch bản mặc định, re-cook) | 6 màn hình | **0** |
| Gate 1 | không thể vượt qua từ bản Next | đã nối: `PUT /projects/{id}/script` lưu kịch bản + ghi nhận xác nhận bản quyền |
| `Topbar.tsx` (197 dòng, không ai import) | còn | đã xóa |
| `lib/api-client.ts` (client cũ) | còn, 13 tệp import | đã xóa cùng refactor |
| Tệp `.ts/.tsx` / số dòng | 96 / ~11.000 | **98 / 18.255** |

Chi tiết và bằng chứng: ghi chú thay đổi ngày 18/09/2026 ở mục 9 của `docs/KE-HOACH-TONG-THE.md`.

### Vẫn còn nguyên (chưa sửa)

| Hạng mục | Trạng thái |
| :--- | :--- |
| Cấu hình ESLint | **không có** — `"lint": "next lint"` trong `package.json` vẫn không chạy được |
| Tệp kiểm thử frontend | **0** |
| Job frontend trong CI | **không có** |
| `next/dynamic` / code-splitting | **0 chỗ** |
| `error.tsx` / `loading.tsx` / `not-found.tsx` | **không có** (`app/` chỉ có `layout.tsx`, `page.tsx`, `globals.css`) |
| Component > 400 dòng | **16** (lớn nhất: `ScriptBriefSettingsPanel.tsx` 901, `ContentEmpireStudio.tsx` 747, `AudioLabStudio.tsx` 686) |
| `formatTimecode` bỏ qua `VideoProject.fps` | còn |
| Validate runtime của response | còn — client vẫn `response.json() as Promise<T>` |
| Dependency không dùng | `@radix-ui/react-dropdown-menu` (gỡ cần `npm install` để đồng bộ lockfile) |

---

## Snapshot hiện trạng (tháng 9/2026)

### Số liệu đo được

| Hạng mục | Giá trị |
| :--- | :--- |
| Frontend #1 — Vanilla JS (production, FastAPI phục vụ) | `app.js` 4.003 + `editor.js` 1.974 + `flow.js` 1.030 + `index.html` 2.411 + `style.css` 6.228 = **15.646 dòng** |
| Frontend #2 — Next.js 14 (dev-only, cổng 3000) | `frontend/src/**` = **18.255 dòng** trên 98 tệp |
| Tổng | **~33.400 dòng frontend** cho cùng một tập tính năng |
| Số "studio" trong bản Next | 11 studio + 8 modal toàn cục |
| Số component > 400 dòng | 10 (`ScriptBriefSettingsPanel` 887, `ContentEmpireStudio` 741, `AudioLabStudio` 697, `VideoMotionFXStudio` 608, `DualMonitorPlayer` 541, ...) |
| Số lần đúc `any` | 50 |
| Số tệp kiểm thử frontend | **0** |
| Cấu hình ESLint | **không có**, dù `package.json` khai báo `"lint": "next lint"` |
| Dependency không dùng | `@radix-ui/react-dropdown-menu`, `tailwindcss-animate` |
| Component chết | `src/components/layout/Topbar.tsx` (197 dòng, không nơi nào import) — **đã xóa 18/09/2026** |
| `next/dynamic` / code-splitting | **0 chỗ** |
| `error.tsx` / `loading.tsx` / `not-found.tsx` | **không có** |

### Trạng thái cây làm việc: đã refactor xong (ghi chú cập nhật 18/09/2026)

Lúc khảo sát, cây làm việc có một refactor **đang chạy dở** trong `types/` và `lib/`: `types/api.ts` và `types/project.ts` đã bị xóa trong khi **13 tệp còn import chúng**, và `lib/api/client.ts` mới chưa được tệp nào dùng. Bản Next **không build được** và **chưa từng được build** — không có Node.js trên máy, nên 62 lỗi TypeScript tích tụ mà không ai thấy.

Refactor đó đã hoàn tất. Kết quả được ghi ở mục *Kết quả refactor* phía trên. Điều đáng giữ lại từ giai đoạn này là **bài học về quy trình**: một client 17.000 dòng không có typecheck, không có test và không có CI sẽ trôi rất xa mà không báo lỗi. Đó là lý do `scripts/frontend_imports.py` tồn tại và là lý do việc cài Node.js là điều kiện tiên quyết để làm việc trên frontend.

**Ảnh hưởng của refactor tới các phát hiện trong bộ tài liệu:**

| Phát hiện | Trạng thái sau refactor |
| :--- | :--- |
| `01`-3.10 (không validate runtime) | **Còn** — `lib/api/client.ts` vẫn `response.json() as Promise<T>`; một lớp kiểm tra bằng zod vẫn là việc cần làm |
| `02`-L12 (`AbortSignal`) | **Cải thiện một nửa** — `RequestOptions` cho `signal` đi qua tới `fetch`, nhưng không hook nào truyền vào |
| `02`-L13 (`any`) | **Đã sửa** — 0 chỗ `any`; store dùng setter có khoá (`setDuckingParam<K extends DuckingParamKey>`) thay vì `(key: string, val: any)` |
| `02`-L6 (timecode 30 fps) | **Còn** — `VideoProject.fps` đã có trong hợp đồng nhưng `formatTimecode` vẫn bỏ qua |
| `04`-F4 (xung đột `revision`) | **Đúng như dự đoán** — `types/timeline.ts` ghi rõ `revision` cho việc phát hiện sửa đồng thời |
| `02`-L7 (không persist) | **Còn** — `lib/api/*` chưa persist gì; xem thêm ghi chú “store trong bộ nhớ” ở `storage/README.md` |
| `01`-3.9 (trùng lặp/dead code) | **Đã dọn** — `lib/api-client.ts` cũ và `Topbar.tsx` đều đã bị xóa |
| Nhóm P0 “UI báo điều không xảy ra” | **Đã sửa** trên 6 màn hình: audit trail, SEO, media bin, thumbnail, kịch bản mặc định, re-cook |

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
