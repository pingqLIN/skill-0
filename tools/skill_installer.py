<<<<<<< Updated upstream
#!/usr/bin/env python3
"""
OpenCode Skill Installer

Installs skills to OpenCode's skill directory.
Supports multiple sources: local files, skill-0 converted, remote repos.

Usage:
    python skill_installer.py install <skill_name_or_path> [--target <opencode_skill_dir>]
    python skill_installer.py list [--source <source_dir>]
    python skill_installer.py uninstall <skill_name>
    python skill_installer.py sync <source_dir>

Author: skill-0 project
Created: 2026-01-27
"""

import os
import sys
import json
import shutil
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any


class OpenCodeSkillInstaller:
    """Install and manage OpenCode skills"""

    # Default OpenCode skill locations to check
    OPENCODE_SKILL_PATHS = [
        Path(os.environ.get("OPENCODE_HOME", "")) / "skill",
        Path.home() / ".opencode" / "skills",
        Path.home() / ".opencode" / "skill",
        Path("C:/Dev/opencode-repo/.opencode/skill"),  # Local repo
    ]

    def __init__(self, target_dir: Optional[Path] = None, verbose: bool = False):
        self.verbose = verbose
        self.target_dir = target_dir or self._find_opencode_skill_dir()

        if not self.target_dir:
            raise RuntimeError(
                "Could not find OpenCode skill directory. "
                "Please specify with --target or set OPENCODE_HOME environment variable."
            )

    def log(self, msg: str):
        if self.verbose:
            print(f"[skill-installer] {msg}")

    def _find_opencode_skill_dir(self) -> Optional[Path]:
        """Find the first existing OpenCode skill directory"""
        for path in self.OPENCODE_SKILL_PATHS:
            if path.exists() and path.is_dir():
                self.log(f"Found OpenCode skill dir: {path}")
                return path

        # Create default if none exists
        default = Path.home() / ".opencode" / "skills"
        default.mkdir(parents=True, exist_ok=True)
        self.log(f"Created default skill dir: {default}")
        return default

    def validate_skill(self, skill_path: Path) -> tuple[bool, str]:
        """Validate a skill has required structure"""
        skill_md = skill_path / "SKILL.md"

        if not skill_path.is_dir():
            return False, f"Not a directory: {skill_path}"

        if not skill_md.exists():
            return False, f"Missing SKILL.md in {skill_path}"

        # Check frontmatter
        content = skill_md.read_text(encoding="utf-8")
        if not content.startswith("---"):
            return False, "SKILL.md missing frontmatter"

        if "name:" not in content[:500]:
            return False, "SKILL.md missing 'name' in frontmatter"

        if "description:" not in content[:1000]:
            return False, "SKILL.md missing 'description' in frontmatter"

        return True, "Valid"

    def get_skill_name(self, skill_path: Path) -> str:
        """Extract skill name from SKILL.md or directory name"""
        skill_md = skill_path / "SKILL.md"

        if skill_md.exists():
            content = skill_md.read_text(encoding="utf-8")
            import re

            match = re.search(r"name:\s*([^\n]+)", content)
            if match:
                return match.group(1).strip().strip("'\"")

        return skill_path.name

    def install(self, source: Path, force: bool = False) -> tuple[bool, str]:
        """Install a skill to OpenCode skill directory"""
        source = Path(source)

        # Handle single SKILL.md file
        if source.is_file() and source.name == "SKILL.md":
            source = source.parent

        # Validate
        valid, msg = self.validate_skill(source)
        if not valid:
            return False, msg

        skill_name = self.get_skill_name(source)
        target = self.target_dir / skill_name

        # Check existing
        if target.exists():
            if not force:
                return (
                    False,
                    f"Skill '{skill_name}' already installed. Use --force to overwrite.",
                )
            self.log(f"Removing existing: {target}")
            shutil.rmtree(target)

        # Copy
        self.log(f"Installing {skill_name} to {target}")
        shutil.copytree(source, target)

        # Write metadata
        meta_file = target / ".installed"
        meta = {
            "source": str(source),
            "installed_at": datetime.now().isoformat(),
            "skill_name": skill_name,
        }
        meta_file.write_text(json.dumps(meta, indent=2))

        return True, f"Installed '{skill_name}' to {target}"

    def uninstall(self, skill_name: str) -> tuple[bool, str]:
        """Remove an installed skill"""
        target = self.target_dir / skill_name

        if not target.exists():
            return False, f"Skill '{skill_name}' not found"

        self.log(f"Removing: {target}")
        shutil.rmtree(target)

        return True, f"Uninstalled '{skill_name}'"

    def list_installed(self) -> List[Dict[str, Any]]:
        """List all installed skills"""
        skills = []

        for item in self.target_dir.iterdir():
            if not item.is_dir():
                continue

            skill_md = item / "SKILL.md"
            if not skill_md.exists():
                continue

            skill_info = {"name": item.name, "path": str(item), "valid": True}

            # Get description
            content = skill_md.read_text(encoding="utf-8")
            import re

            desc_match = re.search(r"description:\s*([^\n]+)", content)
            if desc_match:
                skill_info["description"] = (
                    desc_match.group(1).strip().strip("'\"")[:80]
                )

            # Check metadata
            meta_file = item / ".installed"
            if meta_file.exists():
                try:
                    meta = json.loads(meta_file.read_text())
                    skill_info["source"] = meta.get("source")
                    skill_info["installed_at"] = meta.get("installed_at")
                except:
                    pass

            skills.append(skill_info)

        return skills

    def list_available(self, source_dir: Path) -> List[Dict[str, Any]]:
        """List skills available in a source directory"""
        skills = []

        # Look for SKILL.md files
        for skill_md in source_dir.glob("**/SKILL.md"):
            skill_dir = skill_md.parent
            valid, _ = self.validate_skill(skill_dir)

            skill_info = {
                "name": self.get_skill_name(skill_dir),
                "path": str(skill_dir),
                "valid": valid,
            }

            # Check if already installed
            installed_path = self.target_dir / skill_info["name"]
            skill_info["installed"] = installed_path.exists()

            skills.append(skill_info)

        return skills

    def sync(
        self, source_dir: Path, dry_run: bool = False, pattern: Optional[str] = None
    ) -> Dict[str, Any]:
        """Sync skills from source directory to OpenCode"""
        results = {"installed": [], "skipped": [], "errors": [], "dry_run": dry_run}

        available = self.list_available(source_dir)

        for skill in available:
            if not skill["valid"]:
                results["skipped"].append(
                    {"name": skill["name"], "reason": "Invalid skill structure"}
                )
                continue

            if pattern and pattern not in skill["name"]:
                results["skipped"].append(
                    {
                        "name": skill["name"],
                        "reason": f"Name doesn't match pattern '{pattern}'",
                    }
                )
                continue

            if skill["installed"]:
                results["skipped"].append(
                    {"name": skill["name"], "reason": "Already installed"}
                )
                continue

            if dry_run:
                results["installed"].append(
                    {"name": skill["name"], "note": "Would be installed"}
                )
            else:
                success, msg = self.install(Path(skill["path"]))
                if success:
                    results["installed"].append({"name": skill["name"], "message": msg})
                else:
                    results["errors"].append({"name": skill["name"], "error": msg})

        return results


