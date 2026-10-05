<#
  知食 NutriMind · 一键部署（生产模式 / 单端口）

  流程：
    1. 体检环境（Python / Node / 依赖 / .env）
    2. 生成或校正 backend\.env 的 JWT_SECRET（避免每次重启 Token 失效）
    3. 构建前端：npm run build  →  frontend\dist
    4. 启动后端（无 --reload）并由其**统一托管前端构建产物**
    5. 单端口对外：http://localhost:8000

  相比开发模式的优势：一个进程、一个端口、无跨域，适合演示与交付。

  用法：
    powershell -ExecutionPolicy Bypass -File scripts\deploy.ps1
    powershell -ExecutionPolicy Bypass -File scripts\deploy.ps1 -Port 8080
    powershell -ExecutionPolicy Bypass -File scripts\deploy.ps1 -SkipBuild   # 跳过构建直接启动
#>
[CmdletBinding()]
param(
    [int]$Port = 8000,
    [switch]$SkipBuild,
    [switch]$NoBrowser,
    [switch]$Foreground
)

$ErrorActionPreference = 'Stop'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }

# ---------- 路径 ----------
$Root        = Split-Path -Parent $PSScriptRoot
$BackendDir  = Join-Path $Root 'backend'
$FrontendDir = Join-Path $Root 'frontend'
$VenvPy      = Join-Path $BackendDir '.venv\Scripts\python.exe'
$EnvFile     = Join-Path $BackendDir '.env'
$EnvExample  = Join-Path $BackendDir '.env.example'
$ReqFile     = Join-Path $BackendDir 'requirements.txt'
$DistDir     = Join-Path $FrontendDir 'dist'
$DistIndex   = Join-Path $DistDir 'index.html'

# ---------- 输出工具 ----------
function Write-Step($msg) { Write-Host "[步骤] $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "[完成] $msg" -ForegroundColor Green }
function Write-Warn2($msg){ Write-Host "[注意] $msg" -ForegroundColor Yellow }
function Write-Err2($msg) { Write-Host "[失败] $msg" -ForegroundColor Red }

function Resolve-PythonLauncher {
    $py = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($py) { return @($py.Source, '-3') }
    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($python) { return @($python.Source) }
    return $null
}

function New-RandomHex([int]$ByteCount) {
    $bytes = New-Object byte[] $ByteCount
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    $rng.GetBytes($bytes)
    $rng.Dispose()
    return (($bytes | ForEach-Object { $_.ToString('x2') }) -join '')
}

function Write-Utf8NoBom([string]$Path, [string]$Text) {
    $enc = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Text, $enc)
}

Write-Host ''
Write-Host '============================================================' -ForegroundColor DarkGray
Write-Host '  知食 NutriMind · AI 智能减脂管理系统 —— 一键部署（单端口）' -ForegroundColor White
Write-Host '============================================================' -ForegroundColor DarkGray
Write-Host ''

if (-not (Test-Path $BackendDir))  { Write-Err2 "未找到后端目录：$BackendDir";  exit 1 }
if (-not (Test-Path $FrontendDir)) { Write-Err2 "未找到前端目录：$FrontendDir"; exit 1 }

# ---------- 1. 端口检查 ----------
Write-Step "检查端口 $Port 是否空闲"
$conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($conn) {
    $owner = ($conn | Select-Object -First 1).OwningProcess
    Write-Err2 "端口 $Port 已被 PID $owner 占用，请先运行 stop.bat 或改用 -Port 指定其它端口"
    exit 1
}
Write-Ok "端口 $Port 空闲"

# ---------- 2. 后端依赖 ----------
if (-not (Test-Path $VenvPy)) {
    Write-Step '创建后端虚拟环境 .venv ...'
    $launcher = Resolve-PythonLauncher
    if (-not $launcher) {
        Write-Err2 '未找到 Python。请先安装 Python 3.10+ 并勾选「Add to PATH」。'
        exit 1
    }
    $pyExe = $launcher[0]
    $pyArgs = @()
    if ($launcher.Count -gt 1) { $pyArgs = @($launcher[1]) }
    & $pyExe @pyArgs -m venv (Join-Path $BackendDir '.venv')
    if ($LASTEXITCODE -ne 0) { Write-Err2 '创建虚拟环境失败'; exit 1 }
    Write-Ok '虚拟环境创建完成'
}

Write-Step '检查后端依赖 ...'
$probe = & $VenvPy -c "import fastapi, uvicorn, sqlalchemy, pydantic, jwt, passlib, zhipuai, httpx, cryptography; print('ok')" 2>$null
if ($probe -notmatch 'ok') {
    Write-Host '       正在安装依赖，可能需要 1~3 分钟 ...' -ForegroundColor DarkGray
    & $VenvPy -m pip install --upgrade pip --quiet
    & $VenvPy -m pip install -r $ReqFile
    if ($LASTEXITCODE -ne 0) { Write-Err2 '安装后端依赖失败，请检查网络'; exit 1 }
    Write-Ok '后端依赖安装完成'
} else {
    Write-Ok '后端依赖已就绪'
}

# ---------- 3. .env 与 JWT_SECRET ----------
if (-not (Test-Path $EnvFile)) {
    if (Test-Path $EnvExample) {
        Copy-Item $EnvExample $EnvFile
        Write-Warn2 '已从 .env.example 生成 backend\.env'
    } else {
        Write-Err2 '缺少 backend\.env 与 .env.example，无法继续'
        exit 1
    }
}

