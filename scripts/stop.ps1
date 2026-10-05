<#
  知食 NutriMind · 一键停止服务

  结束由 start.ps1 / deploy.ps1 拉起的进程：
    - 监听指定端口的进程
    - 后端 uvicorn（含 --reload 的父进程，避免被自动拉起）
    - 前端 vite（node 进程）

  用法：
    powershell -ExecutionPolicy Bypass -File scripts\stop.ps1
    powershell -ExecutionPolicy Bypass -File scripts\stop.ps1 -Ports 8000,5173,4173
#>
[CmdletBinding()]
param(
    [int[]]$Ports = @(8000, 5173, 4173)
)

$ErrorActionPreference = 'Continue'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }

function Write-Step($msg) { Write-Host "[步骤] $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "[完成] $msg" -ForegroundColor Green }
function Write-Warn2($msg){ Write-Host "[注意] $msg" -ForegroundColor Yellow }

Write-Host ''
Write-Host '============================================================' -ForegroundColor DarkGray
Write-Host '  知食 NutriMind · 一键停止服务' -ForegroundColor White
Write-Host '============================================================' -ForegroundColor DarkGray
Write-Host ''

$targets = New-Object System.Collections.Generic.List[int]

# 1) 监听目标端口的进程
Write-Step "查找监听端口的进程：$($Ports -join '、')"
foreach ($p in $Ports) {
    $conns = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
    foreach ($c in $conns) {
        if ($c.OwningProcess -gt 0) {
            Write-Host "       端口 $p ← PID $($c.OwningProcess)" -ForegroundColor DarkGray
            $targets.Add([int]$c.OwningProcess)
        }
    }
}

# 2) 后端 uvicorn（含 reloader 父进程）
Write-Step '查找后端 uvicorn 进程'
$uvicorns = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -and $_.CommandLine -like '*uvicorn*main:app*' }
foreach ($proc in $uvicorns) {
    Write-Host "       uvicorn ← PID $($proc.ProcessId)" -ForegroundColor DarkGray
    $targets.Add([int]$proc.ProcessId)
}

# 3) 前端 vite（node 进程）
Write-Step '查找前端 vite 进程'
$vites = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -eq 'node.exe' -and $_.CommandLine -and $_.CommandLine -like '*vite*' }
foreach ($proc in $vites) {
    Write-Host "       vite ← PID $($proc.ProcessId)" -ForegroundColor DarkGray
    $targets.Add([int]$proc.ProcessId)
}

$unique = $targets | Sort-Object -Unique | Where-Object { $_ -and $_ -ne $PID }

if (-not $unique -or $unique.Count -eq 0) {
    Write-Warn2 '未发现正在运行的服务（可能已经停止）'
    Write-Host ''
    exit 0
}

Write-Step ("准备结束 " + $unique.Count + " 个进程 ...")
$killed = 0
foreach ($id in $unique) {
    try {
        Stop-Process -Id $id -Force -ErrorAction Stop
        Write-Host "       已结束 PID $id" -ForegroundColor DarkGray
        $killed++
    } catch {
        Write-Warn2 "PID $id 结束失败（可能已退出或权限不足）：$($_.Exception.Message)"
    }
}

Start-Sleep -Seconds 2

# 复核
$stillBusy = @()
foreach ($p in $Ports) {
    $conns = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
    if ($conns) { $stillBusy += $p }
}

Write-Host ''
if ($stillBusy.Count -eq 0) {
    Write-Ok "已停止 $killed 个进程，端口 $($Ports -join '、') 均已释放"
} else {
    Write-Warn2 ("以下端口仍被占用：" + ($stillBusy -join '、') + "，可尝试以管理员身份再运行一次")
}
Write-Host ''
