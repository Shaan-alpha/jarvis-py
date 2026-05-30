# build.ps1 — produce dist/JarvisAI/ (Windows only)
# Usage:  .\build.ps1
$ErrorActionPreference = "Stop"

Write-Host "Cleaning previous build..."
if (Test-Path build) { Remove-Item -Recurse -Force build }
if (Test-Path dist)  { Remove-Item -Recurse -Force dist }

Write-Host "Running PyInstaller (one-folder)..."
pyinstaller jarvis.spec

Write-Host ""
Write-Host "Build complete: dist\JarvisAI\Jarvis.exe"
Write-Host "Models bundled under dist\JarvisAI\models\"
Write-Host "Reminder: the target machine needs Ollama installed + a model pulled,"
Write-Host "and the Microsoft WebView2 runtime for the HUD."
