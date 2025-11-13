# Zeabur 部署配置指南

## ⚠️ 重要配置

### 1. 构建路径设置

在 Zeabur 项目设置中，**必须配置正确的构建路径**：

- **Root Directory（根目录）**: `AIWeChatauto`
- **Dockerfile 路径**: `Dockerfile`（相对于根目录）

或者如果 Zeabur 支持：
- **Build Context**: `AIWeChatauto`
- **Dockerfile**: `AIWeChatauto/Dockerfile`

### 2. 环境变量配置

在 Zeabur 项目设置 → Environment Variables 中添加：

```
GEMINI_API_KEY=your_gemini_api_key
DEEPSEEK_API_KEY=your_deepseek_api_key
DASHSCOPE_API_KEY=your_dashscope_api_key
ZHIPU_API_KEY=your_zhipu_api_key
WECHAT_APPID=your_wechat_appid
WECHAT_APPSECRET=your_wechat_appsecret
```

**注意**：`PORT` 环境变量由 Zeabur 自动设置，无需手动配置。

### 3. 持久化存储配置

1. 进入项目设置 → **Storage/Volumes**
2. 创建持久化卷：
   - **硬盘 ID**: `wechatbot-data`
   - **挂载目录**: `/app`
3. 点击"挂载硬盘"

### 4. 端口配置

- Zeabur 会自动检测端口
- 应用会从 `PORT` 环境变量读取端口号
- 默认端口：8001

## 🔍 故障排查

### 问题：ModuleNotFoundError: No module named 'app_new'

**原因**：
- 构建路径配置不正确
- Dockerfile 不在正确的目录

**解决方案**：
1. 检查 Zeabur 的 Root Directory 设置是否为 `AIWeChatauto`
2. 确认 Dockerfile 路径正确
3. 查看构建日志，确认文件是否被正确复制

### 问题：构建失败

**检查项**：
1. 确认 GitHub 仓库连接正常
2. 确认分支设置为 `master`
3. 查看构建日志中的错误信息

### 问题：应用启动失败

**检查项**：
1. 查看容器日志
2. 确认环境变量已正确设置
3. 确认持久化存储已挂载

## 📝 验证部署

部署成功后，检查：

1. **访问应用**：打开 Zeabur 提供的域名
2. **查看日志**：在 Zeabur 控制台查看应用日志
3. **检查数据**：确认数据库文件在持久化存储中

## 🔄 重新部署

如果部署失败：

1. 检查并修复配置
2. 在 Zeabur 中点击"重新部署"
3. 查看构建和运行日志
4. 根据错误信息调整配置

