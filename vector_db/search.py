"""
Semantic Search - 語義搜尋 API
整合 Embedder 和 VectorStore，提供完整的搜尋功能
"""

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import threading
from contextlib import contextmanager
from functools import wraps
from typing import Dict, List, Optional, Union
import numpy as np

from .embedder import SkillEmbedder
from .vector_store import VectorStore
from asset_registry.repositories import LegacySkillAssetRepository
from asset_registry.search import AssetSearchResult


REPRESENTATION_VERSION = "skill-text-v1"


def _serialized(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        with self._operation_lock:
            return method(self, *args, **kwargs)

    return wrapper


@dataclass(frozen=True)
class IndexReport:
    total: int
    changed: int
    unchanged: int
    removed: int


def _default_model_name() -> str:
    local_model = Path(__file__).resolve().parent.parent / '.hf-cache' / 'all-MiniLM-L6-v2'
    if local_model.exists():
        return str(local_model)
    return 'all-MiniLM-L6-v2'


class SemanticSearch:
    """語義搜尋引擎"""
    
    def __init__(
        self,
        db_path: Union[str, Path] = 'skills.db',
        model_name: Optional[str] = None,
        *,
        initialize_schema: bool = True,
    ):
        """
        初始化搜尋引擎
        
        Args:
            db_path: 向量資料庫路徑
            model_name: embedding 模型名稱
        """
        self.model_name = model_name or os.getenv('SKILL0_EMBEDDING_MODEL', _default_model_name())
        self.dimension = SkillEmbedder.DEFAULT_DIMENSION
        self._embedder: Optional[SkillEmbedder] = None
        self._operation_lock = threading.RLock()
        self.store = VectorStore(
            db_path,
            dimension=self.dimension,
            initialize_schema=initialize_schema,
        )

    @contextmanager
    def open_unit_of_work(self):
        """Open one factory-backed Index connection while sharing model state."""

        clone = object.__new__(SemanticSearch)
        clone.model_name = self.model_name
        clone.dimension = self.dimension
        clone._embedder = self._embedder
        clone._operation_lock = self._operation_lock
        clone.store = VectorStore(
            self.store.db_path,
            dimension=self.store.dimension,
            initialize_schema=False,
        )
        try:
            yield clone
            if self._embedder is None and clone._embedder is not None:
                self._embedder = clone._embedder
                self.dimension = clone.dimension
        finally:
            clone.close()

    @property
    def embedder(self) -> SkillEmbedder:
        """延遲初始化 embedder，避免純讀取路徑碰到模型載入。"""
        if self._embedder is None:
            self._embedder = SkillEmbedder(self.model_name)
            self.dimension = self._embedder.dimension
        return self._embedder

    def _embedding_identity(self) -> tuple[str, str]:
        model_path = Path(self.model_name)
        model_id = model_path.name if model_path.exists() else self.model_name
        configured_version = os.getenv("SKILL0_EMBEDDING_MODEL_VERSION")
        if configured_version:
            return model_id, configured_version
        if model_path.is_dir():
            digest = hashlib.sha256()
            matched = False
            for candidate in sorted(
                (path for path in model_path.rglob("*") if path.is_file()),
                key=lambda path: path.relative_to(model_path).as_posix(),
            ):
                relative = candidate.relative_to(model_path).as_posix()
                digest.update(relative.encode("utf-8"))
                with candidate.open("rb") as handle:
                    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                        digest.update(chunk)
                matched = True
            if matched:
                return model_id, "sha256:" + digest.hexdigest()
        return model_id, "unversioned"
        
    @_serialized
    def index_skills(self, parsed_dir: Union[str, Path], show_progress: bool = True) -> int:
        """
        索引 parsed 目錄中的所有 skills
        
        Args:
            parsed_dir: parsed/ 目錄路徑
            show_progress: 是否顯示進度
            
        Returns:
            int: 索引的 skill 數量
        """
        skills = self.embedder.load_skills_from_dir(parsed_dir)
        
        if not skills:
            print(f"No skills found in {parsed_dir}")
            return 0
            
        print(f"Embedding {len(skills)} skills...")
        embeddings = self.embedder.embed_skills(skills, show_progress=show_progress)
        
        print(f"Indexing to database...")
        self.store.insert_skills_batch(skills, embeddings)
        
        print(f"✓ Indexed {len(skills)} skills")
        return len(skills)

    @_serialized
    def index_assets(
        self,
        parsed_dir: Union[str, Path],
        *,
        representation_version: str = REPRESENTATION_VERSION,
        show_progress: bool = True,
    ) -> IndexReport:
        """Incrementally reconcile Skill-backed Asset projections."""

        if not self.store.has_asset_index_state():
            raise RuntimeError("asset_index_state migration is required")
        repository = LegacySkillAssetRepository(Path(parsed_dir))
        revisions = repository.list_revisions()
        model_id, model_version = self._embedding_identity()
        if model_version == "unversioned":
            raise RuntimeError(
                "Incremental indexing requires SKILL0_EMBEDDING_MODEL_VERSION "
                "or a digestible local model directory"
            )
        existing = {
            (
                row["asset_id"], row["revision_id"], row["representation_version"],
                row["embedding_model_id"], row["embedding_model_version"],
                row["content_hash"], row["source_path"],
            )
            for row in self.store.get_index_state()
        }
        changed = []
        active_sources = {item.source_path.as_posix() for item in revisions}
        existing_sources = {item[-1] for item in existing}
        for revision in revisions:
            identity = (
                revision.asset_id,
                revision.revision_id,
                representation_version,
                model_id,
                model_version,
                revision.content_hash,
                revision.source_path.as_posix(),
            )
            if identity not in existing:
                changed.append(revision)

        skills = []
        states = []
        for revision in changed:
            skill = dict(revision.payload)
            skill["_filename"] = revision.source_path.as_posix()
            skills.append(skill)
            states.append(
                {
                    "asset_id": revision.asset_id,
                    "revision_id": revision.revision_id,
                    "representation_version": representation_version,
                    "embedding_model_id": model_id,
                    "embedding_model_version": model_version,
                    "content_hash": revision.content_hash,
                    "source_path": revision.source_path.as_posix(),
                    "indexed_at": datetime.now(timezone.utc).isoformat(),
                }
            )

        with self._operation_lock:
            embeddings = (
                self.embedder.embed_skills(skills, show_progress=show_progress)
                if skills
                else []
            )
            self.store.reconcile_assets_batch(
                skills,
                embeddings,
                states,
                active_source_paths=active_sources,
            )
        return IndexReport(
            total=len(revisions),
            changed=len(changed),
            unchanged=len(revisions) - len(changed),
            removed=len(existing_sources - active_sources),
        )

    @_serialized
    def search_assets(
        self,
        query: str,
        *,
        asset_types: tuple[str, ...] = ("skill",),
        limit: int = 5,
    ) -> List[AssetSearchResult]:
        if "skill" not in asset_types:
            return []
        with self._operation_lock:
            query_embedding = self.embedder.embed_query(query)
            results = self.store.search_assets(query_embedding, limit=limit)
        return [
            AssetSearchResult(
                **row,
                similarity=1.0 / (1.0 + row["distance"]),
            )
            for row in results
        ]
    
    @_serialized
    def search(self, query: str, limit: int = 5) -> List[Dict]:
        """
        語義搜尋 skills
        
        Args:
            query: 自然語言查詢
            limit: 返回結果數量
            
        Returns:
            List[Dict]: 匹配的 skills (含相似度分數)
        """
        with self._operation_lock:
            query_embedding = self.embedder.embed_query(query)
            results = self.store.search(query_embedding, limit=limit)
        
        # 轉換 distance 為 similarity (0-1)
        for r in results:
            # sqlite-vec 使用 L2 距離，轉換為相似度
            # 較小的距離 = 較高的相似度
            r['similarity'] = 1.0 / (1.0 + r['distance'])
            
        return results
    
    @_serialized
    def find_similar(self, skill_name: str, limit: int = 5) -> List[Dict]:
        """
        找出與指定 skill 相似的其他 skills
        
        Args:
            skill_name: skill 名稱
            limit: 返回數量 (不含自身)
            
        Returns:
            List[Dict]: 相似 skills
        """
        # 找到指定 skill
        all_skills = self.store.get_all_skills()
        target = None
        for s in all_skills:
            if s['name'].lower() == skill_name.lower():
                target = s
                break
                
        if not target:
            return []
            
        # 取得向量
        embedding = self.store.get_embedding(target['id'])
        if embedding is None:
            return []
            
        # 搜尋相似 (多取一個因為會包含自身)
        results = self.store.search(embedding, limit=limit + 1)
        
        # 排除自身
        results = [r for r in results if r['id'] != target['id']]
        
        # 加入相似度
        for r in results:
            r['similarity'] = 1.0 / (1.0 + r['distance'])
            
        return results[:limit]
    
    @_serialized
    def cluster_skills(self, n_clusters: int = 5) -> Dict[int, List[Dict]]:
        """
        對 skills 進行聚類分析
        
        Args:
            n_clusters: 聚類數量
            
        Returns:
            Dict[int, List[Dict]]: 聚類結果
        """
        from sklearn.cluster import KMeans
        
        all_skills = self.store.get_all_skills()
        if len(all_skills) < n_clusters:
            n_clusters = len(all_skills)
            
        # 收集所有向量
        embeddings = []
        for s in all_skills:
            emb = self.store.get_embedding(s['id'])
            if emb is not None:
                embeddings.append(emb)
            else:
                embeddings.append(np.zeros(self.embedder.dimension))
                
        embeddings = np.array(embeddings)
        
        # K-Means 聚類
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(embeddings)
        
        # 組織結果
        clusters = {}
        for skill, label in zip(all_skills, labels):
            label = int(label)
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(skill)
            
        return clusters
    
    @_serialized
    def get_statistics(self) -> Dict:
        """取得搜尋引擎統計"""
        stats = self.store.get_statistics()
        stats['embedding_dimension'] = self.dimension
        stats['model_name'] = self.model_name
        return stats
    
    def close(self):
        """關閉連線"""
        self.store.close()
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def main():
    """CLI 入口"""
    import argparse
    import time
    
    parser = argparse.ArgumentParser(description='Skill-0 Semantic Search')
    parser.add_argument('--db', default='skills.db', help='Database path')
    parser.add_argument('--parsed-dir', default='parsed', help='Parsed skills directory')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # index 子命令
    index_parser = subparsers.add_parser('index', help='Index skills from parsed directory')
    
    # search 子命令
    search_parser = subparsers.add_parser('search', help='Search for skills')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('-n', '--limit', type=int, default=5, help='Number of results')
    
    # similar 子命令
    similar_parser = subparsers.add_parser('similar', help='Find similar skills')
    similar_parser.add_argument('skill_name', help='Skill name to find similar')
    similar_parser.add_argument('-n', '--limit', type=int, default=5, help='Number of results')
    
    # cluster 子命令
    cluster_parser = subparsers.add_parser('cluster', help='Cluster skills')
    cluster_parser.add_argument('-n', '--clusters', type=int, default=5, help='Number of clusters')
    
    # stats 子命令
    stats_parser = subparsers.add_parser('stats', help='Show statistics')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
        
    search_engine = SemanticSearch(db_path=args.db)
    
    try:
        if args.command == 'index':
            start = time.time()
            count = search_engine.index_skills(args.parsed_dir)
            elapsed = time.time() - start
            print(f"\n✓ Indexed {count} skills in {elapsed:.2f}s")
            
        elif args.command == 'search':
            print(f"\n🔍 Searching for: {args.query}")
            print("-" * 50)
            
            start = time.time()
            results = search_engine.search(args.query, limit=args.limit)
            elapsed = time.time() - start
            
            for i, r in enumerate(results, 1):
                print(f"{i}. {r['name']} ({r['similarity']:.2%})")
                print(f"   Category: {r['category'] or 'N/A'}")
                print(f"   {r['description'][:80]}..." if len(r.get('description', '')) > 80 else f"   {r.get('description', 'N/A')}")
                print()
                
            print(f"Search completed in {elapsed*1000:.1f}ms")
            
        elif args.command == 'similar':
            print(f"\n🔗 Finding skills similar to: {args.skill_name}")
            print("-" * 50)
            
            results = search_engine.find_similar(args.skill_name, limit=args.limit)
            
            if not results:
                print(f"Skill '{args.skill_name}' not found")
            else:
                for i, r in enumerate(results, 1):
                    print(f"{i}. {r['name']} ({r['similarity']:.2%})")
                    print(f"   Category: {r['category'] or 'N/A'}")
                    print()
                    
        elif args.command == 'cluster':
            print(f"\n📊 Clustering skills into {args.clusters} groups...")
            print("-" * 50)
            
            clusters = search_engine.cluster_skills(n_clusters=args.clusters)
            
            for cluster_id, skills in sorted(clusters.items()):
                print(f"\n【Cluster {cluster_id + 1}】({len(skills)} skills)")
                for s in skills:
                    print(f"  • {s['name']}")
                    
        elif args.command == 'stats':
            stats = search_engine.get_statistics()
            print("\n📈 Database Statistics")
            print("-" * 50)
            print(f"Total Skills: {stats['total_skills']}")
            print(f"Total Actions: {stats['total_actions']}")
            print(f"Total Rules: {stats['total_rules']}")
            print(f"Total Directives: {stats['total_directives']}")
            print(f"Embedding Dimension: {stats['embedding_dimension']}")
            print(f"\nCategories:")
            for cat, count in stats['categories'].items():
                print(f"  • {cat}: {count}")
                
    finally:
        search_engine.close()


if __name__ == '__main__':
    main()
