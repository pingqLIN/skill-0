# C++ Security Patterns in skill-0 Format

> C++ 安全模式庫 | C++ Security Pattern Library

**Project:** OpenClaw Real-Time Security Scanner  
**Framework:** skill-0 Ternary Classification  
**Version:** 1.0  
**Date:** 2026-01-30

---

## Pattern Library Overview

This document defines C++-specific security patterns in skill-0 format, mapping common C++ vulnerabilities to the ternary classification system (Actions, Rules, Directives).

### Pattern Categories

| Category | Pattern Count | Severity Range |
|----------|---------------|----------------|
| **Memory Safety** | 10 | Critical - High |
| **Resource Management** | 5 | High - Medium |
| **Type Safety** | 5 | High - Medium |
| **Concurrency** | 8 | Critical - Medium |
| **Input Validation** | 7 | Critical - Medium |
| **Cryptographic** | 5 | High - Medium |

---

## Memory Safety Patterns

### SEC-CPP-001: Unsafe Memory Copy Operations

**Vulnerability:** Buffer overflow from unbounded memory operations

**skill-0 Decomposition:**

```json
{
  "pattern_id": "SEC-CPP-001",
  "name": "Unsafe Memory Copy Operations",
  "category": "memory_safety",
  "severity": "critical",
  "cwe_id": "CWE-120",
  
  "decomposition": {
    "actions": [
      {
        "id": "a_strcpy",
        "name": "Unbounded Memory Copy",
        "action_type": "transform",
        "function_name": "strcpy",
        "description": "Copies string without destination size check",
        "deterministic": true,
        "immutable_elements": ["function_signature"],
        "mutable_elements": ["source", "destination"],
        "side_effects": ["memory_write", "potential_overflow"],
        "parameters": [
          {
            "name": "dest",
            "type": "char*",
            "direction": "out",
            "taint_source": false
          },
          {
            "name": "src",
            "type": "const char*",
            "direction": "in",
            "taint_source": true
          }
        ]
      }
    ],
    
    "rules": [
      {
        "id": "r_bounds_check",
        "name": "Destination Size Validated",
        "condition_type": "validation",
        "condition": "sizeof(dest) >= strlen(src) + 1",
        "output": "boolean",
        "description": "Verifies destination buffer is large enough",
        "failure_consequence": "buffer_overflow"
      },
      {
        "id": "r_null_termination",
        "name": "Null Terminator Present",
        "condition_type": "existence_check",
        "condition": "src contains null terminator",
        "output": "boolean",
        "description": "Ensures source string is properly terminated"
      }
    ],
    
    "directives": [
      {
        "id": "d_memory_safety",
        "directive_type": "constraint",
        "description": "All memory operations must guarantee bounds safety",
        "decomposable": true,
        "decomposition_hint": "Use strncpy, strlcpy, or std::string"
      },
      {
        "id": "d_cwe_120",
        "directive_type": "knowledge",
        "description": "CWE-120: Buffer Copy without Checking Size of Input",
        "decomposable": false,
        "source": "CWE database"
      }
    ]
  },
  
  "detection": {
    "functions": ["strcpy", "wcscpy", "strcat", "wcscat", "sprintf", "gets"],
    "required_risk_indicators": ["no_bounds_check"],
    "optional_risk_indicators": ["user_input", "loop_context"]
  },
  
  "examples": {
    "vulnerable": [
      "char buffer[256]; strcpy(buffer, user_input);",
      "sprintf(msg, \"User: %s\", username);"
    ],
    "safe": [
      "strncpy(buffer, user_input, sizeof(buffer)-1); buffer[sizeof(buffer)-1]='\\0';",
      "snprintf(msg, sizeof(msg), \"User: %s\", username);"
    ]
  },
  
  "recommendation": {
    "primary": "Use bounded alternatives: strncpy, snprintf",
    "modern_cpp": "Use std::string or std::string_view",
    "code_example": "std::string buffer = user_input; // No overflow risk"
  }
}
```

### SEC-CPP-002: Use-After-Free

**Vulnerability:** Accessing memory after it has been freed

**skill-0 Decomposition:**

