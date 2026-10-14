param([switch]$Installer)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
if ($Installer) {
    $Compiler = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    $Candidates = @(
        if ($Compiler) { $Compiler.Source }
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
    )
    $CompilerPath = $Candidates | Where-Object {
        Test-Path -LiteralPath $_ -PathType Leaf
    } | Select-Object -First 1
    if (-not $CompilerPath) {
        throw ("Inno Setup 6 est introuvable. Installez-le avec : " +
            "winget install --id JRSoftware.InnoSetup --exact --source winget --interactive " +
            "; puis relancez le build. Pour un dossier personnalisé, ajoutez-le au PATH.")
    }
}
$Python = Join-Path (Get-Location) ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    throw "Créez .venv et installez requirements-dev.txt avant de compiler."
}
& $Python scripts\generate_assets.py
if ($LASTEXITCODE -ne 0) { throw "La génération des images a échoué." }
& $Python -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw "Les tests ont échoué." }
& $Python -m ruff check .
if ($LASTEXITCODE -ne 0) { throw "La validation du code a échoué." }
& $Python -m PyInstaller --noconfirm WaterReminder.spec
if ($LASTEXITCODE -ne 0) { throw "La compilation PyInstaller a échoué." }
if ($Installer) {
    & $CompilerPath installer\WaterReminder.iss
    if ($LASTEXITCODE -ne 0) { throw "La compilation de l'installateur a échoué." }
}
