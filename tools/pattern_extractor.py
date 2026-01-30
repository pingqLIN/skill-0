#!/usr/bin/env python3
"""
Skill-0 Pattern Extraction Tool
Extracts common patterns from multiple skills and builds a pattern library
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
    """Extracted pattern"""
    id: str
    name: str
    description: str
    pattern_type: str  # action_sequence, rule_group, structure
    structure: Dict[str, Any] = field(default_factory=dict)
    found_in: List[str] = field(default_factory=list)
    frequency: float = 0.0
    examples: List[Dict] = field(default_factory=list)


class PatternExtractor:
    """Pattern extractor"""
    
    def __init__(self, parsed_dir: str):
        self.parsed_dir = Path(parsed_dir)
        self.skills: List[Dict] = []
        self.patterns: List[Pattern] = []
        
    def load_skills(self) -> int:
        """Load all parsed skills"""
        self.skills = []
        
        for json_file in self.parsed_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    skill_data = json.load(f)
                    skill_data['_source_file'] = json_file.stem
                    self.skills.append(skill_data)
            except Exception as e:
                print(f"⚠️ Failed to load {json_file.name}: {e}")
                
        return len(self.skills)
    
    def extract_all_patterns(self) -> List[Pattern]:
        """Extract all pattern types"""
        self.patterns = []
        
        # 1. Extract action type patterns
        self._extract_action_type_patterns()
        
        # 2. Extract directive type patterns
        self._extract_directive_patterns()
        
        # 3. Extract structure patterns (action-rule combinations)
        self._extract_structure_patterns()
        
        # 4. Extract description text patterns (keywords)
        self._extract_keyword_patterns()
        
        return self.patterns
    
    def _extract_action_type_patterns(self):
        """Extract common action type combinations"""
        # Collect action_type sets for each skill
        skill_action_sets: Dict[str, Set[str]] = {}
        
        for skill in self.skills:
            meta = skill.get('meta', {})
            skill_id = meta.get('skill_id', skill.get('skill_id', skill.get('_source_file')))
            action_types = set()
            
            # Support v2.0 schema structure
            decomposition = skill.get('decomposition', {})
            actions = decomposition.get('actions', [])
            
            # Also support legacy elements format
            if not actions:
                actions = [e for e in skill.get('elements', []) if e.get('type') == 'action']
            
            for elem in actions:
                action_types.add(elem.get('action_type', 'unknown'))
            
            if action_types:
                skill_action_sets[skill_id] = action_types
        
        # Find common action combinations
        if len(skill_action_sets) < 2:
            return
            
        # Calculate co-occurrence frequency for each action_type pair
        cooccurrence = Counter()
        for skill_id, actions in skill_action_sets.items():
            action_list = sorted(actions)
            for i, a1 in enumerate(action_list):
                for a2 in action_list[i+1:]:
                    cooccurrence[(a1, a2)] += 1
        
        # Build patterns
        for (a1, a2), count in cooccurrence.most_common(10):
            if count >= 2:  # Appears in at least 2 skills
                found_skills = [
                    sid for sid, actions in skill_action_sets.items()
                    if a1 in actions and a2 in actions
                ]
                
                pattern = Pattern(
                    id=f"pat_act_{a1}_{a2}",
                    name=f"{a1} + {a2} combination",
                    description=f"Contains both {a1} and {a2} action types",
                    pattern_type="action_combination",
                    structure={"action_types": [a1, a2]},
                    found_in=found_skills,
                    frequency=count / len(skill_action_sets)
                )
                self.patterns.append(pattern)
    
    def _extract_directive_patterns(self):
        """Extract directive usage patterns"""
        directive_by_type = defaultdict(list)
        
        for skill in self.skills:
            meta = skill.get('meta', {})
            skill_id = meta.get('skill_id', skill.get('skill_id', skill.get('_source_file')))
            
            # Support v2.0 schema structure
            decomposition = skill.get('decomposition', {})
            directives = decomposition.get('directives', [])
            
            # Also support legacy elements format
            if not directives:
                directives = [e for e in skill.get('elements', []) if e.get('type') == 'directive']
            
            for elem in directives:
                dtype = elem.get('directive_type', 'unknown')
                directive_by_type[dtype].append({
                    'skill': skill_id,
                    'description': elem.get('description', '')[:100]
                })
        
        # Create patterns for each common directive type
        for dtype, items in directive_by_type.items():
            if len(items) >= 1:
                pattern = Pattern(
                    id=f"pat_dir_{dtype}",
                    name=f"Directive: {dtype}",
                    description=f"Uses {dtype} type directive",
                    pattern_type="directive_usage",
                    structure={"directive_type": dtype},
                    found_in=list(set(item['skill'] for item in items)),
                    frequency=len(items) / len(self.skills) if self.skills else 0,
                    examples=items[:3]
                )
                self.patterns.append(pattern)
    
    def _extract_structure_patterns(self):
        """Extract structure patterns (element combinations)"""
        # Analyze element ratios for each skill
        structures = []
        
        for skill in self.skills:
            meta = skill.get('meta', {})
            skill_id = meta.get('skill_id', skill.get('skill_id', skill.get('_source_file')))
            
            # Support v2.0 schema structure
            decomposition = skill.get('decomposition', {})
            elements = (
                decomposition.get('actions', []) + 
                decomposition.get('rules', []) + 
                decomposition.get('directives', [])
            )
            
            # Also support legacy elements format
            if not elements:
                elements = skill.get('elements', [])
            
            # Add type tags to elements (v2.0 format requires type determination from source)
            counts = Counter()
            for e in decomposition.get('actions', []):
                counts['action'] += 1
            for e in decomposition.get('rules', []):
                counts['rule'] += 1
            for e in decomposition.get('directives', []):
                counts['directive'] += 1
            
            # Legacy format
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
        
        # Identify structure types
        action_heavy = [s for s in structures if s['action_ratio'] > 0.6]
        rule_heavy = [s for s in structures if s['rule_ratio'] > 0.4]
        balanced = [s for s in structures if 0.2 <= s['action_ratio'] <= 0.5 
                   and 0.2 <= s['rule_ratio'] <= 0.5]
        
        if action_heavy:
            self.patterns.append(Pattern(
                id="pat_struct_action_heavy",
                name="Action-oriented structure",
                description="Action-dominant skill with actions exceeding 60%",
                pattern_type="structure",
                structure={"dominant": "action", "ratio_threshold": 0.6},
                found_in=[s['skill'] for s in action_heavy],
                frequency=len(action_heavy) / len(structures) if structures else 0
            ))
        
        if rule_heavy:
            self.patterns.append(Pattern(
                id="pat_struct_rule_heavy",
                name="Rule-oriented structure",
                description="Rule-dominant skill with rules exceeding 40%",
                pattern_type="structure",
                structure={"dominant": "rule", "ratio_threshold": 0.4},
                found_in=[s['skill'] for s in rule_heavy],
                frequency=len(rule_heavy) / len(structures) if structures else 0
            ))
        
        if balanced:
            self.patterns.append(Pattern(
                id="pat_struct_balanced",
                name="Balanced structure",
                description="Skill with balanced action and rule ratios",
                pattern_type="structure",
                structure={"type": "balanced"},
                found_in=[s['skill'] for s in balanced],
                frequency=len(balanced) / len(structures) if structures else 0
            ))
    
    def _extract_keyword_patterns(self):
        """Extract keyword patterns from description text"""
        # Common action keywords
        action_keywords = [
            ('file_operation', ['read', 'write', 'create', 'delete', 'load', 'save']),
            ('validation', ['validate', 'check', 'verify', 'confirm', 'test']),
            ('transformation', ['convert', 'transform', 'parse', 'process', 'format']),
            ('output', ['output', 'generate', 'display', 'render', 'produce']),
        ]
        
        keyword_matches = defaultdict(list)
        
        for skill in self.skills:
            meta = skill.get('meta', {})
            skill_id = meta.get('skill_id', skill.get('skill_id', skill.get('_source_file')))
            
            # Collect all description text
            all_text = ""
            
            # Support v2.0 schema structure
            decomposition = skill.get('decomposition', {})
            for elem in decomposition.get('actions', []):
                all_text += elem.get('description', '') + " "
            for elem in decomposition.get('rules', []):
                all_text += elem.get('description', '') + " "
            for elem in decomposition.get('directives', []):
                all_text += elem.get('description', '') + " "
            
            # Also support legacy elements format
            for elem in skill.get('elements', []):
                all_text += elem.get('description', '') + " "
            
            all_text = all_text.lower()
            
            # Check keywords
            for category, keywords in action_keywords:
                for kw in keywords:
                    if kw.lower() in all_text:
                        keyword_matches[category].append(skill_id)
                        break
        
        # Build keyword patterns
        for category, skills in keyword_matches.items():
            unique_skills = list(set(skills))
            if unique_skills:
                self.patterns.append(Pattern(
                    id=f"pat_kw_{category}",
                    name=f"Keyword pattern: {category}",
                    description=f"Skills containing {category}-related operations",
                    pattern_type="keyword",
                    structure={"category": category},
                    found_in=unique_skills,
                    frequency=len(unique_skills) / len(self.skills) if self.skills else 0
                ))
    
    def save_patterns(self, output_path: str):
        """Save pattern library"""
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
        
        # Sort by frequency
        patterns_dict["patterns"].sort(key=lambda x: -x["frequency"])
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(patterns_dict, f, ensure_ascii=False, indent=2)
    
    def generate_report(self) -> str:
        """Generate pattern report"""
        lines = [
            "=" * 60,
            "🔍 Skill-0 Pattern Extraction Report",
            "=" * 60,
            f"Skills analyzed: {len(self.skills)}",
            f"Patterns extracted: {len(self.patterns)}",
            "",
        ]
        
        # Group by type
        by_type = defaultdict(list)
        for p in self.patterns:
            by_type[p.pattern_type].append(p)
        
        for ptype, patterns in by_type.items():
            lines.append(f"📁 {ptype.upper()} patterns ({len(patterns)} total)")
            lines.append("-" * 40)
            
            for p in sorted(patterns, key=lambda x: -x.frequency):
                freq_pct = f"{p.frequency * 100:.0f}%"
                lines.append(f"  [{p.id}] {p.name}")
                lines.append(f"    {p.description}")
                lines.append(f"    Frequency: {freq_pct}, Found in: {', '.join(p.found_in[:3])}{'...' if len(p.found_in) > 3 else ''}")
                lines.append("")
        
        lines.append("=" * 60)
        return "\n".join(lines)


def main():
    """Main program"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Skill-0 Pattern Extraction Tool')
    parser.add_argument('--parsed-dir', '-p', default='parsed',
                        help='Directory of parsed skills (default: parsed)')
    parser.add_argument('--output', '-o', default='analysis/patterns.json',
                        help='Output pattern library path (default: analysis/patterns.json)')
    
    args = parser.parse_args()
    
    extractor = PatternExtractor(args.parsed_dir)
    
    print(f"📂 Loading skills from: {args.parsed_dir}")
    count = extractor.load_skills()
    print(f"✓ Loaded {count} skills")
    
    print("🔍 Extracting patterns...")
    extractor.extract_all_patterns()
    print(f"✓ Extracted {len(extractor.patterns)} patterns")
    
    extractor.save_patterns(args.output)
    print(f"✓ Pattern library saved: {args.output}")
    
    print("\n" + extractor.generate_report())


if __name__ == '__main__':
    main()
