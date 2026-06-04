@echo off
setlocal
set "PROJECT_ROOT=%~dp0.."
set "STORAGE_DIR=%PROJECT_ROOT%\outputs\qdrant_storage"
if not exist "%STORAGE_DIR%" mkdir "%STORAGE_DIR%"

where docker >nul 2>nul
if errorlevel 1 (
  echo Docker was not found. Install Docker Desktop or run Qdrant another way, then use http://localhost:6333.
  echo The Streamlit app itself does not require Qdrant.
  exit /b 1
)

docker info >nul 2>nul
if errorlevel 1 (
  echo Docker is installed, but Docker Desktop or the Docker daemon is not running.
  echo Start Docker Desktop and wait until the engine is running, then retry this command.
  echo Qdrant is optional. The Streamlit app works without it using Chroma, sample docs, and uploads.
  exit /b 1
)

docker ps --filter "name=finance-doc-qdrant" --format "{{.Names}}" | findstr /x "finance-doc-qdrant" >nul
if not errorlevel 1 (
  echo Qdrant is already running at http://localhost:6333
  exit /b 0
)

docker run --name finance-doc-qdrant --rm -p 6333:6333 -p 6334:6334 -v "%STORAGE_DIR%:/qdrant/storage" qdrant/qdrant
