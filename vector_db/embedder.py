"""
Skill Embedder - 將 skill 定義轉換為向量嵌入
使用 sentence-transformers 的 all-MiniLM-L6-v2 模型
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Union
from sentence_transformers import SentenceTransformer
import numpy as np


class SkillEmbedder:
    """將 skill JSON 轉換為語義向量"""
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """
        初始化 embedder
        
        Args:
            model_name: sentence-transformers 模型名稱
                       預設使用 all-MiniLM-L6-v2 (384 維, 快速且高效)
        """
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        
    def skill_to_text(self, skill: Dict) -> str:
        """
        將 skill JSON 轉換為可嵌入的文本
        
        提取關鍵語義資訊:
        - meta.name, meta.description, meta.title
        - decomposition.actions
        - decomposition.rules
        - decomposition.directives
        """
        parts = []
        
        # 從 meta 提取基本資訊
        meta = skill.get('meta', {})
        if meta.get('title'):
            parts.append(f"Skill: {meta['title']}")
        elif meta.get('name'):
            parts.append(f"Skill: {meta['name']}")
        if meta.get('description'):
            parts.append(f"Description: {meta['description']}")
            
        # 從 decomposition 提取元素
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
                # 截斷過長的內容
                if len(dir_content) > 200:
                    dir_content = dir_content[:200] + '...'
                directive_texts.append(f"{dir_type}: {dir_content}")
            if directive_texts:
                parts.append(f"Directives: {'; '.join(directive_texts)}")
                
        return ' | '.join(parts)
    
    def embed_skill(self, skill: Dict) -> np.ndarray:
        """
        將單個 skill 轉換為向量
        
        Returns:
            np.ndarray: 384 維向量 (float32)
        """
        text = self.skill_to_text(skill)
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.astype(np.float32)
    
    def embed_skills(self, skills: List[Dict], show_progress: bool = True) -> List[np.ndarray]:
        """
        批次嵌入多個 skills
        
        Args:
            skills: skill JSON 列表
            show_progress: 是否顯示進度條
            
        Returns:
            List[np.ndarray]: 向量列表
        """
        texts = [self.skill_to_text(s) for s in skills]
        embeddings = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=show_progress)
        return [e.astype(np.float32) for e in embeddings]
    
    def embed_query(self, query: str) -> np.ndarray:
        """
        將搜尋查詢轉換為向量
        
        Args:
            query: 自然語言查詢
            
        Returns:
            np.ndarray: 384 維向量
        """
        embedding = self.model.encode(query, convert_to_numpy=True)
        return embedding.astype(np.float32)
    
    def load_skills_from_dir(self, parsed_dir: Union[str, Path]) -> List[Dict]:
        """
        從目錄載入所有 skill JSON
        
        Args:
            parsed_dir: parsed/ 目錄路徑
            
        Returns:
            List[Dict]: skill 字典列表 (含 _filename 欄位)
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
    # 測試
    embedder = SkillEmbedder()
    print(f"Model dimension: {embedder.dimension}")
    
    # 測試查詢嵌入
    query = "PDF document processing and manipulation"
    vec = embedder.embed_query(query)
    print(f"Query vector shape: {vec.shape}")
    print(f"Query vector sample: {vec[:5]}")
