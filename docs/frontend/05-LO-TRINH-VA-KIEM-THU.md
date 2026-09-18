# 05 — Lộ trình nâng cấp & Kiểm thử

Tài liệu này trả lời hai câu hỏi: **làm gì trước** và **làm sao biết mình không phá vỡ thứ gì**.

Nguyên tắc xuyên suốt: **dựng lưới an toàn trước khi refactor.** Frontend hiện có **0 tệp kiểm thử** cho ~26.600 dòng mã. Mọi đề xuất ở `01`, `02`, `04` đều là refactor — và refactor không có test là đánh bạc.

---

## 1. Quality gate: hiện trạng đang lệch nghiêm trọng

| Lớp | Backend | Frontend |
| :--- | :--- | :--- |
| Lint | `ruff check` — sạch | **Không có cấu hình ESLint nào**, dù `package.json` khai `"lint": "next lint"` |
| Format | `ruff format` — sạch | Không có |
| Kiểu | `mypy src` strict — sạch | `tsc --noEmit` có script, nhưng 50 chỗ `any` vô hiệu hoá nó ở những chỗ quan trọng |
| Test | 347–377 test pytest | **0** |
| Build | — | Có script, **không chạy trong CI** |
| Kiến trúc | `tests/test_architecture.py` áp ngân sách dòng & quy tắc mixin | Không có |
| CI | `.github/workflows/ci.yml` đầy đủ | **Không có job nào** |

Nói cách khác: dự án có kỷ luật chất lượng rất tốt ở backend và **bằng không** ở frontend. Đây là khoảng cách lớn nhất trong toàn bộ tài liệu này.

---

## 2. Giai đoạn 0 — Lưới an toàn

### 2.1 Test đầu tiên nên viết là gì

Đừng bắt đầu bằng unit test cho component. Bắt đầu bằng **bài test E2E mô phỏng đúng quy trình nghiệp vụ**, vì nó phát hiện được lỗi nghiêm trọng nhất đã tìm thấy (`03`-B2: Gate 1 bất khả thi).

**Bài test "Gate 1 → Gate 2" (bài test có giá trị nhất trong toàn bộ frontend):**

```
1. Mở studio, tạo một dự án mới qua UI.
2. Sinh hoặc dán kịch bản.
3. Lưu kịch bản.
4. Xác nhận quyền nguồn.
5. Bấm "Phê Duyệt Kịch Bản (Pass Gate 1)".
6. Kỳ vọng: trạng thái dự án chuyển sang "script_approved".
```

Chạy bài test này **ngay bây giờ** và **cố ý để nó thất bại**. Bước 6 sẽ không bao giờ đạt được, đúng như phân tích ở `03`-B2. Như vậy bạn có một bài test đỏ tương ứng với một lỗi P0 thật, và nó sẽ chuyển xanh khi bạn nối `updateScriptMutation`. Đây là cách chứng minh giá trị của việc dựng test harness mà không phải tranh luận lý thuyết.

Sau đó mở rộng dần: Gate 1 → `generating` → Gate 2 → `published`, mỗi bước một assertion.

### 2.2 Bộ công cụ đề xuất

| Lớp | Công cụ | Lý do |
| :--- | :--- | :--- |
| Chạy test + component test | **Vitest** + React Testing Library | Chuẩn thực tế 2025–2026 cho React; dùng chung cấu hình Vite/ESM |
| Giả lập API | **MSW** (Mock Service Worker) | Chặn ở tầng mạng → test hook `useProjects` thật sự chạy qua `fetch`, không phải mock module |
| E2E | **Playwright** | Chạy được cả Chromium lẫn WebKit — cần thiết vì F1 phụ thuộc WebCodecs/WebGPU (Chromium-first) |
| Kiểm tra hợp đồng | Suy ra kiểu từ **`/openapi.json`** | FastAPI đã xuất sẵn; hoặc `orval`/`openapi-typescript` để sinh client có kiểu |
| Sổ tay component (tuỳ chọn) | **Storybook** + Vitest addon | Hữu ích cho thư viện component, nhưng **không** ưu tiên bằng 2.1 |

