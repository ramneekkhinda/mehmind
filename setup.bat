@echo off
REM MeshMind Local Development Setup Script for Windows
REM This script sets up MeshMind for local development

echo 🚀 Setting up MeshMind for local development...

REM Check prerequisites
echo 📋 Checking prerequisites...

REM Check if Docker is installed
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker is not installed. Please install Docker Desktop first.
    pause
    exit /b 1
)

REM Check if Docker Compose is available
docker compose version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker Compose is not available. Please ensure Docker Desktop is running.
    pause
    exit /b 1
)

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed. Please install Python 3.9+ first.
    pause
    exit /b 1
)

echo ✅ Prerequisites check passed!

REM Install Python dependencies
echo 📦 Installing Python dependencies...
python -m pip install -e .
if errorlevel 1 (
    echo ❌ Failed to install Python dependencies.
    pause
    exit /b 1
)

echo ✅ Python dependencies installed!

REM Start Docker services
echo 🐳 Starting Docker services...
docker compose up -d
if errorlevel 1 (
    echo ❌ Failed to start Docker services.
    pause
    exit /b 1
)

echo ⏳ Waiting for services to start...
timeout /t 10 /nobreak >nul

REM Check if services are running
echo 🔍 Checking service status...
docker compose ps | findstr "Up" >nul
if errorlevel 1 (
    echo ❌ Services failed to start. Check logs with: docker compose logs
    pause
    exit /b 1
)

echo ✅ Services are running!

REM Test referee health
echo 🏥 Testing referee health...
powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://localhost:8080/healthz' -UseBasicParsing; if ($response.Content -like '*healthy*') { Write-Host '✅ Referee service is healthy!' } else { Write-Host '❌ Referee service is not responding correctly.'; exit 1 } } catch { Write-Host '❌ Referee service is not responding. Check logs with: docker compose logs referee'; exit 1 }"
if errorlevel 1 (
    echo ❌ Health check failed.
    pause
    exit /b 1
)

echo.
echo 🎉 MeshMind setup complete!
echo.
echo 📊 Available services:
echo    • Referee API: http://localhost:8080
echo    • Jaeger UI: http://localhost:16686
echo    • PostgreSQL: localhost:5432
echo    • Redis: localhost:6379
echo.
echo 🧪 Run the demo:
echo    python examples/yc_demo/demo.py
echo.
echo 📖 View logs:
echo    docker compose logs -f
echo.
echo 🛑 Stop services:
echo    docker compose down
echo.
echo Happy developing! 🚀
pause
