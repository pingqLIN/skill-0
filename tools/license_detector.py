<<<<<<< Updated upstream
<<<<<<< Updated upstream
#!/usr/bin/env python3
"""
License Detector

Detects and parses software licenses from LICENSE files and content.
Supports SPDX license identifiers and common license patterns.

Usage:
    python license_detector.py detect <path>
    python license_detector.py validate <spdx_id>
    python license_detector.py check-compatibility <spdx_id>

Author: skill-0 project
Created: 2026-01-27
"""

import os
import re
import json
import argparse
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum


class LicenseCategory(Enum):
    """License categories for compatibility checking"""

    PERMISSIVE = "permissive"  # MIT, Apache, BSD, etc.
    WEAK_COPYLEFT = "weak_copyleft"  # LGPL, MPL
    STRONG_COPYLEFT = "strong_copyleft"  # GPL, AGPL
    PROPRIETARY = "proprietary"  # Proprietary, closed source
    RESTRICTED = "restricted"  # Non-commercial, etc.
    UNKNOWN = "unknown"


@dataclass
class LicenseInfo:
    """Detected license information"""

    spdx_id: str
    name: str
    category: LicenseCategory
    confidence: float  # 0-1
    source: str  # 'file', 'content', 'header', 'unknown'
    requires_attribution: bool
    commercial_allowed: bool
    modification_allowed: bool
    distribution_allowed: bool
    compatible_with_opencode: bool
    details: Dict[str, Any] = None

    def to_dict(self) -> dict:
        return {
            "spdx_id": self.spdx_id,
            "name": self.name,
            "category": self.category.value,
            "confidence": round(self.confidence, 2),
            "source": self.source,
            "requires_attribution": self.requires_attribution,
            "commercial_allowed": self.commercial_allowed,
            "modification_allowed": self.modification_allowed,
            "distribution_allowed": self.distribution_allowed,
            "compatible_with_opencode": self.compatible_with_opencode,
            "details": self.details or {},
        }


