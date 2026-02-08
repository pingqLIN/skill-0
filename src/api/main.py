"""
Skill-0 REST API
FastAPI integration with vector search and analysis features
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import os
from pathlib import Path

# Ensure vector_db module can be found
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from vector_db import SemanticSearch

# Configuration
DB_PATH = os.getenv('SKILL0_DB_PATH', 'skills.db')
PARSED_DIR = os.getenv('SKILL0_PARSED_DIR', 'parsed')

# FastAPI application
app = FastAPI(
    title="Skill-0 API",
    description="Claude Skills & MCP Tools Semantic Search API",
    version="2.3.0",
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

# Global search engine (lazy initialization)
search_engine: Optional[SemanticSearch] = None


def get_search_engine() -> SemanticSearch:
    """Get or initialize search engine"""
    global search_engine
    if search_engine is None:
        search_engine = SemanticSearch(db_path=DB_PATH)
    return search_engine


# ==================== Models ====================

class SkillResult(BaseModel):
    """Skill search result"""
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
    """Search request"""
    query: str = Field(..., description="Search query", min_length=1)
    limit: int = Field(5, description="Number of results", ge=1, le=50)


class SearchResponse(BaseModel):
    """Search response"""
    query: str
    results: List[SkillResult]
    count: int
    latency_ms: float


class SimilarRequest(BaseModel):
    """Similar search request"""
    skill_name: str = Field(..., description="Skill name")
    limit: int = Field(5, description="Number of results", ge=1, le=50)


class ClusterResponse(BaseModel):
    """Cluster response"""
    clusters: Dict[int, List[SkillResult]]
    total_skills: int
    n_clusters: int


class StatsResponse(BaseModel):
    """Statistics response"""
    total_skills: int
    total_actions: int
    total_rules: int
    total_directives: int
    total_links: int = 0
    embedding_dimension: int
    model_name: str
    categories: Dict[str, int]
    cache_stats: Optional[Dict[str, Any]] = None


class IndexRequest(BaseModel):
    """Index request"""
    parsed_dir: str = Field(PARSED_DIR, description="Parsed directory path")


class IndexResponse(BaseModel):
    """Index response"""
    indexed_count: int
    elapsed_seconds: float
    message: str


# ==================== Endpoints ====================

@app.get("/", tags=["Root"])
async def root():
    """API root path"""
    return {
        "name": "Skill-0 API",
        "version": "2.3.0",
        "description": "Claude Skills & MCP Tools Semantic Search API",
        "endpoints": {
            "search": "/api/search",
            "similar": "/api/similar",
            "cluster": "/api/cluster",
            "stats": "/api/stats",
            "skills": "/api/skills",
            "links": "/api/links",
            "backlinks": "/api/backlinks/{skill_id}",
            "graph": "/api/graph",
            "moc": "/api/moc",
            "docs": "/docs"
        }
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check"""
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
    Semantic search for Skills
    
    Use natural language query to find relevant skills.
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
    q: str = Query(..., description="Search query", min_length=1),
    limit: int = Query(5, description="Number of results", ge=1, le=50)
):
    """
    Semantic search for Skills (GET)
    
    Use natural language query to find relevant skills.
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
    Find similar Skills
    
    Find other skills with similar functionality based on the specified skill name.
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
    limit: int = Query(5, description="Number of results", ge=1, le=50)
):
    """
    Find similar Skills (GET)
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
    n: int = Query(5, description="Number of clusters", ge=2, le=20)
):
    """
    Skills cluster analysis
    
    Automatically group all skills using K-Means clustering.
    """
    engine = get_search_engine()
    clusters = engine.cluster_skills(n_clusters=n)
    
    # Convert format
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
    """Get database statistics"""
    engine = get_search_engine()
    stats = engine.get_statistics()
    
    return StatsResponse(**stats)


@app.get("/api/skills", tags=["Info"])
async def list_all_skills(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100)
):
    """List all Skills (paginated)"""
    engine = get_search_engine()
    all_skills = engine.store.get_all_skills()
    
    # Pagination
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
    include_json: bool = Query(False, description="Include original JSON")
):
    """Get Skill details by ID"""
    engine = get_search_engine()
    skill = engine.store.get_skill_by_id(skill_id, include_json=include_json)
    
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill with ID {skill_id} not found")
    
    return skill


@app.post("/api/index", response_model=IndexResponse, tags=["Admin"])
async def index_skills(request: IndexRequest):
    """
    Re-index Skills
    
    Rebuild vector index from parsed directory.
    """
    import time
    start = time.time()
    
    engine = get_search_engine()
    
    # Clear and re-index
    engine.store.clear()
    count = engine.index_skills(request.parsed_dir, show_progress=False)
    
    elapsed = time.time() - start
    
    return IndexResponse(
        indexed_count=count,
        elapsed_seconds=round(elapsed, 3),
        message=f"Successfully indexed {count} skills"
    )


