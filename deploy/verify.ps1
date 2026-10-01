# Verify the live API from a separate client (a Windows machine, not the server, not the build
# sandbox): make a check at the first hub for the outcome month the server holds, score the log,
# read the check back with its score, read the audit log, and confirm the audit row was written
# before the check's response was served. Writes the transcript to deploy\verify-log.txt and the
# observation, with no secrets in it, to results\deploy\verification.json so the build can quote it.
#
#   powershell -ExecutionPolicy Bypass -File "C:\Project FullTime\turnaround\deploy\verify.ps1"

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Start-Transcript -Path (Join-Path $repo "deploy\verify-log.txt") -Force | Out-Null
$base = (Get-Content (Join-Path $repo "deploy\live-url.txt") -Raw).Trim()
$token = (Get-Content (Join-Path $repo "deploy\write-token.txt") -Raw).Trim()
$headers = @{ Authorization = "Bearer $token" }

Write-Host "client: $env:COMPUTERNAME ($([Environment]::OSVersion.VersionString)), PowerShell $($PSVersionTable.PSVersion)"
Write-Host "server: $base"
$health = Invoke-RestMethod -Uri "$base/v1/health" -TimeoutSec 90
Write-Host "health: status=$($health.status) database=$($health.database) model=$($health.model_version) hubs=$($health.hubs) outcome=$($health.outcome_month)"

$hub = (Invoke-RestMethod -Uri "$base/v1/hubs" -TimeoutSec 90).hubs[0]
$body = @{
    origin = $hub.origins[0]; connection = $hub.hub; destination = $hub.destinations[0]
    travel_month = $health.outcome_month; inbound_hour = 12; outbound_hour = 13; buffer_minutes = 60
    note = "verification from a separate client"
}
$check = Invoke-RestMethod -Method Post -Uri "$base/v1/checks" -Headers $headers -ContentType "application/json" -TimeoutSec 120 -Body ($body | ConvertTo-Json)
$servedAt = [DateTime]::Parse($check.served_at).ToUniversalTime()
Write-Host "check $($check.check_id): $($body.origin) $($body.connection) $($body.destination), buffer 60, probability $($check.probability) ($($check.low) to $($check.high)), $($check.flights) flights"

$scored = Invoke-RestMethod -Method Post -Uri "$base/v1/score" -Headers $headers -ContentType "application/json" -TimeoutSec 120 -Body (@{ note = "verification from a separate client" } | ConvertTo-Json)
Write-Host "scored $($scored.scored) of $($scored.checks) checks against $($scored.outcome_month), unscored share $($scored.unscored_share)"

$read = Invoke-RestMethod -Uri "$base/v1/checks/$($check.check_id)" -TimeoutSec 90
$audit = Invoke-RestMethod -Uri "$base/v1/audit?limit=50" -TimeoutSec 90
$created = $audit.entries | Where-Object { $_.action -eq "create" -and $_.resource_id -eq $check.check_id } | Select-Object -First 1
$auditBefore = ([DateTime]::Parse($created.at).ToUniversalTime()) -le $servedAt
$ok = ($read.check_id -eq $check.check_id) -and ([Math]::Abs($read.probability - $check.probability) -lt 1e-12) -and ($null -ne $read.score) -and $auditBefore -and ($read.statement.Length -gt 100)
$result = [ordered]@{
    base_url = $base
    client = "$env:COMPUTERNAME, Windows, PowerShell $($PSVersionTable.PSVersion)"
    checked_at = (Get-Date).ToUniversalTime().ToString("o")
    health = @{ status = $health.status; database = $health.database; model_version = $health.model_version; hubs = $health.hubs; outcome_month = $health.outcome_month }
    connection = "$($body.origin) $($body.connection) $($body.destination)"
    travel_month = $health.outcome_month
    buffer_minutes = 60
    check_id = $check.check_id
    probability = $check.probability
    low = $check.low
    high = $check.high
    flights = $check.flights
    read_back_probability = $read.probability
    score = $read.score
    unscored_share = $scored.unscored_share
    audit_entries = $audit.entries.Count
    audit_before_response = $auditBefore
    statement_present = ($read.statement.Length -gt 100)
    passed = $ok
}
New-Item -ItemType Directory -Force -Path (Join-Path $repo "results\deploy") | Out-Null
$result | ConvertTo-Json -Depth 5 | Set-Content -Path (Join-Path $repo "results\deploy\verification.json")
$result | ConvertTo-Json -Depth 5
if (-not $ok) { throw "verification failed" }
Write-Host "verified: the check, its score and its audit row were read back from a separate client"
Stop-Transcript | Out-Null