```json
{
  "pattern_id": "SEC-CPP-002",
  "name": "Use-After-Free Vulnerability",
  "category": "memory_safety",
  "severity": "critical",
  "cwe_id": "CWE-416",
  
  "decomposition": {
    "actions": [
      {
        "id": "a_delete",
        "name": "Memory Deallocation",
        "action_type": "state_change",
        "function_name": "delete",
        "description": "Frees dynamically allocated memory",
        "deterministic": true,
        "side_effects": ["memory_deallocation", "pointer_invalidation"]
      },
      {
        "id": "a_dereference",
        "name": "Pointer Dereference",
        "action_type": "io_read",
        "description": "Accesses memory through pointer",
        "deterministic": true,
        "side_effects": ["memory_read"]
      }
    ],
    
    "rules": [
      {
        "id": "r_pointer_valid",
        "name": "Pointer Still Valid",
        "condition_type": "state_check",
        "condition": "pointer not deleted && pointer not null",
        "output": "boolean",
        "description": "Ensures pointer is valid before use"
      },
      {
        "id": "r_no_double_delete",
        "name": "No Double Delete",
        "condition_type": "state_check",
        "condition": "delete called exactly once per allocation",
        "output": "boolean"
      }
    ],
    
    "directives": [
      {
        "id": "d_raii",
        "directive_type": "principle",
        "description": "Follow RAII (Resource Acquisition Is Initialization)",
        "decomposable": true,
        "decomposition_hint": "Use smart pointers to manage lifetime"
      },
      {
        "id": "d_zero_after_delete",
        "directive_type": "preference",
        "description": "Set pointers to nullptr after delete",
        "decomposable": false
      }
    ]
  },
  
  "detection": {
    "pattern_sequence": [
      {"action": "delete", "target": "pointer"},
      {"action": "dereference", "target": "same_pointer"}
    ],
    "time_gap": "any",
    "required_risk_indicators": ["pointer_used_after_delete"]
  },
  
  "examples": {
    "vulnerable": [
      "Object* obj = new Object(); delete obj; obj->method(); // Use after free",
      "delete ptr; ptr->value = 10; // Dangling pointer access"
    ],
    "safe": [
      "auto obj = std::make_unique<Object>(); obj->method(); // Automatic cleanup",
      "delete ptr; ptr = nullptr; if(ptr) ptr->value = 10; // Null check"
    ]
  },
  
  "recommendation": {
    "primary": "Use smart pointers (unique_ptr, shared_ptr)",
    "secondary": "Set pointers to nullptr after delete",
    "modern_cpp": "auto obj = std::make_unique<Object>();"
  }
}
```

### SEC-CPP-003: Memory Leak

**Vulnerability:** Allocated memory never freed

**skill-0 Decomposition:**

```json
{
  "pattern_id": "SEC-CPP-003",
  "name": "Memory Leak",
  "category": "memory_safety",
  "severity": "high",
  "cwe_id": "CWE-401",
  
  "decomposition": {
    "actions": [
      {
        "id": "a_new",
        "name": "Dynamic Memory Allocation",
        "action_type": "state_change",
        "function_name": "new",
        "description": "Allocates memory on heap",
        "deterministic": false,
        "side_effects": ["memory_allocation", "resource_consumption"]
      }
    ],
    
    "rules": [
      {
        "id": "r_paired_delete",
        "name": "Allocation Paired with Deallocation",
        "condition_type": "consistency_check",
        "condition": "every new has corresponding delete",
        "output": "boolean",
        "description": "Ensures memory is eventually freed"
      },
      {
        "id": "r_exception_safe",
        "name": "Exception-Safe Cleanup",
        "condition_type": "state_check",
        "condition": "cleanup guaranteed even if exception thrown",
        "output": "boolean"
      }
    ],
    
    "directives": [
      {
        "id": "d_raii_mandatory",
        "directive_type": "constraint",
        "description": "All resources must be managed via RAII",
        "decomposable": false
      }
    ]
  },
  
  "detection": {
    "pattern": "new without delete in same scope",
    "exception_paths_checked": true,
    "required_risk_indicators": ["no_paired_delete"]
  },
  
  "recommendation": {
    "primary": "Use smart pointers (unique_ptr, shared_ptr)",
    "code_example": "auto obj = std::make_unique<Object>();"
  }
}
```

---

## Resource Management Patterns

### SEC-CPP-004: RAII Violation

**Vulnerability:** Manual resource management without RAII

**skill-0 Decomposition:**

