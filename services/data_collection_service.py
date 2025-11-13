"""
数据搜集服务 - 管理AI自动搜集资料的状态和进度
"""
import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class DataCollectionService:
    """数据搜集服务"""
    
    def __init__(self):
        self.collection_status = {
            "is_running": False,
            "current_task": None,
            "progress": 0,
            "total_tasks": 0,
            "start_time": None,
            "last_update": None,
            "error_message": None
        }
        
        self.data_sources = {
            "deepseek_web": {
                "name": "DeepSeek联网搜索",
                "status": "ready",  # ready, running, success, error
                "last_run": None,
                "success_count": 0,
                "error_count": 0,
                "avg_response_time": 0
            },
            "screenshot_ai": {
                "name": "截图AI识别",
                "status": "ready",
                "last_run": None,
                "success_count": 0,
                "error_count": 0,
                "avg_response_time": 0
            },
            "sporttery_scraper": {
                "name": "竞彩官网爬虫",
                "status": "ready",
                "last_run": None,
                "success_count": 0,
                "error_count": 0,
                "avg_response_time": 0
            }
        }
        
        self.collection_schedule = []
        self.collection_history = []
        
        # 初始化默认搜集计划
        self._init_default_schedule()
    
    def _init_default_schedule(self):
        """初始化默认搜集计划"""
        now = datetime.now()
        
        # 每天上午9点搜集当日比赛
        daily_time = now.replace(hour=9, minute=0, second=0, microsecond=0)
        if daily_time <= now:
            daily_time += timedelta(days=1)
        
        self.collection_schedule = [
            {
                "id": "daily_morning",
                "name": "每日上午搜集",
                "description": "搜集当日所有比赛的基础信息",
                "trigger_time": daily_time.strftime("%H:%M"),
                "data_sources": ["sporttery_scraper", "deepseek_web"],
                "target_matches": "当日所有比赛",
                "enabled": True,
                "last_run": None,
                "next_run": daily_time.strftime("%Y-%m-%d %H:%M:%S")
            },
            {
                "id": "match_analysis",
                "name": "比赛深度分析",
                "description": "对重点比赛进行深度数据搜集",
                "trigger_time": "14:00",
                "data_sources": ["screenshot_ai", "deepseek_web"],
                "target_matches": "重点比赛",
                "enabled": True,
                "last_run": None,
                "next_run": (now + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
            }
        ]
    
    def get_collection_status(self) -> Dict:
        """获取搜集状态"""
        return {
            "status": self.collection_status,
            "data_sources": self.data_sources,
            "schedule": self.collection_schedule,
            "recent_history": self.collection_history[-10:] if self.collection_history else []
        }
    
    def start_collection(self, task_name: str, data_sources: List[str]) -> bool:
        """开始数据搜集"""
        if self.collection_status["is_running"]:
            return False
        
        self.collection_status.update({
            "is_running": True,
            "current_task": task_name,
            "progress": 0,
            "total_tasks": len(data_sources),
            "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "error_message": None
        })
        
        # 更新数据源状态
        for source in data_sources:
            if source in self.data_sources:
                self.data_sources[source]["status"] = "running"
                self.data_sources[source]["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        logger.info(f"开始数据搜集任务: {task_name}, 数据源: {data_sources}")
        return True
    
    def update_progress(self, progress: int, message: str = None):
        """更新搜集进度"""
        self.collection_status["progress"] = progress
        self.collection_status["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if message:
            logger.info(f"数据搜集进度: {progress}% - {message}")
    
    def complete_collection(self, success: bool, data_count: int = 0, error_message: str = None):
        """完成数据搜集"""
        self.collection_status.update({
            "is_running": False,
            "progress": 100 if success else 0,
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "error_message": error_message
        })
        
        # 记录搜集历史
        history_entry = {
            "id": f"collection_{int(time.time())}",
            "task_name": self.collection_status["current_task"],
            "start_time": self.collection_status["start_time"],
            "end_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "success": success,
            "data_count": data_count,
            "error_message": error_message,
            "data_sources": [source for source, info in self.data_sources.items() if info["status"] == "running"]
        }
        
        self.collection_history.append(history_entry)
        
        # 更新数据源状态
        for source, info in self.data_sources.items():
            if info["status"] == "running":
                info["status"] = "success" if success else "error"
                if success:
                    info["success_count"] += 1
                else:
                    info["error_count"] += 1
        
        logger.info(f"数据搜集完成: {self.collection_status['current_task']}, 成功: {success}, 数据量: {data_count}")
    
    def get_upcoming_matches(self) -> List[Dict]:
        """获取即将进行的比赛（用于AI识别）"""
        # 这里应该从竞彩数据服务获取
        # 暂时返回模拟数据
        return [
            {
                "match_id": "wed_001",
                "home_team": "川崎前锋",
                "away_team": "柏太阳神",
                "match_time": "2025-10-09 18:00:00",
                "league": "日联赛杯",
                "priority": "high",  # high, medium, low
                "data_collected": False
            },
            {
                "match_id": "thu_001", 
                "home_team": "英格兰",
                "away_team": "威尔士",
                "match_time": "2025-10-10 20:00:00",
                "league": "国际赛",
                "priority": "high",
                "data_collected": False
            }
        ]
    
    def simulate_collection_process(self):
        """模拟数据搜集过程（用于演示）"""
        if not self.collection_status["is_running"]:
            return
        
        # 模拟搜集进度
        current_progress = self.collection_status["progress"]
        if current_progress < 100:
            new_progress = min(current_progress + 10, 100)
            self.update_progress(new_progress, f"正在搜集数据... {new_progress}%")
            
            if new_progress >= 100:
                # 模拟搜集完成
                self.complete_collection(True, 15, None)
    
    def trigger_auto_collection(self) -> bool:
        """触发自动搜集"""
        upcoming_matches = self.get_upcoming_matches()
        high_priority_matches = [m for m in upcoming_matches if m["priority"] == "high"]
        
        if not high_priority_matches:
            return False
        
        # 开始搜集重点比赛数据
        return self.start_collection(
            f"搜集{len(high_priority_matches)}场重点比赛数据",
            ["sporttery_scraper", "deepseek_web", "screenshot_ai"]
        )

# 全局实例
data_collection_service = DataCollectionService()
