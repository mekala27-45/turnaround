# The load test against the live API from a separate client (a Windows machine): one warming request,
# then N sequential POST /v1/checks and GET /v1/checks/{id}, then a burst of concurrent checks, timed
# with a stopwatch. Writes results\latency\live.json in the same shape as scripts/load_test.py, which
# the documents read.
#
#   powershell -ExecutionPolicy Bypass -File "C:\Project FullTime\turnaround\deploy\load-test.ps1"

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$base = (Get-Content (Join-Path $repo "deploy\live-url.txt") -Raw).Trim()
$token = (Get-Content (Join-Path $repo "deploy\write-token.txt") -Raw).Trim()
$headers = @{ Authorization = "Bearer $token" }
$requests = 40
$concurrency = 6

function Summary($samples) {
    $sorted = $samples | Sort-Object
    $n = $sorted.Count
    $p99Index = [Math]::Min($n - 1, [Math]::Max(0, [int][Math]::Round(0.99 * ($n - 1))))
    $p50 = if ($n % 2 -eq 1) { $sorted[[int](($n - 1) / 2)] } else { ($sorted[[int]($n / 2) - 1] + $sorted[[int]($n / 2)]) / 2 }
    return [ordered]@{ p50_ms = [Math]::Round($p50, 1); p99_ms = [Math]::Round($sorted[$p99Index], 1); max_ms = [Math]::Round($sorted[$n - 1], 1); mean_ms = [Math]::Round(($sorted | Measure-Object -Average).Average, 1) }
}

$health = Invoke-RestMethod -Uri "$base/v1/health" -TimeoutSec 120
$hubs = (Invoke-RestMethod -Uri "$base/v1/hubs" -TimeoutSec 120).hubs
$bodies = @()
for ($i = 0; $i -lt $hubs.Count; $i++) {
    $h = $hubs[$i]
    $bodies += (@{ origin = $h.busiest_origin; connection = $h.hub; destination = $h.busiest_destination; travel_month = $health.outcome_month; inbound_hour = 12; outbound_hour = 13; buffer_minutes = 45 + 15 * ($i % 4); note = "load test" } | ConvertTo-Json)
}
$sw = [Diagnostics.Stopwatch]::StartNew()
$null = Invoke-RestMethod -Method Post -Uri "$base/v1/checks" -Headers $headers -ContentType "application/json" -TimeoutSec 120 -Body $bodies[0]
$wake = $sw.Elapsed.TotalMilliseconds
$made = @(); $ids = @()
for ($i = 0; $i -lt $requests; $i++) {
    $sw.Restart()
    $r = Invoke-RestMethod -Method Post -Uri "$base/v1/checks" -Headers $headers -ContentType "application/json" -TimeoutSec 120 -Body $bodies[$i % $bodies.Count]
    $made += $sw.Elapsed.TotalMilliseconds
    $ids += $r.check_id
}
$reads = @()
foreach ($id in $ids) {
    $sw.Restart()
    $null = Invoke-RestMethod -Uri "$base/v1/checks/$id" -TimeoutSec 60
    $reads += $sw.Elapsed.TotalMilliseconds
}
$jobs = @()
for ($i = 0; $i -lt $concurrency; $i++) {
    $jobs += Start-Job -ScriptBlock {
        param($base, $token, $body)
        $sw = [Diagnostics.Stopwatch]::StartNew()
        $null = Invoke-RestMethod -Method Post -Uri "$base/v1/checks" -Headers @{ Authorization = "Bearer $token" } -ContentType "application/json" -TimeoutSec 120 -Body $body
        return $sw.Elapsed.TotalMilliseconds
    } -ArgumentList $base, $token, $bodies[$i % $bodies.Count]
}
$burst = $jobs | Wait-Job | Receive-Job
$jobs | Remove-Job
$result = [ordered]@{
    base_url = $base
    measured_at = (Get-Date).ToUniversalTime().ToString("o")
    requests = $requests
    concurrency = $concurrency
    hubs = $hubs.Count
    first_request_ms = [Math]::Round($wake, 1)
    check = Summary $made
    read = Summary $reads
    burst_check_max_ms = [Math]::Round(($burst | Measure-Object -Maximum).Maximum, 1)
    errors = 0
    note = "sequential requests after one warming request from a Windows client; the burst is concurrent checks"
}
New-Item -ItemType Directory -Force -Path (Join-Path $repo "results\latency") | Out-Null
$result | ConvertTo-Json -Depth 5 | Set-Content -Path (Join-Path $repo "results\latency\live.json")
$result | ConvertTo-Json -Depth 5
Write-Host "load test: $requests checks and reads against $base"
