# Agent 編組費用評估報告（修正版 v2）

**產出日期**: 2026-02-11  
**適用範圍**: `FINAL_PHASE_PLAN.md` 的 6-Agent 執行規劃  
**本版目的**: 依你的要求，盡可能納入「所有服務商的最新/頂級模型」做比較，且優先以 OpenCode 已收錄模型為範圍。

---

## 0) 先回答：為何先前看不到 Claude Opus 4.5 / 4.6

- 先前版本主表只列了「當下四策略實際採用模型」，不是完整旗艦模型清單。
- 因此 `claude-opus-4-5` / `claude-opus-4-6` 沒被放進主比較表（不是不可用，也不是官方未收錄）。
- 本版已把 `claude-opus-4-5` 與 `claude-opus-4-6` 正式納入比較與策略。

---

## 1) 範圍與資料原則

### A. 優先範圍：OpenCode 已收錄模型
- 以本地 models.dev 快照中的 `opencode` provider 為基準（31 models）。
- 供應商推定分群（依 model ID 前綴）後，覆蓋到：
  - OpenAI
  - Anthropic
  - Google
  - xAI
  - Moonshot/Kimi
  - Zhipu/GLM
  - MiniMax
  - Alibaba/Qwen
  - Other/Unmapped

### B. 定價原則
- **優先使用供應商官方定價頁**（OpenAI / Anthropic / Google / xAI / DeepSeek 等）。
- 若某服務商第一方定價頁無法穩定抓取，先以「可驗證官方平台定價（如 Fireworks 代管）」標註並區分。
- `models.dev` 僅作補充與交叉檢查，不作唯一權威來源。

---

## 2) OpenCode 已收錄服務商（31 models）

| 服務商（由 model ID 推定） | 收錄數 | 代表最新/頂級模型（OpenCode 清單內） |
|---|---:|---|
| OpenAI | 9 | `gpt-5.2-codex`, `gpt-5.1-codex`, `gpt-5.2` |
| Anthropic | 7 | `claude-opus-4-6`, `claude-opus-4-5`, `claude-sonnet-4-5` |
| Moonshot/Kimi | 4 | `kimi-k2.5`, `kimi-k2-thinking` |
| Zhipu/GLM | 3 | `glm-4.7`, `glm-4.6` |
| Google | 2 | `gemini-3-pro`, `gemini-3-flash` |
| MiniMax | 2 | `minimax-m2.1` |
| Alibaba/Qwen | 1 | `qwen3-coder` |
| xAI | 1 | `grok-code` |
| Other/Unmapped | 2 | `trinity-large-preview-free`, `big-pickle` |

> 註: 上表是 OpenCode 收錄現況，不等於各供應商完整全量模型目錄。

---

## 3) 各服務商「最新/頂級」模型比較（盡可能官方化）

| 服務商 | 模型（顯示名） | 官方/常用 model ID | Input $/1M | Output $/1M | Context / 上限 | 價格來源等級 |
|---|---|---|---:|---:|---|---|
| OpenAI | GPT-5.2 Codex | `gpt-5.2-codex` | 1.75 | 14.00 | (定價頁未列 context) | 官方（OpenAI） |
| OpenAI | GPT-5.1 Codex | `gpt-5.1-codex` | 1.25 | 10.00 | 400K ctx / 128K out | 官方（OpenAI） |
| Anthropic | Claude Opus 4.6 | `claude-opus-4-6` | 5.00 | 25.00 | 200K（1M beta）/ 128K out | 官方（Anthropic） |
| Anthropic | Claude Opus 4.5 | `claude-opus-4-5` | 5.00 | 25.00 | 200K | 官方（Anthropic） |
| Anthropic | Claude Sonnet 4.5 | `claude-sonnet-4-5` | 3.00 | 15.00 | 200K（1M beta）/ 64K out | 官方（Anthropic） |
| Google | Gemini 2.5 Pro | `gemini-2.5-pro` | 1.25* | 10.00* | 1,048,576 in / 65,536 out | 官方（Google） |
| Google | Gemini 2.5 Flash | `gemini-2.5-flash` | 0.30 | 2.50 | 1,048,576 in / 65,536 out | 官方（Google） |
| xAI | Grok Code Fast 1 | `grok-code-fast-1` | 0.20 | 1.50 | 256K | 官方（xAI） |
| DeepSeek | DeepSeek Reasoner | `deepseek-reasoner` | 0.28 | 0.42 | 128K | 官方（DeepSeek） |
| Mistral | Devstral 2 | `devstral-2512` | 0.40 | 2.00 | (依模型頁) | 官方（Mistral） |
| Fireworks* | Qwen3 235B-A22B | `qwen3-235b-a22b` | 0.22 | 0.88 | (平台模型頁) | 官方（Fireworks 平台） |
| Fireworks* | Kimi K2.5 | `kimi-k2p5` | 0.60 | 3.00 | (平台模型頁) | 官方（Fireworks 平台） |
| Fireworks* | GLM-4.7 | `glm-4p7` | 0.60 | 2.20 | (平台模型頁) | 官方（Fireworks 平台） |
| Fireworks* | MiniMax M2.1 | `minimax-m2p1` | 0.30 | 1.20 | (平台模型頁) | 官方（Fireworks 平台） |

