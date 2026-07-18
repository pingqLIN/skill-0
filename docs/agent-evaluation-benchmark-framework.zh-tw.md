# Agent Evaluation Benchmark Framework v1

- 狀態：**已接受的 framework；foundation suite 在 review 與 freeze 前維持 draft**
- 版本：`1.0.0`
- 生效日期：`2026-07-18`
- Runner：[`../tools/agent_evaluation_benchmark.py`](../tools/agent_evaluation_benchmark.py)
- Schemas：`agent-evaluation-{suite,candidate,report}.schema.json`
- Draft suite：[`../benchmarks/agent-evaluation-foundation-v1.json`](../benchmarks/agent-evaluation-foundation-v1.json)
- 英文權威文件：[`agent-evaluation-benchmark-framework.md`](agent-evaluation-benchmark-framework.md)

## 1. 目的

本 framework 以 reviewed、digest-frozen suite 評估已記錄的 agent behavior。它為 Runtime foundation claims 提供 deterministic evidence；不執行 agent、不呼叫 provider、不選 model，也不授權 Runtime run。

```text
external capture adapter（out of scope）
  -> structured candidate replay
reviewed + frozen benchmark suite
  -> deterministic scorer
  -> evidence-only report
```

## 2. Trust boundary

Scorer 只接受 structured outcome、Evidence codes、claim codes 與 optional latency measurement。Free-form model output 必須由另行治理的 capture/extraction process 轉換。Candidate artifact 是 input data；caller 驗證其 provenance 與 suite digest 前，不是 trusted evidence。

Scorer：

- 永遠使用 repository-owned schemas；
- 重算 suite digest 並拒絕 drift；
- 只評分 `reviewed-frozen` suite；
- 拒絕 missing、duplicate 或 unknown candidate cases；
- 用 canonical candidate digest 綁定 report，並以正確名稱 `candidate_produced_at` 保留 candidate timestamp；
- 把 candidate provenance 標記為 `unverified`，因為 capture attestation 不在 scorer boundary；
- 產生 schema-validated、`authority=evaluation-evidence-only` 的 report；
- 不執行 network、model、database、Governance、Runtime 或 Dashboard 工作。

## 3. Metrics 與 gate

| Metric | 意義 |
|---|---|
| `outcome_accuracy` | 所有 cases 的 exact expected outcome |
| `evidence_recall` | 所有 cases 已觀察到的 required Evidence codes |
| `forbidden_claim_rate` | 產生至少一個 forbidden claim code 的 case 比例 |
| `safety_outcome_accuracy` | `safety_critical=true` cases 的 exact outcome accuracy |
| `safety_case_pass_rate` | outcome 正確、required Evidence 完整且沒有 forbidden claim 的 safety cases |

四個 configurable thresholds 都由 suite 擁有並包含在 digest，且以 unrounded values 比較；rounding 只用於呈現。此外，`safety_case_integrity` 是不可設定放寬的 hard gate，要求每個 safety case 都具備正確 outcome、完整 required Evidence，且沒有 forbidden claim。Framework 同時回報 failed checks 與 mismatched case IDs，不會用 aggregate average 隱藏 safety regression。

## 4. Freeze 與 replay protocol

1. 獨立於 candidate output curate cases；不得從待測 implementation 產生 expected values。
2. Review case wording、expected outcomes、required Evidence、forbidden claims、taxonomy coverage 與 thresholds。
3. 設定 `freeze.state=reviewed-frozen`，記錄 `agent:*` reviewer 與 timestamp，再以除了 digest field 之外的完整文件重算 `suite_digest`。
4. 為每個 frozen case capture 一筆完整 candidate record，記錄 exact `benchmark_id` 與 `suite_digest`。
5. 執行 scorer，並一起保存 suite、externally verified candidate provenance、command、exit code 與 report。在另有 attestation contract 前，report 本身仍標記 `candidate_provenance=unverified`。
6. 任何 case、threshold、freeze 或 expected-value 改變都會產生新 digest，並使先前 candidate replay 失效。

Checked-in foundation suite 刻意維持 `draft`；它必須先完成獨立 case-content review 與 freeze 才能評分。

## 5. Interpretation

Passing report 只支持該 exact suite 與 candidate capture 所代表的 claims。它不證明 general intelligence、factual correctness、strict Skill equivalence、production safety 或 execution permission。Benchmark output 不能改變 Asset、Governance 或 Runtime authority。

比較結果必須使用相同 suite digest 與 compatible capture provenance。缺少 capture provenance、未揭露 retries、manual cherry-picking 或 unfrozen suite，都使結果成為 `UNKNOWN`，不是 passing evidence。

## 6. 明確排除項目

Framework v1 不會：

- 呼叫 external 或 local model provider；
- 把結果寫入 operator database；
- 新增 Asset type；
- 使用或整合 FTS5；
- 修改 Dashboard；
- 執行 physical database migration；
- 啟用 real adapter execution；
- 把 evaluation output 升格為 Governance authority。
