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

@"
SKILL0_ENV_FILE=$($envFile -replace '\\', '/')
SKILL0_DB_PATH=/app/data/skills.db
SKILL0_PARSED_DIR=/app/parsed
SKILL0_ENV=production
SKILL0_ENABLE_DOCS=false
SKILL0_GOVERNANCE_DB_PATH=/app/governance/db/governance.db
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

    Write-Host "[STEP] Build and start production compose stack"
    Invoke-Compose up -d --build

    Write-Host "[STEP] Service status"
    Invoke-Compose ps

    Write-Host "[STEP] API health"
    Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$ApiPort/health" | Out-Null

    Write-Host "[STEP] Web health"
    Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$WebPort/" | Out-Null

    Write-Host "[STEP] Named-volume DB presence"
    $volumeCheck = 'from pathlib import Path; paths=[Path("/skills/skills.db"), Path("/governance/governance.db")]; [print(f"{p}: exists={p.exists()} size={p.stat().st_size if p.exists() else 0}") for p in paths]; raise SystemExit(0 if all(p.exists() for p in paths) else 1)'
    docker run --rm -v "${ProjectName}_skill0-skills-db:/skills" -v "${ProjectName}_skill0-governance-db:/governance" python:3.12-slim python -c $volumeCheck

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
