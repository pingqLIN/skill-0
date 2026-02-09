# Skill-0 Examples

> 📚 Practical examples of skill decomposition across different domains

## Table of Contents

1. [Simple Skills](#simple-skills)
2. [Document Processing](#document-processing)
3. [API Integration](#api-integration)
4. [Creative Tools](#creative-tools)
5. [Data Analysis](#data-analysis)
6. [Development Tools](#development-tools)
7. [Real-World Skills](#real-world-skills)

---

## Simple Skills

### Example 1: Text File Reader

**Domain**: File I/O  
**Complexity**: Low  
**Elements**: 3 actions, 2 rules, 2 directives

```json
{
  "meta": {
    "skill_id": "claude__txt-reader",
    "name": "txt-reader",
    "skill_layer": "claude_skill",
    "title": "Plain Text File Reader",
    "description": "Read and return content from plain text files",
    "schema_version": "2.0.0",
    "parse_timestamp": "2026-01-28T10:00:00Z",
    "parser_version": "skill-0 v2.0",
    "parsed_by": "manual"
  },
  "decomposition": {
    "actions": [
      {
        "id": "a_001",
        "name": "Check File Path",
        "action_type": "io_read",
        "description": "Reads file path from user input",
        "deterministic": true,
        "immutable_elements": [],
        "mutable_elements": ["file_path"],
        "side_effects": []
      },
      {
        "id": "a_002",
        "name": "Read File Content",
        "action_type": "io_read",
        "description": "Reads entire file content into memory",
        "deterministic": true,
        "immutable_elements": ["encoding: UTF-8"],
        "mutable_elements": ["file_path"],
        "side_effects": ["memory_allocation"]
      },
      {
        "id": "a_003",
        "name": "Return Content",
        "action_type": "transform",
        "description": "Formats and returns file content to user",
        "deterministic": true,
        "immutable_elements": [],
        "mutable_elements": ["format_type"],
        "side_effects": []
      }
    ],
    "rules": [
      {
        "id": "r_001",
        "name": "Verify File Exists",
        "condition_type": "existence_check",
        "condition": "File exists at specified path",
        "output": "boolean",
        "description": "Prevents reading non-existent files"
      },
      {
        "id": "r_002",
        "name": "Check File Size",
        "condition_type": "range_check",
        "condition": "File size is within acceptable range",
        "output": "boolean",
        "description": "Ensures file is not too large to process"
      }
    ],
    "directives": [
      {
        "id": "d_001",
        "directive_type": "completion",
        "description": "File content successfully read and returned to user",
        "decomposable": false
      },
      {
        "id": "d_002",
        "directive_type": "constraint",
        "description": "Maximum file size: 10 MB",
        "decomposable": false
      }
    ]
  }
}
```

**Key Takeaways**:
- Simple linear flow: check → read → return
- Clear constraints defined upfront
- All actions are deterministic
- Minimal side effects

---

## Document Processing

### Example 2: PDF Table Extractor

**Domain**: Document Processing  
**Complexity**: Medium  
**Elements**: 6 actions, 3 rules, 4 directives

```json
{
  "meta": {
    "skill_id": "claude__pdf-table-extractor",
    "name": "pdf-table-extractor",
    "skill_layer": "claude_skill",
    "title": "PDF Table Extraction Tool",
    "description": "Extract tables from PDF documents and export to Excel format",
    "schema_version": "2.0.0",
    "parse_timestamp": "2026-01-28T10:15:00Z",
    "parser_version": "skill-0 v2.0",
    "parsed_by": "manual"
  },
  "decomposition": {
    "actions": [
      {
        "id": "a_001",
        "name": "Load PDF Document",
        "action_type": "io_read",
        "description": "Loads PDF file into memory for processing",
        "deterministic": true,
        "immutable_elements": ["file_format: PDF"],
        "mutable_elements": ["file_path"],
        "side_effects": ["memory_allocation"]
      },
      {
        "id": "a_002",
        "name": "Detect Table Regions",
        "action_type": "transform",
        "description": "Identifies rectangular regions containing table structures",
        "deterministic": false,
        "immutable_elements": ["algorithm: table_detection"],
        "mutable_elements": ["detection_threshold"],
        "side_effects": []
      },
      {
        "id": "a_003",
        "name": "Extract Table Data",
        "action_type": "transform",
        "description": "Parses table cells and extracts structured data",
        "deterministic": true,
        "immutable_elements": [],
        "mutable_elements": [],
        "side_effects": []
      },
      {
        "id": "a_004",
        "name": "Format as DataFrame",
        "action_type": "transform",
        "description": "Converts extracted data into pandas DataFrame",
        "deterministic": true,
        "immutable_elements": ["data_structure: DataFrame"],
        "mutable_elements": [],
        "side_effects": []
      },
      {
        "id": "a_005",
        "name": "Create Excel Workbook",
        "action_type": "io_write",
        "description": "Creates new Excel file with formatted tables",
        "deterministic": true,
        "immutable_elements": ["output_format: XLSX"],
        "mutable_elements": ["output_path", "sheet_names"],
        "side_effects": ["file_creation"]
      },
      {
        "id": "a_006",
        "name": "Write Tables to Sheets",
        "action_type": "io_write",
        "description": "Writes each table to separate Excel sheet",
        "deterministic": true,
        "immutable_elements": [],
        "mutable_elements": ["formatting_options"],
        "side_effects": ["file_modification"]
      }
    ],
    "rules": [
      {
        "id": "r_001",
        "name": "Validate PDF Contains Tables",
        "condition_type": "existence_check",
        "condition": "At least one table structure detected in PDF",
        "output": "boolean",
        "description": "Ensures PDF has extractable tables"
      },
      {
        "id": "r_002",
        "name": "Check Table Quality",
        "condition_type": "threshold_check",
        "condition": "Detected table has minimum confidence score",
        "output": "score",
        "description": "Filters out low-quality table detections"
      },
      {
        "id": "r_003",
        "name": "Verify Output Path Writable",
        "condition_type": "permission_check",
        "condition": "Output directory exists and is writable",
        "output": "boolean",
        "description": "Ensures Excel file can be created"
      }
    ],
    "directives": [
      {
        "id": "d_001",
        "directive_type": "completion",
        "description": "All tables extracted and saved to Excel with proper formatting",
        "decomposable": true,
        "decomposition_hint": "Can split into: all tables detected, all tables formatted, all sheets written"
      },
      {
        "id": "d_002",
        "directive_type": "knowledge",
        "description": "Table detection uses Camelot or Tabula algorithms",
        "decomposable": false
      },
      {
        "id": "d_003",
        "directive_type": "constraint",
        "description": "Maximum PDF size: 50 MB, Maximum tables per file: 100",
        "decomposable": true,
        "decomposition_hint": "Can split into separate size and count constraints"
      },
      {
        "id": "d_004",
        "directive_type": "strategy",
        "description": "If table detection fails, retry with adjusted threshold",
        "decomposable": false
      }
    ]
  },
  "execution_paths": [
    {
      "path_name": "Successful Extraction",
      "sequence": ["a_001", "a_002", "r_001", "r_002", "a_003", "a_004", "r_003", "a_005", "a_006", "d_001"],
      "description": "Normal flow when tables are detected and extracted"
    },
    {
      "path_name": "No Tables Found",
      "sequence": ["a_001", "a_002", "r_001"],
      "description": "Abort when no tables detected in PDF"
    }
  ]
}
```

**Key Takeaways**:
- Non-deterministic table detection step
- Quality checks with threshold
- Multiple directives for different purposes
- Clear execution paths documented

---

## API Integration

### Example 3: REST API Client

**Domain**: External Integration  
**Complexity**: Medium  
**Elements**: 5 actions, 4 rules, 3 directives

```json
{
  "decomposition": {
    "actions": [
      {
        "id": "a_001",
        "name": "Build API Request",
        "action_type": "transform",
        "description": "Constructs HTTP request with headers and parameters",
        "deterministic": true,
        "immutable_elements": ["protocol: HTTPS", "method: GET/POST"],
        "mutable_elements": ["endpoint", "headers", "body"],
        "side_effects": []
      },
      {
        "id": "a_002",
        "name": "Send HTTP Request",
        "action_type": "external_call",
        "description": "Sends request to remote API endpoint",
        "deterministic": false,
        "immutable_elements": [],
        "mutable_elements": ["url", "timeout"],
        "side_effects": ["network_traffic"]
      },
      {
        "id": "a_003",
        "name": "Parse JSON Response",
        "action_type": "transform",
        "description": "Parses JSON response body into structured data",
        "deterministic": true,
        "immutable_elements": ["format: JSON"],
        "mutable_elements": [],
        "side_effects": []
      },
      {
        "id": "a_004",
        "name": "Handle Error Response",
        "action_type": "transform",
        "description": "Processes error responses and extracts error details",
        "deterministic": true,
        "immutable_elements": [],
        "mutable_elements": [],
        "side_effects": []
      },
      {
        "id": "a_005",
        "name": "Return Result",
        "action_type": "transform",
        "description": "Formats and returns API response to caller",
        "deterministic": true,
        "immutable_elements": [],
        "mutable_elements": ["format_type"],
        "side_effects": []
      }
    ],
    "rules": [
      {
        "id": "r_001",
        "name": "Validate API Endpoint",
        "condition_type": "validation",
        "condition": "Endpoint URL is valid and reachable",
        "output": "boolean",
        "description": "Ensures API endpoint is properly formatted"
      },
      {
        "id": "r_002",
        "name": "Check Authentication",
        "condition_type": "permission_check",
        "condition": "Valid API key or token is present",
        "output": "boolean",
        "description": "Verifies authentication credentials exist"
      },
      {
        "id": "r_003",
        "name": "Verify Response Status",
        "condition_type": "range_check",
        "condition": "HTTP status code is in 2xx range",
        "output": "boolean",
        "description": "Checks if request was successful"
      },
      {
        "id": "r_004",
        "name": "Check Rate Limit",
        "condition_type": "threshold_check",
        "condition": "Rate limit not exceeded for current time window",
        "output": "boolean",
        "description": "Prevents exceeding API rate limits"
      }
    ],
    "directives": [
      {
        "id": "d_001",
        "directive_type": "completion",
        "description": "API response received, parsed, and returned successfully",
        "decomposable": false
      },
      {
        "id": "d_002",
        "directive_type": "strategy",
        "description": "Retry failed requests up to 3 times with exponential backoff",
        "decomposable": true,
        "decomposition_hint": "Can detail retry logic: initial delay, backoff multiplier, max attempts"
      },
      {
        "id": "d_003",
        "directive_type": "constraint",
        "description": "Request timeout: 30 seconds, Rate limit: 100 requests per minute",
        "decomposable": true
      }
    ]
  }
}
```

**Key Takeaways**:
- External call is non-deterministic
- Authentication and rate limiting checks
- Error handling explicitly modeled
- Retry strategy documented as directive

---

## Creative Tools

### Example 4: Image Generator

**Domain**: Creative AI  
**Complexity**: Medium  
**Elements**: 7 actions, 2 rules, 5 directives

```json
{
  "decomposition": {
    "actions": [
      {
        "id": "a_001",
        "name": "Receive User Prompt",
        "action_type": "await_input",
        "description": "Waits for and receives text prompt from user",
        "deterministic": false,
        "immutable_elements": [],
        "mutable_elements": [],
        "side_effects": []
      },
      {
        "id": "a_002",
        "name": "Enhance Prompt",
        "action_type": "llm_inference",
        "description": "Uses LLM to enhance and detail the prompt",
        "deterministic": false,
        "immutable_elements": ["model: claude-3"],
        "mutable_elements": ["enhancement_style"],
        "side_effects": []
      },
      {
        "id": "a_003",
        "name": "Generate Image",
        "action_type": "external_call",
        "description": "Calls image generation API with enhanced prompt",
        "deterministic": false,
        "immutable_elements": ["api: dalle-3"],
        "mutable_elements": ["size", "quality", "style"],
        "side_effects": ["api_cost"]
      },
      {
        "id": "a_004",
        "name": "Download Image",
        "action_type": "io_read",
        "description": "Downloads generated image from temporary URL",
        "deterministic": true,
        "immutable_elements": [],
        "mutable_elements": ["image_url"],
        "side_effects": ["network_traffic"]
      },
      {
        "id": "a_005",
        "name": "Apply Filters",
        "action_type": "transform",
        "description": "Applies optional post-processing filters",
        "deterministic": true,
        "immutable_elements": [],
        "mutable_elements": ["filter_types"],
        "side_effects": []
      },
      {
        "id": "a_006",
        "name": "Save to File",
        "action_type": "io_write",
        "description": "Saves final image to local filesystem",
        "deterministic": true,
        "immutable_elements": ["format: PNG"],
        "mutable_elements": ["output_path", "filename"],
        "side_effects": ["file_creation"]
      },
      {
        "id": "a_007",
        "name": "Display to User",
        "action_type": "io_write",
        "description": "Shows generated image to user in interface",
        "deterministic": true,
        "immutable_elements": [],
        "mutable_elements": [],
        "side_effects": []
      }
    ],
    "rules": [
      {
        "id": "r_001",
        "name": "Validate Prompt Length",
        "condition_type": "range_check",
        "condition": "Prompt is between 1 and 1000 characters",
        "output": "boolean",
        "description": "Ensures prompt is within acceptable length"
      },
      {
        "id": "r_002",
        "name": "Check Content Policy",
        "condition_type": "validation",
        "condition": "Prompt does not violate content policy",
        "output": "boolean",
        "description": "Filters inappropriate content requests"
      }
    ],
    "directives": [
      {
        "id": "d_001",
        "directive_type": "completion",
        "description": "Image generated, processed, and displayed to user",
        "decomposable": false
      },
      {
        "id": "d_002",
        "directive_type": "preference",
        "description": "User prefers high-quality images with natural style",
        "decomposable": false
      },
      {
        "id": "d_003",
        "directive_type": "principle",
        "description": "Enhance prompts to maximize image quality without changing user intent",
        "decomposable": false
      },
      {
        "id": "d_004",
        "directive_type": "knowledge",
        "description": "DALL-E 3 supports sizes: 1024x1024, 1792x1024, 1024x1792",
        "decomposable": false
      },
      {
        "id": "d_005",
        "directive_type": "constraint",
        "description": "Maximum 10 images per user per hour",
        "decomposable": false
      }
    ]
  }
}
```

**Key Takeaways**:
- Multiple non-deterministic operations (user input, LLM, image generation)
- User preferences documented as directives
- Content policy check for safety
- Knowledge about API constraints

---

## Data Analysis

### Example 5: CSV Analyzer

**Domain**: Data Analysis  
**Complexity**: High  
**Elements**: 10 actions, 5 rules, 4 directives

```json
{
  "decomposition": {
    "actions": [
      {
        "id": "a_001",
        "name": "Load CSV File",
        "action_type": "io_read",
        "description": "Reads CSV file into pandas DataFrame",
        "deterministic": true,
        "immutable_elements": ["format: CSV"],
        "mutable_elements": ["file_path", "encoding", "delimiter"],
        "side_effects": ["memory_allocation"]
      },
      {
        "id": "a_002",
        "name": "Detect Column Types",
        "action_type": "compute",
        "description": "Automatically detects data types for each column",
        "deterministic": true,
        "immutable_elements": [],
        "mutable_elements": [],
        "side_effects": []
      },
      {
        "id": "a_003",
        "name": "Calculate Statistics",
        "action_type": "compute",
        "description": "Computes descriptive statistics for numeric columns",
        "deterministic": true,
        "immutable_elements": ["stats: mean, median, std, min, max"],
        "mutable_elements": [],
        "side_effects": []
      },
      {
        "id": "a_004",
        "name": "Identify Missing Values",
        "action_type": "compute",
        "description": "Counts and locates missing values per column",
        "deterministic": true,
        "immutable_elements": [],
        "mutable_elements": [],
        "side_effects": []
      },
      {
        "id": "a_005",
        "name": "Detect Outliers",
        "action_type": "compute",
        "description": "Identifies statistical outliers using IQR method",
        "deterministic": true,
        "immutable_elements": ["method: IQR"],
        "mutable_elements": ["threshold"],
        "side_effects": []
      },
      {
        "id": "a_006",
        "name": "Generate Correlation Matrix",
        "action_type": "compute",
        "description": "Calculates pairwise correlations between numeric columns",
        "deterministic": true,
        "immutable_elements": ["method: pearson"],
        "mutable_elements": [],
        "side_effects": []
      },
      {
        "id": "a_007",
        "name": "Create Visualizations",
        "action_type": "transform",
        "description": "Generates histograms and box plots for key columns",
        "deterministic": true,
        "immutable_elements": ["library: matplotlib"],
        "mutable_elements": ["plot_types"],
        "side_effects": ["memory_allocation"]
      },
      {
        "id": "a_008",
        "name": "Generate Summary Report",
        "action_type": "llm_inference",
        "description": "Uses LLM to create natural language summary of findings",
        "deterministic": false,
        "immutable_elements": [],
        "mutable_elements": ["report_style"],
        "side_effects": []
      },
      {
        "id": "a_009",
        "name": "Export Results",
        "action_type": "io_write",
        "description": "Saves analysis results to HTML report",
        "deterministic": true,
        "immutable_elements": ["format: HTML"],
        "mutable_elements": ["output_path"],
        "side_effects": ["file_creation"]
      },
      {
        "id": "a_010",
        "name": "Display Interactive Report",
        "action_type": "io_write",
        "description": "Opens HTML report in web browser",
        "deterministic": true,
        "immutable_elements": [],
        "mutable_elements": [],
        "side_effects": []
      }
    ],
    "rules": [
      {
        "id": "r_001",
        "name": "Validate CSV Format",
        "condition_type": "validation",
        "condition": "File is valid CSV with consistent column count",
        "output": "boolean",
        "description": "Ensures file can be parsed as CSV"
      },
      {
        "id": "r_002",
        "name": "Check Minimum Rows",
        "condition_type": "threshold_check",
        "condition": "Dataset has at least 10 rows",
        "output": "boolean",
        "description": "Ensures sufficient data for analysis"
      },
      {
        "id": "r_003",
        "name": "Verify Numeric Columns",
        "condition_type": "existence_check",
        "condition": "At least one numeric column exists",
        "output": "boolean",
        "description": "Required for statistical analysis"
      },
      {
        "id": "r_004",
        "name": "Check Data Quality",
        "condition_type": "threshold_check",
        "condition": "Missing values are less than 50% per column",
        "output": "boolean",
        "description": "Ensures data is usable"
      },
      {
        "id": "r_005",
        "name": "Validate Column Names",
        "condition_type": "validation",
        "condition": "All column names are unique and non-empty",
        "output": "boolean",
        "description": "Prevents ambiguous references"
      }
    ],
    "directives": [
      {
        "id": "d_001",
        "directive_type": "completion",
        "description": "Complete analysis performed with statistics, visualizations, and summary",
        "decomposable": true,
        "decomposition_hint": "Can split into: stats computed, visuals created, report generated"
      },
      {
        "id": "d_002",
        "directive_type": "principle",
        "description": "Provide actionable insights, not just raw statistics",
        "decomposable": false
      },
      {
        "id": "d_003",
        "directive_type": "constraint",
        "description": "Maximum file size: 100 MB, Maximum columns: 1000",
        "decomposable": true
      },
      {
        "id": "d_004",
        "directive_type": "strategy",
        "description": "For large datasets, sample 10,000 rows for visualization",
        "decomposable": false
      }
    ]
  }
}
```

**Key Takeaways**:
- Complex multi-step analysis workflow
- Multiple validation rules for data quality
- Mix of deterministic (stats) and non-deterministic (LLM summary)
- Strategy for handling large datasets

---

## Development Tools

### Example 6: Code Formatter

**Domain**: Development Tools  
**Complexity**: Low  
**Elements**: 4 actions, 3 rules, 3 directives

```json
{
  "decomposition": {
    "actions": [
      {
        "id": "a_001",
        "name": "Read Source File",
        "action_type": "io_read",
        "description": "Reads source code file into memory",
        "deterministic": true,
        "immutable_elements": [],
        "mutable_elements": ["file_path"],
        "side_effects": []
      },
      {
        "id": "a_002",
        "name": "Parse Code Syntax",
        "action_type": "transform",
        "description": "Parses code into abstract syntax tree",
        "deterministic": true,
        "immutable_elements": ["language: Python"],
        "mutable_elements": [],
        "side_effects": []
      },
      {
        "id": "a_003",
        "name": "Apply Formatting Rules",
        "action_type": "transform",
        "description": "Applies Black formatting rules to AST",
        "deterministic": true,
        "immutable_elements": ["formatter: Black", "line_length: 88"],
        "mutable_elements": ["config_options"],
        "side_effects": []
      },
      {
        "id": "a_004",
        "name": "Write Formatted Code",
        "action_type": "io_write",
        "description": "Writes formatted code back to file",
        "deterministic": true,
        "immutable_elements": [],
        "mutable_elements": ["file_path"],
        "side_effects": ["file_modification"]
      }
    ],
    "rules": [
      {
        "id": "r_001",
        "name": "Validate Python Syntax",
        "condition_type": "validation",
        "condition": "Code is syntactically valid Python",
        "output": "boolean",
        "description": "Ensures code can be parsed"
      },
      {
        "id": "r_002",
        "name": "Check File Writable",
        "condition_type": "permission_check",
        "condition": "File is writable and not locked",
        "output": "boolean",
        "description": "Ensures file can be modified"
      },
      {
        "id": "r_003",
        "name": "Verify Changes Made",
        "condition_type": "state_check",
        "condition": "Formatted code differs from original",
        "output": "boolean",
        "description": "Determines if formatting changed anything"
      }
    ],
    "directives": [
      {
        "id": "d_001",
        "directive_type": "completion",
        "description": "Code successfully formatted and saved",
        "decomposable": false
      },
      {
        "id": "d_002",
        "directive_type": "principle",
        "description": "Follow Black style guide: consistent, deterministic formatting",
        "decomposable": false
      },
      {
        "id": "d_003",
        "directive_type": "preference",
        "description": "Preserve original file encoding and line endings",
        "decomposable": false
      }
    ]
  }
}
```

**Key Takeaways**:
- Simple, linear workflow
- All operations are deterministic
- Validation before and after formatting
- Style guide as principle directive

---

## Real-World Skills

### Example 7: Email Newsletter Generator

**Domain**: Content Generation  
**Complexity**: High  
**Elements**: 12 actions, 6 rules, 6 directives

This example demonstrates a complete, production-ready skill with:
- Multi-source data aggregation
- LLM-based content generation
- Template rendering
- Email delivery
- Error handling

```json
{
  "meta": {
    "skill_id": "claude__newsletter-generator",
    "name": "newsletter-generator",
    "skill_layer": "claude_skill",
    "title": "Automated Newsletter Generator",
    "description": "Generate and send personalized email newsletters with curated content",
    "schema_version": "2.0.0"
  },
  "decomposition": {
    "actions": [
      {
        "id": "a_001",
        "name": "Fetch RSS Feeds",
        "action_type": "external_call",
        "description": "Retrieves latest articles from configured RSS feeds",
        "deterministic": false,
        "immutable_elements": ["protocol: RSS/Atom"],
        "mutable_elements": ["feed_urls"],
        "side_effects": ["network_traffic"]
      },
      {
        "id": "a_002",
        "name": "Parse Article Data",
        "action_type": "transform",
        "description": "Extracts title, summary, URL from feed entries",
        "deterministic": true,
        "immutable_elements": [],
        "mutable_elements": [],
        "side_effects": []
      },
      {
        "id": "a_003",
        "name": "Filter by Topics",
        "action_type": "transform",
        "description": "Filters articles matching target topics/keywords",
        "deterministic": true,
        "immutable_elements": [],
        "mutable_elements": ["topic_list", "keywords"],
        "side_effects": []
      },
      {
        "id": "a_004",
        "name": "Rank by Relevance",
        "action_type": "llm_inference",
        "description": "Uses LLM to rank articles by relevance and quality",
        "deterministic": false,
        "immutable_elements": [],
        "mutable_elements": ["ranking_criteria"],
        "side_effects": []
      },
      {
        "id": "a_005",
        "name": "Select Top Articles",
        "action_type": "transform",
        "description": "Selects top N articles for inclusion",
        "deterministic": true,
        "immutable_elements": [],
        "mutable_elements": ["count"],
        "side_effects": []
      },
      {
        "id": "a_006",
        "name": "Generate Summaries",
        "action_type": "llm_inference",
        "description": "Creates concise summaries for each article",
        "deterministic": false,
        "immutable_elements": ["max_words: 50"],
        "mutable_elements": ["style"],
        "side_effects": []
      },
      {
        "id": "a_007",
        "name": "Generate Introduction",
        "action_type": "llm_inference",
        "description": "Writes personalized introduction paragraph",
        "deterministic": false,
        "immutable_elements": [],
        "mutable_elements": ["tone", "personalization_data"],
        "side_effects": []
      },
      {
        "id": "a_008",
        "name": "Load Email Template",
        "action_type": "io_read",
        "description": "Reads HTML email template file",
        "deterministic": true,
        "immutable_elements": ["format: HTML"],
        "mutable_elements": ["template_path"],
        "side_effects": []
      },
      {
        "id": "a_009",
        "name": "Render Email Content",
        "action_type": "transform",
        "description": "Populates template with generated content",
        "deterministic": true,
        "immutable_elements": ["engine: Jinja2"],
        "mutable_elements": ["template_vars"],
        "side_effects": []
      },
      {
        "id": "a_010",
        "name": "Load Subscriber List",
        "action_type": "io_read",
        "description": "Reads subscriber emails from database",
        "deterministic": true,
        "immutable_elements": [],
        "mutable_elements": ["db_query"],
        "side_effects": []
      },
      {
        "id": "a_011",
        "name": "Send Emails",
        "action_type": "external_call",
        "description": "Sends personalized emails via SMTP",
        "deterministic": false,
        "immutable_elements": ["protocol: SMTP"],
        "mutable_elements": ["smtp_config", "batch_size"],
        "side_effects": ["email_sent", "network_traffic"]
      },
      {
        "id": "a_012",
        "name": "Log Campaign Stats",
        "action_type": "io_write",
        "description": "Records send statistics to database",
        "deterministic": true,
        "immutable_elements": [],
        "mutable_elements": [],
        "side_effects": ["database_write"]
      }
    ],
    "rules": [
      {
        "id": "r_001",
        "name": "Validate Feed URLs",
        "condition_type": "validation",
        "condition": "All RSS feed URLs are valid and accessible",
        "output": "boolean",
        "description": "Ensures feeds can be fetched"
      },
      {
        "id": "r_002",
        "name": "Check Minimum Articles",
        "condition_type": "threshold_check",
        "condition": "At least 5 articles available after filtering",
        "output": "boolean",
        "description": "Ensures sufficient content for newsletter"
      },
      {
        "id": "r_003",
        "name": "Validate Template",
        "condition_type": "validation",
        "condition": "Email template exists and is valid HTML",
        "output": "boolean",
        "description": "Ensures template can be rendered"
      },
      {
        "id": "r_004",
        "name": "Check Subscribers Exist",
        "condition_type": "existence_check",
        "condition": "At least one active subscriber in database",
        "output": "boolean",
        "description": "Ensures there are recipients"
      },
      {
        "id": "r_005",
        "name": "Verify SMTP Connection",
        "condition_type": "state_check",
        "condition": "SMTP server is reachable and authenticated",
        "output": "boolean",
        "description": "Ensures emails can be sent"
      },
      {
        "id": "r_006",
        "name": "Check Daily Send Limit",
        "condition_type": "threshold_check",
        "condition": "Daily email quota not exceeded",
        "output": "boolean",
        "description": "Prevents exceeding email limits"
      }
    ],
    "directives": [
      {
        "id": "d_001",
        "directive_type": "completion",
        "description": "Newsletter generated, sent to all active subscribers, and stats logged",
        "decomposable": true,
        "decomposition_hint": "Can split into: content generated, emails sent, stats recorded"
      },
      {
        "id": "d_002",
        "directive_type": "principle",
        "description": "Prioritize content quality over quantity - better few great articles than many mediocre ones",
        "decomposable": false
      },
      {
        "id": "d_003",
        "directive_type": "preference",
        "description": "Use friendly, conversational tone in generated content",
        "decomposable": false
      },
      {
        "id": "d_004",
        "directive_type": "constraint",
        "description": "Email size limit: 100 KB, Send rate: 100 emails/minute, Newsletter frequency: Weekly",
        "decomposable": true
      },
      {
        "id": "d_005",
        "directive_type": "strategy",
        "description": "If article ranking fails, fall back to chronological order",
        "decomposable": false
      },
      {
        "id": "d_006",
        "directive_type": "knowledge",
        "description": "RSS/Atom feed formats, SMTP protocol, Jinja2 templating",
        "decomposable": true,
        "decomposition_hint": "Can detail each technology's specifics"
      }
    ]
  },
  "execution_paths": [
    {
      "path_name": "Successful Generation and Send",
      "sequence": [
        "r_001", "a_001", "a_002", "a_003", "r_002", 
        "a_004", "a_005", "a_006", "a_007",
        "r_003", "a_008", "a_009",
        "r_004", "a_010", "r_005", "r_006", "a_011", "a_012",
        "d_001"
      ],
      "description": "Complete workflow when all checks pass"
    },
    {
      "path_name": "Insufficient Content",
      "sequence": ["r_001", "a_001", "a_002", "a_003", "r_002"],
      "description": "Abort when not enough articles available"
    },
    {
      "path_name": "SMTP Failure with Retry",
      "sequence": [
        "a_001", "a_002", "a_003", "a_004", "a_005", "a_006", "a_007",
        "a_008", "a_009", "a_010", "r_005", "r_005", "r_005"
      ],
      "description": "Retry SMTP connection up to 3 times (per d_005 strategy)"
    }
  ]
}
```

**Key Takeaways**:
- Complex multi-stage pipeline
- Multiple external dependencies
- Comprehensive validation at each stage
- Explicit fallback strategies
- Real-world constraints (rate limits, quotas)
- Detailed execution paths including error scenarios

---

## Pattern Summary

### Common Action Sequences

| Pattern | Sequence | Use Cases |
|---------|----------|-----------|
| **Read-Process-Write** | io_read → transform → io_write | File processing, data conversion |
| **Fetch-Parse-Store** | external_call → transform → io_write | API integration, web scraping |
| **Load-Analyze-Report** | io_read → compute → llm_inference → io_write | Data analysis, reporting |
| **Input-Generate-Output** | await_input → llm_inference → io_write | Creative tools, chatbots |

### Typical Element Ratios

| Complexity | Actions | Rules | Directives | Example |
|------------|---------|-------|------------|---------|
| **Simple** | 2-4 | 1-2 | 1-2 | File reader, formatter |
| **Medium** | 5-8 | 2-4 | 3-5 | PDF extractor, API client |
| **Complex** | 9+ | 5+ | 5+ | Newsletter generator, data pipeline |

### Rule Placement Patterns

- **Pre-validation**: existence_check, permission_check (before actions)
- **Mid-validation**: threshold_check, range_check (between actions)
- **Post-validation**: state_check, consistency_check (after actions)

### Directive Type Usage

| Type | % Usage | Common In |
|------|---------|-----------|
| completion | 35% | All skills |
| constraint | 25% | Production skills |
| strategy | 20% | Complex skills |
| knowledge | 10% | Integration skills |
| principle | 5% | Creative tools |
| preference | 5% | User-facing skills |

---

*For more examples, see the [parsed/](parsed/) directory in the repository.*
