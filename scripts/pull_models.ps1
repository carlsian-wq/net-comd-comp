# pull_models.ps1 — pull Ollama models from config.yaml
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ConfigPath = Join-Path $ProjectRoot "config.yaml"
$ollamaCli = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"

if (-not (Test-Path $ollamaCli)) {
    Write-Host "Ollama not found. Install from https://ollama.com"
    exit 1
}

$chat = "qwen2.5:7b"
$embed = "nomic-embed-text"
if (Test-Path $ConfigPath) {
    $content = Get-Content $ConfigPath -Raw
    if ($content -match '(?m)^\s*chat_model:\s*(\S+)') { $chat = $Matches[1] }
    if ($content -match '(?m)^\s*embed_model:\s*(\S+)') { $embed = $Matches[1] }
}

Write-Host "Pulling chat model: $chat"
& $ollamaCli pull $chat
Write-Host "Pulling embed model: $embed"
& $ollamaCli pull $embed
Write-Host "Done."