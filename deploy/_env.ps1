# Shared by the deploy scripts: read KEY=VALUE lines from the .env beside the repository (and one
# inside it, if present) into this process only. Nothing read here is ever printed.
function Read-DotEnv($path) {
    if (Test-Path $path) {
        Get-Content $path | ForEach-Object {
            if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$') {
                $name = $matches[1]; $value = $matches[2].Trim().Trim('"').Trim("'")
                if (-not [string]::IsNullOrEmpty($value)) { [Environment]::SetEnvironmentVariable($name, $value, "Process") }
            }
        }
    }
}

function Use-Flyctl {
    if (-not (Get-Command flyctl -ErrorAction SilentlyContinue)) {
        $candidate = Join-Path $env:USERPROFILE ".fly\bin\flyctl.exe"
        if (-not (Test-Path $candidate)) {
            Write-Host "installing flyctl"
            Invoke-WebRequest -UseBasicParsing https://fly.io/install.ps1 | Invoke-Expression
        }
        $env:Path = "$env:USERPROFILE\.fly\bin;$env:Path"
    }
}
