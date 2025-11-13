"""
配置服务模块
处理应用配置的加载、保存和验证
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import threading
import time

logger = logging.getLogger(__name__)

class ConfigService:
    """配置服务类"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.default_config = self._get_default_config()
        self._start_token_monitor_thread()
        logger.info(f"配置服务初始化完成，配置文件: {self.config_file}")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "wechat_appid": "",
            "wechat_appsecret": "",
            "gemini_api_key": "",
            "gemini_model": "gemini-2.5-flash",
            "deepseek_api_key": "",
            "deepseek_model": "deepseek-chat",
            "dashscope_api_key": "",
            "dashscope_model": "qwen-turbo",
            "zhipu_api_key": "",
            "zhipu_model": "glm-4.5-air",
            # Pexels和Coze配置已移除
            "image_model": "gemini",  # 默认生图模型
            "author": "AI笔记",
            "content_source_url": "",
            "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "updated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def _deep_merge(self, base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
        """
        深度合并字典，避免嵌套字典被覆盖
        递归合并嵌套字典，保留未更新的字段
        """
        result = base.copy()
        
        for key, value in update.items():
            # 如果两个值都是字典，递归合并
            if (key in result and 
                isinstance(result[key], dict) and 
                isinstance(value, dict)):
                result[key] = self._deep_merge(result[key], value)
            else:
                # 否则直接更新（包括列表、字符串等）
                result[key] = value
        
        return result
    
    def _backup_config(self) -> bool:
        """备份当前配置文件"""
        try:
            if not os.path.exists(self.config_file):
                return True  # 文件不存在，无需备份
            
            # 获取配置文件的绝对路径
            config_abs_path = os.path.abspath(self.config_file)
            config_dir = os.path.dirname(config_abs_path)
            
            # 创建备份目录（在配置文件同目录下）
            backup_dir = os.path.join(config_dir, 'backups')
            os.makedirs(backup_dir, exist_ok=True)
            
            # 生成备份文件名（带时间戳）
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = os.path.join(backup_dir, f'config_backup_{timestamp}.json')
            
            # 复制文件
            import shutil
            shutil.copy2(config_abs_path, backup_file)
            
            # 只保留最近10个备份
            backup_files = sorted(
                [f for f in os.listdir(backup_dir) if f.startswith('config_backup_') and f.endswith('.json')],
                reverse=True
            )
            for old_backup in backup_files[10:]:
                try:
                    os.remove(os.path.join(backup_dir, old_backup))
                except Exception:
                    pass
            
            logger.info(f"配置已备份到: {backup_file}")
            return True
        except Exception as e:
            logger.warning(f"配置备份失败: {str(e)}")
            return False  # 备份失败不影响保存操作
    
    def load_config(self) -> Dict[str, Any]:
        """加载配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    logger.info("从文件加载配置成功")
                    
                # 使用深度合并，确保嵌套配置正确合并
                merged_config = self._deep_merge(self.default_config.copy(), config)
                
                return merged_config
            else:
                logger.info("配置文件不存在，使用默认配置")
                return self.default_config.copy()
                
        except Exception as e:
            logger.error(f"加载配置时发生错误: {str(e)}")
            return self.default_config.copy()
    
    def save_config(self, config_data: Dict[str, Any]) -> bool:
        """
        保存配置
        使用深度合并，避免嵌套配置被覆盖
        """
        try:
            # 验证配置数据
            if not self._validate_config(config_data):
                logger.error("配置数据验证失败")
                return False
            
            # 备份当前配置
            self._backup_config()
            
            # 加载现有配置
            current_config = self.load_config()
            
            # 使用深度合并更新配置，避免嵌套字典被覆盖
            merged_config = self._deep_merge(current_config, config_data)
            
            # 更新修改时间
            merged_config["updated_at"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 如果是首次创建，设置创建时间
            if "created_at" not in merged_config or not merged_config.get("created_at"):
                merged_config["created_at"] = merged_config["updated_at"]
            
            # 保存到文件
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(merged_config, f, ensure_ascii=False, indent=4)
            
            logger.info("配置保存成功（已使用深度合并）")
            return True
            
        except Exception as e:
            logger.error(f"保存配置时发生错误: {str(e)}")
            return False
    
    def _validate_config(self, config_data: Dict[str, Any]) -> bool:
        """验证配置数据"""
        # 所有配置字段都是可选的，支持分步配置
        required_fields = []
        
        for field in required_fields:
            if field in config_data:
                value = config_data[field]
                if not isinstance(value, str) or not value.strip():
                    logger.error(f"必填字段 {field} 不能为空")
                    return False
        
        # 验证模型名称
        if 'gemini_model' in config_data:
            valid_models = ['gemini-2.5-flash', 'gemini-2.5-pro']
            if config_data['gemini_model'] not in valid_models:
                logger.warning(f"未知的Gemini模型: {config_data['gemini_model']}")
        
        return True
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """获取单个配置值"""
        try:
            config = self.load_config()
            return config.get(key, default)
        except Exception as e:
            logger.error(f"获取配置值时发生错误: {str(e)}")
            return default
    
    def set_config_value(self, key: str, value: Any) -> bool:
        """设置单个配置值"""
        try:
            config = self.load_config()
            config[key] = value
            return self.save_config(config)
        except Exception as e:
            logger.error(f"设置配置值时发生错误: {str(e)}")
            return False
    
    def get_wechat_config(self) -> Dict[str, str]:
        """获取微信配置"""
        config = self.load_config()
        # 优先从嵌套结构获取，如果不存在则从扁平结构获取（向后兼容）
        wechat_config = config.get('wechat', {})
        return {
            'appid': wechat_config.get('appId', '') or config.get('wechat_appid', ''),
            'appsecret': wechat_config.get('appSecret', '') or config.get('wechat_appsecret', '')
        }
    
    def get_gemini_config(self) -> Dict[str, str]:
        """获取Gemini配置"""
        config = self.load_config()
        # 优先从嵌套结构获取，如果不存在则从扁平结构获取（向后兼容）
        gemini_config = config.get('gemini', {})
        return {
            'api_key': gemini_config.get('apiKey', '') or config.get('gemini_api_key', ''),
            'model': gemini_config.get('model', '') or config.get('gemini_model', 'gemini-2.5-flash')
        }
    
    def get_deepseek_config(self) -> Dict[str, str]:
        """获取DeepSeek配置"""
        config = self.load_config()
        # 优先从嵌套结构获取，如果不存在则从扁平结构获取（向后兼容）
        deepseek_config = config.get('deepseek', {})
        return {
            'api_key': deepseek_config.get('apiKey', '') or config.get('deepseek_api_key', ''),
            'model': deepseek_config.get('model', '') or config.get('deepseek_model', 'deepseek-chat')
        }
    
    def get_dashscope_config(self) -> Dict[str, str]:
        """获取阿里云百炼配置"""
        config = self.load_config()
        # 优先从嵌套结构获取，如果不存在则从扁平结构获取（向后兼容）
        dashscope_config = config.get('dashscope', {})
        return {
            'api_key': dashscope_config.get('apiKey', '') or config.get('dashscope_api_key', ''),
            'model': dashscope_config.get('model', '') or config.get('dashscope_model', 'qwen-turbo')
        }
    
    def get_zhipu_config(self) -> Dict[str, str]:
        """获取智谱AI配置"""
        config = self.load_config()
        # 优先从嵌套结构获取，如果不存在则从扁平结构获取（向后兼容）
        zhipu_config = config.get('zhipu', {})
        return {
            'api_key': zhipu_config.get('apiKey', '') or config.get('zhipu_api_key', ''),
            'model': zhipu_config.get('model', '') or config.get('zhipu_model', 'glm-4.5-air')
        }
    
    # Pexels和Coze配置方法已移除
    
    def get_author_config(self) -> Dict[str, str]:
        """获取作者配置"""
        config = self.load_config()
        return {
            'author': config.get('author', 'AI笔记'),
            'content_source_url': config.get('content_source_url', '')
        }
    
    def is_wechat_configured(self) -> bool:
        """检查微信是否已配置"""
        wechat_config = self.get_wechat_config()
        return bool(wechat_config['appid'] and wechat_config['appsecret'])
    
    def is_gemini_configured(self) -> bool:
        """检查Gemini是否已配置"""
        gemini_config = self.get_gemini_config()
        return bool(gemini_config['api_key'])
    
    def is_deepseek_configured(self) -> bool:
        """检查DeepSeek是否已配置"""
        deepseek_config = self.get_deepseek_config()
        return bool(deepseek_config['api_key'])
    
    def is_dashscope_configured(self) -> bool:
        """检查阿里云百炼是否已配置"""
        dashscope_config = self.get_dashscope_config()
        return bool(dashscope_config['api_key'])
    
    def is_zhipu_configured(self) -> bool:
        """检查智谱AI是否已配置"""
        zhipu_config = self.get_zhipu_config()
        return bool(zhipu_config['api_key'])
    
    # Pexels配置检查已移除
    
    def get_config_status(self) -> Dict[str, bool]:
        """获取配置状态"""
        return {
            'wechat_configured': self.is_wechat_configured(),
            'gemini_configured': self.is_gemini_configured(),
            'deepseek_configured': self.is_deepseek_configured(),
            'dashscope_configured': self.is_dashscope_configured(),
            'zhipu_configured': self.is_zhipu_configured(),
            # Pexels配置状态已移除
            'config_file_exists': os.path.exists(self.config_file)
        }

    def _start_token_monitor_thread(self):
        def monitor():
            while True:
                try:
                    config = self.load_config()
                    access_token = config.get('wechat_access_token', '')
                    expire_time = int(config.get('wechat_access_token_expire_time', 0))
                    now = int(time.time())
                    remain = expire_time - now if expire_time else None
                    try:
                        now_str = datetime.fromtimestamp(now).strftime('%Y-%m-%d %H:%M:%S')
                    except Exception:
                        now_str = str(now)
                    try:
                        expire_str = datetime.fromtimestamp(expire_time).strftime('%Y-%m-%d %H:%M:%S') if expire_time else '无'
                    except Exception:
                        expire_str = str(expire_time)
                    # logger.info(f"access_token检查: 当前时间{now_str}, 过期时间{expire_str}, 剩余{remain}秒")
                    # 如果token快到期（2分钟内）或已过期/不存在，则刷新
                    if (access_token and expire_time and remain <= 120) or (not access_token or not expire_time or remain <= 0):
                        logger.info("access_token即将过期或已过期，自动刷新...")
                        wechat_config = self.get_wechat_config()
                        if wechat_config.get('appid') and wechat_config.get('appsecret'):
                            try:
                                from services.wechat_service import WeChatService
                                ws = WeChatService()
                                token_info = ws.get_access_token(
                                    wechat_config['appid'],
                                    wechat_config['appsecret']
                                )
                                if token_info and token_info.get('access_token'):
                                    self.save_config({
                                        'wechat_access_token': token_info['access_token'],
                                        'wechat_access_token_expires_in': token_info['expires_in'],
                                        'wechat_access_token_expire_time': token_info['expire_time'],
                                        'wechat_access_token_expire_time_str': token_info['expire_time_str'],
                                        'wechat_access_token_update_time': token_info['update_time']
                                    })
                                    logger.info("access_token自动刷新成功")
                                else:
                                    logger.warning("自动刷新access_token失败")
                            except Exception as e:
                                logger.error(f"自动刷新access_token时异常: {str(e)}")
                        else:
                            logger.warning("未配置appid/appsecret，无法自动刷新access_token")
                    # 每30秒检查一次
                    time.sleep(30)
                except Exception as e:
                    logger.error(f"access_token自动刷新线程异常: {str(e)}")
                    time.sleep(60)

# 创建全局单例实例
config_service = ConfigService()