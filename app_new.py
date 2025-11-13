"""
主应用文件
基于Flask的微信公众号AI发布系统
"""

import os
import requests
from flask import Flask, render_template, send_from_directory, jsonify, request
from werkzeug.middleware.proxy_fix import ProxyFix

# 导入配置和服务
from app_config import AppConfig, setup_logging
from controllers.config_controller import ConfigController
from controllers.article_controller import ArticleController
from controllers.prompt_controller import PromptController
from controllers.sporttery_controller import sporttery_controller
from controllers.data_collection_controller import data_collection_bp
from controllers.ai_assistant_controller import ai_assistant_controller
# 导入新的竞彩路由
from controllers.lottery_controller import lottery_bp

# 设置日志
logger = setup_logging()

# 创建Flask应用
app = Flask(__name__)
app.secret_key = AppConfig.SECRET_KEY
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# 禁用模板和静态文件缓存（开发环境）
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# 创建必要的目录
AppConfig.create_directories()

# 初始化控制器
config_controller = ConfigController()
article_controller = ArticleController()
prompt_controller = PromptController()

# 注册蓝图
app.register_blueprint(lottery_bp)
app.register_blueprint(data_collection_bp)

# ☆☆☆初始化预测管理器 - 从数据库加载赛程数据☆☆☆
try:
    from services.lottery.prediction_manager import prediction_manager
    loaded_count = prediction_manager.load_schedule_from_database()
    if loaded_count > 0:
        logger.info(f"✅ 从数据库加载了 {loaded_count} 场比赛到内存缓存")
    else:
        logger.info("ℹ️ 数据库中暂无赛程数据，等待下次抓取")
except Exception as e:
    logger.error(f"❌ 初始化预测管理器失败: {e}")
    logger.warning("⚠️ 系统将继续启动,但需要手动点击'赛程更新'来加载数据")

# API配置加载已移至 main.py，避免重复加载

@app.route('/')
def index():
    """主页面"""
    logger.info("访问主页面")
    return render_template('index.html')

@app.route('/api/config', methods=['GET', 'POST'])
def handle_config():
    """处理配置信息"""
    logger.info(f"处理配置请求: {request.method}")
    result = config_controller.handle_config_request()
    return jsonify(result)

@app.route('/api/test-wechat', methods=['POST'])
def test_wechat():
    """测试微信API连接"""
    logger.info("测试微信API连接")
    result = config_controller.test_wechat_connection()
    return jsonify(result)

@app.route('/api/test-gemini', methods=['POST'])
def test_gemini():
    """测试Gemini AI连接"""
    logger.info("测试Gemini AI连接")
    result = config_controller.test_gemini_connection()
    return jsonify(result)

@app.route('/api/gemini-models', methods=['GET'])
def get_gemini_models():
    """获取Gemini可用模型列表"""
    logger.info("获取Gemini可用模型列表")
    result = config_controller.get_gemini_models()
    return jsonify(result)

@app.route('/api/test-deepseek', methods=['POST'])
def test_deepseek():
    """测试DeepSeek AI连接"""
    logger.info("测试DeepSeek AI连接")
    result = config_controller.test_deepseek_connection()
    return jsonify(result)

@app.route('/api/deepseek-models', methods=['GET'])
def get_deepseek_models():
    """获取DeepSeek可用模型列表"""
    logger.info("获取DeepSeek可用模型列表")
    result = config_controller.get_deepseek_models()
    return jsonify(result)

@app.route('/api/deepseek-debug', methods=['GET'])
def get_deepseek_debug():
    """获取DeepSeek调试信息"""
    logger.info("获取DeepSeek调试信息")
    result = config_controller.get_deepseek_debug_info()
    return jsonify(result)

@app.route('/api/test-dashscope', methods=['POST'])
def test_dashscope():
    """测试阿里云百炼连接"""
    logger.info("测试阿里云百炼连接")
    result = config_controller.test_dashscope_connection()
    return jsonify(result)

@app.route('/api/dashscope-models', methods=['GET'])
def get_dashscope_models():
    """获取阿里云百炼可用模型列表"""
    logger.info("获取阿里云百炼可用模型列表")
    result = config_controller.get_dashscope_models()
    return jsonify(result)

