@echo off
rem ============================================================
rem  LightSlim - One-click START (development mode)
rem  Backend  : FastAPI/uvicorn  http://localhost:8000
rem  Frontend : Vite dev server http://localhost:5173
rem
rem  ASCII ONLY in this file. cmd.exe runs under code page 936
rem  and would corrupt any non-ASCII byte. All Chinese messages
rem  live in scripts\start.ps1 instead.
rem
rem  Options are forwarded, e.g.:
rem    start.bat -BackendPort 8001 -FrontendPort 5174
rem    start.bat -DryRun
rem ============================================================
setlocal
chcp 65001 >nul

set "PS1=%~dp0scripts\start.ps1"
if not exist "%PS1%" (
  echo [ERROR] Missing script: "%PS1%"
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%" %*
set "RC=%ERRORLEVEL%"

echo.
if not "%RC%"=="0" (
  echo [ERROR] start.ps1 exited with code %RC%
) else (
  echo [OK] Services launched in separate windows.
)
pause
exit /b %RC%
