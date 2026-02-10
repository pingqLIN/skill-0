<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
#!/usr/bin/env python3
"""
Skill Format Converter

Converts skills between different AI agent formats:
- Awesome-Copilot (.instructions.md) → OpenCode (SKILL.md)
- Batch conversion support
- Preserves content while adapting frontmatter

Usage:
    python skill_converter.py convert <input_file> <output_dir>
    python skill_converter.py batch <input_dir> <output_dir>
    python skill_converter.py analyze <input_dir>

Author: skill-0 project
Created: 2026-01-27
"""

import os
import re
import json
import argparse
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any


@dataclass
class SkillMetadata:
    """Unified skill metadata structure"""

    name: str
    description: str
    source_format: str  # 'instructions.md', 'skill.md'
    source_path: str
    apply_to: Optional[str] = None
    license: Optional[str] = None

    def to_opencode_frontmatter(self) -> str:
        """Generate OpenCode SKILL.md frontmatter"""
        lines = ["---"]
        lines.append(f"name: {self.name}")

        # Enhance description with trigger info
        desc = self.description
        if self.apply_to:
            desc += f" Triggers on: {self.apply_to}"
        lines.append(f"description: {desc}")

        if self.license:
            lines.append(f"license: {self.license}")

        lines.append("---")
        return "\n".join(lines)


