# Skill-0 SkillOS 技能策展開發計畫

- 日期：`2026-07-15`
- 狀態：`現行開發計畫 / P2 Offline Curator 完成 / P3 尚未開始`
- 文件權威：`無語系後綴的英文版為權威文件；本文件為繁體中文閱讀版。`
- 工作區：`<repo-root>`
- 分支：`codex/skillos-curation-mvp`

## 1. 決策摘要

Skill-0 將加入受論文 *SkillOS: Learning Skill Curation for Self-Evolving
Agents* 啟發的「經驗驅動技能策展」方向。專案仍維持 Skill-0 的核心定位：
ARD 分解、Schema、檢索與 revision governance。新增能力會把執行經驗轉換成
可審核的 Skill 變更提案，並量測這些修訂是否改善後續相關任務。

第一版不實作 Agent OS、Sandbox Runtime、Saga Engine，也不直接重現論文的
RL 訓練。先建立離線、人工審核的策展 MVP，取得資料契約與評估證據後，再
決定是否訓練 Curator。

## 2. 命名與工作區決策

| 範圍 | 決策 | 理由 |
|---|---|---|
| 產品與正式 repository | 維持 `Skill-0` | 保留既有識別、歷史、Schema 與整合。 |
| 開發方向 | `SkillOS Curation` | 指出研究方向，但不把整個產品重新定義成 SkillOS。 |
| 本機 worktree | `skill-0-skillos` | 清楚區隔實驗方向與正式 checkout。 |
| 分支 | `codex/skillos-curation-mvp` | 隔離 ARDE runtime 實驗及原工作區的既存修改。 |
| 未來程式 namespace | 優先使用 `curation/`、`evaluation/` | 描述產品責任，不宣稱完整重現論文。 |

目前不改正式 repository 名稱。若未來技能策展成為獨立部署產品，再評估使用
較中性的 `skill-0-curation`。

## 3. 正確論文脈絡

主要來源：

- Ouyang 等人，*SkillOS: Learning Skill Curation for Self-Evolving Agents*，
  arXiv:2605.06614v1，2026-05-07：
  <https://arxiv.org/html/2605.06614v1>

論文提出的是以經驗驅動、透過 RL 學習 Skill Curator 的方法。核心閉環為：

```text
連續任務
  -> 凍結的 Agent Executor 檢索並使用 Skills
  -> 產生執行 trajectory 與正確性回饋
  -> Skill Curator 提出 insert、update、delete
  -> 更新外部 SkillRepo
  -> 由後續相關任務量測變更效益
```

論文把相關任務分組，讓早期策展決策接受後續任務的延遲回饋；再以 GRPO 及
複合 reward 訓練 Curator。Reward 包含後續任務成果、function call 有效性、
Skill 內容品質與 repository 精簡度。

論文邊界必須明確保留：

- SkillOS 是 Skill curation 學習方法，不是通用 Runtime 作業系統。
- Curator 訓練期間 Agent Executor 維持凍結。
- 論文的參考檢索路徑是 BM25。
- 研究中把每個 Skill 簡化為含 YAML frontmatter 的單一 Markdown 檔。
- Dense/hybrid retrieval、多檔 Skill、階層與組合式 Skill 被列為未來方向。

## 4. Skill-0 的適合作為底座程度

| 論文需求 | Skill-0 既有能力 | 適合度 | 需要補充 |
|---|---|---:|---|
| 結構化可重用 Skill | ARD 分解與 Schema v2.4.0 | 高 | 保留原始 artifact，新增策展 sidecar 契約。 |
| Skill 檢索 | 既有 dense semantic search | 高 | 增加 BM25 與 hybrid 對照基線。 |
| SkillRepo 更新 | Revision-aware governance | 高 | 先建立 proposal，再建立 revision。 |
| 策展操作驗證 | Schema normalization 與 validation | 高 | 驗證 insert/update/delete 及 base revision。 |
| 人工監督 | review、approve、reject、audit、dashboard | 高 | 增加 proposal 與 evaluation 檢視。 |
| 經驗匯入 | 尚無 trajectory 正式契約 | 缺少 | 新增具 provenance 與 redaction 的 trajectory。 |
| 後續任務回饋 | 尚無 grouped-task eval harness | 缺少 | 新增前後版本評估資料與指標。 |
| 可學習 Curator | 尚無 policy 或 training loop | 缺少 | 先做離線 LLM 提案，延後 RL。 |

Skill-0 可以合理補強論文的兩個簡化：比較 BM25、dense、hybrid retrieval；
保留原始多檔 Skill folder，將 ARD parsed data 視為 sidecar，而非強迫將 Skill
扁平化成替代用 Markdown。

## 5. 目標 MVP 閉環

```text
原始 Skill source 與 parsed ARD
  -> 匯入已去識別化的 execution trajectory
  -> 檢索相關的目前 Skill revisions
  -> 離線 Curator 產生 insert/update/delete proposal
  -> Schema、ARD、provenance、衝突驗證
  -> 人工治理 approve 或 reject
  -> 核准後建立不可變的新 Skill revision
  -> 以後續相關任務比較 baseline 與 candidate
  -> 將 evaluation evidence 寫入 proposal 與 revision provenance
```

