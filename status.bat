@echo off
REM ============================================
REM Linew - Check Service Status
REM ============================================

echo ============================================
echo  Linew Service Status
echo ============================================
echo.

docker-compose ps

echo.
echo ============================================
echo  Service URLs
echo ============================================
echo.
echo   Main Site:       https://litimez.ai
echo   Dashboard:       https://litimez.ai/dashboard
echo   WordPress Admin:  https://litimez.ai/wp.admin
echo.
echo   Local API:       http://localhost:8000
echo   Local WP:        http://localhost:8888
echo.
pause
