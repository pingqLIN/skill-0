# 視覺化指南：技能關係圖譜

此指南說明 Skill-0 的技能關係視覺化功能，利用 `/api/graph` 端點提供的資料，在 Dashboard 中呈現類 Obsidian Graph View 的關係圖。

## 1. 功能概述

- **資料來源**：FastAPI `/api/graph`，回傳 `nodes`、`edges` 與統計資訊。
- **視覺化呈現**：Dashboard 的 **Skill Graph** 頁面（`/graph`）以 SVG 方式繪製節點與關係線。
- **節點規則**：節點大小依 `link_count` 調整，顏色依技能分類顯示。

## 2. 啟動方式

```bash
# 啟動 API
python -m src.api.main

# 啟動 Dashboard
cd skill-0-dashboard/apps/web
npm install
npm run dev
```

預設 API 位置為 `http://localhost:8000`。如需自訂，請在 Dashboard 環境變數設定 `VITE_API_URL`。

## 3. 瀏覽視覺化畫面

1. 開啟瀏覽器：`http://localhost:5173/graph`
2. 查看技能節點與連結線條
3. 右側面板會顯示節點/邊統計與連結類型分布

## 4. /api/graph 資料欄位

```json
{
  "nodes": [
    {
      "id": "docx-skill",
      "name": "Docx Skill",
      "category": "document",
      "link_count": 3,
      "action_count": 12,
      "rule_count": 4,
      "directive_count": 6
    }
  ],
  "edges": [
    {
      "source": "docx-skill",
      "target": "pdf-skill",
      "link_type": "related_to",
      "strength": 0.6,
      "bidirectional": true
    }
  ],
  "stats": {
    "total_nodes": 32,
    "total_edges": 18,
    "orphan_nodes": 12,
    "link_type_distribution": {
      "related_to": 10
    }
  }
}
```

## 5. 常見問題

- **圖譜沒有邊**：代表目前沒有建立技能連結，可先透過 `/api/links` 新增關係。
- **節點顯示密集**：可透過縮放瀏覽器或調整視窗大小改善閱讀性。