class SkillConverter:
    """Convert skills between different AI agent formats"""

    # Pattern to match YAML frontmatter
    FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.stats = {"converted": 0, "skipped": 0, "errors": []}

    def log(self, msg: str):
        if self.verbose:
            print(f"[skill-converter] {msg}")

    def parse_frontmatter(self, content: str) -> tuple[Dict[str, str], str]:
        """Parse YAML frontmatter from markdown content"""
        match = self.FRONTMATTER_PATTERN.match(content)
        if not match:
            return {}, content

        frontmatter_text = match.group(1)
        body = content[match.end() :]

        # Simple YAML parsing (handles single-line key: value)
        metadata = {}
        for line in frontmatter_text.split("\n"):
            line = line.strip()
            if ":" in line and not line.startswith("#"):
                key, _, value = line.partition(":")
                key = key.strip()
                value = value.strip().strip("'\"")
                metadata[key] = value

        return metadata, body

    def detect_format(self, filepath: Path) -> str:
        """Detect skill format from file path"""
        name = filepath.name.lower()
        if name == "skill.md":
            return "skill.md"
        elif name.endswith(".instructions.md"):
            return "instructions.md"
        else:
            return "unknown"

    def extract_skill_name(self, filepath: Path) -> str:
        """Extract skill name from file path"""
        name = filepath.stem
        # Remove .instructions suffix if present
        if name.endswith(".instructions"):
            name = name[:-13]
        return name.lower().replace(" ", "-").replace("_", "-")

    def convert_instructions_to_opencode(
        self, input_path: Path, output_dir: Path
    ) -> Optional[Path]:
        """
        Convert Awesome-Copilot .instructions.md to OpenCode SKILL.md

        Input format:
        ---
        description: '...'
        applyTo: '**/*.cs'
        ---

        Output format (in skill_name/SKILL.md):
        ---
        name: skill-name
        description: ... Triggers on: **/*.cs
        ---
        """
        try:
            content = input_path.read_text(encoding="utf-8")
            metadata, body = self.parse_frontmatter(content)

            skill_name = self.extract_skill_name(input_path)

            skill = SkillMetadata(
                name=skill_name,
                description=metadata.get("description", f"{skill_name} guidelines"),
                source_format="instructions.md",
                source_path=str(input_path),
                apply_to=metadata.get("applyTo"),
            )

            # Create output directory
            skill_dir = output_dir / skill_name
            skill_dir.mkdir(parents=True, exist_ok=True)

            # Write SKILL.md
            output_path = skill_dir / "SKILL.md"
            output_content = skill.to_opencode_frontmatter() + "\n" + body
            output_path.write_text(output_content, encoding="utf-8")

            self.log(f"Converted: {input_path.name} -> {output_path}")
            self.stats["converted"] += 1

            return output_path

        except Exception as e:
            self.stats["errors"].append({"file": str(input_path), "error": str(e)})
            self.log(f"Error converting {input_path}: {e}")
            return None

    def convert_skill_md_to_opencode(
        self, input_path: Path, output_dir: Path
    ) -> Optional[Path]:
        """
        Convert existing SKILL.md to standardized OpenCode format

        Ensures consistent frontmatter structure
        """
        try:
            content = input_path.read_text(encoding="utf-8")
            metadata, body = self.parse_frontmatter(content)

            # Get skill name from frontmatter or directory
            skill_name = metadata.get("name", input_path.parent.name).lower()
            skill_name = skill_name.replace(" ", "-").replace("_", "-")

            skill = SkillMetadata(
                name=skill_name,
                description=metadata.get("description", f"{skill_name} skill"),
                source_format="skill.md",
                source_path=str(input_path),
                license=metadata.get("license"),
            )

            # Create output directory
            skill_dir = output_dir / skill_name
            skill_dir.mkdir(parents=True, exist_ok=True)

            # Write SKILL.md
            output_path = skill_dir / "SKILL.md"
            output_content = skill.to_opencode_frontmatter() + "\n" + body
            output_path.write_text(output_content, encoding="utf-8")

            self.log(f"Converted: {input_path} -> {output_path}")
            self.stats["converted"] += 1

            return output_path

        except Exception as e:
            self.stats["errors"].append({"file": str(input_path), "error": str(e)})
            self.log(f"Error converting {input_path}: {e}")
            return None

    def convert(self, input_path: Path, output_dir: Path) -> Optional[Path]:
        """Auto-detect format and convert"""
        fmt = self.detect_format(input_path)

        if fmt == "instructions.md":
            return self.convert_instructions_to_opencode(input_path, output_dir)
        elif fmt == "skill.md":
            return self.convert_skill_md_to_opencode(input_path, output_dir)
        else:
            self.log(f"Skipping unknown format: {input_path}")
            self.stats["skipped"] += 1
            return None

    def batch_convert(
        self, input_dir: Path, output_dir: Path, pattern: str = "*.instructions.md"
    ) -> List[Path]:
        """Convert all matching files in directory"""
        results = []

        for filepath in input_dir.glob(pattern):
            result = self.convert(filepath, output_dir)
            if result:
                results.append(result)

        # Also look for SKILL.md files in subdirectories
        for filepath in input_dir.glob("**/SKILL.md"):
            result = self.convert(filepath, output_dir)
            if result:
                results.append(result)

        return results

    def analyze(self, input_dir: Path) -> Dict[str, Any]:
        """Analyze skills in a directory"""
        analysis = {
            "directory": str(input_dir),
            "timestamp": datetime.now().isoformat(),
            "skills": [],
            "summary": {"instructions_md": 0, "skill_md": 0, "unknown": 0, "total": 0},
        }

        # Find all potential skill files
        patterns = ["*.instructions.md", "**/SKILL.md"]

        seen = set()

        for pattern in patterns:
            for filepath in input_dir.glob(pattern):
                if str(filepath) in seen:
                    continue
                seen.add(str(filepath))

                fmt = self.detect_format(filepath)
                content = filepath.read_text(encoding="utf-8")
                metadata, _ = self.parse_frontmatter(content)

                skill_info = {
                    "path": str(filepath.relative_to(input_dir)),
                    "format": fmt,
                    "name": self.extract_skill_name(filepath),
                    "description": metadata.get("description", "N/A")[:100],
                    "apply_to": metadata.get("applyTo"),
                }

                analysis["skills"].append(skill_info)
                analysis["summary"][fmt.replace(".", "_")] = (
                    analysis["summary"].get(fmt.replace(".", "_"), 0) + 1
                )
                analysis["summary"]["total"] += 1

        return analysis

    def get_stats(self) -> Dict[str, Any]:
        """Get conversion statistics"""
        return self.stats


