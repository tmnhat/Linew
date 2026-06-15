# check-google-setup.ps1
# Script kiem tra cau hinh Google Indexing API

$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Google Indexing API Setup Checker" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$checks = @()
$allPassed = $true

# Check 1: GOOGLE_SERVICE_ACCOUNT_JSON in .env
Write-Host "[1] Kiem tra GOOGLE_SERVICE_ACCOUNT_JSON trong .env..." -ForegroundColor Yellow
$envContent = Get-Content ".env" -Raw -ErrorAction SilentlyContinue
if ($envContent -match 'GOOGLE_SERVICE_ACCOUNT_JSON=.{50,}') {
    Write-Host "    [OK] GOOGLE_SERVICE_ACCOUNT_JSON da duoc cau hinh" -ForegroundColor Green
    $checks += @{Name="GOOGLE_SERVICE_ACCOUNT_JSON"; Status="OK"}
} else {
    Write-Host "    [FAIL] GOOGLE_SERVICE_ACCOUNT_JSON chua duoc cau hinh" -ForegroundColor Red
    Write-Host "           Can them GOOGLE_SERVICE_ACCOUNT_JSON vao file .env" -ForegroundColor Gray
    $checks += @{Name="GOOGLE_SERVICE_ACCOUNT_JSON"; Status="FAIL"}
    $allPassed = $false
}

# Check 2: GOOGLE_SITE_URL in .env
Write-Host ""
Write-Host "[2] Kiem tra GOOGLE_SITE_URL trong .env..." -ForegroundColor Yellow
if ($envContent -match 'GOOGLE_SITE_URL=https?://') {
    $siteUrl = [regex]::Match($envContent, 'GOOGLE_SITE_URL=(.+)').Groups[1].Value.Split("`r")[0]
    Write-Host "    [OK] GOOGLE_SITE_URL: $siteUrl" -ForegroundColor Green
    $checks += @{Name="GOOGLE_SITE_URL"; Status="OK"}
} else {
    Write-Host "    [WARN] GOOGLE_SITE_URL chua duoc cau hinh hoac sai dinh dang" -ForegroundColor Yellow
    Write-Host "           Mac dinh se su dung: https://litimez.ai/" -ForegroundColor Gray
    $checks += @{Name="GOOGLE_SITE_URL"; Status="WARN"}
}

# Check 3: Google service account JSON file
Write-Host ""
Write-Host "[3] Kiem tra file google-service-account.json..." -ForegroundColor Yellow
if (Test-Path "config\google-service-account.json") {
    try {
        $json = Get-Content "config\google-service-account.json" -Raw | ConvertFrom-Json
        Write-Host "    [OK] File credentials hop le" -ForegroundColor Green
        Write-Host "         Project: $($json.project_id)" -ForegroundColor Gray
        Write-Host "         Client: $($json.client_email)" -ForegroundColor Gray
        $checks += @{Name="Credentials File"; Status="OK"}
    } catch {
        Write-Host "    [FAIL] File JSON khong hop le: $($_.Exception.Message)" -ForegroundColor Red
        $checks += @{Name="Credentials File"; Status="FAIL"}
        $allPassed = $false
    }
} else {
    Write-Host "    [INFO] File google-service-account.json khong ton tai trong config/" -ForegroundColor Gray
    Write-Host "           Day khong bat buoc neu GOOGLE_SERVICE_ACCOUNT_JSON da duoc dat trong .env" -ForegroundColor Gray
    $checks += @{Name="Credentials File"; Status="SKIP"}
}

# Check 4: Docker containers running
Write-Host ""
Write-Host "[4] Kiem tra Docker containers..." -ForegroundColor Yellow
$apiRunning = docker ps --filter "name=linew-api" --format "{{.Names}}" 2>$null
$workerRunning = docker ps --filter "name=linew-worker" --format "{{.Names}}" 2>$null

if ($apiRunning) {
    Write-Host "    [OK] API container dang chay" -ForegroundColor Green
    $checks += @{Name="API Container"; Status="OK"}
} else {
    Write-Host "    [WARN] API container chua chay" -ForegroundColor Yellow
    Write-Host "           Chay: docker-compose up -d" -ForegroundColor Gray
    $checks += @{Name="API Container"; Status="WARN"}
}

# Check 5: API health
if ($apiRunning) {
    Write-Host ""
    Write-Host "[5] Kiem tra API connection..." -ForegroundColor Yellow
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/api/seo/test-connections" -TimeoutSec 5 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            $data = $response.Content | ConvertFrom-Json
            if ($data.google.status -eq "connected") {
                Write-Host "    [OK] Google Indexing API da ket noi" -ForegroundColor Green
                $checks += @{Name="Google API Connection"; Status="OK"}
            } else {
                Write-Host "    [WARN] Google status: $($data.google.status)" -ForegroundColor Yellow
                Write-Host "           Message: $($data.google.message)" -ForegroundColor Gray
                $checks += @{Name="Google API Connection"; Status="WARN"}
            }
        } else {
            Write-Host "    [FAIL] API tra ve status: $($response.StatusCode)" -ForegroundColor Red
            $checks += @{Name="Google API Connection"; Status="FAIL"}
            $allPassed = $false
        }
    } catch {
        Write-Host "    [FAIL] Khong the ket noi API: $($_.Exception.Message)" -ForegroundColor Red
        $checks += @{Name="Google API Connection"; Status="FAIL"}
        $allPassed = $false
    }
}

# Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

foreach ($check in $checks) {
    $color = switch ($check.Status) {
        "OK" { "Green" }
        "WARN" { "Yellow" }
        "FAIL" { "Red" }
        "SKIP" { "Gray" }
    }
    Write-Host ("  {0,-25} [{1}]" -f $check.Name, $check.Status) -ForegroundColor $color
}

Write-Host ""
if ($allPassed) {
    Write-Host "  All checks passed!" -ForegroundColor Green
} else {
    Write-Host "  Some checks failed. Please review the errors above." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
if (-not ($envContent -match 'GOOGLE_SERVICE_ACCOUNT_JSON=.{50,}')) {
    Write-Host "  1. Disable Organization Policy on Google Cloud Console" -ForegroundColor Gray
    Write-Host "  2. Create Service Account and download JSON key" -ForegroundColor Gray
    Write-Host "  3. Run: .\scripts\update-env-google.ps1" -ForegroundColor Gray
    Write-Host "  4. Restart: docker-compose down && docker-compose up -d" -ForegroundColor Gray
} else {
    Write-Host "  1. If API not connected, check Google Search Console permissions" -ForegroundColor Gray
    Write-Host "  2. Verify service account email has access to Search Console" -ForegroundColor Gray
    Write-Host "  3. Restart if needed: docker-compose restart api" -ForegroundColor Gray
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
