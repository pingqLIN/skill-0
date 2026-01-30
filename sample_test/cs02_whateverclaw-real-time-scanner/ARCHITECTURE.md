# Scanner Architecture Design

> 系統架構設計 | System Architecture Design

**Project:** OpenClaw Real-Time Security Scanner  
**Framework:** skill-0 Semantic Decomposition  
**Version:** 1.0  
**Date:** 2026-01-30

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Component Architecture](#2-component-architecture)
3. [Data Flow](#3-data-flow)
4. [Security Pattern Library](#4-security-pattern-library)
5. [Integration Architecture](#5-integration-architecture)
6. [Deployment Models](#6-deployment-models)

---

## 1. System Overview

### 1.1 Architecture Principles

The scanner follows these core architectural principles:

| Principle | Description | Benefit |
|-----------|-------------|---------|
| **Separation of Concerns** | Parser, Analyzer, Reporter are independent | Easier testing and maintenance |
| **Extensibility** | Plugin-based pattern library | Community contributions |
| **Performance First** | Caching, incremental parsing, parallelization | Real-time performance |
| **Standards-Based** | SARIF output, LSP integration | Tool interoperability |

### 1.2 High-Level Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                   skill-0 C++ Security Scanner                      │
│                         Architecture Layers                         │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    Integration Layer                          │  │
│  │  IDE Plugin  │  CLI Tool  │  CI/CD  │  Web Dashboard        │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                            ▲                                       │
│                            │                                       │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                      API Layer                                │  │
│  │  REST API  │  Python API  │  Language Server Protocol (LSP)  │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                            ▲                                       │
│                            │                                       │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                   Core Analysis Engine                        │  │
│  │                                                               │  │
│  │   ┌──────────────┐   ┌──────────────┐   ┌────────────────┐   │  │
│  │   │   Parser     │──▶│  Decomposer  │──▶│    Scanner     │   │  │
│  │   │              │   │              │   │                │   │  │
│  │   │ Clang/Tree-  │   │  skill-0     │   │ Pattern Match  │   │  │
│  │   │ sitter       │   │  Ternary     │   │ Risk Scoring   │   │  │
│  │   └──────────────┘   └──────────────┘   └────────────────┘   │  │
│  │                                                               │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                            ▲                                       │
│                            │                                       │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                     Data Layer                                │  │
│  │                                                               │  │
│  │  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐    │  │
│  │  │ AST Cache   │  │ Pattern DB   │  │ Vector Store      │    │  │
│  │  │ (Redis/Mem) │  │ (SQLite)     │  │ (sqlite-vec)      │    │  │
│  │  └─────────────┘  └──────────────┘  └───────────────────┘    │  │
│  │                                                               │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## 2. Component Architecture

### 2.1 Parser Module

**Responsibility:** Convert C++ source code to Abstract Syntax Tree (AST)

#### 2.1.1 Dual Parser Strategy

```python
# parser/parser_factory.py

class ParserFactory:
    """Factory for selecting appropriate parser"""
    
    @staticmethod
    def create_parser(mode: str, config: dict):
        if mode == 'realtime':
            return TreeSitterParser(config)
        elif mode == 'batch':
            return ClangParser(config)
        elif mode == 'hybrid':
            return HybridParser(config)
        else:
            raise ValueError(f"Unknown mode: {mode}")
```

#### Parser Comparison

| Feature | Tree-sitter | Clang LibTooling | Hybrid (Recommended) |
|---------|-------------|------------------|----------------------|
| **Speed** | ⭐⭐⭐⭐⭐ (5-10ms) | ⭐⭐⭐ (50-200ms) | ⭐⭐⭐⭐ |
| **Accuracy** | ⭐⭐⭐ (syntax only) | ⭐⭐⭐⭐⭐ (semantic) | ⭐⭐⭐⭐⭐ |
| **Memory** | ⭐⭐⭐⭐⭐ (<10MB) | ⭐⭐ (200-500MB) | ⭐⭐⭐ |
| **Incremental** | ✅ Yes | ❌ No | ✅ Yes |
| **Type Info** | ❌ No | ✅ Yes | ✅ Yes (cached) |

**Hybrid Strategy:**
- Use Tree-sitter for syntax-level checks (fast)
- Use Clang for semantic checks requiring type information (accurate)
- Cache Clang results for reuse

#### 2.1.2 Implementation

```python
# parser/clang_parser.py

import clang.cindex
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class ASTNode:
    """Unified AST node representation"""
    kind: str
    name: str
    location: tuple  # (file, line, column)
    children: List['ASTNode']
    type_info: Optional[str] = None
    
class ClangParser:
    """Clang-based C++ parser"""
    
    def __init__(self, config: dict):
        self.index = clang.cindex.Index.create()
        self.compile_flags = config.get('compile_flags', ['-std=c++17'])
        self.include_paths = config.get('include_paths', [])
    
    def parse_file(self, filepath: Path) -> ASTNode:
        """Parse C++ file to AST"""
        tu = self.index.parse(
            str(filepath),
            args=self.compile_flags + 
                 [f'-I{p}' for p in self.include_paths]
        )
        
        if tu.diagnostics:
            self._handle_diagnostics(tu.diagnostics)
        
        return self._convert_cursor(tu.cursor)
    
    def _convert_cursor(self, cursor) -> ASTNode:
        """Convert Clang cursor to unified ASTNode"""
        return ASTNode(
            kind=cursor.kind.name,
            name=cursor.spelling,
            location=(
                cursor.location.file.name if cursor.location.file else None,
                cursor.location.line,
                cursor.location.column
            ),
            children=[self._convert_cursor(c) for c in cursor.get_children()],
            type_info=cursor.type.spelling if cursor.type else None
        )
    
    def extract_function_calls(self, ast: ASTNode) -> List[dict]:
        """Extract all function calls from AST"""
        calls = []
        
        def walk(node):
            if node.kind == 'CALL_EXPR':
                calls.append({
                    'function': node.name,
                    'location': node.location,
                    'arguments': [c for c in node.children if c.kind != 'UNEXPOSED_EXPR']
                })
            for child in node.children:
                walk(child)
        
        walk(ast)
        return calls
```

```python
# parser/treesitter_parser.py

from tree_sitter import Language, Parser
import tree_sitter_cpp

class TreeSitterParser:
    """Fast incremental parser using Tree-sitter"""
    
    def __init__(self, config: dict):
        self.parser = Parser()
        self.parser.set_language(tree_sitter_cpp.language())
        self.previous_tree = None
    
    def parse_file(self, filepath: Path, old_tree=None) -> ASTNode:
        """Incremental parsing"""
        with open(filepath, 'rb') as f:
            content = f.read()
        
        tree = self.parser.parse(content, old_tree)
        self.previous_tree = tree
        
        return self._convert_tree_sitter_node(tree.root_node)
    
    def parse_incremental(self, filepath: Path, edit: dict) -> ASTNode:
        """Parse only changed sections"""
        return self.parse_file(filepath, self.previous_tree)
```

### 2.2 Decomposer Module

**Responsibility:** Convert AST nodes to skill-0 Actions/Rules/Directives

```python
# decomposer/cpp_decomposer.py

from typing import List, Dict, Any
from dataclasses import dataclass, asdict

@dataclass
class SecurityAction:
    """skill-0 Action for security analysis"""
    id: str
    name: str
    action_type: str  # transform, io_read, io_write, etc.
    function_name: str
    parameters: List[Dict[str, Any]]
    deterministic: bool
    risk_indicators: List[str]
    location: tuple

@dataclass
class SecurityRule:
    """skill-0 Rule for security checks"""
    id: str
    name: str
    condition_type: str  # validation, existence_check, etc.
    condition: str
    output: str  # boolean, enum, score
    verified: bool
    location: tuple

@dataclass
class SecurityDirective:
    """skill-0 Directive for context"""
    id: str
    directive_type: str  # constraint, principle, knowledge
    description: str
    decomposable: bool
    source: str  # code comment, design doc, etc.

class CPPSecurityDecomposer:
    """Decomposes C++ code into skill-0 security patterns"""
    
    def __init__(self, pattern_db):
        self.patterns = pattern_db
        self.context_analyzer = ContextAnalyzer()
    
    def decompose(self, ast: ASTNode) -> Dict[str, Any]:
        """Main decomposition entry point"""
        actions = []
        rules = []
        directives = []
        
        # Extract function calls (Actions)
        for call in self._extract_calls(ast):
            action = self._decompose_function_call(call)
            if action:
                actions.append(action)
        
        # Extract conditional checks (Rules)
        for condition in self._extract_conditions(ast):
            rule = self._decompose_condition(condition)
            if rule:
                rules.append(rule)
        
        # Extract comments and design patterns (Directives)
        for comment in self._extract_comments(ast):
            directive = self._decompose_comment(comment)
            if directive:
                directives.append(directive)
        
        return {
            'actions': [asdict(a) for a in actions],
            'rules': [asdict(r) for r in rules],
            'directives': [asdict(d) for d in directives]
        }
    
    def _decompose_function_call(self, call: dict) -> Optional[SecurityAction]:
        """Convert function call to security action"""
        func_name = call['function']
        
        # Check if this is a known risky function
        if pattern := self.patterns.get_function_pattern(func_name):
            # Analyze context
            context = self.context_analyzer.analyze(call)
            
            return SecurityAction(
                id=f"a_{func_name}_{call['location'][1]}",
                name=f"{pattern['name']}: {func_name}",
                action_type=pattern['action_type'],
                function_name=func_name,
                parameters=call['arguments'],
                deterministic=pattern.get('deterministic', True),
                risk_indicators=self._identify_risks(call, context),
                location=call['location']
            )
        
        return None
    
    def _identify_risks(self, call: dict, context: dict) -> List[str]:
        """Identify risk indicators for this call"""
        risks = []
        
        # Check for common risk patterns
        if context.get('user_input_tainted'):
            risks.append('user_input')
        
        if context.get('no_bounds_check'):
            risks.append('no_bounds_check')
        
        if context.get('unchecked_return'):
            risks.append('unchecked_return')
        
        if context.get('in_loop'):
            risks.append('resource_exhaustion')
        
        return risks

class ContextAnalyzer:
    """Analyzes code context for risk assessment"""
    
    def analyze(self, call: dict) -> dict:
        """Analyze the context of a function call"""
        context = {
            'user_input_tainted': False,
            'no_bounds_check': False,
            'unchecked_return': False,
            'in_loop': False
        }
        
        # Taint analysis (simple version)
        for arg in call['arguments']:
            if self._is_user_input(arg):
                context['user_input_tainted'] = True
        
        # Check for bounds validation
        if not self._has_bounds_check(call):
            context['no_bounds_check'] = True
        
        # Check if return value is checked
        if not self._return_checked(call):
            context['unchecked_return'] = True
        
        # Check if in loop
        if self._in_loop_context(call):
            context['in_loop'] = True
        
        return context
    
    def _is_user_input(self, arg: dict) -> bool:
        """Check if argument is derived from user input"""
        # Simple heuristic: parameter names containing 'input', 'user', 'file'
        if isinstance(arg, dict) and 'name' in arg:
            name = arg['name'].lower()
            return any(keyword in name for keyword in 
                      ['input', 'user', 'file', 'argv', 'param'])
        return False
```

### 2.3 Scanner Engine

**Responsibility:** Apply security patterns and generate findings

```python
# scanner/security_scanner.py

from typing import List, Dict, Any
from dataclasses import dataclass
from enum import Enum

class Severity(Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class SecurityFinding:
    """A security vulnerability finding"""
    rule_id: str
    rule_name: str
    severity: Severity
    location: tuple  # (file, line, column)
    code_snippet: str
    description: str
    recommendation: str
    cwe_id: Optional[str] = None
    confidence: float = 1.0

class SecurityScanner:
    """Main scanner engine"""
    
    def __init__(self, pattern_library, vector_search):
        self.patterns = pattern_library
        self.vector_search = vector_search
        self.risk_calculator = RiskCalculator()
    
    def scan(self, decomposition: dict) -> List[SecurityFinding]:
        """Scan decomposed code for security issues"""
        findings = []
        
        # Scan actions
        for action in decomposition['actions']:
            action_findings = self._scan_action(action)
            findings.extend(action_findings)
        
        # Scan rules
        for rule in decomposition['rules']:
            rule_findings = self._scan_rule(rule)
            findings.extend(rule_findings)
        
        # Check for similar known vulnerabilities
        similar_findings = self._check_similar_vulns(decomposition)
        findings.extend(similar_findings)
        
        # De-duplicate and prioritize
        findings = self._deduplicate(findings)
        findings.sort(key=lambda f: (f.severity.value, -f.confidence))
        
        return findings
    
    def _scan_action(self, action: dict) -> List[SecurityFinding]:
        """Scan an action against security patterns"""
        findings = []
        
        # Get applicable patterns
        patterns = self.patterns.get_patterns_for_function(
            action['function_name']
        )
        
        for pattern in patterns:
            if self._pattern_matches(pattern, action):
                finding = SecurityFinding(
                    rule_id=pattern['rule_id'],
                    rule_name=pattern['name'],
                    severity=Severity(pattern['severity']),
                    location=action['location'],
                    code_snippet=self._get_code_snippet(action['location']),
                    description=pattern['description'],
                    recommendation=pattern['recommendation'],
                    cwe_id=pattern.get('cwe_id'),
                    confidence=self._calculate_confidence(pattern, action)
                )
                findings.append(finding)
        
        return findings
    
    def _pattern_matches(self, pattern: dict, action: dict) -> bool:
        """Check if pattern matches action"""
        # Check risk indicators
        required_risks = pattern.get('required_risk_indicators', [])
        actual_risks = action.get('risk_indicators', [])
        
        return all(risk in actual_risks for risk in required_risks)
    
    def _check_similar_vulns(self, decomposition: dict) -> List[SecurityFinding]:
        """Check vector database for similar known vulnerabilities"""
        findings = []
        
        # Generate embedding for this code pattern
        code_repr = self._generate_code_representation(decomposition)
        
        # Search for similar patterns
        similar = self.vector_search.search(code_repr, limit=5)
        
        for match in similar:
            if match['similarity'] > 0.8 and match.get('is_vulnerability'):
                finding = SecurityFinding(
                    rule_id="SIM-VULN",
                    rule_name=f"Similar to known vulnerability: {match['name']}",
                    severity=Severity.MEDIUM,
                    location=decomposition['actions'][0]['location'] if decomposition['actions'] else (None, 0, 0),
                    code_snippet="",
                    description=f"This code pattern is {match['similarity']:.0%} similar to {match['name']}",
                    recommendation=f"Review: {match.get('recommendation', 'Check CVE database')}",
                    confidence=match['similarity']
                )
                findings.append(finding)
        
        return findings
    
    def _deduplicate(self, findings: List[SecurityFinding]) -> List[SecurityFinding]:
        """Remove duplicate findings"""
        seen = set()
        unique = []
        
        for finding in findings:
            key = (finding.rule_id, finding.location)
            if key not in seen:
                seen.add(key)
                unique.append(finding)
        
        return unique
```

### 2.4 Pattern Library

**Responsibility:** Store and manage security patterns

```python
# patterns/pattern_library.py

import json
from pathlib import Path
from typing import List, Dict, Optional

class PatternLibrary:
    """Manages security patterns"""
    
    def __init__(self, patterns_dir: Path):
        self.patterns_dir = patterns_dir
        self.patterns = self._load_patterns()
        self.function_index = self._build_function_index()
    
    def _load_patterns(self) -> List[Dict]:
        """Load all patterns from disk"""
        patterns = []
        
        for pattern_file in self.patterns_dir.glob('SEC-CPP-*.json'):
            with open(pattern_file) as f:
                pattern = json.load(f)
                patterns.append(pattern)
        
        return patterns
    
    def _build_function_index(self) -> Dict[str, List[Dict]]:
        """Build index of patterns by function name"""
        index = {}
        
        for pattern in self.patterns:
            for func in pattern.get('functions', []):
                if func not in index:
                    index[func] = []
                index[func].append(pattern)
        
        return index
    
    def get_patterns_for_function(self, func_name: str) -> List[Dict]:
        """Get all patterns applicable to a function"""
        return self.function_index.get(func_name, [])
    
    def get_pattern(self, pattern_id: str) -> Optional[Dict]:
        """Get pattern by ID"""
        for pattern in self.patterns:
            if pattern['id'] == pattern_id:
                return pattern
        return None
    
    def add_pattern(self, pattern: Dict):
        """Add a new custom pattern"""
        self.patterns.append(pattern)
        
        # Update index
        for func in pattern.get('functions', []):
            if func not in self.function_index:
                self.function_index[func] = []
            self.function_index[func].append(pattern)
        
        # Save to disk
        pattern_file = self.patterns_dir / f"{pattern['id']}.json"
        with open(pattern_file, 'w') as f:
            json.dump(pattern, f, indent=2)
```

---

## 3. Data Flow

### 3.1 Scan Workflow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Scan Data Flow                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Input: C++ Source File                                            │
│           │                                                         │
│           ▼                                                         │
│  ┌──────────────────┐                                              │
│  │  1. Parse        │  Clang/Tree-sitter                           │
│  │     (AST)        │  ────────────▶ AST Cache (if caching)        │
│  └──────────────────┘                                              │
│           │                                                         │
│           │ ASTNode                                                 │
│           ▼                                                         │
│  ┌──────────────────┐                                              │
│  │  2. Decompose    │                                              │
│  │     (skill-0)    │  Actions, Rules, Directives                  │
│  └──────────────────┘                                              │
│           │                                                         │
│           │ Decomposition                                           │
│           ▼                                                         │
│  ┌──────────────────────────────────────────────────┐              │
│  │  3. Scan                                         │              │
│  │     ┌─────────────────┐   ┌──────────────────┐  │              │
│  │     │ Pattern Match   │   │ Vector Search    │  │              │
│  │     │ (Rule Engine)   │   │ (Similarity)     │  │              │
│  │     └─────────────────┘   └──────────────────┘  │              │
│  └──────────────────────────────────────────────────┘              │
│           │                                                         │
│           │ Findings                                                │
│           ▼                                                         │
│  ┌──────────────────┐                                              │
│  │  4. Score        │  Risk Calculation                            │
│  │     (Risk)       │  Confidence Adjustment                       │
│  └──────────────────┘                                              │
│           │                                                         │
│           │ Scored Findings                                         │
│           ▼                                                         │
│  ┌──────────────────┐                                              │
│  │  5. Report       │  JSON/SARIF/Text                             │
│  │     (Format)     │  Dashboard Update                            │
│  └──────────────────┘                                              │
│           │                                                         │
│           ▼                                                         │
│  Output: Security Report                                           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 Real-Time Workflow (IDE Integration)

```
┌──────────────────────────────────────────────────────────────┐
│                  Real-Time Scan Workflow                      │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Developer edits file                                        │
│           │                                                  │
│           ▼                                                  │
│  File Save Event                                             │
│           │                                                  │
│           ▼                                                  │
│  ┌──────────────────┐                                        │
│  │ Language Server  │  LSP Protocol                          │
│  │ (skill-0-lsp)    │  ◀──────────▶ IDE                     │
│  └──────────────────┘                                        │
│           │                                                  │
│           ▼                                                  │
│  Check AST Cache                                             │
│      │          │                                            │
│      │          ├──▶ Cache Hit: Use cached AST              │
│      │          │                                            │
│      │          └──▶ Cache Miss: Parse with Tree-sitter     │
│      │               (incremental, ~10ms)                   │
│      ▼                                                       │
│  Quick Scan (syntax-level patterns only)                    │
│           │                                                  │
│           ▼                                                  │
│  Publish Diagnostics ──────▶ IDE (inline warnings)          │
│                                                              │
│  Background Task:                                            │
│  └──▶ Full Scan (semantic patterns) ───▶ Update Cache       │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 4. Security Pattern Library

### 4.1 Pattern Structure

Each security pattern follows this schema:

```json
{
  "id": "SEC-CPP-XXX",
  "name": "Pattern Name",
  "category": "memory_safety | type_safety | concurrency | ...",
  "severity": "critical | high | medium | low | info",
  "description": "What this pattern detects",
  "functions": ["strcpy", "memcpy", "..."],
  "action_type": "transform",
  "required_risk_indicators": ["no_bounds_check", "user_input"],
  "cwe_id": "CWE-120",
  "recommendation": "How to fix",
  "examples": {
    "vulnerable": "...",
    "safe": "..."
  }
}
```

### 4.2 Example Patterns

**SEC-CPP-001: Unsafe Memory Operations**

```json
{
  "id": "SEC-CPP-001",
  "name": "Unsafe Memory Operations",
  "category": "memory_safety",
  "severity": "critical",
  "description": "Detects use of dangerous memory functions without bounds checking",
  "functions": ["strcpy", "strcat", "sprintf", "gets"],
  "action_type": "transform",
  "required_risk_indicators": ["no_bounds_check"],
  "cwe_id": "CWE-120",
  "recommendation": "Use safe alternatives: strncpy, strncat, snprintf, fgets",
  "examples": {
    "vulnerable": "strcpy(dest, src);",
    "safe": "strncpy(dest, src, sizeof(dest) - 1); dest[sizeof(dest)-1] = '\\0';"
  }
}
```

**SEC-CPP-002: RAII Violations**

```json
{
  "id": "SEC-CPP-002",
  "name": "RAII Violations - Manual Memory Management",
  "category": "resource_management",
  "severity": "high",
  "description": "Detects manual memory management that could lead to leaks",
  "functions": ["new", "new[]", "malloc", "calloc"],
  "action_type": "external_call",
  "required_risk_indicators": ["no_paired_delete", "exception_unsafe"],
  "cwe_id": "CWE-401",
  "recommendation": "Use smart pointers: std::unique_ptr, std::shared_ptr, or std::make_unique",
  "examples": {
    "vulnerable": "Object* obj = new Object(); // May leak if exception thrown",
    "safe": "auto obj = std::make_unique<Object>();"
  }
}
```

### 4.3 Pattern Categories

| Category | Pattern Count | Examples |
|----------|---------------|----------|
| **memory_safety** | 10 | strcpy, buffer overflow, use-after-free |
| **resource_management** | 5 | RAII violations, leaks |
| **type_safety** | 5 | unsafe casts, type confusion |
| **concurrency** | 8 | race conditions, deadlocks |
| **input_validation** | 7 | SQL injection, path traversal |
| **crypto** | 5 | weak algorithms, hardcoded keys |

---

## 5. Integration Architecture

### 5.1 Language Server Protocol (LSP)

```python
# integrations/lsp_server.py

from pygls.server import LanguageServer
from pygls.lsp.types import (
    Diagnostic,
    DiagnosticSeverity,
    Position,
    Range,
    DidSaveTextDocumentParams
)

class Skill0LSP(LanguageServer):
    """Language Server for real-time scanning"""
    
    def __init__(self):
        super().__init__()
        self.scanner = SecurityScanner(pattern_library, vector_search)
        self.parser = ParserFactory.create_parser('realtime', {})
    
    @server.feature("textDocument/didSave")
    async def did_save(self, params: DidSaveTextDocumentParams):
        """Triggered when file is saved"""
        uri = params.text_document.uri
        filepath = Path(uri.replace('file://', ''))
        
        # Scan file
        findings = await self._scan_file(filepath)
        
        # Convert to LSP diagnostics
        diagnostics = self._to_diagnostics(findings)
        
        # Publish to IDE
        self.publish_diagnostics(uri, diagnostics)
    
    async def _scan_file(self, filepath: Path) -> List[SecurityFinding]:
        """Scan a file and return findings"""
        # Parse
        ast = self.parser.parse_file(filepath)
        
        # Decompose
        decomposition = self.decomposer.decompose(ast)
        
        # Scan
        findings = self.scanner.scan(decomposition)
        
        return findings
    
    def _to_diagnostics(self, findings: List[SecurityFinding]) -> List[Diagnostic]:
        """Convert findings to LSP diagnostics"""
        diagnostics = []
        
        for finding in findings:
            diagnostic = Diagnostic(
                range=Range(
                    start=Position(line=finding.location[1]-1, character=0),
                    end=Position(line=finding.location[1], character=0)
                ),
                severity=self._severity_to_lsp(finding.severity),
                source='skill-0-scanner',
                message=f"[{finding.rule_id}] {finding.description}\\n\\nRecommendation: {finding.recommendation}"
            )
            diagnostics.append(diagnostic)
        
        return diagnostics
    
    def _severity_to_lsp(self, severity: Severity) -> DiagnosticSeverity:
        mapping = {
            Severity.CRITICAL: DiagnosticSeverity.Error,
            Severity.HIGH: DiagnosticSeverity.Error,
            Severity.MEDIUM: DiagnosticSeverity.Warning,
            Severity.LOW: DiagnosticSeverity.Information,
            Severity.INFO: DiagnosticSeverity.Hint
        }
        return mapping[severity]
```

### 5.2 CI/CD Integration

```yaml
# .github/workflows/skill0-scan.yml

name: skill-0 Security Scan

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  security-scan:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install skill-0 Scanner
        run: |
          pip install skill0-cpp-scanner
      
      - name: Run Security Scan
        run: |
          skill0-scanner scan-project . \
            --format sarif \
            --output results.sarif \
            --fail-on critical,high
      
      - name: Upload SARIF to GitHub
        if: always()
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: results.sarif
      
      - name: Generate Report
        if: always()
        run: |
          skill0-scanner report results.sarif \
            --format markdown \
            --output SECURITY_REPORT.md
      
      - name: Comment on PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const report = fs.readFileSync('SECURITY_REPORT.md', 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: report
            });
```

---

## 6. Deployment Models

### 6.1 Standalone CLI

```bash
# Install
pip install skill0-cpp-scanner

# Scan single file
skill0-scanner scan src/Player.cpp

# Scan project
skill0-scanner scan-project /path/to/openclaw

# Watch mode (continuous)
skill0-scanner watch /path/to/openclaw
```

### 6.2 IDE Plugin (VS Code)

```json
// vscode-extension/package.json
{
  "name": "skill0-cpp-security",
  "displayName": "skill-0 C++ Security Scanner",
  "description": "Real-time security scanning for C++",
  "version": "1.0.0",
  "engines": {
    "vscode": "^1.70.0"
  },
  "activationEvents": [
    "onLanguage:cpp"
  ],
  "main": "./out/extension.js",
  "contributes": {
    "commands": [
      {
        "command": "skill0.scan",
        "title": "skill-0: Scan Current File"
      },
      {
        "command": "skill0.scanWorkspace",
        "title": "skill-0: Scan Workspace"
      }
    ],
    "configuration": {
      "title": "skill-0 Scanner",
      "properties": {
        "skill0.scanOnSave": {
          "type": "boolean",
          "default": true,
          "description": "Scan files automatically on save"
        },
        "skill0.severity": {
          "type": "string",
          "default": "medium",
          "enum": ["critical", "high", "medium", "low", "info"],
          "description": "Minimum severity to show"
        }
      }
    }
  }
}
```

### 6.3 Web Dashboard

```python
# dashboard/app.py

from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles

app = FastAPI()

@app.get("/api/projects")
async def list_projects():
    """List scanned projects"""
    return db.get_projects()

@app.get("/api/projects/{project_id}/findings")
async def get_findings(project_id: str):
    """Get findings for a project"""
    return db.get_findings(project_id)

@app.websocket("/ws/scan")
async def websocket_scan(websocket: WebSocket):
    """Real-time scan updates"""
    await websocket.accept()
    
    while True:
        data = await websocket.receive_json()
        
        # Scan file
        findings = scanner.scan_file(data['filepath'])
        
        # Send results
        await websocket.send_json({
            'findings': [f.to_dict() for f in findings]
        })

app.mount("/", StaticFiles(directory="static", html=True), name="static")
```

---

## 7. Performance Optimizations

### 7.1 Caching Strategy

```python
# cache/ast_cache.py

import pickle
from pathlib import Path
from typing import Optional

class ASTCache:
    """Cache parsed ASTs for reuse"""
    
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)
    
    def get(self, filepath: Path) -> Optional[ASTNode]:
        """Get cached AST if available and fresh"""
        cache_file = self._get_cache_file(filepath)
        
        if not cache_file.exists():
            return None
        
        # Check if source file is newer than cache
        if filepath.stat().st_mtime > cache_file.stat().st_mtime:
            return None
        
        with open(cache_file, 'rb') as f:
            return pickle.load(f)
    
    def set(self, filepath: Path, ast: ASTNode):
        """Cache AST"""
        cache_file = self._get_cache_file(filepath)
        
        with open(cache_file, 'wb') as f:
            pickle.dump(ast, f)
    
    def _get_cache_file(self, filepath: Path) -> Path:
        # Use hash of filepath as cache key
        import hashlib
        key = hashlib.sha256(str(filepath).encode()).hexdigest()
        return self.cache_dir / f"{key}.ast.cache"
```

### 7.2 Parallel Scanning

```python
# scanner/parallel_scanner.py

from multiprocessing import Pool, cpu_count
from typing import List

class ParallelScanner:
    """Scan multiple files in parallel"""
    
    def __init__(self, scanner, num_workers=None):
        self.scanner = scanner
        self.num_workers = num_workers or cpu_count()
    
    def scan_files(self, filepaths: List[Path]) -> List[ScanResult]:
        """Scan multiple files in parallel"""
        with Pool(self.num_workers) as pool:
            results = pool.map(self._scan_single, filepaths)
        
        return results
    
    def _scan_single(self, filepath: Path) -> ScanResult:
        """Scan a single file (worker function)"""
        return self.scanner.scan_file(filepath)
```

---

**End of Architecture Document**

*For implementation details, see IMPLEMENTATION_ROADMAP.md*
