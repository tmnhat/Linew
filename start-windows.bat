@echo off
REM ============================================
REM Linew Windows Startup Script
REM ============================================
REM This script starts all Linew services on Windows
REM Requirements:
REM   - Docker Desktop installed and running
REM   - Linew directory cloned to this location
REM ============================================

echo ============================================
echo  Linew Windows Startup Script
echo ============================================
echo.

REM Check if Docker is running
echo Checking Docker...
docker info >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not running!
    echo Please start Docker Desktop and try again.
    pause
    exit /b 1
)
echo Docker is running.
echo.

REM Check for .env file
if not exist ".env" (
    echo WARNING: .env file not found!
    echo Copy .env.example to .env and configure it.
    echo.
    if exist ".env.example" (
        echo Creating .env from .env.example...
        copy .env.example .env
        echo.
        echo Please edit .env and configure your settings!
        echo Important:
        echo   - WP_URL should be https://litimez.ai
        echo   - AI_GATEWAY_KEY should be your vertex-key API key
        echo.
    )
    pause
)

echo ============================================
echo  Starting Linew Services...
echo ============================================
echo.

REM Start Docker Compose services
docker-compose up -d

if errorlevel 1 (
    echo ERROR: Failed to start services!
    echo Check the output above for errors.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Services Started Successfully!
echo ============================================
echo.
echo Access URLs:
echo   - WordPress:   http://localhost:8888
echo   - WordPress:   https://litimez.ai (when DNS configured)
echo   - WordPress Admin: https://litimez.ai/wp.admin
echo   - Dashboard:   https://litimez.ai/dashboard
echo   - API:         http://localhost:8000
echo   - API Docs:    http://localhost:8000/docs
echo.
echo To check status: docker-compose ps
echo To view logs:    docker-compose logs -f
echo To stop:         docker-compose down
echo.

pause
