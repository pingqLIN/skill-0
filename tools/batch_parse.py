#!/usr/bin/env python3
"""
批次解析 Claude Skills 為 Skill-0 v2.1 格式
"""

import json
from datetime import datetime
from pathlib import Path

# 基本模板
def create_skill_template(skill_id, name, description, source):
    return {
        "$schema": "../schema/skill-decomposition.schema.json",
        "meta": {
            "skill_id": f"claude__{skill_id}",
            "name": name,
            "skill_layer": "claude_skill",
            "title": f"{name.title()} Skill",
            "description": description[:200] if len(description) > 200 else description,
            "schema_version": "2.1.0",
            "parse_timestamp": datetime.now().isoformat() + "Z",
            "parser_version": "skill-0 v2.1",
            "parsed_by": "skill-0-batch"
        },
        "original_definition": {
            "source": source,
            "skill_name": name,
            "skill_description": description
        },
        "decomposition": {
            "actions": [],
            "rules": [],
            "directives": []
        }
    }

# Skills 定義
SKILLS = {
    "xlsx": {
        "name": "xlsx",
        "description": "Comprehensive spreadsheet creation, editing, and analysis with support for formulas, formatting, data analysis, and visualization.",
        "source": "ComposioHQ/awesome-claude-skills",
        "actions": [
            {"id": "a_001", "name": "Read Excel File", "action_type": "io_read", "description": "Load Excel file using pandas or openpyxl"},
            {"id": "a_002", "name": "Write Excel File", "action_type": "io_write", "description": "Save data to Excel format with formatting"},
            {"id": "a_003", "name": "Create Formulas", "action_type": "transform", "description": "Add Excel formulas to cells"},
            {"id": "a_004", "name": "Apply Formatting", "action_type": "transform", "description": "Apply colors, fonts, and cell styles"},
            {"id": "a_005", "name": "Data Analysis", "action_type": "transform", "description": "Analyze data using pandas functions"},
            {"id": "a_006", "name": "Recalculate Formulas", "action_type": "external_call", "description": "Use LibreOffice to recalculate formula values"},
        ],
        "rules": [
            {"id": "r_001", "description": "Use formulas instead of hardcoded values", "condition": "always"},
            {"id": "r_002", "description": "Verify zero formula errors before delivery", "condition": "on_output"},
            {"id": "r_003", "description": "Use proper color coding for financial models", "condition": "when_financial"},
        ],
        "directives": [
            {"id": "d_001", "directive_type": "principle", "description": "Use Excel formulas instead of calculating in Python"},
            {"id": "d_002", "directive_type": "constraint", "description": "Every model must have zero formula errors"},
            {"id": "d_003", "directive_type": "knowledge", "description": "Blue text for inputs, black for formulas, green for links"},
        ]
    },
    
    "docx": {
        "name": "docx",
        "description": "Comprehensive document creation, editing, and analysis with support for tracked changes, comments, and formatting preservation.",
        "source": "ComposioHQ/awesome-claude-skills",
        "actions": [
            {"id": "a_001", "name": "Extract Text", "action_type": "io_read", "description": "Convert document to markdown using pandoc"},
            {"id": "a_002", "name": "Unpack Document", "action_type": "io_read", "description": "Extract OOXML from docx archive"},
            {"id": "a_003", "name": "Create Document", "action_type": "io_write", "description": "Create new Word document using docx-js"},
            {"id": "a_004", "name": "Edit XML", "action_type": "transform", "description": "Modify document.xml content"},
            {"id": "a_005", "name": "Pack Document", "action_type": "io_write", "description": "Repack modified XML to docx"},
            {"id": "a_006", "name": "Add Tracked Changes", "action_type": "transform", "description": "Insert w:ins and w:del tags for redlining"},
        ],
        "rules": [
            {"id": "r_001", "description": "Use redlining workflow for editing others' documents", "condition": "when_editing_external"},
            {"id": "r_002", "description": "Mark only changed text, not entire sentences", "condition": "when_tracking_changes"},
            {"id": "r_003", "description": "Read documentation file before editing", "condition": "before_edit"},
        ],
        "directives": [
            {"id": "d_001", "directive_type": "principle", "description": "Minimal, precise edits - only mark text that actually changes"},
            {"id": "d_002", "directive_type": "completion", "description": "All tracked changes implemented and verified"},
        ]
    },
    
    "pptx": {
        "name": "pptx",
        "description": "Presentation creation, editing, and analysis with support for layouts, comments, and speaker notes.",
        "source": "ComposioHQ/awesome-claude-skills",
        "actions": [
            {"id": "a_001", "name": "Extract Text", "action_type": "io_read", "description": "Convert presentation to markdown"},
            {"id": "a_002", "name": "Create Thumbnails", "action_type": "transform", "description": "Generate thumbnail grid of slides"},
            {"id": "a_003", "name": "Create from HTML", "action_type": "io_write", "description": "Convert HTML slides to PPTX using html2pptx"},
            {"id": "a_004", "name": "Edit OOXML", "action_type": "transform", "description": "Modify slide XML directly"},
            {"id": "a_005", "name": "Rearrange Slides", "action_type": "transform", "description": "Duplicate and reorder slides using script"},
            {"id": "a_006", "name": "Replace Text", "action_type": "transform", "description": "Replace placeholder text in templates"},
        ],
        "rules": [
            {"id": "r_001", "description": "State design approach before writing code", "condition": "before_creation"},
            {"id": "r_002", "description": "Match layout structure to actual content count", "condition": "when_selecting_layout"},
            {"id": "r_003", "description": "Visual validate after creation", "condition": "after_creation"},
        ],
        "directives": [
            {"id": "d_001", "directive_type": "principle", "description": "Use web-safe fonts only"},
            {"id": "d_002", "directive_type": "principle", "description": "Create clear visual hierarchy through size, weight, color"},
            {"id": "d_003", "directive_type": "constraint", "description": "Nothing falls off page, nothing overlaps"},
        ]
    },
    
    "mcp-builder": {
        "name": "mcp-builder",
        "description": "Guide for creating high-quality MCP servers that enable LLMs to interact with external services.",
        "source": "ComposioHQ/awesome-claude-skills",
        "actions": [
            {"id": "a_001", "name": "Fetch Documentation", "action_type": "io_read", "description": "Load MCP protocol and SDK documentation"},
            {"id": "a_002", "name": "Study API", "action_type": "io_read", "description": "Exhaustively study target API documentation"},
            {"id": "a_003", "name": "Create Plan", "action_type": "transform", "description": "Create comprehensive implementation plan"},
            {"id": "a_004", "name": "Implement Tools", "action_type": "io_write", "description": "Write MCP server code with tool definitions"},
            {"id": "a_005", "name": "Build Project", "action_type": "external_call", "description": "Run npm build or python compile"},
            {"id": "a_006", "name": "Create Evaluations", "action_type": "io_write", "description": "Write 10 evaluation questions"},
        ],
        "rules": [
            {"id": "r_001", "description": "Build for workflows, not just API endpoints", "condition": "always"},
            {"id": "r_002", "description": "Return high-signal information, not data dumps", "condition": "when_designing_tools"},
            {"id": "r_003", "description": "Error messages should guide agents toward correct usage", "condition": "when_handling_errors"},
        ],
        "directives": [
            {"id": "d_001", "directive_type": "principle", "description": "Optimize for limited context - agents have constrained windows"},
            {"id": "d_002", "directive_type": "strategy", "description": "Follow 4-phase workflow: Research, Implement, Review, Evaluate"},
            {"id": "d_003", "directive_type": "completion", "description": "10 evaluation questions created and verified"},
        ]
    },
    
    "webapp-testing": {
        "name": "webapp-testing",
        "description": "Toolkit for testing local web applications using Playwright.",
        "source": "ComposioHQ/awesome-claude-skills",
        "actions": [
            {"id": "a_001", "name": "Start Server", "action_type": "external_call", "description": "Launch dev server using with_server.py"},
            {"id": "a_002", "name": "Navigate Page", "action_type": "external_call", "description": "Open URL and wait for networkidle"},
            {"id": "a_003", "name": "Take Screenshot", "action_type": "io_write", "description": "Capture page screenshot"},
            {"id": "a_004", "name": "Inspect DOM", "action_type": "io_read", "description": "Get page content and locate elements"},
            {"id": "a_005", "name": "Execute Actions", "action_type": "external_call", "description": "Click, type, select using discovered selectors"},
        ],
        "rules": [
            {"id": "r_001", "description": "Wait for networkidle before DOM inspection", "condition": "on_dynamic_pages"},
            {"id": "r_002", "description": "Use scripts as black boxes - run --help first", "condition": "when_using_helpers"},
        ],
        "directives": [
            {"id": "d_001", "directive_type": "strategy", "description": "Reconnaissance-then-action pattern: inspect, identify, execute"},
            {"id": "d_002", "directive_type": "principle", "description": "Always close browser when done"},
        ]
    },
    
    "skill-creator": {
        "name": "skill-creator",
        "description": "Guide for creating effective skills that extend Claude's capabilities.",
        "source": "ComposioHQ/awesome-claude-skills",
        "actions": [
            {"id": "a_001", "name": "Gather Examples", "action_type": "await_input", "description": "Understand concrete examples of skill usage"},
            {"id": "a_002", "name": "Plan Contents", "action_type": "transform", "description": "Identify scripts, references, assets needed"},
            {"id": "a_003", "name": "Initialize Skill", "action_type": "external_call", "description": "Run init_skill.py to create structure"},
            {"id": "a_004", "name": "Write SKILL.md", "action_type": "io_write", "description": "Create skill documentation"},
            {"id": "a_005", "name": "Package Skill", "action_type": "external_call", "description": "Validate and package using package_skill.py"},
        ],
        "rules": [
            {"id": "r_001", "description": "Use imperative form, not second person", "condition": "when_writing"},
            {"id": "r_002", "description": "Don't overwhelm users with questions", "condition": "when_gathering_info"},
        ],
        "directives": [
            {"id": "d_001", "directive_type": "knowledge", "description": "Skills have 3-level loading: metadata, SKILL.md, bundled resources"},
            {"id": "d_002", "directive_type": "principle", "description": "Avoid duplication between SKILL.md and references"},
            {"id": "d_003", "directive_type": "completion", "description": "Skill packaged and validated successfully"},
        ]
    },
    
    "canvas-design": {
        "name": "canvas-design",
        "description": "Create beautiful visual art in PNG and PDF documents using design philosophy.",
        "source": "ComposioHQ/awesome-claude-skills",
        "actions": [
            {"id": "a_001", "name": "Create Philosophy", "action_type": "io_write", "description": "Write design philosophy manifesto as .md file"},
            {"id": "a_002", "name": "Deduce Reference", "action_type": "transform", "description": "Identify subtle conceptual thread from request"},
            {"id": "a_003", "name": "Create Canvas", "action_type": "io_write", "description": "Express philosophy visually as PDF or PNG"},
            {"id": "a_004", "name": "Download Fonts", "action_type": "io_read", "description": "Search and use fonts from canvas-fonts directory"},
            {"id": "a_005", "name": "Refine Output", "action_type": "transform", "description": "Take second pass to polish the masterpiece"},
        ],
        "rules": [
            {"id": "r_001", "description": "Text as visual accent only (10% text, 90% visual)", "condition": "always"},
            {"id": "r_002", "description": "Nothing overlaps, nothing falls off page", "condition": "always"},
            {"id": "r_003", "description": "Work must appear meticulously crafted", "condition": "always"},
        ],
        "directives": [
            {"id": "d_001", "directive_type": "principle", "description": "Create art movements, not layouts - emphasize craftsmanship repeatedly"},
            {"id": "d_002", "directive_type": "principle", "description": "Subtle reference embedded within art, not literal"},
            {"id": "d_003", "directive_type": "completion", "description": "Output as single PDF or PNG alongside philosophy .md file"},
        ]
    },
    
    "internal-comms": {
        "name": "internal-comms",
        "description": "Resources for writing internal communications like status reports, newsletters, FAQs.",
        "source": "ComposioHQ/awesome-claude-skills",
        "actions": [
            {"id": "a_001", "name": "Identify Type", "action_type": "transform", "description": "Determine communication type from request"},
            {"id": "a_002", "name": "Load Guideline", "action_type": "io_read", "description": "Load appropriate template from examples/ directory"},
            {"id": "a_003", "name": "Write Communication", "action_type": "io_write", "description": "Follow specific instructions for format and tone"},
        ],
        "rules": [
            {"id": "r_001", "description": "Match communication type to guideline file", "condition": "always"},
        ],
        "directives": [
            {"id": "d_001", "directive_type": "knowledge", "description": "Communication types: 3P updates, newsletters, FAQs, status reports"},
            {"id": "d_002", "directive_type": "completion", "description": "Communication written following company format"},
        ]
    },
    
    "file-organizer": {
        "name": "file-organizer",
        "description": "Intelligently organizes files by understanding context, finding duplicates, suggesting structures.",
        "source": "ComposioHQ/awesome-claude-skills",
        "actions": [
            {"id": "a_001", "name": "Analyze Structure", "action_type": "io_read", "description": "Review folders and files using ls, find, du"},
            {"id": "a_002", "name": "Find Duplicates", "action_type": "io_read", "description": "Identify duplicate files by hash or name"},
            {"id": "a_003", "name": "Propose Plan", "action_type": "transform", "description": "Present organization plan with folder structure"},
            {"id": "a_004", "name": "Create Folders", "action_type": "io_write", "description": "Create new directory structure"},
            {"id": "a_005", "name": "Move Files", "action_type": "io_write", "description": "Relocate files with logging"},
            {"id": "a_006", "name": "Delete Files", "action_type": "io_write", "description": "Remove duplicates or trash after confirmation"},
        ],
        "rules": [
            {"id": "r_001", "description": "Always confirm before deleting anything", "condition": "before_delete"},
            {"id": "r_002", "description": "Log all moves for potential undo", "condition": "when_moving"},
            {"id": "r_003", "description": "Preserve original modification dates", "condition": "when_moving"},
        ],
        "directives": [
            {"id": "d_001", "directive_type": "strategy", "description": "Start small (one folder), build trust, then expand"},
            {"id": "d_002", "directive_type": "principle", "description": "Archive aggressively instead of deleting"},
            {"id": "d_003", "directive_type": "completion", "description": "Provide summary with maintenance tips"},
        ]
    },
    
    "image-enhancer": {
        "name": "image-enhancer",
        "description": "Improves image quality by enhancing resolution, sharpness, and clarity.",
        "source": "ComposioHQ/awesome-claude-skills",
        "actions": [
            {"id": "a_001", "name": "Analyze Image", "action_type": "io_read", "description": "Check resolution, sharpness, compression artifacts"},
            {"id": "a_002", "name": "Upscale Image", "action_type": "transform", "description": "Increase resolution intelligently"},
            {"id": "a_003", "name": "Sharpen Edges", "action_type": "transform", "description": "Enhance edges and details"},
            {"id": "a_004", "name": "Reduce Artifacts", "action_type": "transform", "description": "Clean up compression artifacts and noise"},
            {"id": "a_005", "name": "Save Enhanced", "action_type": "io_write", "description": "Save enhanced image, preserve original"},
        ],
        "rules": [
            {"id": "r_001", "description": "Always keep original files as backup", "condition": "always"},
            {"id": "r_002", "description": "Optimize for target platform if specified", "condition": "when_platform_known"},
        ],
        "directives": [
            {"id": "d_001", "directive_type": "completion", "description": "Enhanced image saved with -enhanced suffix"},
            {"id": "d_002", "directive_type": "principle", "description": "Batch process entire folders when requested"},
        ]
    },
}