硬性規則：

1. Curator 不得直接寫入正式 SkillRepo。
2. Update/delete proposal 必須指出 `skill_id` 與 base revision。
3. Approval 必須建立新 revision，不可原地修改已核准 artifact。
4. 預設不把 raw trajectory 複製到 Skill 或 log。
5. Evidence 是 curation、evaluation、revision provenance 的衍生 envelope，
   不是與 Action、Rule、Directive 並列的第四分類。
6. Proposal 未通過 validation 與人工決策前不得 promotion。
7. 後續 evaluation tasks 必須是 temporal holdout，不得提供給產生該 proposal 的 Curator。
8. Approval 時必須重新確認 proposal 的 base revision 仍為 current；stale proposal
   必須 supersede 或經明確 rebase。

## 6. 第一批資料契約

### 6.1 Trajectory

應包含：

- 穩定的 trajectory、task、executor、run ID；
- task family 或 grouping attributes；
- 有序的 observation、tool/action 摘要及 terminal outcome；
- 被檢索的 Skill ID 與 revision ID；
- 正確性或 reviewer feedback 及其來源；
- timestamp、source、redaction state、content checksum；
- retention class，以及需要完整重播時所使用的隔離 raw content reference；
- 明確排除 secrets、credentials、cookies 與不受控 chain of thought。

### 6.2 Curation Proposal

應包含：

- operation：`insert`、`update`、`delete`；
- 適用時的 target skill 與 base revision；
- proposed source artifact 或 patch，不允許隱含式原地修改；
- supporting trajectory 與 retrieved skill references；
- curator、model/config identity、rationale summary、confidence；
- Schema、ARD、duplicate、conflict、provenance validation；
- draft、pending review、approved、rejected、superseded 狀態；
- approval actor、decision reason、resulting revision ID。

### 6.3 Evaluation Result

應包含：

- task group 與 evaluation protocol identity；
- baseline 與 candidate repository snapshot；
- executor 與 retrieval configuration；
- 後續任務 success、steps、tokens、latency、error 摘要；
- proposal acceptance 與 invalid operation 結果；
- duplicate/conflict 與 repository token growth；
- proposal、revision、trajectory、fixture 的確定性連結。

## 7. 分階段開發計畫

### P0：規劃與基準鎖定

交付：本計畫及英文權威版、乾淨 worktree、論文來源與範圍校正、命名決策、
ARDE disposition、Schema 與 revision governance 的小範圍基準測試。

閘門：文件檢查與基準測試通過，尚不增加 runtime code。

### P1：Contract-only foundation

交付：trajectory、curation proposal、evaluation result JSON Schema；正反例
fixtures；依循既有模式的 Python validation/normalization helper；provenance 與
redaction 規則；temporal holdout 與 stale-base-revision 負面 fixtures。

閘門：既有 parsed skills 不變，全部新增契約測試通過。

實作紀錄（`2026-07-15`）：

- 已於 commit `015b0e6` 完成：`schema/` 下三份 Draft-07 契約、
  `tests/fixtures/curation_contracts/` 下的正反例 fixtures，以及
  `tools/curation_contract.py` 的語意驗證 helper。
- Helper 會檢查 redaction、trajectory step 與 retrieval rank 順序、operation/base
  revision 一致性、temporal holdout 隔離、approved validation state，以及
  evaluation snapshot/delta 一致性。
- P1 驗證通過：契約 focused tests、完整 core regression（`184 passed`），以及
  Flake8 `7.3.0` 的 P1 fatal-error 選項（`E9,F63,F7,F82`，結果 `0`）。
- 未修改 `parsed/`、governance database、API、runtime execution path 或 Curator
  generation path。P2 仍是獨立 review gate。

### P2：離線、人工審核 Curator

交付：接收 trajectory 與 retrieved skills 的 CLI 或 service function；結構化
insert/update/delete proposal；可重現的 prompt/config manifest；僅允許 dry
proposal，不提供正式 repository write path。

閘門：無效操作 fail closed，proposal generation 無法繞過 governance。

實作紀錄（`2026-07-16`）：

- 已在 `curation/offline_curator.py` 與 `tools/offline_curator.py` 建立兩階段
  `prepare`/`propose` 邊界；不會呼叫網路或 model provider。
- 已新增固定 prompt/config resource，以及 Draft-07 skill-context、decision 契約。
  Prompt package 與 decision 以 checksum 綁定並保持 deterministic。
- Insert、update、delete 只會產生 `draft` proposal。Candidate 敏感內容、stale
  target revision、package tampering，以及 ignored `output/curation/` 以外的
  repository-local output path 都會 fail closed。
- 已新增英文與繁中 operator 文件。P2 不保存 proposal、不呼叫 governance、
  不建立 revision，也不寫入 SkillRepo。
- 驗證通過：`50` 個 focused tests、Flake8 fatal checks（`0`）、Python compile，
  以及 core 加 dashboard API 完整 regression（`279 passed`）。

