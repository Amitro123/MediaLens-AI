Write-Host "📺 Starting MediaLens AI..." -ForegroundColor Green

$root = Get-Location

# 1. Start Backend
Write-Host "🚀 Starting Backend..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; python run.py" -WorkingDirectory $root

# 2. Start Frontend
Write-Host "🎨 Starting Frontend..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; npm run dev" -WorkingDirectory $root

Write-Host "✅ Systems initiating..." -ForegroundColor Green
Write-Host "   Backend: http://localhost:8000"
Write-Host "   Frontend: http://localhost:5173"
Write-Host "PRESS ANY KEY TO EXIT THIS LAUNCHER (Servers will keep running)"
Read-Host
