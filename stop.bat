@echo off
rem ============================================================
rem  LightSlim - One-click STOP
rem  Terminates backend (uvicorn) and frontend (vite) processes
rem  started by start.bat / deploy.bat.
rem
rem  ASCII ONLY in this file (see start.bat for the reason).
rem
rem  Options are forwarded, e.g.:
rem    stop.bat -Ports 8000,5173,4173
rem ============================================================
setlocal
chcp 65001 >nul

set "PS1=%~dp0scripts\stop.ps1"
if not exist "%PS1%" (
  echo [ERROR] Missing script: "%PS1%"
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%" %*
set "RC=%ERRORLEVEL%"

echo.
pause
exit /b %RC%
