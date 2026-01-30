"""
Semantic Search - Semantic Search API
Integrates SkillEmbedder and VectorStore to provide complete search functionality
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Union
import numpy as np

from .embedder import SkillEmbedder
from .vector_store import VectorStore


class SemanticSearch:
    """Semantic search engine"""
    
    def __init__(
        self,
        db_path: Union[str, Path] = 'skills.db',
        model_name: str = 'all-MiniLM-L6-v2'
    ):
        """
        Initialize search engine
        
        Args:
            db_path: Vector database path
            model_name: Embedding model name
        """
        self.embedder = SkillEmbedder(model_name)
        self.store = VectorStore(db_path, dimension=self.embedder.dimension)
        
    def index_skills(self, parsed_dir: Union[str, Path], show_progress: bool = True) -> int:
        """
        Index all skills in the parsed directory
        
        Args:
            parsed_dir: Path to parsed/ directory
            show_progress: Whether to display progress
            
        Returns:
            int: Number of skills indexed
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
    
    def search(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Semantic search for skills
        
        Args:
            query: Natural language query
            limit: Number of results to return
            
        Returns:
            List[Dict]: Matched skills (with similarity scores)
        """
        query_embedding = self.embedder.embed_query(query)
        results = self.store.search(query_embedding, limit=limit)
        
        # Convert distance to similarity (0-1)
        for r in results:
            # sqlite-vec uses L2 distance, convert to similarity
            # Smaller distance = higher similarity
            r['similarity'] = 1.0 / (1.0 + r['distance'])
            
        return results
    
    def find_similar(self, skill_name: str, limit: int = 5) -> List[Dict]:
        """
        Find other skills similar to the specified skill
        
        Args:
            skill_name: Skill name
            limit: Number of results to return (excluding self)
            
        Returns:
            List[Dict]: Similar skills
        """
        # Find specified skill
        all_skills = self.store.get_all_skills()
        target = None
        for s in all_skills:
            if s['name'].lower() == skill_name.lower():
                target = s
                break
                
        if not target:
            return []
            
        # Get vector
        embedding = self.store.get_embedding(target['id'])
        if embedding is None:
            return []
            
        # Search for similar (fetch one extra since self will be included)
        results = self.store.search(embedding, limit=limit + 1)
        
        # Exclude self
        results = [r for r in results if r['id'] != target['id']]
        
        # Add similarity
        for r in results:
            r['similarity'] = 1.0 / (1.0 + r['distance'])
            
        return results[:limit]
    
    def cluster_skills(self, n_clusters: int = 5) -> Dict[int, List[Dict]]:
        """
        Perform cluster analysis on skills
        
        Args:
            n_clusters: Number of clusters
            
        Returns:
            Dict[int, List[Dict]]: Clustering results
        """
        from sklearn.cluster import KMeans
        
        all_skills = self.store.get_all_skills()
        if len(all_skills) < n_clusters:
            n_clusters = len(all_skills)
            
        # Collect all vectors
        embeddings = []
        for s in all_skills:
            emb = self.store.get_embedding(s['id'])
            if emb is not None:
                embeddings.append(emb)
            else:
                embeddings.append(np.zeros(self.embedder.dimension))
                
        embeddings = np.array(embeddings)
        
        # K-Means clustering
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(embeddings)
        
        # Organize results
        clusters = {}
        for skill, label in zip(all_skills, labels):
            label = int(label)
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(skill)
            
        return clusters
    
    def get_statistics(self) -> Dict:
        """Get search engine statistics"""
        stats = self.store.get_statistics()
        stats['embedding_dimension'] = self.embedder.dimension
        stats['model_name'] = 'all-MiniLM-L6-v2'
        return stats
    
    def close(self):
        """Close connections"""
        self.store.close()
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def main():
    """CLI entry point"""
    import argparse
    import time
    
    parser = argparse.ArgumentParser(description='Skill-0 Semantic Search')
    parser.add_argument('--db', default='skills.db', help='Database path')
    parser.add_argument('--parsed-dir', default='parsed', help='Parsed skills directory')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # index subcommand
    index_parser = subparsers.add_parser('index', help='Index skills from parsed directory')
    
    # search subcommand
    search_parser = subparsers.add_parser('search', help='Search for skills')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('-n', '--limit', type=int, default=5, help='Number of results')
    
    # similar subcommand
    similar_parser = subparsers.add_parser('similar', help='Find similar skills')
    similar_parser.add_argument('skill_name', help='Skill name to find similar')
    similar_parser.add_argument('-n', '--limit', type=int, default=5, help='Number of results')
    
    # cluster subcommand
    cluster_parser = subparsers.add_parser('cluster', help='Cluster skills')
    cluster_parser.add_argument('-n', '--clusters', type=int, default=5, help='Number of clusters')
    
    # stats subcommand
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
