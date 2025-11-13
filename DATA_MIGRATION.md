# 数据迁移指南

## 📊 本地数据文件位置

你的本地数据文件存储在以下位置：

### 主要数据库文件
- **`system.db`** (200KB) - 存储赛程数据（`lottery_matches` 表）
- **`data/prediction_stats.db`** (28KB) - 预测统计
- **`data/quick_predictions.db`** (16KB) - 快速预测数据
- **`data/schedule_display.db`** (32KB) - 赛程显示数据
- **`data/history_articles.json`** - 历史文章
- **`data/history.json`** - 历史记录

## 🔍 为什么 Zeabur 上没有数据？

1. **`.gitignore` 排除了数据文件**：所有 `.db` 文件和 `data/` 目录都被排除在 Git 之外
2. **Zeabur 从 GitHub 构建**：容器是全新的，没有本地数据
3. **数据需要手动迁移**：需要将本地数据文件上传到 Zeabur

## 🚀 迁移方案（推荐顺序）

### ⚡ 方案 1：最简单 - 使用 Zeabur Shell 直接上传（推荐）

**步骤：**

1. **在本地打包数据**
   ```powershell
   cd E:\CursorData\WechatBOT\AIWeChatauto
   .\scripts\package_data.ps1
   ```
   这会生成 `data_backup.zip` 文件

2. **在 Zeabur 中打开 Shell/Console**
   - 进入你的 Zeabur 项目
   - 找到 "Shell" 或 "Console" 功能（通常在服务详情页）

3. **上传并解压数据**
   ```bash
   # 在 Zeabur Shell 中执行
   cd /app
   
   # 方法 A：如果 Zeabur 支持文件上传，直接上传 data_backup.zip
   # 然后执行：
   unzip data_backup.zip
   mv data_backup/system.db /app/
   mv data_backup/data/* /app/data/
   chmod 644 /app/system.db /app/data/*
   rm -rf data_backup data_backup.zip
   ```

4. **重启服务**
   - 在 Zeabur 控制台重启服务

### 📦 方案 2：通过云存储链接导入

1. **打包数据**（同上）
2. **上传到云存储**（Google Drive / OneDrive / 阿里云OSS）
3. **获取公开下载链接**
4. **在 Zeabur Shell 中下载并导入**
   ```bash
   cd /app
   wget "你的下载链接" -O data_backup.zip
   unzip data_backup.zip
   mv data_backup/system.db /app/
   mv data_backup/data/* /app/data/
   chmod 644 /app/system.db /app/data/*
   rm -rf data_backup data_backup.zip
   ```

### 🔄 方案 3：重新收集数据（如果数据不重要）

如果本地数据不是特别重要，可以：
1. 在 Zeabur 部署的应用中点击 "赛程更新"
2. 系统会自动重新收集赛程数据
3. 数据会保存到容器的持久化存储中

## 📝 详细迁移步骤

### 步骤 1：准备数据文件

在本地执行：
```powershell
cd E:\CursorData\WechatBOT\AIWeChatauto
# 创建数据备份目录
mkdir -p data_backup
# 复制数据文件
copy system.db data_backup\
copy data\*.db data_backup\
copy data\*.json data_backup\
# 打包
Compress-Archive -Path data_backup -DestinationPath data_backup.zip
```

### 步骤 2：上传到可访问位置

选项 A：上传到 GitHub Release
- 在 GitHub 仓库创建 Release
- 上传 `data_backup.zip`

选项 B：使用云存储
- 上传到 Google Drive / OneDrive / 阿里云OSS
- 获取公开下载链接

### 步骤 3：在 Zeabur 中导入

1. **通过 Zeabur Shell 访问容器**
   ```bash
   # 在 Zeabur 项目页面找到 Shell/Console 功能
   ```

2. **下载并解压数据**
   ```bash
   cd /app
   # 下载数据文件（替换为实际链接）
   wget https://your-download-link/data_backup.zip
   unzip data_backup.zip
   
   # 移动文件到正确位置
   mv data_backup/system.db /app/
   mv data_backup/*.db /app/data/
   mv data_backup/*.json /app/data/
   
   # 设置权限
   chmod 644 /app/system.db
   chmod 644 /app/data/*
   ```

3. **重启服务**
   - 在 Zeabur 控制台重启服务

## ⚠️ 注意事项

1. **数据备份**：迁移前先备份本地数据
2. **权限问题**：确保容器有读写权限
3. **路径一致性**：确保 Zeabur 中的路径与代码中的路径一致
4. **数据库兼容性**：SQLite 数据库在不同系统间通常兼容

## 🔄 验证迁移

迁移后检查：
1. 访问 Web 界面，查看是否有赛程数据
2. 检查命中率统计是否显示
3. 查看容器日志确认数据库加载正常

