# skill-0 Docker Compose startup script
# Used by Windows Task Scheduler on system boot

$ProjectRoot = "C:\Dev\Projects\skill-0"
$LogFile = "$ProjectRoot\scripts\startup.log"

function Write-Log($msg) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp $msg" | Out-File -Append -FilePath $LogFile -Encoding utf8
}

Write-Log "=== skill-0 startup ==="

# Wait for Docker Desktop to be ready
$maxWait = 120
$waited = 0
while ($waited -lt $maxWait) {
    try {
        docker info 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) { break }
    } catch {}
    Write-Log "Waiting for Docker... ($waited s)"
    Start-Sleep -Seconds 5
    $waited += 5
}

if ($waited -ge $maxWait) {
    Write-Log "ERROR: Docker not ready after ${maxWait}s, aborting"
    exit 1
}

Write-Log "Docker ready"

Set-Location $ProjectRoot
docker compose up -d 2>&1 | ForEach-Object { Write-Log $_ }

if ($LASTEXITCODE -eq 0) {
    Write-Log "skill-0 started successfully"
} else {
    Write-Log "ERROR: docker compose up failed (exit $LASTEXITCODE)"
    exit 1
}
