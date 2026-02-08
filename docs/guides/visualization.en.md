# Visualization Guide: Skill Relationship Graph

This guide covers Skill-0’s relationship visualization, powered by the `/api/graph` endpoint and rendered in the Dashboard’s **Skill Graph** view.

## 1. Overview

- **Data source**: FastAPI `/api/graph` returning `nodes`, `edges`, and stats.
- **Visualization**: The **Skill Graph** page (`/graph`) renders nodes and links as an SVG graph.
- **Node styling**: Node size reflects `link_count`, and color follows each skill’s category.

## 2. Start the Services

```bash
# Start the API
python -m src.api.main

# Start the dashboard
cd skill-0-dashboard/apps/web
npm install
npm run dev
```

By default, the UI connects to `http://localhost:8000`. To override, set `VITE_API_URL` for the dashboard.

## 3. Open the Graph View

1. Visit `http://localhost:5173/graph`
2. Explore the skill nodes and relationship links
3. The right panel summarizes node/edge counts and link type distribution

## 4. /api/graph Response Schema

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

## 5. Troubleshooting

- **No edges shown**: No skill links exist yet; add links via `/api/links`.
- **Nodes appear crowded**: Resize the window or zoom to improve readability.
