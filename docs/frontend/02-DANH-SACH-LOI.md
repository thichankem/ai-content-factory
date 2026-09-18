# 02 — Danh sách lỗi cụ thể

Mỗi mục có: mức độ, bằng chứng (`file:line`), nguyên nhân, và cách sửa. Toàn bộ đã được xác minh bằng cách đọc mã nguồn; những gì chỉ là phỏng đoán đều ghi rõ.

Khung mức độ: `P0` sai dữ liệu / chặn phát hành · `P1` lỗi rõ ràng · `P2` nợ kỹ thuật · `P3` cải thiện.

---

## P1 — Lỗi thật, sửa được ngay

### L1. `invalidateQueries` trỏ vào query key không tồn tại

**Bằng chứng:** `frontend/src/hooks/useProjects.ts:43,54,66,78,90,102,113` và `frontend/src/hooks/useExternalIngestion.ts:45,75,89`

```ts
queryClient.invalidateQueries({ queryKey: ["projects", project.id] });
```

Query duy nhất cho danh sách dự án dùng key `["projects"]` (`useProjects.ts:9`). TanStack Query khớp theo tiền tố, nên `["projects"]` **không** khớp `["projects", id]` → **10 lời gọi invalidate là no-op** (7 ở `useProjects.ts:43,54,66,78,90,102,113` + 3 ở `useExternalIngestion.ts:45,75,89`). Chỉ `useProjects.ts:31` (dùng `["projects"]`) là có hiệu lực.

**Tác động:** sau khi duyệt Gate 1, duyệt Gate 2, publish, tạo voiceover... danh sách dự án không bao giờ refetch. Lỗi bị che vì `onSuccess` vẫn gọi `setCurrentProject(project)` (ghi thẳng Zustand).

**Sửa:** dùng tiền tố đúng `["projects"]`, hoặc tốt hơn là một factory key dùng chung (xem `01`, mục 3.2).

---

### L2. Trạng thái dự án giả được tiêm vào store khi API rỗng hoặc lỗi

**Bằng chứng:** `frontend/src/app/page.tsx:66-80`

```tsx
useEffect(() => {
  if (projectsQuery.data && projectsQuery.data.length > 0 && !currentProject) {
    setCurrentProject(projectsQuery.data[0]);
  } else if (!currentProject) {
    setCurrentProject({
      id: "demo-project-01",
      name: "Bí mật 3 giây đầu giữ chân khán giả",
      status: "video_review",        // ← trạng thái giả
      source_rights_confirmed: true, // ← quyền nguồn giả
      ...
    });
  }
}, [projectsQuery.data, currentProject, setCurrentProject]);
```

**Tác động — đây là lỗi nghiêm trọng nhất trong danh sách về mặt logic nghiệp vụ:**

- Khi API lỗi (`data === undefined`) **hoặc** khi chưa có dự án nào, UI hiển thị một dự án không tồn tại.
- Dự án giả có `status: "video_review"`, nên thanh bên và Topbar hiển thị badge **"Gate 2: Duyệt video"** — tức hệ thống đang hiển thị như thể một video đã render xong và đang chờ người duyệt.
- Dự án giả có `source_rights_confirmed: true`, trong khi `AGENTS.md` ghi rõ: *"Source rights are never auto-confirmed, by any code path"*. UI đang vi phạm bất biến này.
- Bấm "Duyệt video" → `POST /projects/demo-project-01/approvals` → 404.

**Sửa:** xoá nhánh `else if` này. Thay bằng trạng thái rỗng thật (`EmptyState` + nút "Tạo dự án"), và hiện `projectsQuery.isError` khi gọi API thất bại. Demo data thuộc về seed script của backend, không thuộc `useEffect` của UI.

---

### L3. `catch` báo **thành công** khi thao tác thất bại

**Bằng chứng:** `frontend/src/app/page.tsx:119-131`

```tsx
const handleGenerateCampaign = async () => {
  setCampaignStatus("Đang tổng hợp pillar content thành 5 shorts...");
  try {
    const res = await generateCampaignMutation.mutateAsync();
    setCampaignStatus(`✅ Đã tạo thành công chiến dịch ${res?.shorts?.length || 5} micro-shorts đa kênh!`);
  } catch (e: any) {
    setCampaignStatus(`Đã tạo chiến dịch 5 shorts thành công!`);   // ← báo thành công trong catch
  }
};
```

