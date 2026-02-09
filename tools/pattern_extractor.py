#!/usr/bin/env python3
"""
Skill-0 模式提取工具
從多個 skills 中歸納共通模式，建立模式庫
"""

import json
import re
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Any, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Pattern:
    """歸納出的模式"""
    id: str
    name: str
    description: str
    pattern_type: str  # action_sequence, rule_group, structure
    structure: Dict[str, Any] = field(default_factory=dict)
    found_in: List[str] = field(default_factory=list)
    frequency: float = 0.0
    examples: List[Dict] = field(default_factory=list)


class PatternExtractor:
    """模式提取器"""
    
    def __init__(self, parsed_dir: str):
        self.parsed_dir = Path(parsed_dir)
        self.skills: List[Dict] = []
        self.patterns: List[Pattern] = []
        
    def load_skills(self) -> int:
        """載入所有已解析的 skills"""
        self.skills = []
        
        for json_file in self.parsed_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    skill_data = json.load(f)
                    skill_data['_source_file'] = json_file.stem
                    self.skills.append(skill_data)
            except Exception as e:
                print(f"⚠️ 載入失敗 {json_file.name}: {e}")
                
        return len(self.skills)
    
    def extract_all_patterns(self) -> List[Pattern]:
        """提取所有類型的模式"""
        self.patterns = []
        
        # 1. 提取動作類型模式
        self._extract_action_type_patterns()
        
        # 2. 提取 directive 類型模式
        self._extract_directive_patterns()
        
        # 3. 提取結構模式 (action-rule 組合)
        self._extract_structure_patterns()
        
        # 4. 提取描述文字模式 (關鍵字)
        self._extract_keyword_patterns()
        
        return self.patterns
    
    def _extract_action_type_patterns(self):
        """提取常見的 action 類型組合"""
        # 收集每個 skill 的 action_type 集合
        skill_action_sets: Dict[str, Set[str]] = {}
        
        for skill in self.skills:
            meta = skill.get('meta', {})
            skill_id = meta.get('skill_id', skill.get('skill_id', skill.get('_source_file')))
            action_types = set()
            
            # 支援 v2.0 schema 結構
            decomposition = skill.get('decomposition', {})
            actions = decomposition.get('actions', [])
            
            # 也支援舊的 elements 格式
            if not actions:
                actions = [e for e in skill.get('elements', []) if e.get('type') == 'action']
            
            for elem in actions:
                action_types.add(elem.get('action_type', 'unknown'))
            
            if action_types:
                skill_action_sets[skill_id] = action_types
        
        # 找出共通的 action 組合
        if len(skill_action_sets) < 2:
            return
            
        # 計算每對 action_type 的共現頻率
        cooccurrence = Counter()
        for skill_id, actions in skill_action_sets.items():
            action_list = sorted(actions)
            for i, a1 in enumerate(action_list):
                for a2 in action_list[i+1:]:
                    cooccurrence[(a1, a2)] += 1
        
        # 建立模式
        for (a1, a2), count in cooccurrence.most_common(10):
            if count >= 2:  # 至少出現在 2 個 skills
                found_skills = [
                    sid for sid, actions in skill_action_sets.items()
                    if a1 in actions and a2 in actions
                ]
                
                pattern = Pattern(
                    id=f"pat_act_{a1}_{a2}",
                    name=f"{a1} + {a2} 組合",
                    description=f"同時包含 {a1} 和 {a2} 類型的動作",
                    pattern_type="action_combination",
                    structure={"action_types": [a1, a2]},
                    found_in=found_skills,
                    frequency=count / len(skill_action_sets)
                )
                self.patterns.append(pattern)
    
    def _extract_directive_patterns(self):
        """提取 directive 使用模式"""
        directive_by_type = defaultdict(list)
        
        for skill in self.skills:
            meta = skill.get('meta', {})
            skill_id = meta.get('skill_id', skill.get('skill_id', skill.get('_source_file')))
            
            # 支援 v2.0 schema 結構
            decomposition = skill.get('decomposition', {})
            directives = decomposition.get('directives', [])
            
            # 也支援舊的 elements 格式
            if not directives:
                directives = [e for e in skill.get('elements', []) if e.get('type') == 'directive']
            
            for elem in directives:
                dtype = elem.get('directive_type', 'unknown')
                directive_by_type[dtype].append({
                    'skill': skill_id,
                    'description': elem.get('description', '')[:100]
                })
        
        # 為每種常見的 directive 類型建立模式
        for dtype, items in directive_by_type.items():
            if len(items) >= 1:
                pattern = Pattern(
                    id=f"pat_dir_{dtype}",
                    name=f"Directive: {dtype}",
                    description=f"使用 {dtype} 類型的 directive",
                    pattern_type="directive_usage",
                    structure={"directive_type": dtype},
                    found_in=list(set(item['skill'] for item in items)),
                    frequency=len(items) / len(self.skills) if self.skills else 0,
                    examples=items[:3]
                )
                self.patterns.append(pattern)
    
    def _extract_structure_patterns(self):
        """提取結構模式 (元素組合)"""
        # 分析每個 skill 的元素比例
        structures = []
        
        for skill in self.skills:
            meta = skill.get('meta', {})
            skill_id = meta.get('skill_id', skill.get('skill_id', skill.get('_source_file')))
            
            # 支援 v2.0 schema 結構
            decomposition = skill.get('decomposition', {})
            elements = (
                decomposition.get('actions', []) + 
                decomposition.get('rules', []) + 
                decomposition.get('directives', [])
            )
            
            # 也支援舊的 elements 格式
            if not elements:
                elements = skill.get('elements', [])
            
            # 為元素添加 type 標記 (v2.0 格式中需要根據來源判斷)
            counts = Counter()
            for e in decomposition.get('actions', []):
                counts['action'] += 1
            for e in decomposition.get('rules', []):
                counts['rule'] += 1
            for e in decomposition.get('directives', []):
                counts['directive'] += 1
            
            # 舊格式
            if not counts:
                counts = Counter(e.get('type') for e in elements)
            
            total = sum(counts.values())
            
            if total > 0:
                structure = {
                    'skill': skill_id,
                    'action_ratio': counts.get('action', 0) / total,
                    'rule_ratio': counts.get('rule', 0) / total,
                    'directive_ratio': counts.get('directive', 0) / total,
                    'total': total
                }
                structures.append(structure)
        
        # 識別結構類型
        action_heavy = [s for s in structures if s['action_ratio'] > 0.6]
        rule_heavy = [s for s in structures if s['rule_ratio'] > 0.4]
        balanced = [s for s in structures if 0.2 <= s['action_ratio'] <= 0.5 
                   and 0.2 <= s['rule_ratio'] <= 0.5]
        
        if action_heavy:
            self.patterns.append(Pattern(
                id="pat_struct_action_heavy",
                name="動作導向結構",
                description="以 action 為主的 skill，動作佔比超過 60%",
                pattern_type="structure",
                structure={"dominant": "action", "ratio_threshold": 0.6},
                found_in=[s['skill'] for s in action_heavy],
                frequency=len(action_heavy) / len(structures) if structures else 0
            ))
        
        if rule_heavy:
            self.patterns.append(Pattern(
                id="pat_struct_rule_heavy",
                name="規則導向結構",
                description="以 rule 為主的 skill，規則佔比超過 40%",
                pattern_type="structure",
                structure={"dominant": "rule", "ratio_threshold": 0.4},
                found_in=[s['skill'] for s in rule_heavy],
                frequency=len(rule_heavy) / len(structures) if structures else 0
            ))
        
        if balanced:
            self.patterns.append(Pattern(
                id="pat_struct_balanced",
                name="平衡結構",
                description="action 和 rule 比例平衡的 skill",
                pattern_type="structure",
                structure={"type": "balanced"},
                found_in=[s['skill'] for s in balanced],
                frequency=len(balanced) / len(structures) if structures else 0
            ))
    
    def _extract_keyword_patterns(self):
        """從描述文字提取關鍵字模式"""
        # 常見動作關鍵字
        action_keywords = [
            ('file_operation', ['讀取', '寫入', '建立', '刪除', 'read', 'write', 'create', 'delete']),
            ('validation', ['驗證', '檢查', '確認', 'validate', 'check', 'verify']),
            ('transformation', ['轉換', '處理', '解析', 'convert', 'transform', 'parse']),
            ('output', ['輸出', '產生', '顯示', 'output', 'generate', 'display']),
        ]
        
        keyword_matches = defaultdict(list)
        
        for skill in self.skills:
            meta = skill.get('meta', {})
            skill_id = meta.get('skill_id', skill.get('skill_id', skill.get('_source_file')))
            
            # 收集所有描述文字
            all_text = ""
            
            # 支援 v2.0 schema 結構
            decomposition = skill.get('decomposition', {})
            for elem in decomposition.get('actions', []):
                all_text += elem.get('description', '') + " "
            for elem in decomposition.get('rules', []):
                all_text += elem.get('description', '') + " "
            for elem in decomposition.get('directives', []):
                all_text += elem.get('description', '') + " "
            
            # 也支援舊的 elements 格式
            for elem in skill.get('elements', []):
                all_text += elem.get('description', '') + " "
            
            all_text = all_text.lower()
            
            # 檢查關鍵字
            for category, keywords in action_keywords:
                for kw in keywords:
                    if kw.lower() in all_text:
                        keyword_matches[category].append(skill_id)
                        break
        
        # 建立關鍵字模式
        for category, skills in keyword_matches.items():
            unique_skills = list(set(skills))
            if unique_skills:
                self.patterns.append(Pattern(
                    id=f"pat_kw_{category}",
                    name=f"關鍵字模式: {category}",
                    description=f"包含 {category} 相關操作的 skill",
                    pattern_type="keyword",
                    structure={"category": category},
                    found_in=unique_skills,
                    frequency=len(unique_skills) / len(self.skills) if self.skills else 0
                ))
    
    def save_patterns(self, output_path: str):
        """儲存模式庫"""
        patterns_dict = {
            "version": "1.0",
            "generated_at": datetime.now().isoformat(),
            "total_patterns": len(self.patterns),
            "source_skills_count": len(self.skills),
            "patterns": []
        }
        
        for p in self.patterns:
            patterns_dict["patterns"].append({
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "pattern_type": p.pattern_type,
                "structure": p.structure,
                "found_in": p.found_in,
                "frequency": round(p.frequency, 3),
                "examples": p.examples[:3] if p.examples else []
            })
        
        # 依頻率排序
        patterns_dict["patterns"].sort(key=lambda x: -x["frequency"])
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(patterns_dict, f, ensure_ascii=False, indent=2)
    
    def generate_report(self) -> str:
        """產生模式報告"""
        lines = [
            "=" * 60,
            "🔍 Skill-0 模式提取報告",
            "=" * 60,
            f"分析 Skills 數量: {len(self.skills)}",
            f"提取模式數量: {len(self.patterns)}",
            "",
        ]
        
        # 按類型分組
        by_type = defaultdict(list)
        for p in self.patterns:
            by_type[p.pattern_type].append(p)
        
        for ptype, patterns in by_type.items():
            lines.append(f"📁 {ptype.upper()} 模式 ({len(patterns)} 個)")
            lines.append("-" * 40)
            
            for p in sorted(patterns, key=lambda x: -x.frequency):
                freq_pct = f"{p.frequency * 100:.0f}%"
                lines.append(f"  [{p.id}] {p.name}")
                lines.append(f"    {p.description}")
                lines.append(f"    出現頻率: {freq_pct}, 涵蓋: {', '.join(p.found_in[:3])}{'...' if len(p.found_in) > 3 else ''}")
                lines.append("")
        
        lines.append("=" * 60)
        return "\n".join(lines)


def main():
    """主程式"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Skill-0 模式提取工具')
    parser.add_argument('--parsed-dir', '-p', default='parsed',
                        help='已解析 skills 的目錄 (預設: parsed)')
    parser.add_argument('--output', '-o', default='analysis/patterns.json',
                        help='輸出模式庫路徑 (預設: analysis/patterns.json)')
    
    args = parser.parse_args()
    
    extractor = PatternExtractor(args.parsed_dir)
    
    print(f"📂 載入 skills 從: {args.parsed_dir}")
    count = extractor.load_skills()
    print(f"✓ 載入 {count} 個 skills")
    
    print("🔍 提取模式...")
    extractor.extract_all_patterns()
    print(f"✓ 提取 {len(extractor.patterns)} 個模式")
    
    extractor.save_patterns(args.output)
    print(f"✓ 模式庫已儲存: {args.output}")
    
    print("\n" + extractor.generate_report())


if __name__ == '__main__':
    main()
