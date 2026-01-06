<#
.SYNOPSIS
    DevLens AI - Unified Startup Script
    
.DESCRIPTION
    Starts the DevLens stack in Local Mode:
    - Backend (FastAPI)
    - Frontend (React/Vite with TypeScript + shadcn/ui)

.NOTES
    Run from project root: .\start_devlens.ps1
    Ensure you have a .env file with GEMINI_API_KEY before running.
#>

param(
    [switch]$SkipDocker,
    [switch]$BackendOnly,
    [switch]$FrontendOnly
)

$ErrorActionPreference = "Continue"

function Write-Status {
    param([string]$Message, [string]$Status = "INFO")
    
    switch ($Status) {
        "OK" { Write-Host "[OK] $Message" -ForegroundColor Green }
        "ERROR" { Write-Host "[X] $Message" -ForegroundColor Red }
        "WARN" { Write-Host "[!] $Message" -ForegroundColor Yellow }
        default { Write-Host "[*] $Message" -ForegroundColor Cyan }
    }
}

function Write-Banner {
    Write-Host ""
    Write-Host "=============================================================" -ForegroundColor Cyan
    Write-Host "              DevLens AI - Local Development                 " -ForegroundColor Cyan
    Write-Host "=============================================================" -ForegroundColor Cyan
    Write-Host ""
}

function Test-EnvFile {
    # Check both locations - root and backend folder
    $rootEnvPath = Join-Path $PSScriptRoot ".env"
    $backendEnvPath = Join-Path $PSScriptRoot "backend\.env"
    
    $envPath = $null
    if (Test-Path $rootEnvPath) {
        $envPath = $rootEnvPath
    }
    elseif (Test-Path $backendEnvPath) {
        $envPath = $backendEnvPath
    }
    
    if (-not $envPath) {
        Write-Host ""
        Write-Host "=============================================================" -ForegroundColor Red
        Write-Host "  ERROR: Missing .env file!" -ForegroundColor Red
        Write-Host "=============================================================" -ForegroundColor Red
        Write-Host ""
        Write-Host "  Please create .env in the project root with your API keys:" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "    GEMINI_API_KEY=your_gemini_api_key_here" -ForegroundColor White
        Write-Host "    GROQ_API_KEY=your_groq_api_key_here     (optional)" -ForegroundColor Gray
        Write-Host ""
        Write-Host "  Get your Gemini API key at:" -ForegroundColor Cyan
        Write-Host "    https://makersuite.google.com/app/apikey" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "=============================================================" -ForegroundColor Red
        Write-Host ""
        return $false
    }
    
    # Check if GEMINI_API_KEY is set
    $content = Get-Content $envPath -Raw
    if ($content -notmatch "GEMINI_API_KEY\s*=\s*\S+") {
        Write-Status "GEMINI_API_KEY not set in .env file" "WARN"
        return $false
    }
    
    return $true
}

function Start-Backend {
    Write-Status "Starting Backend Server..." "INFO"
    
    $backendPath = Join-Path $PSScriptRoot "backend"
    $requirementsPath = Join-Path $PSScriptRoot "requirements.txt"
    
    if (-not (Test-Path $backendPath)) {
        Write-Status "Backend directory not found: $backendPath" "ERROR"
        return $false
    }
    
    $cmd = @"
Set-Location '$backendPath'
Write-Host ''
Write-Host '============================================' -ForegroundColor Cyan
Write-Host '      DevLens Backend Server                ' -ForegroundColor Cyan  
Write-Host '============================================' -ForegroundColor Cyan
Write-Host ''
Write-Host 'Installing dependencies...' -ForegroundColor Yellow
pip install -r '$requirementsPath' --quiet 2>&1 | Out-Null
Write-Host 'Starting server at http://localhost:8000...' -ForegroundColor Green
Write-Host ''
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"@
    
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $cmd
    
    Write-Status "Backend server starting in new window..." "OK"
    return $true
}

function Start-Frontend {
    Write-Status "Starting Frontend Server..." "INFO"
    
    $frontendPath = Join-Path $PSScriptRoot "frontend"
    
    if (-not (Test-Path $frontendPath)) {
        Write-Status "Frontend directory not found: $frontendPath" "ERROR"
        return $false
    }
    
    $nodeModules = Join-Path $frontendPath "node_modules"
    $installCmd = ""
    if (-not (Test-Path $nodeModules)) {
        $installCmd = "Write-Host 'Installing npm dependencies...' -ForegroundColor Yellow; npm install;"
    }
    
    $cmd = @"
Set-Location '$frontendPath'
Write-Host ''
Write-Host '============================================' -ForegroundColor Magenta
Write-Host '      DevLens Frontend (Lovable UI v2.0)    ' -ForegroundColor Magenta
Write-Host '============================================' -ForegroundColor Magenta
Write-Host ''
$installCmd
Write-Host 'Starting at http://localhost:5173...' -ForegroundColor Green
Write-Host ''
npm run dev
"@
    
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $cmd
    
    Write-Status "Frontend server starting in new window..." "OK"
    return $true
}

function Write-Summary {
    Write-Host ""
    Write-Host "=============================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  DevLens AI Started Successfully!" -ForegroundColor Green
    Write-Host "  Running in Local Mode (No Docker)" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Open in your browser:" -ForegroundColor White
    Write-Host ""
    Write-Host "    Frontend:    http://localhost:5173" -ForegroundColor Cyan
    Write-Host "    Backend API: http://localhost:8000" -ForegroundColor Cyan
    Write-Host "    API Docs:    http://localhost:8000/docs" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Quick Start:" -ForegroundColor White
    Write-Host "    1. Click 'Get Started' or go to Dashboard" -ForegroundColor Gray
    Write-Host "    2. Select a documentation mode (Bug Report, etc.)" -ForegroundColor Gray
    Write-Host "    3. Upload a video via drag-and-drop" -ForegroundColor Gray
    Write-Host "    4. View generated documentation" -ForegroundColor Gray
    Write-Host ""
    Write-Host "=============================================================" -ForegroundColor Green
    Write-Host ""
}

# ============================================================================
# Main Script
# ============================================================================

Write-Banner

# Check for .env file
if (-not (Test-EnvFile)) {
    Write-Host "Press any key to exit..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}

Write-Status ".env file found" "OK"

# Start Backend
if (-not $FrontendOnly) {
    Start-Backend | Out-Null
    Start-Sleep -Seconds 2
}

# Start Frontend
if (-not $BackendOnly) {
    Start-Frontend | Out-Null
}

# Print Summary
Start-Sleep -Seconds 1
Write-Summary