def main():
    parser = argparse.ArgumentParser(
        description="Convert skills between AI agent formats"
    )
    parser.add_argument("-v", "--verbose", action="store_true")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # convert command
    convert_parser = subparsers.add_parser("convert", help="Convert single file")
    convert_parser.add_argument("input_file", type=Path)
    convert_parser.add_argument("output_dir", type=Path)

    # batch command
    batch_parser = subparsers.add_parser("batch", help="Batch convert directory")
    batch_parser.add_argument("input_dir", type=Path)
    batch_parser.add_argument("output_dir", type=Path)
    batch_parser.add_argument("--pattern", default="*.instructions.md")

    # analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze skills directory")
    analyze_parser.add_argument("input_dir", type=Path)
    analyze_parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()
    converter = SkillConverter(verbose=args.verbose)

    if args.command == "convert":
        result = converter.convert(args.input_file, args.output_dir)
        if result:
            print(f"✅ Converted to: {result}")
        else:
            print("❌ Conversion failed")

    elif args.command == "batch":
        results = converter.batch_convert(args.input_dir, args.output_dir, args.pattern)
        stats = converter.get_stats()
        print(f"\n📊 Batch conversion complete:")
        print(f"   ✅ Converted: {stats['converted']}")
        print(f"   ⏭️  Skipped: {stats['skipped']}")
        print(f"   ❌ Errors: {len(stats['errors'])}")

        if stats["errors"]:
            print("\n⚠️  Errors:")
            for err in stats["errors"]:
                print(f"   - {err['file']}: {err['error']}")

    elif args.command == "analyze":
        analysis = converter.analyze(args.input_dir)

        if args.json:
            print(json.dumps(analysis, indent=2))
        else:
            print(f"\n📁 Skills Analysis: {args.input_dir}")
            print(f"   Total: {analysis['summary']['total']}")
            print(
                f"   .instructions.md: {analysis['summary'].get('instructions_md', 0)}"
            )
            print(f"   SKILL.md: {analysis['summary'].get('skill_md', 0)}")
            print("\n📋 Skills found:")
            for skill in analysis["skills"][:20]:  # Show first 20
                print(f"   - {skill['name']} ({skill['format']})")
            if len(analysis["skills"]) > 20:
                print(f"   ... and {len(analysis['skills']) - 20} more")


if __name__ == "__main__":
    main()
=======
=======
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
#!/usr/bin/env python3
"""
Skill Format Converter

Converts skills between different AI agent formats:
- Awesome-Copilot (.instructions.md) → OpenCode (SKILL.md)
- Batch conversion support
- Preserves content while adapting frontmatter

Usage:
    python skill_converter.py convert <input_file> <output_dir>
    python skill_converter.py batch <input_dir> <output_dir>
    python skill_converter.py analyze <input_dir>

Author: skill-0 project
Created: 2026-01-27
"""

import os
import re
import json
import argparse
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any


@dataclass
class SkillMetadata:
    """Unified skill metadata structure"""

    name: str
    description: str
    source_format: str  # 'instructions.md', 'skill.md'
    source_path: str
    apply_to: Optional[str] = None
    license: Optional[str] = None

    def to_opencode_frontmatter(self) -> str:
        """Generate OpenCode SKILL.md frontmatter"""
        lines = ["---"]
        lines.append(f"name: {self.name}")

        # Enhance description with trigger info
        desc = self.description
        if self.apply_to:
            desc += f" Triggers on: {self.apply_to}"
        lines.append(f"description: {desc}")

        if self.license:
            lines.append(f"license: {self.license}")

        lines.append("---")
        return "\n".join(lines)