\* `gemini-2.5-pro` 有 `<=200K` / `>200K` 分段價，見第 4 節。  
\* Fireworks 為代管平台價格，不等於 Qwen/Kimi/GLM/MiniMax 第一方 API 原廠價格。

---

## 4) 必須反映的費率規則（避免低估）

### A. OpenAI reasoning token 計費
- 官方規則：reasoning tokens 以 output token 費率計價。
- 本報告在成本估算時，對 OpenAI reasoning 模型以 output 單價計 reasoning 成本。

### B. Gemini 2.5 Pro 分段計價（關鍵）
- `<=200K prompt`: Input $1.25 / Output $10
- `>200K prompt`: Input $2.50 / Output $15
- 超過門檻時需切換高價段，否則會低估。

### C. Anthropic long-context（關鍵）
- Opus 4.6 / Sonnet 4.5 / Sonnet 4 在 1M context beta 下，input >200K 會進 long-context 計價。
- 本報告主表預設 <=200K 場景；若超過需改高價段。

---

## 5) Agent 工作量假設（沿用）

| Agent | 任務 | Input | Output | Reasoning |
|---|---|---:|---:|---:|
| A | 安全加固 | 80,000 | 40,000 | 30,000 |
| B | GPU fallback | 15,000 | 5,000 | 3,000 |
| C | DevOps 基建 | 60,000 | 35,000 | 20,000 |
| D | 後端測試 | 100,000 | 60,000 | 35,000 |
| E | 前端測試 | 80,000 | 45,000 | 25,000 |
| F | 文件與監控 | 50,000 | 40,000 | 15,000 |
|  | **合計** | **385,000** | **225,000** | **128,000** |

---

## 6) 四策略（v2，含 Opus 4.6）

計算式（每 Agent）：
- `InputCost = input_tokens * input_price / 1,000,000`
- `OutputCost = output_tokens * output_price / 1,000,000`
- `ReasonCost = reasoning_tokens * output_price / 1,000,000`（估算）
- `Subtotal = InputCost + OutputCost + ReasonCost`

### 策略 1: 性能取向（Max Performance，更新為 Opus 4.6）

| Agent | 模型 ID | 服務商 | 小計 (USD) |
|---|---|---|---:|
| A | `claude-opus-4-6` | Anthropic | 2.1500 |
| B | `claude-sonnet-4-5` | Anthropic | 0.1650 |
| C | `gpt-5.2-codex` | OpenAI | 0.8750 |
| D | `claude-opus-4-6` | Anthropic | 2.8750 |
| E | `claude-sonnet-4-5` | Anthropic | 1.2900 |
| F | `o3` | OpenAI | 0.5400 |
|  | **TOTAL** |  | **7.8950** |

### 策略 2: 高性能 + 費用分攤（推薦）

