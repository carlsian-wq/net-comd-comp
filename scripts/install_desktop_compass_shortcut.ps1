# install_desktop_compass_shortcut.ps1
# Desktop shortcut for Net Command Comparator — compass icon, same flow as launch.ps1.
#
# Run once:
#   powershell -ExecutionPolicy Bypass -File scripts\install_desktop_compass_shortcut.ps1

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$LauncherPs1 = Join-Path $ProjectRoot "scripts\launch.ps1"
$BuildIcon = Join-Path $ProjectRoot "scripts\build_compass_icon.py"
$Python = Join-Path $ProjectRoot "venv\Scripts\python.exe"
$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $Desktop "Net Command Comparator.lnk"
$Icon = Join-Path $ProjectRoot "assets\compass_logo.ico"
$PowerShellExe = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"

if (-not (Test-Path $LauncherPs1)) {
    Write-Error "Launcher not found: $LauncherPs1"
}

if (Test-Path $Python) {
    $pillowOk = & $Python -c "import PIL" 2>$null; $LASTEXITCODE -eq 0
    if (-not $pillowOk) {
        Write-Host "Installing Pillow for compass icon..."
        & $Python -m pip install pillow -q
    }
    if (Test-Path $BuildIcon) {
        & $Python $BuildIcon
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Compass icon build failed; shortcut will use a default icon."
        }
    }
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($ShortcutPath)
$shortcut.TargetPath = $PowerShellExe
$shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$LauncherPs1`""
$shortcut.WorkingDirectory = $ProjectRoot
$shortcut.WindowStyle = 1
$shortcut.Description = "Net Command Comparator - Cisco / Arista CLI"
if (Test-Path $Icon) {
    $shortcut.IconLocation = "$Icon,0"
}
$shortcut.Save()

Write-Host "Desktop shortcut created:" -ForegroundColor Green
Write-Host "  $ShortcutPath"
Write-Host ""
Write-Host "Double-click 'Net Command Comparator' on your Desktop (compass icon)."
Write-Host "Same as: powershell -ExecutionPolicy Bypass -File scripts\launch.ps1"
Write-Host "Opens http://localhost:8503 in Chrome/Edge app mode."