**Điểm quan trọng về MSW:** nó cho phép test đúng thứ đang hỏng — **hợp đồng giữa frontend và backend**. Ví dụ: test khẳng định rằng sau khi mutation thành công, `["projects"]` **được refetch** sẽ phát hiện lỗi L1 (`invalidateQueries` no-op) ngay lập tức. Và test khẳng định `PUT /projects/{id}/script` **được gọi** với `source_rights_confirmed: true` sẽ phát hiện B2.

### 2.3 Thứ tự viết test (từ dễ/nhiều giá trị đến khó)

1. **Hàm thuần** — `lib/utils.ts` (`formatTimecode`, `cn`). Bắt đầu ở đây để dựng khung; test `formatTimecode` với fps 24/25/30/60 chính là bài test cho lỗi L6.
2. **Hợp đồng hook với MSW** — `useProjects`, `useExternalIngestion`, `useWorkflowDAG`. Đây là nơi chứa các lỗi thật (L1, L4, L12).
3. **Component có logic** — `ScriptBriefSettingsPanel` (10 chiều briefing, đáng test), `TimelineVisualizer`, `PropertiesInspector`.
4. **E2E Playwright** — chỉ một vài luồng, nhưng là luồng nghiệp vụ (quy trình 7 bước + hai cổng).

Tỉ lệ hợp lý: **nhiều test ở lớp 1–2, rất ít ở lớp 4.** E2E chậm và dễ vỡ; giá trị của nó nằm ở việc phủ *hành trình*, không phải phủ *chi tiết*.

### 2.4 Test kiến trúc cho frontend (song song với backend)

Dự án đã có tiền lệ rất tốt ở `tests/test_architecture.py` (ngân sách dòng, quy tắc mixin). Hãy làm điều tương tự cho frontend — rẻ và ngăn chặn thoái hoá:

| Luật | Cách kiểm | Chống lại |
| :--- | :--- | :--- |
| Không tệp `.tsx` nào > 300 dòng | Đọc độ dài tệp | Vấn đề `01`-3.8 |
| Không gọi `fetch` trực tiếp ngoài `lib/api-client.ts` | Regex trên mã nguồn | Lỗi L5, `01`-3.7 |
| Không có `console.*` trong `src/` (trừ `lib/logger`) | Regex | Nhiễu |
| Không chuỗi tiếng Việt literal trong JSX | Regex ký tự có dấu | `04`-F14 |
| Không export nào của `src/` bị bỏ không dùng | `knip` hoặc `ts-prune` | Dead code như `Topbar.tsx` (`01`-3.9) |
| Mọi `queryKey` sinh từ một factory dùng chung | Regex trên `queryKey:` | Lỗi L1 |

Sáu luật này chặn được gần hết các vấn đề đã nêu ở `01` và `02`, và chúng không cần chạy trình duyệt.

---

## 3. Giai đoạn 1 — Lint, format, CI

### 3.1 Dựng ESLint (đang thiếu hoàn toàn)

```bash
npm i -D eslint eslint-config-next @typescript-eslint/eslint-plugin \
         @typescript-eslint/parser eslint-plugin-jsx-a11y
```

Cấu hình tối thiểu, bật các luật nhắm đúng vào lỗi đã tìm thấy:

| Luật | Mức | Nhắm vào |
| :--- | :--- | :--- |
| `@typescript-eslint/no-explicit-any` | error | 50 chỗ `any` (`02`-L13) |
| `jsx-a11y/click-events-have-key-events` | error | `div` + `onClick` (`04`-F12) |
| `jsx-a11y/no-static-element-interactions` | error | như trên |
| `react-hooks/exhaustive-deps` | error | Effect thiếu phụ thuộc |
| `no-restricted-globals` (`alert`, `confirm`) | error | `02`-L9 |
| `@typescript-eslint/no-floating-promises` | error | `02`-L4 (promise không được bắt) |

`no-floating-promises` đặc biệt đáng giá ở đây: nó sẽ chỉ ra chính xác 5 handler ở `page.tsx` đang bỏ rơi promise.

> **Lựa chọn thay thế năm 2026:** nếu ưu tiên tốc độ, **oxlint** + **oxfmt** hoặc **Biome** thay thế ESLint + Prettier. Với dự án Next.js đang cần `eslint-config-next` và các luật `jsx-a11y`/`react-hooks`, ESLint vẫn là đường an toàn hơn; có thể chạy oxlint như lớp nhanh ở giai đoạn sau.