# License database with patterns and metadata
LICENSE_DATABASE: Dict[str, Dict[str, Any]] = {
    # Permissive licenses
    "MIT": {
        "name": "MIT License",
        "category": LicenseCategory.PERMISSIVE,
        "patterns": [
            r"MIT\s+License",
            r"Permission\s+is\s+hereby\s+granted,?\s+free\s+of\s+charge",
            r"The\s+MIT\s+License\s+\(MIT\)",
            r"SPDX-License-Identifier:\s*MIT",
        ],
        "requires_attribution": True,
        "commercial_allowed": True,
        "modification_allowed": True,
        "distribution_allowed": True,
        "compatible_with_opencode": True,
    },
    "Apache-2.0": {
        "name": "Apache License 2.0",
        "category": LicenseCategory.PERMISSIVE,
        "patterns": [
            r"Apache\s+License,?\s+Version\s+2\.0",
            r"Licensed\s+under\s+the\s+Apache\s+License",
            r"SPDX-License-Identifier:\s*Apache-2\.0",
        ],
        "requires_attribution": True,
        "commercial_allowed": True,
        "modification_allowed": True,
        "distribution_allowed": True,
        "compatible_with_opencode": True,
    },
    "BSD-2-Clause": {
        "name": "BSD 2-Clause License",
        "category": LicenseCategory.PERMISSIVE,
        "patterns": [
            r"BSD\s+2-Clause",
            r"Redistributions\s+of\s+source\s+code\s+must\s+retain",
            r"Simplified\s+BSD\s+License",
        ],
        "requires_attribution": True,
        "commercial_allowed": True,
        "modification_allowed": True,
        "distribution_allowed": True,
        "compatible_with_opencode": True,
    },
    "BSD-3-Clause": {
        "name": "BSD 3-Clause License",
        "category": LicenseCategory.PERMISSIVE,
        "patterns": [
            r"BSD\s+3-Clause",
            r"Neither\s+the\s+name\s+of.*nor\s+the\s+names\s+of\s+its\s+contributors",
        ],
        "requires_attribution": True,
        "commercial_allowed": True,
        "modification_allowed": True,
        "distribution_allowed": True,
        "compatible_with_opencode": True,
    },
    "ISC": {
        "name": "ISC License",
        "category": LicenseCategory.PERMISSIVE,
        "patterns": [
            r"ISC\s+License",
            r"Permission\s+to\s+use,?\s+copy,?\s+modify,?\s+and/or\s+distribute",
            r"SPDX-License-Identifier:\s*ISC",
        ],
        "requires_attribution": True,
        "commercial_allowed": True,
        "modification_allowed": True,
        "distribution_allowed": True,
        "compatible_with_opencode": True,
    },
    "Unlicense": {
        "name": "The Unlicense",
        "category": LicenseCategory.PERMISSIVE,
        "patterns": [
            r"This\s+is\s+free\s+and\s+unencumbered\s+software",
            r"THE\s+UNLICENSE",
            r"released\s+into\s+the\s+public\s+domain",
        ],
        "requires_attribution": False,
        "commercial_allowed": True,
        "modification_allowed": True,
        "distribution_allowed": True,
        "compatible_with_opencode": True,
    },
    "CC0-1.0": {
        "name": "Creative Commons Zero v1.0 Universal",
        "category": LicenseCategory.PERMISSIVE,
        "patterns": [
            r"CC0\s+1\.0",
            r"Creative\s+Commons\s+Zero",
            r"No\s+Copyright",
        ],
        "requires_attribution": False,
        "commercial_allowed": True,
        "modification_allowed": True,
        "distribution_allowed": True,
        "compatible_with_opencode": True,
    },
    "WTFPL": {
        "name": "Do What The F*ck You Want To Public License",
        "category": LicenseCategory.PERMISSIVE,
        "patterns": [
            r"WTFPL",
            r"DO\s+WHAT\s+THE\s+FUCK\s+YOU\s+WANT\s+TO",
            r"Sam\s+Hocevar",
        ],
        "requires_attribution": False,
        "commercial_allowed": True,
        "modification_allowed": True,
        "distribution_allowed": True,
        "compatible_with_opencode": True,
    },
    # Weak copyleft
    "LGPL-2.1": {
        "name": "GNU Lesser General Public License v2.1",
        "category": LicenseCategory.WEAK_COPYLEFT,
        "patterns": [
            r"GNU\s+Lesser\s+General\s+Public\s+License.*2\.1",
            r"LGPL-2\.1",
        ],
        "requires_attribution": True,
        "commercial_allowed": True,
        "modification_allowed": True,
        "distribution_allowed": True,
        "compatible_with_opencode": True,  # Weak copyleft OK for skills
    },
    "LGPL-3.0": {
        "name": "GNU Lesser General Public License v3.0",
        "category": LicenseCategory.WEAK_COPYLEFT,
        "patterns": [
            r"GNU\s+Lesser\s+General\s+Public\s+License.*3\.0",
            r"LGPL-3\.0",
        ],
        "requires_attribution": True,
        "commercial_allowed": True,
        "modification_allowed": True,
        "distribution_allowed": True,
        "compatible_with_opencode": True,
    },
    "MPL-2.0": {
        "name": "Mozilla Public License 2.0",
        "category": LicenseCategory.WEAK_COPYLEFT,
        "patterns": [
            r"Mozilla\s+Public\s+License.*2\.0",
            r"MPL-2\.0",
        ],
        "requires_attribution": True,
        "commercial_allowed": True,
        "modification_allowed": True,
        "distribution_allowed": True,
        "compatible_with_opencode": True,
    },
    # Strong copyleft (requires review)
    "GPL-2.0": {
        "name": "GNU General Public License v2.0",
        "category": LicenseCategory.STRONG_COPYLEFT,
        "patterns": [
            r"GNU\s+General\s+Public\s+License.*(?:version\s+)?2",
            r"GPL-2\.0",
            r"GPLv2",
        ],
        "requires_attribution": True,
        "commercial_allowed": True,
        "modification_allowed": True,
        "distribution_allowed": True,
        "compatible_with_opencode": False,  # Requires review
    },
    "GPL-3.0": {
        "name": "GNU General Public License v3.0",
        "category": LicenseCategory.STRONG_COPYLEFT,
        "patterns": [
            r"GNU\s+General\s+Public\s+License.*(?:version\s+)?3",
            r"GPL-3\.0",
            r"GPLv3",
        ],
        "requires_attribution": True,
        "commercial_allowed": True,
        "modification_allowed": True,
        "distribution_allowed": True,
        "compatible_with_opencode": False,
    },
    "AGPL-3.0": {
        "name": "GNU Affero General Public License v3.0",
        "category": LicenseCategory.STRONG_COPYLEFT,
        "patterns": [
            r"GNU\s+Affero\s+General\s+Public\s+License",
            r"AGPL-3\.0",
        ],
        "requires_attribution": True,
        "commercial_allowed": True,
        "modification_allowed": True,
        "distribution_allowed": True,
        "compatible_with_opencode": False,
    },
    # Restricted licenses
    "BUSL-1.1": {
        "name": "Business Source License 1.1",
        "category": LicenseCategory.RESTRICTED,
        "patterns": [
            r"Business\s+Source\s+License",
            r"BUSL-1\.1",
        ],
        "requires_attribution": True,
        "commercial_allowed": False,
        "modification_allowed": True,
        "distribution_allowed": True,
        "compatible_with_opencode": False,
    },
    "CC-BY-NC-4.0": {
        "name": "Creative Commons Attribution-NonCommercial 4.0",
        "category": LicenseCategory.RESTRICTED,
        "patterns": [
            r"CC-BY-NC",
            r"Creative\s+Commons.*NonCommercial",
            r"Attribution-NonCommercial",
        ],
        "requires_attribution": True,
        "commercial_allowed": False,
        "modification_allowed": True,
        "distribution_allowed": True,
        "compatible_with_opencode": False,
    },
    "PROPRIETARY": {
        "name": "Proprietary License",
        "category": LicenseCategory.PROPRIETARY,
        "patterns": [
            r"All\s+rights\s+reserved",
            r"Proprietary",
            r"Copyright.*All\s+rights\s+reserved",
        ],
        "requires_attribution": True,
        "commercial_allowed": False,
        "modification_allowed": False,
        "distribution_allowed": False,
        "compatible_with_opencode": False,
    },
}


