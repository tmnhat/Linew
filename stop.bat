@echo off
REM ============================================
REM Linew - Stop All Services
REM ============================================

echo ============================================
echo  Stopping Linew Services...
echo ============================================
echo.

docker-compose down

echo.
echo Services stopped.
echo.
pause