```json
{
  "pattern_id": "SEC-CPP-004",
  "name": "RAII Violation",
  "category": "resource_management",
  "severity": "high",
  "cwe_id": "CWE-404",
  
  "decomposition": {
    "actions": [
      {
        "id": "a_acquire",
        "name": "Resource Acquisition",
        "action_type": "external_call",
        "description": "Acquires system resource (file, socket, lock)",
        "deterministic": false,
        "side_effects": ["resource_consumption"]
      },
      {
        "id": "a_release",
        "name": "Resource Release",
        "action_type": "external_call",
        "description": "Releases system resource",
        "deterministic": true,
        "side_effects": ["resource_release"]
      }
    ],
    
    "rules": [
      {
        "id": "r_automatic_cleanup",
        "name": "Automatic Cleanup on Scope Exit",
        "condition_type": "state_check",
        "condition": "resource released via destructor",
        "output": "boolean"
      }
    ],
    
    "directives": [
      {
        "id": "d_raii_principle",
        "directive_type": "principle",
        "description": "Resource lifetime tied to object lifetime",
        "decomposable": true,
        "decomposition_hint": "Wrap resources in classes with destructors"
      }
    ]
  },
  
  "examples": {
    "vulnerable": [
      "FILE* f = fopen(\"file.txt\", \"r\"); /* ... */ fclose(f); // Manual management"
    ],
    "safe": [
      "std::ifstream file(\"file.txt\"); // Automatic cleanup"
    ]
  }
}
```

---

## Type Safety Patterns

### SEC-CPP-005: Unsafe Type Cast

**Vulnerability:** Type confusion from unsafe casts

**skill-0 Decomposition:**

```json
{
  "pattern_id": "SEC-CPP-005",
  "name": "Unsafe Type Cast",
  "category": "type_safety",
  "severity": "high",
  "cwe_id": "CWE-843",
  
  "decomposition": {
    "actions": [
      {
        "id": "a_c_style_cast",
        "name": "C-Style Cast",
        "action_type": "transform",
        "description": "Performs unchecked type conversion",
        "deterministic": true,
        "risk_indicators": ["unchecked_cast", "type_confusion"]
      },
      {
        "id": "a_reinterpret_cast",
        "name": "Reinterpret Cast",
        "action_type": "transform",
        "description": "Reinterprets bit pattern as different type",
        "deterministic": true,
        "risk_indicators": ["dangerous_cast", "undefined_behavior"]
      }
    ],
    
    "rules": [
      {
        "id": "r_type_compatible",
        "name": "Types Are Compatible",
        "condition_type": "type_check",
        "condition": "source type is convertible to destination type",
        "output": "boolean"
      }
    ],
    
    "directives": [
      {
        "id": "d_safe_casts",
        "directive_type": "preference",
        "description": "Prefer static_cast and dynamic_cast over C-style casts",
        "decomposable": false
      }
    ]
  },
  
  "detection": {
    "patterns": ["(Type*)expr", "reinterpret_cast<Type>"],
    "required_risk_indicators": ["unchecked_cast"]
  },
  
  "examples": {
    "vulnerable": [
      "Base* b = (Derived*)ptr; // Unchecked downcast"
    ],
    "safe": [
      "Base* b = dynamic_cast<Derived*>(ptr); if(b) { /* ... */ }"
    ]
  }
}
```

---

## Concurrency Patterns

### SEC-CPP-006: Race Condition

**Vulnerability:** Unsynchronized access to shared data

**skill-0 Decomposition:**

```json
{
  "pattern_id": "SEC-CPP-006",
  "name": "Race Condition",
  "category": "concurrency",
  "severity": "critical",
  "cwe_id": "CWE-362",
  
  "decomposition": {
    "actions": [
      {
        "id": "a_shared_write",
        "name": "Write to Shared Variable",
        "action_type": "state_change",
        "description": "Modifies shared state from multiple threads",
        "deterministic": false,
        "side_effects": ["shared_state_change"]
      },
      {
        "id": "a_shared_read",
        "name": "Read from Shared Variable",
        "action_type": "io_read",
        "description": "Reads shared state from multiple threads",
        "deterministic": false
      }
    ],
    
    "rules": [
      {
        "id": "r_synchronized",
        "name": "Access is Synchronized",
        "condition_type": "state_check",
        "condition": "protected by mutex or atomic",
        "output": "boolean"
      }
    ],
    
    "directives": [
      {
        "id": "d_thread_safety",
        "directive_type": "constraint",
        "description": "All shared data must be protected by synchronization",
        "decomposable": true,
        "decomposition_hint": "Use std::mutex, std::atomic, or locks"
      }
    ]
  },
  
  "detection": {
    "pattern": "shared variable accessed without lock",
    "multi_threaded": true,
    "required_risk_indicators": ["unprotected_shared_access"]
  },
  
  "examples": {
    "vulnerable": [
      "int counter; /* global */ void increment() { counter++; } // Race!"
    ],
    "safe": [
      "std::atomic<int> counter; void increment() { counter++; } // Thread-safe"
    ]
  }
}
```

