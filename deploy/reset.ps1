# The reset half of reset and rederive, from a Windows machine: delete the checks the demo
# recording, the persistence check, the verification and the load test made in the live log, by
# their stated notes, with their scores, and leave the demo queue and the audit log alone.
#
# Uses Neon's HTTP SQL endpoint (https://<host>/sql with the connection string in the
# Neon-Connection-String header), because this machine has no psql. Reads the connection string from
# the .env beside the repository, the same file deploy.ps1 reads, and uses the `turnaround` schema
# when the string is the shared DATABASE_URL. Writes what it removed to deploy\reset-result.json.
#
#   powershell -ExecutionPolicy Bypass -File "C:\Project FullTime\turnaround\deploy\reset.ps1"

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
. (Join-Path $repo "deploy\_env.ps1")
Read-DotEnv (Join-Path (Split-Path -Parent $repo) ".env")
Read-DotEnv (Join-Path $repo ".env")

if ($env:TURNAROUND_DATABASE_URL) { $connection = $env:TURNAROUND_DATABASE_URL; $prefix = "" }
elseif ($env:DATABASE_URL) { $connection = $env:DATABASE_URL; $prefix = "turnaround." }
else { throw "neither TURNAROUND_DATABASE_URL nor DATABASE_URL is set" }
$connection = $connection -replace '^postgresql\+psycopg://', 'postgresql://'
$hostName = ([Uri]$connection).Host
$endpoint = "https://$hostName/sql"
$headers = @{ "Neon-Connection-String" = $connection; "Neon-Raw-Text-Output" = "true"; "Neon-Array-Mode" = "false" }

function Invoke-Sql($query) {
    $body = @{ query = $query; params = @() } | ConvertTo-Json -Depth 5
    return Invoke-RestMethod -Method Post -Uri $endpoint -Headers $headers -ContentType "application/json" -TimeoutSec 90 -Body $body
}

$notes = @("demo recording", "recorded session", "persistence check", "verification from a separate client", "load test")
$list = "'" + ($notes -join "','") + "'"
$before = Invoke-Sql "select count(*)::int as n from ${prefix}checks where note in ($list)"
$scores = Invoke-Sql "delete from ${prefix}check_scores where check_id in (select check_id from ${prefix}checks where note in ($list))"
$checks = Invoke-Sql "delete from ${prefix}checks where note in ($list)"
$audit = Invoke-Sql "insert into ${prefix}audit_log (at, actor, action, resource, resource_id, detail) values (now(), 'operator', 'reset', 'check', '', '{""notes"": ""recording and checks""}'::json)"
$after = Invoke-Sql "select count(*)::int as n from ${prefix}checks"
$result = [ordered]@{
    reset_at = (Get-Date).ToUniversalTime().ToString("o")
    matched = $before.rows[0].n
    deleted = @{ scores = $scores.rowCount; checks = $checks.rowCount }
    remaining_checks = $after.rows[0].n
    audit_log = "left alone, with a reset row added"
}
$result | ConvertTo-Json -Depth 5 | Set-Content -Path (Join-Path $repo "deploy\reset-result.json")
$result | ConvertTo-Json -Depth 5
Write-Host "reset: removed the checks the recording and the checks made; the demo queue and the audit log stay"
