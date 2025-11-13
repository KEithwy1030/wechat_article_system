# WechatBOT - 微信公众号AI自动发布系统

基于 Flask 的微信公众号内容创作与自动发布平台，专注于竞彩足球预测文章的自动生成与发布。

## ✨ 核心功能

### 🎯 竞彩数据管理
- **赛程更新**：自动抓取最新竞彩赛程数据
- **赛果更新**：定时抓取比赛结果并更新数据库
- **快速预测**：基于 AI 模型的快速比分预测
- **深度分析**：AI 生成深度分析文章
- **命中率统计**：自动统计预测准确率（快速预测/深度分析分别统计）

### 🤖 多AI模型支持
- **Gemini**：Google Gemini 模型
- **DeepSeek**：DeepSeek Chat 模型
- **DashScope**：阿里云通义千问模型
- **智谱AI**：Zhipu AI 模型
- 支持模型切换和配置管理

### 📝 文章生成与发布
- **AI 文章生成**：基于 Prompt 模板生成文章
- **Markdown 转换**：自动转换为微信格式
- **历史记录**：文章生成历史查看和管理
- **一键发布**：支持发布到微信公众号

### 📊 数据统计与分析
- **预测统计**：快速预测和深度分析的命中率统计
- **赛程管理**：比赛数据可视化展示
- **结果追踪**：比赛结果自动更新和匹配

### ⏰ 定时任务
- **自动赛果抓取**：定时抓取昨日比赛结果
- **准确率更新**：定时更新预测准确率统计
- **赛程更新**：定时抓取最新赛程
- **自动预测**：定时执行快速预测和深度分析

## 🚀 快速开始

### 环境要求
- Python 3.11+
- Chrome/Chromium 浏览器（用于数据抓取）

### 本地部署

1. **克隆项目**
```bash
git clone https://github.com/KEithwy1030/wechat_article_system.git
cd wechat_article_system/AIWeChatauto
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **配置环境变量**
```bash
# 复制环境变量示例文件
cp env.example .env

# 编辑 .env 文件，填入你的 API Keys
# - GEMINI_API_KEY
# - DEEPSEEK_API_KEY
# - DASHSCOPE_API_KEY
# - ZHIPU_API_KEY
# - WECHAT_APPID
# - WECHAT_APPSECRET
```

4. **启动应用**
```bash
python main.py
```

5. **访问系统**
- 本地访问：http://localhost:8001

### Docker 部署

1. **使用 Docker Compose（推荐）**
```bash
cd AIWeChatauto
docker-compose up -d
```

2. **或使用 Dockerfile**
```bash
docker build -t wechatbot-app .
docker run -d -p 8001:8001 \
  -e GEMINI_API_KEY=your_key \
  -e DEEPSEEK_API_KEY=your_key \
  -e WECHAT_APPID=your_appid \
  -e WECHAT_APPSECRET=your_secret \
  wechatbot-app
```

详细部署文档请参考：[DOCKER_DEPLOY.md](DOCKER_DEPLOY.md)

### Zeabur 云部署

1. **连接 GitHub 仓库**
   - 在 Zeabur 创建新项目
   - 连接 `https://github.com/KEithwy1030/wechat_article_system`
   - 设置分支为 `master`

2. **配置环境变量**
   - 在 Zeabur 项目设置中添加所有 API Keys
   - 参考 `env.example` 文件

3. **配置持久化存储（重要！）**
   - 进入 Storage/Volumes 设置
   - 创建持久化卷，挂载到 `/app`
   - 确保数据在容器重启后不丢失

4. **部署**
   - Zeabur 会自动构建和部署
   - 部署完成后访问提供的域名

详细部署文档请参考：[DOCKER_DEPLOY.md](DOCKER_DEPLOY.md)

## 📁 项目结构

