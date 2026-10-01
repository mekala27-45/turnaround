# fetch-data.ps1: download the public data turnaround needs onto this PC.
#
# The build sandbox cannot reach transtats.bts.gov, registry.faa.gov or open-meteo.com, so this
# script runs here, on Windows, from Git GUI's Tools menu. It is safe to re-run: a finished file is
# skipped, a half written one is fetched again, and the weather pulls resume where they stopped.
# Each mode logs to fetch-log-<mode>.txt and writes fetch-status-<mode>.json, which the build reads.
#
#   powershell -ExecutionPolicy Bypass -File fetch-data.ps1 flights   (BTS months and the FAA registry)
#   powershell -ExecutionPolicy Bypass -File fetch-data.ps1 weather   (Open-Meteo, the FAA Core 30)
#   powershell -ExecutionPolicy Bypass -File fetch-data.ps1 faaref    (the registry's aircraft reference file)
#
# Sources and terms:
#   BTS, Reporting Carrier On-Time Performance (1987 to present), the monthly PREZIP files.
#     U.S. government work, public domain.
#   FAA, Releasable Aircraft Database (ReleasableAircraft.zip). U.S. government work, public domain.
#   Open-Meteo historical weather API, CC BY 4.0, "Weather data by Open-Meteo.com". No key.

param([string]$Mode = "flights")

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$btsDir = Join-Path $root "bts"
$faaDir = Join-Path $root "faa"
$weatherDir = Join-Path $root "weather"
foreach ($d in @($btsDir, $faaDir, $weatherDir)) { New-Item -ItemType Directory -Force -Path $d | Out-Null }
Start-Transcript -Path (Join-Path $root "fetch-log-$Mode.txt") -Append | Out-Null
$started = Get-Date
$now = $started.ToUniversalTime()
Write-Host "fetch $Mode started $($now.ToString('o')) on $env:COMPUTERNAME"
$agent = "turnaround-data-fetch/0.1 (portfolio analysis of public on-time data)"
$browserAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"

function Test-Zip($path) {
    if (-not (Test-Path $path)) { return $false }
    if ((Get-Item $path).Length -lt 1000000) { return $false }
    $fs = [IO.File]::OpenRead($path)
    try { $a = $fs.ReadByte(); $b = $fs.ReadByte() } finally { $fs.Close() }
    return ($a -eq 0x50 -and $b -eq 0x4B)
}

function Get-File($url, $dest, $ua) {
    # Downloads to a .part file and renames on success, so a finished name is never half written.
    $part = "$dest.part"
    if (Test-Path $part) { Remove-Item $part -Force }
    & curl.exe -L --fail --silent --show-error --retry 4 --retry-delay 20 --connect-timeout 60 --max-time 2400 -A $ua -o $part $url
    $code = $LASTEXITCODE
    if ($code -ne 0) {
        if (Test-Path $part) { Remove-Item $part -Force }
        return $code
    }
    Move-Item -Force $part $dest
    return 0
}

