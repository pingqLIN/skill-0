<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
#!/usr/bin/env python3
"""
Skill Equivalence Tester

Tests conversion equivalence between original and converted skills.
Uses semantic similarity, structure comparison, and keyword preservation.

Usage:
    python skill_tester.py test <original_path> <converted_path>
    python skill_tester.py batch <original_dir> <converted_dir>
    python skill_tester.py report <original_path> <converted_path> --format json|text

Requirements:
    pip install sentence-transformers scikit-learn

Author: skill-0 project
Created: 2026-01-27
"""

import os
import re
import sys
import json
import argparse
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from collections import Counter
import hashlib


# Try to import ML libraries (optional for basic functionality)
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np

    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


@dataclass
class EquivalenceResult:
    """Result of equivalence testing"""

    original_path: str
    converted_path: str
    skill_name: str
    tested_at: str
    tester_version: str

    # Scores (0-1)
    semantic_similarity: float = 0.0
    structure_similarity: float = 0.0
    keyword_similarity: float = 0.0
    metadata_completeness: float = 0.0

    # Overall
    overall_score: float = 0.0
    passed: bool = False

    # Details
    details: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "original_path": self.original_path,
            "converted_path": self.converted_path,
            "skill_name": self.skill_name,
            "tested_at": self.tested_at,
            "tester_version": self.tester_version,
            "scores": {
                "semantic_similarity": round(self.semantic_similarity, 4),
                "structure_similarity": round(self.structure_similarity, 4),
                "keyword_similarity": round(self.keyword_similarity, 4),
                "metadata_completeness": round(self.metadata_completeness, 4),
                "overall": round(self.overall_score, 4),
            },
            "passed": self.passed,
            "details": self.details,
            "warnings": self.warnings,
            "errors": self.errors,
        }


