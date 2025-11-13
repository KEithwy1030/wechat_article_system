# Docker 构建脚本（PowerShell）

Write-Host "开始构建 Docker 镜像..." -ForegroundColor Green

# 检查 Docker 是否运行
$dockerRunning = docker ps 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "错误: Docker 未运行，请先启动 Docker Desktop" -ForegroundColor Red
    exit 1
}

# 尝试拉取 Python 3.11 镜像
Write-Host "尝试拉取 Python 3.11-slim 镜像..." -ForegroundColor Yellow
docker pull python:3.11-slim 2>&1 | Out-Null

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Python 3.11-slim 镜像拉取成功" -ForegroundColor Green
    $pythonImage = "python:3.11-slim"
} else {
    Write-Host "✗ Python 3.11-slim 拉取失败，尝试使用 Python 3.9-slim..." -ForegroundColor Yellow
    docker pull python:3.9-slim 2>&1 | Out-Null
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Python 3.9-slim 镜像拉取成功" -ForegroundColor Green
        $pythonImage = "python:3.9-slim"
        # 临时修改 Dockerfile
        $dockerfileContent = Get-Content Dockerfile -Raw
        $dockerfileContent = $dockerfileContent -replace "FROM python:3.11-slim", "FROM python:3.9-slim"
        Set-Content Dockerfile -Value $dockerfileContent
        Write-Host "已临时修改 Dockerfile 使用 Python 3.9" -ForegroundColor Yellow
    } else {
        Write-Host "✗ 无法拉取 Python 镜像，请检查网络连接或配置镜像加速器" -ForegroundColor Red
        Write-Host "参考: DOCKER_BUILD_TROUBLESHOOTING.md" -ForegroundColor Yellow
        exit 1
    }
}

# 构建镜像
Write-Host "`n开始构建 wechatbot 镜像..." -ForegroundColor Green
docker build -t wechatbot:latest .

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✓ 镜像构建成功！" -ForegroundColor Green
    Write-Host "`n下一步：" -ForegroundColor Cyan
    Write-Host "  1. 启动服务: docker-compose up -d" -ForegroundColor White
    Write-Host "  2. 查看日志: docker-compose logs -f" -ForegroundColor White
    Write-Host "  3. 访问服务: http://localhost:8001" -ForegroundColor White
} else {
    Write-Host "`n✗ 镜像构建失败，请查看错误信息" -ForegroundColor Red
    exit 1
}

