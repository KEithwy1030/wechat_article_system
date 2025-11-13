"""
系统运行日志记录服务
记录系统工作状态，特别是快速预测任务的执行情况
"""

import logging
import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class SystemLogger:
    """系统运行日志记录器"""
    
    def __init__(self, db_path: str = "system.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """初始化日志数据库表"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建系统运行日志表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_runtime_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_type TEXT NOT NULL,
                    task_name TEXT,
                    match_code TEXT,
                    status TEXT NOT NULL,
                    message TEXT,
                    error_type TEXT,
                    error_details TEXT,
                    created_at TEXT NOT NULL,
                    metadata TEXT
                )
            ''')
            
            # 创建索引以提高查询性能
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_task_type ON system_runtime_logs(task_type)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_created_at ON system_runtime_logs(created_at)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_match_code ON system_runtime_logs(match_code)
            ''')
            
            conn.commit()
            conn.close()
            
            logger.info("系统运行日志数据库初始化完成")
            
        except Exception as e:
            logger.error(f"初始化系统运行日志数据库失败: {e}")
    
    def log_quick_prediction(
        self,
        match_code: str,
        status: str,
        message: str,
        error_type: Optional[str] = None,
        error_details: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """
        记录快速预测任务日志
        
        Args:
            match_code: 比赛编号
            status: 状态（success, failed, skipped, error）
            message: 日志消息
            error_type: 错误类型（如：network_error, api_error, web_search_not_used等）
            error_details: 错误详情
            metadata: 额外元数据
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO system_runtime_logs 
                (task_type, task_name, match_code, status, message, error_type, error_details, created_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                'quick_prediction',
                '快速预测任务',
                match_code,
                status,
                message,
                error_type,
                error_details,
                datetime.now().isoformat(),
                json.dumps(metadata, ensure_ascii=False) if metadata else None
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"记录快速预测日志失败: {e}")
    
    def log_task_start(self, task_type: str, task_name: str, metadata: Optional[Dict] = None):
        """记录任务开始"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO system_runtime_logs 
                (task_type, task_name, status, message, created_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                task_type,
                task_name,
                'started',
                f'{task_name}开始执行',
                datetime.now().isoformat(),
                json.dumps(metadata, ensure_ascii=False) if metadata else None
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"记录任务开始日志失败: {e}")
    
    def log_task_end(self, task_type: str, task_name: str, status: str = 'completed', message: str = None, metadata: Optional[Dict] = None):
        """记录任务结束"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO system_runtime_logs 
                (task_type, task_name, status, message, created_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                task_type,
                task_name,
                status,
                message or f'{task_name}执行完成',
                datetime.now().isoformat(),
                json.dumps(metadata, ensure_ascii=False) if metadata else None
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"记录任务结束日志失败: {e}")
    
    def get_logs(
        self,
        task_type: Optional[str] = None,
        match_code: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """
        获取运行日志
        
        Args:
            task_type: 任务类型筛选
            match_code: 比赛编号筛选
            status: 状态筛选
            limit: 返回数量限制
            offset: 偏移量
        
        Returns:
            日志列表
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 构建查询条件
            conditions = []
            params = []
            
            if task_type:
                conditions.append('task_type = ?')
                params.append(task_type)
            
            if match_code:
                conditions.append('match_code = ?')
                params.append(match_code)
            
            if status:
                conditions.append('status = ?')
                params.append(status)
            
            where_clause = 'WHERE ' + ' AND '.join(conditions) if conditions else ''
            
            query = f'''
                SELECT * FROM system_runtime_logs
                {where_clause}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            '''
            
            params.extend([limit, offset])
            cursor.execute(query, params)
            
            rows = cursor.fetchall()
            logs = []
            for row in rows:
                log = dict(row)
                # 解析metadata JSON
                if log.get('metadata'):
                    try:
                        log['metadata'] = json.loads(log['metadata'])
                    except:
                        log['metadata'] = {}
                logs.append(log)
            
            conn.close()
            return logs
            
        except Exception as e:
            logger.error(f"获取运行日志失败: {e}")
            return []
    
    def get_log_stats(self, days: int = 7) -> Dict:
        """获取日志统计信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 计算日期范围
            from datetime import timedelta
            start_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # 统计各状态数量
            cursor.execute('''
                SELECT status, COUNT(*) as count
                FROM system_runtime_logs
                WHERE created_at >= ?
                GROUP BY status
            ''', (start_date,))
            
            status_stats = {row[0]: row[1] for row in cursor.fetchall()}
            
            # 统计错误类型
            cursor.execute('''
                SELECT error_type, COUNT(*) as count
                FROM system_runtime_logs
                WHERE created_at >= ? AND error_type IS NOT NULL
                GROUP BY error_type
            ''', (start_date,))
            
            error_stats = {row[0]: row[1] for row in cursor.fetchall()}
            
            conn.close()
            
            return {
                'status_stats': status_stats,
                'error_stats': error_stats,
                'days': days
            }
            
        except Exception as e:
            logger.error(f"获取日志统计失败: {e}")
            return {
                'status_stats': {},
                'error_stats': {},
                'days': days
            }


# 全局实例
system_logger = SystemLogger()