# ==================== Skill Links (借鑑 Obsidian) ====================

class SkillLinkRequest(BaseModel):
    """Skill link creation request"""
    source_skill_id: str = Field(..., description="Source skill ID")
    target_skill_id: str = Field(..., description="Target skill ID")
    link_type: str = Field(..., description="Link type")
    description: Optional[str] = Field(None, description="Link description")
    strength: float = Field(0.5, description="Link strength (0-1)", ge=0, le=1)
    bidirectional: bool = Field(False, description="Whether bidirectional")


class SkillLinkResponse(BaseModel):
    """Skill link response"""
    id: Optional[int] = None
    source_skill_id: str
    target_skill_id: str
    link_type: str
    description: Optional[str] = None
    strength: float = 0.5
    bidirectional: bool = False
    direction: Optional[str] = None
    linked_from: Optional[str] = None
    created_at: Optional[str] = None


class GraphResponse(BaseModel):
    """Graph data response"""
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    stats: Dict[str, Any]


class MOCCategory(BaseModel):
    """MOC category"""
    category: str
    skills: List[Dict[str, Any]]
    total_actions: int
    total_rules: int
    total_directives: int
    total_links: int


class MOCResponse(BaseModel):
    """MOC response"""
    categories: List[MOCCategory]
    summary: Dict[str, int]


@app.post("/api/links", tags=["Links"])
async def create_skill_link(request: SkillLinkRequest):
    """
    Create a link between two skills (inspired by Obsidian bidirectional links)
    
    Link types: depends_on, extends, composes_with, alternative_to, 
    related_to, derived_from, parent_of
    """
    engine = get_search_engine()
    try:
        link_id = engine.add_link(
            source_skill_id=request.source_skill_id,
            target_skill_id=request.target_skill_id,
            link_type=request.link_type,
            description=request.description,
            strength=request.strength,
            bidirectional=request.bidirectional,
        )
        return {
            "id": link_id,
            "message": f"Link created: {request.source_skill_id} --{request.link_type}--> {request.target_skill_id}",
            "bidirectional": request.bidirectional,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/links", tags=["Links"])
async def list_all_links():
    """List all skill links"""
    engine = get_search_engine()
    links = engine.store.get_all_links()
    return {
        "links": [SkillLinkResponse(**link) for link in links],
        "total": len(links),
    }


@app.get("/api/links/{skill_id}", tags=["Links"])
async def get_skill_links(skill_id: str):
    """Get outgoing links for a skill"""
    engine = get_search_engine()
    links = engine.get_links(skill_id)
    return {
        "skill_id": skill_id,
        "links": links,
        "count": len(links),
    }


@app.get("/api/backlinks/{skill_id}", tags=["Links"])
async def get_skill_backlinks(skill_id: str):
    """
    Get backlinks for a skill (inspired by Obsidian Backlinks)
    
    Returns all skills that link TO this skill, including
    reverse relationships from bidirectional links.
    """
    engine = get_search_engine()
    backlinks = engine.get_backlinks(skill_id)
    return {
        "skill_id": skill_id,
        "backlinks": backlinks,
        "count": len(backlinks),
    }


@app.delete("/api/links/{link_id}", tags=["Links"])
async def delete_skill_link(link_id: int):
    """Delete a skill link by ID"""
    engine = get_search_engine()
    success = engine.delete_link(link_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Link with ID {link_id} not found")
    return {"message": f"Link {link_id} deleted", "success": True}


@app.get("/api/graph", response_model=GraphResponse, tags=["Graph"])
async def get_graph_data():
    """
    Get skill relationship graph data (inspired by Obsidian Graph View)
    
    Returns nodes (skills) and edges (links) suitable for
    force-directed graph visualization.
    """
    engine = get_search_engine()
    graph = engine.get_graph_data()
    return GraphResponse(**graph)


@app.get("/api/moc", response_model=MOCResponse, tags=["MOC"])
async def get_moc():
    """
    Get skill Map of Content (inspired by Obsidian MOC pattern)
    
    Returns skills organized by category with link statistics,
    serving as a structured navigation index.
    """
    engine = get_search_engine()
    moc = engine.get_moc()
    return MOCResponse(**moc)


@app.get("/api/links/stats", tags=["Links"])
async def get_link_statistics():
    """Get link statistics"""
    engine = get_search_engine()
    return engine.get_link_statistics()


@app.get("/api/cache/stats", tags=["Cache"])
async def get_cache_statistics():
    """
    Get cache statistics (inspired by Obsidian MetadataCache)
    """
    engine = get_search_engine()
    return engine.get_cache_stats()


# ==================== Startup ====================

def main():
    """Start API server"""
    import uvicorn
    
    # Ensure database exists
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
