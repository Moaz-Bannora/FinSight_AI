$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    throw "Could not find $VenvPython. Create the virtual environment and install requirements first."
}

& $VenvPython -m streamlit run (Join-Path $ProjectRoot "app.py") --server.headless true --server.port 8501