class LicenseDetector:
    """Detect and analyze software licenses"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.license_db = LICENSE_DATABASE

    def log(self, msg: str):
        if self.verbose:
            print(f"[license] {msg}")

    def detect(self, path: Path) -> LicenseInfo:
        """Detect license from a file or directory"""
        path = Path(path)

        if path.is_file():
            return self._detect_from_file(path)
        elif path.is_dir():
            return self._detect_from_directory(path)
        else:
            return self._unknown_license()

    def _detect_from_directory(self, directory: Path) -> LicenseInfo:
        """Look for LICENSE files in directory"""
        license_files = [
            "LICENSE",
            "LICENSE.txt",
            "LICENSE.md",
            "LICENCE",
            "LICENCE.txt",
            "LICENCE.md",
            "COPYING",
            "COPYING.txt",
        ]

        for filename in license_files:
            license_path = directory / filename
            if license_path.exists():
                self.log(f"Found license file: {license_path}")
                return self._detect_from_file(license_path)

        # Also check for SPDX headers in main files
        for pattern in ["*.md", "*.txt"]:
            for file_path in directory.glob(pattern):
                info = self._check_spdx_header(file_path)
                if info and info.spdx_id != "UNKNOWN":
                    return info

        return self._unknown_license()

    def _detect_from_file(self, file_path: Path) -> LicenseInfo:
        """Detect license from file content"""
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            self.log(f"Error reading {file_path}: {e}")
            return self._unknown_license()

        return self._detect_from_content(content, source="file")

    def _detect_from_content(
        self, content: str, source: str = "content"
    ) -> LicenseInfo:
        """Detect license from text content"""
        # Check for SPDX identifier first
        spdx_match = re.search(r"SPDX-License-Identifier:\s*(\S+)", content)
        if spdx_match:
            spdx_id = spdx_match.group(1).strip()
            if spdx_id in self.license_db:
                self.log(f"Found SPDX identifier: {spdx_id}")
                return self._create_license_info(
                    spdx_id, confidence=1.0, source="spdx_header"
                )

        # Match against known patterns
        best_match = None
        best_confidence = 0.0

        for spdx_id, info in self.license_db.items():
            for pattern in info["patterns"]:
                if re.search(pattern, content, re.IGNORECASE):
                    # Calculate confidence based on pattern specificity
                    confidence = min(0.9, 0.5 + len(pattern) / 200)

                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = spdx_id

        if best_match:
            self.log(
                f"Matched license: {best_match} (confidence: {best_confidence:.2f})"
            )
            return self._create_license_info(
                best_match, confidence=best_confidence, source=source
            )

        return self._unknown_license(source=source)

    def _check_spdx_header(self, file_path: Path) -> Optional[LicenseInfo]:
        """Check for SPDX identifier in file header"""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                # Read first 50 lines
                header = "".join(f.readline() for _ in range(50))
        except Exception:
            return None

        spdx_match = re.search(r"SPDX-License-Identifier:\s*(\S+)", header)
        if spdx_match:
            spdx_id = spdx_match.group(1).strip()
            if spdx_id in self.license_db:
                return self._create_license_info(
                    spdx_id, confidence=1.0, source="spdx_header"
                )

        return None

    def _create_license_info(
        self,
        spdx_id: str,
        confidence: float = 1.0,
        source: str = "unknown",
    ) -> LicenseInfo:
        """Create LicenseInfo from database entry"""
        info = self.license_db.get(spdx_id, {})

        return LicenseInfo(
            spdx_id=spdx_id,
            name=info.get("name", spdx_id),
            category=info.get("category", LicenseCategory.UNKNOWN),
            confidence=confidence,
            source=source,
            requires_attribution=info.get("requires_attribution", True),
            commercial_allowed=info.get("commercial_allowed", False),
            modification_allowed=info.get("modification_allowed", False),
            distribution_allowed=info.get("distribution_allowed", False),
            compatible_with_opencode=info.get("compatible_with_opencode", False),
        )

    def _unknown_license(self, source: str = "unknown") -> LicenseInfo:
        """Return unknown license info"""
        return LicenseInfo(
            spdx_id="UNKNOWN",
            name="Unknown License",
            category=LicenseCategory.UNKNOWN,
            confidence=0.0,
            source=source,
            requires_attribution=True,
            commercial_allowed=False,
            modification_allowed=False,
            distribution_allowed=False,
            compatible_with_opencode=False,
        )

    def validate_spdx(self, spdx_id: str) -> Tuple[bool, str]:
        """Validate if SPDX identifier is known"""
        if spdx_id in self.license_db:
            return True, f"Valid SPDX identifier: {self.license_db[spdx_id]['name']}"
        elif spdx_id == "UNKNOWN":
            return False, "Unknown license"
        else:
            return False, f"Unrecognized SPDX identifier: {spdx_id}"

    def check_compatibility(self, spdx_id: str) -> Dict[str, Any]:
        """Check license compatibility with OpenCode"""
        if spdx_id not in self.license_db:
            return {
                "spdx_id": spdx_id,
                "compatible": False,
                "reason": "Unknown license",
                "recommendation": "manual_review",
            }

        info = self.license_db[spdx_id]
        category = info["category"]

        if info["compatible_with_opencode"]:
            return {
                "spdx_id": spdx_id,
                "compatible": True,
                "reason": f"{info['name']} is compatible with OpenCode",
                "recommendation": "auto_approve",
            }
        elif category == LicenseCategory.STRONG_COPYLEFT:
            return {
                "spdx_id": spdx_id,
                "compatible": False,
                "reason": f"{info['name']} has strong copyleft requirements",
                "recommendation": "review_required",
            }
        elif category == LicenseCategory.RESTRICTED:
            return {
                "spdx_id": spdx_id,
                "compatible": False,
                "reason": f"{info['name']} has usage restrictions",
                "recommendation": "reject",
            }
        elif category == LicenseCategory.PROPRIETARY:
            return {
                "spdx_id": spdx_id,
                "compatible": False,
                "reason": "Proprietary license - not allowed",
                "recommendation": "reject",
            }
        else:
            return {
                "spdx_id": spdx_id,
                "compatible": False,
                "reason": "Unknown compatibility",
                "recommendation": "manual_review",
            }


def main():
    parser = argparse.ArgumentParser(description="License Detector")
    parser.add_argument("-v", "--verbose", action="store_true")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # detect command
    detect_parser = subparsers.add_parser(
        "detect", help="Detect license from file or directory"
    )
    detect_parser.add_argument("path", type=Path, help="File or directory path")
    detect_parser.add_argument("--format", choices=["text", "json"], default="text")

    # validate command
    validate_parser = subparsers.add_parser("validate", help="Validate SPDX identifier")
    validate_parser.add_argument("spdx_id", help="SPDX license identifier")

    # check-compatibility command
    compat_parser = subparsers.add_parser(
        "check-compatibility", help="Check license compatibility"
    )
    compat_parser.add_argument("spdx_id", help="SPDX license identifier")
    compat_parser.add_argument("--format", choices=["text", "json"], default="text")

    # list command
    list_parser = subparsers.add_parser("list", help="List known licenses")
    list_parser.add_argument("--category", help="Filter by category")
    list_parser.add_argument(
        "--compatible", action="store_true", help="Show only compatible"
    )

    args = parser.parse_args()
    detector = LicenseDetector(verbose=args.verbose)

    if args.command == "detect":
        info = detector.detect(args.path)

        if args.format == "json":
            print(json.dumps(info.to_dict(), indent=2))
        else:
            compat_icon = "✅" if info.compatible_with_opencode else "⚠️"
            conf_str = f"{info.confidence:.0%}" if info.confidence > 0 else "N/A"

            print(f"\n📄 License Detection Result")
            print(f"   Path: {args.path}")
            print(f"   SPDX ID: {info.spdx_id}")
            print(f"   Name: {info.name}")
            print(f"   Category: {info.category.value}")
            print(f"   Confidence: {conf_str}")
            print(f"   Source: {info.source}")
            print()
            print(
                f"   {compat_icon} Compatible with OpenCode: {info.compatible_with_opencode}"
            )
            print(f"   Requires Attribution: {info.requires_attribution}")
            print(f"   Commercial Use: {info.commercial_allowed}")
            print(f"   Modification: {info.modification_allowed}")

    elif args.command == "validate":
        valid, msg = detector.validate_spdx(args.spdx_id)
        icon = "✅" if valid else "❌"
        print(f"{icon} {msg}")

    elif args.command == "check-compatibility":
        result = detector.check_compatibility(args.spdx_id)

        if args.format == "json":
            print(json.dumps(result, indent=2))
        else:
            icon = "✅" if result["compatible"] else "❌"
            rec_icon = {
                "auto_approve": "✅",
                "review_required": "⚠️",
                "reject": "🚫",
                "manual_review": "❓",
            }.get(result["recommendation"], "❓")

            print(f"\n📜 License Compatibility Check")
            print(f"   SPDX ID: {result['spdx_id']}")
            print(f"   {icon} Compatible: {result['compatible']}")
            print(f"   Reason: {result['reason']}")
            print(f"   {rec_icon} Recommendation: {result['recommendation']}")

    elif args.command == "list":
        print("\n📋 Known Licenses:\n")

        for spdx_id, info in sorted(LICENSE_DATABASE.items()):
            category = info["category"].value

            if args.category and args.category != category:
                continue
            if args.compatible and not info["compatible_with_opencode"]:
                continue

            compat_icon = "✅" if info["compatible_with_opencode"] else "⚠️"
            print(f"  {compat_icon} {spdx_id:20} [{category:15}] {info['name']}")


if __name__ == "__main__":
    main()
=======
=======
>>>>>>> Stashed changes
#!/usr/bin/env python3
"""
License Detector

