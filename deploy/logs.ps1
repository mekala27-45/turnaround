# Read the live API's recent logs from Fly on a Windows machine, so a failing health check can be
# explained without opening a dashboard. Redacts anything that looks like a connection string or a
# bearer token, and writes the result to deploy\fly-logs.txt.
#
#   powershell -ExecutionPolicy Bypass -File "C:\Project FullTime\turnaround\deploy\logs.ps1"

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
. (Join-Path $repo "deploy\_env.ps1")
Read-DotEnv (Join-Path (Split-Path -Parent $repo) ".env")
Read-DotEnv (Join-Path $repo ".env")
Use-Flyctl
$base = (Get-Content (Join-Path $repo "deploy\live-url.txt") -Raw).Trim()
$app = ([Uri]$base).Host.Split(".")[0]
$lines = flyctl logs --app $app --no-tail 2>&1 | ForEach-Object { "$_" }
$redacted = $lines | ForEach-Object {
    $_ -replace 'postgres(ql)?(\+[a-z]+)?://[^\s"]+', 'postgresql://REDACTED' `
       -replace '(?i)bearer\s+[A-Za-z0-9._-]+', 'Bearer REDACTED' `
       -replace '(?i)(token[=:]\s*)[A-Za-z0-9._-]+', '$1REDACTED'
}
$redacted | Set-Content -Path (Join-Path $repo "deploy\fly-logs.txt")
Write-Host "wrote $($redacted.Count) lines to deploy\fly-logs.txt"
$redacted | Select-Object -Last 40