| Agent | 模型 ID | 服務商 | 小計 (USD) |
|---|---|---|---:|
| A | `claude-sonnet-4-5` | Anthropic | 1.2900 |
| B | `o4-mini` | OpenAI | 0.0517 |
| C | `gpt-5.1-codex` | OpenAI | 0.6250 |
| D | `claude-sonnet-4-0` | Anthropic | 1.7250 |
| E | `gemini-2.5-pro` | Google | 0.8000 |
| F | `claude-haiku-4-5` | Anthropic | 0.3250 |
|  | **TOTAL** |  | **4.8167** |

### 策略 3: 均衡（Balanced）

| Agent | 模型 ID | 服務商 | 小計 (USD) |
|---|---|---|---:|
| A | `claude-sonnet-4-0` | Anthropic | 1.2900 |
| B | `gemini-2.5-flash` | Google | 0.0245 |
| C | `gemini-2.5-flash` | Google | 0.1555 |
| D | `o4-mini` | OpenAI | 0.5280 |
| E | `claude-haiku-4-5` | Anthropic | 0.4300 |
| F | `gemini-2.5-flash` | Google | 0.1525 |
|  | **TOTAL** |  | **2.5805** |

### 策略 4: 低費用高報酬（Budget）

| Agent | 模型 ID | 服務商 | 小計 (USD) |
|---|---|---|---:|
| A | `deepseek-reasoner` | DeepSeek | 0.0518 |
| B | `devstral-small-2` | Mistral | 0.0000 |
| C | `deepseek-chat` | DeepSeek | 0.0399 |
| D | `qwen3-235b-a22b` | Fireworks | 0.1056 |
| E | `gemini-2.5-flash-lite` | Google | 0.0360 |
| F | `devstral-small-2` | Mistral | 0.0000 |
|  | **TOTAL** |  | **0.2333** |

---

## 7) 策略總表（單次）

| 策略 | 總費用 (USD) | 相對策略1 |
|---|---:|---:|
| 策略1 性能取向（Opus4.6） | 7.90 | baseline |
| 策略2 高性能+分攤 | 4.82 | -39% |
| 策略3 均衡 | 2.58 | -67% |
| 策略4 低費用 | 0.23 | -97% |

---

## 8) 本版已修正清單

- 已把 `Claude Opus 4.5/4.6` 納入主比較表與策略邏輯。
- 已把比較範圍擴到「OpenCode 已收錄的所有服務商分群」。
- 已補齊「最新/頂級模型」比較區，並標註來源等級（官方第一方 vs 官方代管平台）。
- 已保留與更新四策略數學一致性（小計與總計一致）。
- 已明確區分 `reasoning token` 規則適用範圍（OpenAI 官方明示）。

---

## 9) 尚需持續追蹤（透明揭露）

- Moonshot/Kimi、Zhipu/GLM、MiniMax、Alibaba/Qwen 的**第一方官方定價頁**有些需 JS/地區語系登入流程，機器抓取穩定度較低。
- 因此這些供應商在本版主比較中，部分價格暫以 Fireworks 官方代管定價補位，已明確標註。
- 若你要「全數第一方官方定價」版本，我下一版可只保留已抓到第一方者，其餘留白待人工核驗。

---

## 10) 來源清單（可追溯）

- OpenAI Pricing: `https://platform.openai.com/docs/pricing`  
- OpenAI Pricing (portal): `https://platform.openai.com/pricing`  
- OpenAI GPT-5.1 Codex model page: `https://developers.openai.com/api/docs/models/gpt-5.1-codex`  
- Anthropic Pricing: `https://docs.anthropic.com/en/about-claude/pricing`  
- Anthropic Models overview: `https://docs.anthropic.com/en/docs/about-claude/models`  
- Gemini API Pricing: `https://ai.google.dev/gemini-api/docs/pricing`  
- xAI Models & Pricing: `https://docs.x.ai/docs/models`  
- DeepSeek Pricing: `https://platform.deepseek.com/api-docs/pricing/`  
- Mistral Models docs: `https://docs.mistral.ai/getting-started/models/`  
- Mistral Pricing: `https://mistral.ai/pricing/`  
- Fireworks Pricing: `https://fireworks.ai/pricing`  
- Fireworks Models: `https://fireworks.ai/models`
