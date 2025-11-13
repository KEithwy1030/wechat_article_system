"""
自动调度器 - 定时触发快速预测和深度分析
"""
import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import schedule
import time
import threading

logger = logging.getLogger(__name__)

class AutoScheduler:
    """自动调度器 - 处理定时任务"""
    
    def __init__(self):
        self.is_running = False
        self.scheduler_thread = None
        self.schedule_lock = threading.Lock()
        
        # 导入服务
        from .lottery_scraper import lottery_scraper
        from .score_predictor import score_predictor
        from .match_selector import match_selector
        from .prediction_manager import prediction_manager
        from services.lottery.lottery_models import lottery_db
        
        self.lottery_scraper = lottery_scraper
        self.score_predictor = score_predictor
        self.match_selector = match_selector
        self.prediction_manager = prediction_manager
        self.lottery_db = lottery_db

        self._task_map = {
            'schedule_collection': self._daily_schedule_collection,
            'result_collection': self._result_collection_task,
            'quick_prediction': self._quick_prediction_task,
            'deep_analysis_selection': self._deep_analysis_selection,
            'deep_analysis_generation': self._deep_analysis_generation,
            'accuracy_update': self._update_accuracy_stats
        }
    
    def start_scheduler(self):
        """启动调度器"""
        if self.is_running:
            logger.warning("调度器已在运行")
            return
        
        self.is_running = True
        
        # 设置定时任务
        self._setup_schedules()
        
        # 启动调度器线程
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        logger.info("自动调度器已启动")
    
    def stop_scheduler(self):
        """停止调度器"""
        self.is_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        logger.info("自动调度器已停止")
    
    def _setup_schedules(self):
        """根据配置表设置定时任务"""
        configs = self._load_scheduler_configs()

        summary = []
        with self.schedule_lock:
            schedule.clear()

            for config in configs:
                if not config.get('enabled', True):
                    continue

                task_key = config.get('task_key')
                job = self._task_map.get(task_key)
                if not job:
                    logger.warning(f"未找到任务处理函数: {task_key}")
                    continue

                raw_time_points = config.get('time_points') or []
                valid_times: List[str] = []
                for time_point in raw_time_points:
                    normalized = self._normalize_time_point(time_point)
                    if normalized:
                        valid_times.append(normalized)
                    else:
                        logger.warning(f"跳过无效时间配置 {task_key}: {time_point}")

                if not valid_times:
                    logger.warning(f"任务 {task_key} 未配置时间点，跳过")
                    continue

                schedule_type = (config.get('schedule_type') or 'daily').lower()
                weekdays = config.get('weekdays') or []

                for time_point in valid_times:
                    if schedule_type == 'weekly' and weekdays:
                        for weekday in weekdays:
                            weekday_attr = self._weekday_to_schedule_attr(weekday)
                            if not weekday_attr:
                                logger.warning(f"未知的星期配置 {weekday}，任务 {task_key}")
                                continue
                            getattr(schedule.every(), weekday_attr).at(time_point).do(job)
                    else:
                        schedule.every().day.at(time_point).do(job)

                summary.append(f"{config.get('task_name', task_key)}({','.join(valid_times)})")

        if summary:
            logger.info("定时任务设置完成 - " + "；".join(summary))
        else:
            logger.info("定时任务设置完成 - 当前无启用任务")
    
    def _run_scheduler(self):
        """运行调度器"""
        while self.is_running:
            try:
                with self.schedule_lock:
                    schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
            except Exception as e:
                logger.error(f"调度器运行错误: {e}")
                time.sleep(60)
    
    def _daily_schedule_collection(self):
        """每日赛程收集任务"""
        try:
            logger.info("开始每日赛程收集任务")
            
            # 运行赛程收集
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(self.lottery_scraper.collect_all_matches())
            
            if result and result.get('matches'):
                matches = result['matches']
                
                # 更新赛程显示
                self.prediction_manager.update_schedule_display(matches)
                
                # 保存到数据库
                try:
                    from services.lottery.lottery_models import lottery_db
                    saved_count = lottery_db.save_matches(matches)
                    logger.info(f"自动收集：成功保存 {saved_count} 场比赛到数据库")
                except Exception as e:
                    logger.error(f"自动收集保存到数据库失败: {e}")
                
                logger.info(f"赛程收集完成: {len(matches)}场比赛")
            else:
                logger.warning("赛程收集失败或无比赛数据")
            
            loop.close()
            
        except Exception as e:
            logger.error(f"每日赛程收集任务失败: {e}")
    
    def _quick_prediction_task(self):
        """快速预测任务（比赛前12小时）"""
        from .system_logger import system_logger
        
        try:
            logger.info("开始快速预测任务")
            system_logger.log_task_start('quick_prediction', '快速预测任务')
            
            # 获取未来12小时内的比赛（基于比赛时间match_time，不是下注时间group_date）
            matches = self.prediction_manager.get_matches_within_hours(hours=12)
            
            if not matches:
                logger.info("未来12小时内没有比赛，跳过快速预测")
                system_logger.log_task_end('quick_prediction', '快速预测任务', 'skipped', '未来12小时内没有比赛')
                return
            
            # 运行快速预测
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            success_count = 0
            failed_count = 0
            
            for match in matches:
                match_code = match.get('match_code', '未知')
                try:
                    # 生成快速预测
                    prediction_result = loop.run_until_complete(
                        self.score_predictor.predict_match(match)
                    )
                    
                    if prediction_result and prediction_result.get('status') == 'success':
                        # 使用正确的预测结果格式
                        prediction = {
                            'scores': prediction_result.get('scores', []),
                            'short_reason': prediction_result.get('short_reason', ''),
                            'predicted_at': prediction_result.get('predicted_at', '')
                        }
                        
                        # 保存快速预测
                        self.prediction_manager.save_quick_prediction(match, prediction)
                        
                        # 更新显示数据库（初始状态）
                        self.prediction_manager.update_schedule_display([match])
                        
                        logger.info(f"快速预测完成: {match_code}")
                        system_logger.log_quick_prediction(
                            match_code,
                            'success',
                            f'快速预测成功',
                            metadata={'scores': prediction.get('scores'), 'reason': prediction.get('short_reason')}
                        )
                        success_count += 1
                    else:
                        # 获取失败原因
                        error_type = prediction_result.get('error_type', 'unknown_error')
                        error_message = prediction_result.get('error_message', prediction_result.get('short_reason', '预测失败'))
                        
                        logger.warning(f"快速预测失败: {match_code} - {error_message}")
                        system_logger.log_quick_prediction(
                            match_code,
                            'failed',
                            f'快速预测失败: {error_message}',
                            error_type=error_type,
                            error_details=error_message
                        )
                        failed_count += 1
                        # 跳过当前比赛，继续下一场
                        continue
                        
                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"单场比赛预测失败 {match_code}: {error_msg}")
                    
                    # 判断错误类型
                    error_type = 'unknown_error'
                    if '未使用联网搜索' in error_msg or '无参考价值' in error_msg:
                        error_type = 'web_search_not_used'
                    elif '网络' in error_msg or '连接' in error_msg or 'timeout' in error_msg.lower():
                        error_type = 'network_error'
                    elif 'API' in error_msg or '401' in error_msg or '403' in error_msg or '429' in error_msg or '500' in error_msg:
                        error_type = 'api_error'
                    elif '未设置DEEPSEEK_API_KEY' in error_msg:
                        error_type = 'config_error'
                    
                    system_logger.log_quick_prediction(
                        match_code,
                        'error',
                        f'预测异常: {error_msg}',
                        error_type=error_type,
                        error_details=error_msg
                    )
                    failed_count += 1
                    # 跳过当前比赛，继续下一场
                    continue
            
            loop.close()
            
            # 记录任务完成
            summary = f'成功: {success_count}场, 失败: {failed_count}场'
            logger.info(f"快速预测任务完成 - {summary}")
            system_logger.log_task_end(
                'quick_prediction',
                '快速预测任务',
                'completed',
                summary,
                metadata={'total': len(matches), 'success': success_count, 'failed': failed_count}
            )
            
        except Exception as e:
            logger.error(f"快速预测任务失败: {e}")
            system_logger.log_task_end(
                'quick_prediction',
                '快速预测任务',
                'error',
                f'任务执行异常: {str(e)}',
                metadata={'error': str(e)}
            )
    
    def _deep_analysis_selection(self):
        """深度分析选择任务"""
        try:
            logger.info("开始深度分析选择任务")
            
            now = datetime.now()
            time_limit = now + timedelta(hours=12)
            
            # 获取今天的比赛（自动触发时）或当前页面的比赛（手动触发时）
            today = now.strftime('%Y-%m-%d')
            matches = self.prediction_manager.get_schedule_for_display(today)
            
            if not matches:
                logger.info("今天没有比赛，跳过深度分析选择")
                return
            
            # 仅保留未来12小时内的比赛
            filtered_matches = []
            for match in matches:
                match_time_str = match.get('match_time') or match.get('time_display')
                if not match_time_str:
                    continue
                
                match_time_obj = None
                try:
                    match_time_obj = datetime.fromisoformat(match_time_str)
                except ValueError:
                    try:
                        match_time_obj = datetime.strptime(match_time_str, '%Y-%m-%d %H:%M')
                    except ValueError:
                        logger.warning(f"无法解析比赛时间，跳过该场比赛: {match.get('match_code', '未知')} - {match_time_str}")
                        continue
                
                if now <= match_time_obj <= time_limit:
                    filtered_matches.append(match)
            
            if not filtered_matches:
                logger.info("未来12小时内没有可供深度分析的比赛，跳过深度分析选择")
                return
            
            # 在限定范围内随机选择3场比赛进行深度分析
            selected_matches = self.match_selector.select_random_3_matches(filtered_matches)
            
            if selected_matches:
                # 标记选中的比赛
                self.prediction_manager.mark_selected_for_analysis(selected_matches)
                
                # 记录选择理由
                reason = self.match_selector.get_selection_reason(selected_matches)
                logger.info(f"深度分析选择完成:\n{reason}")
            else:
                logger.warning("没有选择到任何比赛进行深度分析")
            
        except Exception as e:
            logger.error(f"深度分析选择任务失败: {e}")
    
    def _deep_analysis_generation(self):
        """深度分析生成任务"""
        try:
            logger.info("开始深度分析生成任务")
            
            # 获取被选中进行深度分析的比赛（不限日期，查询所有缓存）
            all_matches = self.prediction_manager.get_schedule_for_display()
            selected_matches = [m for m in all_matches if m.get('is_selected_for_analysis')]
            
            if not selected_matches:
                logger.info("没有选中的比赛进行深度分析")
                return
            
            # 运行深度分析：调用真实的文章生成器
            from .article_generator import article_generator
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            for match in selected_matches:
                try:
                    # 调用真实的深度分析：三源资料搜集 + 文章生成
                    logger.info(f"开始为比赛 {match.get('match_code')} 生成深度分析文章")
                    
                    result = loop.run_until_complete(
                        article_generator.generate_article(match)
                    )
                    
                    if result and result.get('article_status') == 'completed':
                        logger.info(f"深度分析文章生成成功: {match.get('match_code')}")
                        
                        # 从生成的文章中提取预测结果
                        article_data = result.get('article_data', {})
                        prediction_info = article_data.get('prediction', {})
                        
                        if prediction_info:
                            deep_analysis = {
                                'scores': prediction_info.get('scores', []),
                                'reason': prediction_info.get('analysis', ''),
                                'materials_quality': result.get('data_quality', {}).get('overall_score', 5),
                                'article_id': result.get('article_id', '')
                            }
                            
                            # 保存深度分析结果
                            self.prediction_manager.save_deep_analysis(
                                match.get('match_code'), 
                                deep_analysis
                            )
                    else:
                        logger.warning(f"深度分析文章生成失败: {match.get('match_code')}, 原因: {result.get('error', '未知')}")
                        
                except Exception as e:
                    logger.error(f"单场比赛深度分析失败 {match.get('match_code')}: {e}")
            
            loop.close()
            logger.info("深度分析生成任务完成")
            
        except Exception as e:
            logger.error(f"深度分析生成任务失败: {e}")
    
    def _result_collection_task(self):
        """赛果收集任务"""
        try:
            logger.info("开始赛果收集任务")
            
            # 运行赛果收集
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(self.lottery_scraper._extract_match_results())
            
            if result:
                logger.info(f"赛果收集完成: {len(result)}场比赛结果")
                
                # 统一保存赛果数据到数据库和缓存
                updated_count = self._unified_save_results(result, source="自动抓取")
                logger.info(f"自动抓取完成，共更新了 {updated_count} 场比赛的赛果")
                
                # 赛果更新后自动刷新命中率统计
                if updated_count > 0:
                    try:
                        self._update_accuracy_stats()
                        logger.info("赛果更新后已自动刷新命中率统计")
                    except Exception as stats_error:
                        logger.warning(f"自动刷新命中率统计失败: {stats_error}")
                
            else:
                logger.warning("赛果收集失败或无结果数据")
            
            loop.close()
            
        except Exception as e:
            logger.error(f"赛果收集任务失败: {e}")
    
    def _unified_save_results(self, results: List[Dict], source: str = "未知") -> int:
        """统一保存赛果数据到数据库和统计"""
        try:
            updated_count = 0
            
            # 统一保存赛果并同步到分组进度

            for match_result in results:
                match_code = match_result.get('match_code')
                full_score = match_result.get('full_score')
                
                if match_code and full_score:
                    try:
                        # 1. 保存到数据库（独立保存，不依赖lottery_matches）
                        db_saved = self._save_result_to_database(match_result)
                        
                        if db_saved:
                            try:
                                update_info = self.prediction_manager.update_match_result_in_schedule(
                                    match_code,
                                    full_score,
                                    match_result.get('half_score')
                                )
                                if update_info.get('group_completed'):
                                    logger.info(f"[{source}] 分组 {update_info.get('group_date')} 已全部完成，命中率已刷新")
                            except Exception as e:
                                logger.warning(f"[{source}] 同步lottery_matches失败 {match_code}: {e}")

                            updated_count += 1
                            logger.info(f"[{source}] 已保存比赛 {match_code} 的赛果: {full_score}")
                        else:
                            logger.warning(f"[{source}] 保存比赛 {match_code} 失败: db_saved={db_saved}")
                            
                    except Exception as e:
                        logger.error(f"[{source}] 保存单个比赛结果失败 {match_code}: {e}")
            
            return updated_count
            
        except Exception as e:
            logger.error(f"[{source}] 统一保存赛果数据失败: {e}")
            return 0
    
    def _save_result_to_database(self, match_result: Dict) -> bool:
        """保存单个赛果到数据库 - 独立保存，不依赖lottery_matches表"""
        try:
            import sqlite3
            from datetime import datetime
            
            conn = sqlite3.connect("system.db")
            cursor = conn.cursor()
            
            match_code = match_result.get('match_code', '')
            home_team = match_result.get('home_team', '')
            away_team = match_result.get('away_team', '')
            full_score = match_result.get('full_score', '')
            half_score = match_result.get('half_score', '')
            status = match_result.get('status', '已完成')
            league = match_result.get('league', '')
            
            if not full_score or not match_code:
                conn.close()
                return False
            
            # 直接使用抓取的match_code保存，不匹配lottery_matches表
            # 检查是否已存在赛果
            cursor.execute('SELECT id FROM lottery_results WHERE match_code = ?', (match_code,))
            existing = cursor.fetchone()
            
            if not existing:
                # 插入新记录到lottery_results表（包含league字段）
                cursor.execute('''
                    INSERT INTO lottery_results 
                    (match_code, home_team, away_team, half_score, full_score, status, source, scraped_at, created_at, updated_at, league)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    match_code,
                    home_team,
                    away_team,
                    half_score,
                    full_score,
                    status,
                    'auto_scheduler',
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                    league  # 添加联赛字段
                ))
                conn.commit()
                conn.close()
                logger.info(f"自动抓取保存赛果到数据库: {match_code} - {home_team} vs {away_team} - {full_score}")
                return True
            else:
                conn.close()
                logger.info(f"赛果已存在，跳过保存: {match_code}")
                return True  # 算作成功，因为数据已经存在
            
        except Exception as e:
            logger.error(f"保存赛果到数据库失败: {e}")
            return False
    
    def _update_accuracy_stats(self):
        """准确率更新任务 - 从system.db实时计算"""
        try:
            logger.info("开始准确率更新任务")
            
            # 从system.db实时计算命中率（不依赖dual_stats_tracker）
            from .prediction_manager import prediction_manager
            
            # 获取所有已完成的比赛（有实际比分的）
            completed_matches = prediction_manager.get_completed_matches_grouped(days_back=30)
            
            # 分别统计快速预测和深度分析
            quick_total = 0
            quick_hits = 0
            deep_total = 0
            deep_hits = 0
            
            for match in completed_matches:
                # 统计规则：必须同时有实际比分和预测比分才统计，两者缺一不可
                # 例如：有实际比分但没有预测结果 → 不统计（不判定为"未命中"）
                #      有预测结果但没有实际比分 → 不统计
                #      两者都有 → 统计并判断是否命中
                if not match.get('actual_score') or not match.get('scores'):
                    continue
                
                source_type = match.get('source_type', 'quick')
                is_hit = match.get('is_hit', False)
                
                if source_type == 'deep':
                    deep_total += 1
                    if is_hit:
                        deep_hits += 1
                else:
                    quick_total += 1
                    if is_hit:
                        quick_hits += 1
            
            # 计算命中率
            quick_accuracy = (quick_hits / quick_total * 100) if quick_total > 0 else 0.0
            deep_accuracy = (deep_hits / deep_total * 100) if deep_total > 0 else 0.0
            
            logger.info(f"定时任务命中率统计: 快速预测 {quick_hits}/{quick_total} ({quick_accuracy:.1f}%), 深度分析 {deep_hits}/{deep_total} ({deep_accuracy:.1f}%)")
            
        except Exception as e:
            logger.error(f"准确率更新任务失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def get_scheduler_status(self) -> Dict:
        """获取调度器状态"""
        return {
            'is_running': self.is_running,
            'next_jobs': [
                str(job.next_run) for job in schedule.jobs
            ],
            'total_jobs': len(schedule.jobs)
        }
    
    def get_scheduler_configs(self) -> List[Dict]:
        """获取当前定时任务配置"""
        return self._load_scheduler_configs()

    def save_scheduler_configs(self, configs: List[Dict]) -> bool:
        """保存配置并刷新调度任务"""
        success = self.lottery_db.update_scheduler_configs(configs)
        if success:
            self.refresh_schedules()
        return success

    def refresh_schedules(self):
        """重新加载调度配置"""
        self._setup_schedules()

    def run_manual_task(self, task_name: str) -> bool:
        """手动运行任务"""
        try:
            if task_name == 'schedule_collection':
                self._daily_schedule_collection()
            elif task_name == 'quick_prediction':
                self._quick_prediction_task()
            elif task_name == 'deep_analysis_selection':
                self._deep_analysis_selection()
            elif task_name == 'deep_analysis_generation':
                self._deep_analysis_generation()
            elif task_name == 'result_collection':
                self._result_collection_task()
            elif task_name == 'accuracy_update':
                self._update_accuracy_stats()
            else:
                logger.error(f"未知任务: {task_name}")
                return False
            
            logger.info(f"手动任务执行完成: {task_name}")
            return True
            
        except Exception as e:
            logger.error(f"手动任务执行失败 {task_name}: {e}")
            return False

    def _load_scheduler_configs(self) -> List[Dict]:
        try:
            return self.lottery_db.get_scheduler_configs()
        except Exception as e:
            logger.error(f"加载调度配置失败: {e}")
            return []

    @staticmethod
    def _normalize_time_point(time_point: str) -> Optional[str]:
        if not time_point:
            return None
        try:
            parsed = datetime.strptime(time_point.strip(), "%H:%M")
            return parsed.strftime("%H:%M")
        except ValueError:
            return None

    @staticmethod
    def _weekday_to_schedule_attr(weekday: str) -> Optional[str]:
        if not weekday:
            return None
        normalized = weekday.strip().lower()
        mapping = {
            'mon': 'monday',
            'monday': 'monday',
            'tue': 'tuesday',
            'tues': 'tuesday',
            'tuesday': 'tuesday',
            'wed': 'wednesday',
            'wednesday': 'wednesday',
            'thu': 'thursday',
            'thur': 'thursday',
            'thurs': 'thursday',
            'thursday': 'thursday',
            'fri': 'friday',
            'friday': 'friday',
            'sat': 'saturday',
            'saturday': 'saturday',
            'sun': 'sunday',
            'sunday': 'sunday'
        }
        return mapping.get(normalized)

# 全局实例
auto_scheduler = AutoScheduler()
