"""
AI服务统一管理器
解决重复实例化问题，提供单例模式的AI服务访问
"""

import logging
from typing import Optional
from services.gemini_service import GeminiService
from services.deepseek_service import DeepSeekService
from services.dashscope_service import DashScopeService

logger = logging.getLogger(__name__)

class AIServiceManager:
    """AI服务统一管理器 - 单例模式"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._gemini_service = None
            self._deepseek_service = None
            self._dashscope_service = None
            self._initialized = True
            logger.info("AI服务管理器初始化完成")
    
    @property
    def gemini(self) -> GeminiService:
        """获取Gemini服务实例"""
        if self._gemini_service is None:
            self._gemini_service = GeminiService()
            logger.info("Gemini服务实例已创建")
        return self._gemini_service
    
    @property
    def deepseek(self) -> DeepSeekService:
        """获取DeepSeek服务实例"""
        if self._deepseek_service is None:
            self._deepseek_service = DeepSeekService()
            logger.info("DeepSeek服务实例已创建")
        return self._deepseek_service
    
    @property
    def dashscope(self) -> DashScopeService:
        """获取DashScope服务实例"""
        if self._dashscope_service is None:
            self._dashscope_service = DashScopeService()
            logger.info("DashScope服务实例已创建")
        return self._dashscope_service
    
    def get_service(self, service_name: str):
        """根据名称获取服务"""
        services = {
            'gemini': self.gemini,
            'deepseek': self.deepseek,
            'dashscope': self.dashscope
        }
        return services.get(service_name.lower())

# 全局单例实例
ai_service_manager = AIServiceManager()
