#Requires -RunAsAdministrator
# ===================================================================
# LINEW EXPORT — Chạy trên máy Windows CŨ
# Tạo folder export chứa MỌI THỨ cần thiết để migrate sang máy mới
# ===================================================================

param(
    [string]$LinewPath = "C:\Linew",
    [string]$DataPath = "C:\Linew-Data",
    [string]$ExportPath = "C:\Linew-Export"
)

$ErrorActionPreference = "Stop"

function Write-Step($step, $msg) {
    Write-Host "`n[$step] $msg" -ForegroundColor Yellow
}

function Write-Ok($msg) {
    Write-Host "  ✅ $msg" -ForegroundColor Green
}

function Write-Warn($msg) {
    Write-Host "  ⚠️ $msg" -ForegroundColor Yellow
}

function Write-Fail($msg) {
    Write-Host "  ❌ $msg" -ForegroundColor Red
}

# ===== START =====
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  LINEW EXPORT — Máy Windows cũ" -ForegroundColor Cyan
Write-Host "  Source: $LinewPath" -ForegroundColor Cyan
Write-Host "  Export to: $ExportPath" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# Verify Linew exists
if (-not (Test-Path "$LinewPath\docker-compose.yml")) {
    Write-Fail "Không tìm thấy Linew tại $LinewPath"
    Write-Host "Sửa lại: .\export-linew.ps1 -LinewPath 'D:\path\to\linew'" -ForegroundColor Cyan
    exit 1
}