Detects and parses software licenses from LICENSE files and content.
Supports SPDX license identifiers and common license patterns.

Usage:
    python license_detector.py detect <path>
    python license_detector.py validate <spdx_id>
    python license_detector.py check-compatibility <spdx_id>

Author: skill-0 project
Created: 2026-01-27
"""

import os
import re
import json
import argparse
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum


class LicenseCategory(Enum):
    """License categories for compatibility checking"""

    PERMISSIVE = "permissive"  # MIT, Apache, BSD, etc.
    WEAK_COPYLEFT = "weak_copyleft"  # LGPL, MPL
    STRONG_COPYLEFT = "strong_copyleft"  # GPL, AGPL
    PROPRIETARY = "proprietary"  # Proprietary, closed source
    RESTRICTED = "restricted"  # Non-commercial, etc.
    UNKNOWN = "unknown"


@dataclass
class LicenseInfo:
    """Detected license information"""

    spdx_id: str
    name: str
    category: LicenseCategory
    confidence: float  # 0-1
    source: str  # 'file', 'content', 'header', 'unknown'
    requires_attribution: bool
    commercial_allowed: bool
    modification_allowed: bool
    distribution_allowed: bool
    compatible_with_opencode: bool
    details: Dict[str, Any] = None

    def to_dict(self) -> dict:
        return {
            "spdx_id": self.spdx_id,
            "name": self.name,
            "category": self.category.value,
            "confidence": round(self.confidence, 2),
            "source": self.source,
            "requires_attribution": self.requires_attribution,
            "commercial_allowed": self.commercial_allowed,
            "modification_allowed": self.modification_allowed,
            "distribution_allowed": self.distribution_allowed,
            "compatible_with_opencode": self.compatible_with_opencode,
            "details": self.details or {},
        }


# License database with patterns and metadata
LICENSE_DATABASE: Dict[str, Dict[str, Any]] = {
    # Permissive licenses
    "MIT": {
        "name": "MIT License",
        "category": LicenseCategory.PERMISSIVE,
        "patterns": [
            r"MIT\s+License",
            r"Permission\s+is\s+hereby\s+granted,?\s+free\s+of\s+charge",
            r"The\s+MIT\s+License\s+\(MIT\)",
            r"SPDX-License-Identifier:\s*MIT",
        ],
        "requires_attribution": True,
        "commercial_allowed": True,
        "modification_allowed": True,
        "distribution_allowed": True,
        "compatible_with_opencode": True,
    },
    "Apache-2.0": {
        "name": "Apache License 2.0",
        "category": LicenseCategory.PERMISSIVE,
        "patterns": [
            r"Apache\s+License,?\s+Version\s+2\.0",
            r"Licensed\s+under\s+the\s+Apache\s+License",
            r"SPDX-License-Identifier:\s*Apache-2\.0",
        ],
        "requires_attribution": True,
        "commercial_allowed": True,
        "modification_allowed": True,
        "distribution_allowed": True,
        "compatible_with_opencode": True,
    },
    "BSD-2-Clause": {
        "name": "BSD 2-Clause License",
        "category": LicenseCategory.PERMISSIVE,
        "patterns": [
            r"BSD\s+2-Clause",
            r"Redistributions\s+of\s+source\s+code\s+must\s+retain",
            r"Simplified\s+BSD\s+License",
        ],
        "requires_attribution": True,
        "commercial_allowed": True,
        "modification_allowed": True,
        "distribution_allowed": True,
        "compatible_with_opencode": True,
    },
    "BSD-3-Clause": {
        "name": "BSD 3-Clause License",
        "category": LicenseCategory.PERMISSIVE,
        "patterns": [
            r"BSD\s+3-Clause",
            r"Neither\s+the\s+name\s+of.*nor\s+the\s+names\s+of\s+its\s+contributors",
        ],
        "requires_attribution": True,
        "commercial_allowed": True,
        "modification_allowed": True,
        "distribution_allowed": True,
        "compatible_with_opencode": True,
    },
    "ISC": {
        "name": "ISC License",
        "category": LicenseCategory.PERMISSIVE,
        "patterns": [
            r"ISC\s+License",
            r"Permission\s+to\s+use,?\s+copy,?\s+modify,?\s+and/or\s+distribute",
            r"SPDX-License-Identifier:\s*ISC",
        ],
        "requires_attribution": True,
        "commercial_allowed": True,
        "modification_allowed": True,
        "distribution_allowed": True,
        "compatible_with_opencode": True,
    },
    "Unlicense": {
        "name": "The Unlicense",
        "category": LicenseCategory.PERMISSIVE,
        "patterns": [
            r"This\s+is\s+free\s+and\s+unencumbered\s+software",
            r"THE\s+UNLICENSE",
            r"released\s+into\s+the\s+public\s+domain",
        ],
        "requires_attribution": False,
        "commercial_allowed": True,
        "modification_allowed": True,
        "distribution_allowed": True,
        "compatible_with_opencode": True,
    },
    "CC0-1.0": {
        "name": "Creative Commons Zero v1.0 Universal",
        "category": LicenseCategory.PERMISSIVE,
        "patterns": [
            r"CC0\s+1\.0",
            r"Creative\s+Commons\s+Zero",
            r"No\s+Copyright",
        ],
        "requires_attribution": False,
        "commercial_allowed": True,
        "modification_allowed": True,
        "distribution_allowed": True,
        "compatible_with_opencode": True,
    },
    "WTFPL": {
        "name": "Do What The F*ck You Want To Public License",
        "category": LicenseCategory.PERMISSIVE,
        "patterns": [
            r"WTFPL",
            r"DO\s+WHAT\s+THE\s+FUCK\s+YOU\s+WANT\s+TO",
            r"Sam\s+Hocevar",
        ],
        "requires_attribution": False,
        "commercial_allowed": True,
        "modification_allowed": True,
        "distribution_allowed": True,
        "compatible_with_opencode": True,
    },
    # Weak copyleft
    "LGPL-2.1": {
        "name": "GNU Lesser General Public License v2.1",
        "category": LicenseCategory.WEAK_COPYLEFT,
        "patterns": [
            r"GNU\s+Lesser\s+General\s+Public\s+License.*2\.1",
            r"LGPL-2\.1",
        ],
        "requires_attribution": True,
        "commercial_allowed": True,
        "modification_allowed": True,
        "distribution_allowed": True,
        "compatible_with_opencode": True,  # Weak copyleft OK for skills
    },
    "LGPL-3.0": {
        "name": "GNU Lesser General Public License v3.0",
        "category": LicenseCategory.WEAK_COPYLEFT,
        "patterns": [
            r"GNU\s+Lesser\s+General\s+Public\s+License.*3\.0",
            r"LGPL-3\.0",
        ],
        "requires_attribution": True,
        "commercial_allowed": True,
        "modification_allowed": True,
        "distribution_allowed": True,
        "compatible_with_opencode": True,
    },
    "MPL-2.0": {
        "name": "Mozilla Public License 2.0",
        "category": LicenseCategory.WEAK_COPYLEFT,
        "patterns": [
            r"Mozilla\s+Public\s+License.*2\.0",
            r"MPL-2\.0",
        ],
        "requires_attribution": True,
        "commercial_allowed": True,
        "modification_allowed": True,
        "distribution_allowed": True,
        "compatible_with_opencode": True,
    },
    # Strong copyleft (requires review)
    "GPL-2.0": {
        "name": "GNU General Public License v2.0",
        "category": LicenseCategory.STRONG_COPYLEFT,
        "patterns": [
            r"GNU\s+General\s+Public\s+License.*(?:version\s+)?2",
            r"GPL-2\.0",
            r"GPLv2",
        ],
        "requires_attribution": True,
        "commercial_allowed": True,
        "modification_allowed": True,
        "distribution_allowed": True,
        "compatible_with_opencode": False,  # Requires review
    },
    "GPL-3.0": {
        "name": "GNU General Public License v3.0",
        "category": LicenseCategory.STRONG_COPYLEFT,
        "patterns": [
            r"GNU\s+General\s+Public\s+License.*(?:version\s+)?3",
            r"GPL-3\.0",
            r"GPLv3",
        ],
        "requires_attribution": True,
        "commercial_allowed": True,
        "modification_allowed": True,
        "distribution_allowed": True,
        "compatible_with_opencode": False,
    },
    "AGPL-3.0": {
        "name": "GNU Affero General Public License v3.0",
        "category": LicenseCategory.STRONG_COPYLEFT,
        "patterns": [
            r"GNU\s+Affero\s+General\s+Public\s+License",
            r"AGPL-3\.0",
        ],
        "requires_attribution": True,
        "commercial_allowed": True,
        "modification_allowed": True,
        "distribution_allowed": True,
        "compatible_with_opencode": False,
    },
    # Restricted licenses
    "BUSL-1.1": {
        "name": "Business Source License 1.1",
        "category": LicenseCategory.RESTRICTED,
        "patterns": [
            r"Business\s+Source\s+License",
            r"BUSL-1\.1",
        ],
        "requires_attribution": True,
        "commercial_allowed": False,
        "modification_allowed": True,
        "distribution_allowed": True,
        "compatible_with_opencode": False,
    },
    "CC-BY-NC-4.0": {
        "name": "Creative Commons Attribution-NonCommercial 4.0",
        "category": LicenseCategory.RESTRICTED,
        "patterns": [
            r"CC-BY-NC",
            r"Creative\s+Commons.*NonCommercial",
            r"Attribution-NonCommercial",
        ],
        "requires_attribution": True,
        "commercial_allowed": False,
        "modification_allowed": True,
        "distribution_allowed": True,
        "compatible_with_opencode": False,
    },
    "PROPRIETARY": {
        "name": "Proprietary License",
        "category": LicenseCategory.PROPRIETARY,
        "patterns": [
            r"All\s+rights\s+reserved",
            r"Proprietary",
            r"Copyright.*All\s+rights\s+reserved",
        ],
        "requires_attribution": True,
        "commercial_allowed": False,
        "modification_allowed": False,
        "distribution_allowed": False,
        "compatible_with_opencode": False,
    },
}


class LicenseDetector:
    """Detect and analyze software licenses"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.license_db = LICENSE_DATABASE

    def log(self, msg: str):
        if self.verbose:
            print(f"[license] {msg}")

    def detect(self, path: Path) -> LicenseInfo:
        """Detect license from a file or directory"""
        path = Path(path)

        if path.is_file():
            return self._detect_from_file(path)
        elif path.is_dir():
            return self._detect_from_directory(path)
        else:
            return self._unknown_license()

    def _detect_from_directory(self, directory: Path) -> LicenseInfo:
        """Look for LICENSE files in directory"""
        license_files = [
            "LICENSE",
            "LICENSE.txt",
            "LICENSE.md",
            "LICENCE",
            "LICENCE.txt",
            "LICENCE.md",
            "COPYING",
            "COPYING.txt",
        ]

        for filename in license_files:
            license_path = directory / filename
            if license_path.exists():
                self.log(f"Found license file: {license_path}")
                return self._detect_from_file(license_path)

        # Also check for SPDX headers in main files
        for pattern in ["*.md", "*.txt"]:
            for file_path in directory.glob(pattern):
                info = self._check_spdx_header(file_path)
                if info and info.spdx_id != "UNKNOWN":
                    return info

        return self._unknown_license()

    def _detect_from_file(self, file_path: Path) -> LicenseInfo:
        """Detect license from file content"""
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            self.log(f"Error reading {file_path}: {e}")
            return self._unknown_license()

        return self._detect_from_content(content, source="file")

    def _detect_from_content(
        self, content: str, source: str = "content"
    ) -> LicenseInfo:
        """Detect license from text content"""
        # Check for SPDX identifier first
        spdx_match = re.search(r"SPDX-License-Identifier:\s*(\S+)", content)
        if spdx_match:
            spdx_id = spdx_match.group(1).strip()
            if spdx_id in self.license_db:
                self.log(f"Found SPDX identifier: {spdx_id}")
                return self._create_license_info(
                    spdx_id, confidence=1.0, source="spdx_header"
                )

        # Match against known patterns
        best_match = None
        best_confidence = 0.0

        for spdx_id, info in self.license_db.items():
            for pattern in info["patterns"]:
                if re.search(pattern, content, re.IGNORECASE):
                    # Calculate confidence based on pattern specificity
                    confidence = min(0.9, 0.5 + len(pattern) / 200)

                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = spdx_id

        if best_match:
            self.log(
                f"Matched license: {best_match} (confidence: {best_confidence:.2f})"
            )
            return self._create_license_info(
                best_match, confidence=best_confidence, source=source
            )

        return self._unknown_license(source=source)

    def _check_spdx_header(self, file_path: Path) -> Optional[LicenseInfo]:
        """Check for SPDX identifier in file header"""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                # Read first 50 lines
                header = "".join(f.readline() for _ in range(50))
        except Exception:
            return None

        spdx_match = re.search(r"SPDX-License-Identifier:\s*(\S+)", header)
        if spdx_match:
            spdx_id = spdx_match.group(1).strip()
            if spdx_id in self.license_db:
                return self._create_license_info(
                    spdx_id, confidence=1.0, source="spdx_header"
                )

        return None

    def _create_license_info(
        self,
        spdx_id: str,
        confidence: float = 1.0,
        source: str = "unknown",
    ) -> LicenseInfo:
        """Create LicenseInfo from database entry"""
        info = self.license_db.get(spdx_id, {})

        return LicenseInfo(
            spdx_id=spdx_id,
            name=info.get("name", spdx_id),
            category=info.get("category", LicenseCategory.UNKNOWN),
            confidence=confidence,
            source=source,
            requires_attribution=info.get("requires_attribution", True),
            commercial_allowed=info.get("commercial_allowed", False),
            modification_allowed=info.get("modification_allowed", False),
            distribution_allowed=info.get("distribution_allowed", False),
            compatible_with_opencode=info.get("compatible_with_opencode", False),
        )

    def _unknown_license(self, source: str = "unknown") -> LicenseInfo:
        """Return unknown license info"""
        return LicenseInfo(
            spdx_id="UNKNOWN",
            name="Unknown License",
            category=LicenseCategory.UNKNOWN,
            confidence=0.0,
            source=source,
            requires_attribution=True,
            commercial_allowed=False,
            modification_allowed=False,
            distribution_allowed=False,
            compatible_with_opencode=False,
        )

    def validate_spdx(self, spdx_id: str) -> Tuple[bool, str]:
        """Validate if SPDX identifier is known"""
        if spdx_id in self.license_db:
            return True, f"Valid SPDX identifier: {self.license_db[spdx_id]['name']}"
        elif spdx_id == "UNKNOWN":
            return False, "Unknown license"
        else:
            return False, f"Unrecognized SPDX identifier: {spdx_id}"

    def check_compatibility(self, spdx_id: str) -> Dict[str, Any]:
        """Check license compatibility with OpenCode"""
        if spdx_id not in self.license_db:
            return {
                "spdx_id": spdx_id,
                "compatible": False,
                "reason": "Unknown license",
                "recommendation": "manual_review",
            }

        info = self.license_db[spdx_id]
        category = info["category"]

        if info["compatible_with_opencode"]:
            return {
                "spdx_id": spdx_id,
                "compatible": True,
                "reason": f"{info['name']} is compatible with OpenCode",
                "recommendation": "auto_approve",
            }
        elif category == LicenseCategory.STRONG_COPYLEFT:
            return {
                "spdx_id": spdx_id,
                "compatible": False,
                "reason": f"{info['name']} has strong copyleft requirements",
                "recommendation": "review_required",
            }
        elif category == LicenseCategory.RESTRICTED:
            return {
                "spdx_id": spdx_id,
                "compatible": False,
                "reason": f"{info['name']} has usage restrictions",
                "recommendation": "reject",
            }
        elif category == LicenseCategory.PROPRIETARY:
            return {
                "spdx_id": spdx_id,
                "compatible": False,
                "reason": "Proprietary license - not allowed",
                "recommendation": "reject",
            }
        else:
            return {
                "spdx_id": spdx_id,
                "compatible": False,
                "reason": "Unknown compatibility",
                "recommendation": "manual_review",
            }


