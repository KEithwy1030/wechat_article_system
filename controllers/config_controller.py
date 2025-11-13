"""
配置控制器模块
处理配置相关的HTTP请求
"""

import logging
from flask import request, jsonify
from typing import Dict, Any
from services.config_service import ConfigService
from services.wechat_service import WeChatService
from services.gemini_service import GeminiService
from services.deepseek_service import DeepSeekService
from services.dashscope_service import DashScopeService

logger = logging.getLogger(__name__)

class ConfigController:
    """配置控制器类"""
    
    def __init__(self):
        self.config_service = ConfigService()
        self.wechat_service = WeChatService()
        self.gemini_service = GeminiService()
        self.deepseek_service = DeepSeekService()
        self.dashscope_service = DashScopeService()
        logger.info("配置控制器初始化完成")
    
    def handle_config_request(self) -> Dict[str, Any]:
        """
        处理配置请求
        :return: 响应数据
        """
        try:
            if request.method == 'GET':
                return self._get_config()
            elif request.method == 'POST':
                return self._save_config()
            else:
                return {
                    'success': False,
                    'message': '不支持的请求方法'
                }
        except Exception as e:
            logger.error(f"处理配置请求时发生错误: {str(e)}")
            return {
                'success': False,
                'message': f'服务器错误: {str(e)}'
            }
    
    def _get_config(self) -> Dict[str, Any]:
        """获取配置"""
        try:
            logger.info("开始获取配置信息")
            config = self.config_service.load_config()
            # 直接返回真实配置信息，不隐藏敏感信息
            logger.info("配置信息获取成功")
            return {
                'success': True,
                'data': config,
                'message': '配置加载成功'
            }
        except Exception as e:
            logger.error(f"获取配置时发生错误: {str(e)}")
            return {
                'success': False,
                'message': f'加载配置失败: {str(e)}'
            }
    
    def _save_config(self) -> Dict[str, Any]:
        """保存配置"""
        try:
            config_data = request.get_json()
            if not config_data:
                logger.error("请求数据为空")
                return {
                    'success': False,
                    'message': '请求数据为空'
                }
            
            logger.info("开始保存配置")
            logger.info(f"接收到的配置数据: {config_data}")
            
            # 验证必填字段
            validation_result = self._validate_config_data(config_data)
            if not validation_result['valid']:
                logger.error(f"配置验证失败: {validation_result['message']}")
                return {
                    'success': False,
                    'message': validation_result['message']
                }
            
            # 保存配置
            save_result = self.config_service.save_config(config_data)
            logger.info(f"配置保存结果: {save_result}")
            
            if save_result:
                # 验证保存是否成功
                saved_config = self.config_service.load_config()
                logger.info(f"保存后读取的配置: {saved_config}")
                
                # 🔥 立即更新环境变量，让配置立即生效
                self._update_environment_variables(saved_config)
                
                # 🔥 同步更新相关服务的配置
                self._sync_service_configs(saved_config)
                
                logger.info("配置保存成功")
                return {
                    'success': True,
                    'message': '配置保存成功',
                    'data': saved_config
                }
            else:
                logger.error("配置保存失败")
                return {
                    'success': False,
                    'message': '配置保存失败'
                }
                
        except Exception as e:
            logger.error(f"保存配置时发生错误: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'保存配置失败: {str(e)}'
            }
    
    def _validate_config_data(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """验证配置数据"""
        logger.info(f"开始验证配置数据: {config_data}")
        
        # 检查必填字段，但允许部分为空以支持分步配置
        required_fields = {
            # 微信公众号配置为可选，不强制验证
            # 'wechat_appid': '微信AppID',
            # 'wechat_appsecret': '微信AppSecret', 
            # 其他不做强制校验，coze_token 不做强制校验
            # coze_workflow_id 不做强制校验
        }
        
        # 只验证存在且非空的字段
        for field, label in required_fields.items():
            if field in config_data and config_data[field]:
                value = config_data[field]
                if not isinstance(value, str) or not value.strip():
                    logger.error(f"字段 {field} 值无效: {value}")
                    return {
                        'valid': False,
                        'message': f'{label}格式错误'
                    }
                
                # 验证微信AppID格式（如果提供）
                if field == 'wechat_appid':
                    wechat_appid = value.strip()
                    if not wechat_appid.startswith('wx') or len(wechat_appid) != 18:
                        return {
                            'valid': False,
                            'message': '微信AppID格式不正确，应为wx开头的18位字符'
                        }
                
                # 验证Gemini API密钥格式（如果提供）
                if field == 'gemini_api_key':
                    gemini_api_key = value.strip()
                    if not gemini_api_key.startswith('AIza'):
                        return {
                            'valid': False,
                            'message': 'Gemini API密钥格式不正确，应以AIza开头'
                        }
        
        logger.info("配置数据验证通过")
        return {'valid': True}
    
    def _update_environment_variables(self, config_data: Dict[str, Any]):
        """保存配置后立即更新环境变量，让配置立即生效"""
        try:
            import os
            
            # 更新DeepSeek API Key - 优先从嵌套结构获取
            deepseek_key = config_data.get('deepseek', {}).get('apiKey', '') or config_data.get('deepseek_api_key', '')
            if deepseek_key:
                os.environ['DEEPSEEK_API_KEY'] = deepseek_key
                logger.info("✅ DeepSeek API Key环境变量已更新")
            elif 'deepseek' in config_data or 'deepseek_api_key' in config_data:
                # 如果配置中明确设置为空，也清理环境变量
                if 'DEEPSEEK_API_KEY' in os.environ:
                    del os.environ['DEEPSEEK_API_KEY']
                logger.info("✅ DeepSeek API Key环境变量已清理")
            
            # 更新Gemini API Key - 优先从嵌套结构获取
            gemini_key = config_data.get('gemini', {}).get('apiKey', '') or config_data.get('gemini_api_key', '')
            if gemini_key:
                os.environ['GEMINI_API_KEY'] = gemini_key
                logger.info("✅ Gemini API Key环境变量已更新")
            elif 'gemini' in config_data or 'gemini_api_key' in config_data:
                # 如果配置中明确设置为空，也清理环境变量
                if 'GEMINI_API_KEY' in os.environ:
                    del os.environ['GEMINI_API_KEY']
                logger.info("✅ Gemini API Key环境变量已清理")
            
            # 更新DashScope API Key - 优先从嵌套结构获取
            dashscope_key = config_data.get('dashscope', {}).get('apiKey', '') or config_data.get('dashscope_api_key', '')
            if dashscope_key:
                os.environ['DASHSCOPE_API_KEY'] = dashscope_key
                logger.info("✅ DashScope API Key环境变量已更新")
            elif 'dashscope' in config_data or 'dashscope_api_key' in config_data:
                if 'DASHSCOPE_API_KEY' in os.environ:
                    del os.environ['DASHSCOPE_API_KEY']
                logger.info("✅ DashScope API Key环境变量已清理")
            
            # 更新智谱AI API Key - 优先从嵌套结构获取
            zhipu_key = config_data.get('zhipu', {}).get('apiKey', '') or config_data.get('zhipu_api_key', '')
            if zhipu_key:
                os.environ['ZHIPU_API_KEY'] = zhipu_key
                logger.info("✅ 智谱AI API Key环境变量已更新")
            elif 'zhipu' in config_data or 'zhipu_api_key' in config_data:
                if 'ZHIPU_API_KEY' in os.environ:
                    del os.environ['ZHIPU_API_KEY']
                logger.info("✅ 智谱AI API Key环境变量已清理")
            
            logger.info("✅ 环境变量更新完成")
            
        except Exception as e:
            logger.error(f"更新环境变量失败: {e}")
    
    def _sync_service_configs(self, config_data: Dict[str, Any]):
        """同步更新相关服务的配置"""
        try:
            # 同步智谱AI服务配置
            if 'zhipu_api_key' in config_data:
                try:
                    from services.zhipu_service import zhipu_service
                    zhipu_service.reload_config()
                    logger.info("✅ 智谱AI服务配置已同步")
                except Exception as e:
                    logger.warning(f"同步智谱AI服务配置失败: {e}")
            
            logger.info("✅ 服务配置同步完成")
            
        except Exception as e:
            logger.error(f"同步服务配置失败: {e}")
    
    def test_wechat_connection(self) -> Dict[str, Any]:
        """测试微信连接，并保存access_token等信息到配置"""
        try:
            logger.info("开始测试微信API连接")
            # 获取当前配置
            config = self.config_service.load_config()
            logger.info(f"当前完整配置: {config}")
            wechat_config = self.config_service.get_wechat_config()

            # 允许使用请求体中临时传入的appid/appsecret进行测试（未保存也可测试）
            try:
                from flask import request
                payload = request.get_json(silent=True) or {}
                temp_appid = payload.get('appid')
                temp_appsecret = payload.get('appsecret')
                if temp_appid:
                    wechat_config['appid'] = temp_appid
                if temp_appsecret:
                    wechat_config['appsecret'] = temp_appsecret
            except Exception:
                pass
            logger.info(f"微信配置: appid={wechat_config.get('appid', 'None')[:10]}..., appsecret={'已设置' if wechat_config.get('appsecret') else '未设置'}")
            if not wechat_config['appid'] or not wechat_config['appsecret']:
                logger.error(f"微信配置不完整: appid={bool(wechat_config.get('appid'))}, appsecret={bool(wechat_config.get('appsecret'))}")
                return {
                    'success': False,
                    'message': '请先配置微信公众号信息',
                    'debug_info': {
                        'has_appid': bool(wechat_config.get('appid')),
                        'has_appsecret': bool(wechat_config.get('appsecret')),
                        'config_keys': list(config.keys())
                    }
                }
            # 获取access_token
            token_info = self.wechat_service.get_access_token(
                wechat_config['appid'],
                wechat_config['appsecret']
            )
            if token_info and token_info.get('access_token'):
                # 保存access_token等信息到config.json
                config_update = {
                    'wechat_access_token': token_info['access_token'],
                    'wechat_access_token_expires_in': token_info['expires_in'],
                    'wechat_access_token_expire_time': token_info['expire_time'],
                    'wechat_access_token_expire_time_str': token_info['expire_time_str'],
                    'wechat_access_token_update_time': token_info['update_time']
                }
                self.config_service.save_config(config_update)
                logger.info("微信API连接测试成功，access_token已保存到配置")
                return {
                    'success': True,
                    'message': '微信API连接成功，access_token已保存',
                    'data': config_update
                }
            elif token_info and token_info.get('error'):
                # 处理具体的微信API错误
                error_code = token_info.get('error_code', 'unknown')
                error_msg = token_info.get('error_msg', 'unknown error')
                
                # 根据错误码提供更具体的提示
                if error_code == 40164:
                    user_message = f"IP地址未添加到微信公众号白名单。请将当前IP地址添加到公众号的IP白名单中。"
                elif error_code == 40013:
                    user_message = f"AppID无效，请检查AppID是否正确。"
                elif error_code == 40125:
                    user_message = f"AppSecret无效，请检查AppSecret是否正确。"
                else:
                    user_message = f"微信API错误 (错误码: {error_code}): {error_msg}"
                
                logger.error(f"微信API连接测试失败，错误码: {error_code}, 错误信息: {error_msg}")
                return {
                    'success': False,
                    'message': user_message,
                    'error_code': error_code,
                    'error_msg': error_msg
                }
            else:
                logger.error("微信API连接测试失败，未能获取access_token")
                return {
                    'success': False,
                    'message': '微信API连接失败，未能获取access_token，请检查AppID和AppSecret是否正确或IP白名单设置',
                }
        except Exception as e:
            logger.error(f"测试微信连接时发生错误: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'测试失败: {str(e)}'
            }
    
    def test_gemini_connection(self) -> Dict[str, Any]:
        """测试Gemini连接"""
        try:
            logger.info("开始测试Gemini AI连接")
            
            # 获取请求数据
            request_data = request.get_json() or {}
            logger.info(f"测试连接请求数据: {request_data}")
            
            # 优先使用请求中的API密钥，如果没有则从配置文件获取
            api_key = request_data.get('gemini_api_key', '')
            model = request_data.get('gemini_model', '')
            
            if not api_key:
                # 从配置文件获取
                config = self.config_service.load_config()
                logger.info(f"当前完整配置: {config}")
                
                gemini_config = self.config_service.get_gemini_config()
                logger.info(f"Gemini配置: api_key={'已设置' if gemini_config.get('api_key') else '未设置'}, model={gemini_config.get('model', 'None')}")
                
                api_key = gemini_config.get('api_key', '')
                if not model:
                    model = gemini_config.get('model', 'gemini-2.5-flash')
            
            if not api_key:
                logger.error(f"Gemini API密钥未配置")
                return {
                    'success': False,
                    'message': '请先配置Gemini API密钥',
                    'debug_info': {
                        'has_api_key': bool(api_key),
                        'request_data': request_data
                    }
                }
            
            # 如果没有指定模型，使用默认值
            if not model:
                model = 'gemini-2.5-flash'
            
            logger.info(f"Gemini测试参数: api_key={'已设置' if api_key else '未设置'}, model={model}")
            
            # 设置API密钥
            self.gemini_service.set_api_key(api_key)
            
            result = self.gemini_service.test_connection(model)
            
            logger.info(f"Gemini连接测试完整结果: {result}")
            return result
            
        except Exception as e:
            logger.error(f"测试Gemini连接时发生错误: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'测试失败: {str(e)}'
            }
    
    def get_gemini_models(self) -> Dict[str, Any]:
        """获取Gemini可用模型列表"""
        try:
            logger.info("开始获取Gemini可用模型列表")
            
            # 获取当前配置
            config = self.config_service.load_config()
            gemini_config = self.config_service.get_gemini_config()
            
            if not gemini_config['api_key']:
                logger.error("Gemini API密钥未配置")
                return {
                    'success': False,
                    'message': '请先配置Gemini API密钥',
                    'data': {
                        'models': [],
                        'current_model': gemini_config.get('model', 'gemini-2.5-flash')
                    }
                }
            
            # 设置API密钥
            self.gemini_service.set_api_key(gemini_config['api_key'])
            
            # 获取可用模型列表
            models = self.gemini_service.get_available_models()
            
            logger.info(f"成功获取到 {len(models)} 个可用模型")
            return {
                'success': True,
                'message': '模型列表获取成功',
                'data': {
                    'models': models,
                    'current_model': gemini_config.get('model', 'gemini-2.5-flash')
                }
            }
            
        except Exception as e:
            logger.error(f"获取Gemini模型列表时发生错误: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'获取模型列表失败: {str(e)}',
                'data': {
                    'models': [],
                    'current_model': 'gemini-2.5-flash'
                }
            }
    
    def test_deepseek_connection(self) -> Dict[str, Any]:
        """测试DeepSeek连接"""
        try:
            logger.info("开始测试DeepSeek AI连接")
            
            # 获取请求数据
            request_data = request.get_json() or {}
            logger.info(f"测试连接请求数据: {request_data}")
            
            # 优先使用请求中的API密钥，如果没有则从配置文件获取
            api_key = request_data.get('deepseek_api_key', '')
            model = request_data.get('deepseek_model', '')
            
            logger.info(f"从请求获取的API密钥: '{api_key}' (长度: {len(api_key)})")
            logger.info(f"从请求获取的模型: '{model}'")
            
            if not api_key:
                # 从配置文件获取
                config = self.config_service.load_config()
                logger.info(f"当前完整配置: {config}")
                
                deepseek_config = self.config_service.get_deepseek_config()
                logger.info(f"DeepSeek配置: api_key={'已设置' if deepseek_config.get('api_key') else '未设置'}, model={deepseek_config.get('model', 'None')}")
                
                api_key = deepseek_config.get('api_key', '')
                if not model:
                    model = deepseek_config.get('model', 'deepseek-chat')
            
            if not api_key:
                logger.error(f"DeepSeek API密钥未配置")
                return {
                    'success': False,
                    'message': '请先配置DeepSeek API密钥',
                    'debug_info': {
                        'has_api_key': bool(api_key),
                        'request_data': request_data
                    }
                }
            
            # 如果没有指定模型，使用默认值
            if not model:
                model = 'deepseek-chat'
            
            logger.info(f"DeepSeek测试参数: api_key={'已设置' if api_key else '未设置'}, model={model}")
            
            # 设置API密钥
            self.deepseek_service.set_api_key(api_key)
            
            result = self.deepseek_service.test_connection(model)
            
            logger.info(f"DeepSeek连接测试完整结果: {result}")
            return result
            
        except Exception as e:
            logger.error(f"测试DeepSeek连接时发生错误: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'测试失败: {str(e)}'
            }
    
    def get_deepseek_models(self) -> Dict[str, Any]:
        """获取DeepSeek可用模型列表"""
        try:
            logger.info("开始获取DeepSeek可用模型列表")
            
            # 获取当前配置
            config = self.config_service.load_config()
            deepseek_config = self.config_service.get_deepseek_config()
            
            if not deepseek_config['api_key']:
                logger.error("DeepSeek API密钥未配置")
                return {
                    'success': False,
                    'message': '请先配置DeepSeek API密钥',
                    'data': {
                        'models': [],
                        'current_model': deepseek_config.get('model', 'deepseek-chat')
                    }
                }
            
            # 设置API密钥
            self.deepseek_service.set_api_key(deepseek_config['api_key'])
            
            # 获取可用模型列表
            models = self.deepseek_service.get_available_models()
            
            logger.info(f"成功获取到 {len(models)} 个可用模型")
            return {
                'success': True,
                'message': '模型列表获取成功',
                'data': {
                    'models': models,
                    'current_model': deepseek_config.get('model', 'deepseek-chat')
                }
            }
            
        except Exception as e:
            logger.error(f"获取DeepSeek模型列表时发生错误: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'获取模型列表失败: {str(e)}',
                'data': {
                    'models': [],
                    'current_model': 'deepseek-chat'
                }
            }
    
    def get_deepseek_debug_info(self) -> Dict[str, Any]:
        """获取DeepSeek调试信息"""
        try:
            logger.info("开始获取DeepSeek调试信息")
            
            # 获取当前配置
            config = self.config_service.load_config()
            deepseek_config = self.config_service.get_deepseek_config()
            
            if not deepseek_config['api_key']:
                return {
                    'success': False,
                    'message': 'DeepSeek API密钥未配置',
                    'debug_info': {
                        'has_api_key': False,
                        'config_keys': list(config.keys())
                    }
                }
            
            # 设置API密钥
            self.deepseek_service.set_api_key(deepseek_config['api_key'])
            
            # 获取API详细信息
            api_info = self.deepseek_service.get_api_info()
            
            return {
                'success': True,
                'message': '调试信息获取成功',
                'data': {
                    'api_info': api_info,
                    'config': deepseek_config
                }
            }
            
        except Exception as e:
            logger.error(f"获取DeepSeek调试信息时发生错误: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'获取调试信息失败: {str(e)}'
            }
    
    def get_config_status(self) -> Dict[str, Any]:
        """获取配置状态"""
        try:
            status = self.config_service.get_config_status()
            
            return {
                'success': True,
                'data': status,
                'message': '配置状态获取成功'
            }
            
        except Exception as e:
            logger.error(f"获取配置状态时发生错误: {str(e)}")
            return {
                'success': False,
                'message': f'获取配置状态失败: {str(e)}'
            }
    
    def test_dashscope_connection(self) -> Dict[str, Any]:
        """测试阿里云百炼连接"""
        try:
            logger.info("开始测试阿里云百炼连接")
            
            # 获取请求数据
            request_data = request.get_json() or {}
            logger.info(f"测试连接请求数据: {request_data}")
            
            # 优先使用请求中的API密钥，如果没有则从配置文件获取
            api_key = request_data.get('dashscope_api_key', '')
            model = request_data.get('dashscope_model', '')
            
            if not api_key:
                # 从配置文件获取
                config = self.config_service.load_config()
                logger.info(f"当前完整配置: {config}")
                
                dashscope_config = self.config_service.get_dashscope_config()
                logger.info(f"阿里云百炼配置: api_key={'已设置' if dashscope_config.get('api_key') else '未设置'}, model={dashscope_config.get('model', 'None')}")
                
                api_key = dashscope_config.get('api_key', '')
                if not model:
                    model = dashscope_config.get('model', 'qwen-turbo')
            
            if not api_key:
                logger.error(f"阿里云百炼API密钥未配置")
                return {
                    'success': False,
                    'message': '请先配置阿里云百炼API密钥',
                    'debug_info': {
                        'has_api_key': bool(api_key),
                        'request_data': request_data
                    }
                }
            
            # 如果没有指定模型，使用默认值
            if not model:
                model = 'qwen-turbo'
            
            logger.info(f"阿里云百炼测试参数: api_key={'已设置' if api_key else '未设置'}, model={model}")
            
            # 设置API密钥
            self.dashscope_service = DashScopeService(api_key)
            
            result = self.dashscope_service.test_connection(model)
            
            logger.info(f"阿里云百炼连接测试完整结果: {result}")
            return result
            
        except Exception as e:
            logger.error(f"测试阿里云百炼连接时发生错误: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'测试失败: {str(e)}'
            }
    
    def get_dashscope_models(self) -> Dict[str, Any]:
        """获取阿里云百炼可用模型列表"""
        try:
            logger.info("开始获取阿里云百炼可用模型列表")
            
            # 获取当前配置
            config = self.config_service.load_config()
            dashscope_config = self.config_service.get_dashscope_config()
            
            if not dashscope_config['api_key']:
                logger.error("阿里云百炼API密钥未配置")
                return {
                    'success': False,
                    'message': '请先配置阿里云百炼API密钥',
                    'data': {
                        'models': [],
                        'current_model': dashscope_config.get('model', 'qwen-turbo')
                    }
                }
            
            # 设置API密钥
            self.dashscope_service = DashScopeService(dashscope_config['api_key'])
            
            # 获取可用模型列表
            models = self.dashscope_service.get_models()
            
            logger.info(f"成功获取到 {len(models)} 个可用模型")
            return {
                'success': True,
                'message': '模型列表获取成功',
                'data': {
                    'models': models,
                    'current_model': dashscope_config.get('model', 'qwen-turbo')
                }
            }
            
        except Exception as e:
            logger.error(f"获取阿里云百炼模型列表时发生错误: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'获取模型列表失败: {str(e)}',
                'data': {
                    'models': [],
                    'current_model': 'qwen-turbo'
                }
            }
    
    def get_dashscope_debug_info(self) -> Dict[str, Any]:
        """获取阿里云百炼调试信息"""
        try:
            logger.info("开始获取阿里云百炼调试信息")
            
            # 获取当前配置
            config = self.config_service.load_config()
            dashscope_config = self.config_service.get_dashscope_config()
            
            if not dashscope_config['api_key']:
                return {
                    'success': False,
                    'message': '阿里云百炼API密钥未配置',
                    'debug_info': {
                        'has_api_key': False,
                        'config_keys': list(config.keys())
                    }
                }
            
            # 设置API密钥
            self.dashscope_service = DashScopeService(dashscope_config['api_key'])
            
            # 获取API详细信息
            api_info = self.dashscope_service.get_api_info()
            
            return {
                'success': True,
                'message': '调试信息获取成功',
                'data': {
                    'api_info': api_info,
                    'config': dashscope_config
                }
            }
            
        except Exception as e:
            logger.error(f"获取阿里云百炼调试信息时发生错误: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'获取调试信息失败: {str(e)}'
            }
    
    # Pexels连接测试已移除