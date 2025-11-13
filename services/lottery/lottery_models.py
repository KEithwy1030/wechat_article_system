"""
竞彩数据库模型 - WechatBOT版本
从ai_content_system迁移的数据库表结构
"""
import sqlite3
import json
import logging
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class LotteryDatabase:
    """竞彩数据库管理"""
    
    def __init__(self, db_path: str = "system.db"):
        """
        初始化数据库
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        logger.info(f"竞彩数据库初始化：{db_path}")
        self.init_tables()
    
    def init_tables(self):
        """创建数据库表结构"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=30)
            
            # 性能优化设置
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=30000")
            conn.execute("PRAGMA synchronous=NORMAL")
            
            cursor = conn.cursor()
            
            # 1. 比赛数据表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS lottery_matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    match_code TEXT UNIQUE NOT NULL,
                    day TEXT NOT NULL,
                    home_team TEXT NOT NULL,
                    away_team TEXT NOT NULL,
                    match_time TEXT NOT NULL,
                    league TEXT NOT NULL,
                    match_display TEXT NOT NULL,
                    source TEXT NOT NULL,
                    scraped_at TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    group_date TEXT,
                    actual_score TEXT,
                    half_score TEXT,
                    result_updated_at TEXT,
                    group_completed INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 兼容旧表：如果表已存在但没有group_date字段，则添加
            try:
                cursor.execute('ALTER TABLE lottery_matches ADD COLUMN group_date TEXT')
                logger.info("已添加group_date字段到lottery_matches表")
            except sqlite3.OperationalError:
                # 字段已存在，忽略错误
                pass
            # 补充新增字段（兼容旧库）
            try:
                cursor.execute('ALTER TABLE lottery_matches ADD COLUMN actual_score TEXT')
                logger.info("已添加actual_score字段到lottery_matches表")
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute('ALTER TABLE lottery_matches ADD COLUMN half_score TEXT')
                logger.info("已添加half_score字段到lottery_matches表")
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute('ALTER TABLE lottery_matches ADD COLUMN result_updated_at TEXT')
                logger.info("已添加result_updated_at字段到lottery_matches表")
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute('ALTER TABLE lottery_matches ADD COLUMN group_completed INTEGER DEFAULT 0')
                logger.info("已添加group_completed字段到lottery_matches表")
            except sqlite3.OperationalError:
                pass
            
            # 2. AI预测结果表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS lottery_predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    match_code TEXT UNIQUE NOT NULL,
                    scores TEXT NOT NULL,
                    short_reason TEXT,
                    analysis TEXT,
                    short_article TEXT,
                    status TEXT NOT NULL,
                    predicted_at TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (match_code) REFERENCES lottery_matches (match_code)
                )
            ''')
            
            # 3. 比赛结果表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS lottery_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    match_code TEXT UNIQUE NOT NULL,
                    home_team TEXT NOT NULL,
                    away_team TEXT NOT NULL,
                    half_score TEXT,
                    full_score TEXT NOT NULL,
                    status TEXT NOT NULL,
                    source TEXT NOT NULL,
                    scraped_at TEXT NOT NULL,
                    league TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (match_code) REFERENCES lottery_matches (match_code)
                )
            ''')
            
            # 兼容旧表：如果表已存在但没有league字段，则添加
            try:
                cursor.execute('ALTER TABLE lottery_results ADD COLUMN league TEXT')
                logger.info("已添加league字段到lottery_results表")
            except sqlite3.OperationalError:
                # 字段已存在，忽略错误
                pass
            
            # 4. 准确率统计表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS lottery_accuracy (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    match_code TEXT UNIQUE NOT NULL,
                    predicted_scores TEXT NOT NULL,
                    actual_score TEXT,
                    is_hit INTEGER DEFAULT 0,
                    hit_type TEXT,
                    details TEXT,
                    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (match_code) REFERENCES lottery_matches (match_code)
                )
            ''')
            
            # 创建索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_lottery_matches_time ON lottery_matches (match_time)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_lottery_matches_code ON lottery_matches (match_code)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_lottery_matches_group_date ON lottery_matches (group_date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_lottery_predictions_code ON lottery_predictions (match_code)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_lottery_results_code ON lottery_results (match_code)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_lottery_accuracy_code ON lottery_accuracy (match_code)')

            # 5. 定时任务配置表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS scheduler_configs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_key TEXT UNIQUE NOT NULL,
                    task_name TEXT NOT NULL,
                    enabled INTEGER DEFAULT 1,
                    schedule_type TEXT DEFAULT 'daily',
                    time_points TEXT DEFAULT '[]',
                    weekdays TEXT DEFAULT '["mon","tue","wed","thu","fri","sat","sun"]',
                    extra_config TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            default_weekdays = json.dumps(["mon", "tue", "wed", "thu", "fri", "sat", "sun"])
            default_tasks = [
                ("schedule_collection", "赛程抓取", ["11:00"], "daily"),
                ("result_collection", "赛果抓取", ["10:30"], "daily"),
                ("quick_prediction", "快速预测", ["11:10"], "daily"),
                ("deep_analysis_selection", "深度分析选取", ["11:20"], "daily"),
                ("deep_analysis_generation", "撰写文章", ["11:30"], "daily"),
                ("accuracy_update", "命中率统计", ["10:45"], "daily")
            ]

            for task_key, task_name, time_points, schedule_type in default_tasks:
                cursor.execute('''
                    INSERT OR IGNORE INTO scheduler_configs (
                        task_key, task_name, enabled, schedule_type, time_points, weekdays, extra_config
                    ) VALUES (?, ?, 1, ?, ?, ?, ?)
                ''', (
                    task_key,
                    task_name,
                    schedule_type,
                    json.dumps(time_points),
                    default_weekdays,
                    json.dumps({})
                ))
            
            conn.commit()
            conn.close()
            
            logger.info("竞彩数据库表结构创建成功")
            
        except Exception as e:
            logger.error(f"创建数据库表失败: {str(e)}")
            raise
    
    def save_matches(self, matches: List[Dict]) -> int:
        """
        保存比赛数据（统一保存逻辑，包含group_date字段）
        方案2：保存新赛程时，将不在新赛程中的旧比赛标记为is_active=0（保留历史数据）
        
        Args:
            matches: 比赛数据列表
        
        Returns:
            保存成功的数量
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 方案2实现：先获取新赛程的match_code列表
            new_match_codes = set()
            for match in matches:
                match_code = match.get('match_code', '')
                if match_code:
                    new_match_codes.add(match_code)

            # 将不在新赛程中的旧比赛标记为is_active=0（保留历史数据，不删除）
            if new_match_codes:
                placeholders = ','.join('?' for _ in new_match_codes)
                cursor.execute(f'''
                    UPDATE lottery_matches 
                    SET is_active = 0, updated_at = ?
                    WHERE is_active = 1 
                    AND match_code NOT IN ({placeholders})
                ''', (datetime.now().isoformat(), *new_match_codes))
                
                deactivated_count = cursor.rowcount
                if deactivated_count > 0:
                    logger.info(f"已将 {deactivated_count} 场旧比赛标记为不活跃（保留历史数据）")
            else:
                logger.warning("新赛程列表为空，将保持现有数据不变")

            # 保存新赛程（所有新赛程都是is_active=1）
            saved_count = 0
            for match in matches:
                try:
                    # 获取group_date（下注时间）
                    # 注意：不使用match_time作为备选，因为下注时间和比赛时间可能不在同一天
                    group_date = match.get('group_date', '')
                    if not group_date:
                        logger.warning(f"比赛 {match.get('match_code')} 缺少group_date，将使用空值")
                    
                    cursor.execute('''
                        INSERT OR REPLACE INTO lottery_matches (
                            match_code, day, home_team, away_team, match_time,
                            league, match_display, source, scraped_at, is_active, group_date, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                    ''', (
                        match.get('match_code', ''),
                        match.get('day', ''),
                        match.get('home_team', ''),
                        match.get('away_team', ''),
                        match.get('match_time', ''),
                        match.get('league', ''),
                        match.get('match_display', ''),
                        match.get('source', ''),
                        match.get('scraped_at', ''),
                        group_date or '',
                        datetime.now().isoformat()
                    ))
                    saved_count += 1
                except Exception as e:
                    logger.error(f"保存比赛失败 {match.get('match_code')}: {str(e)}")
            
            conn.commit()
            conn.close()
            
            logger.info(f"成功保存 {saved_count} 场比赛（旧比赛已标记为不活跃，保留历史数据）")
            return saved_count
            
        except Exception as e:
            logger.error(f"保存比赛数据失败: {str(e)}")
            return 0
    
    def save_prediction(self, match_code: str, prediction: Dict) -> bool:
        """
        保存AI预测结果
        
        Args:
            match_code: 比赛编号
            prediction: 预测数据
        
        Returns:
            是否保存成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            scores_json = json.dumps(prediction.get('scores', []))
            
            cursor.execute('''
                INSERT OR REPLACE INTO lottery_predictions (
                    match_code, scores, short_reason, analysis, short_article,
                    status, predicted_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                match_code,
                scores_json,
                prediction.get('short_reason', ''),
                prediction.get('analysis', ''),
                prediction.get('short_article', ''),
                prediction.get('status', 'success'),
                prediction.get('predicted_at', datetime.now().isoformat()),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"成功保存预测：{match_code}")
            return True
            
        except Exception as e:
            logger.error(f"保存预测失败 {match_code}: {str(e)}")
            return False
    
    def get_matches(self, is_active: Optional[int] = None) -> List[Dict]:
        """
        获取比赛数据
        
        Args:
            is_active: 是否活跃（1=活跃, 0=历史, None=全部）
        
        Returns:
            比赛列表
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if is_active is not None:
                cursor.execute('''
                    SELECT * FROM lottery_matches 
                    WHERE is_active = ? 
                    ORDER BY match_time DESC
                ''', (is_active,))
            else:
                cursor.execute('''
                    SELECT * FROM lottery_matches 
                    ORDER BY match_time DESC
                ''')
            
            rows = cursor.fetchall()
            matches = [dict(row) for row in rows]
            
            conn.close()
            return matches
            
        except Exception as e:
            logger.error(f"获取比赛数据失败: {str(e)}")
            return []
    
    def get_prediction(self, match_code: str) -> Optional[Dict]:
        """
        获取AI预测结果
        
        Args:
            match_code: 比赛编号
        
        Returns:
            预测数据
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM lottery_predictions 
                WHERE match_code = ?
            ''', (match_code,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                pred = dict(row)
                # 解析JSON
                pred['scores'] = json.loads(pred.get('scores', '[]'))
                return pred
            return None
            
        except Exception as e:
            logger.error(f"获取预测失败 {match_code}: {str(e)}")
            return None


    def get_scheduler_configs(self) -> List[Dict]:
        """获取定时任务配置"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('SELECT * FROM scheduler_configs ORDER BY id')
            rows = cursor.fetchall()
            conn.close()

            configs = []
            for row in rows:
                data = dict(row)
                try:
                    data['time_points'] = json.loads(data.get('time_points') or '[]')
                except json.JSONDecodeError:
                    data['time_points'] = []

                try:
                    data['weekdays'] = json.loads(data.get('weekdays') or '[]')
                except json.JSONDecodeError:
                    data['weekdays'] = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

                try:
                    data['extra_config'] = json.loads(data.get('extra_config') or '{}')
                except json.JSONDecodeError:
                    data['extra_config'] = {}

                configs.append(data)

            return configs
        except Exception as e:
            logger.error(f"获取调度配置失败: {str(e)}")
            return []

    def update_scheduler_configs(self, configs: List[Dict]) -> bool:
        """批量更新定时任务配置"""
        try:
            now = datetime.now().isoformat()
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            for config in configs:
                task_key = config.get('task_key')
                if not task_key:
                    continue

                task_name = config.get('task_name') or ''
                enabled = 1 if config.get('enabled', True) else 0
                schedule_type = config.get('schedule_type', 'daily')
                time_points = config.get('time_points') or []
                weekdays = config.get('weekdays') or ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
                extra_config = config.get('extra_config') or {}

                cursor.execute('''
                    INSERT INTO scheduler_configs (
                        task_key, task_name, enabled, schedule_type, time_points, weekdays, extra_config, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(task_key) DO UPDATE SET
                        task_name = excluded.task_name,
                        enabled = excluded.enabled,
                        schedule_type = excluded.schedule_type,
                        time_points = excluded.time_points,
                        weekdays = excluded.weekdays,
                        extra_config = excluded.extra_config,
                        updated_at = excluded.updated_at
                ''', (
                    task_key,
                    task_name,
                    enabled,
                    schedule_type,
                    json.dumps(time_points),
                    json.dumps(weekdays),
                    json.dumps(extra_config),
                    now,
                    now
                ))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"更新调度配置失败: {str(e)}")
            return False


# 创建数据库实例
lottery_db = LotteryDatabase()

