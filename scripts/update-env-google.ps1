# update-env-google.ps1
# Script để tự động cập nhật file .env với Google Service Account credentials

param(
    [Parameter(Mandatory=$false)]
    [string]$EnvFile = ".env",

    [Parameter(Mandatory=$false)]
    [string]$GoogleJsonFile = "config\google-service-account.json"
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Update .env with Google Credentials" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if .env exists
if (-not (Test-Path $EnvFile)) {
    Write-Host "ERROR: File .env not found in current directory" -ForegroundColor Red
    Write-Host "Vui long chay script nay tu thu muc Linew" -ForegroundColor Yellow
    exit 1
}

# Check if Google JSON file exists
if (-not (Test-Path $GoogleJsonFile)) {
    Write-Host "ERROR: File not found: $GoogleJsonFile" -ForegroundColor Red
    Write-Host ""
    Write-Host "Vui long dam bao file google-service-account.json ton tai trong thu muc config/" -ForegroundColor Yellow
    exit 1
}

try {
    Write-Host "Doc file credentials: $GoogleJsonFile" -ForegroundColor Green
    
    # Read JSON file
    $jsonContent = Get-Content -Path $GoogleJsonFile -Raw -Encoding UTF8
    
    # Validate JSON
    $parsed = $jsonContent | ConvertFrom-Json
    Write-Host "Service Account: $($parsed.client_email)" -ForegroundColor Green
    Write-Host "Project ID: $($parsed.project_id)" -ForegroundColor Green
    
    # Remove all whitespace from JSON
    $encoded = $jsonContent -replace '[\r\n\t]', '' -replace '\s+', ''
    
    # Read current .env
    $envContent = Get-Content -Path $EnvFile -Raw -Encoding UTF8
    
    # Check if GOOGLE_SERVICE_ACCOUNT_JSON already exists
    if ($envContent -match 'GOOGLE_SERVICE_ACCOUNT_JSON=') {
        Write-Host ""
        Write-Host "Phat hien GOOGLE_SERVICE_ACCOUNT_JSON da ton tai trong .env" -ForegroundColor Yellow
        Write-Host "Se thay the gia tri cu..." -ForegroundColor Yellow
        
        # Replace existing value
        $envContent = $envContent -replace 'GOOGLE_SERVICE_ACCOUNT_JSON=.*', "GOOGLE_SERVICE_ACCOUNT_JSON=$encoded"
    } else {
        # Append to file
        $envContent = $envContent -replace '(\r?\n)$', "`$1"
        $envContent += "`r`n`r`n# Google Indexing API (for SEO ping)`r`n"
        $envContent += "GOOGLE_SERVICE_ACCOUNT_JSON=$encoded`r`n"
    }
    
    # Write back to .env
    $envContent | Out-File -FilePath $EnvFile -Encoding UTF8 -NoNewline
    
    Write-Host ""
    Write-Host "SUCCESS! Da cap nhat .env voi Google credentials" -ForegroundColor Green
    Write-Host ""
    Write-Host "Tiep theo:" -ForegroundColor Yellow
    Write-Host "  1. Khoi dong lai Linew: docker-compose down && docker-compose up -d" -ForegroundColor Gray
    Write-Host "  2. Kiem tra ket noi: curl http://localhost:8000/api/seo/test-connections" -ForegroundColor Gray
    Write-Host ""
    
} catch {
    Write-Host ""
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host "========================================" -ForegroundColor Cyan