**Tác động:** mọi lỗi (mất mạng, 500, sai payload) đều hiển thị cho người vận hành là "đã tạo thành công". Với một quy trình có hai cổng duyệt con người, việc UI khẳng định một việc đã xong khi nó chưa xong là lỗi tin cậy, không chỉ là lỗi hiển thị.

**Sửa:** phân biệt nhánh thành công/thất bại; hiển thị `e.message`. Cùng vấn đề ở `handleRunWorkflow` (dòng 108-117) dùng tiền tố "Hoàn tất chạy workflow:" cho cả lỗi.

---

### L4. Năm handler không có xử lý lỗi → promise rejection không được bắt

**Bằng chứng:** `frontend/src/app/page.tsx:82-105`

`handleGenerateVideo`, `handleApproveGate2`, `handlePublish`, `handleVoiceover`, `handleAiAssist` đều `await ...mutateAsync(...)` mà không có `try/catch`. `mutateAsync` **ném** lỗi; không có `onError` ở bất kỳ mutation nào trong `useProjects.ts`. Kết quả: lỗi đi thẳng ra `onClick` → unhandled rejection, người dùng không thấy gì xảy ra.

**Sửa:** thêm `onError` ở tầng hook (một chỗ, phủ hết) hoặc một helper `runMutation()` chung xử lý `toast`.

---

### L5. URL backend hardcode sai cổng và bỏ qua proxy

**Bằng chứng:** `frontend/src/components/media/VideoUrlRecookStudio.tsx:89`

```ts
const response = await fetch("http://127.0.0.1:8000/media/from-url", { ... });
```

Ba vấn đề cùng lúc:

1. **Sai cổng.** Backend mặc định chạy ở **8080** (`scripts/dev.sh`: `PORT="${1:-8080}"`), không phải 8000.
2. **Bỏ qua proxy.** Mọi chỗ khác đi qua `fetchApi` → `/projects/...` → `rewrites()` của Next. Chỗ này gọi thẳng, nên mất khả năng cấu hình qua `NEXT_PUBLIC_API_BASE_URL` và sẽ vỡ khi deploy.
3. **CORS.** Gọi thẳng cross-origin từ `localhost:3000` sang `localhost:8080` cần backend bật CORS đúng — một phụ thuộc ẩn không cần thiết.

**Sửa:** dùng `fetchApi("/media/from-url", ...)`.

---

### L6. Timecode giả định cứng 30 fps

**Bằng chứng:** `frontend/src/lib/utils.ts`
```ts
export function formatTimecode(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  const frames = Math.floor((seconds % 1) * 30);   // ← 30 fps cố định
  return `${mins}:${secs}:${frames}`;
}
```

**Tác động:** trong một NLE, timecode là dữ liệu tham chiếu để cắt/xác nhận cảnh. Với dự án 24/25/60 fps, con số frames hiển thị **sai**. Thêm nữa `formatTimecode` chỉ in `MM:SS:FF`, trong khi README hứa "SMPTE timecode" đầy đủ (`00:00:00:00`).

**Lưu ý:** hợp đồng `VideoProject` **đã có** trường `fps` (xem `types/timeline.ts`), nên bản sửa rất rẻ — chỉ là hàm này chưa nhận tham số. Giá trị fps cần được lấy từ project đang mở, không phải hằng số.

**Sửa:** truyền `fps` vào hàm (`formatTimecode(seconds, fps)`), giữ fps trong `usePlayerStore`, và thêm giờ + drop-frame nếu cần đúng SMPTE.

---

### L7. Trạng thái chỉnh sửa không được lưu → F5 là mất hết

**Kiểm chứng:** tìm `localStorage` / `sessionStorage` / `persist` trong `frontend/src` → **không có kết quả nào**.

**Tác động:** `activeTab`, `sidebarCollapsed`, `brief` (10 chiều), `scriptText` đang gõ dở, `pacingConfig`, `scenes` trong timeline, trạng thái player — tất cả nằm trong bộ nhớ. Refresh là mất. Công cụ dựng phim 10 phút briefing có thể mất trắng vì một lần F5.

**Sửa:** `zustand/middleware` `persist` cho các store client (`useUIStore`, `usePlayerStore`, `usePhotoStore`, `useVideoFXStore`), lưu bản nháp script xuống localStorage có debounce, và autosave `video_project` lên backend (đã có `PUT /projects/{id}/video-project`).