def parse_skill(skill_key, skill_data):
    """解析單一 skill 為 v2.0 格式"""
    template = create_skill_template(
        skill_id=skill_key.replace("-", "_"),
        name=skill_data["name"],
        description=skill_data["description"],
        source=skill_data["source"]
    )
    
    # 添加 actions
    for action in skill_data.get("actions", []):
        template["decomposition"]["actions"].append({
            "id": action["id"],
            "name": action["name"],
            "action_type": action["action_type"],
            "description": action["description"],
            "deterministic": action.get("deterministic", True),
            "side_effects": action.get("side_effects", [])
        })
    
    # 添加 rules
    for rule in skill_data.get("rules", []):
        template["decomposition"]["rules"].append({
            "id": rule["id"],
            "description": rule["description"],
            "condition": rule.get("condition", "always"),
            "output": rule.get("output", "proceed_or_halt")
        })
    
    # 添加 directives
    for directive in skill_data.get("directives", []):
        template["decomposition"]["directives"].append({
            "id": directive["id"],
            "directive_type": directive["directive_type"],
            "description": directive["description"],
            "decomposable": directive.get("decomposable", True)
        })
    
    return template


def main():
    """批次解析所有 skills"""
    output_dir = Path("parsed")
    output_dir.mkdir(exist_ok=True)
    
    print(f"📦 開始批次解析 {len(SKILLS)} 個 skills...")
    
    for skill_key, skill_data in SKILLS.items():
        parsed = parse_skill(skill_key, skill_data)
        output_path = output_dir / f"{skill_key}-skill.json"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(parsed, f, ensure_ascii=False, indent=2)
        
        action_count = len(parsed["decomposition"]["actions"])
        rule_count = len(parsed["decomposition"]["rules"])
        directive_count = len(parsed["decomposition"]["directives"])
        
        print(f"  ✓ {skill_key}: {action_count}A / {rule_count}R / {directive_count}D")
    
    print(f"\n✅ 完成！已解析 {len(SKILLS)} 個 skills 至 {output_dir}/")


if __name__ == "__main__":
    main()
