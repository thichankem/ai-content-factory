# 01 — Kiến trúc & Tech Debt

Tài liệu này mô tả frontend **đang thực sự được tổ chức như thế nào** (không phải như README mô tả), các lớp state, và nợ kỹ thuật xếp theo mức độ.

---

## 1. Bản đồ thực tế

### 1.1 Hai frontend song song

| | Frontend A — Vanilla JS | Frontend B — Next.js |
| :--- | :--- | :--- |
| Tệp | `frontend/index.html`, `app.js`, `editor.js`, `flow.js`, `style.css` | `frontend/src/**` |
| Số dòng | ~15.646 | ~11.000 |
| Được phục vụ bởi | FastAPI tại `GET /` (`src/content_factory/api/routers/index.py:18` → `FRONTEND_DIR / "index.html"`), asset mount tại `/assets` (`src/content_factory/api/app.py:97`) | Dev server riêng cổng 3000 (`npm run dev`), proxy API qua `rewrites()` trong `next.config.mjs` |
| Có trong CI | Không | Không |
| Có test | Không | Không |
| Trạng thái | **Đang chạy production** | Bản viết lại dang dở |

Hai bản này **trùng chức năng gần như hoàn toàn**: Script Studio, NLE Timeline, Photo Lab, DAG Flow, Campaign/Empire, Ingest Hub, SEO, QA, Audio Lab đều có ở cả hai.

Điểm cộng hướng (nếu chọn B): bản Next đã tách `types/`, `hooks/`, `stores/`, `lib/` rõ ràng, dùng TanStack Query + Zustand đúng hướng, có shadcn/ui. Điểm trừ (nếu chọn A): 15k dòng JS thuần, một tệp `app.js` 4.003 dòng và `style.css` 6.228 dòng — gần như không thể refactor an toàn khi không có test.

### 1.2 Luồng dữ liệu của bản Next

```
Component  ──►  hooks/*.ts (TanStack Query)  ──►  lib/api-client.ts:fetchApi
   │                     │
   │                     └── ghi trực tiếp vào ──►  stores/useProjectStore (Zustand)
   │
   └──►  stores/*.ts (Zustand)  ── client state (activeTab, modal, player, timeline)
```

Vấn đề cấu trúc: **server state bị sao chép sang client store**, tạo hai nguồn sự thật (chi tiết ở mục 3.1).

---

## 2. Quyết định phải đưa ra trước mọi việc khác

> Không nên viết thêm tính năng nào trước khi chốt được câu hỏi này.

**Phương án A — Hợp nhất về Next.js.** Next.js trở thành frontend duy nhất; backend phục vụ nó (export tĩnh, hoặc chạy song song và reverse-proxy). Uỷ thác `frontend/index.html` + `app.js` + `editor.js` + `flow.js` + `style.css` vào `/legacy/` rồi xoá dần. Cần: bổ sung test, nâng Next, và bù các tính năng còn thiếu trong bản vanilla.

**Phương án B — Hợp nhất về vanilla.** Giữ bản đang chạy, xoá `frontend/src/`. Rẻ trước mắt nhưng khoá dự án vào 15k dòng JS không type, không test, không component hoá — mọi tính năng tiếp theo đều đắt dần.

**Phương án C — Giữ cả hai, ghi rõ vai trò.** Chỉ hợp lý nếu B thực sự là "làn thử nghiệm song song có thời hạn" và có mốc kết thúc.

Khuyến nghị: **A**, nhưng theo từng bước có thể đảo ngược (xem `05`). Lý do: bản B đã có nền tảng đúng (typed API layer, query cache, component hoá) — nâng cấp nó rẻ hơn việc retrofit TypeScript + test vào 15k dòng vanilla.

> **Kiểm tra trước khi quyết:** chạy `npm run build` trong `frontend/` để xác nhận bản Next build được ở trạng thái hiện tại. Tài liệu này `chưa` chạy build (không cài `node_modules`), nên hãy coi "bản B build được" là giả thuyết cần xác minh.

---

## 3. Các vấn đề kiến trúc

### 3.1 [P1] Server state bị sao chép sang Zustand — hai nguồn sự thật

`frontend/src/hooks/useProjects.ts:11-19` ghi kết quả query vào store:

```ts
queryFn: async () => {
  const data = await fetchApi<Project[]>("/projects");
  setProjects(data);          // ← side effect bên trong queryFn
  return data;
},
```

Và gần như mọi mutation lại gọi `setCurrentProject(project)` trong `onSuccess` (dòng 43, 54, 66, 78, 90, 102, 113).

Hệ quả:
- Cùng một `Project` tồn tại ở **cả** Query cache **và** Zustand. Không có cơ chế nào đảm bảo chúng khớp nhau.
- `setProjects` nằm trong `queryFn` — chạy trong pha fetch; với React StrictMode (`reactStrictMode: true` trong `next.config.mjs`) hàm có thể chạy hai lần, gây thêm một vòng render.
- Vì store luôn được cập nhật thẳng, lỗi invalidate ở 3.2 bị **che khuất** — UI trông vẫn đúng.

**Sửa:** server state chỉ sống trong Query. Zustand chỉ giữ `currentProjectId: string | null`; component đọc project bằng `useQuery(["projects", id])` hoặc chọn từ list.

### 3.2 [P1] Invalidate trỏ vào query key không tồn tại

`frontend/src/hooks/useProjects.ts:43,54,66,78,90,102,113` (7 chỗ) và `frontend/src/hooks/useExternalIngestion.ts:45,75,89` gọi:

```ts
queryClient.invalidateQueries({ queryKey: ["projects", project.id] });
```

Nhưng **không có query nào** dùng key `["projects", id]`. Query duy nhất là `["projects"]` (`useProjects.ts:9`). TanStack khớp theo *tiền tố*: key `["projects"]` **không** bắt đầu bằng `["projects", id]`, nên **10 lời gọi này là no-op hoàn toàn**. Danh sách dự án không bao giờ được refetch sau mutation.

**Sửa:** dùng `["projects"]`, hoặc chuẩn hoá một `queryKeys` factory dùng chung:

```ts
export const qk = {
  projects: ["projects"] as const,
  project: (id: string) => ["projects", "detail", id] as const,
  externalAssets: (id: string) => ["external-assets", id] as const,
};
```

### 3.3 [P1] Không có routing — App Router bị dùng như SPA một route

`frontend/src/app/` chỉ có `layout.tsx` + `page.tsx`. Studio thứ mấy đang mở nằm trong `useUIStore.activeTab` (`stores/useUIStore.ts:37`), và `page.tsx` render bằng chuỗi `{activeTab === "..." && <Studio />}` (dòng ~139-260).

Hệ quả: URL không chia sẻ được, F5 mất ngữ cảnh, nút Back của trình duyệt không dùng được, không deep-link tới một cảnh/dự án cụ thể.

**Sửa:** chuyển sang route thật, `frontend/src/app/(studio)/[projectId]/timeline/page.tsx` v.v., giữ `activeTab` chỉ như trạng thái dẫn xuất từ URL. Bước rẻ nhất trước mắt: đồng bộ `activeTab` với query string (`?view=timeline&project=...`).

### 3.4 [P1] Không có code-splitting, mọi studio nằm trong bundle đầu

`page.tsx:3-27` import tĩnh **11 studio + 8 modal**, và **0 chỗ** dùng `next/dynamic`. Vì `page.tsx` là `"use client"`, toàn bộ cây này vào JS khởi tạo — kể cả Photo Lab, Fusion Compositor, Audio Lab mà người dùng chưa mở.

**Sửa:**

```tsx
const TimelineAssemblyStudio = dynamic(() => import("...").then(m => m.TimelineAssemblyStudio), { ssr: false });
```

Với app studio thuần client thì `ssr: false` hợp lý cho các studio nặng.

### 3.5 [P1] Chọn toàn bộ store bằng destructuring → re-render toàn cây

`useUIStore()` và `useProjectStore()` được gọi **không selector** ở nhiều nơi (ví dụ `page.tsx:50-51`, `SidebarWorkflowNav.tsx:79-91`). Zustand v5 trả về state object, và object đó đổi identity mỗi lần `set`. Nghĩa là: mở/đóng bất kỳ modal nào → identity store đổi → `page.tsx` re-render → **toàn bộ 11 studio và 8 modal re-render theo**.

**Sửa:** luôn dùng selector hẹp, hoặc `useShallow`:

```ts
const activeTab = useUIStore((s) => s.activeTab);
const setActiveTab = useUIStore((s) => s.setActiveTab);
```

### 3.6 [P2] Modal toàn cục luôn mount → query chạy dù chưa mở

8 modal được render vô điều kiện ở cuối `page.tsx` (dòng ~270-278). Radix `Dialog` với `open={false}` không render portal, nhưng **thân component vẫn chạy** → hook bên trong vẫn hoạt động:

- `useAuditCost.ts:6-9` — `useQuery({ queryKey: ["audit-trail"], queryFn: () => fetchApi("/audit") })`, **không có `enabled`** → gọi `GET /audit` ngay lần paint đầu.
- `useSEO.ts:44-48` — `useQuery({ queryKey: ["seo-rules"], queryFn: () => fetchApi("/seo/rules") })`, **không có `enabled`** → gọi `GET /seo/rules` ngay lần paint đầu.

**Sửa:** `enabled: isAuditModalOpen` / `enabled: isSeoModalOpen`; hoặc chuyển sang `<Dialog>{open && <LazyContent/>}</Dialog>`.

### 3.7 [P2] `next.config.mjs` khai 20+ rewrite thủ công thay vì một wildcard

`frontend/next.config.mjs` liệt kê từng tiền tố (`/projects`, `/script`, `/timeline`, `/qa`, ... 21 mục). Dễ quên khi backend thêm router mới — và thực tế đã quên: **không có** rule cho `/uploads` (được mount tại `src/content_factory/api/app.py:94`), nên URL media trả về từ ingest hub sẽ không đi qua proxy.

**Sửa:**

```js
async rewrites() {
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8080";
  return [{ source: "/api/:path*", destination: `${apiBase}/:path*` }];
}
```

...và cho `api-client.ts` dùng tiền tố `/api`. Một rule, không thể lệch.

### 3.8 [P2] Component quá lớn, không có ngân sách dòng cho frontend

`ScriptBriefSettingsPanel.tsx` 887 dòng, `ContentEmpireStudio.tsx` 741, `AudioLabStudio.tsx` 697, `VideoMotionFXStudio.tsx` 608, `DualMonitorPlayer.tsx` 541.

Backend đã có `tests/test_architecture.py` áp ngân sách dòng cho module. Frontend không có gì tương đương.

**Sửa:** thêm luật ESLint chặn tệp > ~300 dòng (hoặc một test đơn giản đọc độ dài tệp), và tách theo tiêu chí "một panel = một tệp".

### 3.9 [P3] Dead code & dependency thừa

- ~~`src/components/layout/Topbar.tsx` — 197 dòng, không nơi nào import~~ — **ĐÃ XÓA 18/09/2026.** Tệp này là tàn dư của một quyết định xóa có chủ ý: `docs/KE-HOACH-TONG-THE.md:1483` ghi *"Loại bỏ hoàn toàn thanh Topbar ở trên đỉnh theo yêu cầu người vận hành"*. Đáng chú ý khi nó còn tồn tại: nó lặp lại **cùng một** `useEffect` bắt `Ctrl+K` như `SidebarWorkflowNav.tsx:93-103`, nên nếu có ai render nó thì hai listener sẽ cùng chạy.
- `@radix-ui/react-dropdown-menu` — khai trong `package.json`, không dùng ở đâu.
- **Hai HTTP client cùng tồn tại:** `lib/api-client.ts` (cũ, 13 tệp còn import) và `lib/api/client.ts` (mới, chưa tệp nào import). Đây là trạng thái chuyển tiếp của refactor đang diễn ra — cần hoàn tất, không để tồn tại song song lâu.
- `tailwindcss-animate` — có trong `plugins` của `tailwind.config.ts` nhưng không được import ở mã nguồn; các class `animate-in`/`fade-in-*` trong `components/ui/dialog.tsx` phụ thuộc plugin này, nên cần giữ **hoặc** gỡ cả hai cho nhất quán.
- `zod` chưa có — xem 3.10.

### 3.10 [P2] Không có validate runtime ở biên

`lib/api-client.ts` parse JSON rồi trả về `T` **không kiểm tra gì**:

```ts
export async function fetchApi<T>(path, options): Promise<T> {
  ...
  return response.json();   // ← ép kiểu mù
}
```