---

## P2 — Chất lượng & tính đúng đắn

### L8. Dữ liệu giả hiển thị như dữ liệu thật

Danh sách, kèm nơi cần sửa:

| Nơi | Dữ liệu giả | Vấn đề |
| :--- | :--- | :--- |
| `components/audit/AuditCostModal.tsx:21-29` | `mockAuditLogs` — 4 bản ghi "GATE_1_SCRIPT_APPROVED", "SOURCE_RIGHTS_CONFIRMED" với hash SHA-256 giả | Dùng làm fallback khi API rỗng (`dòng 29`). **"Provenance Audit Trail" đang hiển thị nhật ký kiểm toán bịa** — phá hỏng chính mục đích của audit trail |
| `components/audit/AuditCostModal.tsx:18-19` | `budgetLimit = 5.0`, `spent = 0.42` | Ngân sách hiển thị là số cứng, không đọc từ `/cost/check` |
| `components/thumbnails/ThumbnailModal.tsx:17-21` | 3 candidate kèm CTR "15.8%" / "12.4%" / "14.1%" | Hiện **trước khi** người dùng bấm tạo; CTR là số bịa nhưng trình bày như dự đoán |
| `components/media/MediaStudio.tsx:38-45` | 6 asset cứng (Kling, Suno, Veo...) | Media Bin không đọc từ `/media` hay `/external/assets` |
| `components/campaign/ContentEmpireStudio.tsx` | Nội dung shorts sinh sẵn | Cần rà lại xem bao nhiêu phần là dữ liệu thật |
| `components/media/VideoUrlRecookStudio.tsx:36-59` | `downloadedMedia` khởi tạo bằng một video TikTok không có thật + transcript | Người dùng thấy kết quả trước khi nạp bất cứ gì |

**Sửa:** mọi danh sách phải khởi tạo rỗng và load từ API; số liệu (CTR, ngân sách, hash) phải đến từ backend hoặc ghi rõ nhãn "ví dụ". Với `AuditCostModal`, fallback giả **phải xoá ngay** — audit log hiển thị mục bịa là lỗi tuân thủ.

### L9. `alert()` dùng làm kênh phản hồi chính

**Bằng chứng:** `frontend/src/app/page.tsx:229` (Pre-flight Checklist), `components/thumbnails/ThumbnailModal.tsx:120` ("Chọn & Dùng").

**Tác động:** `alert()` chặn luồng, không style được, không accessibility tốt, và trong một studio nhiều cửa sổ thì rất phiền. Dự án đã có Radix + shadcn/ui → nên dùng `Dialog` hoặc một toast.

**Sửa:** thêm `sonner` hoặc `@radix-ui/react-toast` và thay toàn bộ `alert()`.

### L10. `setTimeout` sau khi unmount không được dọn

**Bằng chứng:** 55 chỗ `setTimeout` trong `src/`, phần lớn hai dạng:

- `await new Promise((r) => setTimeout(r, 1200))` — mô phỏng độ trễ AI đang chạy thật (xem L11).
- `setTimeout(() => setStatusMessage(null), 2500)` — **không lưu timer id, không clear** — ví dụ `components/media/ExternalIngestionModal.tsx:61,64,80,83,98,101,115,118,127`, `components/media/HtmlSlideDeckStudio.tsx:194,221`, `components/script/ScriptBriefSettingsPanel.tsx:861`.

**Tác động:** đóng modal trong khoảng 2,5 giây → callback chạy trên component đã unmount. React 18 không cảnh báo nữa nên lỗi này âm thầm.

**Sửa:** một hook `useTransientMessage(ms)` tự quản lý `useRef` + `clearTimeout` trong cleanup.

### L11. 55 chỗ mô phỏng AI bằng `setTimeout` rồi báo "đã xong"

**Bằng chứng:** 55 kết quả `setTimeout` trong `src/`. Ví dụ `components/media/MediaStudio.tsx:63-70`:

```tsx
setAiStatus("AI đang kết nối Midjourney v6.1 Harness sinh 2 ảnh nghệ thuật 4K...");
await new Promise((r) => setTimeout(r, 1400));
setAssetsList((prev) => [{ name: "ai_hero_cinematic_portrait_4k.png", source: "Midjourney v6.1", ... }, ...prev]);
setAiStatus("Đã tạo xong ảnh 4K độ nét cao đưa vào Media Bin!");
```

