# Complex Skills Analysis Strategy

Updated: `2026-03-23`

**Implementation status:** 🟡 Designed

## Purpose

本文件把 `skill-0` 主專案、`skill-0-GUI` 視覺化專案，以及 Claude Code Skills 官方文件放在同一個分析框架下，回答一個更實際的問題：

當技能開始出現主技能、子技能、`references/`、`scripts/`、`templates/`、`commands` 合流、`context: fork`、`agent`、參數注入與跨檔案依賴時，在有限計算與上下文資源下，如何做出最有效益的分析，以及真正對使用者有價值的提醒。

這份文件的結論不是「把一切完整解析成最細的 graph」，而是建立一個高訊號、可追溯、可漸進加深的分析策略。

## Scope

本次評估同時涵蓋：

- `skill-0` 主專案：canonical parser / schema / search / governance
- `skill-0-GUI`：parser bridge、fallback parser、視覺化與輸入工作台
- Claude Code Skills 官方文件：`https://code.claude.com/docs/en/skills`

官方文件已於 `2026-03-23` 實際查閱。依當日文件內容，Claude Skills 已明確支援：

- nested `.claude/skills/` 自動發現
- supporting files 與 progressive loading
- `allowed-tools`
- `disable-model-invocation`
- `argument-hint`
- `context: fork`
- `agent`
- `$ARGUMENTS`
- `.claude/commands/` 與 skills 合流

## What Claude Skills Actually Looks Like Now

依官方文件目前定義，複雜 skill 不再只是單一 `SKILL.md` 指令檔，而是可能包含：

1. 一個進入點 `SKILL.md`
2. frontmatter 中的執行控制資訊
3. `references/`、`scripts/`、`templates/`、`assets/` 等 supporting files
4. 可能分布在 monorepo 巢狀目錄中的技能
5. 可能以 `context: fork` + `agent` 進一步把任務交給子代理
6. 可能由 `/skill-name` 或舊式 `.claude/commands/` 觸發

這代表對複雜 skill 的分析若仍只把單一 markdown 段落拆成 actions / rules / directives，會有三個明顯盲區：

- 忽略跨檔案依賴
- 忽略執行權限與觸發條件
- 忽略實際工作流常由「主 skill + supporting resources + subagent」共同構成

## Current State: skill-0

`skill-0` 已具備分析複雜 skill 的幾個重要基礎，但還沒有真正把複雜 skill 當成「技能圖」來處理。

### Already strong

