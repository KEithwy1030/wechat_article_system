"""
单场比赛预测队列管理器（方案A：简单队列）
按顺序处理任务，超过限制时提示用户等待
"""
import threading
import logging
from typing import Dict, Optional
from collections import deque
from datetime import datetime

logger = logging.getLogger(__name__)

class SingleMatchQueue:
    """单场比赛预测队列管理器"""
    
    def __init__(self):
        self._lock = threading.Lock()
        self.quick_prediction_queue = deque()  # 快速预测队列
        self.deep_analysis_queue = deque()    # 深度分析队列
        self.quick_prediction_running = False  # 是否有快速预测正在运行
        self.deep_analysis_running = False    # 是否有深度分析正在运行
        self.max_quick_concurrent = 3  # 快速预测最多3场
        self.max_deep_concurrent = 2  # 深度分析最多2场
        self.current_quick_count = 0   # 当前快速预测数量
        self.current_deep_count = 0   # 当前深度分析数量
    
    def can_add_quick_prediction(self):
        """
        检查是否可以添加快速预测任务
        返回: (是否可以添加, 提示信息)
        """
        with self._lock:
            if self.current_quick_count >= self.max_quick_concurrent:
                return False, f"当前有 {self.current_quick_count} 场快速预测正在处理，最多支持 {self.max_quick_concurrent} 场并发，请稍后重试"
            return True, ""
    
    def can_add_deep_analysis(self):
        """
        检查是否可以添加深度分析任务
        返回: (是否可以添加, 提示信息)
        """
        with self._lock:
            if self.current_deep_count >= self.max_deep_concurrent:
                return False, f"当前有 {self.current_deep_count} 场深度分析正在处理，最多支持 {self.max_deep_concurrent} 场并发，请稍后重试"
            return True, ""
    
    def add_quick_prediction(self, match_code: str) -> bool:
        """添加快速预测任务到队列"""
        logger.info(f"[队列] 尝试添加快速预测任务: {match_code}")
        try:
            with self._lock:
                logger.info(f"[队列] 获取锁成功: {match_code}")
                # 直接检查，避免重复获取锁（can_add_quick_prediction内部也会获取锁，会导致死锁）
                if self.current_quick_count >= self.max_quick_concurrent:
                    message = f"当前有 {self.current_quick_count} 场快速预测正在处理，最多支持 {self.max_quick_concurrent} 场并发，请稍后重试"
                    logger.warning(f"[队列] 无法添加快速预测任务: {match_code}, 原因: {message}")
                    return False
                
                self.quick_prediction_queue.append({
                    'match_code': match_code,
                    'added_at': datetime.now().isoformat()
                })
                self.current_quick_count += 1
                logger.info(f"[队列] 添加快速预测任务成功: {match_code}，当前队列长度: {len(self.quick_prediction_queue)}, 当前计数: {self.current_quick_count}")
                return True
        except Exception as e:
            logger.error(f"[队列] 添加快速预测任务异常: {match_code} - {e}", exc_info=True)
            return False
    
    def add_deep_analysis(self, match_code: str) -> bool:
        """添加深度分析任务到队列"""
        with self._lock:
            # 直接检查，避免重复获取锁（can_add_deep_analysis内部也会获取锁，会导致死锁）
            if self.current_deep_count >= self.max_deep_concurrent:
                return False
            
            self.deep_analysis_queue.append({
                'match_code': match_code,
                'added_at': datetime.now().isoformat()
            })
            self.current_deep_count += 1
            logger.info(f"添加深度分析任务: {match_code}，当前队列长度: {len(self.deep_analysis_queue)}")
            return True
    
    def finish_quick_prediction(self, match_code: str):
        """完成快速预测任务"""
        with self._lock:
            if self.current_quick_count > 0:
                self.current_quick_count -= 1
            logger.info(f"完成快速预测任务: {match_code}，当前剩余: {self.current_quick_count}")
    
    def finish_deep_analysis(self, match_code: str):
        """完成深度分析任务"""
        with self._lock:
            if self.current_deep_count > 0:
                self.current_deep_count -= 1
            logger.info(f"完成深度分析任务: {match_code}，当前剩余: {self.current_deep_count}")
    
    def get_status(self) -> Dict:
        """获取队列状态"""
        with self._lock:
            return {
                'quick_prediction': {
                    'current': self.current_quick_count,
                    'max': self.max_quick_concurrent,
                    'queue_length': len(self.quick_prediction_queue)
                },
                'deep_analysis': {
                    'current': self.current_deep_count,
                    'max': self.max_deep_concurrent,
                    'queue_length': len(self.deep_analysis_queue)
                }
            }

# 全局单例
single_match_queue = SingleMatchQueue()