### 3.2 Thêm job frontend vào CI

`.github/workflows/ci.yml` hiện chỉ chạy backend. Thêm:

```yaml
  frontend:
    runs-on: ubuntu-latest
    defaults: { run: { working-directory: frontend } }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 22, cache: npm, cache-dependency-path: frontend/package-lock.json }
      - run: npm ci
      - run: npm run type-check
      - run: npm run lint
      - run: npm run test -- --run
      - run: npm run build
```

Dùng `npm ci` (không phải `npm install`) để tôn trọng `package-lock.json` — quan trọng ở đây vì chính lockfile quyết định bạn đang chạy Next `14.2.35` chứ không phải `^14.2.15`.

**Điều kiện để job này có ý nghĩa:** phải xanh. Nếu `npm run lint` đang đỏ vì chưa có cấu hình, hãy dựng cấu hình trước (3.1), hoặc tạm `continue-on-error: true` kèm một issue theo dõi — nhưng đừng để nó đỏ vĩnh viễn, vì như vậy CI sẽ bị bỏ qua.

### 3.3 Chuẩn hoá kiểm tra kiểu

- Chạy `npm audit` và ghi kết quả vào `docs/KE-HOACH-TONG-THE.md` (`03`-A5).
- Xoá `@radix-ui/react-dropdown-menu` khỏi `package.json` (không dùng).
- ~~Xoá `Topbar.tsx` (dead code)~~ — đã xong 18/09/2026. Còn lại: gỡ `@radix-ui/react-dropdown-menu` khỏi `package.json`, **nhớ cập nhật `package-lock.json` cùng lúc** (nếu không `npm ci` trong CI sẽ lỗi vì hai tệp lệch nhau).

### 3.4 Ngân sách hiệu năng

Thêm một bước kiểm tra kích thước bundle với một ngưỡng được ghi rõ. Không có ngân sách thì kích thước bundle chỉ tăng. Ngưỡng ban đầu nên **đo trước rồi mới đặt** (không đặt bừa) — hãy chạy `npm run build` và ghi lại con số hiện tại làm mốc.

---

## 4. Giai đoạn 2 — Nâng cấp nền tảng

> **Điều kiện tiên quyết:** hoàn thành Giai đoạn 0 và 1. Nâng cấp framework mà không có test là cách chắc chắn nhất để biến một buổi chiều thành một tuần.

### 4.1 Lộ trình phiên bản

| Bước | Từ | Đến | Ghi chú |
| :--- | :--- | :--- | :--- |
| 2a | Next 14.2.35 | **Next 15** | Dùng codemod chính thức. Điểm phá vỡ cần chú ý: `fetch` mặc định không cache, `params`/`searchParams` trở thành async, Route Handlers thay đổi mặc định |
| 2b | React 18 | **React 19** | `forwardRef` không còn bắt buộc (đã thấy dùng nhiều trong `components/ui/*`) |
| 2c | Next 15 | **Next 16** | Bản App Router ổn định mới nhất (16.3.x, 9/2026), dùng React canary kèm tính năng 19.2 |
| 2d | — | **React Compiler** | Đã **stable 1.0 từ 10/2025**, tương thích React 17+. Bật, rồi **xoá** `useMemo`/`useCallback` thủ công. Cần plugin ESLint của compiler để phát hiện mã không tuân thủ quy tắc |
| 2e | Tailwind 3.4 | Tailwind 4 | **Tách riêng một đợt.** v4 đổi cách cấu hình (CSS-first). Không gộp vào cùng đợt nâng Next |

**Thứ tự bắt buộc:** 2a → 2b → 2c. Bỏ qua bước giữa sẽ khiến việc tìm lỗi khó hơn nhiều.

### 4.2 Song song đó — tăng độ chặt kiểu

Chọn một trong hai:

- **Sinh kiểu từ OpenAPI:** dùng `/openapi.json` của FastAPI, sinh client có kiểu. Loại bỏ hoàn toàn việc khai kiểu bằng tay và **luôn khớp backend** — rất hợp với dự án backend tiến hoá nhanh.
- **zod ở biên:** schema ở `lib/schemas/`, validate trong `fetchApi`. Linh hoạt hơn, nhưng vẫn phải cập nhật tay khi backend đổi.

