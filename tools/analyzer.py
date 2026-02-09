#!/usr/bin/env python3
"""
Skill-0 結構分析工具
分析已解析的 skills，產生統計報告與模式識別
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
    """單一元素類型的統計"""
    total_count: int = 0
    type_distribution: Dict[str, int] = field(default_factory=dict)
    common_patterns: List[str] = field(default_factory=list)


@dataclass 
class SkillSummary:
    """單一 Skill 的摘要"""
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
    """完整分析報告"""
    version: str = "1.0"
    generated_at: str = ""
    total_skills: int = 0
    skills: List[SkillSummary] = field(default_factory=list)
    
    # 全域統計
    action_stats: ElementStats = field(default_factory=ElementStats)
    rule_stats: ElementStats = field(default_factory=ElementStats)
    directive_stats: ElementStats = field(default_factory=ElementStats)
    
    # 模式分析
    common_action_sequences: List[Dict] = field(default_factory=list)
    common_rule_patterns: List[Dict] = field(default_factory=list)


class SkillAnalyzer:
    """Skill 結構分析器"""
    
    def __init__(self, parsed_dir: str):
        self.parsed_dir = Path(parsed_dir)
        self.skills: List[Dict] = []
        self.report = AnalysisReport()
        
    def load_skills(self) -> int:
        """載入所有已解析的 skills"""
        self.skills = []
        
        for json_file in self.parsed_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    skill_data = json.load(f)
                    skill_data['_source_file'] = json_file.name
                    self.skills.append(skill_data)
            except Exception as e:
                print(f"⚠️ 載入失敗 {json_file.name}: {e}")
                
        return len(self.skills)
    
    def analyze(self) -> AnalysisReport:
        """執行完整分析"""
        self.report = AnalysisReport(
            generated_at=datetime.now().isoformat(),
            total_skills=len(self.skills)
        )
        
        # 收集器
        all_action_types = Counter()
        all_directive_types = Counter()
        all_rule_conditions = []
        action_sequences = []
        
        for skill in self.skills:
            summary = self._analyze_skill(skill)
            self.report.skills.append(summary)
            
            # 累計統計
            all_action_types.update(summary.action_types)
            all_directive_types.update(summary.directive_types)
            
            # 提取執行序列
            if 'execution_flow' in skill:
                seq = self._extract_sequence(skill['execution_flow'])
                if seq:
                    action_sequences.append(seq)
        
        # 彙整全域統計
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
        
        # 分析常見模式
        self.report.common_action_sequences = self._find_common_sequences(action_sequences)
        
        return self.report
    
    def _analyze_skill(self, skill: Dict) -> SkillSummary:
        """分析單一 skill"""
        # 支援 v2.0 schema 結構 (decomposition.actions/rules/directives)
        decomposition = skill.get('decomposition', {})
        meta = skill.get('meta', {})
        
        actions = decomposition.get('actions', [])
        rules = decomposition.get('rules', [])
        directives = decomposition.get('directives', [])
        
        # 也支援舊的 elements 陣列格式
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
        """從執行流程提取動作序列"""
        sequence = []
        
        def traverse(node):
            if isinstance(node, dict):
                if 'step' in node:
                    # 提取 step 的元素類型
                    elem_id = node.get('element_ref', '')
                    if elem_id.startswith('a_'):
                        sequence.append('action')
                    elif elem_id.startswith('r_'):
                        sequence.append('rule')
                    elif elem_id.startswith('d_'):
                        sequence.append('directive')
                        
                # 遞迴處理子節點
                for key in ['then', 'next', 'on_true', 'on_false', 'steps']:
                    if key in node:
                        traverse(node[key])
                        
            elif isinstance(node, list):
                for item in node:
                    traverse(item)
        
        traverse(flow)
        return sequence if sequence else None
    
    def _find_common_sequences(self, sequences: List[List[str]]) -> List[Dict]:
        """找出常見的動作序列模式"""
        # 轉換為字串以便計數
        seq_strings = ['->'.join(s) for s in sequences]
        counter = Counter(seq_strings)
        
        return [
            {"pattern": seq, "count": count}
            for seq, count in counter.most_common(10)
            if count > 1
        ]
    
    def generate_report_text(self) -> str:
        """產生人類可讀的報告"""
        r = self.report
        lines = [
            "=" * 60,
            "📊 Skill-0 結構分析報告",
            "=" * 60,
            f"產生時間: {r.generated_at}",
            f"分析 Skills 數量: {r.total_skills}",
            "",
            "📈 元素統計",
            "-" * 40,
            f"  Action 總數: {r.action_stats.total_count}",
            f"  Rule 總數: {r.rule_stats.total_count}",
            f"  Directive 總數: {r.directive_stats.total_count}",
            "",
        ]
        
        # Action 類型分布
        if r.action_stats.type_distribution:
            lines.append("🎬 Action 類型分布:")
            for atype, count in sorted(r.action_stats.type_distribution.items(), 
                                       key=lambda x: -x[1]):
                lines.append(f"  - {atype}: {count}")
            lines.append("")
        
        # Directive 類型分布
        if r.directive_stats.type_distribution:
            lines.append("📌 Directive 類型分布:")
            for dtype, count in sorted(r.directive_stats.type_distribution.items(),
                                       key=lambda x: -x[1]):
                lines.append(f"  - {dtype}: {count}")
            lines.append("")
        
        # 各 Skill 摘要
        lines.append("📋 各 Skill 摘要")
        lines.append("-" * 40)
        for s in r.skills:
            lines.append(f"  [{s.skill_id}] {s.name}")
            lines.append(f"    Actions: {s.action_count}, Rules: {s.rule_count}, Directives: {s.directive_count}")
            lines.append(f"    有執行流程: {'✓' if s.has_flow else '✗'}")
            lines.append("")
        
        # 常見模式
        if r.common_action_sequences:
            lines.append("🔄 常見執行序列模式")
            lines.append("-" * 40)
            for p in r.common_action_sequences:
                lines.append(f"  {p['pattern']} (出現 {p['count']} 次)")
            lines.append("")
        
        lines.append("=" * 60)
        return "\n".join(lines)
    
    def save_report(self, output_path: str):
        """儲存 JSON 報告"""
        # 轉換 dataclass 為 dict
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
    """主程式"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Skill-0 結構分析工具')
    parser.add_argument('--parsed-dir', '-p', default='parsed',
                        help='已解析 skills 的目錄 (預設: parsed)')
    parser.add_argument('--output', '-o', default='analysis/report.json',
                        help='輸出報告路徑 (預設: analysis/report.json)')
    parser.add_argument('--text', '-t', action='store_true',
                        help='同時輸出文字報告')
    
    args = parser.parse_args()
    
    # 確保輸出目錄存在
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 執行分析
    analyzer = SkillAnalyzer(args.parsed_dir)
    
    print(f"📂 載入 skills 從: {args.parsed_dir}")
    count = analyzer.load_skills()
    print(f"✓ 載入 {count} 個 skills")
    
    print("🔍 執行分析...")
    analyzer.analyze()
    
    # 輸出
    analyzer.save_report(args.output)
    print(f"✓ JSON 報告已儲存: {args.output}")
    
    if args.text:
        text_report = analyzer.generate_report_text()
        text_path = output_path.with_suffix('.txt')
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write(text_report)
        print(f"✓ 文字報告已儲存: {text_path}")
    
    # 顯示摘要
    print("\n" + analyzer.generate_report_text())


if __name__ == '__main__':
    main()
