# Runtime Risk Hardening Spec

Updated: `2026-03-31`
Implementation status: `🟢 Implemented in core API baseline on 2026-04-02`
Scope: `api/main.py runtime baseline hardening`

Status note: The core API implementation for trusted proxy client IP extraction and structured search-backend `503` responses landed on `2026-04-02`. Treat the design sections below as the rationale and contract record for the implemented baseline.

## 1. Purpose

本文件把目前仍未落地的 runtime 風險補齊項目，收斂成可實作規格，聚焦兩條：

1. RISK-4: rate limiter 在反向代理後不讀 `X-Forwarded-For`
2. RISK-5: search endpoints 缺少統一 graceful error handling

## 2. Current Baseline

截至 `2026-03-31`：

1. API 已有 in-memory rate limiter 與 async lock。
2. rate limiter 目前主要依賴 `request.client.host`。
3. `/api/search`、`/api/similar`、`/api/cluster` 若 search engine / embedder / DB 出錯，可能直接回 500。
4. API 已有 request id、structured logging、metrics。

這表示 runtime hardening 並非從 0 開始，而是要把已存在基線補成「反向代理友善 + 錯誤語義可預期」。

## 3. Goals

1. 在可信 proxy 情境下，rate limiter 能辨識真實 client IP。
2. 在不可信 forwarded headers 情境下，仍保守回退到 `request.client.host`。
3. search endpoints 對 runtime failure 回傳統一 `503` 結構，不直接洩漏 traceback。
4. structured logs 與 metrics 能區分 rate limit / search unavailable / unexpected failure。

## 4. Non-Goals

1. 多節點共享 rate limit state。
2. 直接遷移到 Redis / `slowapi`。
3. 對所有非 search 路由重做例外包裝。
4. 完整 zero-trust proxy chain 驗證平台。

## 5. Forwarded Header Policy

### 5.1 Trusted proxy mode

新增設定：

- `SKILL0_TRUST_PROXY_HEADERS=false`
- `SKILL0_TRUSTED_PROXY_CIDRS=` 例如 `127.0.0.1/32,10.0.0.0/8`

只有在以下條件都成立時才讀 forwarded headers：

1. `SKILL0_TRUST_PROXY_HEADERS=true`
2. `request.client.host` 落在 `SKILL0_TRUSTED_PROXY_CIDRS`

### 5.2 Extraction order

建議 client IP 解析順序：

1. `CF-Connecting-IP`
2. `X-Forwarded-For` 的第一個 IP
3. `X-Real-IP`
4. fallback `request.client.host`

### 5.3 Validation rules

1. 只接受可解析的單一 IP。
2. `X-Forwarded-For` 若含多值，取第一個 non-empty value。
3. 若 header 值非法，記 warning log，回退到 socket peer。
4. 若 proxy 不在 trusted CIDR，即忽略所有 forwarded headers。

## 6. Rate Limiter Contract

新增內部 helper：

- `_extract_client_ip(request: Request) -> str`

rate limit bucket key 從：

- `scope:request.client.host`

改為：

- `scope:_extract_client_ip(request)`

需新增測試情境：

1. 未啟用 trust proxy 時忽略 forwarded headers
2. 啟用 trust proxy 且 proxy IP 可信時，使用 forwarded IP
3. forwarded header 非法時 fallback
4. 多個 forwarded IP 時取第一個
5. auth 與 api bucket 仍保持分離

## 7. Search Error Handling Contract

### 7.1 Covered endpoints

- `POST /api/search`
- `GET /api/search`
- `GET /api/similar/{name}`
- `GET /api/cluster`

### 7.2 Error response shape

當 search engine / embedder / DB 發生 runtime failure，回：

```json
{
  "detail": {
    "code": "SEARCH_BACKEND_UNAVAILABLE",
    "message": "Search service is temporarily unavailable.",
    "request_id": "abcd1234"
  }
}
```

HTTP status: `503`

正式 response schema：

- `detail.code: str`
- `detail.message: str`
- `detail.request_id: str`

固定值規則：

- `detail.code = SEARCH_BACKEND_UNAVAILABLE`
- `detail.message = Search service is temporarily unavailable.`
- `detail.request_id` 必須對應當前 request middleware 產生的 request id

### 7.3 Logging rule

server side log 應保留：

- endpoint
- request_id
- exception class
- safe error summary

但 response 不直接回 raw exception string，避免把環境與檔案細節外露。

## 8. Implementation Shape

### 8.1 Shared helper

建議新增 helper：

- `_search_service_unavailable(request_id: str) -> HTTPException`

### 8.2 Wrapping policy

對 search endpoints 中真正會碰 search backend 的區塊加 `try/except Exception`：

1. log exception with request_id
2. increment unavailable metric if needed
3. return `503` structured response

非 search endpoint 不在本次範圍內做全面統一包裝。

## 9. Metrics

建議新增 counter：

- `skill0_search_failures_total{endpoint,reason}`

最小 reason 集合：

- `backend_unavailable`
- `invalid_dependency`
- `unexpected_error`

## 10. Tests

最小測試矩陣：

1. trusted proxy disabled -> use socket IP
2. trusted proxy enabled + trusted peer + `X-Forwarded-For` -> use forwarded IP
3. untrusted peer + forwarded header -> ignore header
4. malformed header -> fallback and log
5. `/api/search` backend failure returns `503`
6. `/api/similar` backend failure returns `503`
7. `/api/cluster` backend failure returns `503`
8. `request_id` is present in `503` payload
9. `503` payload matches the documented schema for search/similar/cluster

## 11. Suggested Delivery Order

1. add client IP extraction helper + unit tests
2. switch rate limiter bucket key to helper
3. add structured `503` helper for search endpoints
4. cover search/similar/cluster with graceful error handling
5. add metrics/log assertions where practical
6. refresh docs and verification note

## 12. Outcome Note (`2026-04-02`)

Implemented in `api/main.py`:

1. `_extract_client_ip(request)` now supports trusted proxy mode with:
   - `SKILL0_TRUST_PROXY_HEADERS`
   - `SKILL0_TRUSTED_PROXY_CIDRS`
   - header precedence `CF-Connecting-IP` -> `X-Forwarded-For` -> `X-Real-IP`
2. baseline rate limiter bucket keys now use extracted client IP
3. `/api/search`, `/api/similar`, and `/api/cluster` runtime backend failures now return structured `503`
4. `detail.request_id` now matches the request middleware `X-Request-ID`
5. `skill0_search_failures_total{endpoint,reason}` metric now records backend-unavailable failures

Validated with:

```bash
.venv/bin/python -m pytest tests/test_api_security.py tests/integration/test_rate_limiting.py tests/integration/test_api_core.py -q
```
