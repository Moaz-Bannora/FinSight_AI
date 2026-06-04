@echo off
setlocal
set "PROJECT_ROOT=%~dp0.."
set "VENV_PYTHON=%PROJECT_ROOT%\.venv\Scripts\python.exe"

if not exist "%VENV_PYTHON%" (
  echo Could not find "%VENV_PYTHON%".
  echo Create the virtual environment and install requirements first.
  exit /b 1
)

"%VENV_PYTHON%" -m streamlit run "%PROJECT_ROOT%\app.py" --server.headless true --server.port 8501