def main():
    parser = argparse.ArgumentParser(description="License Detector")
    parser.add_argument("-v", "--verbose", action="store_true")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # detect command
    detect_parser = subparsers.add_parser(
        "detect", help="Detect license from file or directory"
    )
    detect_parser.add_argument("path", type=Path, help="File or directory path")
    detect_parser.add_argument("--format", choices=["text", "json"], default="text")

    # validate command
    validate_parser = subparsers.add_parser("validate", help="Validate SPDX identifier")
    validate_parser.add_argument("spdx_id", help="SPDX license identifier")

    # check-compatibility command
    compat_parser = subparsers.add_parser(
        "check-compatibility", help="Check license compatibility"
    )
    compat_parser.add_argument("spdx_id", help="SPDX license identifier")
    compat_parser.add_argument("--format", choices=["text", "json"], default="text")

    # list command
    list_parser = subparsers.add_parser("list", help="List known licenses")
    list_parser.add_argument("--category", help="Filter by category")
    list_parser.add_argument(
        "--compatible", action="store_true", help="Show only compatible"
    )

    args = parser.parse_args()
    detector = LicenseDetector(verbose=args.verbose)

    if args.command == "detect":
        info = detector.detect(args.path)

        if args.format == "json":
            print(json.dumps(info.to_dict(), indent=2))
        else:
            compat_icon = "✅" if info.compatible_with_opencode else "⚠️"
            conf_str = f"{info.confidence:.0%}" if info.confidence > 0 else "N/A"

            print(f"\n📄 License Detection Result")
            print(f"   Path: {args.path}")
            print(f"   SPDX ID: {info.spdx_id}")
            print(f"   Name: {info.name}")
            print(f"   Category: {info.category.value}")
            print(f"   Confidence: {conf_str}")
            print(f"   Source: {info.source}")
            print()
            print(
                f"   {compat_icon} Compatible with OpenCode: {info.compatible_with_opencode}"
            )
            print(f"   Requires Attribution: {info.requires_attribution}")
            print(f"   Commercial Use: {info.commercial_allowed}")
            print(f"   Modification: {info.modification_allowed}")

    elif args.command == "validate":
        valid, msg = detector.validate_spdx(args.spdx_id)
        icon = "✅" if valid else "❌"
        print(f"{icon} {msg}")

    elif args.command == "check-compatibility":
        result = detector.check_compatibility(args.spdx_id)

        if args.format == "json":
            print(json.dumps(result, indent=2))
        else:
            icon = "✅" if result["compatible"] else "❌"
            rec_icon = {
                "auto_approve": "✅",
                "review_required": "⚠️",
                "reject": "🚫",
                "manual_review": "❓",
            }.get(result["recommendation"], "❓")

            print(f"\n📜 License Compatibility Check")
            print(f"   SPDX ID: {result['spdx_id']}")
            print(f"   {icon} Compatible: {result['compatible']}")
            print(f"   Reason: {result['reason']}")
            print(f"   {rec_icon} Recommendation: {result['recommendation']}")

    elif args.command == "list":
        print("\n📋 Known Licenses:\n")

        for spdx_id, info in sorted(LICENSE_DATABASE.items()):
            category = info["category"].value

            if args.category and args.category != category:
                continue
            if args.compatible and not info["compatible_with_opencode"]:
                continue

            compat_icon = "✅" if info["compatible_with_opencode"] else "⚠️"
            print(f"  {compat_icon} {spdx_id:20} [{category:15}] {info['name']}")


if __name__ == "__main__":
    main()
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
