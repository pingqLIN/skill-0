"""
Skill-0 REST API
FastAPI 整合向量搜尋與分析功能
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import os
from pathlib import Path

# 確保可以找到 vector_db 模組
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from vector_db import SemanticSearch

# 配置
DB_PATH = os.getenv('SKILL0_DB_PATH', 'skills.db')
PARSED_DIR = os.getenv('SKILL0_PARSED_DIR', 'parsed')

# FastAPI 應用
app = FastAPI(
    title="Skill-0 API",
    description="Claude Skills & MCP Tools 語義搜尋 API",
    version="2.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全域搜尋引擎 (延遲初始化)
search_engine: Optional[SemanticSearch] = None


def get_search_engine() -> SemanticSearch:
    """取得或初始化搜尋引擎"""
    global search_engine
    if search_engine is None:
        search_engine = SemanticSearch(db_path=DB_PATH)
    return search_engine


# ==================== Models ====================

class SkillResult(BaseModel):
    """Skill 搜尋結果"""
    id: int
    name: str
    filename: str
    description: Optional[str] = None
    category: Optional[str] = None
    action_count: int = 0
    rule_count: int = 0
    directive_count: int = 0
    similarity: Optional[float] = None
    distance: Optional[float] = None


class SearchRequest(BaseModel):
    """搜尋請求"""
    query: str = Field(..., description="搜尋查詢", min_length=1)
    limit: int = Field(5, description="返回數量", ge=1, le=50)


class SearchResponse(BaseModel):
    """搜尋回應"""
    query: str
    results: List[SkillResult]
    count: int
    latency_ms: float


class SimilarRequest(BaseModel):
    """相似搜尋請求"""
    skill_name: str = Field(..., description="Skill 名稱")
    limit: int = Field(5, description="返回數量", ge=1, le=50)


class ClusterResponse(BaseModel):
    """聚類回應"""
    clusters: Dict[int, List[SkillResult]]
    total_skills: int
    n_clusters: int


class StatsResponse(BaseModel):
    """統計回應"""
    total_skills: int
    total_actions: int
    total_rules: int
    total_directives: int
    embedding_dimension: int
    model_name: str
    categories: Dict[str, int]


class IndexRequest(BaseModel):
    """索引請求"""
    parsed_dir: str = Field(PARSED_DIR, description="Parsed 目錄路徑")


class IndexResponse(BaseModel):
    """索引回應"""
    indexed_count: int
    elapsed_seconds: float
    message: str


# ==================== Endpoints ====================

@app.get("/", tags=["Root"])
async def root():
    """API 根路徑"""
    return {
        "name": "Skill-0 API",
        "version": "2.1.0",
        "description": "Claude Skills & MCP Tools 語義搜尋 API",
        "endpoints": {
            "search": "/api/search",
            "similar": "/api/similar",
            "cluster": "/api/cluster",
            "stats": "/api/stats",
            "skills": "/api/skills",
            "docs": "/docs"
        }
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """健康檢查"""
    try:
        engine = get_search_engine()
        stats = engine.get_statistics()
        return {
            "status": "healthy",
            "db_path": DB_PATH,
            "total_skills": stats['total_skills']
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unavailable: {str(e)}")


@app.post("/api/search", response_model=SearchResponse, tags=["Search"])
async def search_skills(request: SearchRequest):
    """
    語義搜尋 Skills
    
    使用自然語言查詢找到相關的 skills。
    """
    import time
    start = time.time()
    
    engine = get_search_engine()
    results = engine.search(request.query, limit=request.limit)
    
    elapsed = (time.time() - start) * 1000
    
    return SearchResponse(
        query=request.query,
        results=[SkillResult(**r) for r in results],
        count=len(results),
        latency_ms=round(elapsed, 2)
    )


@app.get("/api/search", response_model=SearchResponse, tags=["Search"])
async def search_skills_get(
    q: str = Query(..., description="搜尋查詢", min_length=1),
    limit: int = Query(5, description="返回數量", ge=1, le=50)
):
    """
    語義搜尋 Skills (GET)
    
    使用自然語言查詢找到相關的 skills。
    """
    import time
    start = time.time()
    
    engine = get_search_engine()
    results = engine.search(q, limit=limit)
    
    elapsed = (time.time() - start) * 1000
    
    return SearchResponse(
        query=q,
        results=[SkillResult(**r) for r in results],
        count=len(results),
        latency_ms=round(elapsed, 2)
    )


@app.post("/api/similar", response_model=SearchResponse, tags=["Search"])
async def find_similar_skills(request: SimilarRequest):
    """
    找相似 Skills
    
    根據指定的 skill 名稱找出功能相似的其他 skills。
    """
    import time
    start = time.time()
    
    engine = get_search_engine()
    results = engine.find_similar(request.skill_name, limit=request.limit)
    
    if not results:
        raise HTTPException(status_code=404, detail=f"Skill '{request.skill_name}' not found")
    
    elapsed = (time.time() - start) * 1000
    
    return SearchResponse(
        query=f"similar to: {request.skill_name}",
        results=[SkillResult(**r) for r in results],
        count=len(results),
        latency_ms=round(elapsed, 2)
    )


@app.get("/api/similar/{skill_name}", response_model=SearchResponse, tags=["Search"])
async def find_similar_skills_get(
    skill_name: str,
    limit: int = Query(5, description="返回數量", ge=1, le=50)
):
    """
    找相似 Skills (GET)
    """
    import time
    start = time.time()
    
    engine = get_search_engine()
    results = engine.find_similar(skill_name, limit=limit)
    
    if not results:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")
    
    elapsed = (time.time() - start) * 1000
    
    return SearchResponse(
        query=f"similar to: {skill_name}",
        results=[SkillResult(**r) for r in results],
        count=len(results),
        latency_ms=round(elapsed, 2)
    )


@app.get("/api/cluster", response_model=ClusterResponse, tags=["Analysis"])
async def cluster_skills(
    n: int = Query(5, description="聚類數量", ge=2, le=20)
):
    """
    Skills 聚類分析
    
    使用 K-Means 將所有 skills 自動分群。
    """
    engine = get_search_engine()
    clusters = engine.cluster_skills(n_clusters=n)
    
    # 轉換格式
    formatted_clusters = {}
    total = 0
    for cluster_id, skills in clusters.items():
        formatted_clusters[cluster_id] = [SkillResult(**s) for s in skills]
        total += len(skills)
    
    return ClusterResponse(
        clusters=formatted_clusters,
        total_skills=total,
        n_clusters=len(clusters)
    )


@app.get("/api/stats", response_model=StatsResponse, tags=["Info"])
async def get_statistics():
    """取得資料庫統計"""
    engine = get_search_engine()
    stats = engine.get_statistics()
    
    return StatsResponse(**stats)


@app.get("/api/skills", tags=["Info"])
async def list_all_skills(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100)
):
    """列出所有 Skills（分頁）"""
    engine = get_search_engine()
    all_skills = engine.store.get_all_skills()
    
    # 分頁
    start = (page - 1) * per_page
    end = start + per_page
    paginated = all_skills[start:end]
    
    return {
        "skills": [SkillResult(**s) for s in paginated],
        "total": len(all_skills),
        "page": page,
        "per_page": per_page,
        "total_pages": (len(all_skills) + per_page - 1) // per_page
    }


@app.get("/api/skills/{skill_id}", tags=["Info"])
async def get_skill_by_id(
    skill_id: int,
    include_json: bool = Query(False, description="是否包含原始 JSON")
):
    """根據 ID 取得 Skill 詳情"""
    engine = get_search_engine()
    skill = engine.store.get_skill_by_id(skill_id, include_json=include_json)
    
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill with ID {skill_id} not found")
    
    return skill


@app.post("/api/index", response_model=IndexResponse, tags=["Admin"])
async def index_skills(request: IndexRequest):
    """
    重新索引 Skills
    
    從 parsed 目錄重新建立向量索引。
    """
    import time
    start = time.time()
    
    engine = get_search_engine()
    
    # 清空並重新索引
    engine.store.clear()
    count = engine.index_skills(request.parsed_dir, show_progress=False)
    
    elapsed = time.time() - start
    
    return IndexResponse(
        indexed_count=count,
        elapsed_seconds=round(elapsed, 3),
        message=f"Successfully indexed {count} skills"
    )


# ==================== 啟動 ====================

def main():
    """啟動 API 伺服器"""
    import uvicorn
    
    # 確保資料庫存在
    if not Path(DB_PATH).exists():
        print(f"Database not found at {DB_PATH}, indexing skills...")
        engine = get_search_engine()
        engine.index_skills(PARSED_DIR, show_progress=True)
    
    print(f"""
╔════════════════════════════════════════════════════════════╗
║              Skill-0 API Server v2.1.0                     ║
╠════════════════════════════════════════════════════════════╣
║  API Docs:  http://127.0.0.1:8000/docs                     ║
║  ReDoc:     http://127.0.0.1:8000/redoc                    ║
║  Health:    http://127.0.0.1:8000/health                   ║
╚════════════════════════════════════════════════════════════╝
""")
    
    uvicorn.run(
        "api.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )


if __name__ == "__main__":
    main()
