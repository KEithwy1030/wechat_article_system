from app_new import app

# 临时注释掉init_wechat_token的导入，避免启动问题
try:
    from app_new import init_wechat_token
except ImportError:
    init_wechat_token = None
import socket
import os
import platform
import logging

logger = logging.getLogger(__name__)

def is_docker_env():
    """检测是否在 Docker 环境中运行"""
    return os.path.exists('/.dockerenv') or os.environ.get('DOCKER_CONTAINER') == 'true'

def check_port_available(port, max_retries=3):
    """检查端口是否可用（跨平台版本）"""
    # Docker 环境中跳过端口检查（容器环境通常端口是干净的）
    if is_docker_env():
        return True
    
    # 本地开发环境才进行端口检查
    for retry in range(max_retries):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('0.0.0.0', port))
            sock.close()
            return True
        except OSError as e:
            if retry < max_retries - 1:
                print(f"端口 {port} 绑定失败 (第 {retry + 1}/{max_retries} 次): {e}")
                import time
                time.sleep(2)
            else:
                print(f"端口 {port} 无法绑定: {e}")
                return False
    return False

if __name__ == '__main__':
    # 从环境变量读取端口（Zeabur/Docker 会设置 PORT 环境变量）
    # 默认使用 8080，便于与 Zeabur 保持一致；本地开发如需其他端口可自行设置 PORT
    port = int(os.environ.get('PORT', 8080))
    
    # 🔥 加载所有API配置到环境变量
    try:
        from services.config_service import config_service
        import os
        
        config = config_service.load_config()
        
        # 加载DeepSeek API Key - 优先从嵌套结构获取
        deepseek_key = config.get('deepseek', {}).get('apiKey') or config.get('deepseek_api_key')
        if deepseek_key:
            os.environ['DEEPSEEK_API_KEY'] = deepseek_key
            print("[成功] DeepSeek API Key已加载")
        else:
            print("[警告] 未找到DeepSeek API Key配置")
        
        # 加载Gemini API Key - 优先从嵌套结构获取
        gemini_key = config.get('gemini', {}).get('apiKey') or config.get('gemini_api_key')
        if gemini_key:
            os.environ['GEMINI_API_KEY'] = gemini_key
            print("[成功] Gemini API Key已加载")
        
        # 加载DashScope API Key - 优先从嵌套结构获取
        dashscope_key = config.get('dashscope', {}).get('apiKey') or config.get('dashscope_api_key')
        if dashscope_key:
            os.environ['DASHSCOPE_API_KEY'] = dashscope_key
            print("[成功] DashScope API Key已加载")
        
        # 加载智谱AI API Key - 优先从嵌套结构获取
        zhipu_key = config.get('zhipu', {}).get('apiKey') or config.get('zhipu_api_key')
        if zhipu_key:
            os.environ['ZHIPU_API_KEY'] = zhipu_key
            print("[成功] 智谱AI API Key已加载")
            
    except Exception as e:
        print(f"[错误] 加载API配置失败: {e}")
    
    # 初始化微信token
    if init_wechat_token:
        try:
            init_wechat_token()
        except Exception as e:
            logger.warning(f"微信token初始化失败: {e}")
    else:
        logger.info("跳过微信token初始化")
    
    # 只在非 Docker 环境检查端口
    if not is_docker_env() and not check_port_available(port):
        print(f"端口 {port} 被占用，请手动检查或重启系统")
        if platform.system() == 'Windows':
            print("提示：可以运行 'netstat -ano | findstr :8001' 查看占用进程")
        else:
            print("提示：可以运行 'lsof -i :8001' 或 'netstat -tulpn | grep 8001' 查看占用进程")
        exit(1)
    
    print(f"正在启动Flask应用，端口: {port}")
    if is_docker_env():
        print("检测到 Docker 环境，使用生产模式")
        # Docker 环境使用生产模式（不使用 debug）
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False, threaded=True)
    else:
        # 本地开发环境
        app.run(host='0.0.0.0', port=port, debug=True, use_reloader=False, threaded=True)
