<#
.SYNOPSIS
    MediTour 后端本地运维脚本：start / stop / restart / status。

.DESCRIPTION
    把常见步骤收敛成一条命令，并在启动前处理三类常见问题：
    - 端口被占用：先确认占用进程；属于本仓库的服务直接停止，其它进程需要 -Force；
    - 虚拟环境缺失：自动创建 backend/.venv 并安装 requirements.txt；
    - 密钥未设置：自动在 backend/.env 写入随机 MEDITOUR_SECRET_KEY。

.EXAMPLE
    .\scripts\dev_server.ps1 start
    .\scripts\dev_server.ps1 status
    .\scripts\dev_server.ps1 restart
    .\scripts\dev_server.ps1 stop
    .\scripts\dev_server.ps1 start -Port 8001 -Force
#>

param(
    [Parameter(Position = 0)]
    [ValidateSet("start", "stop", "restart", "status")]
    [string]$Action = "status",

    [int]$Port = 8000,

    # 端口被非本服务进程占用时，允许强制结束该进程。
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$BackendDir = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $BackendDir ".venv\Scripts\python.exe"
$VarDir = Join-Path $BackendDir "var"
$PidFile = Join-Path $VarDir "dev_server.pid"
$LogFile = Join-Path $VarDir "dev_server.log"
$ErrorLogFile = Join-Path $VarDir "dev_server.err.log"
$EnvFile = Join-Path $BackendDir ".env"
$HealthUrl = "http://127.0.0.1:$Port/api/v1/health"

function Write-Step {
    param([string]$Message)
    Write-Host "[dev_server] $Message" -ForegroundColor Cyan
}

function Fail {
    param([string]$Message)
    Write-Host "[dev_server] $Message" -ForegroundColor Red
    exit 1
}

function New-Secret {
    $chars = (48..57) + (65..90) + (97..122)
    return -join ($chars | Get-Random -Count 48 | ForEach-Object { [char]$_ })
}

function Ensure-EnvFile {
    if (-not (Test-Path $EnvFile)) {
        $example = Join-Path $BackendDir ".env.example"
        if (Test-Path $example) {
            Copy-Item $example $EnvFile
            Write-Step "已从 .env.example 创建 backend/.env"
        } else {
            Set-Content -Path $EnvFile -Value "" -Encoding UTF8
        }
    }

    $content = Get-Content $EnvFile -Raw
    if ($null -eq $content) { $content = "" }

    if ($content -match "(?m)^\s*MEDITOUR_SECRET_KEY\s*=\s*(\S+)\s*$") {
        if ($Matches[1] -and $Matches[1] -ne "replace-with-a-long-random-string") {
            return
        }
        $key = New-Secret
        $content = [regex]::Replace(
            $content,
            "(?m)^\s*MEDITOUR_SECRET_KEY\s*=.*$",
            "MEDITOUR_SECRET_KEY=$key"
        )
        Set-Content -Path $EnvFile -Value $content -NoNewline -Encoding UTF8
        Write-Step "已为 backend/.env 生成随机 MEDITOUR_SECRET_KEY"
        return
    }

    if ($content -match "(?m)^\s*SECRET_KEY\s*=\s*(\S+)\s*$" -and $Matches[1]) {
        return
    }

    Add-Content -Path $EnvFile -Value "MEDITOUR_SECRET_KEY=$(New-Secret)" -Encoding UTF8
    Write-Step "已向 backend/.env 追加随机 MEDITOUR_SECRET_KEY"
}

function Ensure-Venv {
    if (Test-Path $VenvPython) { return }

    $systemPython = Get-Command python -ErrorAction SilentlyContinue
    if ($null -eq $systemPython) {
        Fail "未找到 python，请先安装 Python 3.12 并加入 PATH。"
    }

    Write-Step "未找到 .venv，正在创建虚拟环境（首次执行会安装依赖）..."
    & python -m venv (Join-Path $BackendDir ".venv")
    if ($LASTEXITCODE -ne 0) { Fail "创建虚拟环境失败。" }

    & $VenvPython -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { Fail "升级 pip 失败。" }

    & $VenvPython -m pip install -r (Join-Path $BackendDir "requirements.txt")
    if ($LASTEXITCODE -ne 0) { Fail "安装 requirements.txt 失败。" }

    Write-Step "虚拟环境准备完成。"
}

function Get-PortOwner {
    param([int]$TargetPort)
    try {
        $connection = Get-NetTCPConnection -LocalPort $TargetPort -State Listen -ErrorAction Stop |
            Select-Object -First 1
    } catch {
        return $null
    }
    if ($null -eq $connection) { return $null }
    return Get-Process -Id $connection.OwningProcess -ErrorAction SilentlyContinue
}

function Get-RunningPid {
    if (-not (Test-Path $PidFile)) { return $null }
    $raw = Get-Content $PidFile -Raw -ErrorAction SilentlyContinue
    if ($null -eq $raw) { return $null }
    $raw = $raw.Trim()
    if (-not $raw) { return $null }
    $process = Get-Process -Id ([int]$raw) -ErrorAction SilentlyContinue
    if ($null -eq $process) {
        Remove-Item $PidFile -ErrorAction SilentlyContinue
        return $null
    }
    return $process
}

function Wait-PortFree {
    param([int]$TargetPort, [int]$Seconds = 10)
    for ($i = 0; $i -lt ($Seconds * 2); $i++) {
        if ($null -eq (Get-PortOwner -TargetPort $TargetPort)) { return $true }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

function Wait-Healthy {
    param([int]$Seconds = 30)
    for ($i = 0; $i -lt ($Seconds * 2); $i++) {
        try {
            $response = Invoke-WebRequest -Uri $HealthUrl -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200) { return $true }
        } catch {
            # 服务尚未就绪，继续等待。
        }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

function Show-Health {
    try {
        $response = Invoke-RestMethod -Uri $HealthUrl -TimeoutSec 3
        Write-Host "[dev_server] 健康检查: $($response | ConvertTo-Json -Compress)"
    } catch {
        Write-Host "[dev_server] 健康检查失败: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

function Start-Server {
    $running = Get-RunningPid
    if ($null -ne $running) {
        Write-Step "服务已运行（PID $($running.Id)），端口 $Port。"
        Show-Health
        return
    }

    $owner = Get-PortOwner -TargetPort $Port
    if ($null -ne $owner) {
        if (-not $Force) {
            Fail "端口 $Port 已被 $($owner.ProcessName)（PID $($owner.Id)）占用。确认可结束后用 -Force 重试。"
        }
        Write-Step "端口 $Port 被 $($owner.ProcessName)（PID $($owner.Id)）占用，按 -Force 结束该进程..."
        Stop-Process -Id $owner.Id -Force
        if (-not (Wait-PortFree -TargetPort $Port)) {
            Fail "端口 $Port 仍被占用，请手动检查。"
        }
    }

    Ensure-EnvFile
    Ensure-Venv

    if (-not (Test-Path $VarDir)) {
        New-Item -ItemType Directory -Path $VarDir | Out-Null
    }

    Write-Step "启动 API：port=$Port，日志见 backend/var/dev_server.log"
    $process = Start-Process -FilePath $VenvPython `
        -ArgumentList @("-m", "uvicorn", "app.main:app", "--port", "$Port") `
        -WorkingDirectory $BackendDir `
        -RedirectStandardOutput $LogFile `
        -RedirectStandardError $ErrorLogFile `
        -PassThru

    Set-Content -Path $PidFile -Value $process.Id -Encoding ASCII

    if (Wait-Healthy) {
        Write-Step "启动成功（PID $($process.Id)）。文档: http://127.0.0.1:$Port/docs"
        Show-Health
    } else {
        Write-Host "[dev_server] 启动后 30 秒内健康检查未通过，请查看 $LogFile 与 $ErrorLogFile。" -ForegroundColor Yellow
        Get-Content $ErrorLogFile -Tail 20 -ErrorAction SilentlyContinue
        exit 1
    }
}

function Stop-Server {
    $stopped = $false

    $running = Get-RunningPid
    if ($null -ne $running) {
        Write-Step "停止服务（PID $($running.Id)）..."
        Stop-Process -Id $running.Id -Force
        $stopped = $true
    }
    Remove-Item $PidFile -ErrorAction SilentlyContinue

    $owner = Get-PortOwner -TargetPort $Port
    if ($null -ne $owner) {
        if ($Force) {
            Write-Step "端口 $Port 仍被 $($owner.ProcessName)（PID $($owner.Id)）占用，按 -Force 结束。"
            Stop-Process -Id $owner.Id -Force
            $stopped = $true
        } else {
            Fail "端口 $Port 被 $($owner.ProcessName)（PID $($owner.Id)）占用，未结束。确认后用 -Force 重试。"
        }
    }

    if ($stopped) {
        if (Wait-PortFree -TargetPort $Port) {
            Write-Step "服务已停止，端口 $Port 已释放。"
        } else {
            Write-Step "进程已结束，但端口 $Port 尚未释放，请稍后复查。"
        }
    } else {
        Write-Step "没有发现正在运行的服务。"
    }
}

function Show-Status {
    $running = Get-RunningPid
    $owner = Get-PortOwner -TargetPort $Port

    if ($null -ne $running) {
        Write-Step "运行中：PID $($running.Id)，端口 $Port。"
    } elseif ($null -ne $owner) {
        Write-Host "[dev_server] 本服务未登记 PID，但端口 $Port 被 $($owner.ProcessName)（PID $($owner.Id)）占用。" -ForegroundColor Yellow
    } else {
        Write-Step "未运行（端口 $Port 空闲）。"
    }

    if ($null -ne (Get-PortOwner -TargetPort $Port)) {
        Show-Health
    }

    if (Test-Path $LogFile) {
        Write-Host "[dev_server] 最近日志（$LogFile）："
        Get-Content $LogFile -Tail 5 -ErrorAction SilentlyContinue
    }
}

switch ($Action) {
    "start" { Start-Server }
    "stop" { Stop-Server }
    "restart" {
        Stop-Server
        Start-Server
    }
    "status" { Show-Status }
    default { Fail "未知操作：$Action" }
}