```
AIWeChatauto/
├── app_new.py              # Flask 主应用
├── main.py                 # 启动入口
├── app_config.py           # 应用配置
├── config.json             # 配置文件（本地，不提交）
├── requirements.txt        # Python 依赖
├── Dockerfile              # Docker 构建文件
├── docker-compose.yml      # Docker Compose 配置
├── controllers/            # 控制器层
│   ├── lottery_controller.py      # 竞彩控制器
│   ├── article_controller.py     # 文章控制器
│   ├── config_controller.py      # 配置控制器
│   └── ...
├── services/               # 服务层
│   ├── lottery/            # 竞彩相关服务
│   │   ├── prediction_manager.py  # 预测管理
│   │   ├── lottery_scraper.py     # 数据抓取
│   │   ├── score_predictor.py     # 比分预测
│   │   └── ...
│   ├── gemini_service.py   # Gemini AI 服务
│   ├── deepseek_service.py # DeepSeek AI 服务
│   ├── wechat_service.py   # 微信服务
│   └── ...
├── templates/              # 前端模板
├── static/                 # 静态资源
├── data/                   # 数据目录（数据库文件）
└── logs/                   # 日志目录
```

## ⚙️ 配置说明

### 环境变量配置

通过环境变量或 `.env` 文件配置：

| 变量名 | 说明 | 必需 |
|--------|------|------|
| `GEMINI_API_KEY` | Gemini API Key | 否 |
| `DEEPSEEK_API_KEY` | DeepSeek API Key | 否 |
| `DASHSCOPE_API_KEY` | 阿里云 DashScope API Key | 否 |
| `ZHIPU_API_KEY` | 智谱AI API Key | 否 |
| `WECHAT_APPID` | 微信公众号 AppID | 是 |
| `WECHAT_APPSECRET` | 微信公众号 AppSecret | 是 |
| `PORT` | 服务端口（默认 8001） | 否 |

### 数据库

系统使用 SQLite 数据库：
- `system.db` - 主数据库（赛程、赛果数据）
- `data/prediction_stats.db` - 预测统计
- `data/quick_predictions.db` - 快速预测数据
- `data/schedule_display.db` - 赛程显示数据

**注意**：数据库文件需要持久化存储，否则容器重启会丢失数据。

## 🔧 功能使用

### 赛程管理
1. 点击"赛程更新"按钮，系统会自动抓取最新赛程
2. 在赛程列表中查看所有比赛
3. 点击"快速预测"进行快速比分预测
4. 点击"深度"进行深度分析文章生成

### 文章生成
1. 在文章生成页面选择 AI 模型
2. 输入文章标题或使用模板
3. 配置生成参数（字数、配图等）
4. 点击生成，系统会自动生成文章
5. 在历史记录中查看和管理生成的文章

### 数据统计
- 系统自动统计快速预测和深度分析的命中率
- 在统计页面查看详细数据
- 支持按时间范围筛选

## 📚 文档

- [Docker 部署指南](DOCKER_DEPLOY.md) - 详细的 Docker 和 Zeabur 部署说明
- [数据迁移指南](DATA_MIGRATION.md) - 如何迁移本地数据到云环境
- [数据库策略](DATABASE_STRATEGY.md) - SQLite vs MySQL 选择建议

## 🛠️ 开发

### 本地开发
```bash
# 安装依赖
pip install -r requirements.txt

# 启动开发服务器
python main.py

# 访问 http://localhost:8001
```

### 代码结构
- **MVC 架构**：Controllers（控制器）、Services（服务层）、Templates（视图）
- **模块化设计**：各功能模块独立，便于维护和扩展
- **异步任务**：使用线程池处理耗时任务

## ⚠️ 注意事项

1. **数据持久化**：部署时必须配置持久化存储，否则数据会丢失
2. **API 限制**：注意各 AI 平台的 API 调用限制
3. **网络要求**：数据抓取需要稳定的网络连接
4. **Chrome 驱动**：确保 Chrome/Chromium 浏览器可用

## 📝 License

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

**项目地址**：https://github.com/KEithwy1030/wechat_article_system
