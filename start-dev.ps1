# WinterStream AI - Development Startup Script (PowerShell)
# Run this script to start both backend and frontend servers

Write-Host "🏂 Starting WinterStream AI Development Environment" -ForegroundColor Cyan
Write-Host ""

# Check if Python virtual environment exists
$venvPath = "backend\venv"
if (-not (Test-Path $venvPath)) {
    Write-Host "Creating Python virtual environment..." -ForegroundColor Yellow
    python -m venv backend\venv
}

# Start Backend in new terminal
Write-Host "Starting Backend Server (FastAPI)..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", @"
    cd '$PSScriptRoot\backend'
    .\venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    Write-Host 'Starting FastAPI server on http://localhost:8000' -ForegroundColor Green
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
"@

# Wait a moment for backend to initialize
Start-Sleep -Seconds 3

# Start Frontend in new terminal
Write-Host "Starting Frontend Server (Next.js)..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", @"
    cd '$PSScriptRoot\frontend'
    npm install
    Write-Host 'Starting Next.js dev server on http://localhost:3000' -ForegroundColor Green
    npm run dev
"@

Write-Host ""
Write-Host "✨ Development servers starting!" -ForegroundColor Cyan
Write-Host ""
Write-Host "Backend API: http://localhost:8000" -ForegroundColor White
Write-Host "Frontend:    http://localhost:3000" -ForegroundColor White
Write-Host "API Docs:    http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "Press any key to exit this window (servers will keep running)..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