@app.route('/api/dashscope-debug', methods=['GET'])
def get_dashscope_debug():
    """获取阿里云百炼调试信息"""
    logger.info("获取阿里云百炼调试信息")
    result = config_controller.get_dashscope_debug_info()
    return jsonify(result)

# 已按需移除：Pexels 功能接口（前端不再展示）

@app.route('/api/generate-article', methods=['POST'])
def generate_article():
    """生成文章"""
    logger.info("生成文章请求")
    result = article_controller.generate_article()
    return jsonify(result)

@app.route('/api/generate-enhanced-article', methods=['POST'])
def generate_enhanced_article():
    """生成增强版文章（集成N8N工作流逻辑）"""
    logger.info("生成增强版文章请求")
    result = article_controller.generate_enhanced_article()
    return jsonify(result)

@app.route('/api/save-draft', methods=['POST'])
def save_draft():
    """保存文章草稿"""
    logger.info("保存草稿请求")
    result = article_controller.save_draft()
    return jsonify(result)

@app.route('/api/publish-draft', methods=['POST'])
def publish_draft():
    """发布草稿到微信公众号"""
    logger.info("发布草稿请求")
    result = article_controller.publish_draft()
    return jsonify(result)

@app.route('/api/generation-history', methods=['GET'])
def get_generation_history():
    """获取文章生成历史"""
    logger.info("获取生成历史请求")
    result = article_controller.get_generation_history()
    return jsonify(result)

@app.route('/api/publish-history', methods=['GET'])
def get_publish_history():
    """获取发布历史"""
    logger.info("获取发布历史请求")
    result = article_controller.get_publish_history()
    return jsonify(result)

@app.route('/api/article-content', methods=['POST'])
def get_article_content():
    """获取指定文章的内容"""
    logger.info("获取文章内容请求")
    result = article_controller.get_article_content()
    return jsonify(result)

@app.route('/api/config-status', methods=['GET'])
def get_config_status():
    """获取配置状态"""
    logger.info("获取配置状态")
    result = config_controller.get_config_status()
    return jsonify(result)

