# 数据打包脚本（Windows PowerShell）
# 用于打包本地数据文件以便迁移到 Zeabur

$ErrorActionPreference = "Stop"

Write-Host "开始打包数据文件..." -ForegroundColor Green

# 切换到项目根目录
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

# 创建临时目录
$backupDir = "data_backup"
if (Test-Path $backupDir) {
    Remove-Item -Recurse -Force $backupDir
}
New-Item -ItemType Directory -Path $backupDir | Out-Null

# 复制数据文件
Write-Host "复制 system.db..." -ForegroundColor Yellow
if (Test-Path "system.db") {
    Copy-Item "system.db" "$backupDir\system.db"
    Write-Host "  ✅ system.db 已复制" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  system.db 不存在" -ForegroundColor Yellow
}

Write-Host "复制 data/ 目录..." -ForegroundColor Yellow
if (Test-Path "data") {
    New-Item -ItemType Directory -Path "$backupDir\data" | Out-Null
    Copy-Item "data\*" "$backupDir\data\" -Recurse -Force
    Write-Host "  ✅ data/ 目录已复制" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  data/ 目录不存在" -ForegroundColor Yellow
}

# 打包
$zipFile = "data_backup.zip"
if (Test-Path $zipFile) {
    Remove-Item -Force $zipFile
}

Write-Host "创建压缩包..." -ForegroundColor Yellow
Compress-Archive -Path $backupDir -DestinationPath $zipFile -Force

# 显示文件大小
$zipSize = (Get-Item $zipFile).Length / 1MB
Write-Host "`n✅ 数据打包完成！" -ForegroundColor Green
Write-Host "文件: $zipFile" -ForegroundColor Cyan
Write-Host "大小: $([math]::Round($zipSize, 2)) MB" -ForegroundColor Cyan
Write-Host "`n下一步：" -ForegroundColor Yellow
Write-Host "1. 将 $zipFile 上传到可访问的位置（GitHub Release / 云存储）" -ForegroundColor White
Write-Host "2. 在 Zeabur 中设置 DATA_BACKUP_URL 环境变量指向下载链接" -ForegroundColor White
Write-Host "3. 或者在 Zeabur Shell 中手动导入数据" -ForegroundColor White

# 清理临时目录
Remove-Item -Recurse -Force $backupDir

