param(
    [string]$ProjectName = "skill0-rehearsal",
    [int]$ApiPort = 18080,
    [int]$WebPort = 13080,
    [switch]$KeepRunning
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $env:TEMP "$ProjectName.env"

function Invoke-Compose {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
    docker compose --env-file $envFile -f (Join-Path $repoRoot "docker-compose.prod.yml") -p $ProjectName @Args
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
SKILL0_RUNTIME_ALLOW_INITIALIZE=true
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

try {
    Write-Host "[STEP] Compose config"
    Invoke-Compose config | Out-Null

    Write-Host "[STEP] Build production compose images"
    Invoke-Compose build

    Write-Host "[STEP] Initialize disposable governance volume"
    Invoke-Compose run --rm --no-deps dashboard python -c 'from tools.governance_db import GovernanceDB; GovernanceDB("/app/governance/db/governance.db")'

    Write-Host "[STEP] Start production compose stack"
    Invoke-Compose up -d

    Write-Host "[STEP] Service status"
    Invoke-Compose ps

    Write-Host "[STEP] API health"
    Wait-Http -Uri "http://127.0.0.1:$ApiPort/health"

    Write-Host "[STEP] Web health"
    Wait-Http -Uri "http://127.0.0.1:$WebPort/"

    Write-Host "[STEP] Runtime production doctor"
    Invoke-Compose exec -T api python /app/scripts/runtime_doctor.py --production --json

    Write-Host "[STEP] Create Runtime persistence sentinel"
    $sentinelCreate = 'from api.routers.runs_v4 import get_runtime_db_path,get_runtime_hitl_ttl_seconds,get_runtime_journal_mode; from runtime.ledger import RuntimeLedger; ledger=RuntimeLedger(get_runtime_db_path(),journal_mode=get_runtime_journal_mode(),hitl_ttl_seconds=get_runtime_hitl_ttl_seconds()); run_id=ledger.create_run(skill_name="runtime-rehearsal-sentinel",skill_version="1"); ledger.close(); print(run_id)'
    $sentinelRunId = ((Invoke-Compose exec -T api python -c $sentinelCreate | Select-Object -Last 1) -as [string]).Trim()
    if (-not $sentinelRunId) { throw "Runtime persistence sentinel was not created" }

    Write-Host "[STEP] Named-volume DB presence"
    $volumeCheck = 'from pathlib import Path; paths=[Path("/skills/skills.db"), Path("/governance/governance.db"), Path("/runtime/runtime.db")]; [print(f"{p}: exists={p.exists()} size={p.stat().st_size if p.exists() else 0}") for p in paths]; raise SystemExit(0 if all(p.exists() and p.stat().st_size > 0 for p in paths) else 1)'
    docker run --rm -v "${ProjectName}_skill0-skills-db:/skills:ro" -v "${ProjectName}_skill0-governance-db:/governance:ro" -v "${ProjectName}_skill0-runtime-db:/runtime:ro" python:3.12-slim python -c $volumeCheck

    Write-Host "[STEP] Three-store online backup and restore verification"
    $storageCheck = 'import sqlite3,sys,tempfile; from pathlib import Path; sentinel=sys.argv[1]; sources={"skills":Path("/skills/skills.db"),"governance":Path("/governance/governance.db"),"runtime":Path("/runtime/runtime.db")}; root=Path(tempfile.mkdtemp()); [(sqlite3.connect(str(src)).backup(sqlite3.connect(str(root/f"{name}.backup.db")))) for name,src in sources.items()]; [(sqlite3.connect(str(root/f"{name}.backup.db")).backup(sqlite3.connect(str(root/f"{name}.restored.db")))) for name in sources]; checks={name:sqlite3.connect(str(root/f"{name}.restored.db")).execute("PRAGMA quick_check").fetchone()[0] for name in sources}; restored=sqlite3.connect(str(root/"runtime.restored.db")); sentinel_ok=restored.execute("SELECT COUNT(*) FROM runtime_runs WHERE run_id=? AND skill_name=?",(sentinel,"runtime-rehearsal-sentinel")).fetchone()[0]==1; restored.close(); print({"quick_check":checks,"sentinel_ok":sentinel_ok}); raise SystemExit(0 if all(value=="ok" for value in checks.values()) and sentinel_ok else 1)'
    docker run --rm -v "${ProjectName}_skill0-skills-db:/skills:ro" -v "${ProjectName}_skill0-governance-db:/governance:ro" -v "${ProjectName}_skill0-runtime-db:/runtime:ro" python:3.12-slim python -c $storageCheck $sentinelRunId

    Write-Host "[STEP] API restart persistence"
    Invoke-Compose restart api
    Wait-Http -Uri "http://127.0.0.1:$ApiPort/health"
    Invoke-Compose exec -T api python /app/scripts/runtime_doctor.py --production --json
    $sentinelCheck = 'import sqlite3,sys; run_id=sys.argv[1]; connection=sqlite3.connect("/app/runtime-data/runtime.db"); found=connection.execute("SELECT COUNT(*) FROM runtime_runs WHERE run_id=? AND skill_name=?",(run_id,"runtime-rehearsal-sentinel")).fetchone()[0]; connection.close(); print(f"runtime_sentinel_after_restart={found}"); raise SystemExit(0 if found==1 else 1)'
    Invoke-Compose exec -T api python -c $sentinelCheck $sentinelRunId

    Write-Host "[OK] Production compose rehearsal passed."
}
finally {
    if (-not $KeepRunning) {
        Write-Host "[STEP] Cleanup compose stack and volumes"
        try {
            Invoke-Compose down --volumes --remove-orphans
        }
        catch {
            Write-Warning "Cleanup failed: $_"
        }
    }
    Remove-Item -LiteralPath $envFile -Force -ErrorAction SilentlyContinue
}
