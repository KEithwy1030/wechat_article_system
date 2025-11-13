"""
预测管理器 - 处理快速预测和深度分析的覆盖逻辑
"""
import logging
import traceback
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json

logger = logging.getLogger(__name__)

class PredictionManager:
    """预测管理器 - 直接使用数据库，无缓存"""
    
    def __init__(self):
        self.approved_articles: Dict[str, bool] = {}
        logger.info("预测管理器初始化完成（直接使用数据库）")
    
    def is_match_completed(self, match_time: str) -> bool:
        """判断比赛是否已结束（当前时间 > 开赛时间 + 2.5小时）"""
        try:
            if not match_time:
                return False
            
            match_datetime = datetime.fromisoformat(match_time)
            current_time = datetime.now()
            end_time = match_datetime + timedelta(hours=2.5)
            
            return current_time > end_time
        except Exception as e:
            logger.error(f"判断比赛结束状态失败: {e}")
            return False

    @staticmethod
    def _normalize_score(score: Optional[str]) -> str:
        """统一比分格式，使用连字符表示"""
        if not score:
            return ''
        normalized = score.strip()
        normalized = normalized.replace('：', ':')
        normalized = normalized.replace(':', '-')
        return normalized

    def _evaluate_group_completion(self, cursor, group_date: str) -> Dict:
        """
        检查并刷新某个分组的完成状态
        :return: {
            "completed_now": bool,        # 当前是否全部有赛果
            "was_completed": bool,        # 刷新前是否已标记完成
            "matches": List[sqlite3.Row]  # 分组内的比赛记录
        }
        """
        cursor.execute('''
            SELECT lm.*, 
                   COALESCE(NULLIF(lm.actual_score, ''), NULLIF(lr.full_score, '')) AS merged_actual_score,
                   lr.full_score AS result_full_score,
                   lr.half_score AS result_half_score,
                   lr.scraped_at AS result_scraped_at,
                   lr.status AS result_status
            FROM lottery_matches lm
            LEFT JOIN lottery_results lr ON lm.match_code = lr.match_code
            WHERE lm.group_date = ?
        ''', (group_date,))

        rows = cursor.fetchall()
        if not rows:
            return {
                "completed_now": False,
                "was_completed": False,
                "matches": []
            }

        was_completed = all(bool(row['group_completed']) for row in rows)

        # 如果组内任意一场缺少比分，则视为未完成
        completed_now = all(
            bool(self._normalize_score(row['merged_actual_score']))
            for row in rows
        )

        if completed_now:
            cursor.execute(
                'UPDATE lottery_matches SET group_completed = 1 WHERE group_date = ?',
                (group_date,)
            )
        else:
            cursor.execute(
                'UPDATE lottery_matches SET group_completed = 0 WHERE group_date = ?',
                (group_date,)
            )

        return {
            "completed_now": completed_now,
            "was_completed": was_completed,
            "matches": rows
        }

    def _process_group_completion(self, group_date: str, matches: List[Dict]):
        """
        当分组全部拿到赛果时，触发命中率统计更新
        """
        try:
            from .dual_stats_tracker import dual_stats_tracker
            import sqlite3

            logger.info(f"分组 {group_date} 已全部完成，开始更新命中率统计（{len(matches)} 场）")

            # 重新查询，以便获取预测数据
            conn = sqlite3.connect("system.db")
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT lm.*, 
                       ap.prediction_type, 
                       ap.predicted_scores, 
                       ap.reason, 
                       ap.predicted_at,
                       COALESCE(NULLIF(lm.actual_score, ''), NULLIF(lr.full_score, '')) AS merged_actual_score
                FROM lottery_matches lm
                LEFT JOIN ai_predictions ap ON lm.match_code = ap.match_code
                LEFT JOIN lottery_results lr ON lm.match_code = lr.match_code
                WHERE lm.group_date = ?
            ''', (group_date,))
            detailed_rows = cursor.fetchall()
            conn.close()

            for row in detailed_rows:
                match_dict = dict(row)
                actual_score = self._normalize_score(match_dict.get('merged_actual_score'))
                if not actual_score:
                    continue

                predicted_scores = []
                if match_dict.get('predicted_scores'):
                    try:
                        predicted_scores = json.loads(match_dict['predicted_scores'])
                    except Exception as e:
                        logger.warning(f"解析预测比分失败 {match_dict.get('match_code')}: {e}")

                match_dict['scores'] = predicted_scores
                match_dict['source_type'] = 'deep' if match_dict.get('prediction_type') == 'deep' else 'quick'

                try:
                    dual_stats_tracker.update_match_result(match_dict, actual_score)
                except Exception as e:
                    logger.warning(f"更新命中率统计失败 {match_dict.get('match_code')}: {e}")

            logger.info(f"分组 {group_date} 命中率统计更新完成")

        except Exception as e:
            logger.error(f"处理分组命中率统计失败 {group_date}: {e}")
    
    def update_schedule_display(self, matches: List[Dict]):
        """直接保存到数据库，不再使用内存缓存"""
        conn = None
        try:
            import sqlite3
            
            conn = sqlite3.connect("system.db")
            cursor = conn.cursor()
            
            for match in matches:
                # 确保match_date是YYYY-MM-DD格式
                if 'match_time' in match and isinstance(match['match_time'], str):
                    try:
                        match_datetime = datetime.fromisoformat(match['match_time'])
                        match['match_date'] = match_datetime.strftime('%Y-%m-%d')
                    except ValueError:
                        logger.warning(f"Invalid match_time format for {match.get('match_code')}: {match['match_time']}")
                        match['match_date'] = 'unknown'
                else:
                    match['match_date'] = 'unknown'
                
                # 确保group_date字段存在（竞彩网的分组日期）
                if not match.get('group_date'):
                    raise ValueError(f"比赛 {match.get('match_code')} 缺少group_date，赛程数据不完整")

                # 直接更新数据库
                now = datetime.now().isoformat()
                cursor.execute('''
                    INSERT INTO lottery_matches 
                    (match_code, day, home_team, away_team, match_time, league, match_display, source, scraped_at, is_active, group_date, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                    ON CONFLICT(match_code) DO UPDATE SET
                        day=excluded.day,
                        home_team=excluded.home_team,
                        away_team=excluded.away_team,
                        match_time=excluded.match_time,
                        league=excluded.league,
                        match_display=excluded.match_display,
                        source=excluded.source,
                        scraped_at=excluded.scraped_at,
                        is_active=excluded.is_active,
                        group_date=excluded.group_date,
                        updated_at=excluded.updated_at
                ''', (
                    match.get('match_code'),
                    match.get('day', ''),
                    match.get('home_team', ''),
                    match.get('away_team', ''),
                    match.get('match_time', ''),
                    match.get('league', ''),
                    match.get('match_display', ''),
                    match.get('source', 'manual'),
                    now,
                    match.get('group_date', ''),
                    now
                ))
            
            conn.commit()
            conn.close()
            logger.info(f"已直接更新数据库中的 {len(matches)} 场比赛数据")
            
        except Exception as e:
            try:
                if conn:
                    conn.rollback()
                    conn.close()
            except Exception:
                pass
            logger.error(f"更新数据库失败: {e}")

    def get_schedule_for_display(self, date_str: str = None) -> List[Dict]:
        """直接从数据库获取赛程显示数据"""
        try:
            import sqlite3
            
            conn = sqlite3.connect("system.db")
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 构建查询条件
            where_conditions = ["is_active = 1"]
            params = []
            
            if date_str:
                where_conditions.append("date(match_time) = ?")
                params.append(date_str)
            
            # 查询比赛数据
            query = f'''
                SELECT * FROM lottery_matches 
                WHERE {' AND '.join(where_conditions)}
                ORDER BY match_time ASC
            '''
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            all_matches = []
            for row in rows:
                match = dict(row)
                match['group_completed'] = bool(match.get('group_completed'))
                if match['group_completed']:
                    continue

                match['is_completed'] = False

                match['group_date'] = match.get('group_date') or ''
                if match.get('match_time'):
                    try:
                        match_dt = datetime.fromisoformat(match['match_time'])
                        match['time_display'] = match_dt.strftime('%Y-%m-%d %H:%M')
                    except ValueError:
                        match['time_display'] = match.get('match_time', '未知时间')
                else:
                    match['time_display'] = '未知时间'

                match['league_display'] = match.get('league', '未知联赛')
                match['actual_score'] = self._normalize_score(match.get('actual_score'))
                match['half_score'] = self._normalize_score(match.get('half_score')) if match.get('half_score') else ''

                cursor.execute('''
                    SELECT prediction_type, predicted_scores, reason, predicted_at
                    FROM ai_predictions 
                    WHERE match_code = ?
                    ORDER BY predicted_at DESC
                    LIMIT 1
                ''', (match.get('match_code'),))
                prediction_row = cursor.fetchone()
                if prediction_row:
                    pred = dict(prediction_row)
                    match['scores'] = json.loads(pred.get('predicted_scores', '[]')) if pred.get('predicted_scores') else []
                    match['source_type'] = 'deep' if pred.get('prediction_type') == 'deep' else 'quick'
                    match['reason'] = pred.get('reason', '')
                    match['prediction_type'] = pred.get('prediction_type', '')
                    match['predicted_at'] = pred.get('predicted_at', '')
                else:
                    match['scores'] = []
                    match['source_type'] = ''
                    match['reason'] = ''
                    match['prediction_type'] = ''
                    match['predicted_at'] = ''
                
                all_matches.append(match)
            
            conn.close()
            
            # 统计快速预测和深度分析数量
            quick_count = sum(1 for m in all_matches if m.get('source_type') != 'deep')
            deep_count = sum(1 for m in all_matches if m.get('source_type') == 'deep')
            
            logger.debug(f"从数据库获取日期 {date_str} 的活跃赛程数据，共 {len(all_matches)} 场（快速预测：{quick_count}，深度分析：{deep_count}）。")
            return all_matches
            
        except Exception as e:
            logger.error(f"从数据库获取赛程数据失败: {e}")
            return []
    
    def get_matches_within_hours(self, hours: int = 12) -> List[Dict]:
        """
        获取未来N小时内（基于比赛时间match_time）的比赛数据
        用于快速预测任务，确保只预测未来12小时内的比赛
        
        Args:
            hours: 未来多少小时（默认12小时）
        
        Returns:
            比赛数据列表
        """
        try:
            import sqlite3
            
            conn = sqlite3.connect("system.db")
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 计算时间范围：当前时间 到 未来N小时
            now = datetime.now()
            future_time = now + timedelta(hours=hours)
            
            now_str = now.strftime('%Y-%m-%d %H:%M')
            future_str = future_time.strftime('%Y-%m-%d %H:%M')
            
            logger.info(f"查询未来{hours}小时内的比赛（基于比赛时间）：{now_str} 到 {future_str}")
            
            # 查询比赛时间在指定范围内的比赛（使用match_time，不是group_date）
            query = '''
                SELECT * FROM lottery_matches 
                WHERE is_active = 1
                AND match_time >= ?
                AND match_time <= ?
                ORDER BY match_time ASC
            '''
            
            cursor.execute(query, (now_str, future_str))
            rows = cursor.fetchall()
            
            all_matches = []
            for row in rows:
                match = dict(row)
                
                # 只返回未结束的比赛
                if not self.is_match_completed(match.get('match_time', '')):
                    # 确保所有期望的字段都存在
                    match['league_display'] = match.get('league', '未知联赛')
                    match['time_display'] = datetime.fromisoformat(match['match_time']).strftime('%Y-%m-%d %H:%M') if match.get('match_time') else '未知时间'
                    match['status'] = match.get('status', 'scheduled')
                    
                    # 从ai_predictions表获取预测数据
                    cursor.execute('''
                        SELECT prediction_type, predicted_scores, reason, predicted_at
                        FROM ai_predictions 
                        WHERE match_code = ?
                        ORDER BY predicted_at DESC
                        LIMIT 1
                    ''', (match.get('match_code'),))
                    
                    prediction_row = cursor.fetchone()
                    if prediction_row:
                        pred = dict(prediction_row)
                        match['scores'] = json.loads(pred.get('predicted_scores', '[]')) if pred.get('predicted_scores') else []
                        match['source_type'] = 'deep' if pred.get('prediction_type') == 'deep' else 'quick'
                        match['reason'] = pred.get('reason', '')
                        match['prediction_type'] = pred.get('prediction_type', '')
                        match['predicted_at'] = pred.get('predicted_at', '')
                    else:
                        match['scores'] = []
                        match['source_type'] = ''
                        match['reason'] = ''
                        match['prediction_type'] = ''
                        match['predicted_at'] = ''
                    
                    all_matches.append(match)
            
            conn.close()
            
            logger.info(f"查询到未来{hours}小时内的比赛：{len(all_matches)}场")
            return all_matches
            
        except Exception as e:
            logger.error(f"获取未来{hours}小时内的比赛数据失败: {e}")
            return []
    
    def get_schedule_for_display_by_group_date(self, group_date_str: str) -> List[Dict]:
        """直接从数据库根据group_date获取赛程显示数据"""
        try:
            import sqlite3
            
            conn = sqlite3.connect("system.db")
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 查询指定分组日期的比赛数据
            cursor.execute('''
                SELECT * FROM lottery_matches 
                WHERE is_active = 1 
                AND (group_date = ? OR group_date LIKE ?)
                ORDER BY match_time ASC
            ''', (group_date_str, f'%-{group_date_str}'))
            
            rows = cursor.fetchall()
            
            all_matches = []
            for row in rows:
                match = dict(row)
                
                # 只返回未结束的比赛
                if not self.is_match_completed(match.get('match_time', '')):
                    # 确保所有期望的字段都存在
                    match['league_display'] = match.get('league', '未知联赛')
                    match['time_display'] = datetime.fromisoformat(match['match_time']).strftime('%Y-%m-%d %H:%M') if match.get('match_time') else '未知时间'
                    match['status'] = match.get('status', 'scheduled')
                    
                    # 从ai_predictions表获取预测数据
                    cursor.execute('''
                        SELECT prediction_type, predicted_scores, reason, predicted_at
                        FROM ai_predictions 
                        WHERE match_code = ?
                        ORDER BY predicted_at DESC
                        LIMIT 1
                    ''', (match.get('match_code'),))
                    
                    prediction_row = cursor.fetchone()
                    if prediction_row:
                        pred = dict(prediction_row)
                        match['scores'] = json.loads(pred.get('predicted_scores', '[]')) if pred.get('predicted_scores') else []
                        match['source_type'] = 'deep' if pred.get('prediction_type') == 'deep' else 'quick'
                        match['reason'] = pred.get('reason', '')
                        match['prediction_type'] = pred.get('prediction_type', '')
                        match['predicted_at'] = pred.get('predicted_at', '')
                    else:
                        match['scores'] = []
                        match['source_type'] = ''
                        match['reason'] = ''
                        match['prediction_type'] = ''
                        match['predicted_at'] = ''
                    
                    all_matches.append(match)
            
            conn.close()
            
            logger.debug(f"从数据库获取分组日期 {group_date_str} 的赛程显示数据，共 {len(all_matches)} 场比赛，预测：{len([m for m in all_matches if m.get('scores')])}场，准确预测：{len([m for m in all_matches if m.get('actual_score')])}场")
            return all_matches
            
        except Exception as e:
            logger.error(f"从数据库获取分组赛程数据失败: {e}")
            return []

    
    def update_match_result_in_schedule(self, match_code: str, actual_score: Optional[str], half_score: Optional[str] = None) -> Dict:
        """
        更新单场比赛的比分信息，并在整组完成后触发命中率统计
        :return: {
            "success": bool,
            "group_completed": bool,
            "group_date": Optional[str]
        }
        """
        try:
            import sqlite3

            normalized_score = self._normalize_score(actual_score)
            normalized_half = self._normalize_score(half_score) if half_score is not None else None

            conn = sqlite3.connect("system.db")
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('SELECT group_date, group_completed FROM lottery_matches WHERE match_code = ?', (match_code,))
            row = cursor.fetchone()
            if not row:
                conn.close()
                logger.warning(f"未找到比赛: {match_code}")
                return {
                    "success": False,
                    "group_completed": False,
                    "group_date": None
                }

            group_date = row['group_date']

            now = datetime.now().isoformat()
            set_clauses = ["actual_score = ?", "result_updated_at = ?"]
            params = [normalized_score, now]
            if normalized_half is not None:
                set_clauses.insert(1, "half_score = ?")
                params.insert(1, normalized_half)

            cursor.execute(
                f'''
                    UPDATE lottery_matches
                    SET {', '.join(set_clauses)}
                    WHERE match_code = ?
                ''',
                (*params, match_code)
            )

            if cursor.rowcount == 0:
                conn.close()
                logger.warning(f"更新比赛结果失败: {match_code}")
                return {
                    "success": False,
                    "group_completed": False,
                    "group_date": group_date
                }

            group_info = None
            if group_date:
                group_info = self._evaluate_group_completion(cursor, group_date)

            conn.commit()
            conn.close()

            group_completed = bool(group_info and group_info["completed_now"])
            was_completed = bool(group_info and group_info["was_completed"])

            logger.info(f"已更新比赛结果: {match_code} -> {normalized_score or '未录入'} (group_date={group_date})")

            if group_completed and not was_completed:
                self._process_group_completion(group_date, group_info["matches"])

            return {
                "success": True,
                "group_completed": group_completed,
                "group_date": group_date
            }

        except Exception as e:
            logger.error(f"更新比赛结果失败 {match_code}: {e}")
            return {
                "success": False,
                "group_completed": False,
                "group_date": None,
                "error": str(e)
            }
    
    def get_match_detail(self, match_code: str) -> Optional[Dict]:
        """直接从数据库查询单场比赛的详细信息"""
        try:
            import sqlite3
            
            conn = sqlite3.connect("system.db")
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 查询比赛基本信息
            cursor.execute('''
                SELECT * FROM lottery_matches 
                WHERE match_code = ?
            ''', (match_code,))
            
            row = cursor.fetchone()
            if not row:
                conn.close()
                logger.warning(f"未找到比赛: {match_code}")
                return None
            
            match = dict(row)
            
            # 查询预测数据
            cursor.execute('''
                SELECT prediction_type, predicted_scores, reason, predicted_at
                FROM ai_predictions 
                WHERE match_code = ?
                ORDER BY predicted_at DESC
                LIMIT 1
            ''', (match_code,))
            
            prediction_row = cursor.fetchone()
            if prediction_row:
                pred = dict(prediction_row)
                match['scores'] = json.loads(pred.get('predicted_scores', '[]')) if pred.get('predicted_scores') else []
                match['source_type'] = 'deep' if pred.get('prediction_type') == 'deep' else 'quick'
                match['reason'] = pred.get('reason', '')
                match['prediction_type'] = pred.get('prediction_type', '')
                match['predicted_at'] = pred.get('predicted_at', '')
            else:
                match['scores'] = []
                match['source_type'] = ''
                match['reason'] = ''
                match['prediction_type'] = ''
                match['predicted_at'] = ''
            
            # 添加审核状态
            if match.get('article_id'):
                match['is_approved'] = self.approved_articles.get(match['article_id'], False)
            
            conn.close()
            logger.info(f"从数据库获取比赛详情: {match_code}")
            return match
            
        except Exception as e:
            logger.error(f"从数据库获取比赛详情失败 {match_code}: {e}")
            return None
    
    def mark_selected_for_analysis(self, matches: List[Dict]):
        """标记比赛为选中进行深度分析（已废弃，不再使用缓存）"""
        logger.info(f"标记 {len(matches)} 场比赛为深度分析（直接使用数据库）")
    
    def get_selected_matches(self) -> List[Dict]:
        """获取被选中进行深度分析的比赛（已废弃，不再使用缓存）"""
        logger.info("获取选中比赛（直接使用数据库）")
        return []
    
    def save_quick_prediction(self, match_data: Dict, prediction: Dict):
        """直接保存快速预测结果到数据库"""
        try:
            import sqlite3
            from .dual_stats_tracker import dual_stats_tracker
            
            match_code = match_data.get('match_code')
            if not match_code:
                logger.warning("缺少比赛代码")
                return False
            
            conn = sqlite3.connect("system.db")
            cursor = conn.cursor()
            
            # 保存到ai_predictions表
            cursor.execute('''
                INSERT OR REPLACE INTO ai_predictions 
                (match_code, prediction_type, predicted_scores, reason, predicted_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                match_code,
                'quick',
                json.dumps(prediction.get('scores', [])),
                prediction.get('short_reason', ''),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"快速预测已保存到数据库: {match_code}")

            # 补充记录到统计数据库，便于后续计算命中率
            try:
                stats_match = dict(match_data) if isinstance(match_data, dict) else {}
                if not stats_match.get('match_time') or not stats_match.get('home_team') or not stats_match.get('league'):
                    refreshed = self.get_match_detail(match_code)
                    if refreshed:
                        stats_match.update(refreshed)
                stats_prediction = dict(prediction) if isinstance(prediction, dict) else {}
                if not stats_prediction.get('predicted_at'):
                    stats_prediction['predicted_at'] = datetime.now().isoformat()
                dual_stats_tracker.record_quick_prediction(stats_match, stats_prediction)
            except Exception as stats_error:
                logger.warning(f"记录快速预测统计数据失败 {match_code}: {stats_error}")

            return True
            
        except Exception as e:
            logger.error(f"保存快速预测失败: {e}")
            return False
    
    def save_deep_analysis(self, match_code: str, analysis_data: Dict):
        """直接保存深度分析结果到数据库"""
        try:
            import sqlite3
            from .dual_stats_tracker import dual_stats_tracker
            
            logger.info(f"开始保存深度分析结果到数据库: {match_code}")
            
            conn = sqlite3.connect("system.db")
            cursor = conn.cursor()
            
            # 保存到ai_predictions表
            cursor.execute('''
                INSERT OR REPLACE INTO ai_predictions 
                (match_code, prediction_type, predicted_scores, reason, predicted_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                match_code,
                'deep',
                json.dumps(analysis_data.get('scores', [])),
                analysis_data.get('reason', ''),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ 深度分析已保存到数据库: {match_code}")

            # 记录深度分析至统计数据库
            try:
                match_info = self.get_match_detail(match_code) or {'match_code': match_code}
                stats_analysis = dict(analysis_data) if isinstance(analysis_data, dict) else {}
                if not stats_analysis.get('predicted_at'):
                    stats_analysis['predicted_at'] = datetime.now().isoformat()
                dual_stats_tracker.record_deep_analysis(
                    match_info,
                    stats_analysis,
                    analysis_data.get('article_id')
                )
            except Exception as stats_error:
                logger.warning(f"记录深度分析统计数据失败 {match_code}: {stats_error}")
            
            return True
                
        except Exception as e:
            logger.error(f"保存深度分析到数据库失败: {match_code} - {e}")
            return False
    
    def get_prediction_data(self, match_code: str) -> Optional[Dict]:
        """直接从数据库获取比赛的预测数据"""
        try:
            import sqlite3
            
            conn = sqlite3.connect("system.db")
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT prediction_type, predicted_scores, reason, predicted_at
                FROM ai_predictions 
                WHERE match_code = ?
                ORDER BY predicted_at DESC
                LIMIT 1
            ''', (match_code,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                pred = dict(row)
                return {
                    'scores': json.loads(pred.get('predicted_scores', '[]')) if pred.get('predicted_scores') else [],
                    'source_type': 'deep' if pred.get('prediction_type') == 'deep' else 'quick',
                    'reason': pred.get('reason', ''),
                    'prediction_type': pred.get('prediction_type', ''),
                    'predicted_at': pred.get('predicted_at', ''),
                    'analyzed_at': pred.get('predicted_at', '') if pred.get('prediction_type') == 'deep' else ''
                }
            return None
            
        except Exception as e:
            logger.error(f"从数据库获取预测数据失败: {e}")
            return None
    
    def get_completed_matches_with_results(self, days_back: int = 7) -> List[Dict]:
        """获取整组已完成的比赛数据"""
        try:
            import sqlite3

            conn = sqlite3.connect("system.db")
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cutoff_datetime = datetime.now() - timedelta(days=days_back)
            cutoff_date = cutoff_datetime.strftime('%Y-%m-%d')
            cutoff_iso = cutoff_datetime.isoformat()

            cursor.execute('''
                SELECT lm.*, 
                       lr.full_score AS result_full_score,
                       lr.half_score AS result_half_score,
                       lr.status AS result_status,
                       lr.scraped_at AS result_scraped_at,
                       ap.prediction_type,
                       ap.predicted_scores,
                       ap.reason,
                       ap.predicted_at
                FROM lottery_matches lm
                LEFT JOIN lottery_results lr ON lm.match_code = lr.match_code
                LEFT JOIN ai_predictions ap ON lm.match_code = ap.match_code
                WHERE lm.group_completed = 1
                  AND date(
                        COALESCE(
                            lm.match_time,
                            lr.scraped_at,
                            CASE
                                WHEN lm.group_date IS NULL OR TRIM(lm.group_date) = '' THEN NULL
                                WHEN LENGTH(TRIM(lm.group_date)) = 5 THEN strftime('%Y', 'now') || '-' || TRIM(lm.group_date)
                                WHEN LENGTH(TRIM(lm.group_date)) = 8 THEN '20' || TRIM(lm.group_date)
                                ELSE TRIM(lm.group_date)
                            END
                        )
                      ) >= ?
                ORDER BY lm.group_date DESC, lm.match_code DESC
            ''', (cutoff_date,))

            rows = cursor.fetchall()
            conn.close()

            completed_matches: List[Dict] = []
            for row in rows:
                match = dict(row)
                match['group_completed'] = True
                match['is_completed'] = True
                match['group_date'] = match.get('group_date') or ''

                if match.get('match_time'):
                    try:
                        match_dt = datetime.fromisoformat(match['match_time'])
                        match['time_display'] = match_dt.strftime('%Y-%m-%d %H:%M')
                    except ValueError:
                        match['time_display'] = match.get('match_time', '未知时间')
                else:
                    match['time_display'] = '未知时间'

                match['league_display'] = match.get('league', '未知联赛')
                match['result_scraped_at'] = match.get('result_scraped_at') or ''

                actual_score = match.get('actual_score') or match.get('result_full_score') or ''
                match['actual_score'] = self._normalize_score(actual_score)
                half_score = match.get('half_score') or match.get('result_half_score') or ''
                match['half_score'] = self._normalize_score(half_score)

                predicted_scores = []
                if match.get('predicted_scores'):
                    try:
                        predicted_scores = json.loads(match['predicted_scores'])
                    except Exception as e:
                        logger.warning(f"解析预测比分失败 {match.get('match_code')}: {e}")
                match['scores'] = predicted_scores

                match['source_type'] = 'deep' if match.get('prediction_type') == 'deep' else 'quick'
                match['reason'] = match.get('reason', '')
                match['predicted_at'] = match.get('predicted_at', '')

                predicted_main = ''
                if isinstance(predicted_scores, list) and predicted_scores:
                    predicted_main = predicted_scores[0]
                elif isinstance(predicted_scores, str):
                    predicted_main = predicted_scores
                match['predicted_score'] = self._normalize_score(predicted_main)

                # 修复：检查所有预测比分，只要有一个匹配实际比分就判定为命中
                match['is_hit'] = False
                if match['actual_score'] and predicted_scores:
                    normalized_actual = self._normalize_score(match['actual_score'])
                    for pred_score in predicted_scores:
                        normalized_pred = self._normalize_score(pred_score)
                        if normalized_pred == normalized_actual:
                            match['is_hit'] = True
                            break

                completed_matches.append(match)

            logger.info(f"获取整组已完成比赛 {len(completed_matches)} 场")
            return completed_matches

        except Exception as e:
            logger.error(f"从数据库获取已结束比赛数据失败: {e}")
            return []
    
    def get_completed_matches_grouped(self, days_back: int = 30) -> List[Dict]:
        """
        获取已完成的比赛数据（按分组）- get_completed_matches_with_results 的别名
        为了保持向后兼容性，保留此方法名
        """
        return self.get_completed_matches_with_results(days_back=days_back)
    
    def load_schedule_from_database(self) -> int:
        """不再需要从数据库加载到缓存，直接返回数据库中的比赛数量"""
        try:
            import sqlite3
            
            conn = sqlite3.connect("system.db")
            cursor = conn.cursor()
            
            # 统计活跃比赛数量
            cursor.execute('''
                SELECT COUNT(*) FROM lottery_matches 
                WHERE is_active = 1 
                AND match_time >= date('now', '-7 days')
            ''')
            
            count = cursor.fetchone()[0]
            conn.close()
            
            logger.info(f"✅ 数据库中活跃比赛数量: {count}")
            return count
            
        except Exception as e:
            logger.error(f"统计数据库比赛数量失败: {e}")
            return 0

# 单例实例
prediction_manager = PredictionManager()
