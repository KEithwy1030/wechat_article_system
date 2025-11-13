# Docker 生产环境部署指南

## 📋 端口信息

- **应用端口**: `8001`
- **Zeabur 部署**: Zeabur 会自动设置 `PORT` 环境变量，应用会自动适配

## 🚀 本地测试 Docker 环境

### 1. 准备环境变量

复制 `env.example` 为 `.env` 并填入实际值：

```bash
cp env.example .env
# 编辑 .env 文件，填入你的 API Keys
```

### 2. 构建并启动容器

```bash
# 构建镜像
docker-compose build

# 启动容器
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止容器
docker-compose down
```

### 3. 访问应用

- **本地访问**: http://localhost:8001
- **容器内访问**: http://0.0.0.0:8001

### 4. 检查容器状态

```bash
# 查看运行状态
docker-compose ps

# 进入容器
docker-compose exec wechatbot bash

# 查看资源使用
docker stats wechatbot-app
```

## 🌐 部署到 Zeabur

### 1. 准备步骤

1. 确保代码已推送到 Git 仓库（GitHub/GitLab）
2. 在 Zeabur 上创建新项目
3. 连接你的 Git 仓库

### 2. 配置环境变量

在 Zeabur 项目设置中添加以下环境变量：

```
GEMINI_API_KEY=your_gemini_api_key
DEEPSEEK_API_KEY=your_deepseek_api_key
DASHSCOPE_API_KEY=your_dashscope_api_key
ZHIPU_API_KEY=your_zhipu_api_key
WECHAT_APPID=your_wechat_appid
WECHAT_APPSECRET=your_wechat_appsecret
```

**注意**: `PORT` 环境变量由 Zeabur 自动设置，无需手动配置。

### 3. 配置构建和部署

- **Dockerfile 路径**: `AIWeChatauto/Dockerfile`
- **工作目录**: `AIWeChatauto/`
- **端口**: Zeabur 会自动检测（应用会从 `PORT` 环境变量读取）

### 4. 数据持久化（重要！）

**必须配置持久化存储，否则容器重启会丢失数据！**

在 Zeabur 项目设置中：
1. 进入 **Storage/Volumes** 或 **持久化存储** 设置
2. 创建持久化卷并挂载到：
   - `/app` → 存储 `system.db`
   - `/app/data` → 存储其他数据库文件（`prediction_stats.db` 等）
3. 确保数据在容器重启后不丢失

**为什么重要**：
- SQLite 数据库文件存储在容器文件系统中
- 如果不配置持久化，容器重启/重建会丢失所有数据
- 配置后数据会保存在持久化卷中

## 🔍 故障排查

### Gunicorn 启动失败

如果 gunicorn 启动失败，检查容器日志：

```bash
docker-compose logs wechatbot
```

常见问题：
- 模块导入错误：检查 `app_new.py` 中的导入
- 端口冲突：确保端口未被占用
- 环境变量缺失：检查 `.env` 文件或环境变量配置

### 应用无法访问

1. 检查容器是否运行：`docker-compose ps`
2. 检查端口映射：确保 `8001:8001` 正确
3. 查看应用日志：`docker-compose logs -f wechatbot`

### 环境变量未生效

1. 检查 `.env` 文件是否存在且格式正确
2. 重启容器：`docker-compose restart`
3. 在容器内检查：`docker-compose exec wechatbot env`

## 📊 性能优化

当前配置：
- **Workers**: 2
- **Threads**: 4 per worker
- **Timeout**: 120 秒
- **内存限制**: 2GB
- **CPU 限制**: 1.0 core

可根据实际需求调整 `Dockerfile` 中的 gunicorn 参数。

## ✅ 测试清单

部署前请确认：
- [ ] Docker 镜像构建成功
- [ ] 容器启动正常
- [ ] Web 界面可访问
- [ ] API 接口正常响应
- [ ] 环境变量正确加载
- [ ] 数据库文件正常创建
- [ ] 日志输出正常
- [ ] Gunicorn 正常启动（非 Flask 开发服务器）