---

## Input Validation Patterns

### SEC-CPP-007: SQL Injection

**Vulnerability:** Untrusted input in SQL queries

**skill-0 Decomposition:**

```json
{
  "pattern_id": "SEC-CPP-007",
  "name": "SQL Injection",
  "category": "input_validation",
  "severity": "critical",
  "cwe_id": "CWE-89",
  
  "decomposition": {
    "actions": [
      {
        "id": "a_sql_query",
        "name": "Execute SQL Query",
        "action_type": "external_call",
        "description": "Sends SQL query to database",
        "deterministic": false,
        "side_effects": ["database_access"]
      }
    ],
    
    "rules": [
      {
        "id": "r_parameterized",
        "name": "Query is Parameterized",
        "condition_type": "validation",
        "condition": "uses prepared statements or parameterized queries",
        "output": "boolean"
      },
      {
        "id": "r_input_sanitized",
        "name": "Input is Sanitized",
        "condition_type": "validation",
        "condition": "user input is escaped or validated",
        "output": "boolean"
      }
    ],
    
    "directives": [
      {
        "id": "d_never_concat",
        "directive_type": "constraint",
        "description": "Never concatenate user input into SQL queries",
        "decomposable": false
      }
    ]
  },
  
  "detection": {
    "pattern": "string concatenation in SQL query with user input",
    "required_risk_indicators": ["user_input", "string_concatenation"]
  },
  
  "examples": {
    "vulnerable": [
      "string query = \"SELECT * FROM users WHERE name='\" + username + \"'\";"
    ],
    "safe": [
      "PreparedStatement stmt = conn.prepareStatement(\"SELECT * FROM users WHERE name=?\"); stmt.setString(1, username);"
    ]
  }
}
```

### SEC-CPP-008: Path Traversal

**Vulnerability:** Unauthorized file access through path manipulation

**skill-0 Decomposition:**

```json
{
  "pattern_id": "SEC-CPP-008",
  "name": "Path Traversal",
  "category": "input_validation",
  "severity": "high",
  "cwe_id": "CWE-22",
  
  "decomposition": {
    "actions": [
      {
        "id": "a_file_open",
        "name": "Open File",
        "action_type": "io_read",
        "description": "Opens file for reading/writing",
        "deterministic": false,
        "parameters": [
          {
            "name": "filepath",
            "type": "string",
            "taint_source": true
          }
        ]
      }
    ],
    
    "rules": [
      {
        "id": "r_path_validated",
        "name": "Path is Validated",
        "condition_type": "validation",
        "condition": "path contains no .. or absolute paths",
        "output": "boolean"
      },
      {
        "id": "r_in_allowed_dir",
        "name": "Path Within Allowed Directory",
        "condition_type": "validation",
        "condition": "canonical path starts with allowed directory",
        "output": "boolean"
      }
    ],
    
    "directives": [
      {
        "id": "d_validate_paths",
        "directive_type": "constraint",
        "description": "All file paths from user input must be validated",
        "decomposable": false
      }
    ]
  },
  
  "detection": {
    "pattern": "file operation with user-controlled path",
    "dangerous_patterns": ["../", "..\\", "/etc/", "C:\\"],
    "required_risk_indicators": ["user_input", "file_operation"]
  },
  
  "examples": {
    "vulnerable": [
      "string path = basePath + \"/\" + userFilename; fopen(path.c_str(), \"r\");"
    ],
    "safe": [
      "fs::path canonical = fs::canonical(basePath / userFilename); if(canonical.string().starts_with(basePath)) { fopen(canonical.c_str(), \"r\"); }"
    ]
  }
}
```

---