class SkillEquivalenceTester:
    """Test equivalence between original and converted skills"""

    VERSION = "1.0.0"

    # Thresholds for pass/fail
    THRESHOLDS = {
        "semantic_similarity": 0.85,
        "structure_similarity": 0.80,
        "keyword_similarity": 0.75,
        "metadata_completeness": 0.90,
        "overall": 0.80,
    }

    # Score weights for overall calculation
    WEIGHTS = {
        "semantic_similarity": 0.35,
        "structure_similarity": 0.25,
        "keyword_similarity": 0.20,
        "metadata_completeness": 0.20,
    }

    def __init__(self, verbose: bool = False, model_name: str = "all-MiniLM-L6-v2"):
        self.verbose = verbose
        self.model_name = model_name
        self._model = None
        self._tfidf = None

    def log(self, msg: str):
        if self.verbose:
            print(f"[tester] {msg}")

    @property
    def model(self):
        """Lazy load the sentence transformer model"""
        if self._model is None and HAS_SENTENCE_TRANSFORMERS:
            self.log(f"Loading model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def extract_content(self, file_path: Path) -> str:
        """Read and normalize file content"""
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        return content

    def extract_frontmatter(self, content: str) -> Dict[str, Any]:
        """Extract YAML frontmatter from markdown"""
        if not content.startswith("---"):
            return {}

        try:
            # Find end of frontmatter
            end_idx = content.find("---", 3)
            if end_idx == -1:
                return {}

            frontmatter = content[3:end_idx].strip()

            # Simple YAML parsing (basic key: value)
            result = {}
            for line in frontmatter.split("\n"):
                if ":" in line:
                    key, _, value = line.partition(":")
                    key = key.strip()
                    value = value.strip().strip("'\"")
                    result[key] = value

            return result
        except Exception:
            return {}

    def extract_body(self, content: str) -> str:
        """Extract body (everything after frontmatter)"""
        if not content.startswith("---"):
            return content

        end_idx = content.find("---", 3)
        if end_idx == -1:
            return content

        return content[end_idx + 3 :].strip()

    def extract_headings(self, content: str) -> List[Tuple[int, str]]:
        """Extract markdown headings with their levels"""
        headings = []
        for line in content.split("\n"):
            match = re.match(r"^(#{1,6})\s+(.+)$", line.strip())
            if match:
                level = len(match.group(1))
                text = match.group(2).strip()
                headings.append((level, text))
        return headings

    def extract_code_blocks(self, content: str) -> List[Dict[str, str]]:
        """Extract code blocks with language info"""
        blocks = []
        pattern = r"```(\w*)\n(.*?)```"
        for match in re.finditer(pattern, content, re.DOTALL):
            blocks.append(
                {
                    "language": match.group(1) or "unknown",
                    "code": match.group(2).strip(),
                }
            )
        return blocks

    def extract_keywords(self, content: str) -> List[str]:
        """Extract significant keywords from content"""
        # Remove code blocks and URLs
        text = re.sub(r"```.*?```", " ", content, flags=re.DOTALL)
        text = re.sub(r"https?://\S+", " ", text)
        text = re.sub(r"`[^`]+`", " ", text)

        # Extract words
        words = re.findall(r"\b[a-zA-Z][a-zA-Z0-9_-]{2,}\b", text.lower())

        # Filter common words
        stopwords = {
            "the",
            "and",
            "for",
            "with",
            "that",
            "this",
            "from",
            "are",
            "was",
            "will",
            "have",
            "has",
            "been",
            "being",
            "can",
            "should",
            "would",
            "use",
            "using",
            "used",
            "when",
            "where",
            "what",
            "which",
            "who",
            "how",
            "why",
            "all",
            "any",
            "some",
            "each",
            "every",
            "other",
            "into",
            "over",
            "such",
            "than",
            "then",
            "here",
            "there",
            "your",
            "our",
            "their",
            "its",
            "not",
            "but",
            "also",
            "only",
            "just",
            "more",
            "most",
            "very",
            "well",
            "may",
            "must",
            "shall",
        }

        keywords = [w for w in words if w not in stopwords and len(w) > 2]
        return keywords

    def compute_semantic_similarity(self, text1: str, text2: str) -> float:
        """Compute semantic similarity using sentence transformers"""
        if not HAS_SENTENCE_TRANSFORMERS:
            self.log("Warning: sentence-transformers not available, using fallback")
            return self.compute_keyword_similarity(text1, text2)

        if self.model is None:
            return 0.0

        try:
            # Encode texts
            emb1 = self.model.encode(text1, normalize_embeddings=True)
            emb2 = self.model.encode(text2, normalize_embeddings=True)

            # Cosine similarity
            similarity = float(np.dot(emb1, emb2))
            return max(0.0, min(1.0, similarity))
        except Exception as e:
            self.log(f"Error computing semantic similarity: {e}")
            return 0.0

    def compute_structure_similarity(
        self,
        headings1: List[Tuple[int, str]],
        headings2: List[Tuple[int, str]],
        blocks1: List[Dict[str, str]],
        blocks2: List[Dict[str, str]],
    ) -> Tuple[float, Dict[str, Any]]:
        """Compute structural similarity"""
        details = {}

        # Heading structure
        if headings1 or headings2:
            # Compare heading levels distribution
            levels1 = Counter(h[0] for h in headings1)
            levels2 = Counter(h[0] for h in headings2)

            all_levels = set(levels1.keys()) | set(levels2.keys())
            if all_levels:
                level_sim = sum(
                    min(levels1.get(l, 0), levels2.get(l, 0)) for l in all_levels
                ) / max(sum(levels1.values()), sum(levels2.values()), 1)
            else:
                level_sim = 1.0

            # Compare heading text similarity
            texts1 = [h[1].lower() for h in headings1]
            texts2 = [h[1].lower() for h in headings2]

            if texts1 and texts2:
                common = sum(
                    1 for t in texts1 if any(t in t2 or t2 in t for t2 in texts2)
                )
                text_sim = common / max(len(texts1), len(texts2))
            else:
                text_sim = 0.5 if not texts1 and not texts2 else 0.0

            heading_sim = (level_sim + text_sim) / 2
            details["heading_similarity"] = round(heading_sim, 4)
        else:
            heading_sim = 1.0
            details["heading_similarity"] = 1.0

        # Code block structure
        if blocks1 or blocks2:
            # Compare number of code blocks
            count_sim = 1 - abs(len(blocks1) - len(blocks2)) / max(
                len(blocks1), len(blocks2), 1
            )

            # Compare language distribution
            langs1 = Counter(b["language"] for b in blocks1)
            langs2 = Counter(b["language"] for b in blocks2)

            all_langs = set(langs1.keys()) | set(langs2.keys())
            if all_langs:
                lang_sim = sum(
                    min(langs1.get(l, 0), langs2.get(l, 0)) for l in all_langs
                ) / max(sum(langs1.values()), sum(langs2.values()), 1)
            else:
                lang_sim = 1.0

            code_sim = (count_sim + lang_sim) / 2
            details["code_block_similarity"] = round(code_sim, 4)
        else:
            code_sim = 1.0
            details["code_block_similarity"] = 1.0

        # Overall structure
        overall = (heading_sim + code_sim) / 2
        return overall, details

    def compute_keyword_similarity(self, text1: str, text2: str) -> float:
        """Compute keyword overlap similarity"""
        kw1 = set(self.extract_keywords(text1))
        kw2 = set(self.extract_keywords(text2))

        if not kw1 and not kw2:
            return 1.0
        if not kw1 or not kw2:
            return 0.0

        # Jaccard similarity
        intersection = len(kw1 & kw2)
        union = len(kw1 | kw2)

        return intersection / union if union > 0 else 0.0

    def compute_tfidf_similarity(self, text1: str, text2: str) -> float:
        """Compute TF-IDF cosine similarity"""
        if not HAS_SKLEARN:
            return self.compute_keyword_similarity(text1, text2)

        try:
            vectorizer = TfidfVectorizer(
                lowercase=True,
                stop_words="english",
                ngram_range=(1, 2),
                max_features=1000,
            )
            tfidf = vectorizer.fit_transform([text1, text2])
            similarity = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]
            return float(similarity)
        except Exception as e:
            self.log(f"Error computing TF-IDF: {e}")
            return self.compute_keyword_similarity(text1, text2)

    def check_metadata_completeness(
        self,
        converted_frontmatter: Dict[str, Any],
        converted_path: Path,
    ) -> Tuple[float, Dict[str, Any]]:
        """Check if converted skill has complete metadata"""
        required_fields = ["name", "description"]
        recommended_fields = ["triggers", "globs"]

        details = {
            "required_present": [],
            "required_missing": [],
            "recommended_present": [],
            "recommended_missing": [],
        }

        # Check required
        for field in required_fields:
            if field in converted_frontmatter and converted_frontmatter[field]:
                details["required_present"].append(field)
            else:
                details["required_missing"].append(field)

        # Check recommended
        for field in recommended_fields:
            if field in converted_frontmatter and converted_frontmatter[field]:
                details["recommended_present"].append(field)
            else:
                details["recommended_missing"].append(field)

        # Calculate score
        required_score = (
            len(details["required_present"]) / len(required_fields)
            if required_fields
            else 1.0
        )
        recommended_score = (
            len(details["recommended_present"]) / len(recommended_fields)
            if recommended_fields
            else 1.0
        )

        # Required is more important
        score = required_score * 0.7 + recommended_score * 0.3

        return score, details

    def test_equivalence(
        self,
        original_path: Path,
        converted_path: Path,
    ) -> EquivalenceResult:
        """Test equivalence between original and converted skill"""
        original_path = Path(original_path)
        converted_path = Path(converted_path)

        # Find the main files
        if original_path.is_dir():
            # Look for .instructions.md or SKILL.md
            orig_file = None
            for pattern in ["*.instructions.md", "SKILL.md", "*.md"]:
                files = list(original_path.glob(pattern))
                if files:
                    orig_file = files[0]
                    break
            if not orig_file:
                raise FileNotFoundError(f"No skill file found in {original_path}")
            original_path = orig_file

        if converted_path.is_dir():
            conv_file = converted_path / "SKILL.md"
            if not conv_file.exists():
                files = list(converted_path.glob("*.md"))
                if files:
                    conv_file = files[0]
                else:
                    raise FileNotFoundError(f"No SKILL.md found in {converted_path}")
            converted_path = conv_file

        self.log(f"Testing: {original_path.name} vs {converted_path.name}")

        # Read content
        orig_content = self.extract_content(original_path)
        conv_content = self.extract_content(converted_path)

        # Extract components
        orig_frontmatter = self.extract_frontmatter(orig_content)
        conv_frontmatter = self.extract_frontmatter(conv_content)

        orig_body = self.extract_body(orig_content)
        conv_body = self.extract_body(conv_content)

        orig_headings = self.extract_headings(orig_body)
        conv_headings = self.extract_headings(conv_body)

        orig_blocks = self.extract_code_blocks(orig_body)
        conv_blocks = self.extract_code_blocks(conv_body)

        # Get skill name
        skill_name = conv_frontmatter.get("name", converted_path.parent.name)

        result = EquivalenceResult(
            original_path=str(original_path),
            converted_path=str(converted_path),
            skill_name=skill_name,
            tested_at=datetime.now().isoformat(),
            tester_version=self.VERSION,
        )

        # 1. Semantic Similarity
        self.log("  Computing semantic similarity...")
        result.semantic_similarity = self.compute_semantic_similarity(
            orig_body, conv_body
        )
        result.details["semantic"] = {
            "score": round(result.semantic_similarity, 4),
            "method": "sentence-transformers"
            if HAS_SENTENCE_TRANSFORMERS
            else "keyword-fallback",
        }

        # 2. Structure Similarity
        self.log("  Computing structure similarity...")
        result.structure_similarity, struct_details = self.compute_structure_similarity(
            orig_headings, conv_headings, orig_blocks, conv_blocks
        )
        result.details["structure"] = {
            "score": round(result.structure_similarity, 4),
            "original_headings": len(orig_headings),
            "converted_headings": len(conv_headings),
            "original_code_blocks": len(orig_blocks),
            "converted_code_blocks": len(conv_blocks),
            **struct_details,
        }

        # 3. Keyword Similarity
        self.log("  Computing keyword similarity...")
        if HAS_SKLEARN:
            result.keyword_similarity = self.compute_tfidf_similarity(
                orig_body, conv_body
            )
            method = "tfidf"
        else:
            result.keyword_similarity = self.compute_keyword_similarity(
                orig_body, conv_body
            )
            method = "jaccard"

        result.details["keywords"] = {
            "score": round(result.keyword_similarity, 4),
            "method": method,
        }

        # 4. Metadata Completeness
        self.log("  Checking metadata completeness...")
        result.metadata_completeness, meta_details = self.check_metadata_completeness(
            conv_frontmatter, converted_path
        )
        result.details["metadata"] = {
            "score": round(result.metadata_completeness, 4),
            **meta_details,
        }

        # Calculate overall score
        result.overall_score = (
            result.semantic_similarity * self.WEIGHTS["semantic_similarity"]
            + result.structure_similarity * self.WEIGHTS["structure_similarity"]
            + result.keyword_similarity * self.WEIGHTS["keyword_similarity"]
            + result.metadata_completeness * self.WEIGHTS["metadata_completeness"]
        )

        # Check thresholds
        checks = [
            ("semantic_similarity", result.semantic_similarity),
            ("structure_similarity", result.structure_similarity),
            ("keyword_similarity", result.keyword_similarity),
            ("metadata_completeness", result.metadata_completeness),
            ("overall", result.overall_score),
        ]

        failed_checks = []
        for name, value in checks:
            threshold = self.THRESHOLDS[name]
            if value < threshold:
                failed_checks.append(f"{name}: {value:.2%} < {threshold:.2%}")

        result.passed = len(failed_checks) == 0

        if failed_checks:
            result.warnings.extend(failed_checks)

        # Add warnings for missing recommended fields
        if meta_details.get("recommended_missing"):
            result.warnings.append(
                f"Missing recommended fields: {', '.join(meta_details['recommended_missing'])}"
            )

        # Add errors for missing required fields
        if meta_details.get("required_missing"):
            result.errors.append(
                f"Missing required fields: {', '.join(meta_details['required_missing'])}"
            )

        return result

    def batch_test(
        self,
        original_dir: Path,
        converted_dir: Path,
        match_by: str = "name",
    ) -> List[EquivalenceResult]:
        """Test all skills in directories"""
        results = []
        original_dir = Path(original_dir)
        converted_dir = Path(converted_dir)

        # Find converted skills
        converted_skills = {}
        for skill_md in converted_dir.glob("**/SKILL.md"):
            skill_dir = skill_md.parent
            content = skill_md.read_text(encoding="utf-8")
            fm = self.extract_frontmatter(content)
            name = fm.get("name", skill_dir.name)
            converted_skills[name.lower()] = skill_dir

        self.log(f"Found {len(converted_skills)} converted skills")

        # Find original skills and match
        for orig_file in original_dir.glob("**/*.instructions.md"):
            # Extract name from filename (e.g., "csharp.instructions.md" -> "csharp")
            name = orig_file.stem.replace(".instructions", "")

            # Try to match
            conv_dir = converted_skills.get(name.lower())

            if conv_dir:
                try:
                    result = self.test_equivalence(orig_file, conv_dir)
                    results.append(result)
                except Exception as e:
                    self.log(f"Error testing {name}: {e}")
            else:
                self.log(f"No converted skill found for: {name}")

        return results

    def format_report_text(self, result: EquivalenceResult) -> str:
        """Format result as human-readable text"""
        lines = []

        status = "✅ PASSED" if result.passed else "❌ FAILED"

        lines.append("=" * 60)
        lines.append(f"Equivalence Test Report: {result.skill_name}")
        lines.append("=" * 60)
        lines.append(f"Status: {status}")
        lines.append(f"Overall Score: {result.overall_score:.1%}")
        lines.append(f"Tested: {result.tested_at}")
        lines.append("")
        lines.append("--- Scores ---")
        lines.append(
            f"  Semantic Similarity:   {result.semantic_similarity:.1%} (threshold: {self.THRESHOLDS['semantic_similarity']:.0%})"
        )
        lines.append(
            f"  Structure Similarity:  {result.structure_similarity:.1%} (threshold: {self.THRESHOLDS['structure_similarity']:.0%})"
        )
        lines.append(
            f"  Keyword Similarity:    {result.keyword_similarity:.1%} (threshold: {self.THRESHOLDS['keyword_similarity']:.0%})"
        )
        lines.append(
            f"  Metadata Completeness: {result.metadata_completeness:.1%} (threshold: {self.THRESHOLDS['metadata_completeness']:.0%})"
        )

        if result.errors:
            lines.append("\n--- Errors ---")
            for error in result.errors:
                lines.append(f"  ❌ {error}")

        if result.warnings:
            lines.append("\n--- Warnings ---")
            for warning in result.warnings:
                lines.append(f"  ⚠️ {warning}")

        lines.append("\n--- Files ---")
        lines.append(f"  Original:  {result.original_path}")
        lines.append(f"  Converted: {result.converted_path}")

        lines.append("\n" + "=" * 60)
        return "\n".join(lines)

    def format_report_json(self, result: EquivalenceResult) -> str:
        """Format result as JSON"""
        return json.dumps(result.to_dict(), indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description="Skill Equivalence Tester")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument(
        "--model", default="all-MiniLM-L6-v2", help="Sentence transformer model"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # test command
    test_parser = subparsers.add_parser("test", help="Test equivalence of two skills")
    test_parser.add_argument("original", type=Path, help="Original skill path")
    test_parser.add_argument("converted", type=Path, help="Converted skill path")
    test_parser.add_argument("--format", choices=["text", "json"], default="text")

    # batch command
    batch_parser = subparsers.add_parser("batch", help="Test all skills in directories")
    batch_parser.add_argument(
        "original_dir", type=Path, help="Directory with original skills"
    )
    batch_parser.add_argument(
        "converted_dir", type=Path, help="Directory with converted skills"
    )
    batch_parser.add_argument("--format", choices=["text", "json"], default="text")
    batch_parser.add_argument("--output", type=Path, help="Output file")
    batch_parser.add_argument(
        "--failed-only", action="store_true", help="Show only failed tests"
    )

    # report command
    report_parser = subparsers.add_parser("report", help="Generate detailed report")
    report_parser.add_argument("original", type=Path)
    report_parser.add_argument("converted", type=Path)
    report_parser.add_argument("--format", choices=["text", "json"], default="text")
    report_parser.add_argument("--output", type=Path)

    args = parser.parse_args()
    tester = SkillEquivalenceTester(verbose=args.verbose, model_name=args.model)

    if args.command in ["test", "report"]:
        try:
            result = tester.test_equivalence(args.original, args.converted)

            if args.format == "json":
                output = tester.format_report_json(result)
            else:
                output = tester.format_report_text(result)

            if hasattr(args, "output") and args.output:
                args.output.write_text(output, encoding="utf-8")
                print(f"📄 Report saved to {args.output}")
            else:
                print(output)

            sys.exit(0 if result.passed else 1)

        except FileNotFoundError as e:
            print(f"❌ Error: {e}")
            sys.exit(1)

    elif args.command == "batch":
        results = tester.batch_test(args.original_dir, args.converted_dir)

        if args.failed_only:
            results = [r for r in results if not r.passed]

        if args.format == "json":
            output = json.dumps(
                [r.to_dict() for r in results], indent=2, ensure_ascii=False
            )
        else:
            passed = sum(1 for r in results if r.passed)
            failed = len(results) - passed

            lines = [
                f"\n📊 Batch Test Results",
                f"   Total:  {len(results)}",
                f"   Passed: {passed} ✅",
                f"   Failed: {failed} ❌",
                "",
            ]

            if failed > 0:
                lines.append("Failed tests:")
                for r in results:
                    if not r.passed:
                        lines.append(f"  ❌ {r.skill_name}: {r.overall_score:.1%}")
                        for w in r.warnings[:2]:
                            lines.append(f"     - {w}")

            output = "\n".join(lines)

        if args.output:
            args.output.write_text(output, encoding="utf-8")
            print(f"📄 Results saved to {args.output}")
        else:
            print(output)

        # Exit with error if any failed
        if any(not r.passed for r in results):
            sys.exit(1)


if __name__ == "__main__":
    main()
=======
=======
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
#!/usr/bin/env python3
"""
Skill Equivalence Tester

Tests conversion equivalence between original and converted skills.
Uses semantic similarity, structure comparison, and keyword preservation.

Usage:
    python skill_tester.py test <original_path> <converted_path>
    python skill_tester.py batch <original_dir> <converted_dir>
    python skill_tester.py report <original_path> <converted_path> --format json|text

Requirements:
    pip install sentence-transformers scikit-learn

Author: skill-0 project
Created: 2026-01-27
"""

import os
import re
import sys
import json
import argparse
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from collections import Counter
import hashlib


# Try to import ML libraries (optional for basic functionality)
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np

    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


@dataclass
class EquivalenceResult:
    """Result of equivalence testing"""

    original_path: str
    converted_path: str
    skill_name: str
    tested_at: str
    tester_version: str

    # Scores (0-1)
    semantic_similarity: float = 0.0
    structure_similarity: float = 0.0
    keyword_similarity: float = 0.0
    metadata_completeness: float = 0.0

    # Overall
    overall_score: float = 0.0
    passed: bool = False

    # Details
    details: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "original_path": self.original_path,
            "converted_path": self.converted_path,
            "skill_name": self.skill_name,
            "tested_at": self.tested_at,
            "tester_version": self.tester_version,
            "scores": {
                "semantic_similarity": round(self.semantic_similarity, 4),
                "structure_similarity": round(self.structure_similarity, 4),
                "keyword_similarity": round(self.keyword_similarity, 4),
                "metadata_completeness": round(self.metadata_completeness, 4),
                "overall": round(self.overall_score, 4),
            },
            "passed": self.passed,
            "details": self.details,
            "warnings": self.warnings,
            "errors": self.errors,
        }