def main():
    parser = argparse.ArgumentParser(description="Install and manage OpenCode skills")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--target", type=Path, help="OpenCode skill directory")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # install command
    install_parser = subparsers.add_parser("install", help="Install a skill")
    install_parser.add_argument("source", type=Path, help="Skill directory to install")
    install_parser.add_argument(
        "--force", action="store_true", help="Overwrite existing"
    )

    # uninstall command
    uninstall_parser = subparsers.add_parser("uninstall", help="Remove a skill")
    uninstall_parser.add_argument("skill_name", help="Name of skill to remove")

    # list command
    list_parser = subparsers.add_parser("list", help="List skills")
    list_parser.add_argument(
        "--source", type=Path, help="Source directory to list available skills"
    )
    list_parser.add_argument("--json", action="store_true")

    # sync command
    sync_parser = subparsers.add_parser("sync", help="Sync skills from source")
    sync_parser.add_argument("source_dir", type=Path)
    sync_parser.add_argument("--dry-run", action="store_true")
    sync_parser.add_argument("--pattern", help="Filter skills by name pattern")

    args = parser.parse_args()

    try:
        installer = OpenCodeSkillInstaller(target_dir=args.target, verbose=args.verbose)
    except RuntimeError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

    if args.command == "install":
        success, msg = installer.install(args.source, force=args.force)
        if success:
            print(f"✅ {msg}")
            print("\n⚠️  Restart OpenCode to pick up new skills.")
        else:
            print(f"❌ {msg}")
            sys.exit(1)

    elif args.command == "uninstall":
        success, msg = installer.uninstall(args.skill_name)
        if success:
            print(f"✅ {msg}")
        else:
            print(f"❌ {msg}")
            sys.exit(1)

    elif args.command == "list":
        if args.source:
            skills = installer.list_available(args.source)
            title = f"Available skills in {args.source}"
        else:
            skills = installer.list_installed()
            title = f"Installed skills in {installer.target_dir}"

        if args.json:
            print(json.dumps(skills, indent=2))
        else:
            print(f"\n📋 {title}:")
            print(f"   Total: {len(skills)}")
            print()
            for skill in skills:
                status = "✅" if skill.get("valid", True) else "⚠️"
                installed = " (installed)" if skill.get("installed") else ""
                desc = skill.get("description", "")[:50]
                print(f"   {status} {skill['name']}{installed}")
                if desc:
                    print(f"      {desc}...")

    elif args.command == "sync":
        results = installer.sync(
            args.source_dir, dry_run=args.dry_run, pattern=args.pattern
        )

        mode = "[DRY RUN] " if args.dry_run else ""
        print(f"\n📊 {mode}Sync results:")
        print(f"   ✅ Installed: {len(results['installed'])}")
        print(f"   ⏭️  Skipped: {len(results['skipped'])}")
        print(f"   ❌ Errors: {len(results['errors'])}")

        if results["installed"]:
            print("\n   Installed:")
            for item in results["installed"]:
                print(f"      - {item['name']}")

        if results["errors"]:
            print("\n   Errors:")
            for item in results["errors"]:
                print(f"      - {item['name']}: {item['error']}")

        if not args.dry_run and results["installed"]:
            print("\n⚠️  Restart OpenCode to pick up new skills.")


