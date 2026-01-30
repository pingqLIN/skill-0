#!/usr/bin/env python3
"""
GitHub Skill Search Tool

Searches GitHub for popular skills/projects that align with skill-0 goals:
- Claude Skills
- MCP Servers  
- GitHub Copilot instructions
- AI agent skills

Usage:
    python github_skill_search.py --target 30 --output report.md
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# GitHub search queries for skill-related repositories
SEARCH_QUERIES = [
    {
        "query": "claude skill language:Markdown stars:>5",
        "category": "Claude Skills",
        "description": "Claude AI skills and instructions"
    },
    {
        "query": "mcp server language:Python OR language:TypeScript stars:>10",
        "category": "MCP Servers",
        "description": "Model Context Protocol server implementations"
    },
    {
        "query": "github copilot instructions language:Markdown stars:>5",
        "category": "GitHub Copilot",
        "description": "GitHub Copilot custom instructions"
    },
    {
        "query": "ai agent skill language:Markdown stars:>5",
        "category": "AI Agent Skills",
        "description": "General AI agent skills and prompts"
    },
    {
        "query": "SKILL.md in:path stars:>3",
        "category": "SKILL.md Format",
        "description": "Repositories using SKILL.md format"
    },
]

# Compatible licenses (permissive open source)
COMPATIBLE_LICENSES = {
    "mit": "MIT License",
    "apache-2.0": "Apache License 2.0",
    "bsd-2-clause": "BSD 2-Clause",
    "bsd-3-clause": "BSD 3-Clause",
    "isc": "ISC License",
    "cc0-1.0": "CC0 1.0 Universal",
    "unlicense": "The Unlicense",
    "0bsd": "BSD Zero Clause License",
}


class GitHubSkillSearcher:
    """Search GitHub for skills and MCP projects"""

    def __init__(self, target_count: int = 30, verbose: bool = False):
        self.target_count = target_count
        self.verbose = verbose
        self.results = []
        self.stats = {
            "total_found": 0,
            "license_compatible": 0,
            "license_incompatible": 0,
            "no_license": 0,
            "by_category": {},
        }

    def search(self) -> List[Dict[str, Any]]:
        """
        Search GitHub for skills using the GitHub MCP server.
        
        NOTE: This is a template/placeholder implementation. 
        The actual search was performed manually using GitHub MCP server tools
        in the development environment. This tool serves as:
        1. A template for future automated searches
        2. Documentation of search queries used
        3. A starting point for integration with GitHub MCP server
        
        Returns:
            Empty list (actual results documented in generated reports)
        """
        print(f"\n{'='*70}")
        print(f"🔍 Searching GitHub for Skills and MCP Projects")
        print(f"{'='*70}")
        print(f"Target: {self.target_count} projects\n")

        # Placeholder: In real implementation, this would use github-mcp-server tools
        # to search repositories
        
        print("⚠️  This tool requires GitHub MCP server integration for live search.")
        print("   Please use the GitHub search tools available in your environment.\n")
        
        print("📋 Search Queries to Execute:\n")
        for i, query_info in enumerate(SEARCH_QUERIES, 1):
            print(f"{i}. Category: {query_info['category']}")
            print(f"   Query: {query_info['query']}")
            print(f"   Description: {query_info['description']}\n")

        return self.results

    def check_license(self, license_key: str) -> bool:
        """
        Check if license is compatible.
        
        NOTE: This method is provided for future automated license checking.
        Currently, license compatibility was verified manually during the
        GitHub search process.
        """
        if not license_key:
            return False
        return license_key.lower() in COMPATIBLE_LICENSES

    def generate_report(self, output_path: Path) -> None:
        """
        Generate markdown report of findings.
        
        NOTE: This generates a template report. The actual statistics and 
        results were populated manually after performing searches using 
        GitHub MCP server tools. See docs/github-skills-search-results.json
        for the actual data collected.
        """
        
        report_content = f"""# GitHub Skills Search Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Target:** {self.target_count} projects  
**Total Found:** {self.stats['total_found']}

## Search Queries Used

"""
        
        for i, query_info in enumerate(SEARCH_QUERIES, 1):
            report_content += f"""### {i}. {query_info['category']}

**Query:** `{query_info['query']}`  
**Description:** {query_info['description']}

"""

        report_content += f"""
## License Compatibility

| Status | Count | Percentage |
|--------|-------|------------|
| ✅ Compatible | {self.stats['license_compatible']} | {self.stats['license_compatible']/max(self.stats['total_found'],1)*100:.1f}% |
| ❌ Incompatible | {self.stats['license_incompatible']} | {self.stats['license_incompatible']/max(self.stats['total_found'],1)*100:.1f}% |
| ⚠️ No License | {self.stats['no_license']} | {self.stats['no_license']/max(self.stats['total_found'],1)*100:.1f}% |

### Compatible Licenses

The following licenses are considered compatible with skill-0:

"""
        
        for key, name in COMPATIBLE_LICENSES.items():
            report_content += f"- `{key}`: {name}\n"

        report_content += """
## Search Instructions

To complete this search manually:

1. Use GitHub's search interface or GitHub MCP server tools
2. Execute each query listed above
3. For each result:
   - Check the repository license (must be in compatible list)
   - Verify it contains skill/instruction content
   - Check star count and activity (prefer active projects)
   - Note the repository URL and description

4. Select top 30 projects that:
   - Have compatible licenses
   - Contain high-quality skill definitions
   - Are actively maintained (recent commits)
   - Align with skill-0 project goals

5. For each selected project:
   - Clone or download the repository
   - Extract skill files (SKILL.md, instructions, etc.)
   - Add to `converted-skills/` directory
   - Document in the results section below

## Results

<!-- Add discovered projects here -->

| # | Repository | Stars | License | Category | Notes |
|---|------------|-------|---------|----------|-------|
| 1 | | | | | |
| 2 | | | | | |
| ... | | | | | |

## Next Steps

1. ✅ Complete the search queries above
2. ✅ Verify licenses for all candidates
3. ✅ Download/clone 30 eligible projects
4. ✅ Add skills to `converted-skills/` directory
5. ✅ Parse skills using `tools/batch_parse.py`
6. ✅ Index skills using vector database
7. ✅ Update project statistics

---

*Generated by skill-0 GitHub Search Tool*
"""

        output_path.write_text(report_content)
        print(f"✅ Report generated: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Search GitHub for skills and MCP projects")
    parser.add_argument("--target", type=int, default=30, help="Target number of projects")
    parser.add_argument("--output", type=str, default="github-skills-search-report.md", 
                       help="Output report file")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    searcher = GitHubSkillSearcher(target_count=args.target, verbose=args.verbose)
    results = searcher.search()
    
    output_path = Path(args.output)
    searcher.generate_report(output_path)
    
    print(f"\n{'='*70}")
    print(f"📊 Search Complete")
    print(f"{'='*70}")
    print(f"Report: {output_path}")
    print(f"\nNext: Use GitHub MCP server tools to execute searches and populate results.")
    print(f"{'='*70}\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
