# Docker 生产环境测试清单

## 为什么要在 Docker 中测试？

✅ **强烈建议**在部署到 Zeabur 之前，先在本地 Docker 中模拟生产环境进行测试：

1. **环境一致性**：Docker 环境与 Zeabur 更接近，能发现本地开发环境发现不了的问题
2. **提前发现问题**：避免在 Zeabur 上反复调试，节省时间和成本
3. **验证配置**：确保环境变量、端口、资源限制等配置正确
4. **性能测试**：可以测试在资源限制下的运行情况

## 测试步骤

### 1. 构建 Docker 镜像

```bash
# 在项目根目录执行
cd AIWeChatauto
docker build -t wechatbot-app .
```

### 2. 准备环境变量

创建 `.env` 文件（或直接在 docker-compose.yml 中设置）：

```env
GEMINI_API_KEY=your_gemini_key
DEEPSEEK_API_KEY=your_deepseek_key
DASHSCOPE_API_KEY=your_dashscope_key
ZHIPU_API_KEY=your_zhipu_key
WECHAT_APPID=your_wechat_appid
WECHAT_APPSECRET=your_wechat_appsecret
```

### 3. 启动容器

```bash
# 使用 docker-compose（推荐）
docker-compose up -d

# 或直接使用 docker run
docker run -d \
  --name wechatbot-app \
  -p 8001:8001 \
  -e PORT=8001 \
  -e GEMINI_API_KEY=your_key \
  -e DEEPSEEK_API_KEY=your_key \
  -e DASHSCOPE_API_KEY=your_key \
  -e ZHIPU_API_KEY=your_key \
  -e WECHAT_APPID=your_appid \
  -e WECHAT_APPSECRET=your_secret \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/cache:/app/cache \
  wechatbot-app
```

### 4. 检查容器状态

```bash
# 查看容器运行状态
docker ps

# 查看容器日志
docker logs wechatbot-app

# 实时查看日志
docker logs -f wechatbot-app
```

### 5. 功能测试清单

#### ✅ 基础功能测试

- [ ] **Web 界面访问**
  - 访问 `http://localhost:8001`
  - 检查页面是否正常加载
  - 检查静态资源（CSS、JS）是否正常加载

- [ ] **API 接口测试**
  - 测试配置接口：`GET /api/config`
  - 测试文章生成接口：`POST /api/article/generate`
  - 测试竞彩数据接口：`GET /api/lottery/matches`

- [ ] **数据库功能**
  - 检查数据库文件是否正常创建（`data/system.db`）
  - 测试数据读写功能
  - 检查数据持久化（重启容器后数据是否保留）

#### ✅ 核心功能测试

- [ ] **AI 服务调用**
  - 测试 Gemini API 调用
  - 测试 DeepSeek API 调用
  - 测试 DashScope API 调用
  - 测试 ZhipuAI API 调用

- [ ] **文章生成**
  - 测试完整文章生成流程
  - 检查文章内容质量
  - 验证文章保存功能

- [ ] **竞彩功能**
  - 测试数据采集
  - 测试快速预测
  - 测试深度分析
  - 测试定时任务

- [ ] **定时任务**
  - 检查定时任务是否正常启动
  - 验证任务执行日志

#### ✅ 生产环境特性测试

- [ ] **Gunicorn 运行**
  - 检查是否使用 gunicorn 启动（而非 `python main.py`）
  - 查看日志确认：`gunicorn --bind 0.0.0.0:8001`

- [ ] **资源限制**
  - 检查内存使用是否在限制范围内（2G）
  - 检查 CPU 使用是否正常

- [ ] **环境变量**
  - 验证所有 API Key 是否正确加载
  - 检查 PORT 环境变量是否生效

- [ ] **持久化存储**
  - 重启容器，检查数据是否保留
  - 验证日志文件是否正常写入

- [ ] **错误处理**
  - 测试 API Key 错误时的处理
  - 测试网络错误时的处理
  - 检查错误日志是否正常记录

### 6. 性能测试

- [ ] **响应时间**
  - 测试页面加载速度
  - 测试 API 响应时间

- [ ] **并发测试**
  - 测试多个用户同时访问
  - 检查资源使用情况

- [ ] **长时间运行**
  - 运行 24 小时，检查稳定性
  - 检查内存泄漏问题

### 7. 日志检查

```bash
# 查看应用日志
docker logs wechatbot-app | grep -i error
docker logs wechatbot-app | grep -i warning

# 查看系统日志
docker exec wechatbot-app cat /app/logs/app_*.log
```

检查要点：
- [ ] 无严重错误（ERROR）
- [ ] 警告信息（WARNING）在可接受范围内
- [ ] 启动日志正常
- [ ] API 调用日志正常

### 8. 清理测试

```bash
# 停止容器
docker-compose down

# 或
docker stop wechatbot-app
docker rm wechatbot-app

# 清理镜像（可选）
docker rmi wechatbot-app
```

## 常见问题排查

### 问题1：容器启动失败

**检查：**
```bash
docker logs wechatbot-app
```

**可能原因：**
- 端口被占用
- 环境变量缺失
- 依赖安装失败

### 问题2：API 调用失败

**检查：**
- API Key 是否正确设置
- 网络连接是否正常
- 查看日志中的错误信息

### 问题3：数据库文件丢失

**检查：**
- 数据卷挂载是否正确
- 文件权限是否正确

### 问题4：Gunicorn 启动失败

**检查：**
```bash
docker exec wechatbot-app ps aux | grep gunicorn
```

如果 gunicorn 未运行，检查：
- requirements.txt 中是否包含 gunicorn
- Dockerfile 中的 CMD 命令是否正确

## 测试通过标准

✅ **所有基础功能测试通过**
✅ **所有核心功能测试通过**
✅ **无严重错误日志**
✅ **资源使用正常**
✅ **数据持久化正常**
✅ **长时间运行稳定**

## 测试通过后

如果所有测试通过，可以：

1. **标记测试版本**
   ```bash
   docker tag wechatbot-app:latest wechatbot-app:v1.0.0
   ```

2. **准备部署到 Zeabur**
   - 确保代码已提交到 Git
   - 准备 Zeabur 环境变量配置
   - 按照 Zeabur 部署流程进行部署

## 快速测试命令

```bash
# 一键测试脚本
docker-compose up -d && \
sleep 5 && \
curl http://localhost:8001/api/config && \
echo "✅ 基础测试通过" || echo "❌ 测试失败"
```