Không có lệnh gọi mạng nào. Không ảnh nào được tạo. Ảnh "4K" chỉ là một đối tượng trong mảng.

Cùng dạng ở `VideoMotionFXStudio.tsx:65,77,87`, `AudioLabStudio.tsx:60,72,82`, `TimelineAssemblyStudio.tsx:38,57,69`, `ContentEmpireStudio.tsx:179,197`, `PhotoLabStudio.tsx:151,161,173`, `ExportReviewStudio.tsx:70,89`, `ScriptStudio.tsx:84`.

**Tác động:** đây là nợ kỹ thuật *về mặt sản phẩm*, không chỉ về mã. Người vận hành không thể phân biệt "AI đã chạy" với "UI vừa giả vờ chạy". Trong một quy trình có cổng duyệt con người, điều đó làm mất giá trị của cả hai cổng.

**Sửa — chọn một trong hai, đừng để lấp lửng:**
- **(a)** Nối vào endpoint thật đã có (`/media/from-url`, `/thumbnail/generate`, `/render/duck`, `/cost/check`, `/seo`, `/qa/*`...). Backend đã có sẵn phần lớn.
- **(b)** Nếu chưa nối được, đổi nhãn rõ ràng thành `[Mô phỏng — chưa nối backend]` và tách bằng một cờ `ENABLE_DEMO_SIMULATION`. Ít nhất người dùng biết mình đang xem gì.

### L12. `AbortSignal` chưa được truyền từ hook

**Bằng chứng:** `lib/api-client.ts` (cũ) không truyền `signal`; TanStack Query hỗ trợ `signal` qua `queryFn({ signal })` nhưng không hook nào dùng.

*Cập nhật so với lần khảo sát đầu:* client mới `lib/api/client.ts` khai `RequestOptions extends Omit<RequestInit, "body" | "method">` và spread `...init` xuống `fetch`, nên **transport đã sẵn sàng nhận `signal`**. Khoảng trống còn lại nằm ở tầng hook: chưa nơi nào lấy `signal` từ `queryFn` để truyền xuống. Mức độ vì thế hạ xuống P2 và cách sửa ngắn hơn.

**Tác động:** đổi dự án liên tục, hoặc search trong khi gõ → response về không đúng thứ tự, kết quả cũ ghi đè kết quả mới (race condition cổ điển).

**Sửa:** `queryFn: ({ signal }) => apiFetch(path, { signal })`.

### L13. `any` làm mất tác dụng của `strict: true`

**Bằng chứng:** 50 chỗ đúc `any` trong `src/`. Ví dụ `components/audit/AuditCostModal.tsx:97` (`row: any`), `components/media/MediaStudio.tsx:35` (`useState<any>`), `components/thumbnails/ThumbnailModal.tsx:17` (`useState<any[]>`), `app/page.tsx:114,124` (`catch (e: any)`).

`tsconfig.json` bật `strict: true`, nhưng `any` mở đường vòng qua toàn bộ hệ thống kiểu. Đặc biệt `row: any` ở audit table che mất việc hai shape khác nhau (`row.time || row.timestamp`, `row.hash || row.sha256_hash`) — dấu hiệu contract với backend không thống nhất.

**Sửa:** `catch (e: unknown)` + type guard; dùng kiểu thật cho mọi `useState`; thêm `@typescript-eslint/no-explicit-any` ở mức `error` (cần ESLint, xem `05`).

**Mẫu tốt để noi theo:** client mới `lib/api/client.ts` (xem `README.md`) dùng `unknown` cho `detail`, có type guard trong `describe()`, và không có một `any` nào. Nếu toàn bộ `src/` được viết theo chuẩn đó, luật lint ở trên sẽ không cần tới ngoại lệ nào.

### L14. Không có error boundary, loading state, hay empty state

**Kiểm chứng:** `src/app/` chỉ có `globals.css`, `layout.tsx`, `page.tsx`. Không có `error.tsx`, `loading.tsx`, `not-found.tsx`.

**Tác động:** một lỗi render ở bất kỳ studio nào (11 studio, hàng nghìn dòng) làm **trắng toàn bộ ứng dụng**, mất luôn công việc chưa lưu. Không có `Suspense` → không có chỗ để khai báo trạng thái chờ.

