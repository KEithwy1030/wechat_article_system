#!/bin/bash
# 数据导入脚本
# 用于在 Zeabur 容器中导入本地数据

set -e

echo "开始导入数据..."

# 数据文件下载链接（需要替换为实际链接）
DATA_URL="${DATA_BACKUP_URL:-}"

if [ -z "$DATA_URL" ]; then
    echo "错误: 请设置 DATA_BACKUP_URL 环境变量"
    exit 1
fi

# 下载数据文件
echo "下载数据文件..."
cd /app
wget -q "$DATA_URL" -O data_backup.zip

# 解压
echo "解压数据文件..."
unzip -q data_backup.zip -d data_backup

# 移动文件
echo "移动数据文件..."
if [ -f "data_backup/system.db" ]; then
    cp data_backup/system.db /app/system.db
    echo "✅ system.db 已导入"
fi

if [ -d "data_backup/data" ]; then
    mkdir -p /app/data
    cp data_backup/data/* /app/data/ 2>/dev/null || true
    echo "✅ data/ 目录文件已导入"
fi

# 设置权限
chmod 644 /app/system.db 2>/dev/null || true
chmod 644 /app/data/* 2>/dev/null || true

# 清理
rm -rf data_backup data_backup.zip

echo "✅ 数据导入完成！"

