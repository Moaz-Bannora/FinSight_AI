$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$StorageDir = Join-Path $ProjectRoot "outputs\qdrant_storage"
New-Item -ItemType Directory -Force -Path $StorageDir | Out-Null

$docker = Get-Command docker -ErrorAction SilentlyContinue
if (-not $docker) {
    Write-Host "Docker was not found. Install Docker Desktop or run Qdrant another way, then use http://localhost:6333."
    Write-Host "The Streamlit app itself does not require Qdrant."
    exit 1
}

docker info *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker is installed, but Docker Desktop or the Docker daemon is not running."
    Write-Host "Start Docker Desktop and wait until the engine is running, then retry this command."
    Write-Host "Qdrant is optional. The Streamlit app works without it using Chroma, sample docs, and uploads."
    exit 1
}

$existing = docker ps --filter "name=finance-doc-qdrant" --format "{{.Names}}"
if ($existing -contains "finance-doc-qdrant") {
    Write-Host "Qdrant is already running at http://localhost:6333"
    exit 0
}

docker run --name finance-doc-qdrant --rm -p 6333:6333 -p 6334:6334 -v "${StorageDir}:/qdrant/storage" qdrant/qdrant
