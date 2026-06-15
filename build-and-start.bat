@echo off
REM ============================================
REM Linew - Build & Start All Services
REM ============================================
REM 
REM Prerequisites:
REM   1. Docker Desktop must be installed
REM   2. Docker Desktop must be running
REM   3. Cloudflare DNS must point to this server
REM
REM Usage:
REM   Double-click this file OR run from PowerShell
REM ============================================

echo ============================================
echo  Linew - Build & Start Services
echo ============================================
echo.

REM Check if Docker is running
echo [1/5] Checking Docker status...
docker info >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Docker is not running!
    echo.
    echo Please:
    echo   1. Open Docker Desktop application
    echo   2. Wait for it to fully start (the whale icon stable)
    echo   3. Run this script again
    echo.
    pause
    exit /b 1
)
echo     Docker is running.
echo.

REM Check for .env file
echo [2/5] Checking configuration...
if not exist ".env" (
    echo     WARNING: .env file not found!
    echo     Creating .env from .env.example...
    copy .env.example .env 2>nul
    echo.
    echo     Please edit .env and configure your settings!
    echo     Important settings:
    echo       - WP_URL=https://litimez.ai
    echo       - AI_GATEWAY_KEY=your_vertex_key
    echo.
    pause
    exit /b 1
)
echo     Configuration OK.
echo.

REM Create data directory
echo [3/5] Creating directories...
if not exist "data" mkdir data
if not exist "dashboard\dist" mkdir dashboard\dist
echo     Directories ready.
echo.

REM Build images
echo [4/5] Building Docker images (first time takes 5-10 minutes)...
echo.
docker-compose build --parallel
if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    echo Check the output above for errors.
    pause
    exit /b 1
)
echo.
echo     Build completed.
echo.

REM Start services
echo [5/5] Starting services...
docker-compose up -d
if errorlevel 1 (
    echo.
    echo ERROR: Failed to start services!
    echo Check the output above for errors.
    pause
    exit /b 1
)
echo.

REM Wait for services to be healthy
echo Waiting for services to start...
timeout /t 10 /nobreak >nul

echo.
echo ============================================
echo  Services Started Successfully!
echo ============================================
echo.
echo Access URLs (after DNS propagates - may take 5-30 minutes):
echo.
echo   Main Site:       https://litimez.ai
echo   Dashboard:       https://litimez.ai/dashboard
echo   WordPress Admin:  https://litimez.ai/wp.admin
echo.
echo Local URLs (for testing):
echo.
echo   Main Site:       http://localhost/
echo   WordPress:       http://localhost:8888
echo   API:             http://localhost:8000
echo   API Docs:        http://localhost:8000/docs
echo   Dashboard:       http://localhost/
echo.
echo ============================================
echo  Useful Commands
echo ============================================
echo.
echo   Check status:   docker-compose ps
echo   View logs:      docker-compose logs -f
echo   View API logs:  docker-compose logs -f api
echo   Stop services:  docker-compose down
echo   Restart:        docker-compose restart
echo.
echo ============================================
echo  Troubleshooting
echo ============================================
echo.
echo   If site doesn't load:
echo   1. Wait 5-30 minutes for DNS to propagate
echo   2. Check Cloudflare dashboard - orange cloud should be ON
echo   3. Verify DNS A record points to your public IP
echo   4. Test locally: curl http://localhost:8888
echo.
echo   To check DNS propagation:
echo   https://dnschecker.org/#A/litimez.ai
echo.
echo ============================================
echo.

pause
