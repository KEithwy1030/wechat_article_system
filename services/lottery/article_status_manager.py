"""
文章状态管理系统
管理文章从生成到发布的整个生命周期
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
from app_config import setup_logging

logger = setup_logging()

class ArticleStatus(Enum):
    """文章状态枚举"""
    NOT_GENERATED = "not_generated"      # 未生成
    GENERATING = "generating"            # 生成中
    GENERATED = "generated"              # 已生成
    REVIEWING = "reviewing"              # 审核中
    APPROVED = "approved"                # 已审核
    PUBLISHED = "published"              # 已发布
    REJECTED = "rejected"                # 已拒绝
    FAILED = "failed"                    # 生成失败

class ArticleStatusManager:
    """文章状态管理器"""
    
    def __init__(self):
        self.status_cache_folder = "cache/article_status"
        self.status_history_folder = "cache/article_history"
        
        # 确保缓存文件夹存在
        os.makedirs(self.status_cache_folder, exist_ok=True)
        os.makedirs(self.status_history_folder, exist_ok=True)
        
        logger.info("文章状态管理系统初始化完成")
    
    def update_article_status(self, match_id: str, status: ArticleStatus, 
                            metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        更新文章状态
        :param match_id: 比赛ID
        :param status: 新状态
        :param metadata: 附加元数据
        :return: 是否更新成功
        """
        try:
            # 获取当前状态
            current_data = self.get_article_status(match_id)
            
            # 构建新的状态数据
            new_data = {
                'match_id': match_id,
                'status': status.value,
                'updated_at': datetime.now().isoformat(),
                'metadata': metadata or {},
                'status_history': current_data.get('status_history', [])
            }
            
            # 添加状态变更记录
            status_change = {
                'from': current_data.get('status', 'unknown'),
                'to': status.value,
                'changed_at': datetime.now().isoformat(),
                'metadata': metadata or {}
            }
            new_data['status_history'].append(status_change)
            
            # 保存状态
            self._save_status(match_id, new_data)
            
            # 保存历史记录
            self._save_status_history(match_id, status_change)
            
            logger.info(f"文章状态已更新: {match_id} -> {status.value}")
            return True
            
        except Exception as e:
            logger.error(f"更新文章状态失败: {str(e)}")
            return False
    
    def get_article_status(self, match_id: str) -> Dict[str, Any]:
        """
        获取文章状态
        :param match_id: 比赛ID
        :return: 文章状态数据
        """
        try:
            status_file = os.path.join(self.status_cache_folder, f"status_{match_id}.json")
            if os.path.exists(status_file):
                with open(status_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # 返回默认状态
                return {
                    'match_id': match_id,
                    'status': ArticleStatus.NOT_GENERATED.value,
                    'updated_at': datetime.now().isoformat(),
                    'metadata': {},
                    'status_history': []
                }
        except Exception as e:
            logger.error(f"获取文章状态失败: {str(e)}")
            return {
                'match_id': match_id,
                'status': ArticleStatus.NOT_GENERATED.value,
                'updated_at': datetime.now().isoformat(),
                'metadata': {},
                'status_history': [],
                'error': str(e)
            }
    
    def get_articles_by_status(self, status: ArticleStatus) -> List[Dict[str, Any]]:
        """
        根据状态获取文章列表
        :param status: 文章状态
        :return: 文章列表
        """
        try:
            articles = []
            for filename in os.listdir(self.status_cache_folder):
                if filename.startswith('status_') and filename.endswith('.json'):
                    match_id = filename.replace('status_', '').replace('.json', '')
                    article_data = self.get_article_status(match_id)
                    if article_data.get('status') == status.value:
                        articles.append(article_data)
            
            return articles
            
        except Exception as e:
            logger.error(f"根据状态获取文章列表失败: {str(e)}")
            return []
    
    def get_all_articles_status(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        获取所有文章的状态统计
        :return: 按状态分组的文章列表
        """
        try:
            status_groups = {}
            
            # 初始化所有状态组
            for status in ArticleStatus:
                status_groups[status.value] = []
            
            # 遍历所有状态文件
            for filename in os.listdir(self.status_cache_folder):
                if filename.startswith('status_') and filename.endswith('.json'):
                    match_id = filename.replace('status_', '').replace('.json', '')
                    article_data = self.get_article_status(match_id)
                    status = article_data.get('status', ArticleStatus.NOT_GENERATED.value)
                    status_groups[status].append(article_data)
            
            return status_groups
            
        except Exception as e:
            logger.error(f"获取所有文章状态统计失败: {str(e)}")
            return {}
    
    def get_status_statistics(self) -> Dict[str, Any]:
        """
        获取状态统计信息
        :return: 统计信息
        """
        try:
            all_articles = self.get_all_articles_status()
            
            statistics = {
                'total_articles': 0,
                'status_counts': {},
                'status_percentages': {},
                'generated_at': datetime.now().isoformat()
            }
            
            # 计算各状态数量
            for status, articles in all_articles.items():
                count = len(articles)
                statistics['status_counts'][status] = count
                statistics['total_articles'] += count
            
            # 计算百分比
            total = statistics['total_articles']
            if total > 0:
                for status, count in statistics['status_counts'].items():
                    statistics['status_percentages'][status] = round(count / total * 100, 2)
            
            return statistics
            
        except Exception as e:
            logger.error(f"获取状态统计信息失败: {str(e)}")
            return {'error': str(e)}
    
    def get_article_status_history(self, match_id: str) -> List[Dict[str, Any]]:
        """
        获取文章状态变更历史
        :param match_id: 比赛ID
        :return: 状态变更历史列表
        """
        try:
            history_file = os.path.join(self.status_history_folder, f"history_{match_id}.json")
            if os.path.exists(history_file):
                with open(history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return []
        except Exception as e:
            logger.error(f"获取文章状态历史失败: {str(e)}")
            return []
    
    def can_transition_to(self, current_status: ArticleStatus, target_status: ArticleStatus) -> bool:
        """
        检查状态转换是否合法
        :param current_status: 当前状态
        :param target_status: 目标状态
        :return: 是否可以转换
        """
        # 定义合法的状态转换
        valid_transitions = {
            ArticleStatus.NOT_GENERATED: [ArticleStatus.GENERATING, ArticleStatus.FAILED],
            ArticleStatus.GENERATING: [ArticleStatus.GENERATED, ArticleStatus.FAILED],
            ArticleStatus.GENERATED: [ArticleStatus.REVIEWING, ArticleStatus.REJECTED],
            ArticleStatus.REVIEWING: [ArticleStatus.APPROVED, ArticleStatus.REJECTED],
            ArticleStatus.APPROVED: [ArticleStatus.PUBLISHED, ArticleStatus.REJECTED],
            ArticleStatus.PUBLISHED: [],  # 已发布状态不可再转换
            ArticleStatus.REJECTED: [ArticleStatus.GENERATING, ArticleStatus.GENERATED],
            ArticleStatus.FAILED: [ArticleStatus.GENERATING, ArticleStatus.NOT_GENERATED]
        }
        
        return target_status in valid_transitions.get(current_status, [])
    
    def _save_status(self, match_id: str, status_data: Dict[str, Any]):
        """保存状态数据"""
        try:
            status_file = os.path.join(self.status_cache_folder, f"status_{match_id}.json")
            with open(status_file, 'w', encoding='utf-8') as f:
                json.dump(status_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存状态数据失败: {str(e)}")
            raise
    
    def _save_status_history(self, match_id: str, status_change: Dict[str, Any]):
        """保存状态变更历史"""
        try:
            history_file = os.path.join(self.status_history_folder, f"history_{match_id}.json")
            
            # 读取现有历史
            history = []
            if os.path.exists(history_file):
                with open(history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            
            # 添加新的变更记录
            history.append(status_change)
            
            # 保存历史（最多保留100条记录）
            if len(history) > 100:
                history = history[-100:]
            
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"保存状态变更历史失败: {str(e)}")
    
    def cleanup_old_data(self, days: int = 30):
        """
        清理旧数据
        :param days: 保留天数
        """
        try:
            import time
            current_time = time.time()
            cutoff_time = current_time - (days * 24 * 60 * 60)
            
            cleaned_files = 0
            
            # 清理状态文件
            for filename in os.listdir(self.status_cache_folder):
                file_path = os.path.join(self.status_cache_folder, filename)
                if os.path.getmtime(file_path) < cutoff_time:
                    os.remove(file_path)
                    cleaned_files += 1
            
            # 清理历史文件
            for filename in os.listdir(self.status_history_folder):
                file_path = os.path.join(self.status_history_folder, filename)
                if os.path.getmtime(file_path) < cutoff_time:
                    os.remove(file_path)
                    cleaned_files += 1
            
            logger.info(f"清理完成，删除了 {cleaned_files} 个旧文件")
            
        except Exception as e:
            logger.error(f"清理旧数据失败: {str(e)}")

# 创建全局实例
article_status_manager = ArticleStatusManager()
