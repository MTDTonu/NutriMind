<#
  知食 NutriMind · 一键启动（开发模式）

  同时拉起两个进程：
    - 后端 FastAPI / uvicorn  → http://localhost:8000  （--reload 热重载，/docs 接口文档）
    - 前端 Vite dev server     → http://localhost:5173 （/api 与 /uploads 已代理到后端）

  首次运行会自动：建虚拟环境、装后端依赖、从 .env.example 生成 .env、装前端依赖。

  用法：
    powershell -ExecutionPolicy Bypass -File scripts\start.ps1
    powershell -ExecutionPolicy Bypass -File scripts\start.ps1 -BackendPort 8001
    powershell -ExecutionPolicy Bypass -File scripts\start.ps1 -DryRun   # 只体检不启动
#>
[CmdletBinding()]
param(
    [int]$BackendPort  = 8000,
    [int]$FrontendPort = 5173,
    [switch]$NoBrowser,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }

# ---------- 路径 ----------
$Root        = Split-Path -Parent $PSScriptRoot
$BackendDir  = Join-Path $Root 'backend'
$FrontendDir = Join-Path $Root 'frontend'
$VenvDir     = Join-Path $BackendDir '.venv'
$VenvPy      = Join-Path $VenvDir 'Scripts\python.exe'
$EnvFile     = Join-Path $BackendDir '.env'
$EnvExample  = Join-Path $BackendDir '.env.example'
$ReqFile     = Join-Path $BackendDir 'requirements.txt'

