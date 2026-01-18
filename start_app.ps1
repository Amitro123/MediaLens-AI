Set-Location $PSScriptRoot
Write-Host "Starting MediaLens..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; python run.py"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; npm run dev"
