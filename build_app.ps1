<#
.SYNOPSIS
  Builds the Sales Coach Windows app (dist\SalesCoach\SalesCoach.exe).

.DESCRIPTION
  Run from the project folder (the one containing launcher.py) in PowerShell,
  with your virtual environment activated:

      .\build_app.ps1
      .\build_app.ps1 -UiProject C:\path\to\your-ui-project -WhisperModel small

  The UI folder is remembered after the first successful run, so you only
  need -UiProject once.

  Before running:
    - HF_TOKEN must be in your .env file (used once to download the pyannote models)
    - the React project's src\CallReviewUI.jsx must be the latest version
    - node/npm must be installed (you already use it for the UI)

  The first build is slow (downloading models, then bundling torch).
  Later builds can skip the model download with -SkipModels.
#>
param(
    [string]$UiProject = "",
    [string]$WhisperModel = "small",
    [switch]$SkipModels
)

$ErrorActionPreference = "Stop"

function Step($message) { Write-Host "`n==> $message" -ForegroundColor Cyan }
function Check($what) {
    if ($LASTEXITCODE -ne 0) { throw "$what failed (exit code $LASTEXITCODE)" }
}

if (-not (Test-Path "launcher.py")) { throw "Run this from the project folder that contains launcher.py." }

# The UI folder: use -UiProject if given, otherwise the folder remembered from
# the last successful run, otherwise the default sibling folder.
$pathMemo = ".ui_project_path"
if (-not $UiProject) {
    if (Test-Path $pathMemo) { $UiProject = (Get-Content $pathMemo -Raw).Trim() }
    else                     { $UiProject = "..\sales-coach-ui" }
}
if (-not (Test-Path $UiProject)) { throw "UI project not found at '$UiProject'. Pass -UiProject <path> (it is remembered for next time)." }
Set-Content -Path $pathMemo -Value (Resolve-Path $UiProject).Path

Step "Installing Python dependencies and PyInstaller"
python -m pip install --upgrade pyinstaller; Check "Installing PyInstaller"
python -m pip install -r requirements.txt;   Check "Installing requirements"

Step "Building the web UI"
Push-Location $UiProject
try {
    npm install;       Check "npm install"
    npm run build;     Check "npm run build"
} finally {
    Pop-Location
}
if (Test-Path "ui") { Remove-Item "ui" -Recurse -Force }
Copy-Item (Join-Path $UiProject "dist") "ui" -Recurse

if (-not $SkipModels) {
    Step "Downloading speech models (Whisper '$WhisperModel' + pyannote) - this can take a while"
    if (Test-Path "models") { Remove-Item "models" -Recurse -Force }
    $env:WHISPER_MODEL = $WhisperModel
    python prefetch_models.py; Check "Downloading models"
} elseif (-not (Test-Path "models")) {
    throw "-SkipModels was given but there is no 'models' folder yet. Run once without it."
}

Step "Bundling the app with PyInstaller - this is the slow part"
python -m PyInstaller SalesCoach.spec --noconfirm --clean; Check "PyInstaller"

Copy-Item "START_HERE.txt" "dist\SalesCoach\START_HERE.txt"

$sizeGb = [math]::Round(((Get-ChildItem "dist\SalesCoach" -Recurse -File | Measure-Object Length -Sum).Sum / 1GB), 2)
Write-Host "`nDone. dist\SalesCoach is $sizeGb GB." -ForegroundColor Green
Write-Host "Test it:  .\dist\SalesCoach\SalesCoach.exe"
Write-Host "To share: zip the whole dist\SalesCoach folder (right-click > Send to > Compressed folder)."
