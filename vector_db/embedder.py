"""
Skill Embedder - Converts skill definitions to vector embeddings
Uses sentence-transformers' all-MiniLM-L6-v2 model
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Union
from sentence_transformers import SentenceTransformer
import numpy as np


class SkillEmbedder:
    """Converts skill JSON to semantic vectors"""
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """
        Initialize embedder
        
        Args:
            model_name: sentence-transformers model name.
                       Default: all-MiniLM-L6-v2 (384 dimensions, fast and efficient)
        """
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        
    def skill_to_text(self, skill: Dict) -> str:
        """
        Convert skill JSON to embeddable text
        
        Extracts key semantic information:
        - meta.name, meta.description, meta.title
        - decomposition.actions
        - decomposition.rules
        - decomposition.directives
        """
        parts = []
        
        # Extract basic information from meta
        meta = skill.get('meta', {})
        if meta.get('title'):
            parts.append(f"Skill: {meta['title']}")
        elif meta.get('name'):
            parts.append(f"Skill: {meta['name']}")
        if meta.get('description'):
            parts.append(f"Description: {meta['description']}")
            
        # Extract elements from decomposition
        decomp = skill.get('decomposition', {})
            
        # Actions
        actions = decomp.get('actions', [])
        if actions:
            action_texts = []
            for action in actions:
                action_type = action.get('type', 'unknown')
                action_desc = action.get('description', action.get('id', ''))
                action_texts.append(f"{action_type}: {action_desc}")
            if action_texts:
                parts.append(f"Actions: {'; '.join(action_texts)}")
                
        # Rules
        rules = decomp.get('rules', [])
        if rules:
            rule_texts = []
            for rule in rules:
                rule_mode = rule.get('mode', 'unknown')
                rule_cond = rule.get('condition', rule.get('id', ''))
                rule_texts.append(f"{rule_mode}: {rule_cond}")
            if rule_texts:
                parts.append(f"Rules: {'; '.join(rule_texts)}")
                
        # Directives
        directives = decomp.get('directives', [])
        if directives:
            directive_texts = []
            for directive in directives:
                dir_type = directive.get('type', 'unknown')
                dir_content = directive.get('content', directive.get('id', ''))
                # Truncate overly long content
                if len(dir_content) > 200:
                    dir_content = dir_content[:200] + '...'
                directive_texts.append(f"{dir_type}: {dir_content}")
            if directive_texts:
                parts.append(f"Directives: {'; '.join(directive_texts)}")
                
        return ' | '.join(parts)
    
    def embed_skill(self, skill: Dict) -> np.ndarray:
        """
        Convert a single skill to a vector
        
        Returns:
            np.ndarray: 384-dimensional vector (float32)
        """
        text = self.skill_to_text(skill)
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.astype(np.float32)
    
    def embed_skills(self, skills: List[Dict], show_progress: bool = True) -> List[np.ndarray]:
        """
        Batch embed multiple skills
        
        Args:
            skills: List of skill JSONs
            show_progress: Whether to display progress bar
            
        Returns:
            List[np.ndarray]: List of vectors
        """
        texts = [self.skill_to_text(s) for s in skills]
        embeddings = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=show_progress)
        return [e.astype(np.float32) for e in embeddings]
    
    def embed_query(self, query: str) -> np.ndarray:
        """
        Convert search query to a vector
        
        Args:
            query: Natural language query
            
        Returns:
            np.ndarray: 384-dimensional vector
        """
        embedding = self.model.encode(query, convert_to_numpy=True)
        return embedding.astype(np.float32)
    
    def load_skills_from_dir(self, parsed_dir: Union[str, Path]) -> List[Dict]:
        """
        Load all skill JSONs from directory
        
        Args:
            parsed_dir: Path to parsed/ directory
            
        Returns:
            List[Dict]: List of skill dictionaries (with _filename field)
        """
        parsed_path = Path(parsed_dir)
        skills = []
        
        for json_file in sorted(parsed_path.glob('*-skill.json')):
            with open(json_file, 'r', encoding='utf-8') as f:
                skill = json.load(f)
                skill['_filename'] = json_file.name
                skills.append(skill)
                
        return skills


if __name__ == '__main__':
    # Test
    embedder = SkillEmbedder()
    print(f"Model dimension: {embedder.dimension}")
    
    # Test query embedding
    query = "PDF document processing and manipulation"
    vec = embedder.embed_query(query)
    print(f"Query vector shape: {vec.shape}")
    print(f"Query vector sample: {vec[:5]}")
