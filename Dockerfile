# 使用 Python 3.11 作为基础镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 先安装系统依赖和 Chrome（这些变化较少，可以缓存）
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# 先复制依赖文件（利用 Docker 缓存，依赖不变时不重新安装）
COPY requirements.txt .

# 安装 Python 依赖（使用国内镜像加速，可选）
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir schedule

# 复制应用代码
COPY . .

# 创建必要的目录
RUN mkdir -p logs cache data backups

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PORT=8001

# 暴露端口（Zeabur 会通过环境变量 PORT 设置）
EXPOSE 8001

# 启动命令
# Zeabur 生产环境：使用 gunicorn（性能更好）
# 设置 PYTHONPATH 确保模块导入正常
ENV PYTHONPATH=/app
CMD ["sh", "-c", "python -c 'from app_new import app; print(\"App imported successfully\")' && gunicorn --bind 0.0.0.0:${PORT:-8001} --workers 2 --threads 4 --timeout 120 --access-logfile - --error-logfile - --preload app_new:app"]