class SkillConverter:
    """Convert skills between different AI agent formats"""

    # Pattern to match YAML frontmatter
    FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.stats = {"converted": 0, "skipped": 0, "errors": []}

    def log(self, msg: str):
        if self.verbose:
            print(f"[skill-converter] {msg}")

    def parse_frontmatter(self, content: str) -> tuple[Dict[str, str], str]:
        """Parse YAML frontmatter from markdown content"""
        match = self.FRONTMATTER_PATTERN.match(content)
        if not match:
            return {}, content

        frontmatter_text = match.group(1)
        body = content[match.end() :]

        # Simple YAML parsing (handles single-line key: value)
        metadata = {}
        for line in frontmatter_text.split("\n"):
            line = line.strip()
            if ":" in line and not line.startswith("#"):
                key, _, value = line.partition(":")
                key = key.strip()
                value = value.strip().strip("'\"")
                metadata[key] = value

        return metadata, body

    def detect_format(self, filepath: Path) -> str:
        """Detect skill format from file path"""
        name = filepath.name.lower()
        if name == "skill.md":
            return "skill.md"
        elif name.endswith(".instructions.md"):
            return "instructions.md"
        else:
            return "unknown"

    def extract_skill_name(self, filepath: Path) -> str:
        """Extract skill name from file path"""
        name = filepath.stem
        # Remove .instructions suffix if present
        if name.endswith(".instructions"):
            name = name[:-13]
        return name.lower().replace(" ", "-").replace("_", "-")

    def convert_instructions_to_opencode(
        self, input_path: Path, output_dir: Path
    ) -> Optional[Path]:
        """
        Convert Awesome-Copilot .instructions.md to OpenCode SKILL.md

        Input format:
        ---
        description: '...'
        applyTo: '**/*.cs'
        ---

        Output format (in skill_name/SKILL.md):
        ---
        name: skill-name
        description: ... Triggers on: **/*.cs
        ---
        """
        try:
            content = input_path.read_text(encoding="utf-8")
            metadata, body = self.parse_frontmatter(content)

            skill_name = self.extract_skill_name(input_path)

            skill = SkillMetadata(
                name=skill_name,
                description=metadata.get("description", f"{skill_name} guidelines"),
                source_format="instructions.md",
                source_path=str(input_path),
                apply_to=metadata.get("applyTo"),
            )

            # Create output directory
            skill_dir = output_dir / skill_name
            skill_dir.mkdir(parents=True, exist_ok=True)

            # Write SKILL.md
            output_path = skill_dir / "SKILL.md"
            output_content = skill.to_opencode_frontmatter() + "\n" + body
            output_path.write_text(output_content, encoding="utf-8")

            self.log(f"Converted: {input_path.name} -> {output_path}")
            self.stats["converted"] += 1

            return output_path

        except Exception as e:
            self.stats["errors"].append({"file": str(input_path), "error": str(e)})
            self.log(f"Error converting {input_path}: {e}")
            return None

    def convert_skill_md_to_opencode(
        self, input_path: Path, output_dir: Path
    ) -> Optional[Path]:
        """
        Convert existing SKILL.md to standardized OpenCode format

        Ensures consistent frontmatter structure
        """
        try:
            content = input_path.read_text(encoding="utf-8")
            metadata, body = self.parse_frontmatter(content)

            # Get skill name from frontmatter or directory
            skill_name = metadata.get("name", input_path.parent.name).lower()
            skill_name = skill_name.replace(" ", "-").replace("_", "-")

            skill = SkillMetadata(
                name=skill_name,
                description=metadata.get("description", f"{skill_name} skill"),
                source_format="skill.md",
                source_path=str(input_path),
                license=metadata.get("license"),
            )

            # Create output directory
            skill_dir = output_dir / skill_name
            skill_dir.mkdir(parents=True, exist_ok=True)

            # Write SKILL.md
            output_path = skill_dir / "SKILL.md"
            output_content = skill.to_opencode_frontmatter() + "\n" + body
            output_path.write_text(output_content, encoding="utf-8")

            self.log(f"Converted: {input_path} -> {output_path}")
            self.stats["converted"] += 1

            return output_path

        except Exception as e:
            self.stats["errors"].append({"file": str(input_path), "error": str(e)})
            self.log(f"Error converting {input_path}: {e}")
            return None

    def convert(self, input_path: Path, output_dir: Path) -> Optional[Path]:
        """Auto-detect format and convert"""
        fmt = self.detect_format(input_path)

        if fmt == "instructions.md":
            return self.convert_instructions_to_opencode(input_path, output_dir)
        elif fmt == "skill.md":
            return self.convert_skill_md_to_opencode(input_path, output_dir)
        else:
            self.log(f"Skipping unknown format: {input_path}")
            self.stats["skipped"] += 1
            return None

    def batch_convert(
        self, input_dir: Path, output_dir: Path, pattern: str = "*.instructions.md"
    ) -> List[Path]:
        """Convert all matching files in directory"""
        results = []

        for filepath in input_dir.glob(pattern):
            result = self.convert(filepath, output_dir)
            if result:
                results.append(result)

        # Also look for SKILL.md files in subdirectories
        for filepath in input_dir.glob("**/SKILL.md"):
            result = self.convert(filepath, output_dir)
            if result:
                results.append(result)

        return results

    def analyze(self, input_dir: Path) -> Dict[str, Any]:
        """Analyze skills in a directory"""
        analysis = {
            "directory": str(input_dir),
            "timestamp": datetime.now().isoformat(),
            "skills": [],
            "summary": {"instructions_md": 0, "skill_md": 0, "unknown": 0, "total": 0},
        }

        # Find all potential skill files
        patterns = ["*.instructions.md", "**/SKILL.md"]

        seen = set()

        for pattern in patterns:
            for filepath in input_dir.glob(pattern):
                if str(filepath) in seen:
                    continue
                seen.add(str(filepath))

                fmt = self.detect_format(filepath)
                content = filepath.read_text(encoding="utf-8")
                metadata, _ = self.parse_frontmatter(content)

                skill_info = {
                    "path": str(filepath.relative_to(input_dir)),
                    "format": fmt,
                    "name": self.extract_skill_name(filepath),
                    "description": metadata.get("description", "N/A")[:100],
                    "apply_to": metadata.get("applyTo"),
                }

                analysis["skills"].append(skill_info)
                analysis["summary"][fmt.replace(".", "_")] = (
                    analysis["summary"].get(fmt.replace(".", "_"), 0) + 1
                )
                analysis["summary"]["total"] += 1

        return analysis

    def get_stats(self) -> Dict[str, Any]:
        """Get conversion statistics"""
        return self.stats


