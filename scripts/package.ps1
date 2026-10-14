$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
$Destination = Join-Path (Get-Location) "dist\WaterReminder-project.zip"
New-Item -ItemType Directory -Force dist | Out-Null
$Files = @(
    "water_reminder", "tests", "scripts", "installer", "docs",
    "run.pyw", "WaterReminder.spec", "requirements.txt", "requirements-dev.txt",
    "requirements-lock.txt", "pyproject.toml", "README.md", ".gitignore",
    "prompt.txt", "prompt-notification-messages.txt"
)
$Existing = $Files | Where-Object { Test-Path $_ }
# Compress-Archive includes caches inside folders: exclude them using an explicit file list.
Add-Type -AssemblyName System.IO.Compression.FileSystem
$Stream = [System.IO.File]::Open($Destination, [System.IO.FileMode]::Create)
$Zip = [System.IO.Compression.ZipArchive]::new(
    $Stream, [System.IO.Compression.ZipArchiveMode]::Create
)
try {
    foreach ($Item in $Existing) {
        $Entries = if (Test-Path $Item -PathType Container) {
            Get-ChildItem $Item -File -Recurse | Where-Object {
                $_.FullName -notmatch '\\(__pycache__|\.ruff_cache)\\'
            }
        } else { Get-Item $Item }
        foreach ($Entry in $Entries) {
            $Relative = [System.IO.Path]::GetRelativePath((Get-Location).Path, $Entry.FullName)
            [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
                $Zip, $Entry.FullName, $Relative.Replace('\', '/')
            ) | Out-Null
        }
    }
    foreach ($Binary in @("WaterReminder.exe", "WaterReminderSetup.exe")) {
        $Path = Join-Path (Get-Location) "dist\$Binary"
        if (Test-Path $Path) {
            [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
                $Zip, $Path, "bin/$Binary"
            ) | Out-Null
        }
    }
} finally {
    $Zip.Dispose()
    $Stream.Dispose()
}
Write-Output $Destination
