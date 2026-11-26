param(
    [Parameter(ValueFromRemainingArguments = $true)]
    $RemainingArgs
)

# 1. Verify uv package manager is available
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "[EKIP] 'uv' package manager not found. Attempting install via pip..." -ForegroundColor Yellow
    python -m pip install uv | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[EKIP] Error: Please install 'uv' from https://astral.sh/uv" -ForegroundColor Red
        exit 1
    }
}

# 2. Auto-bootstrap virtual environment and dependencies on clean clone
if (-not (Test-Path ".venv")) {
    Write-Host "[EKIP] Fresh repository detected. Bootstrapping virtual environment and dependencies..." -ForegroundColor Cyan
    uv sync --extra dev
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[EKIP] Error: Dependency installation failed. Please check network connectivity." -ForegroundColor Red
        exit 1
    }
    Write-Host "[EKIP] Environment initialized successfully." -ForegroundColor Green
}

# 3. Auto-create .env from template if missing
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Write-Host "[EKIP] Generating .env from .env.example template..." -ForegroundColor Yellow
        Copy-Item ".env.example" ".env"
        Write-Host "[EKIP] Note: Please update GOOGLE_API_KEY in .env for live Gemini operations." -ForegroundColor Yellow
    }
}

# 4. Dispatch command to unified CLI
uv run ekip @RemainingArgs