def main():
    parser = argparse.ArgumentParser(
        description="Convert skills between AI agent formats"
    )
    parser.add_argument("-v", "--verbose", action="store_true")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # convert command
    convert_parser = subparsers.add_parser("convert", help="Convert single file")
    convert_parser.add_argument("input_file", type=Path)
    convert_parser.add_argument("output_dir", type=Path)

    # batch command
    batch_parser = subparsers.add_parser("batch", help="Batch convert directory")
    batch_parser.add_argument("input_dir", type=Path)
    batch_parser.add_argument("output_dir", type=Path)
    batch_parser.add_argument("--pattern", default="*.instructions.md")

    # analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze skills directory")
    analyze_parser.add_argument("input_dir", type=Path)
    analyze_parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()
    converter = SkillConverter(verbose=args.verbose)

    if args.command == "convert":
        result = converter.convert(args.input_file, args.output_dir)
        if result:
            print(f"✅ Converted to: {result}")
        else:
            print("❌ Conversion failed")

    elif args.command == "batch":
        results = converter.batch_convert(args.input_dir, args.output_dir, args.pattern)
        stats = converter.get_stats()
        print(f"\n📊 Batch conversion complete:")
        print(f"   ✅ Converted: {stats['converted']}")
        print(f"   ⏭️  Skipped: {stats['skipped']}")
        print(f"   ❌ Errors: {len(stats['errors'])}")

        if stats["errors"]:
            print("\n⚠️  Errors:")
            for err in stats["errors"]:
                print(f"   - {err['file']}: {err['error']}")

    elif args.command == "analyze":
        analysis = converter.analyze(args.input_dir)

        if args.json:
            print(json.dumps(analysis, indent=2))
        else:
            print(f"\n📁 Skills Analysis: {args.input_dir}")
            print(f"   Total: {analysis['summary']['total']}")
            print(
                f"   .instructions.md: {analysis['summary'].get('instructions_md', 0)}"
            )
            print(f"   SKILL.md: {analysis['summary'].get('skill_md', 0)}")
            print("\n📋 Skills found:")
            for skill in analysis["skills"][:20]:  # Show first 20
                print(f"   - {skill['name']} ({skill['format']})")
            if len(analysis["skills"]) > 20:
                print(f"   ... and {len(analysis['skills']) - 20} more")


if __name__ == "__main__":
    main()
<<<<<<< Updated upstream
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