class SkillEquivalenceTester:
    """Test equivalence between original and converted skills"""

    VERSION = "1.0.0"

    # Thresholds for pass/fail
    THRESHOLDS = {
        "semantic_similarity": 0.85,
        "structure_similarity": 0.80,
        "keyword_similarity": 0.75,
        "metadata_completeness": 0.90,
        "overall": 0.80,
    }

    # Score weights for overall calculation
    WEIGHTS = {
        "semantic_similarity": 0.35,
        "structure_similarity": 0.25,
        "keyword_similarity": 0.20,
        "metadata_completeness": 0.20,
    }

    def __init__(self, verbose: bool = False, model_name: str = "all-MiniLM-L6-v2"):
        self.verbose = verbose
        self.model_name = model_name
        self._model = None
        self._tfidf = None

    def log(self, msg: str):
        if self.verbose:
            print(f"[tester] {msg}")

    @property
    def model(self):
        """Lazy load the sentence transformer model"""
        if self._model is None and HAS_SENTENCE_TRANSFORMERS:
            self.log(f"Loading model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def extract_content(self, file_path: Path) -> str:
        """Read and normalize file content"""
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        return content

    def extract_frontmatter(self, content: str) -> Dict[str, Any]:
        """Extract YAML frontmatter from markdown"""
        if not content.startswith("---"):
            return {}

        try:
            # Find end of frontmatter
            end_idx = content.find("---", 3)
            if end_idx == -1:
                return {}

            frontmatter = content[3:end_idx].strip()

            # Simple YAML parsing (basic key: value)
            result = {}
            for line in frontmatter.split("\n"):
                if ":" in line:
                    key, _, value = line.partition(":")
                    key = key.strip()
                    value = value.strip().strip("'\"")
                    result[key] = value

            return result
        except Exception:
            return {}

    def extract_body(self, content: str) -> str:
        """Extract body (everything after frontmatter)"""
        if not content.startswith("---"):
            return content

        end_idx = content.find("---", 3)
        if end_idx == -1:
            return content

        return content[end_idx + 3 :].strip()

    def extract_headings(self, content: str) -> List[Tuple[int, str]]:
        """Extract markdown headings with their levels"""
        headings = []
        for line in content.split("\n"):
            match = re.match(r"^(#{1,6})\s+(.+)$", line.strip())
            if match:
                level = len(match.group(1))
                text = match.group(2).strip()
                headings.append((level, text))
        return headings

    def extract_code_blocks(self, content: str) -> List[Dict[str, str]]:
        """Extract code blocks with language info"""
        blocks = []
        pattern = r"```(\w*)\n(.*?)```"
        for match in re.finditer(pattern, content, re.DOTALL):
            blocks.append(
                {
                    "language": match.group(1) or "unknown",
                    "code": match.group(2).strip(),
                }
            )
        return blocks

    def extract_keywords(self, content: str) -> List[str]:
        """Extract significant keywords from content"""
        # Remove code blocks and URLs
        text = re.sub(r"```.*?```", " ", content, flags=re.DOTALL)
        text = re.sub(r"https?://\S+", " ", text)
        text = re.sub(r"`[^`]+`", " ", text)

        # Extract words
        words = re.findall(r"\b[a-zA-Z][a-zA-Z0-9_-]{2,}\b", text.lower())

        # Filter common words
        stopwords = {
            "the",
            "and",
            "for",
            "with",
            "that",
            "this",
            "from",
            "are",
            "was",
            "will",
            "have",
            "has",
            "been",
            "being",
            "can",
            "should",
            "would",
            "use",
            "using",
            "used",
            "when",
            "where",
            "what",
            "which",
            "who",
            "how",
            "why",
            "all",
            "any",
            "some",
            "each",
            "every",
            "other",
            "into",
            "over",
            "such",
            "than",
            "then",
            "here",
            "there",
            "your",
            "our",
            "their",
            "its",
            "not",
            "but",
            "also",
            "only",
            "just",
            "more",
            "most",
            "very",
            "well",
            "may",
            "must",
            "shall",
        }

        keywords = [w for w in words if w not in stopwords and len(w) > 2]
        return keywords

    def compute_semantic_similarity(self, text1: str, text2: str) -> float:
        """Compute semantic similarity using sentence transformers"""
        if not HAS_SENTENCE_TRANSFORMERS:
            self.log("Warning: sentence-transformers not available, using fallback")
            return self.compute_keyword_similarity(text1, text2)

        if self.model is None:
            return 0.0

        try:
            # Encode texts
            emb1 = self.model.encode(text1, normalize_embeddings=True)
            emb2 = self.model.encode(text2, normalize_embeddings=True)

            # Cosine similarity
            similarity = float(np.dot(emb1, emb2))
            return max(0.0, min(1.0, similarity))
        except Exception as e:
            self.log(f"Error computing semantic similarity: {e}")
            return 0.0

    def compute_structure_similarity(
        self,
        headings1: List[Tuple[int, str]],
        headings2: List[Tuple[int, str]],
        blocks1: List[Dict[str, str]],
        blocks2: List[Dict[str, str]],
    ) -> Tuple[float, Dict[str, Any]]:
        """Compute structural similarity"""
        details = {}

        # Heading structure
        if headings1 or headings2:
            # Compare heading levels distribution
            levels1 = Counter(h[0] for h in headings1)
            levels2 = Counter(h[0] for h in headings2)

            all_levels = set(levels1.keys()) | set(levels2.keys())
            if all_levels:
                level_sim = sum(
                    min(levels1.get(l, 0), levels2.get(l, 0)) for l in all_levels
                ) / max(sum(levels1.values()), sum(levels2.values()), 1)
            else:
                level_sim = 1.0

            # Compare heading text similarity
            texts1 = [h[1].lower() for h in headings1]
            texts2 = [h[1].lower() for h in headings2]

            if texts1 and texts2:
                common = sum(
                    1 for t in texts1 if any(t in t2 or t2 in t for t2 in texts2)
                )
                text_sim = common / max(len(texts1), len(texts2))
            else:
                text_sim = 0.5 if not texts1 and not texts2 else 0.0

            heading_sim = (level_sim + text_sim) / 2
            details["heading_similarity"] = round(heading_sim, 4)
        else:
            heading_sim = 1.0
            details["heading_similarity"] = 1.0

        # Code block structure
        if blocks1 or blocks2:
            # Compare number of code blocks
            count_sim = 1 - abs(len(blocks1) - len(blocks2)) / max(
                len(blocks1), len(blocks2), 1
            )

            # Compare language distribution
            langs1 = Counter(b["language"] for b in blocks1)
            langs2 = Counter(b["language"] for b in blocks2)

            all_langs = set(langs1.keys()) | set(langs2.keys())
            if all_langs:
                lang_sim = sum(
                    min(langs1.get(l, 0), langs2.get(l, 0)) for l in all_langs
                ) / max(sum(langs1.values()), sum(langs2.values()), 1)
            else:
                lang_sim = 1.0

            code_sim = (count_sim + lang_sim) / 2
            details["code_block_similarity"] = round(code_sim, 4)
        else:
            code_sim = 1.0
            details["code_block_similarity"] = 1.0

        # Overall structure
        overall = (heading_sim + code_sim) / 2
        return overall, details

    def compute_keyword_similarity(self, text1: str, text2: str) -> float:
        """Compute keyword overlap similarity"""
        kw1 = set(self.extract_keywords(text1))
        kw2 = set(self.extract_keywords(text2))

        if not kw1 and not kw2:
            return 1.0
        if not kw1 or not kw2:
            return 0.0

        # Jaccard similarity
        intersection = len(kw1 & kw2)
        union = len(kw1 | kw2)

        return intersection / union if union > 0 else 0.0

    def compute_tfidf_similarity(self, text1: str, text2: str) -> float:
        """Compute TF-IDF cosine similarity"""
        if not HAS_SKLEARN:
            return self.compute_keyword_similarity(text1, text2)

        try:
            vectorizer = TfidfVectorizer(
                lowercase=True,
                stop_words="english",
                ngram_range=(1, 2),
                max_features=1000,
            )
            tfidf = vectorizer.fit_transform([text1, text2])
            similarity = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]
            return float(similarity)
        except Exception as e:
            self.log(f"Error computing TF-IDF: {e}")
            return self.compute_keyword_similarity(text1, text2)

    def check_metadata_completeness(
        self,
        converted_frontmatter: Dict[str, Any],
        converted_path: Path,
    ) -> Tuple[float, Dict[str, Any]]:
        """Check if converted skill has complete metadata"""
        required_fields = ["name", "description"]
        recommended_fields = ["triggers", "globs"]

        details = {
            "required_present": [],
            "required_missing": [],
            "recommended_present": [],
            "recommended_missing": [],
        }

        # Check required
        for field in required_fields:
            if field in converted_frontmatter and converted_frontmatter[field]:
                details["required_present"].append(field)
            else:
                details["required_missing"].append(field)

        # Check recommended
        for field in recommended_fields:
            if field in converted_frontmatter and converted_frontmatter[field]:
                details["recommended_present"].append(field)
            else:
                details["recommended_missing"].append(field)

        # Calculate score
        required_score = (
            len(details["required_present"]) / len(required_fields)
            if required_fields
            else 1.0
        )
        recommended_score = (
            len(details["recommended_present"]) / len(recommended_fields)
            if recommended_fields
            else 1.0
        )

        # Required is more important
        score = required_score * 0.7 + recommended_score * 0.3

        return score, details

    def test_equivalence(
        self,
        original_path: Path,
        converted_path: Path,
    ) -> EquivalenceResult:
        """Test equivalence between original and converted skill"""
        original_path = Path(original_path)
        converted_path = Path(converted_path)

        # Find the main files
        if original_path.is_dir():
            # Look for .instructions.md or SKILL.md
            orig_file = None
            for pattern in ["*.instructions.md", "SKILL.md", "*.md"]:
                files = list(original_path.glob(pattern))
                if files:
                    orig_file = files[0]
                    break
            if not orig_file:
                raise FileNotFoundError(f"No skill file found in {original_path}")
            original_path = orig_file

        if converted_path.is_dir():
            conv_file = converted_path / "SKILL.md"
            if not conv_file.exists():
                files = list(converted_path.glob("*.md"))
                if files:
                    conv_file = files[0]
                else:
                    raise FileNotFoundError(f"No SKILL.md found in {converted_path}")
            converted_path = conv_file

        self.log(f"Testing: {original_path.name} vs {converted_path.name}")

        # Read content
        orig_content = self.extract_content(original_path)
        conv_content = self.extract_content(converted_path)

        # Extract components
        orig_frontmatter = self.extract_frontmatter(orig_content)
        conv_frontmatter = self.extract_frontmatter(conv_content)

        orig_body = self.extract_body(orig_content)
        conv_body = self.extract_body(conv_content)

        orig_headings = self.extract_headings(orig_body)
        conv_headings = self.extract_headings(conv_body)

        orig_blocks = self.extract_code_blocks(orig_body)
        conv_blocks = self.extract_code_blocks(conv_body)

        # Get skill name
        skill_name = conv_frontmatter.get("name", converted_path.parent.name)

        result = EquivalenceResult(
            original_path=str(original_path),
            converted_path=str(converted_path),
            skill_name=skill_name,
            tested_at=datetime.now().isoformat(),
            tester_version=self.VERSION,
        )

        # 1. Semantic Similarity
        self.log("  Computing semantic similarity...")
        result.semantic_similarity = self.compute_semantic_similarity(
            orig_body, conv_body
        )
        result.details["semantic"] = {
            "score": round(result.semantic_similarity, 4),
            "method": "sentence-transformers"
            if HAS_SENTENCE_TRANSFORMERS
            else "keyword-fallback",
        }

        # 2. Structure Similarity
        self.log("  Computing structure similarity...")
        result.structure_similarity, struct_details = self.compute_structure_similarity(
            orig_headings, conv_headings, orig_blocks, conv_blocks
        )
        result.details["structure"] = {
            "score": round(result.structure_similarity, 4),
            "original_headings": len(orig_headings),
            "converted_headings": len(conv_headings),
            "original_code_blocks": len(orig_blocks),
            "converted_code_blocks": len(conv_blocks),
            **struct_details,
        }

        # 3. Keyword Similarity
        self.log("  Computing keyword similarity...")
        if HAS_SKLEARN:
            result.keyword_similarity = self.compute_tfidf_similarity(
                orig_body, conv_body
            )
            method = "tfidf"
        else:
            result.keyword_similarity = self.compute_keyword_similarity(
                orig_body, conv_body
            )
            method = "jaccard"

        result.details["keywords"] = {
            "score": round(result.keyword_similarity, 4),
            "method": method,
        }

        # 4. Metadata Completeness
        self.log("  Checking metadata completeness...")
        result.metadata_completeness, meta_details = self.check_metadata_completeness(
            conv_frontmatter, converted_path
        )
        result.details["metadata"] = {
            "score": round(result.metadata_completeness, 4),
            **meta_details,
        }

        # Calculate overall score
        result.overall_score = (
            result.semantic_similarity * self.WEIGHTS["semantic_similarity"]
            + result.structure_similarity * self.WEIGHTS["structure_similarity"]
            + result.keyword_similarity * self.WEIGHTS["keyword_similarity"]
            + result.metadata_completeness * self.WEIGHTS["metadata_completeness"]
        )

        # Check thresholds
        checks = [
            ("semantic_similarity", result.semantic_similarity),
            ("structure_similarity", result.structure_similarity),
            ("keyword_similarity", result.keyword_similarity),
            ("metadata_completeness", result.metadata_completeness),
            ("overall", result.overall_score),
        ]

        failed_checks = []
        for name, value in checks:
            threshold = self.THRESHOLDS[name]
            if value < threshold:
                failed_checks.append(f"{name}: {value:.2%} < {threshold:.2%}")

        result.passed = len(failed_checks) == 0

        if failed_checks:
            result.warnings.extend(failed_checks)

        # Add warnings for missing recommended fields
        if meta_details.get("recommended_missing"):
            result.warnings.append(
                f"Missing recommended fields: {', '.join(meta_details['recommended_missing'])}"
            )

        # Add errors for missing required fields
        if meta_details.get("required_missing"):
            result.errors.append(
                f"Missing required fields: {', '.join(meta_details['required_missing'])}"
            )

        return result

    def batch_test(
        self,
        original_dir: Path,
        converted_dir: Path,
        match_by: str = "name",
    ) -> List[EquivalenceResult]:
        """Test all skills in directories"""
        results = []
        original_dir = Path(original_dir)
        converted_dir = Path(converted_dir)

        # Find converted skills
        converted_skills = {}
        for skill_md in converted_dir.glob("**/SKILL.md"):
            skill_dir = skill_md.parent
            content = skill_md.read_text(encoding="utf-8")
            fm = self.extract_frontmatter(content)
            name = fm.get("name", skill_dir.name)
            converted_skills[name.lower()] = skill_dir

        self.log(f"Found {len(converted_skills)} converted skills")

        # Find original skills and match
        for orig_file in original_dir.glob("**/*.instructions.md"):
            # Extract name from filename (e.g., "csharp.instructions.md" -> "csharp")
            name = orig_file.stem.replace(".instructions", "")

            # Try to match
            conv_dir = converted_skills.get(name.lower())

            if conv_dir:
                try:
                    result = self.test_equivalence(orig_file, conv_dir)
                    results.append(result)
                except Exception as e:
                    self.log(f"Error testing {name}: {e}")
            else:
                self.log(f"No converted skill found for: {name}")

        return results

    def format_report_text(self, result: EquivalenceResult) -> str:
        """Format result as human-readable text"""
        lines = []

        status = "✅ PASSED" if result.passed else "❌ FAILED"

        lines.append("=" * 60)
        lines.append(f"Equivalence Test Report: {result.skill_name}")
        lines.append("=" * 60)
        lines.append(f"Status: {status}")
        lines.append(f"Overall Score: {result.overall_score:.1%}")
        lines.append(f"Tested: {result.tested_at}")
        lines.append("")
        lines.append("--- Scores ---")
        lines.append(
            f"  Semantic Similarity:   {result.semantic_similarity:.1%} (threshold: {self.THRESHOLDS['semantic_similarity']:.0%})"
        )
        lines.append(
            f"  Structure Similarity:  {result.structure_similarity:.1%} (threshold: {self.THRESHOLDS['structure_similarity']:.0%})"
        )
        lines.append(
            f"  Keyword Similarity:    {result.keyword_similarity:.1%} (threshold: {self.THRESHOLDS['keyword_similarity']:.0%})"
        )
        lines.append(
            f"  Metadata Completeness: {result.metadata_completeness:.1%} (threshold: {self.THRESHOLDS['metadata_completeness']:.0%})"
        )

        if result.errors:
            lines.append("\n--- Errors ---")
            for error in result.errors:
                lines.append(f"  ❌ {error}")

        if result.warnings:
            lines.append("\n--- Warnings ---")
            for warning in result.warnings:
                lines.append(f"  ⚠️ {warning}")

        lines.append("\n--- Files ---")
        lines.append(f"  Original:  {result.original_path}")
        lines.append(f"  Converted: {result.converted_path}")

        lines.append("\n" + "=" * 60)
        return "\n".join(lines)

    def format_report_json(self, result: EquivalenceResult) -> str:
        """Format result as JSON"""
        return json.dumps(result.to_dict(), indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description="Skill Equivalence Tester")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument(
        "--model", default="all-MiniLM-L6-v2", help="Sentence transformer model"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # test command
    test_parser = subparsers.add_parser("test", help="Test equivalence of two skills")
    test_parser.add_argument("original", type=Path, help="Original skill path")
    test_parser.add_argument("converted", type=Path, help="Converted skill path")
    test_parser.add_argument("--format", choices=["text", "json"], default="text")

    # batch command
    batch_parser = subparsers.add_parser("batch", help="Test all skills in directories")
    batch_parser.add_argument(
        "original_dir", type=Path, help="Directory with original skills"
    )
    batch_parser.add_argument(
        "converted_dir", type=Path, help="Directory with converted skills"
    )
    batch_parser.add_argument("--format", choices=["text", "json"], default="text")
    batch_parser.add_argument("--output", type=Path, help="Output file")
    batch_parser.add_argument(
        "--failed-only", action="store_true", help="Show only failed tests"
    )

    # report command
    report_parser = subparsers.add_parser("report", help="Generate detailed report")
    report_parser.add_argument("original", type=Path)
    report_parser.add_argument("converted", type=Path)
    report_parser.add_argument("--format", choices=["text", "json"], default="text")
    report_parser.add_argument("--output", type=Path)

    args = parser.parse_args()
    tester = SkillEquivalenceTester(verbose=args.verbose, model_name=args.model)

    if args.command in ["test", "report"]:
        try:
            result = tester.test_equivalence(args.original, args.converted)

            if args.format == "json":
                output = tester.format_report_json(result)
            else:
                output = tester.format_report_text(result)

            if hasattr(args, "output") and args.output:
                args.output.write_text(output, encoding="utf-8")
                print(f"📄 Report saved to {args.output}")
            else:
                print(output)

            sys.exit(0 if result.passed else 1)

        except FileNotFoundError as e:
            print(f"❌ Error: {e}")
            sys.exit(1)

    elif args.command == "batch":
        results = tester.batch_test(args.original_dir, args.converted_dir)

        if args.failed_only:
            results = [r for r in results if not r.passed]

        if args.format == "json":
            output = json.dumps(
                [r.to_dict() for r in results], indent=2, ensure_ascii=False
            )
        else:
            passed = sum(1 for r in results if r.passed)
            failed = len(results) - passed

            lines = [
                f"\n📊 Batch Test Results",
                f"   Total:  {len(results)}",
                f"   Passed: {passed} ✅",
                f"   Failed: {failed} ❌",
                "",
            ]

            if failed > 0:
                lines.append("Failed tests:")
                for r in results:
                    if not r.passed:
                        lines.append(f"  ❌ {r.skill_name}: {r.overall_score:.1%}")
                        for w in r.warnings[:2]:
                            lines.append(f"     - {w}")

            output = "\n".join(lines)

        if args.output:
            args.output.write_text(output, encoding="utf-8")
            print(f"📄 Results saved to {args.output}")
        else:
            print(output)

        # Exit with error if any failed
        if any(not r.passed for r in results):
            sys.exit(1)


if __name__ == "__main__":
    main()
<<<<<<< Updated upstream
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