Client mới `lib/api/client.ts` (xem cảnh báo refactor dở dang ở `README.md`) **cải thiện nhiều thứ** — gom một điểm vào duy nhất, có lớp `ApiError` mang `detail` của FastAPI, có `buildQuery`, xử lý `FormData` đúng — nhưng **vẫn không validate**:

```ts
export function apiFetch<T>(path: string, options?: RequestOptions): Promise<T> {
  return request(path, options, (response) => response.json() as Promise<T>);
}
```

`as Promise<T>` vẫn là ép kiểu mù. `types/*.ts` là kiểu chỉ tồn tại lúc biên dịch. Backend đổi field (dự án này backend tiến hoá rất nhanh — nhiều router, mixin, Pydantic) thì frontend nhận `undefined` im lặng, và lỗi nổi lên rất xa nơi phát sinh.

**Bằng chứng cụ thể rằng vấn đề này có thật:** `types/timeline.ts` ghi rõ có **"hai cách viết"** cho cùng một dữ liệu — `duration_seconds`/`image_url` (chuẩn) và `duration`/`asset_url`/`index` (bí danh cho trình soạn thảo). Khi một hợp đồng có hai tên cho một trường, mã tiêu thụ sẽ phải đoán — và đó đúng là những gì đang xảy ra ở `AuditCostModal.tsx:104` với `row.time || row.timestamp`, `row.hash || row.sha256_hash`.

**Sửa:** thêm `zod` + schema ở `lib/schemas/`, validate trong `apiFetch`; hoặc sinh client từ OpenAPI (`/openapi.json` đã có sẵn từ FastAPI) để type và runtime luôn khớp backend.

---

## 4. Bảng xếp hạng nợ kỹ thuật

| # | Vấn đề | Mức | Chi phí sửa | Rủi ro nếu không sửa |
| :--- | :--- | :--- | :--- | :--- |
| 1 | Hai frontend song song | P0 | Lớn | Mọi việc sau đây nhân đôi; tài liệu tiếp tục mâu thuẫn |
| 2 | Invalidate no-op (`["projects", id]`) | P1 | Rất nhỏ | Dữ liệu cũ hiển thị; bị che bởi store |
| 3 | Server state trùng trong Zustand | P1 | Nhỏ | Hai nguồn sự thật, lỗi khó tái hiện |
| 4 | Không routing | P1 | Trung bình | Không chia sẻ/deep-link; không back/forward |
| 5 | Không code-splitting | P1 | Nhỏ | Bundle đầu phình, TTI kém |
| 6 | Destructure toàn store | P1 | Nhỏ | Re-render toàn cây mỗi lần đổi UI state |
| 7 | Modal luôn mount → query thừa | P2 | Rất nhỏ | 2+ request vô ích mỗi lần tải |
| 8 | 21 rewrite thủ công, thiếu `/uploads` | P2 | Rất nhỏ | Media vỡ khi thêm router mới |
| 9 | Không validate runtime | P2 | Trung bình | Lỗi im lặng khi API đổi |
| 10 | Component > 500 dòng | P2 | Lớn | Không thể test/refactor |
| 11 | Dead code + dep thừa | P3 | Rất nhỏ | Nhiễu, tăng thời gian cài |
| 12 | 0 test frontend | P0 | Lớn | Không có lưới an toàn cho chính việc refactor ở trên |

---

## 5. Việc nên làm ngay (thứ tự đề xuất)

1. Chốt phương án A/B/C ở mục 2 và ghi vào `docs/KE-HOACH-TONG-THE.md`.
2. Sửa `invalidateQueries` (3.2) — vài dòng, sửa một lỗi thật.
3. Thêm `enabled` cho `audit-trail` và `seo-rules` (3.6) — vài dòng.
4. Gộp rewrites còn một wildcard `(3.7)` — vài dòng.
5. ~~Xoá `Topbar.tsx`~~ — đã xong 18/09/2026. Còn lại: dep thừa `@radix-ui/react-dropdown-menu` (cần `npm install` để cập nhật `package-lock.json` cùng lúc, nếu không `npm ci` sẽ lỗi).
6. Dựng khung test trước khi refactor bất cứ thứ gì (xem `05`).