**Sửa:** `src/app/error.tsx` + `src/app/global-error.tsx`, và một `<StudioBoundary>` bao quanh phần render từng studio để lỗi cục bộ không kéo sập cả app.

### L15. Nút tải file trong Media Bin không làm gì

**Bằng chứng:** `components/media/MediaStudio.tsx:300-303` — nút "Tải Lên File (Upload)" không có `onClick`.

Mặt khác, `useExternalIngestion.uploadAssetMutation` (`hooks/useExternalIngestion.ts:48-78`) **đã hoạt động đầy đủ** (FormData, `POST /projects/{id}/external/upload`, có xử lý lỗi). Tức là backend và hook sẵn sàng, chỉ thiếu dây nối.

**Sửa:** nối nút vào `uploadAssetMutation`.

---

## P3 — Nhỏ nhưng nên dọn

### L16. Mã chết và dependency thừa

- `src/components/layout/Topbar.tsx` (197 dòng) — không nơi nào import. Nó cũng lặp lại `useEffect` bắt `Ctrl+K` giống `SidebarWorkflowNav.tsx:93-103` → nếu render, hai listener cùng chạy và `setCommandBarOpen(true)` gọi hai lần.
- `@radix-ui/react-dropdown-menu` trong `package.json` — không dùng.
- `frontend/README.md` mô tả cấu trúc không khớp thực tế (ví dụ liệt kê `frontend/index.html` là "Vanilla/FastAPI fallback entry (satisfies smoke test)" trong khi thực tế nó **chính là** ứng dụng production).

### L17. Trùng lặp thông báo lỗi và format số

`hooks/useExternalIngestion.ts:53-56`, `hooks/useSEO.ts:52`, `hooks/useWorkflowDAG.ts`... đều lặp lại khối:

```ts
if (!projectId) throw new Error("No project selected");
```

Ngoài ra logic `((size || 15000000) / (1024 * 1024)).toFixed(1)` để format MB lặp lại trong `VideoUrlRecookStudio.tsx:120`. Theo `AGENTS.md`: *"Shared helpers go in the module that owns the concept — never copy a tokenizer, slug or error mapper into a second place."* → gom vào `lib/format.ts` và một `requireProjectId()`.

### L18. Magic number về thời gian chờ AI

Các giá trị `1200`, `1400`, `900`, `1100`, `1600` ms xuất hiện rải rác (55 chỗ) không có hằng số dùng chung, không có nguồn gốc. Khi chuyển sang gọi API thật (L11) thì chúng sẽ biến mất — nhưng nếu còn dùng ở chế độ demo, nên có một bảng hằng số duy nhất.

---

## Bảng tổng hợp

| ID | Lỗi | Mức | Chi phí |
| :--- | :--- | :--- | :--- |
| L1 | `invalidateQueries` no-op | P1 | Rất nhỏ |
| L2 | Dự án giả + `source_rights_confirmed: true` giả | **P0** | Nhỏ |
| L3 | `catch` báo thành công | **P0** | Rất nhỏ |
| L4 | Không bắt lỗi mutation | P1 | Nhỏ |
| L5 | Hardcode `127.0.0.1:8000` | P1 | Rất nhỏ |
| L6 | Timecode cứng 30 fps | P1 | Nhỏ |
| L7 | Không persist, F5 mất hết | P1 | Nhỏ–TB |
| L8 | Dữ liệu giả hiển thị như thật (audit log!) | **P0** | TB |
| L9 | `alert()` làm kênh phản hồi | P2 | Nhỏ |
| L10 | `setTimeout` không dọn | P2 | Nhỏ |
| L11 | 55 chỗ mô phỏng AI | P2 | Lớn |
| L12 | Không có `AbortSignal` | P2 | Nhỏ |
| L13 | 50 chỗ `any` | P2 | TB |
| L14 | Không error/loading/empty state | P2 | Nhỏ |
| L15 | Nút upload rỗng | P2 | Rất nhỏ |
| L16–L18 | Dead code, trùng lặp, magic number | P3 | Nhỏ |

**Ba mục P0 xử lý trước:** L2, L3, L8. Cả ba đều cùng một chủ đề — **UI đang khẳng định những điều không đúng** (dự án tồn tại, thao tác thành công, nhật ký kiểm toán có thật). Với một quy trình mà toàn bộ giá trị nằm ở hai cổng duyệt con người, đó là lỗi nghiêm trọng nhất có thể có.