- schema `2.4.0` 已有 provenance、location、extraction、`related_elements`、`parser_meta`、`decomposition_depth`、`requires_deep_parse` 等欄位，可支撐漸進式深解析。[skill-decomposition.schema.json](<repo-root>/schema/skill-decomposition.schema.json#L11) [skill-decomposition.schema.json](<repo-root>/schema/skill-decomposition.schema.json#L422) [skill-decomposition.schema.json](<repo-root>/schema/skill-decomposition.schema.json#L681)
- `CLAUDE.md` 已經有「large skills 要分批、先抓核心 action/rule、directive 後展開」的設計哲學，這和有限資源分析很一致。[CLAUDE.md](<repo-root>/CLAUDE.md#L121)
- repo 內已有對 supporting files / `references/` / 漸進載入的研究素材，例如 [agent-skills/SKILL.md](<repo-root>/converted-skills/agent-skills/SKILL.md#L90)。
- `parsed/anthropic-pdf-skill.json` 這類案例已經示範 `decomposition_hint`、`related_elements`、`execution_paths`、`parser_meta` 的方向，表示主專案不是完全沒有深解析思路。

### Current limits

- `scripts/auto_parse.py` 現行主邏輯仍以單檔 `SKILL.md` 啟發式拆解為主，frontmatter 僅做簡單 key/value 解析，對 YAML 複合結構沒有正式建模。[auto_parse.py](<repo-root>/scripts/auto_parse.py#L27)
- command extraction 只是在 fenced code block 中抓少數 shell 前綴，最多保留五筆，再轉成 generic actions，沒有形成結構化 command references。[auto_parse.py](<repo-root>/scripts/auto_parse.py#L156) [auto_parse.py](<repo-root>/scripts/auto_parse.py#L189)
- schema 雖然支援 provenance，但目前沒有看到 parsed output 實際普遍填入具體 locator，如 `SKILL.md#L...`。
- `reference.md` 等較舊文件仍停在 `2.0.0` 表述，和 live schema `2.4.0` 有文件漂移。[reference.md](<repo-root>/reference.md#L1) [skill-decomposition.schema.json](<repo-root>/schema/skill-decomposition.schema.json#L6)

## Current State: skill-0-GUI

`skill-0-GUI` 的定位很清楚：它補的是展示與工作台，不是 canonical parsing 本體。

### What it does well

- 透過 bridge 共用 `skill-0` 的 canonical parser，開發與 production runtime 都重用同一橋接層。[skill0Bridge.mjs](../../../skill-0-GUI/bridge/skill0Bridge.mjs#L50) [server.mjs](../../../skill-0-GUI/server.mjs#L8) [vite.config.ts](../../../skill-0-GUI/vite.config.ts#L8)
- 在找不到主 repo 時，可退回 standalone fallback parser，維持 demoability 與 deployability。[02-runtime-and-system-architecture.md](../../../skill-0-GUI/docs/02-runtime-and-system-architecture.md#L61)
- 文件設計上已把 GUI 定位為 intake + parsing + decomposition review + risk framing + security presentation 的工作台。[03-functional-modules.md](../../../skill-0-GUI/docs/03-functional-modules.md#L143)

### Current limits

- bridge/fallback parser 仍沿用與主專案相近的扁平啟發式拆法，尚未真正建立 multi-file skill graph。[skill0Bridge.mjs](../../../skill-0-GUI/bridge/skill0Bridge.mjs#L110) [skill0Bridge.mjs](../../../skill-0-GUI/bridge/skill0Bridge.mjs#L175)
- GUI 回傳的是 visualization-oriented envelope，裡面有 `phases`、`riskAssessment`、`threeClassification`，但這些目前仍偏 synthetic interpretation，不是完整的技能依賴圖。[02-runtime-and-system-architecture.md](../../../skill-0-GUI/docs/02-runtime-and-system-architecture.md#L103)
- working tree 目前主要是 `dist/` 與 bridge/runtime 文檔，可維運但不利於針對深層 graph UI 做實作與驗證。[02-runtime-and-system-architecture.md](../../../skill-0-GUI/docs/02-runtime-and-system-architecture.md#L145)

## Core Judgment

面對複雜型 skills，最有效益的方向不是：

- 一開始就完整展平所有主/副 skill 與所有 supporting files
- 嘗試把每一段文字都變成 action / rule / directive
- 把 GUI 直接做成全功能 graph IDE

最有效益的方向是：

1. 先建立「技能結構摘要層」
2. 只對高風險、高影響、高不確定性的部分做深解析
3. 把提醒做成可執行、可驗證、可追溯的說明，而不是泛泛警語

## Recommended Strategy Under Limited Resources

### Phase 1: Discovery pass

先做非常便宜的結構盤點，不做深解析。

最低限度應抽出：

- entry skill 名稱、描述、路徑
- frontmatter 關鍵欄位
- referenced local files
- command-like blocks
- 是否使用 `context: fork`
- 是否指定 `agent`
- 是否存在 supporting folders
- 是否來自 nested skill path

這一層的目標不是理解全部內容，而是建立一份 `skill manifest`。

### Phase 2: Dependency summary

把 skill 視為一個小型 dependency graph，而不是單檔文本。

最值得建模的節點類型只有五種：

1. `entry_skill`
2. `supporting_reference`
3. `executable_script`
4. `template_or_asset`
5. `subagent_or_forked_task`

最值得建模的邊也只有幾種：

- `references`
- `executes`
- `delegates_to`
- `depends_on`
- `suggests_output_from`

做到這裡，就已經比單純的 markdown heuristics 更接近真實工作方式，而且成本仍然可控。

### Phase 3: Selective deep parse

只在以下情況啟動深解析：

- skill 有 `context: fork` / `agent`
- skill 引用了多個 supporting files
- skill 命令數量超過閾值
- 出現高風險 shell / network / file mutation 行為
- description 與 body 明顯不一致
- 使用者明確要求深度審查

深解析的目標也不應是全文展平，而是補齊：

- provenance
- location
- command intent
- important related elements
- execution path variants

## What to Explain to Users

真正有價值的說明，不是「這個 skill 很複雜」，而是指出它複雜在哪裡、會造成什麼理解成本、哪些地方值得人工判讀。

建議輸出固定包含以下四類提醒。

### 1. Structural reminders

例如：

- 此 skill 不是單檔定義，另依賴 `references/` 與 `scripts/`
- 此分析目前只完整覆蓋 entry `SKILL.md`，supporting files 僅做摘要盤點
- 此 skill 來自 nested directory，可能只對特定子目錄或 package 生效

### 2. Execution reminders

例如：

- 此 skill 可自動觸發，非純手動流程
- 此 skill 會要求特定工具或降低互動確認門檻
- 此 skill 可能把任務交給 forked subagent，因此執行上下文與主對話不同

### 3. Risk reminders

例如：

- command block 含有 state-changing 或 external-call 行為
- 指令與 supporting scripts 之間存在隱性執行鏈
- fallback parser 與 canonical parser 只保證高層 contract 相容，不保證深層語意等價

### 4. Confidence reminders

例如：

- 這次結果屬於 discovery-level，未展開 supporting resources
- 這次結果已包含 deep parse，並附帶具體 locator
- 這次結果為 fallback mode，不宜視為正式治理判定

## Best ROI Improvements

如果只做少量工程投資，優先順序應該是：

### P0

- 在 parser 前面新增 manifest extraction，而不是直接重寫整個 parser
- 補齊 frontmatter 的結構化欄位擷取：至少 `allowed-tools`、`disable-model-invocation`、`argument-hint`、`context`、`agent`
- 解析 markdown 內相對路徑連結，建立 `references` / `scripts` / `templates` 摘要
- 對 command block 做風險分級，而不是只抽成 generic action

### P1

- 讓 parsed output 真正填入 provenance / locator
- 把 supporting files 納入 GUI 的 summary panel，而不是只顯示 actions / rules / directives
- 對 `context: fork` / `agent` 產出「delegation node」而非一般 directive

### P2

- 視需要才做完整 skill graph 視覺化
- 視需要才做跨 skill inclusion / nested path inheritance 的完整推論
- 視需要才做 command reference 的參數級語意分析

## Practical Impact on Each Project

### For skill-0

主專案最適合承擔：

- manifest extraction
- schema / provenance 擴充
- selective deep parse
- governance-grade warning generation

不適合先做的是重度 UI 或 3D graph 呈現。

### For skill-0-GUI

GUI 最適合承擔：

- intake of multi-file skill bundles
- manifest summary presentation
- mode / confidence / degradation 視覺提示
- dependency graph 的輕量視圖

不適合先做的是把 fallback parser 演進成第二套 canonical parser。

## Concrete Warnings Worth Showing by Default

如果只允許顯示少量提醒，預設值最值得保留的是：

1. `This skill depends on supporting files beyond SKILL.md`
2. `This skill may delegate work to a forked subagent`
3. `This skill contains executable command references`
4. `This result is manifest-only and not a full deep parse`
5. `This result came from standalone fallback mode rather than canonical parser mode`

這五種提醒都直接對理解邊界、執行風險與信心等級有幫助，訊號密度最高。

## Final Recommendation

在目前條件下，最合理的產品策略是：

- 由 `skill-0` 擔任 canonical analysis engine
- 由 `skill-0-GUI` 擔任 intake + visualization workbench
- 先把複雜 skill 當成「可分層盤點的 dependency package」
- 先做高價值提醒與 selective deep parse
- 暫時不要把資源砸在完整展平所有 nested skill 關係

一句話總結：

複雜型 skills 的最佳分析方式，不是先追求全面，而是先追求可追溯的結構摘要、可操作的風險提醒、與按需展開的深解析。