if ($Mode -eq "flights") {
    # 1. The FAA registry, refreshed daily by the FAA; one copy is enough for the join.
    $faaDest = Join-Path $faaDir "ReleasableAircraft.zip"
    if (-not (Test-Zip $faaDest)) {
        foreach ($ua in @($agent, $browserAgent)) {
            Write-Host "faa: ReleasableAircraft.zip"
            $code = Get-File "https://registry.faa.gov/database/ReleasableAircraft.zip" $faaDest $ua
            if ($code -eq 0 -and (Test-Zip $faaDest)) { Write-Host "  ok $((Get-Item $faaDest).Length) bytes"; break }
            Write-Host "  faa attempt failed (curl $code)"
            if (Test-Path $faaDest) { Remove-Item $faaDest -Force }
        }
    } else { Write-Host "faa: have ReleasableAircraft.zip" }

    # 2. BTS: every month from 2015_1 until the first month that is not published yet.
    $btsHosts = @("https://transtats.bts.gov/PREZIP", "https://www.transtats.bts.gov/PREZIP")
    $btsFiles = @(); $btsMissing = @(); $btsLatest = $null
    :months foreach ($year in 2015..$now.Year) {
        foreach ($month in 1..12) {
            if ($year -eq $now.Year -and $month -ge $now.Month) { break months }
            $name = "On_Time_Reporting_Carrier_On_Time_Performance_1987_present_${year}_${month}.zip"
            $dest = Join-Path $btsDir $name
            if (Test-Zip $dest) { $btsFiles += $name; $btsLatest = "${year}_${month}"; continue }
            $ok = $false
            foreach ($h in $btsHosts) {
                for ($attempt = 1; $attempt -le 3 -and -not $ok; $attempt++) {
                    Write-Host "bts: $name from $h (attempt $attempt)"
                    $code = Get-File "$h/$name" $dest $agent
                    if ($code -eq 0 -and (Test-Zip $dest)) { $ok = $true; break }
                    if (Test-Path $dest) { Remove-Item $dest -Force }
                    if ($code -eq 22) { break }
                    Start-Sleep -Seconds 30
                }
                if ($ok) { break }
            }
            if ($ok) {
                $btsFiles += $name; $btsLatest = "${year}_${month}"
                Write-Host "  ok $((Get-Item $dest).Length) bytes"
                Start-Sleep -Seconds 2
            } else {
                Write-Host "  not available: $name"
                $btsMissing += "${year}_${month}"
                if ($year -ge 2026) { break months }
            }
        }
    }
    $status = [ordered]@{
        mode = $Mode
        fetched_at = (Get-Date).ToUniversalTime().ToString("o")
        machine = $env:COMPUTERNAME
        minutes = [math]::Round(((Get-Date) - $started).TotalMinutes, 1)
        bts_latest = $btsLatest
        bts_count = $btsFiles.Count
        bts_missing = $btsMissing
        bts_files = @(Get-ChildItem $btsDir -Filter "*.zip" | Sort-Object Name | ForEach-Object { @{ name = $_.Name; bytes = $_.Length } })
        faa_files = @(Get-ChildItem $faaDir -Filter "*.zip" | ForEach-Object { @{ name = $_.Name; bytes = $_.Length; written = $_.LastWriteTimeUtc.ToString("o") } })
    }
}
elseif ($Mode -eq "weather") {
    # 3. Weather: hourly, UTC, per airport and year, at the FAA Core 30 in weather_locations.csv.
    $locations = Import-Csv (Join-Path $root "weather_locations.csv")
    $lastArchived = $now.Date.AddDays(-7)
    $vars = "temperature_2m,precipitation,snowfall,wind_speed_10m,wind_gusts_10m,cloud_cover_low,weather_code"
    $done = 0; $kept = 0; $failed = @()
    foreach ($loc in $locations) {
        foreach ($year in 2015..$now.Year) {
            $start = "$year-01-01"
            $endDate = [DateTime]::ParseExact("$year-12-31", "yyyy-MM-dd", $null)
            if ($endDate -gt $lastArchived) { $endDate = $lastArchived }
            $end = $endDate.ToString("yyyy-MM-dd")
            $dest = Join-Path $weatherDir "$($loc.airport)_$year.json"
            if (Test-Path $dest) {
                $keep = $true
                if ($year -eq $now.Year) {
                    try {
                        $existing = Get-Content $dest -Raw | ConvertFrom-Json
                        if ($existing.hourly.time[-1] -lt "$end") { $keep = $false }
                    } catch { $keep = $false }
                }
                if ($keep) { $kept += 1; continue }
            }
            $url = "https://archive-api.open-meteo.com/v1/archive?latitude=$($loc.latitude)&longitude=$($loc.longitude)&start_date=$start&end_date=$end&hourly=$vars&timezone=UTC"
            $ok = $false
            for ($attempt = 1; $attempt -le 6 -and -not $ok; $attempt++) {
                try {
                    $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 180 -UserAgent $agent
                    $payload = $response.Content | ConvertFrom-Json
                    if (-not $payload.hourly.time) { throw "no hourly block in the response" }
                    [IO.File]::WriteAllText($dest, $response.Content)
                    $ok = $true; $done += 1
                    Write-Host "weather: $($loc.airport) $year ($($payload.hourly.time.Count) hours)"
                    Start-Sleep -Seconds 3
                } catch {
                    $message = "$_"
                    Write-Host "  weather: $($loc.airport) $year attempt $attempt failed: $message"
                    if ($message -match "429" -or $message -match "limit") { Start-Sleep -Seconds 120 } else { Start-Sleep -Seconds 15 }
                }
            }
            if (-not $ok) { $failed += "$($loc.airport)_$year" }
        }
    }
    $status = [ordered]@{
        mode = $Mode
        fetched_at = (Get-Date).ToUniversalTime().ToString("o")
        machine = $env:COMPUTERNAME
        minutes = [math]::Round(((Get-Date) - $started).TotalMinutes, 1)
        variables = $vars
        weather_files = (Get-ChildItem $weatherDir -Filter "*.json").Count
        weather_pulled_now = $done
        weather_kept = $kept
        weather_failed = $failed
    }
}
elseif ($Mode -eq "faaref") {
    # The daily ReleasableAircraft.zip of 2026-09-29 shipped without ACFTREF.txt, the file that names the
    # make and model behind each MFR MDL CODE. Try the yearly archives and the next daily build.
    $tried = @()
    $candidates = @(
        @{ name = "ReleasableAircraft.2025.zip"; url = "https://registry.faa.gov/database/yearly/ReleasableAircraft.2025.zip" },
        @{ name = "ReleasableAircraft.2024.zip"; url = "https://registry.faa.gov/database/yearly/ReleasableAircraft.2024.zip" },
        @{ name = "ReleasableAircraft.daily.zip"; url = "https://registry.faa.gov/database/ReleasableAircraft.zip" }
    )
    foreach ($c in $candidates) {
        $dest = Join-Path $faaDir $c.name
        if (Test-Zip $dest) { $tried += "$($c.name) kept"; continue }
        Write-Host "faa: $($c.url)"
        $code = Get-File $c.url $dest $browserAgent
        if ($code -eq 0 -and (Test-Zip $dest)) {
            Write-Host "  ok $((Get-Item $dest).Length) bytes"
            $tried += "$($c.name) ok"
        } else {
            Write-Host "  not available (curl $code)"
            if (Test-Path $dest) { Remove-Item $dest -Force }
            $tried += "$($c.name) missing"
        }
    }
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $members = @{}
    foreach ($zip in Get-ChildItem $faaDir -Filter "*.zip") {
        $archive = [IO.Compression.ZipFile]::OpenRead($zip.FullName)
        try { $members[$zip.Name] = @($archive.Entries | ForEach-Object { $_.FullName }) } finally { $archive.Dispose() }
    }
    $status = [ordered]@{
        mode = $Mode
        fetched_at = (Get-Date).ToUniversalTime().ToString("o")
        machine = $env:COMPUTERNAME
        minutes = [math]::Round(((Get-Date) - $started).TotalMinutes, 1)
        tried = $tried
        members = $members
    }
}
else { throw "unknown mode $Mode (use flights, weather or faaref)" }

$status | ConvertTo-Json -Depth 4 | Set-Content -Path (Join-Path $root "fetch-status-$Mode.json") -Encoding UTF8
Write-Host "fetch $Mode finished in $($status.minutes) minutes"
Stop-Transcript | Out-Null