# Clean + create export folder
if (Test-Path $ExportPath) {
    Remove-Item $ExportPath -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $ExportPath | Out-Null
New-Item -ItemType Directory -Force -Path "$ExportPath\configs" | Out-Null

# ===== STEP 1: Stop Linew =====
Write-Step "1/9" "Stopping Linew Docker services..."
Set-Location $LinewPath
docker compose down 2>$null
Write-Ok "Services stopped"

# ===== STEP 2: Export PostgreSQL =====
Write-Step "2/9" "Exporting PostgreSQL databases..."

# Start only postgres
docker compose up -d postgres 2>$null
Write-Host "  Waiting for PostgreSQL..." -ForegroundColor Gray
Start-Sleep -Seconds 12

# Check postgres ready
$pgReady = docker exec linew-postgres pg_isready -U linew 2>&1
if ($pgReady -notmatch "accepting") {
    Write-Host "  Waiting more..." -ForegroundColor Gray
    Start-Sleep -Seconds 10
}

# Dump all databases
docker exec linew-postgres pg_dumpall -U linew > "$ExportPath\full-database.sql" 2>$null
$dbSize = (Get-Item "$ExportPath\full-database.sql").Length / 1MB
Write-Ok "Database exported: $([math]::Round($dbSize, 1)) MB"

docker compose down 2>$null

# ===== STEP 3: Export WordPress volume =====
Write-Step "3/9" "Exporting WordPress files..."

$wpVolumeExists = docker volume ls --format "{{.Name}}" | Select-String "wpdata"
if ($wpVolumeExists) {
    docker run --rm -v linew_wpdata:/data -v "${ExportPath}:/backup" alpine tar czf /backup/wordpress-files.tar.gz -C /data . 2>$null
    $wpSize = (Get-Item "$ExportPath\wordpress-files.tar.gz").Length / 1MB
    Write-Ok "WordPress files exported: $([math]::Round($wpSize, 1)) MB"
} else {
    Write-Warn "WordPress volume not found, skipping"
}

# ===== STEP 4: Copy source code =====
Write-Step "4/9" "Copying source code..."

# Robocopy: fast copy, exclude unnecessary folders
robocopy $LinewPath "$ExportPath\linew-source" /E /XD node_modules __pycache__ .git venv .venv dashboard\dist /XF *.pyc /NFL /NDL /NJH /NJS /NC /NS /NP 2>$null

# Ensure .env files are copied (robocopy might skip hidden files)
Copy-Item "$LinewPath\.env" "$ExportPath\linew-source\.env" -Force -ErrorAction SilentlyContinue
Copy-Item "$LinewPath\.env.*" "$ExportPath\linew-source\" -Force -ErrorAction SilentlyContinue 2>$null

Write-Ok "Source code copied"

# ===== STEP 5: Copy Cloudflare Tunnel config =====
Write-Step "5/9" "Copying Cloudflare Tunnel config..."

$cfDir = "$env:USERPROFILE\.cloudflared"
if (Test-Path $cfDir) {
    Copy-Item $cfDir "$ExportPath\configs\cloudflared" -Recurse -Force

    # Ghi lại username hiện tại (để fix paths trên máy mới)
    "$env:USERNAME" | Out-File "$ExportPath\configs\old-username.txt"
    "$env:USERPROFILE" | Out-File "$ExportPath\configs\old-userprofile.txt"

    Write-Ok "Cloudflare config copied"
} else {
    Write-Warn "No .cloudflared directory found"
}

# ===== STEP 6: Copy rclone config =====
Write-Step "6/9" "Copying rclone config..."

$rcloneConf = "$env:APPDATA\rclone\rclone.conf"
if (Test-Path $rcloneConf) {
    New-Item -ItemType Directory -Force -Path "$ExportPath\configs\rclone" | Out-Null
    Copy-Item $rcloneConf "$ExportPath\configs\rclone\rclone.conf" -Force
    Write-Ok "rclone config copied"
} else {
    Write-Warn "No rclone config found"
}

# ===== STEP 7: Copy archive data =====
Write-Step "7/9" "Copying archive data..."

if (Test-Path "$DataPath\archive") {
    robocopy "$DataPath\archive" "$ExportPath\archive" /E /NFL /NDL /NJH /NJS /NC /NS /NP 2>$null
    $archiveSize = (Get-ChildItem "$ExportPath\archive" -Recurse -File | Measure-Object -Property Length -Sum).Sum / 1MB
    Write-Ok "Archive copied: $([math]::Round($archiveSize, 1)) MB"
} else {
    Write-Warn "No archive data found at $DataPath\archive"
}

# ===== STEP 8: Copy scheduled tasks info =====
Write-Step "8/9" "Saving scheduled tasks info..."

$tasks = Get-ScheduledTask | Where-Object { $_.TaskName -like "Linew*" }
if ($tasks) {
    $tasks | Format-List TaskName, Description, State | Out-File "$ExportPath\configs\scheduled-tasks.txt"
    Write-Ok "$($tasks.Count) scheduled tasks documented"
} else {
    Write-Warn "No Linew scheduled tasks found"
}

# ===== STEP 9: Generate import info =====
Write-Step "9/9" "Generating migration info..."

$info = @"
LINEW MIGRATION EXPORT
======================
Export Date: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
Source Machine: $env:COMPUTERNAME
Source OS: $(Get-CimInstance Win32_OperatingSystem | Select-Object -ExpandProperty Caption)
Source User: $env:USERNAME
Linew Path: $LinewPath
Data Path: $DataPath
Docker Version: $(docker --version 2>$null)

Files in this export:
- full-database.sql          PostgreSQL dump (linew + wordpress databases)
- wordpress-files.tar.gz     WordPress volume (themes, plugins, uploads)
- linew-source\              Complete source code + .env
- configs\cloudflared\       Cloudflare Tunnel credentials
- configs\rclone\            Google Drive backup config
- configs\old-username.txt   Username on source machine (for path fixing)
- archive\                   SQLite archive files (if any)

TO IMPORT ON NEW MACHINE:
1. Copy this entire folder to new machine (e.g. C:\Linew-Export)
2. Open PowerShell as Administrator on new machine
3. Run: .\import-linew.ps1 -ExportPath "C:\Linew-Export"
4. Wait for script to complete
5. Linew will be running automatically
"@
Set-Content "$ExportPath\README-MIGRATION.txt" $info

# Total export size
$totalSize = (Get-ChildItem $ExportPath -Recurse -File | Measure-Object -Property Length -Sum).Sum / 1MB

Write-Host "`n============================================" -ForegroundColor Green
Write-Host "  EXPORT COMPLETE" -ForegroundColor Green
Write-Host "  Location: $ExportPath" -ForegroundColor Green
Write-Host "  Total size: $([math]::Round($totalSize, 1)) MB" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "NEXT:" -ForegroundColor Yellow
Write-Host "  1. Copy folder '$ExportPath' to USB drive" -ForegroundColor Cyan
Write-Host "  2. On new machine, copy to C:\Linew-Export" -ForegroundColor Cyan
Write-Host "  3. Run import-linew.ps1 on new machine" -ForegroundColor Cyan
Write-Host ""

# Restart Linew on current machine
Write-Host "Restarting Linew on this machine..." -ForegroundColor Yellow
Set-Location $LinewPath
docker compose up -d 2>$null
Write-Ok "Linew restarted on current machine"
