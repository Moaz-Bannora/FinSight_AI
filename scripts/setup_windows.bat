@echo off
setlocal
set "PROJECT_ROOT=%~dp0.."
pushd "%PROJECT_ROOT%" >nul

where py >nul 2>nul
if not errorlevel 1 (
  set "PY_CMD=py -3"
) else (
  where python >nul 2>nul
  if errorlevel 1 (
    echo Python was not found. Install Python 3.10 or newer, then run this script again.
    popd >nul
    exit /b 1
  )
  set "PY_CMD=python"
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment...
  %PY_CMD% -m venv .venv
  if errorlevel 1 (
    echo Failed to create the virtual environment.
    popd >nul
    exit /b 1
  )
)

echo Installing project dependencies...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
  echo Failed to upgrade pip.
  popd >nul
  exit /b 1
)

".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo Failed to install requirements.txt.
  popd >nul
  exit /b 1
)

echo Setup complete.
echo Next:
echo   1. Install Ollama from https://ollama.com
echo   2. Run: ollama pull llama3.2:3b
echo   3. Run: ollama pull nomic-embed-text
echo   4. Start the app with: scripts\run_app.bat

popd >nul
