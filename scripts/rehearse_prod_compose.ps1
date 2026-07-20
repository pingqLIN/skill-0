param(
    [string]$ProjectName = "skill0-rehearsal",
    [int]$ApiPort = 18080,
    [int]$WebPort = 13080,
    [string]$BuildCaFile = "",
    [switch]$KeepRunning
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $env:TEMP "$ProjectName-$PID.env"
$buildOverrideFile = Join-Path $env:TEMP "$ProjectName-$PID.build-ca.yml"
$composeFiles = @("-f", (Join-Path $repoRoot "docker-compose.prod.yml"))

function Assert-LocalPortAvailable {
    param([Parameter(Mandatory = $true)][int]$Port)

    $listener = [System.Net.Sockets.TcpListener]::new(
        [System.Net.IPAddress]::Loopback,
        $Port
    )
    try {
        $listener.Start()
    }
    catch {
        throw "Local port $Port is already in use; choose another -ApiPort or -WebPort value"
    }
    finally {
        $listener.Stop()
    }
}

Assert-LocalPortAvailable -Port $ApiPort
Assert-LocalPortAvailable -Port $WebPort

if ($BuildCaFile) {
    $resolvedCaFile = (Resolve-Path -LiteralPath $BuildCaFile).Path
    $composeCaPath = $resolvedCaFile -replace '\\', '/'
    @"
services:
  api:
    build:
      secrets:
        - build_ca
secrets:
  build_ca:
    file: "$composeCaPath"
"@ | Set-Content -LiteralPath $buildOverrideFile -NoNewline -Encoding utf8
    $composeFiles += @("-f", $buildOverrideFile)
}

function Invoke-Compose {
    param([Parameter(Mandatory = $true)][string[]]$ComposeArgs)
    & docker compose --env-file $envFile @composeFiles -p $ProjectName @ComposeArgs
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose $($ComposeArgs -join ' ') failed with exit code $LASTEXITCODE"
    }
}

function Wait-Http {
    param([string]$Uri, [int]$Attempts = 30)
    for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
        try {
            Invoke-WebRequest -UseBasicParsing -Uri $Uri | Out-Null
            return
        }
        catch {
            if ($attempt -eq $Attempts) { throw }
            Start-Sleep -Seconds 2
        }
    }
}

@"
SKILL0_ENV_FILE=$($envFile -replace '\\', '/')
SKILL0_DB_PATH=/app/data/skills.db
SKILL0_PARSED_DIR=/app/parsed
SKILL0_ENV=production
SKILL0_ENABLE_DOCS=false
SKILL0_GOVERNANCE_DB_PATH=/app/governance/db/governance.db
SKILL0_RUNTIME_DB_PATH=/app/runtime-data/runtime.db
SKILL0_RUNTIME_BINDING_KEY=rehearsal-runtime-binding-key-0123456789
SKILL0_RUNTIME_DECISION_ACTORS=rehearsal-admin
SKILL0_RUNTIME_HITL_TTL_SECONDS=86400
SKILL0_RUNTIME_JOURNAL_MODE=WAL
SKILL0_RUNTIME_ALLOW_INITIALIZE=false
SKILL0_TOOLS_PATH=/app/tools
SKILL0_DEVICE=cpu
CORS_ORIGINS=https://rehearsal.example.invalid
JWT_SECRET_KEY=rehearsal-secret-key-change-me-0123456789
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=15
API_USERNAME=rehearsal-admin
API_PASSWORD=rehearsal-password-0123456789
API_PORT=$ApiPort
WEB_PORT=$WebPort
API_RATE_LIMIT=60/minute
AUTH_RATE_LIMIT=5/minute
SKILL0_LOG_LEVEL=WARNING
SKILL0_LOG_FORMAT=json
"@ | Set-Content -LiteralPath $envFile -NoNewline -Encoding utf8

$rehearsalPassed = $false