@app.route('/api/style-templates', methods=['GET'])
def get_style_templates():
    import os, json
    templates_dir = os.path.join('static', 'style_templates')
    templates = []
    log_msgs = []
    for fname in os.listdir(templates_dir):
        if fname.endswith('.json'):
            meta_path = os.path.join(templates_dir, fname)
            html_path = meta_path.replace('.json', '.html')
            try:
                with open(meta_path, 'r', encoding='utf-8-sig') as f:
                    meta = json.load(f)
                if os.path.exists(html_path):
                    with open(html_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    meta['content'] = content
                    templates.append(meta)
                    log_msgs.append(f"[样式库] 加载模板: id={meta.get('id')}, name={meta.get('name')}, desc={meta.get('desc')}")
                else:
                    log_msgs.append(f"[样式库] 缺少HTML文件: {html_path}")
            except Exception as e:
                log_msgs.append(f"[样式库] 读取模板{fname}失败: {e}")
    # 打印到工作台
    for msg in log_msgs:
        print(msg)
    return jsonify({'success': True, 'templates': templates, 'log': log_msgs})

@app.route('/api/get_ip', methods=['GET'])
def get_ip():
    from flask import request, jsonify
    # 获取用户真实IP（优先X-Forwarded-For，再remote_addr）
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ip and ',' in ip:
        ip = ip.split(',')[0].strip()

    # 返回最近一次微信API错误中解析出的出口IP（比如40164错误返回的IP）
    try:
        from services.wechat_service import LAST_WECHAT_ERROR_IP
        error_ip = LAST_WECHAT_ERROR_IP
    except Exception:
        error_ip = None

    return jsonify({'ip': ip, 'wechat_error_ip': error_ip})

@app.route('/api/proxy-image', methods=['GET'])
def proxy_image():
    """代理访问微信图片，解决防盗链问题"""
    import requests
    from urllib.parse import unquote, quote
    
    try:
        image_url = request.args.get('url')
        if not image_url:
            return jsonify({'error': '缺少图片URL参数'}), 400
        
        # URL解码
        image_url = unquote(image_url)
        
        # 验证是否为微信图片URL
        if not image_url.startswith('http://mmbiz.qpic.cn/'):
            return jsonify({'error': '非微信图片URL'}), 400
        
        # 设置请求头，模拟浏览器访问
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://mp.weixin.qq.com/',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # 请求图片
        response = requests.get(image_url, headers=headers, timeout=10, stream=True)
        
        if response.status_code == 200:
            # 设置响应头
            from flask import Response
            resp = Response(response.iter_content(chunk_size=8192))
            resp.headers['Content-Type'] = response.headers.get('Content-Type', 'image/jpeg')
            resp.headers['Cache-Control'] = 'public, max-age=3600'  # 缓存1小时
            resp.headers['Access-Control-Allow-Origin'] = '*'  # 允许跨域
            return resp
        else:
            logger.error(f"代理图片访问失败: {image_url}, 状态码: {response.status_code}")
            return jsonify({'error': '图片访问失败'}), 404
            
    except Exception as e:
        logger.error(f"代理图片时发生错误: {str(e)}")
        return jsonify({'error': f'代理图片失败: {str(e)}'}), 500

@app.route('/api/get-latest-cache-file', methods=['GET'])
def get_latest_cache_file():
    """获取cache文件夹中最新的文章文件"""
    import os
    import glob
    from datetime import datetime
    
    try:
        cache_dir = AppConfig.CACHE_FOLDER
        if not os.path.exists(cache_dir):
            return jsonify({
                'success': False,
                'message': 'cache文件夹不存在'
            })
        
        # 查找所有article_cleaned_开头的文件
        pattern = os.path.join(cache_dir, 'article_cleaned_*.html')
        files = glob.glob(pattern)
        
        if not files:
            return jsonify({
                'success': False,
                'message': '没有找到已保存的文章文件'
            })
        
        # 按修改时间排序，获取最新的文件
        latest_file = max(files, key=os.path.getmtime)
        
        # 读取文件内容
        with open(latest_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 处理微信图片防盗链问题
        import re
        # 查找微信图片URL并替换为代理访问
        wx_image_pattern = r'http://mmbiz\.qpic\.cn/[^"\']+'
        
        def replace_wx_image(match):
            wx_url = match.group(0)
            # URL编码，确保特殊字符正确处理
            from urllib.parse import quote
            encoded_url = quote(wx_url, safe='')
            # 使用代理URL访问微信图片
            proxy_url = f'/api/proxy-image?url={encoded_url}'
            return proxy_url
        
        # 替换所有微信图片URL
        processed_content = re.sub(wx_image_pattern, replace_wx_image, content)
        
        # 获取文件信息
        file_info = {
            'filename': os.path.basename(latest_file),
            'size': os.path.getsize(latest_file),
            'modified_time': datetime.fromtimestamp(os.path.getmtime(latest_file)).strftime('%Y-%m-%d %H:%M:%S'),
            'content': processed_content
        }
        
        logger.info(f"获取最新缓存文件: {file_info['filename']}")
        
        return jsonify({
            'success': True,
            'message': '获取最新文件成功',
            'data': file_info
        })
        
    except Exception as e:
        logger.error(f"获取最新缓存文件时发生错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'获取文件失败: {str(e)}'
        })

@app.route('/cache/<filename>')
def serve_cache_file(filename):
    """提供缓存文件访问"""
    logger.info(f"访问缓存文件: {filename}")
    return send_from_directory(AppConfig.CACHE_FOLDER, filename)

@app.route('/favicon.ico')
def favicon():
    from flask import send_from_directory
    return send_from_directory('static', 'favicon.ico')

@app.errorhandler(404)
def not_found(error):
    """404错误处理"""
    logger.warning(f"404错误: {request.url}")
    return jsonify({
        'success': False,
        'message': '页面未找到'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """500错误处理"""
    logger.error(f"服务器内部错误: {str(error)}")
    return jsonify({
        'success': False,
        'message': '服务器内部错误'
    }), 500

@app.before_request
def before_request():
    """请求前处理"""
    from flask import request
    logger.info(f"请求: {request.method} {request.path}")

# 预留定时发布API接口（可后续完善）
@app.route('/api/schedule-publish', methods=['POST'])
def schedule_publish():
    """定时发布接口，接收media_id和publish_time"""
    from services.scheduler_service import add_publish_job
    data = request.json
    media_id = data.get('media_id')
    publish_time = data.get('publish_time')
    draft_id = data.get('draft_id', None)
    enable_mass_send = data.get('enable_mass_send', False)
    if not media_id or not publish_time:
        return jsonify({'success': False, 'msg': '参数缺失'}), 400
    job_id = add_publish_job(draft_id, media_id, publish_time, enable_mass_send)
    if job_id:
        return jsonify({'success': True, 'job_id': job_id})
    else:
        return jsonify({'success': False, 'msg': '定时任务添加失败'}), 500

@app.route('/api/mass-send', methods=['POST'])
def mass_send():
    """群发接口，接收publish_id进行群发"""
    logger.info("群发请求")
    data = request.json
    publish_id = data.get('publish_id')
    if not publish_id:
        return jsonify({'success': False, 'msg': 'publish_id参数缺失'}), 400
    
    try:
        # 获取access_token
        from services.config_service import ConfigService
        config_service = ConfigService()
        wx_cfg = config_service.get_wechat_config()
        from services.wechat_service import WeChatService
        wechat_service = WeChatService()
        access_token_info = wechat_service.get_access_token(wx_cfg['appid'], wx_cfg['appsecret'])
        if not access_token_info or 'access_token' not in access_token_info:
            return jsonify({'success': False, 'msg': '获取access_token失败'}), 500
        
        access_token = access_token_info['access_token']
        
        # 调用群发接口
        url = f"{AppConfig.WECHAT_BASE_URL}/cgi-bin/message/mass/send"
        params = {'access_token': access_token}
        
        # 群发给所有粉丝
        payload = {
            "touser": [],  # 空数组表示群发给所有粉丝
            "mpnews": {
                "media_id": publish_id
            },
            "msgtype": "mpnews"
        }
        
        response = requests.post(url, params=params, json=payload, timeout=AppConfig.API_TIMEOUT)
        response.raise_for_status()
        result = response.json()
        
        if result.get('errcode') == 0:
            logger.info(f"群发任务提交成功，msg_id: {result.get('msg_id')}")
            # 更新群发状态到历史记录
            from services.history_service import HistoryService
            history_service = HistoryService()
            history_service.update_mass_send_status(publish_id, result)
            return jsonify({
                'success': True, 
                'msg_id': result.get('msg_id'),
                'msg_data_id': result.get('msg_data_id')
            })
        else:
            error_msg = result.get('errmsg', '未知错误')
            logger.error(f"群发失败，错误码: {result.get('errcode')}, 错误信息: {error_msg}")
            return jsonify({'success': False, 'msg': f'群发失败: {error_msg}'}), 500
            
    except Exception as e:
        logger.error(f"群发异常: {str(e)}")
        return jsonify({'success': False, 'msg': f'群发异常: {str(e)}'}), 500

@app.route('/api/local_version', methods=['GET'])
def get_local_version():
    return jsonify(article_controller.get_local_version())

@app.route('/api/update_from_github', methods=['POST'])
def update_from_github():
    return jsonify(article_controller.update_from_github())

# 提示词管理相关路由
@app.route('/prompt-manager')
def prompt_manager_page():
    """提示词管理页面"""
    logger.info("访问提示词管理页面")
    return prompt_controller.prompt_manager_page()

@app.route('/enhanced-generator')
def enhanced_generator_page():
    """增强版文章生成器页面"""
    logger.info("访问增强版文章生成器页面")
    return render_template('enhanced_generator.html')

@app.route('/features')
def features_page():
    """功能清单页面（前端展示，暂不落库）"""
    logger.info("访问功能清单页面")
    return render_template('features.html')

@app.route('/layout-demo')
def layout_demo():
    """界面设计对比页面"""
    logger.info("访问界面设计对比页面")
    return render_template('layout_demo.html')

@app.route('/layout-demo-v2')
def layout_demo_v2():
    """更多界面设计对比页面"""
    logger.info("访问更多界面设计对比页面")
    return render_template('layout_demo_v2.html')

@app.route('/_routes')
def list_routes():
    """调试：列出所有路由"""
    try:
        rules = []
        for r in app.url_map.iter_rules():
            rules.append({
                'rule': str(r),
                'endpoint': r.endpoint,
                'methods': sorted(list(r.methods))
            })
        return jsonify({'success': True, 'routes': rules})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/prompt-templates', methods=['GET'])
def get_prompt_templates():
    """获取所有提示词模板"""
    return prompt_controller.get_templates()

@app.route('/api/prompt-templates', methods=['POST'])
def create_prompt_template():
    """创建新的提示词模板"""
    return prompt_controller.create_template()

@app.route('/api/prompt-templates/<key>', methods=['GET'])
def get_prompt_template(key):
    """获取单个提示词模板"""
    return prompt_controller.get_template(key)

@app.route('/api/prompt-templates/<key>', methods=['PUT'])
def update_prompt_template(key):
    """更新提示词模板"""
    return prompt_controller.update_template(key)

@app.route('/api/prompt-templates/<key>', methods=['DELETE'])
def delete_prompt_template(key):
    """删除提示词模板"""
    return prompt_controller.delete_template(key)

@app.route('/api/prompt-templates/category/<category>', methods=['GET'])
def get_prompt_templates_by_category(category):
    """按分类获取提示词模板"""
    return prompt_controller.get_templates_by_category(category)

@app.route('/api/prompt-templates/<key>/render', methods=['POST'])
def render_prompt_template(key):
    """渲染提示词模板"""
    return prompt_controller.render_template(key)

@app.route('/api/prompt-templates/<key>/usage', methods=['POST'])
def record_prompt_usage(key):
    """记录模板使用情况"""
    return prompt_controller.record_usage(key)

@app.route('/api/prompt-templates/export', methods=['GET'])
def export_prompt_templates():
    """导出提示词模板"""
    return prompt_controller.export_templates()

@app.route('/api/prompt-templates/import', methods=['POST'])
def import_prompt_templates():
    """导入提示词模板"""
    return prompt_controller.import_templates()

@app.route('/api/prompt-templates/statistics', methods=['GET'])
def get_prompt_statistics():
    """获取模板统计信息"""
    return prompt_controller.get_template_statistics()

@app.route('/api/sync-qwen-vl-prompt', methods=['POST'])
def sync_qwen_vl_prompt():
    """同步千问VL提示词到实际工作流"""
    return prompt_controller.sync_qwen_vl_prompt()

@app.route('/api/test-qwen-vl', methods=['POST'])
def test_qwen_vl():
    """测试千问VL图片识别"""
    import base64
    from services.dashscope_service import dashscope_service
    
    try:
        # 检查是否有上传的图片
        if 'image' not in request.files:
            return jsonify({
                'success': False,
                'message': '未找到上传的图片'
            }), 400
        
        image_file = request.files['image']
        prompt = request.form.get('prompt', '请分析这张图片')
        
        if image_file.filename == '':
            return jsonify({
                'success': False,
                'message': '未选择图片'
            }), 400
        
        # 读取图片并转为base64
        image_data = base64.b64encode(image_file.read()).decode('utf-8')
        
        # 调用千问VL分析
        logger.info(f"开始测试千问VL图片识别")
        result = dashscope_service.analyze_image(image_data, prompt)
        
        if result and result.get('success'):
            logger.info(f"千问VL识别成功")
            return jsonify({
                'success': True,
                'message': '识别成功',
                'data': result.get('content', '')
            })
        else:
            error_msg = result.get('message', '识别失败，请检查API配置') if result else 'API调用失败'
            logger.error(f"千问VL识别失败: {error_msg}")
            return jsonify({
                'success': False,
                'message': error_msg
            }), 500
            
    except Exception as e:
        logger.error(f"测试千问VL失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'测试失败: {str(e)}'
        }), 500

# 竞彩数据相关API
@app.route('/api/sporttery/matches', methods=['GET'])
def get_sporttery_matches():
    """获取竞彩比赛数据"""
    return jsonify(sporttery_controller.get_matches())

@app.route('/api/sporttery/results', methods=['GET'])
def get_sporttery_results():
    """获取竞彩赛果数据"""
    return jsonify(sporttery_controller.get_results())

@app.route('/api/sporttery/refresh', methods=['POST'])
def refresh_sporttery_data():
    """刷新竞彩数据"""
    return jsonify(sporttery_controller.refresh_data())


# 数据搜集相关路由已移至蓝图 data_collection_bp，无需重复定义

# AI助手相关路由
@app.route('/api/ai-assistant/test-zhipu', methods=['POST'])
def test_zhipu_connection():
    """测试智谱AI连接"""
    try:
        data = request.get_json()
        api_key = data.get('api_key')
        model = data.get('model', 'glm-4')
        
        if not api_key:
            return jsonify({
                "success": False,
                "message": "API密钥不能为空"
            }), 400
        
        return ai_assistant_controller.test_zhipu_connection(api_key, model)
    except Exception as e:
        logger.error(f"测试智谱AI连接失败: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"测试连接失败: {str(e)}"
        }), 500

@app.route('/api/ai-assistant/save-zhipu-config', methods=['POST'])
def save_zhipu_config():
    """保存智谱AI配置"""
    try:
        data = request.get_json()
        api_key = data.get('api_key')
        model = data.get('model', 'glm-4.5-air')
        
        if not api_key:
            return jsonify({
                "success": False,
                "message": "API密钥不能为空"
            }), 400
        
        return ai_assistant_controller.save_zhipu_config(api_key, model)
    except Exception as e:
        logger.error(f"保存智谱AI配置失败: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"保存配置失败: {str(e)}"
        }), 500