if __name__ == "__main__":
    main()
=======
#!/usr/bin/env python3
"""
OpenCode Skill Installer

Installs skills to OpenCode's skill directory.
Supports multiple sources: local files, skill-0 converted, remote repos.

Usage:
    python skill_installer.py install <skill_name_or_path> [--target <opencode_skill_dir>]
    python skill_installer.py list [--source <source_dir>]
    python skill_installer.py uninstall <skill_name>
    python skill_installer.py sync <source_dir>

Author: skill-0 project
Created: 2026-01-27
"""

import os
import sys
import json
import shutil
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any


class OpenCodeSkillInstaller:
    """Install and manage OpenCode skills"""

    # Default OpenCode skill locations to check
    OPENCODE_SKILL_PATHS = [
        Path(os.environ.get("OPENCODE_HOME", "")) / "skill",
        Path.home() / ".opencode" / "skills",
        Path.home() / ".opencode" / "skill",
        Path("C:/Dev/opencode-repo/.opencode/skill"),  # Local repo
    ]

    def __init__(self, target_dir: Optional[Path] = None, verbose: bool = False):
        self.verbose = verbose
        self.target_dir = target_dir or self._find_opencode_skill_dir()

        if not self.target_dir:
            raise RuntimeError(
                "Could not find OpenCode skill directory. "
                "Please specify with --target or set OPENCODE_HOME environment variable."
            )

    def log(self, msg: str):
        if self.verbose:
            print(f"[skill-installer] {msg}")

    def _find_opencode_skill_dir(self) -> Optional[Path]:
        """Find the first existing OpenCode skill directory"""
        for path in self.OPENCODE_SKILL_PATHS:
            if path.exists() and path.is_dir():
                self.log(f"Found OpenCode skill dir: {path}")
                return path

        # Create default if none exists
        default = Path.home() / ".opencode" / "skills"
        default.mkdir(parents=True, exist_ok=True)
        self.log(f"Created default skill dir: {default}")
        return default

    def validate_skill(self, skill_path: Path) -> tuple[bool, str]:
        """Validate a skill has required structure"""
        skill_md = skill_path / "SKILL.md"

        if not skill_path.is_dir():
            return False, f"Not a directory: {skill_path}"

        if not skill_md.exists():
            return False, f"Missing SKILL.md in {skill_path}"

        # Check frontmatter
        content = skill_md.read_text(encoding="utf-8")
        if not content.startswith("---"):
            return False, "SKILL.md missing frontmatter"

        if "name:" not in content[:500]:
            return False, "SKILL.md missing 'name' in frontmatter"

        if "description:" not in content[:1000]:
            return False, "SKILL.md missing 'description' in frontmatter"

        return True, "Valid"

    def get_skill_name(self, skill_path: Path) -> str:
        """Extract skill name from SKILL.md or directory name"""
        skill_md = skill_path / "SKILL.md"

        if skill_md.exists():
            content = skill_md.read_text(encoding="utf-8")
            import re

            match = re.search(r"name:\s*([^\n]+)", content)
            if match:
                return match.group(1).strip().strip("'\"")

        return skill_path.name

    def install(self, source: Path, force: bool = False) -> tuple[bool, str]:
        """Install a skill to OpenCode skill directory"""
        source = Path(source)

        # Handle single SKILL.md file
        if source.is_file() and source.name == "SKILL.md":
            source = source.parent

        # Validate
        valid, msg = self.validate_skill(source)
        if not valid:
            return False, msg

        skill_name = self.get_skill_name(source)
        target = self.target_dir / skill_name

        # Check existing
        if target.exists():
            if not force:
                return (
                    False,
                    f"Skill '{skill_name}' already installed. Use --force to overwrite.",
                )
            self.log(f"Removing existing: {target}")
            shutil.rmtree(target)

        # Copy
        self.log(f"Installing {skill_name} to {target}")
        shutil.copytree(source, target)

        # Write metadata
        meta_file = target / ".installed"
        meta = {
            "source": str(source),
            "installed_at": datetime.now().isoformat(),
            "skill_name": skill_name,
        }
        meta_file.write_text(json.dumps(meta, indent=2))

        return True, f"Installed '{skill_name}' to {target}"

    def uninstall(self, skill_name: str) -> tuple[bool, str]:
        """Remove an installed skill"""
        target = self.target_dir / skill_name

        if not target.exists():
            return False, f"Skill '{skill_name}' not found"

        self.log(f"Removing: {target}")
        shutil.rmtree(target)

        return True, f"Uninstalled '{skill_name}'"

    def list_installed(self) -> List[Dict[str, Any]]:
        """List all installed skills"""
        skills = []

        for item in self.target_dir.iterdir():
            if not item.is_dir():
                continue

            skill_md = item / "SKILL.md"
            if not skill_md.exists():
                continue

            skill_info = {"name": item.name, "path": str(item), "valid": True}

            # Get description
            content = skill_md.read_text(encoding="utf-8")
            import re

            desc_match = re.search(r"description:\s*([^\n]+)", content)
            if desc_match:
                skill_info["description"] = (
                    desc_match.group(1).strip().strip("'\"")[:80]
                )

            # Check metadata
            meta_file = item / ".installed"
            if meta_file.exists():
                try:
                    meta = json.loads(meta_file.read_text())
                    skill_info["source"] = meta.get("source")
                    skill_info["installed_at"] = meta.get("installed_at")
                except:
                    pass

            skills.append(skill_info)

        return skills

    def list_available(self, source_dir: Path) -> List[Dict[str, Any]]:
        """List skills available in a source directory"""
        skills = []

        # Look for SKILL.md files
        for skill_md in source_dir.glob("**/SKILL.md"):
            skill_dir = skill_md.parent
            valid, _ = self.validate_skill(skill_dir)

            skill_info = {
                "name": self.get_skill_name(skill_dir),
                "path": str(skill_dir),
                "valid": valid,
            }

            # Check if already installed
            installed_path = self.target_dir / skill_info["name"]
            skill_info["installed"] = installed_path.exists()

            skills.append(skill_info)

        return skills

    def sync(
        self, source_dir: Path, dry_run: bool = False, pattern: Optional[str] = None
    ) -> Dict[str, Any]:
        """Sync skills from source directory to OpenCode"""
        results = {"installed": [], "skipped": [], "errors": [], "dry_run": dry_run}

        available = self.list_available(source_dir)

        for skill in available:
            if not skill["valid"]:
                results["skipped"].append(
                    {"name": skill["name"], "reason": "Invalid skill structure"}
                )
                continue

            if pattern and pattern not in skill["name"]:
                results["skipped"].append(
                    {
                        "name": skill["name"],
                        "reason": f"Name doesn't match pattern '{pattern}'",
                    }
                )
                continue

            if skill["installed"]:
                results["skipped"].append(
                    {"name": skill["name"], "reason": "Already installed"}
                )
                continue

            if dry_run:
                results["installed"].append(
                    {"name": skill["name"], "note": "Would be installed"}
                )
            else:
                success, msg = self.install(Path(skill["path"]))
                if success:
                    results["installed"].append({"name": skill["name"], "message": msg})
                else:
                    results["errors"].append({"name": skill["name"], "error": msg})

        return results


