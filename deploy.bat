@echo off
rem ============================================================
rem  LightSlim - One-click DEPLOY (production / single port)
rem  Builds the frontend and serves it from the backend,
rem  so the whole app is reachable at http://localhost:8000
rem
rem  ASCII ONLY in this file (see start.bat for the reason).
rem
rem  Options are forwarded, e.g.:
rem    deploy.bat -Port 8080
rem    deploy.bat -SkipBuild
rem    deploy.bat -Foreground
rem ============================================================
setlocal
chcp 65001 >nul

set "PS1=%~dp0scripts\deploy.ps1"
if not exist "%PS1%" (
  echo [ERROR] Missing script: "%PS1%"
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%" %*
set "RC=%ERRORLEVEL%"

echo.
if not "%RC%"=="0" (
  echo [ERROR] deploy.ps1 exited with code %RC%
) else (
  echo [OK] Deployment finished.
)
pause
exit /b %RC%