try {
    Write-Host "[STEP] Compose config"
    Invoke-Compose -ComposeArgs @("config") | Out-Null

    Write-Host "[STEP] Build production compose images"
    Invoke-Compose -ComposeArgs @("build")

    Write-Host "[STEP] Initialize disposable governance volume"
    Invoke-Compose -ComposeArgs @("run", "--rm", "--no-deps", "dashboard", "python", "-c", 'from tools.governance_db import GovernanceDB; GovernanceDB("/app/governance/db/governance.db")')

    Write-Host "[STEP] Initialize disposable Runtime ledger before production startup"
    $runtimeInitialize = 'from runtime.ledger import RuntimeLedger; RuntimeLedger("/app/runtime-data/runtime.db", journal_mode="WAL", hitl_ttl_seconds=86400).close()'
    Invoke-Compose -ComposeArgs @("run", "--rm", "--no-deps", "--entrypoint", "python", "api", "-c", $runtimeInitialize)

    Write-Host "[STEP] Start production compose stack"
    Invoke-Compose -ComposeArgs @("up", "--detach")

    Write-Host "[STEP] Service status"
    Invoke-Compose -ComposeArgs @("ps")

    Write-Host "[STEP] API health"
    Wait-Http -Uri "http://127.0.0.1:$ApiPort/health"

    Write-Host "[STEP] Web health"
    Wait-Http -Uri "http://127.0.0.1:$WebPort/"

    Write-Host "[STEP] Runtime production doctor"
    Invoke-Compose -ComposeArgs @("exec", "-T", "api", "python", "/app/scripts/runtime_doctor.py", "--production", "--json")

    Write-Host "[STEP] Governed Runtime dry-run and deterministic Evidence"
    $governanceSeed = 'import json; from pathlib import Path; from runtime.digest import canonical_digest; from tools.governance_db import GovernanceDB; document=json.loads(Path("/app/parsed/a11y-skill.json").read_text(encoding="utf-8")); database=GovernanceDB("/app/governance/db/governance.db"); skill_id=database.create_skill(name=document["meta"]["name"],source_type="local",source_path="parsed/a11y-skill.json",version="2.4.0"); database.bind_runtime_artifact(skill_id,canonical_skill_id=document["meta"]["skill_id"],artifact_digest=canonical_digest(document),bound_by="rehearsal-binder"); approved=database.approve_skill(skill_id,approved_by="rehearsal-reviewer",reason="closeout rehearsal"); print(f"governance_runtime_approval={int(approved)}"); raise SystemExit(0 if approved else 1)'
    Invoke-Compose -ComposeArgs @("exec", "-T", "dashboard", "python", "-c", $governanceSeed)

    $authBody = @{
        username = "rehearsal-admin"
        password = "rehearsal-password-0123456789"
    } | ConvertTo-Json -Compress
    $tokenResponse = Invoke-RestMethod `
        -Method Post `
        -Uri "http://127.0.0.1:$ApiPort/api/auth/token" `
        -ContentType "application/json" `
        -Body $authBody
    $authHeaders = @{ Authorization = "Bearer $($tokenResponse.access_token)" }

    $contract = Get-Content -Raw -LiteralPath (Join-Path $repoRoot "examples/runtime-contract.read-only.json") | ConvertFrom-Json
    $contract.skill_ref.name = "a11y"
    $contract.skill_ref.version = "2.4.0"
    $contract.action_bindings[0].validation.precondition_rule_ids = @()
    $runBody = @{
        skill_id = "claude__skill__a_y"
        runtime_contract = $contract
        parameters = @{}
        dry_run = $true
    } | ConvertTo-Json -Depth 100 -Compress
    $runtimeRun = Invoke-RestMethod `
        -Method Post `
        -Uri "http://127.0.0.1:$ApiPort/api/runs" `
        -Headers $authHeaders `
        -ContentType "application/json" `
        -Body $runBody
    if ($runtimeRun.status -ne "succeeded") {
        throw "Governed Runtime dry-run did not succeed: $($runtimeRun.status)"
    }

    $runRead = Invoke-RestMethod `
        -Uri "http://127.0.0.1:$ApiPort/api/runs/$($runtimeRun.run_id)" `
        -Headers $authHeaders
    $eventsRead = Invoke-WebRequest -UseBasicParsing `
        -Uri "http://127.0.0.1:$ApiPort/api/runs/$($runtimeRun.run_id)/events" `
        -Headers $authHeaders
    $firstEvidence = Invoke-WebRequest -UseBasicParsing `
        -Uri "http://127.0.0.1:$ApiPort/api/runs/$($runtimeRun.run_id)/evidence" `
        -Headers $authHeaders
    $secondEvidence = Invoke-WebRequest -UseBasicParsing `
        -Uri "http://127.0.0.1:$ApiPort/api/runs/$($runtimeRun.run_id)/evidence" `
        -Headers $authHeaders
    if ($runRead.status -ne "succeeded" -or $firstEvidence.Content -cne $secondEvidence.Content) {
        throw "Runtime run read or deterministic Evidence comparison failed"
    }
    foreach ($privateValue in @(
        "rehearsal-password-0123456789",
        "rehearsal-secret-key-change-me-0123456789",
        "rehearsal-runtime-binding-key-0123456789",
        "Bearer "
    )) {
        if ($firstEvidence.Content.Contains($privateValue) -or $eventsRead.Content.Contains($privateValue)) {
            throw "Runtime public projection exposed private rehearsal material"
        }
    }
    $evidenceBytes = [System.Text.Encoding]::UTF8.GetBytes($firstEvidence.Content)
    $evidenceSha256 = [Convert]::ToHexString(
        [System.Security.Cryptography.SHA256]::HashData($evidenceBytes)
    ).ToLowerInvariant()
    Write-Host "runtime_run_id=$($runtimeRun.run_id)"
    Write-Host "runtime_run_status=$($runtimeRun.status)"
    Write-Host "runtime_evidence_sha256=$evidenceSha256"
    Write-Host "runtime_evidence_json=$($firstEvidence.Content)"

    Write-Host "[STEP] Create Runtime persistence sentinel"
    $sentinelCreate = 'from api.routers.runs_v4 import get_runtime_db_path,get_runtime_hitl_ttl_seconds,get_runtime_journal_mode; from runtime.ledger import RuntimeLedger; ledger=RuntimeLedger(get_runtime_db_path(),journal_mode=get_runtime_journal_mode(),hitl_ttl_seconds=get_runtime_hitl_ttl_seconds()); run_id=ledger.create_run(skill_name="runtime-rehearsal-sentinel",skill_version="1"); ledger.close(); print(run_id)'
    $sentinelRunId = ((Invoke-Compose -ComposeArgs @("exec", "-T", "api", "python", "-c", $sentinelCreate) | Select-Object -Last 1) -as [string]).Trim()
    if (-not $sentinelRunId) { throw "Runtime persistence sentinel was not created" }

    Write-Host "[STEP] Named-volume DB presence"
    $volumeCheck = 'from pathlib import Path; paths=[Path("/skills/skills.db"), Path("/governance/governance.db"), Path("/runtime/runtime.db")]; [print(f"{p}: exists={p.exists()} size={p.stat().st_size if p.exists() else 0}") for p in paths]; raise SystemExit(0 if all(p.exists() and p.stat().st_size > 0 for p in paths) else 1)'
    docker run --rm -v "${ProjectName}_skill0-skills-db:/skills:ro" -v "${ProjectName}_skill0-governance-db:/governance:ro" -v "${ProjectName}_skill0-runtime-db:/runtime:ro" python:3.12-slim python -c $volumeCheck
    if ($LASTEXITCODE -ne 0) { throw "Named-volume DB presence check failed" }

    Write-Host "[STEP] Three-store online backup and restore verification"
    $storageCheck = 'import sqlite3,sys,tempfile; from pathlib import Path; sentinel=sys.argv[1]; sources={"skills":Path("/skills/skills.db"),"governance":Path("/governance/governance.db"),"runtime":Path("/runtime/runtime.db")}; root=Path(tempfile.mkdtemp()); open_source=lambda src: sqlite3.connect(f"file:{src}?mode=ro",uri=True); [(open_source(src).backup(sqlite3.connect(str(root/f"{name}.backup.db")))) for name,src in sources.items()]; [(sqlite3.connect(str(root/f"{name}.backup.db")).backup(sqlite3.connect(str(root/f"{name}.restored.db")))) for name in sources]; checks={name:sqlite3.connect(str(root/f"{name}.restored.db")).execute("PRAGMA quick_check").fetchone()[0] for name in sources}; restored=sqlite3.connect(str(root/"runtime.restored.db")); sentinel_ok=restored.execute("SELECT COUNT(*) FROM runtime_runs WHERE run_id=? AND skill_name=?",(sentinel,"runtime-rehearsal-sentinel")).fetchone()[0]==1; restored.close(); print({"quick_check":checks,"sentinel_ok":sentinel_ok}); raise SystemExit(0 if all(value=="ok" for value in checks.values()) and sentinel_ok else 1)'
    docker run --rm -v "${ProjectName}_skill0-skills-db:/skills" -v "${ProjectName}_skill0-governance-db:/governance" -v "${ProjectName}_skill0-runtime-db:/runtime" python:3.12-slim python -c $storageCheck $sentinelRunId
    if ($LASTEXITCODE -ne 0) { throw "Three-store backup/restore check failed" }

    Write-Host "[STEP] API restart persistence"
    Invoke-Compose -ComposeArgs @("restart", "api")
    Wait-Http -Uri "http://127.0.0.1:$ApiPort/health"
    Invoke-Compose -ComposeArgs @("exec", "-T", "api", "python", "/app/scripts/runtime_doctor.py", "--production", "--json")
    $sentinelCheck = 'import sqlite3,sys; run_id=sys.argv[1]; connection=sqlite3.connect("/app/runtime-data/runtime.db"); found=connection.execute("SELECT COUNT(*) FROM runtime_runs WHERE run_id=? AND skill_name=?",(run_id,"runtime-rehearsal-sentinel")).fetchone()[0]; connection.close(); print(f"runtime_sentinel_after_restart={found}"); raise SystemExit(0 if found==1 else 1)'
    Invoke-Compose -ComposeArgs @("exec", "-T", "api", "python", "-c", $sentinelCheck, $sentinelRunId)

    Write-Host "[OK] Production compose rehearsal passed."
    $rehearsalPassed = $true
}
finally {
    if (-not $KeepRunning -or -not $rehearsalPassed) {
        Write-Host "[STEP] Cleanup compose stack and volumes"
        try {
            Invoke-Compose -ComposeArgs @("down", "--volumes", "--remove-orphans")
        }
        catch {
            Write-Warning "Cleanup failed: $_"
        }
    }
    Remove-Item -LiteralPath $envFile -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $buildOverrideFile -Force -ErrorAction SilentlyContinue
}