Write-Step '校正 JWT_SECRET（保证 Token 跨重启有效）'
$envText = [System.IO.File]::ReadAllText($EnvFile)
$match = [regex]::Match($envText, '(?m)^\s*JWT_SECRET\s*=\s*(.*)$')
$current = ''
if ($match.Success) { $current = $match.Groups[1].Value.Trim() }

$weak = ($current -eq '') -or ($current -eq 'change-me-secret') -or ($current.Length -lt 32)
if ($weak) {
    $newSecret = New-RandomHex 32
    if ($match.Success) {
        $envText = $envText.Substring(0, $match.Index) + "JWT_SECRET=$newSecret" + $envText.Substring($match.Index + $match.Length)
    } else {
        $envText = $envText.TrimEnd() + "`r`nJWT_SECRET=$newSecret`r`n"
    }
    Write-Utf8NoBom $EnvFile $envText
    Write-Ok '已生成 64 位随机 JWT_SECRET 并写入 backend\.env'
} else {
    Write-Ok 'JWT_SECRET 已就绪（长度 >= 32）'
}

# 检查 AI Key
$envText = [System.IO.File]::ReadAllText($EnvFile)
$keyMatch = [regex]::Match($envText, '(?m)^\s*ZHIPU_API_KEY\s*=\s*(.*)$')
$keyVal = ''
if ($keyMatch.Success) { $keyVal = $keyMatch.Groups[1].Value.Trim() }
if ($keyVal -eq '') {
    Write-Warn2 '未配置 ZHIPU_API_KEY：AI 相关功能不可用（其余功能正常）。可在「我的 → 大模型配置」中图形化配置。'
} else {
    Write-Ok '已检测到 ZHIPU_API_KEY（智谱默认使用永久免费模型 glm-4-flash / glm-4v-flash）'
}

# ---------- 4. 前端依赖与构建 ----------
if (-not (Test-Path (Join-Path $FrontendDir 'node_modules'))) {
    Write-Step '安装前端依赖（npm install）...'
    Push-Location $FrontendDir
    try {
        cmd /c 'npm install'
        if ($LASTEXITCODE -ne 0) { Write-Err2 'npm install 失败，请检查 Node.js 与本机 npm 代理配置'; exit 1 }
    } finally { Pop-Location }
    Write-Ok '前端依赖安装完成'
} else {
    Write-Ok '前端依赖已就绪'
}

if ($SkipBuild) {
    Write-Warn2 '已跳过构建（-SkipBuild），将直接使用现有 frontend\dist'
} else {
    Write-Step '构建前端（npm run build）...'
    Push-Location $FrontendDir
    try {
        cmd /c 'npm run build'
        if ($LASTEXITCODE -ne 0) { Write-Err2 '前端构建失败，请查看上方报错'; exit 1 }
    } finally { Pop-Location }
    Write-Ok '前端构建完成 → frontend\dist'
}

if (-not (Test-Path $DistIndex)) {
    Write-Err2 "未找到构建产物：$DistIndex（请去掉 -SkipBuild 重新构建）"
    exit 1
}
$distSize = [math]::Round((Get-ChildItem $DistDir -Recurse -File | Measure-Object -Property Length -Sum).Sum / 1MB, 2)
Write-Ok "构建产物就绪（$distSize MB）"

# ---------- 5. 启动服务 ----------
Write-Step "启动后端并托管前端（端口 $Port，单进程）"
$env:FRONTEND_DIST = $DistDir
$env:PORT = "$Port"
$env:HOST = '0.0.0.0'

$backendArgs = @('-m', 'uvicorn', 'main:app', '--host', '0.0.0.0', '--port', "$Port")

if ($Foreground) {
    Write-Host '       前台运行，按 Ctrl+C 停止' -ForegroundColor DarkGray
    Write-Host ''
    Push-Location $BackendDir
    try { & $VenvPy @backendArgs } finally { Pop-Location }
    exit 0
}

Start-Process -FilePath $VenvPy -ArgumentList $backendArgs -WorkingDirectory $BackendDir | Out-Null
Write-Ok '服务已在新窗口启动'

# ---------- 6. 就绪探测 ----------
Write-Step '等待服务就绪 ...'
$ready = $false
for ($i = 0; $i -lt 40; $i++) {
    Start-Sleep -Milliseconds 700
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/health" -UseBasicParsing -TimeoutSec 2
        if ($r.StatusCode -eq 200) { $ready = $true; break }
    } catch { }
}

Write-Host ''
Write-Host '------------------------------------------------------------' -ForegroundColor DarkGray
if ($ready) {
    Write-Host '  部署完成，应用地址：' -ForegroundColor White
    Write-Host "    http://localhost:$Port" -ForegroundColor Green
    Write-Host "    接口文档  http://localhost:$Port/docs" -ForegroundColor DarkGray

    # 局域网访问地址（便于手机同网段访问）
    try {
        $lanIps = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
            Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' -and $_.PrefixOrigin -ne 'WellKnown' } |
            Select-Object -ExpandProperty IPAddress -Unique
        if ($lanIps) {
            Write-Host '    局域网访问（手机同 WiFi 可用）：' -ForegroundColor DarkGray
            foreach ($ip in $lanIps) { Write-Host "      http://${ip}:$Port" -ForegroundColor DarkGray }
        }
    } catch { }

    Write-Host '  结束服务：双击 stop.bat（或关闭服务窗口）' -ForegroundColor DarkGray
} else {
    Write-Warn2 '服务未在预期时间内就绪，请查看新窗口中的报错信息'
}
Write-Host '------------------------------------------------------------' -ForegroundColor DarkGray
Write-Host ''

if (-not $NoBrowser -and $ready) { Start-Process "http://localhost:$Port" | Out-Null }