def main():
    parser = argparse.ArgumentParser(description="Install and manage OpenCode skills")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--target", type=Path, help="OpenCode skill directory")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # install command
    install_parser = subparsers.add_parser("install", help="Install a skill")
    install_parser.add_argument("source", type=Path, help="Skill directory to install")
    install_parser.add_argument(
        "--force", action="store_true", help="Overwrite existing"
    )

    # uninstall command
    uninstall_parser = subparsers.add_parser("uninstall", help="Remove a skill")
    uninstall_parser.add_argument("skill_name", help="Name of skill to remove")

    # list command
    list_parser = subparsers.add_parser("list", help="List skills")
    list_parser.add_argument(
        "--source", type=Path, help="Source directory to list available skills"
    )
    list_parser.add_argument("--json", action="store_true")

    # sync command
    sync_parser = subparsers.add_parser("sync", help="Sync skills from source")
    sync_parser.add_argument("source_dir", type=Path)
    sync_parser.add_argument("--dry-run", action="store_true")
    sync_parser.add_argument("--pattern", help="Filter skills by name pattern")

    args = parser.parse_args()

    try:
        installer = OpenCodeSkillInstaller(target_dir=args.target, verbose=args.verbose)
    except RuntimeError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

    if args.command == "install":
        success, msg = installer.install(args.source, force=args.force)
        if success:
            print(f"✅ {msg}")
            print("\n⚠️  Restart OpenCode to pick up new skills.")
        else:
            print(f"❌ {msg}")
            sys.exit(1)

    elif args.command == "uninstall":
        success, msg = installer.uninstall(args.skill_name)
        if success:
            print(f"✅ {msg}")
        else:
            print(f"❌ {msg}")
            sys.exit(1)

    elif args.command == "list":
        if args.source:
            skills = installer.list_available(args.source)
            title = f"Available skills in {args.source}"
        else:
            skills = installer.list_installed()
            title = f"Installed skills in {installer.target_dir}"

        if args.json:
            print(json.dumps(skills, indent=2))
        else:
            print(f"\n📋 {title}:")
            print(f"   Total: {len(skills)}")
            print()
            for skill in skills:
                status = "✅" if skill.get("valid", True) else "⚠️"
                installed = " (installed)" if skill.get("installed") else ""
                desc = skill.get("description", "")[:50]
                print(f"   {status} {skill['name']}{installed}")
                if desc:
                    print(f"      {desc}...")

    elif args.command == "sync":
        results = installer.sync(
            args.source_dir, dry_run=args.dry_run, pattern=args.pattern
        )

        mode = "[DRY RUN] " if args.dry_run else ""
        print(f"\n📊 {mode}Sync results:")
        print(f"   ✅ Installed: {len(results['installed'])}")
        print(f"   ⏭️  Skipped: {len(results['skipped'])}")
        print(f"   ❌ Errors: {len(results['errors'])}")

        if results["installed"]:
            print("\n   Installed:")
            for item in results["installed"]:
                print(f"      - {item['name']}")

        if results["errors"]:
            print("\n   Errors:")
            for item in results["errors"]:
                print(f"      - {item['name']}: {item['error']}")

        if not args.dry_run and results["installed"]:
            print("\n⚠️  Restart OpenCode to pick up new skills.")


if __name__ == "__main__":
    main()
>>>>>>> Stashed changes
