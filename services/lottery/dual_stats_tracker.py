"""
双统计系统 - 分别统计快速预测和深度分析的命中率
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json

logger = logging.getLogger(__name__)

class DualStatsTracker:
    """双统计系统 - 分别统计两种预测的命中率"""
    
    def __init__(self):
        # 使用绝对路径
        import os
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        data_dir = os.path.join(base_dir, 'data')
        os.makedirs(data_dir, exist_ok=True)
        self.stats_db_path = os.path.join(data_dir, "prediction_stats.db")
        self._init_database()
    
    def _init_database(self):
        """初始化统计数据库"""
        try:
            import sqlite3
            
            conn = sqlite3.connect(self.stats_db_path)
            cursor = conn.cursor()
            
            # 快速预测统计表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS quick_prediction_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    match_code TEXT UNIQUE NOT NULL,
                    match_date TEXT NOT NULL,
                    home_team TEXT NOT NULL,
                    away_team TEXT NOT NULL,
                    league TEXT NOT NULL,
                    predicted_scores TEXT NOT NULL,  -- JSON格式
                    actual_score TEXT,
                    is_hit BOOLEAN,
                    hit_type TEXT,  -- exact, partial, miss
                    confidence REAL,
                    predicted_at TEXT NOT NULL,
                    result_updated_at TEXT,
                    created_at TEXT NOT NULL
                )
            ''')
            
            # 深度分析统计表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS deep_analysis_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    match_code TEXT UNIQUE NOT NULL,
                    match_date TEXT NOT NULL,
                    home_team TEXT NOT NULL,
                    away_team TEXT NOT NULL,
                    league TEXT NOT NULL,
                    predicted_scores TEXT NOT NULL,  -- JSON格式
                    actual_score TEXT,
                    is_hit BOOLEAN,
                    hit_type TEXT,  -- exact, partial, miss
                    materials_quality INTEGER,
                    article_id INTEGER,
                    predicted_at TEXT NOT NULL,
                    result_updated_at TEXT,
                    created_at TEXT NOT NULL
                )
            ''')
            
            # 总体统计表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS overall_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stat_date TEXT NOT NULL,
                    prediction_type TEXT NOT NULL,  -- 'quick' 或 'deep'
                    total_predictions INTEGER DEFAULT 0,
                    hit_count INTEGER DEFAULT 0,
                    exact_hits INTEGER DEFAULT 0,
                    partial_hits INTEGER DEFAULT 0,
                    miss_count INTEGER DEFAULT 0,
                    hit_rate REAL DEFAULT 0.0,
                    exact_hit_rate REAL DEFAULT 0.0,
                    partial_hit_rate REAL DEFAULT 0.0,
                    avg_confidence REAL DEFAULT 0.0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')
            
            conn.commit()
            conn.close()
            
            logger.info("双统计系统数据库初始化完成")
            
        except Exception as e:
            logger.error(f"统计数据库初始化失败: {e}")
    
    def record_quick_prediction(self, match_data: Dict, prediction: Dict) -> bool:
        """记录快速预测"""
        try:
            import sqlite3
            
            conn = sqlite3.connect(self.stats_db_path)
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            match_date = match_data.get('match_time', '')[:10]
            
            cursor.execute('''
                INSERT OR REPLACE INTO quick_prediction_stats 
                (match_code, match_date, home_team, away_team, league, 
                 predicted_scores, confidence, predicted_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                match_data.get('match_code'),
                match_date,
                match_data.get('home_team'),
                match_data.get('away_team'),
                match_data.get('league'),
                json.dumps(prediction.get('scores', [])),
                prediction.get('confidence', 0.0),
                prediction.get('predicted_at', now),
                now
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"快速预测已记录: {match_data.get('match_code')}")
            return True
            
        except Exception as e:
            logger.error(f"记录快速预测失败: {e}")
            return False
    
    def record_deep_analysis(self, match_data: Dict, analysis: Dict, article_id: int = None) -> bool:
        """记录深度分析"""
        try:
            import sqlite3
            
            conn = sqlite3.connect(self.stats_db_path)
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            match_date = match_data.get('match_time', '')[:10]
            
            cursor.execute('''
                INSERT OR REPLACE INTO deep_analysis_stats 
                (match_code, match_date, home_team, away_team, league, 
                 predicted_scores, materials_quality, article_id, predicted_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                match_data.get('match_code'),
                match_date,
                match_data.get('home_team'),
                match_data.get('away_team'),
                match_data.get('league'),
                json.dumps(analysis.get('scores', [])),
                analysis.get('materials_quality', 5),
                article_id,
                analysis.get('predicted_at', now),
                now
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"深度分析已记录: {match_data.get('match_code')}")
            return True
            
        except Exception as e:
            logger.error(f"记录深度分析失败: {e}")
            return False
    
    def update_match_result(self, match_data: Dict, actual_score: str) -> bool:
        """更新比赛结果并计算命中率（支持match_data参数）"""
        try:
            match_code = match_data.get('match_code') if isinstance(match_data, dict) else match_data
            
            import sqlite3
            
            conn = sqlite3.connect(self.stats_db_path)
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            
            # 检测预测类型
            prediction_type = match_data.get('source_type', 'quick') if isinstance(match_data, dict) else 'both'
            
            # 更新快速预测结果
            if prediction_type in ['quick', 'both']:
                cursor.execute('''
                    SELECT predicted_scores FROM quick_prediction_stats 
                    WHERE match_code = ?
                ''', (match_code,))
                
                quick_result = cursor.fetchone()
                if quick_result:
                    predicted_scores = json.loads(quick_result[0])
                    is_hit, hit_type = self._calculate_hit_status(predicted_scores, actual_score)
                    
                    cursor.execute('''
                        UPDATE quick_prediction_stats 
                        SET actual_score = ?, is_hit = ?, hit_type = ?, result_updated_at = ?
                        WHERE match_code = ?
                    ''', (actual_score, is_hit, hit_type, now, match_code))
            
            # 更新深度分析结果
            if prediction_type in ['deep', 'both']:
                cursor.execute('''
                    SELECT predicted_scores FROM deep_analysis_stats 
                    WHERE match_code = ?
                ''', (match_code,))
                
                deep_result = cursor.fetchone()
                if deep_result:
                    predicted_scores = json.loads(deep_result[0])
                    is_hit, hit_type = self._calculate_hit_status(predicted_scores, actual_score)
                    
                    cursor.execute('''
                        UPDATE deep_analysis_stats 
                        SET actual_score = ?, is_hit = ?, hit_type = ?, result_updated_at = ?
                        WHERE match_code = ?
                    ''', (actual_score, is_hit, hit_type, now, match_code))
            
            conn.commit()
            conn.close()
            
            # 更新总体统计
            self._update_overall_stats()
            
            logger.info(f"比赛结果已更新: {match_code} = {actual_score}")
            return True
            
        except Exception as e:
            logger.error(f"更新比赛结果失败: {e}")
            return False
    
    def _calculate_hit_status(self, predicted_scores: List[str], actual_score: str) -> tuple:
        """计算命中状态"""
        try:
            if not predicted_scores or not actual_score:
                return False, 'miss'
            
            # 检查精确命中
            if actual_score in predicted_scores:
                return True, 'exact'
            
            # 检查部分命中（比分接近）
            actual_parts = actual_score.split('-')
            if len(actual_parts) == 2:
                actual_home = int(actual_parts[0])
                actual_away = int(actual_parts[1])
                
                for pred_score in predicted_scores:
                    pred_parts = pred_score.split('-')
                    if len(pred_parts) == 2:
                        pred_home = int(pred_parts[0])
                        pred_away = int(pred_parts[1])
                        
                        # 部分命中：胜负关系正确
                        if (actual_home > actual_away and pred_home > pred_away) or \
                           (actual_home < actual_away and pred_home < pred_away) or \
                           (actual_home == actual_away and pred_home == pred_away):
                            return True, 'partial'
            
            return False, 'miss'
            
        except Exception as e:
            logger.error(f"计算命中状态失败: {e}")
            return False, 'miss'
    
    def _update_overall_stats(self):
        """更新总体统计"""
        try:
            import sqlite3
            
            conn = sqlite3.connect(self.stats_db_path)
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            today = now[:10]
            
            # 更新快速预测统计
            cursor.execute('''
                SELECT COUNT(*), SUM(CASE WHEN is_hit = 1 THEN 1 ELSE 0 END),
                       SUM(CASE WHEN hit_type = 'exact' THEN 1 ELSE 0 END),
                       SUM(CASE WHEN hit_type = 'partial' THEN 1 ELSE 0 END),
                       AVG(confidence)
                FROM quick_prediction_stats 
                WHERE actual_score IS NOT NULL
            ''')
            
            quick_stats = cursor.fetchone()
            if quick_stats and quick_stats[0] > 0:
                total, hits, exact_hits, partial_hits, avg_conf = quick_stats
                hit_rate = (hits / total) * 100 if total > 0 else 0
                exact_hit_rate = (exact_hits / total) * 100 if total > 0 else 0
                partial_hit_rate = (partial_hits / total) * 100 if total > 0 else 0
                
                cursor.execute('''
                    INSERT OR REPLACE INTO overall_stats 
                    (stat_date, prediction_type, total_predictions, hit_count, exact_hits, 
                     partial_hits, miss_count, hit_rate, exact_hit_rate, partial_hit_rate, 
                     avg_confidence, created_at, updated_at)
                    VALUES (?, 'quick', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (today, total, hits, exact_hits, partial_hits, total - hits,
                      hit_rate, exact_hit_rate, partial_hit_rate, avg_conf or 0, now, now))
            
            # 更新深度分析统计
            cursor.execute('''
                SELECT COUNT(*), SUM(CASE WHEN is_hit = 1 THEN 1 ELSE 0 END),
                       SUM(CASE WHEN hit_type = 'exact' THEN 1 ELSE 0 END),
                       SUM(CASE WHEN hit_type = 'partial' THEN 1 ELSE 0 END),
                       AVG(materials_quality)
                FROM deep_analysis_stats 
                WHERE actual_score IS NOT NULL
            ''')
            
            deep_stats = cursor.fetchone()
            if deep_stats and deep_stats[0] > 0:
                total, hits, exact_hits, partial_hits, avg_quality = deep_stats
                hit_rate = (hits / total) * 100 if total > 0 else 0
                exact_hit_rate = (exact_hits / total) * 100 if total > 0 else 0
                partial_hit_rate = (partial_hits / total) * 100 if total > 0 else 0
                
                cursor.execute('''
                    INSERT OR REPLACE INTO overall_stats 
                    (stat_date, prediction_type, total_predictions, hit_count, exact_hits, 
                     partial_hits, miss_count, hit_rate, exact_hit_rate, partial_hit_rate, 
                     avg_confidence, created_at, updated_at)
                    VALUES (?, 'deep', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (today, total, hits, exact_hits, partial_hits, total - hits,
                      hit_rate, exact_hit_rate, partial_hit_rate, avg_quality or 0, now, now))
            
            conn.commit()
            conn.close()
            
            logger.info("总体统计已更新")
            
        except Exception as e:
            logger.error(f"更新总体统计失败: {e}")
    
    def get_quick_prediction_stats(self) -> Dict:
        """获取快速预测统计"""
        try:
            import sqlite3
            
            conn = sqlite3.connect(self.stats_db_path)
            cursor = conn.cursor()
            
            # 获取最新统计
            cursor.execute('''
                SELECT * FROM overall_stats 
                WHERE prediction_type = 'quick' 
                ORDER BY updated_at DESC LIMIT 1
            ''')
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'total_predictions': result[3],
                    'hit_count': result[4],
                    'exact_hits': result[5],
                    'partial_hits': result[6],
                    'miss_count': result[7],
                    'hit_rate': result[8],
                    'exact_hit_rate': result[9],
                    'partial_hit_rate': result[10],
                    'avg_confidence': result[11],
                    'last_updated': result[13]
                }
            else:
                return {
                    'total_predictions': 0,
                    'hit_count': 0,
                    'exact_hits': 0,
                    'partial_hits': 0,
                    'miss_count': 0,
                    'hit_rate': 0.0,
                    'exact_hit_rate': 0.0,
                    'partial_hit_rate': 0.0,
                    'avg_confidence': 0.0,
                    'last_updated': None
                }
                
        except Exception as e:
            logger.error(f"获取快速预测统计失败: {e}")
            return {}
    
    def get_deep_analysis_stats(self) -> Dict:
        """获取深度分析统计"""
        try:
            import sqlite3
            
            conn = sqlite3.connect(self.stats_db_path)
            cursor = conn.cursor()
            
            # 获取最新统计
            cursor.execute('''
                SELECT * FROM overall_stats 
                WHERE prediction_type = 'deep' 
                ORDER BY updated_at DESC LIMIT 1
            ''')
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'total_predictions': result[3],
                    'hit_count': result[4],
                    'exact_hits': result[5],
                    'partial_hits': result[6],
                    'miss_count': result[7],
                    'hit_rate': result[8],
                    'exact_hit_rate': result[9],
                    'partial_hit_rate': result[10],
                    'avg_confidence': result[11],
                    'last_updated': result[13]
                }
            else:
                return {
                    'total_predictions': 0,
                    'hit_count': 0,
                    'exact_hits': 0,
                    'partial_hits': 0,
                    'miss_count': 0,
                    'hit_rate': 0.0,
                    'exact_hit_rate': 0.0,
                    'partial_hit_rate': 0.0,
                    'avg_confidence': 0.0,
                    'last_updated': None
                }
                
        except Exception as e:
            logger.error(f"获取深度分析统计失败: {e}")
            return {}
    
    def get_comparison_stats(self) -> Dict:
        """获取对比统计"""
        try:
            quick_stats = self.get_quick_prediction_stats()
            deep_stats = self.get_deep_analysis_stats()
            
            comparison = {
                'quick_prediction': quick_stats,
                'deep_analysis': deep_stats,
                'comparison': {
                    'hit_rate_difference': deep_stats.get('hit_rate', 0) - quick_stats.get('hit_rate', 0),
                    'exact_hit_rate_difference': deep_stats.get('exact_hit_rate', 0) - quick_stats.get('exact_hit_rate', 0),
                    'deep_analysis_advantage': deep_stats.get('hit_rate', 0) > quick_stats.get('hit_rate', 0),
                    'recommendation': '深度分析' if deep_stats.get('hit_rate', 0) > quick_stats.get('hit_rate', 0) else '快速预测'
                }
            }
            
            return comparison
            
        except Exception as e:
            logger.error(f"获取对比统计失败: {e}")
            return {}
    
    def calculate_overall_stats(self, date_str: str = None) -> Optional[Dict]:
        """计算指定日期的准确率统计"""
        try:
            import sqlite3
            
            # 如果没有指定日期，使用昨天
            if not date_str:
                date_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            
            conn = sqlite3.connect(self.stats_db_path)
            cursor = conn.cursor()
            
            # 计算快速预测统计
            cursor.execute('''
                SELECT COUNT(*), 
                       SUM(CASE WHEN is_hit = 1 THEN 1 ELSE 0 END),
                       SUM(CASE WHEN hit_type = 'exact' THEN 1 ELSE 0 END),
                       SUM(CASE WHEN hit_type = 'partial' THEN 1 ELSE 0 END),
                       AVG(confidence)
                FROM quick_prediction_stats 
                WHERE match_date = ? AND actual_score IS NOT NULL
            ''', (date_str,))
            
            quick_result = cursor.fetchone()
            quick_total, quick_hits, quick_exact, quick_partial, quick_conf = quick_result
            quick_total = quick_total or 0
            quick_hits = quick_hits or 0
            quick_accuracy = (quick_hits / quick_total) if quick_total > 0 else 0
            
            # 计算深度分析统计
            cursor.execute('''
                SELECT COUNT(*), 
                       SUM(CASE WHEN is_hit = 1 THEN 1 ELSE 0 END),
                       SUM(CASE WHEN hit_type = 'exact' THEN 1 ELSE 0 END),
                       SUM(CASE WHEN hit_type = 'partial' THEN 1 ELSE 0 END),
                       AVG(materials_quality)
                FROM deep_analysis_stats 
                WHERE match_date = ? AND actual_score IS NOT NULL
            ''', (date_str,))
            
            deep_result = cursor.fetchone()
            deep_total, deep_hits, deep_exact, deep_partial, deep_quality = deep_result
            deep_total = deep_total or 0
            deep_hits = deep_hits or 0
            deep_accuracy = (deep_hits / deep_total) if deep_total > 0 else 0
            
            conn.close()
            
            stats = {
                'date': date_str,
                'quick_prediction': {
                    'total_matches': quick_total,
                    'hit_count': quick_hits,
                    'exact_hits': quick_exact or 0,
                    'partial_hits': quick_partial or 0,
                    'accuracy': quick_accuracy,
                    'avg_confidence': quick_conf or 0
                },
                'deep_analysis': {
                    'total_matches': deep_total,
                    'hit_count': deep_hits,
                    'exact_hits': deep_exact or 0,
                    'partial_hits': deep_partial or 0,
                    'accuracy': deep_accuracy,
                    'avg_quality': deep_quality or 0
                },
                'total_matches': quick_total + deep_total,
                'quick_matches': quick_total,
                'deep_matches': deep_total,
                'quick_accuracy': quick_accuracy,
                'deep_accuracy': deep_accuracy,
                'calculated_at': datetime.now().isoformat()
            }
            
            logger.info(f"准确率统计计算完成: {date_str}")
            return stats
            
        except Exception as e:
            logger.error(f"计算准确率统计失败: {e}")
            return None

# 全局实例
dual_stats_tracker = DualStatsTracker()
