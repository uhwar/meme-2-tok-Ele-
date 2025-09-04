# Reddit-to-TikTok Generator Launcher
Write-Host "Starting Reddit-to-TikTok Generator..." -ForegroundColor Green
Write-Host ""

# Get the script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& "venv\Scripts\Activate.ps1"

# Navigate to backend directory
Set-Location "thread-2-tok\backend"

# Run the app
Write-Host "Starting the app..." -ForegroundColor Green
Write-Host ""
py app.py

# Keep window open if there's an error
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "An error occurred. Press any key to exit..." -ForegroundColor Red
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}