Khuyến nghị: **sinh từ OpenAPI**, vì backend đã là nguồn sự thật cho mọi domain model và dự án đã có `docs/AGENT-BRIDGE.md` thể hiện văn hoá "hợp đồng tường minh".

### 4.3 Kết thúc câu hỏi "hai frontend"

Ở giai đoạn này, hãy chốt theo quyết định ở `01`-2:

- Nếu chọn **Next**: chuyển `frontend/index.html` + `app.js` + `editor.js` + `flow.js` + `style.css` vào `frontend/legacy/` (chỉ đọc, ghi rõ trong README), trỏ `GET /` của FastAPI sang bản Next, và **đảm bảo smoke test 64 checks vẫn xanh** (nó phụ thuộc endpoint `/`, nên đây là thay đổi có rủi ro — cần chạy `scripts/smoke.py` trước và sau).
- Nếu chọn **vanilla**: xoá `frontend/src/` và ghi vào `KE-HOACH-TONG-THE.md`, đồng thời chuyển các đề xuất ở `04` sang dạng kế hoạch JavaScript thuần (kém khả thi hơn — đó là lý do tài liệu này nghiêng về Next).

---

## 5. Giai đoạn 3 — Đo lường & khả năng quan sát

1. **Error boundary có báo cáo.** Bắt đầu bằng `error.tsx` + `global-error.tsx` ghi lỗi vào một nơi đọc được. Chỉ thêm Sentry/dịch vụ ngoài khi thật sự cần — với công cụ local-first, một tệp log cục bộ có thể đã đủ.
2. **Web Vitals.** Next có sẵn hook; ghi lại TTFB/LCP/INP để có mốc so sánh trước khi tối ưu. Đừng tối ưu khi chưa đo.
3. **Ngân sách hiệu năng thành bài test.** Sau F13 (ảo hoá), đo thời gian render một frame khi cuộn timeline với 500 clip và biến nó thành ngưỡng trong CI.
4. **Đo độ trung thực preview/final** (F2) — chỉ số `fidelity drift` như đề xuất ở `04`.

---

## 6. Bảng tổng hợp lộ trình

| Giai đoạn | Nội dung | Điều kiện hoàn thành |
| :--- | :--- | :--- |
| **0** | Test harness (Vitest + RTL + MSW + Playwright); bài test Gate 1→Gate 2 chạy đỏ; 6 luật test kiến trúc | Bài test Gate 1 tồn tại và **thất bại vì lý do đúng** |
| **1** | ESLint + jsx-a11y + `no-explicit-any` + `no-floating-promises`; job `frontend` trong CI; dọn dep/dead code; `npm audit`; đo bundle | CI xanh cho cả backend lẫn frontend |
| **2** | Next 14→15→16, React 18→19, React Compiler, kiểu sinh từ OpenAPI, chốt chuyện hai frontend | Smoke test 64 checks vẫn xanh sau khi đổi `GET /` |
| **3** | Error boundary, Web Vitals, ngân sách hiệu năng, chỉ số fidelity | Có số đo lịch sử để so sánh |

**Ước lượng thô:** giai đoạn 0 là khoản đầu tư lớn nhất và mang lại nhiều nhất; giai đoạn 1 ngắn nhưng phải xong trước giai đoạn 2; giai đoạn 2 nên làm từng bước nhỏ, mỗi bước một PR xanh.

---

## 7. Điều quan trọng nhất của tài liệu này

Nếu chỉ làm được **một** việc, hãy làm việc này:

> Viết bài test E2E đi hết quy trình 7 bước với hai cổng duyệt con người, và chỉnh nó cho tới khi nó **xanh**.

Bài test đó sẽ buộc phải sửa B2 (Gate 1 bất khả thi), B1 (`source_rights_confirmed` chỉ ở client), B3 (checklist QC báo sai), L2 (dự án giả), L3 (`catch` báo thành công), và L4 (lỗi không được bắt) — tức toàn bộ nhóm lỗi P0 trong tài liệu này. Nó cũng là lưới an toàn cho mọi refactor ở giai đoạn 2.

Một bài test xanh trên đúng hành trình nghiệp vụ đáng giá hơn hàng trăm test đơn vị trên những hàm không ai gọi.
