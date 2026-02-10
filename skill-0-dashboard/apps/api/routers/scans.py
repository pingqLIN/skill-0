<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
"""Scans API router"""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import JSONResponse

from ..schemas.scan import ScanSummary, ScanDetail, ScanExport
from ..services.governance import GovernanceService
from ..dependencies import get_governance_service

router = APIRouter()


# Detection standards used by the advanced analyzer
DETECTION_STANDARDS = [
    {
        "name": "OWASP LLM Top 10 - Prompt Injection",
        "url": "https://genai.owasp.org/llmrisk/llm01-prompt-injection/",
        "description": "Industry standard for LLM security vulnerabilities",
    },
    {
        "name": "Vigil-LLM YARA Rules",
        "url": "https://github.com/deadbits/vigil-llm/tree/main/data/yara",
        "description": "Pattern-based prompt injection detection rules",
    },
    {
        "name": "ProtectAI LLM Guard",
        "url": "https://github.com/protectai/llm-guard",
        "description": "ML-based and heuristic prompt injection detection",
    },
    {
        "name": "skill-0 Governance Spec",
        "url": "https://github.com/user/skill-0/blob/main/governance/GOVERNANCE.md",
        "description": "Project-specific security rules (SEC001-SEC009)",
    },
]


class ScanListItem(ScanSummary):
    """Scan list item with skill info"""

    skill_id: str
    skill_name: str


@router.get("/scans", response_model=List[ScanListItem])
def list_scans(
    limit: int = Query(
        100, ge=1, le=500, description="Maximum number of scans to return"
    ),
    service: GovernanceService = Depends(get_governance_service),
) -> List[ScanListItem]:
    """List all recent scans across all skills"""
    data = service.list_scans(limit=limit)
    return [ScanListItem(**item) for item in data]


@router.get("/scans/{skill_id}", response_model=List[ScanDetail])
def get_skill_scans(
    skill_id: str,
    service: GovernanceService = Depends(get_governance_service),
) -> List[ScanDetail]:
    """Get scan history for a specific skill"""
    data = service.get_skill_scans(skill_id)
    return [ScanDetail(**item) for item in data]


@router.get("/scans/{skill_id}/export")
def export_skill_scan(
    skill_id: str,
    format: str = Query("json", description="Export format (json or html)"),
    service: GovernanceService = Depends(get_governance_service),
):
    """Export scan report for a skill with full context and references"""
    # Get skill info
    skill = service.get_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    # Get scan history
    scans = service.get_skill_scans(skill_id)
    if not scans:
        raise HTTPException(status_code=404, detail="No scans found for skill")

    latest_scan = scans[0]

    export_data = {
        "skill_name": skill["name"],
        "skill_id": skill_id,
        "scan": latest_scan,
        "detection_standards": DETECTION_STANDARDS,
        "export_date": datetime.now().isoformat(),
        "export_format": format,
    }

    if format == "html":
        # Generate HTML report
        html_content = _generate_html_report(export_data)
        return JSONResponse(
            content={"html": html_content}, headers={"Content-Type": "application/json"}
        )

    return export_data


