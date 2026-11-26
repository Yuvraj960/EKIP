@echo off
setlocal

:: 1. Verify uv package manager is available
where uv >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [EKIP] 'uv' package manager not found.
    echo [EKIP] Attempting bootstrap via pip...
    python -m pip install uv >nul 2>nul
    if %ERRORLEVEL% neq 0 (
        echo [EKIP] Error: Please install 'uv' from https://astral.sh/uv or ensure Python is on PATH.
        exit /b 1
    )
)

:: 2. Auto-bootstrap virtual environment and dependencies on clean clone
if not exist ".venv" (
    echo [EKIP] Fresh repository detected. Bootstrapping virtual environment and dependencies...
    uv sync --extra dev
    if %ERRORLEVEL% neq 0 (
        echo [EKIP] Error: Dependency installation failed. Please check network connectivity.
        exit /b 1
    )
    echo [EKIP] Environment initialized successfully.
)

:: 3. Auto-create .env from template if missing
if not exist ".env" (
    if exist ".env.example" (
        echo [EKIP] Generating .env from .env.example template...
        copy .env.example .env >nul
        echo [EKIP] Note: Please update GOOGLE_API_KEY in .env for live Gemini operations.
    )
)

:: 4. Dispatch command to unified CLI
uv run ekip %*
