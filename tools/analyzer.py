#!/usr/bin/env python3
"""
Skill-0 Structure Analysis Tool
Analyzes parsed skills and generates statistical reports with pattern recognition
"""

import json
import os
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class ElementStats:
    """Statistics for a single element type"""
    total_count: int = 0
    type_distribution: Dict[str, int] = field(default_factory=dict)
    common_patterns: List[str] = field(default_factory=list)


@dataclass 
class SkillSummary:
    """Summary of a single skill"""
    skill_id: str
    name: str
    source_file: str
    action_count: int = 0
    rule_count: int = 0
    directive_count: int = 0
    action_types: List[str] = field(default_factory=list)
    directive_types: List[str] = field(default_factory=list)
    has_flow: bool = False
    

@dataclass
class AnalysisReport:
    """Complete analysis report"""
    version: str = "1.0"
    generated_at: str = ""
    total_skills: int = 0
    skills: List[SkillSummary] = field(default_factory=list)
    
    # Global statistics
    action_stats: ElementStats = field(default_factory=ElementStats)
    rule_stats: ElementStats = field(default_factory=ElementStats)
    directive_stats: ElementStats = field(default_factory=ElementStats)
    
    # Pattern analysis
    common_action_sequences: List[Dict] = field(default_factory=list)
    common_rule_patterns: List[Dict] = field(default_factory=list)


