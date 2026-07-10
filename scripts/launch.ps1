# launch.ps1 — start Net Command Comparator (Streamlit) with Ollama ready.
param(
    [int]$Port = 0,
    [string]$Browser = "chrome"
)

$ErrorActionPreference = "Continue"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ConfigPath = Join-Path $ProjectRoot "config.yaml"
$VenvPython = Join-Path $ProjectRoot "venv\Scripts\python.exe"
$Streamlit = Join-Path $ProjectRoot "venv\Scripts\streamlit.exe"

function Get-ConfigPort {
    if (-not (Test-Path $ConfigPath)) { return 8503 }
    $content = Get-Content $ConfigPath -Raw
    if ($content -match '(?m)^\s*port:\s*(\d+)') { return [int]$Matches[1] }
    return 8503
}

function Get-ConfigHost {
    if (-not (Test-Path $ConfigPath)) { return "0.0.0.0" }
    $content = Get-Content $ConfigPath -Raw
    if ($content -match '(?m)^\s*host:\s*(\S+)') { return $Matches[1].Trim() }
    return "0.0.0.0"
}

if ($Port -le 0) { $Port = Get-ConfigPort }
$HostAddr = Get-ConfigHost
$Url = "http://localhost:$Port"

function Test-ServerUp([string]$BaseUrl) {
    try {
        $resp = Invoke-WebRequest -Uri $BaseUrl -UseBasicParsing -TimeoutSec 3
        return ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 500)
    } catch { return $false }
}

function Test-OllamaApi {
    try {
        $null = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/version" -TimeoutSec 3
        return $true
    } catch { return $false }
}

function Ensure-OllamaServer {
    if (Test-OllamaApi) { return $true }
    $ollamaCli = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
    if (-not (Test-Path $ollamaCli)) { return $false }
    Start-Process -FilePath $ollamaCli -ArgumentList @("serve") -WindowStyle Hidden
    $deadline = (Get-Date).AddSeconds(45)
    while ((Get-Date) -lt $deadline) {
        if (Test-OllamaApi) { return $true }
        Start-Sleep -Seconds 2
    }
    return $false
}

Ensure-OllamaServer | Out-Null

if (-not (Test-Path $Streamlit)) {
    Write-Host "Run: python -m venv venv && venv\Scripts\pip install -r requirements.txt"
    exit 1
}

if (-not (Test-ServerUp $Url)) {
    $cmd = "& '$Streamlit' run app.py --server.port $Port --server.address $HostAddr"
    Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoExit", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
        "Set-Location -LiteralPath '$ProjectRoot'; $cmd"
    ) -WorkingDirectory $ProjectRoot
    $deadline = (Get-Date).AddSeconds(45)
    while ((Get-Date) -lt $deadline) {
        if (Test-ServerUp $Url) { break }
        Start-Sleep -Milliseconds 500
    }
}

$chrome = "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe"
$edge = "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
$browserExe = if ($Browser -eq "edge" -and (Test-Path $edge)) { $edge }
              elseif (Test-Path $chrome) { $chrome }
              elseif (Test-Path $edge) { $edge }
              else { $null }

if ($browserExe) {
    Start-Process -FilePath $browserExe -ArgumentList @("--app=$Url", "--new-window")
} else {
    Start-Process $Url
}