# 已删除冗余的AI助手配置保存接口
# 统一使用 /api/config 接口进行配置保存

@app.route('/api/ai-assistant/chat', methods=['POST'])
def ai_assistant_chat():
    """AI助手对话接口"""
    try:
        data = request.get_json()
        user_input = data.get('message', '').strip()
        use_web_search = bool(data.get('use_web_search'))
        search_engine = data.get('search_engine') or None
        
        if not user_input:
            return jsonify({
                "success": False,
                "message": "输入内容不能为空"
            }), 400
        
        return ai_assistant_controller.process_user_command(
            user_input=user_input,
            use_web_search=use_web_search,
            search_engine=search_engine
        )
    except Exception as e:
        logger.error(f"AI助手对话失败: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"对话失败: {str(e)}"
        }), 500

# 注意：启动代码已移至 main.py，这里保留微信token刷新逻辑
def init_wechat_token():
    """初始化微信access_token（在应用启动时调用）"""
    logger.info("启动微信公众号AI发布系统")
    
    # 刷新微信access_token（确保token有效）
    try:
        from services.config_service import config_service
        from services.wechat_service import wechat_service
        
        config = config_service.load_config()
        wechat_config = config.get('wechat', {})
        appid = wechat_config.get('wechat_appid')
        appsecret = wechat_config.get('wechat_appsecret')
        
        if appid and appsecret:
            logger.info("🔄 正在刷新微信access_token...")
            token_info = wechat_service.get_access_token(appid, appsecret)
            if token_info and token_info.get('access_token'):
                logger.info("✅ 微信access_token刷新成功")
            else:
                logger.warning("⚠️ 微信access_token刷新失败,发布功能可能不可用")
        else:
            logger.warning("⚠️ 未配置微信AppID/AppSecret,跳过token刷新")
    except Exception as e:
        logger.error(f"❌ 微信token刷新失败: {e}")

if __name__ == '__main__':
    # 如果直接运行app_new.py，则自动初始化微信token
    init_wechat_token()
    # 但推荐使用 main.py 启动，这样可以避免端口冲突
    logger.info("建议使用 'python main.py' 启动应用")