## Cryptographic Patterns

### SEC-CPP-009: Weak Cryptographic Algorithm

**Vulnerability:** Use of deprecated or weak crypto

**skill-0 Decomposition:**

```json
{
  "pattern_id": "SEC-CPP-009",
  "name": "Weak Cryptographic Algorithm",
  "category": "cryptographic",
  "severity": "high",
  "cwe_id": "CWE-327",
  
  "decomposition": {
    "actions": [
      {
        "id": "a_md5_hash",
        "name": "MD5 Hash",
        "action_type": "transform",
        "description": "Computes MD5 hash (cryptographically broken)",
        "deterministic": true,
        "risk_indicators": ["weak_crypto"]
      },
      {
        "id": "a_des_encrypt",
        "name": "DES Encryption",
        "action_type": "transform",
        "description": "Uses DES algorithm (broken)",
        "deterministic": true,
        "risk_indicators": ["weak_crypto"]
      }
    ],
    
    "rules": [
      {
        "id": "r_modern_algorithm",
        "name": "Uses Modern Algorithm",
        "condition_type": "validation",
        "condition": "algorithm in [SHA-256, AES-256, RSA-2048+]",
        "output": "boolean"
      }
    ],
    
    "directives": [
      {
        "id": "d_no_weak_crypto",
        "directive_type": "constraint",
        "description": "Never use MD5, SHA-1, DES, or RC4",
        "decomposable": false
      }
    ]
  },
  
  "detection": {
    "functions": ["MD5", "SHA1", "DES", "RC4"],
    "required_risk_indicators": ["weak_crypto"]
  },
  
  "examples": {
    "vulnerable": [
      "MD5_CTX ctx; MD5_Init(&ctx); // Weak algorithm"
    ],
    "safe": [
      "EVP_MD_CTX *ctx = EVP_MD_CTX_new(); EVP_DigestInit_ex(ctx, EVP_sha256(), NULL); // Strong"
    ]
  }
}
```

---

## Pattern Summary Table

| Pattern ID | Name | Category | Severity | CWE | Functions |
|------------|------|----------|----------|-----|-----------|
| SEC-CPP-001 | Unsafe Memory Copy | Memory Safety | Critical | CWE-120 | strcpy, sprintf, gets |
| SEC-CPP-002 | Use-After-Free | Memory Safety | Critical | CWE-416 | delete + dereference |
| SEC-CPP-003 | Memory Leak | Memory Safety | High | CWE-401 | new without delete |
| SEC-CPP-004 | RAII Violation | Resource Mgmt | High | CWE-404 | fopen, malloc |
| SEC-CPP-005 | Unsafe Type Cast | Type Safety | High | CWE-843 | C-cast, reinterpret_cast |
| SEC-CPP-006 | Race Condition | Concurrency | Critical | CWE-362 | shared access |
| SEC-CPP-007 | SQL Injection | Input Validation | Critical | CWE-89 | string concat in SQL |
| SEC-CPP-008 | Path Traversal | Input Validation | High | CWE-22 | file ops with user input |
| SEC-CPP-009 | Weak Crypto | Cryptographic | High | CWE-327 | MD5, DES, SHA1 |

---

## Pattern Application Strategy

### Detection Flow

```
Input: C++ Code (AST)
     │
     ▼
Extract Actions (function calls, operations)
     │
     ▼
Check Against Pattern Library
     │
     ├──▶ Direct Match (function name)
     │
     ├──▶ Context Analysis (parameters, control flow)
     │
     └──▶ Vector Search (similar vulnerabilities)
     │
     ▼
Apply Rules (bounds check, validation)
     │
     ▼
Generate Findings
     │
     ├──▶ Severity: Pattern + Context
     │
     ├──▶ Confidence: Rule verification
     │
     └──▶ Recommendation: From pattern
     │
     ▼
Output: Security Report
```

### Extensibility

New patterns can be added by:

1. **Define Actions**: What operations are involved?
2. **Define Rules**: What checks should be present?
3. **Define Directives**: What constraints/principles apply?
4. **Specify Detection**: Function names, indicators
5. **Provide Examples**: Vulnerable and safe code
6. **Add to Library**: JSON file in patterns/ directory

---

**End of Security Patterns Document**

*For implementation details, see ARCHITECTURE.md and IMPLEMENTATION_ROADMAP.md*
