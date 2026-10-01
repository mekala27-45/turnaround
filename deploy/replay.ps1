# Fill the demo queue from a separate client: one check at every hub the server covers, for the
# outcome month it holds (its busiest listed inbound and outbound routes, a 13:00 departure after a
# 12:00 arrival, a 60 minute buffer), then score the log, so the check log is never empty. Writes
# what the server answered to results\deploy\replay.json.
#
#   powershell -ExecutionPolicy Bypass -File "C:\Project FullTime\turnaround\deploy\replay.ps1"

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$base = (Get-Content (Join-Path $repo "deploy\live-url.txt") -Raw).Trim()
$token = (Get-Content (Join-Path $repo "deploy\write-token.txt") -Raw).Trim()
$headers = @{ Authorization = "Bearer $token" }
$health = Invoke-RestMethod -Uri "$base/v1/health" -TimeoutSec 120
$hubs = (Invoke-RestMethod -Uri "$base/v1/hubs" -TimeoutSec 90).hubs
$made = @()
foreach ($h in $hubs) {
    $body = @{
        origin = $h.origins[0]; connection = $h.hub; destination = $h.destinations[0]
        travel_month = $health.outcome_month; inbound_hour = 12; outbound_hour = 13; buffer_minutes = 60; note = "demo queue"
    }
    try {
        $r = Invoke-RestMethod -Method Post -Uri "$base/v1/checks" -Headers $headers -ContentType "application/json" -TimeoutSec 120 -Body ($body | ConvertTo-Json)
        $made += [ordered]@{ hub = $h.hub; check_id = $r.check_id; probability = $r.probability; flights = $r.flights }
        Write-Host "check at $($h.hub): $($r.check_id) probability $($r.probability)"
    } catch {
        Write-Host "no check at $($h.hub): $($_.Exception.Message)"
    }
}
$scored = Invoke-RestMethod -Method Post -Uri "$base/v1/score" -Headers $headers -ContentType "application/json" -TimeoutSec 180 -Body (@{ note = "demo queue" } | ConvertTo-Json)
$card = Invoke-RestMethod -Uri "$base/v1/scorecard" -TimeoutSec 90
$result = [ordered]@{
    base_url = $base
    replayed_at = (Get-Date).ToUniversalTime().ToString("o")
    outcome_month = $health.outcome_month
    checks_made = $made.Count
    hubs = $hubs.Count
    scored = $scored.scored
    unscored_share = $scored.unscored_share
    scorecard = @{ checks = $card.checks; scored = $card.scored; mean_absolute_error = $card.mean_absolute_error; interval_coverage = $card.interval_coverage }
}
New-Item -ItemType Directory -Force -Path (Join-Path $repo "results\deploy") | Out-Null
$result | ConvertTo-Json -Depth 5 | Set-Content -Path (Join-Path $repo "results\deploy\replay.json")
$result | ConvertTo-Json -Depth 5
Write-Host "replayed: $($made.Count) demo checks made and scored on the live log"