def _generate_html_report(data: dict) -> str:
    """Generate HTML report from export data"""
    skill_name = data["skill_name"]
    scan = data["scan"]
    standards = data["detection_standards"]

    findings_html = ""
    for i, f in enumerate(scan.get("findings", []), 1):
        severity_badge = f.get("adjusted_severity", f.get("severity", "unknown"))
        context_badge = "code" if f.get("in_code_block") else "prose"
        context_class = "code-context" if f.get("in_code_block") else "prose-context"

        severity_change = ""
        if f.get("severity_changed"):
            severity_change = f"""
            <span class="severity-change">
                (was {f.get("original_severity", "N/A")})
            </span>
            """

        standard_link = ""
        if f.get("standard_url"):
            standard_link = f"""
            <a href="{f["standard_url"]}" target="_blank" class="standard-link">
                {f.get("detection_standard", "Reference")}
            </a>
            """

        findings_html += f"""
        <div class="finding">
            <div class="finding-header">
                <span class="finding-number">#{i}</span>
                <span class="rule-id">{f.get("rule_id", "N/A")}</span>
                <span class="rule-name">{f.get("rule_name", "Unknown")}</span>
                <span class="severity severity-{severity_badge}">{severity_badge}</span>
                {severity_change}
                <span class="context {context_class}">{context_badge}</span>
            </div>
            <div class="finding-location">
                Line {f.get("line_number", 0)}: <code>{f.get("line_content", "")[:80]}...</code>
            </div>
            <div class="finding-reason">
                {f.get("adjustment_reason", "")}
            </div>
            <div class="finding-standard">
                {standard_link}
            </div>
        </div>
        """

    standards_html = ""
    for s in standards:
        standards_html += f"""
        <div class="standard">
            <a href="{s["url"]}" target="_blank">{s["name"]}</a>
            <p>{s["description"]}</p>
        </div>
        """

    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>Security Scan Report: {skill_name}</title>
    <style>
        body {{ font-family: system-ui, -apple-system, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #1a1a2e; }}
        .summary {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; }}
        .summary-item {{ text-align: center; }}
        .summary-value {{ font-size: 2em; font-weight: bold; }}
        .summary-label {{ color: #666; }}
        .risk-safe {{ color: #22c55e; }}
        .risk-low {{ color: #84cc16; }}
        .risk-medium {{ color: #eab308; }}
        .risk-high {{ color: #f97316; }}
        .risk-critical {{ color: #ef4444; }}
        .finding {{ border: 1px solid #e5e7eb; border-radius: 8px; padding: 15px; margin-bottom: 15px; }}
        .finding-header {{ display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }}
        .finding-number {{ font-weight: bold; color: #666; }}
        .rule-id {{ background: #e5e7eb; padding: 2px 8px; border-radius: 4px; font-family: monospace; }}
        .severity {{ padding: 2px 8px; border-radius: 4px; color: white; font-size: 0.85em; }}
        .severity-info {{ background: #3b82f6; }}
        .severity-low {{ background: #22c55e; }}
        .severity-medium {{ background: #eab308; }}
        .severity-high {{ background: #f97316; }}
        .severity-critical {{ background: #ef4444; }}
        .severity-change {{ color: #666; font-style: italic; }}
        .context {{ padding: 2px 8px; border-radius: 4px; font-size: 0.85em; }}
        .code-context {{ background: #dbeafe; color: #1e40af; }}
        .prose-context {{ background: #fef3c7; color: #92400e; }}
        .finding-location {{ margin-top: 10px; }}
        .finding-location code {{ background: #f3f4f6; padding: 2px 6px; border-radius: 4px; }}
        .finding-reason {{ margin-top: 10px; color: #666; font-size: 0.9em; }}
        .finding-standard {{ margin-top: 10px; }}
        .standard-link {{ color: #3b82f6; text-decoration: none; font-size: 0.85em; }}
        .standard-link:hover {{ text-decoration: underline; }}
        .standards-section {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; }}
        .standard {{ margin-bottom: 15px; }}
        .standard a {{ color: #3b82f6; font-weight: 500; }}
        .standard p {{ margin: 5px 0 0 0; color: #666; font-size: 0.9em; }}
        .export-footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; color: #666; font-size: 0.85em; }}
    </style>
</head>
<body>
    <h1>Security Scan Report</h1>
    <h2>{skill_name}</h2>
    
    <div class="summary">
        <div class="summary-grid">
            <div class="summary-item">
                <div class="summary-value risk-{scan.get("risk_level", "unknown")}">{scan.get("risk_level", "N/A").upper()}</div>
                <div class="summary-label">Risk Level</div>
            </div>
            <div class="summary-item">
                <div class="summary-value">{scan.get("risk_score", 0)}</div>
                <div class="summary-label">Risk Score</div>
            </div>
            <div class="summary-item">
                <div class="summary-value">{scan.get("findings_count", 0)}</div>
                <div class="summary-label">Total Findings</div>
            </div>
            <div class="summary-item">
                <div class="summary-value">{scan.get("findings_in_code_blocks", 0)}</div>
                <div class="summary-label">In Code Blocks</div>
            </div>
            <div class="summary-item">
                <div class="summary-value">{scan.get("severity_adjustments", 0)}</div>
                <div class="summary-label">Adjusted</div>
            </div>
        </div>
    </div>
    
    <h3>Findings</h3>
    {findings_html if findings_html else "<p>No security findings.</p>"}
    
    <div class="standards-section">
        <h3>Detection Standards</h3>
        {standards_html}
    </div>
    
    <div class="export-footer">
        <p>Exported: {data["export_date"]}</p>
        <p>Scanner: Advanced Skill Analyzer v{scan.get("scanner_version", "2.1.0")}</p>
    </div>
</body>
</html>
    """
=======
=======
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
"""Scans API router"""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import JSONResponse

from ..schemas.scan import ScanSummary, ScanDetail, ScanExport
from ..services.governance import GovernanceService
from ..dependencies import get_governance_service

router = APIRouter()


# Detection standards used by the advanced analyzer
DETECTION_STANDARDS = [
    {
        "name": "OWASP LLM Top 10 - Prompt Injection",
        "url": "https://genai.owasp.org/llmrisk/llm01-prompt-injection/",
        "description": "Industry standard for LLM security vulnerabilities",
    },
    {
        "name": "Vigil-LLM YARA Rules",
        "url": "https://github.com/deadbits/vigil-llm/tree/main/data/yara",
        "description": "Pattern-based prompt injection detection rules",
    },
    {
        "name": "ProtectAI LLM Guard",
        "url": "https://github.com/protectai/llm-guard",
        "description": "ML-based and heuristic prompt injection detection",
    },
    {
        "name": "skill-0 Governance Spec",
        "url": "https://github.com/user/skill-0/blob/main/governance/GOVERNANCE.md",
        "description": "Project-specific security rules (SEC001-SEC009)",
    },
]


class ScanListItem(ScanSummary):
    """Scan list item with skill info"""

    skill_id: str
    skill_name: str


@router.get("/scans", response_model=List[ScanListItem])
def list_scans(
    limit: int = Query(
        100, ge=1, le=500, description="Maximum number of scans to return"
    ),
    service: GovernanceService = Depends(get_governance_service),
) -> List[ScanListItem]:
    """List all recent scans across all skills"""
    data = service.list_scans(limit=limit)
    return [ScanListItem(**item) for item in data]


@router.get("/scans/{skill_id}", response_model=List[ScanDetail])
def get_skill_scans(
    skill_id: str,
    service: GovernanceService = Depends(get_governance_service),
) -> List[ScanDetail]:
    """Get scan history for a specific skill"""
    data = service.get_skill_scans(skill_id)
    return [ScanDetail(**item) for item in data]


@router.get("/scans/{skill_id}/export")
def export_skill_scan(
    skill_id: str,
    format: str = Query("json", description="Export format (json or html)"),
    service: GovernanceService = Depends(get_governance_service),
):
    """Export scan report for a skill with full context and references"""
    # Get skill info
    skill = service.get_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    # Get scan history
    scans = service.get_skill_scans(skill_id)
    if not scans:
        raise HTTPException(status_code=404, detail="No scans found for skill")

    latest_scan = scans[0]

    export_data = {
        "skill_name": skill["name"],
        "skill_id": skill_id,
        "scan": latest_scan,
        "detection_standards": DETECTION_STANDARDS,
        "export_date": datetime.now().isoformat(),
        "export_format": format,
    }

    if format == "html":
        # Generate HTML report
        html_content = _generate_html_report(export_data)
        return JSONResponse(
            content={"html": html_content}, headers={"Content-Type": "application/json"}
        )

    return export_data


def _generate_html_report(data: dict) -> str:
    """Generate HTML report from export data"""
    skill_name = data["skill_name"]
    scan = data["scan"]
    standards = data["detection_standards"]

    findings_html = ""
    for i, f in enumerate(scan.get("findings", []), 1):
        severity_badge = f.get("adjusted_severity", f.get("severity", "unknown"))
        context_badge = "code" if f.get("in_code_block") else "prose"
        context_class = "code-context" if f.get("in_code_block") else "prose-context"

        severity_change = ""
        if f.get("severity_changed"):
            severity_change = f"""
            <span class="severity-change">
                (was {f.get("original_severity", "N/A")})
            </span>
            """

        standard_link = ""
        if f.get("standard_url"):
            standard_link = f"""
            <a href="{f["standard_url"]}" target="_blank" class="standard-link">
                {f.get("detection_standard", "Reference")}
            </a>
            """

        findings_html += f"""
        <div class="finding">
            <div class="finding-header">
                <span class="finding-number">#{i}</span>
                <span class="rule-id">{f.get("rule_id", "N/A")}</span>
                <span class="rule-name">{f.get("rule_name", "Unknown")}</span>
                <span class="severity severity-{severity_badge}">{severity_badge}</span>
                {severity_change}
                <span class="context {context_class}">{context_badge}</span>
            </div>
            <div class="finding-location">
                Line {f.get("line_number", 0)}: <code>{f.get("line_content", "")[:80]}...</code>
            </div>
            <div class="finding-reason">
                {f.get("adjustment_reason", "")}
            </div>
            <div class="finding-standard">
                {standard_link}
            </div>
        </div>
        """

    standards_html = ""
    for s in standards:
        standards_html += f"""
        <div class="standard">
            <a href="{s["url"]}" target="_blank">{s["name"]}</a>
            <p>{s["description"]}</p>
        </div>
        """

    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>Security Scan Report: {skill_name}</title>
    <style>
        body {{ font-family: system-ui, -apple-system, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #1a1a2e; }}
        .summary {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; }}
        .summary-item {{ text-align: center; }}
        .summary-value {{ font-size: 2em; font-weight: bold; }}
        .summary-label {{ color: #666; }}
        .risk-safe {{ color: #22c55e; }}
        .risk-low {{ color: #84cc16; }}
        .risk-medium {{ color: #eab308; }}
        .risk-high {{ color: #f97316; }}
        .risk-critical {{ color: #ef4444; }}
        .finding {{ border: 1px solid #e5e7eb; border-radius: 8px; padding: 15px; margin-bottom: 15px; }}
        .finding-header {{ display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }}
        .finding-number {{ font-weight: bold; color: #666; }}
        .rule-id {{ background: #e5e7eb; padding: 2px 8px; border-radius: 4px; font-family: monospace; }}
        .severity {{ padding: 2px 8px; border-radius: 4px; color: white; font-size: 0.85em; }}
        .severity-info {{ background: #3b82f6; }}
        .severity-low {{ background: #22c55e; }}
        .severity-medium {{ background: #eab308; }}
        .severity-high {{ background: #f97316; }}
        .severity-critical {{ background: #ef4444; }}
        .severity-change {{ color: #666; font-style: italic; }}
        .context {{ padding: 2px 8px; border-radius: 4px; font-size: 0.85em; }}
        .code-context {{ background: #dbeafe; color: #1e40af; }}
        .prose-context {{ background: #fef3c7; color: #92400e; }}
        .finding-location {{ margin-top: 10px; }}
        .finding-location code {{ background: #f3f4f6; padding: 2px 6px; border-radius: 4px; }}
        .finding-reason {{ margin-top: 10px; color: #666; font-size: 0.9em; }}
        .finding-standard {{ margin-top: 10px; }}
        .standard-link {{ color: #3b82f6; text-decoration: none; font-size: 0.85em; }}
        .standard-link:hover {{ text-decoration: underline; }}
        .standards-section {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; }}
        .standard {{ margin-bottom: 15px; }}
        .standard a {{ color: #3b82f6; font-weight: 500; }}
        .standard p {{ margin: 5px 0 0 0; color: #666; font-size: 0.9em; }}
        .export-footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; color: #666; font-size: 0.85em; }}
    </style>
</head>
<body>
    <h1>Security Scan Report</h1>
    <h2>{skill_name}</h2>
    
    <div class="summary">
        <div class="summary-grid">
            <div class="summary-item">
                <div class="summary-value risk-{scan.get("risk_level", "unknown")}">{scan.get("risk_level", "N/A").upper()}</div>
                <div class="summary-label">Risk Level</div>
            </div>
            <div class="summary-item">
                <div class="summary-value">{scan.get("risk_score", 0)}</div>
                <div class="summary-label">Risk Score</div>
            </div>
            <div class="summary-item">
                <div class="summary-value">{scan.get("findings_count", 0)}</div>
                <div class="summary-label">Total Findings</div>
            </div>
            <div class="summary-item">
                <div class="summary-value">{scan.get("findings_in_code_blocks", 0)}</div>
                <div class="summary-label">In Code Blocks</div>
            </div>
            <div class="summary-item">
                <div class="summary-value">{scan.get("severity_adjustments", 0)}</div>
                <div class="summary-label">Adjusted</div>
            </div>
        </div>
    </div>
    
    <h3>Findings</h3>
    {findings_html if findings_html else "<p>No security findings.</p>"}
    
    <div class="standards-section">
        <h3>Detection Standards</h3>
        {standards_html}
    </div>
    
    <div class="export-footer">
        <p>Exported: {data["export_date"]}</p>
        <p>Scanner: Advanced Skill Analyzer v{scan.get("scanner_version", "2.1.0")}</p>
    </div>
</body>
</html>
    """
<<<<<<< Updated upstream
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
