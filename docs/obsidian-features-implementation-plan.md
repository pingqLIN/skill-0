# Obsidian 啟發功能實作計畫

**作者**: pingqLIN  
**日期**: 2026-02-08  
**版本**: 1.0.0  
**狀態**: 執行中

---

## 1. 動機與背景

### 1.1 緣起

根據《Obsidian 資料庫架構研究與 Skill-0 適用性評估》（`docs/obsidian-architecture-evaluation.md`）中的分析，Obsidian 的數項核心機制對 Skill-0 專案具有高度參考價值。本計畫針對評估報告中**推薦指數 4 星（⭐⭐⭐⭐）以上**的項目，規劃並執行實作。

### 1.2 目標項目

| 項目 | 推薦指數 | Obsidian 原型 | Skill-0 目標 |
|------|---------|---------------|-------------|
| **雙向連結** | ⭐⭐⭐⭐⭐ | Bidirectional Links / Backlinks | 技能間關係網路 |
| **Graph View** | ⭐⭐⭐⭐⭐ | Force-directed Graph Visualization | 技能關係圖譜 API |
| **Metadata Cache** | ⭐⭐⭐⭐ | MetadataCache / resolvedLinks | 技能連結快取機制 |
| **MOC 模式** | ⭐⭐⭐⭐ | Map of Content | 技能分類索引自動生成 |

### 1.3 動機分析

**核心問題**: Skill-0 目前擁有 53 個已解析技能，具備完善的技能內部分解（Action/Rule/Directive 三元分類），但技能之間是**完全孤立**的——缺乏任何跨技能關係建模機制。

**Obsidian 啟示**: Obsidian 的「連結優先於分類」設計哲學證明，知識單元之間的關係與知識單元本身同等重要。

**預期效益**:
- 技能間依賴關係的結構化記錄
- 基於連結的智慧推薦能力
- 技能生態的全景視覺化
- 技能發現與組合的效率提升

---

## 2. 新技術/架構/能力的資料蒐集與評估

### 2.1 技術方案評估

#### 雙向連結（Bidirectional Links）

| 評估面向 | 說明 |
|---------|------|
| **技術來源** | Obsidian MetadataCache.resolvedLinks 概念 |
| **實作方式** | SQLite 關係表 + 反向連結視圖（VIEW） |
| **相關性** | 直接填補 Skill-0 技能間關係的空白 |
| **合規性** | 使用純 SQLite，無額外授權問題 |
| **適當性** | 完美契合——Skill-0 已用 SQLite，擴展成本極低 |

#### 圖譜視覺化（Graph View）

| 評估面向 | 說明 |
|---------|------|
| **技術來源** | Obsidian Graph View（力導向圖） |
| **實作方式** | API 端點提供 JSON 格式的 nodes/edges 資料 |
| **相關性** | 使技能關係可被前端視覺化（Dashboard 或第三方工具） |
| **合規性** | 純後端 API，不引入前端依賴 |
| **適當性** | 高——API-first 設計，前端可自由選擇實作技術 |

#### Metadata Cache

| 評估面向 | 說明 |
|---------|------|
| **技術來源** | Obsidian MetadataCache 記憶體快取模式 |
| **實作方式** | Python dict 快取 + TTL 過期機制 |
| **相關性** | 加速連結查詢，避免重複 SQL 查詢 |
| **合規性** | 純 Python 實作，無外部依賴 |
| **適當性** | 中等——目前規模（53 技能）下效能提升有限，但為未來擴展做好準備 |

#### MOC 模式

| 評估面向 | 說明 |
|---------|------|
| **技術來源** | Obsidian Map of Content 社群模式 |
| **實作方式** | 自動化技能分類索引 API + 統計摘要 |
| **相關性** | 提供技能生態的結構化導航能力 |
| **合規性** | 使用現有語義搜尋 + 連結分析，無新依賴 |
| **適當性** | 高——與現有 category 欄位和語義搜尋高度互補 |

### 2.2 技術風險評估

| 風險項目 | 等級 | 緩解措施 |
|---------|------|---------|
| Schema 變更破壞向後相容 | 低 | `skill_links` 為可選欄位 |
| SQLite 效能瓶頸 | 低 | 53 技能規模遠低於瓶頸，且已建立索引 |
| 快取一致性問題 | 中 | 實作 cache invalidation 機制 |
| API 介面變更影響前端 | 低 | 新增端點，不修改既有 API |

---

## 3. 原始專案現階段評估報告

### 3.1 專案現狀

