<#
.SYNOPSIS
    MediTour 备份的计划任务入口：调用 backup_db.py，把输出追加到 var/logs/backup.log。

.EXAMPLE
    powershell.exe -NoProfile -ExecutionPolicy Bypass `
      -File I:\meditour_app\backend\scripts\run_backup_task.ps1 `
      -OutputDir I:\meditour_app\backend\var\backups

.NOTES
    - 退出码原样透传：备份或保留清理失败时计划任务会显示为非零。
    - 默认按天保留 7 份、按周保留 4 份（更早的周各留最新一份，最新一份永不删除）。
    - 计划任务以运行该任务的 Windows 账户执行，该账户必须对输出目录有写权限。
#>
param(
    [string]$OutputDir = "",
    [int]$DailyKeep = 7,
    [int]$WeeklyKeep = 4
)

$ErrorActionPreference = "Stop"

$Backend = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Backend ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $Python = "python"
}

$LogDir = Join-Path $Backend "var\logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Log = Join-Path $LogDir "backup.log"

$arguments = @(
    (Join-Path $Backend "scripts\backup_db.py"),
    "--daily-keep", "$DailyKeep",
    "--weekly-keep", "$WeeklyKeep"
)
if ($OutputDir) {
    $arguments += @("--output-dir", $OutputDir)
}

$started = Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz"
"[${started}] backup start daily=$DailyKeep weekly=$WeeklyKeep" |
    Out-File -FilePath $Log -Append -Encoding utf8

& $Python @arguments 2>&1 | Out-File -FilePath $Log -Append -Encoding utf8
$code = $LASTEXITCODE

$finished = Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz"
"[${finished}] backup exit=$code" | Out-File -FilePath $Log -Append -Encoding utf8
exit $code