class SkillAnalyzer:
    """Skill structure analyzer"""
    
    def __init__(self, parsed_dir: str):
        self.parsed_dir = Path(parsed_dir)
        self.skills: List[Dict] = []
        self.report = AnalysisReport()
        
    def load_skills(self) -> int:
        """Load all parsed skills"""
        self.skills = []
        
        for json_file in self.parsed_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    skill_data = json.load(f)
                    skill_data['_source_file'] = json_file.name
                    self.skills.append(skill_data)
            except Exception as e:
                print(f"⚠️ Failed to load {json_file.name}: {e}")
                
        return len(self.skills)
    
    def analyze(self) -> AnalysisReport:
        """Execute complete analysis"""
        self.report = AnalysisReport(
            generated_at=datetime.now().isoformat(),
            total_skills=len(self.skills)
        )
        
        # Collectors
        all_action_types = Counter()
        all_directive_types = Counter()
        all_rule_conditions = []
        action_sequences = []
        
        for skill in self.skills:
            summary = self._analyze_skill(skill)
            self.report.skills.append(summary)
            
            # Accumulate statistics
            all_action_types.update(summary.action_types)
            all_directive_types.update(summary.directive_types)
            
            # Extract execution sequences
            if 'execution_flow' in skill:
                seq = self._extract_sequence(skill['execution_flow'])
                if seq:
                    action_sequences.append(seq)
        
        # Aggregate global statistics
        self.report.action_stats = ElementStats(
            total_count=sum(s.action_count for s in self.report.skills),
            type_distribution=dict(all_action_types)
        )
        
        self.report.rule_stats = ElementStats(
            total_count=sum(s.rule_count for s in self.report.skills)
        )
        
        self.report.directive_stats = ElementStats(
            total_count=sum(s.directive_count for s in self.report.skills),
            type_distribution=dict(all_directive_types)
        )
        
        # Analyze common patterns
        self.report.common_action_sequences = self._find_common_sequences(action_sequences)
        
        return self.report
    
    def _analyze_skill(self, skill: Dict) -> SkillSummary:
        """Analyze a single skill"""
        # Support v2.0 schema structure (decomposition.actions/rules/directives)
        decomposition = skill.get('decomposition', {})
        meta = skill.get('meta', {})
        
        actions = decomposition.get('actions', [])
        rules = decomposition.get('rules', [])
        directives = decomposition.get('directives', [])
        
        # Also support legacy elements array format
        if not actions and not rules and not directives:
            elements = skill.get('elements', [])
            actions = [e for e in elements if e.get('type') == 'action']
            rules = [e for e in elements if e.get('type') == 'rule']
            directives = [e for e in elements if e.get('type') == 'directive']
        
        return SkillSummary(
            skill_id=meta.get('skill_id', skill.get('skill_id', 'unknown')),
            name=meta.get('name', skill.get('skill_name', 'Unknown')),
            source_file=skill.get('_source_file', ''),
            action_count=len(actions),
            rule_count=len(rules),
            directive_count=len(directives),
            action_types=[a.get('action_type', 'unknown') for a in actions],
            directive_types=[d.get('directive_type', 'unknown') for d in directives],
            has_flow='execution_flow' in decomposition or 'execution_flow' in skill
        )
    
    def _extract_sequence(self, flow: Dict) -> Optional[List[str]]:
        """Extract action sequence from execution flow"""
        sequence = []
        
        def traverse(node):
            if isinstance(node, dict):
                if 'step' in node:
                    # Extract element type from step
                    elem_id = node.get('element_ref', '')
                    if elem_id.startswith('a_'):
                        sequence.append('action')
                    elif elem_id.startswith('r_'):
                        sequence.append('rule')
                    elif elem_id.startswith('d_'):
                        sequence.append('directive')
                        
                # Recursively process child nodes
                for key in ['then', 'next', 'on_true', 'on_false', 'steps']:
                    if key in node:
                        traverse(node[key])
                        
            elif isinstance(node, list):
                for item in node:
                    traverse(item)
        
        traverse(flow)
        return sequence if sequence else None
    
    def _find_common_sequences(self, sequences: List[List[str]]) -> List[Dict]:
        """Find common action sequence patterns"""
        # Convert to strings for counting
        seq_strings = ['->'.join(s) for s in sequences]
        counter = Counter(seq_strings)
        
        return [
            {"pattern": seq, "count": count}
            for seq, count in counter.most_common(10)
            if count > 1
        ]
    
    def generate_report_text(self) -> str:
        """Generate human-readable report"""
        r = self.report
        lines = [
            "=" * 60,
            "📊 Skill-0 Structure Analysis Report",
            "=" * 60,
            f"Generated at: {r.generated_at}",
            f"Skills analyzed: {r.total_skills}",
            "",
            "📈 Element Statistics",
            "-" * 40,
            f"  Total Actions: {r.action_stats.total_count}",
            f"  Total Rules: {r.rule_stats.total_count}",
            f"  Total Directives: {r.directive_stats.total_count}",
            "",
        ]
        
        # Action type distribution
        if r.action_stats.type_distribution:
            lines.append("🎬 Action Type Distribution:")
            for atype, count in sorted(r.action_stats.type_distribution.items(), 
                                       key=lambda x: -x[1]):
                lines.append(f"  - {atype}: {count}")
            lines.append("")
        
        # Directive type distribution
        if r.directive_stats.type_distribution:
            lines.append("📌 Directive Type Distribution:")
            for dtype, count in sorted(r.directive_stats.type_distribution.items(),
                                       key=lambda x: -x[1]):
                lines.append(f"  - {dtype}: {count}")
            lines.append("")
        
        # Per-skill summary
        lines.append("📋 Per-Skill Summary")
        lines.append("-" * 40)
        for s in r.skills:
            lines.append(f"  [{s.skill_id}] {s.name}")
            lines.append(f"    Actions: {s.action_count}, Rules: {s.rule_count}, Directives: {s.directive_count}")
            lines.append(f"    Has execution flow: {'✓' if s.has_flow else '✗'}")
            lines.append("")
        
        # Common patterns
        if r.common_action_sequences:
            lines.append("🔄 Common Execution Sequence Patterns")
            lines.append("-" * 40)
            for p in r.common_action_sequences:
                lines.append(f"  {p['pattern']} (appears {p['count']} times)")
            lines.append("")
        
        lines.append("=" * 60)
        return "\n".join(lines)
    
    def save_report(self, output_path: str):
        """Save JSON report"""
        # Convert dataclass to dict
        report_dict = {
            "version": self.report.version,
            "generated_at": self.report.generated_at,
            "total_skills": self.report.total_skills,
            "summary": {
                "action_count": self.report.action_stats.total_count,
                "rule_count": self.report.rule_stats.total_count,
                "directive_count": self.report.directive_stats.total_count,
            },
            "action_type_distribution": self.report.action_stats.type_distribution,
            "directive_type_distribution": self.report.directive_stats.type_distribution,
            "skills": [asdict(s) for s in self.report.skills],
            "common_patterns": {
                "action_sequences": self.report.common_action_sequences
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, ensure_ascii=False, indent=2)


def main():
    """Main program"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Skill-0 Structure Analysis Tool')
    parser.add_argument('--parsed-dir', '-p', default='parsed',
                        help='Directory of parsed skills (default: parsed)')
    parser.add_argument('--output', '-o', default='analysis/report.json',
                        help='Output report path (default: analysis/report.json)')
    parser.add_argument('--text', '-t', action='store_true',
                        help='Also output text report')
    
    args = parser.parse_args()
    
    # Ensure output directory exists
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Execute analysis
    analyzer = SkillAnalyzer(args.parsed_dir)
    
    print(f"📂 Loading skills from: {args.parsed_dir}")
    count = analyzer.load_skills()
    print(f"✓ Loaded {count} skills")
    
    print("🔍 Executing analysis...")
    analyzer.analyze()
    
    # Output
    analyzer.save_report(args.output)
    print(f"✓ JSON report saved: {args.output}")
    
    if args.text:
        text_report = analyzer.generate_report_text()
        text_path = output_path.with_suffix('.txt')
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write(text_report)
        print(f"✓ Text report saved: {text_path}")
    
    # Display summary
    print("\n" + analyzer.generate_report_text())


if __name__ == '__main__':
    main()