| 面向 | 狀態 | 詳情 |
|------|------|------|
| **已解析技能數** | 53 | `data/parsed/` 目錄 |
| **Schema 版本** | 2.2.0 | 三元分類 + 資源依賴 + Provenance |
| **向量搜尋** | ✅ 完備 | SQLite-vec + all-MiniLM-L6-v2 (384-dim) |
| **REST API** | ✅ 完備 | FastAPI，含搜尋/相似/聚類/統計 |
| **Dashboard** | 🔧 進行中 | React + Vite + TailwindCSS |
| **測試** | ✅ 部分 | pytest，含 helper 和 enhancement 測試 |
| **技能間關係** | ❌ 完全缺失 | 這正是本次實作要填補的空白 |

### 3.2 受影響的檔案

| 檔案 | 變更類型 | 說明 |
|------|---------|------|
| `schema/skill-decomposition.schema.json` | 擴展 | 新增 `skill_links` 定義 |
| `src/vector_db/vector_store.py` | 擴展 | 新增 skill_links 表 + 管理方法 |
| `src/vector_db/search.py` | 擴展 | 新增連結查詢方法 |
| `src/api/main.py` | 擴展 | 新增 API 端點 |
| `tests/test_skill_links.py` | 新增 | 連結功能測試 |

### 3.3 不受影響的檔案

- `data/parsed/*.json` — 現有技能檔案無需修改（`skill_links` 為可選）
- `src/vector_db/embedder.py` — 向量嵌入邏輯不受影響
- `src/parsers/` — 解析器不受影響
- 現有 API 端點 — 保持向後相容

---

## 4. 加入新項目的要求與優劣報告

### 4.1 功能要求

#### 必要功能（Must Have）
1. **skill_links Schema 定義**: 7 種連結類型（depends_on, extends, composes_with, alternative_to, related_to, derived_from, parent_of）
2. **SQLite skill_links 表**: 含索引與唯一性約束
3. **反向連結查詢視圖**: SQL VIEW 自動生成反向連結
4. **CRUD API**: 新增/查詢/刪除技能連結
5. **圖譜資料 API**: 回傳 nodes + edges 的 JSON 格式

#### 期望功能（Should Have）
6. **記憶體快取**: 連結關係的快取與過期機制
7. **MOC 索引 API**: 自動生成技能分類統計與導航
8. **反向連結端點**: 查詢某技能的所有反向連結

#### 可選功能（Nice to Have）
9. **連結強度推斷**: 基於語義相似度自動建議連結
10. **孤立技能偵測**: 識別無任何連結的技能

### 4.2 優勢分析

| 優勢 | 說明 |
|------|------|
| **填補關鍵空白** | 從孤立的技能集合升級為互聯的技能網路 |
| **低侵入性** | 全部為新增欄位/表/端點，不修改既有功能 |
| **向後相容** | `skill_links` 為可選欄位，既有資料無需變更 |
| **可漸進採用** | Schema → 資料庫 → API → 視覺化，分階段導入 |
| **技術一致性** | 延用既有技術棧（SQLite + FastAPI + Python） |
| **擴展性** | 為未來 Dashboard 圖譜視覺化奠定資料基礎 |

### 4.3 劣勢分析

| 劣勢 | 緩解策略 |
|------|---------|
| **增加 Schema 複雜度** | `skill_links` 為可選，不影響最小化使用場景 |
| **人工維護連結成本** | 提供自動建議功能，減少人工輸入 |
| **快取一致性風險** | 實作 TTL + invalidation 機制 |
| **測試覆蓋增加** | 新增專門測試套件 |

### 4.4 與現有系統的整合評估

| 整合點 | 難度 | 說明 |
|--------|------|------|
| VectorStore | 低 | 同一 SQLite 資料庫，新增表即可 |
| SemanticSearch | 低 | 新增查詢方法，不影響既有搜尋 |
| FastAPI | 低 | 新增 API 端點，REST 設計一致 |
| JSON Schema | 低 | 新增可選 property |
| Dashboard | N/A | 僅提供 API，前端不在本次範圍 |

---

## 5. 實作範圍與交付標準

### 5.1 交付項目

1. ✅ Schema 擴展（`skill_links` + `skill_link` 定義）
2. ✅ SQLite 資料表（`skill_links` 表 + 索引 + 視圖）
3. ✅ VectorStore 擴展（連結 CRUD 方法）
4. ✅ SemanticSearch 擴展（連結查詢 + 圖譜 + MOC）
5. ✅ FastAPI 端點（連結管理 + 圖譜 + MOC + 反向連結）
6. ✅ 記憶體快取（SkillLinkCache 類別）
7. ✅ 測試套件（test_skill_links.py）
8. ✅ 本文件（實作計畫書）

### 5.2 驗收標準

- [ ] 所有新增 API 端點回傳正確結果
- [ ] 反向連結查詢正確反轉關係類型
- [ ] 快取命中/失效機制正確運作
- [ ] 測試全數通過
- [ ] 既有測試不受影響

---

**文件版本**: 1.0.0  
**最後更新**: 2026-02-08  
**作者**: pingqLIN