### P3：Revision governance integration

交付：proposal persistence 與 audit event；approve/reject/supersede；核准的
insert/update 建立新 revision；delete 使用可復原、保留歷史的治理狀態轉換；
promotion 使用 optimistic concurrency，base revision 已變更時必須拒絕。

閘門：所有 promotion artifact 都綁定 revision 並可追溯 proposal；stale proposal
不能覆蓋較新的 revision。

### P4：Retrieval baseline

交付：論文參考用 BM25、既有 dense retrieval、hybrid rank fusion；固定 corpus、
query set、top-k budget 與可重現指標。

閘門：不同 retrieval 使用相同輸入，並同時報告 relevance 與 downstream result。

### P5：Grouped-task evaluation harness

交付：task-group schema 與 fixture runner；baseline/candidate snapshots；future-task
success 與效率；proposal quality、invalid operation、duplicate、conflict、
compactness 指標；並保留 temporal split 證據，證明 proposal 未看到後續任務。

閘門：至少一個受控 benchmark 能顯示核准策展是否改善後續任務。

### P6：Curator learning 研究閘門

只有 P5 證明有可量測價值後，才決定是否重現 GRPO 或其他 learned Curator。
本階段需另做 compute、data、model license、reproducibility、cost 審查。論文的
訓練規模明顯大於本 MVP，因此 RL 不屬於前述階段的隱含交付。

## 8. 成功指標

- 與未變更 baseline 相比的 future-task success 或 exact-match 差異；
- 每個成功任務所需 steps 或 tokens；
- 人工 proposal acceptance rate；
- invalid curation operation rate；
- duplicate 或 contradictory skill rate；
- SkillRepo token 與 revision growth；
- 固定 top-k 下的 retrieval relevance。

MVP 成功代表後續任務改善，且 invalid operation、conflict、repository growth
仍在可接受範圍。Proposal 數量本身不是成功指標。

## 9. ARDE v4 處置

| ARDE v4 方向 | 處置 | 主線規則 |
|---|---|---|
| ARD parser、canonical schema、semantic search | 保留 | Skill-0 核心底座。 |
| Revision governance、人工 review | 保留 | Curator proposal promotion gate。 |
| Evidence projection、append-only audit 概念 | 改造後保留 | 用於 proposal、evaluation、revision provenance。 |
| Runtime Contract、`/api/runs` | Experimental | 獨立 safety extension，非 SkillOS 必要項。 |
| Dry-run executor、runtime ledger | Experimental | 不得阻擋 curation MVP。 |
| Saga compensation、crash recovery | Experimental | 僅與 side-effect execution 有關。 |
| MCP、Agents SDK、LangGraph、OPA、sandbox | 延後 | 策展閉環取得證據後再評估。 |
| Evidence 作為第四個 ARD peer | 不採用 | Evidence 維持衍生 metadata/provenance。 |
| Skill-0 作為完整 Agent OS | 不採用 | 維持 skill intelligence 與 governance layer。 |

本策展 MVP 不會將任何 ARDE runtime commit 合併到此分支。

## 10. 風險與復原

| 風險 | 控制 | Rollback 或停用方式 |
|---|---|---|
| Curator 產生有害或低品質 Skill | Proposal-only 與人工核准 | Reject/supersede，current revision 不變。 |
| 敏感 trajectory 進入儲存 | Redaction 契約與 allowed fields | 隔離 trajectory，失效其相依 proposals。 |
| Repository 成長但沒有價值 | Compactness 與 duplicate metrics | Reject，或將 current pointer 回復前版。 |
| Retrieval 對照有偏差 | 固定 corpus、top-k、executor | 由 immutable snapshots 重跑。 |
| 對外宣稱超出證據 | 區分研究重現與產品 MVP | Benchmark 前標示為 engineering experiment。 |
| Experimental runtime 汙染主線 | 分支與 module boundary | 不合併 runtime commits，保持 disabled。 |

## 11. 開發工作流契約

`dev-workflow-scale-planner` 將整體工作判定為 `大`；本次文件工作使用
快速、非互動規劃模式。

後續以可審查 commit 依序執行：

1. 計畫與權威索引；
2. 契約與 fixtures；
3. Offline Curator proposal path；
4. Governance integration；
5. Retrieval baselines；
6. Grouped-task evaluation。

每個實作 commit 都要有 targeted tests 與 read-only review。Public push、release、
dependency mutation、database migration、把私人資料傳給外部模型，以及 runtime
exposure 都保留為明確 approval checkpoint。

## 12. 下一個立即開發切片

P2 已完成。在 P2 proposal-only boundary 完成審查前停止，不進入 P3。下一個需
另行核准的切片僅限 P3：

1. 定義 proposal persistence 與 append-only audit record；
2. 新增 approve、reject、supersede transition；
3. 保留 proposal/revision provenance，不原地修改 approved artifact；
4. Promotion 時重新執行 optimistic concurrency 檢查；
5. 只有必要 validations 與人工 approval 全部通過後才建立 revision；
6. 進入 P4 retrieval baseline 前再次停止。