# ---------- 输出工具 ----------
function Write-Step($msg) { Write-Host "[步骤] $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "[完成] $msg" -ForegroundColor Green }
function Write-Warn2($msg){ Write-Host "[注意] $msg" -ForegroundColor Yellow }
function Write-Err2($msg) { Write-Host "[失败] $msg" -ForegroundColor Red }

function Get-PortOwner([int]$Port) {
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($conn) { return ($conn | Select-Object -First 1).OwningProcess }
    return 0
}

function Resolve-PythonLauncher {
    # 优先 py -3（Windows 官方启动器），其次 python
    $py = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($py) { return @($py.Source, '-3') }
    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($python) { return @($python.Source) }
    return $null
}

# ---------- 开始 ----------
Write-Host ''
Write-Host '============================================================' -ForegroundColor DarkGray
Write-Host '  知食 NutriMind · AI 智能减脂管理系统 —— 一键启动（开发模式）' -ForegroundColor White
Write-Host '============================================================' -ForegroundColor DarkGray
Write-Host ''

if (-not (Test-Path $BackendDir)) {
    Write-Err2 "未找到后端目录：$BackendDir"
    exit 1
}
if (-not (Test-Path $FrontendDir)) {
    Write-Err2 "未找到前端目录：$FrontendDir"
    exit 1
}

# ---------- 1. 端口占用检查 ----------
Write-Step "检查端口占用（后端 $BackendPort / 前端 $FrontendPort）"
$busy = @()
foreach ($p in @($BackendPort, $FrontendPort)) {
    $owner = Get-PortOwner $p
    if ($owner -ne 0) { $busy += "$p (PID $owner)" }
}
if ($busy.Count -gt 0) {
    Write-Err2 ("以下端口已被占用：" + ($busy -join '、'))
    Write-Host '       请先运行 stop.bat 结束旧进程，或改用其它端口：' -ForegroundColor Yellow
    Write-Host '       start.bat -BackendPort 8001 -FrontendPort 5174' -ForegroundColor Yellow
    exit 1
}
Write-Ok "端口空闲"

# ---------- 2. 后端虚拟环境 ----------
if (-not (Test-Path $VenvPy)) {
    Write-Step '未检测到后端虚拟环境，正在创建 .venv ...'
    if ($DryRun) {
        Write-Warn2 '[DryRun] 将执行：python -m venv .venv'
    } else {
        $launcher = Resolve-PythonLauncher
        if (-not $launcher) {
            Write-Err2 '未找到 Python。请先安装 Python 3.10+ 并勾选「Add to PATH」。'
            exit 1
        }
        $pyExe = $launcher[0]
        $pyArgs = @()
        if ($launcher.Count -gt 1) { $pyArgs = @($launcher[1]) }
        & $pyExe @pyArgs -m venv $VenvDir
        if ($LASTEXITCODE -ne 0) { Write-Err2 '创建虚拟环境失败'; exit 1 }
        Write-Ok '虚拟环境创建完成'
    }
}

if (Test-Path $VenvPy) {
    Write-Step '检查后端依赖 ...'
    $probe = & $VenvPy -c "import fastapi, uvicorn, sqlalchemy, pydantic, jwt, passlib, zhipuai, httpx, cryptography; print('ok')" 2>$null
    $needInstall = -not ($probe -match 'ok')
    if ($needInstall) {
        if ($DryRun) {
            Write-Warn2 '[DryRun] 后端依赖缺失，将执行：pip install -r requirements.txt'
        } else {
            Write-Host '       首次安装依赖，可能需要 1~3 分钟 ...' -ForegroundColor DarkGray
            & $VenvPy -m pip install --upgrade pip --quiet
            & $VenvPy -m pip install -r $ReqFile
            if ($LASTEXITCODE -ne 0) { Write-Err2 '安装后端依赖失败，请检查网络'; exit 1 }
            Write-Ok '后端依赖安装完成'
        }
    } else {
        Write-Ok '后端依赖已就绪'
    }
}

# ---------- 3. .env ----------
if (-not (Test-Path $EnvFile)) {
    if (Test-Path $EnvExample) {
        Copy-Item $EnvExample $EnvFile
        Write-Warn2 "已从 .env.example 生成 backend\.env"
        Write-Warn2 "如需使用 AI 功能，请编辑 backend\.env 填入 ZHIPU_API_KEY（智谱默认使用免费模型）"
    } else {
        Write-Warn2 "未找到 backend\.env 与 .env.example，后端将使用环境变量兜底配置"
    }
}

# ---------- 4. 前端依赖 ----------
$NodeModules = Join-Path $FrontendDir 'node_modules'
if (-not (Test-Path $NodeModules)) {
    Write-Step '未检测到前端依赖，正在执行 npm install ...'
    if ($DryRun) {
        Write-Warn2 '[DryRun] 将执行：npm install'
    } else {
        Push-Location $FrontendDir
        try {
            cmd /c 'npm install'
            if ($LASTEXITCODE -ne 0) { Write-Err2 'npm install 失败，请检查 Node.js 与本机 npm 代理配置'; exit 1 }
            Write-Ok '前端依赖安装完成'
        } finally {
            Pop-Location
        }
    }
} else {
    Write-Ok '前端依赖已就绪'
}

if ($DryRun) {
    Write-Host ''
    Write-Ok '体检完成（DryRun，未启动任何进程）'
    exit 0
}

# ---------- 5. 启动后端 ----------
Write-Step "启动后端（端口 $BackendPort，热重载）"
# 开发模式下不让后端托管前端构建产物，避免 8000 端口出现「上一次的旧构建」
$env:FRONTEND_DIST = Join-Path $Root '__no_dist_in_dev__'

$backendArgs = @('-m', 'uvicorn', 'main:app', '--host', '0.0.0.0', '--port', "$BackendPort", '--reload')
Start-Process -FilePath $VenvPy -ArgumentList $backendArgs -WorkingDirectory $BackendDir | Out-Null
Write-Ok "后端已在新窗口启动： http://localhost:$BackendPort  （接口文档 /docs）"

# ---------- 6. 启动前端 ----------
Write-Step "启动前端（端口 $FrontendPort）"
Start-Process -FilePath 'cmd.exe' -ArgumentList @('/k', 'npm run dev') -WorkingDirectory $FrontendDir | Out-Null
Write-Ok "前端已在新窗口启动： http://localhost:$FrontendPort"

# ---------- 7. 等待就绪并打开浏览器 ----------
Write-Step '等待服务就绪 ...'
$backendReady = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Milliseconds 700
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:$BackendPort/health" -UseBasicParsing -TimeoutSec 2
        if ($r.StatusCode -eq 200) { $backendReady = $true; break }
    } catch { }
}
if ($backendReady) { Write-Ok '后端健康检查通过' } else { Write-Warn2 '后端尚未就绪，请查看后端窗口的报错信息' }

$frontendReady = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Milliseconds 700
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:$FrontendPort/" -UseBasicParsing -TimeoutSec 2
        if ($r.StatusCode -eq 200) { $frontendReady = $true; break }
    } catch { }
}
if ($frontendReady) { Write-Ok '前端就绪' } else { Write-Warn2 '前端尚未就绪，请查看前端窗口的报错信息' }

Write-Host ''
Write-Host '------------------------------------------------------------' -ForegroundColor DarkGray
Write-Host '  启动完成，浏览器访问：' -ForegroundColor White
Write-Host "    前端页面   http://localhost:$FrontendPort" -ForegroundColor Green
Write-Host "    接口文档   http://localhost:$BackendPort/docs" -ForegroundColor Green
Write-Host '  结束服务：双击 stop.bat（或直接关闭两个新窗口）' -ForegroundColor DarkGray
Write-Host '------------------------------------------------------------' -ForegroundColor DarkGray
Write-Host ''

if (-not $NoBrowser -and $frontendReady) { Start-Process "http://localhost:$FrontendPort" | Out-Null }
