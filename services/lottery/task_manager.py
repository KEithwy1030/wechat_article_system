"""
深度分析任务管理器
提供异步任务执行、进度跟踪、ETA计算功能
"""
import uuid
import threading
import time
from datetime import datetime
from typing import Dict, Optional, List
from collections import deque
import asyncio

import logging

logger = logging.getLogger(__name__)


class TaskManager:
    """任务管理器：管理异步深度分析任务"""
    
    def __init__(self):
        self.tasks: Dict[str, Dict] = {}  # task_id -> task_info
        self.history_times: deque = deque(maxlen=10)  # 保留最近10次的耗时记录
        self._lock = threading.Lock()
        self.interrupt_flags: Dict[str, bool] = {}  # task_id -> should_interrupt
        
    def create_task(self, matches: List[Dict], task_type: str = 'deep_analysis') -> Dict:
        """创建新任务并返回任务信息"""
        task_id = str(uuid.uuid4())[:8]
        
        # 根据任务类型计算预计时间
        if task_type == 'quick_prediction':
            estimated_seconds = self._calculate_quick_prediction_eta(len(matches))
            current_step = '快速预测'
            steps = {
                'predict': {'status': 'running', 'time': 0}
            }
        else:  # deep_analysis
            estimated_seconds = self._calculate_eta(len(matches))
            current_step = '选择比赛'
            steps = {
                'select': {'status': 'completed', 'time': 0},
                'collect': {'status': 'pending', 'time': 0},
                'generate': {'status': 'pending', 'time': 0}
            }
        
        task_info = {
            'task_id': task_id,
            'task_type': task_type,  # deep_analysis 或 quick_prediction
            'status': 'running',  # running/completed/failed/interrupted
            'started_at': datetime.now().isoformat(),
            'estimated_seconds': estimated_seconds,
            'total_matches': len(matches),
            'completed_matches': 0,
            'current_step': current_step,
            'current_match': None,
            'steps': steps,
            'results': [],
            'error': None
        }
        
        with self._lock:
            self.tasks[task_id] = task_info
            self.interrupt_flags[task_id] = False
        
        logger.info(f"创建任务 {task_id}，预计耗时 {estimated_seconds} 秒")
        return task_info
    
    def _calculate_eta(self, num_matches: int) -> int:
        """计算深度分析ETA（基于历史平均值）"""
        if self.history_times:
            avg_per_match = sum(self.history_times) / len(self.history_times) / 3  # 历史平均值
        else:
            avg_per_match = 110  # 默认值：搜集45s + 生成65s
        
        return int(avg_per_match * num_matches)
    
    def _calculate_quick_prediction_eta(self, num_matches: int) -> int:
        """计算快速预测ETA"""
        # 快速预测平均每场比赛大约10-15秒（调用API时间）
        avg_per_match = 12  # 12秒/场
        return int(avg_per_match * num_matches)
    
    def update_task(self, task_id: str, **kwargs):
        """更新任务状态"""
        with self._lock:
            if task_id in self.tasks:
                self.tasks[task_id].update(kwargs)
    
    def update_step(self, task_id: str, step: str, status: str, elapsed_time: float = 0):
        """更新任务步骤状态"""
        with self._lock:
            if task_id in self.tasks:
                self.tasks[task_id]['steps'][step] = {
                    'status': status,
                    'time': elapsed_time
                }
                self.tasks[task_id]['current_step'] = step
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """获取任务状态"""
        with self._lock:
            task = self.tasks.get(task_id)
            if not task:
                return None
            
            # 计算剩余时间
            if task['status'] == 'running':
                elapsed = (datetime.now() - datetime.fromisoformat(task['started_at'])).total_seconds()
                remaining = max(0, task['estimated_seconds'] - elapsed)
                
                # 动态校准ETA（基于已完成的比赛）
                if task['completed_matches'] > 0:
                    avg_per_match = elapsed / task['completed_matches']
                    remaining_matches = task['total_matches'] - task['completed_matches']
                    remaining = max(0, int(avg_per_match * remaining_matches))
                
                task['elapsed_seconds'] = int(elapsed)
                task['remaining_seconds'] = int(remaining)
            
            return task.copy()
    
    def complete_task(self, task_id: str, results: List[Dict]):
        """标记任务完成"""
        with self._lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                elapsed = (datetime.now() - datetime.fromisoformat(task['started_at'])).total_seconds()
                
                task['status'] = 'completed'
                task['completed_at'] = datetime.now().isoformat()
                task['elapsed_seconds'] = int(elapsed)
                task['remaining_seconds'] = 0
                task['results'] = results
                
                # 记录到历史耗时
                self.history_times.append(elapsed)
                
                logger.info(f"任务 {task_id} 完成，实际耗时 {elapsed:.1f} 秒")
    
    def fail_task(self, task_id: str, error: str):
        """标记任务失败"""
        with self._lock:
            if task_id in self.tasks:
                self.tasks[task_id]['status'] = 'failed'
                self.tasks[task_id]['error'] = error
                self.tasks[task_id]['completed_at'] = datetime.now().isoformat()
                
                logger.error(f"任务 {task_id} 失败: {error}")
    
    def interrupt_task(self, task_id: str) -> bool:
        """中断指定的任务"""
        with self._lock:
            logger.info(f"尝试中断任务 {task_id}")
            logger.info(f"当前任务列表: {list(self.tasks.keys())}")
            logger.info(f"当前中断标志: {list(self.interrupt_flags.keys())}")
            
            if task_id not in self.tasks:
                logger.warning(f"任务 {task_id} 不存在于任务列表中")
                return False
                
            if task_id not in self.interrupt_flags:
                logger.warning(f"任务 {task_id} 不存在于中断标志列表中")
                return False
            
            task_status = self.tasks[task_id].get('status')
            logger.info(f"任务 {task_id} 当前状态: {task_status}")
            
            if task_status == 'running':
                self.interrupt_flags[task_id] = True
                self.tasks[task_id]['status'] = 'interrupted'
                logger.info(f"任务 {task_id} 已标记为中断")
                return True
            else:
                logger.warning(f"任务 {task_id} 不在运行状态 (当前状态: {task_status})，无法中断")
                return False
    
    def is_interrupted(self, task_id: str) -> bool:
        """检查任务是否被中断"""
        with self._lock:
            return self.interrupt_flags.get(task_id, False)
    
    def get_running_tasks(self) -> List[str]:
        """获取所有正在运行的任务ID"""
        with self._lock:
            return [task_id for task_id, task in self.tasks.items() 
                   if task.get('status') == 'running']
    
    def run_deep_analysis_async(self, task_id: str, matches: List[Dict]):
        """异步执行深度分析任务"""
        from .article_generator import article_generator
        
        def _run():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                results = []
                
                for idx, match in enumerate(matches):
                    # 检查是否被中断
                    if self.is_interrupted(task_id):
                        logger.info(f"[{task_id}] 任务被中断，停止执行")
                        with self._lock:
                            if task_id in self.tasks:
                                self.tasks[task_id]['status'] = 'interrupted'
                                self.tasks[task_id]['completed_at'] = datetime.now().isoformat()
                                self.tasks[task_id]['error'] = '用户中断'
                        return
                    
                    match_code = match.get('match_code')
                    self.update_task(task_id, 
                                    current_match=match_code,
                                    completed_matches=idx)
                    
                    try:
                        # 步骤1：三源资料搜集
                        step_start = time.time()
                        self.update_step(task_id, 'collect', 'running')
                        logger.info(f"[{task_id}] 开始搜集比赛 {match_code} 的三源资料")
                        
                        # 调用文章生成器（内部包含三源搜集）
                        self.update_step(task_id, 'generate', 'running')
                        logger.info(f"[{task_id}] 开始为比赛 {match_code} 生成深度分析文章")
                        
                        result = loop.run_until_complete(
                            article_generator.generate_article(match)
                        )
                        
                        step_elapsed = time.time() - step_start
                        
                        # 无论成功还是失败，都尝试保存深度分析结果
                        if result and result.get('article_data'):
                            # 保存深度分析结果到预测管理器
                            try:
                                from .prediction_manager import prediction_manager

                                logger.info(f"[{task_id}] 开始保存深度分析结果: {match_code}")
                                logger.info(f"[{task_id}] 输入参数 - match_code: {match_code}")
                                
                                article_data = result.get('article_data', {})
                                prediction_info = article_data.get('prediction', {})
                                
                                if prediction_info:
                                    deep_analysis = {
                                        'scores': prediction_info.get('scores', []),
                                        'reason': prediction_info.get('analysis', ''),
                                        'materials_quality': result.get('data_quality', {}).get('overall_score', 5),
                                        'article_id': result.get('article_id', '')
                                    }
                                    
                                    logger.info(f"[{task_id}] 深度分析数据: {deep_analysis}")
                                    
                                    save_result = prediction_manager.save_deep_analysis(match_code, deep_analysis)
                                    
                                    logger.info(f"[{task_id}] 调用 save_deep_analysis 后 - 返回结果: {save_result}")
                                    
                                    if save_result:
                                        logger.info(f"[{task_id}] 深度分析结果已保存: {match_code}")
                                        
                                        # 立即验证状态更新是否成功
                                        match_data = prediction_manager.get_prediction_data(match_code) or {}
                                        source_type = match_data.get('source_type')
                                        prediction_type = match_data.get('prediction_type')
                                        logger.info(f"[{task_id}] 状态更新验证: {match_code} - source_type={source_type}, prediction_type={prediction_type}")
                                        
                                        if source_type == 'deep':
                                            logger.info(f"[{task_id}] ✅ 状态更新成功: {match_code} 按钮应显示为'深度分析'")
                                        else:
                                            logger.warning(f"[{task_id}] ❌ 状态更新失败: {match_code} 按钮仍显示为'等待分析'")
                                        
                                        # 标记为成功，因为深度分析状态已保存
                                        self.update_step(task_id, 'generate', 'completed', step_elapsed)
                                        logger.info(f"[{task_id}] ✅ 比赛 {match_code} 深度分析完成，耗时 {step_elapsed:.1f}秒")
                                        
                                        results.append({
                                            'match_code': match_code,
                                            'status': 'success',
                                            'article_id': result.get('article_id')
                                        })
                                    else:
                                        logger.error(f"[{task_id}] 保存深度分析结果失败: save_deep_analysis 返回 False")
                                        self.update_step(task_id, 'generate', 'failed', step_elapsed)
                                        results.append({
                                            'match_code': match_code,
                                            'status': 'failed',
                                            'error': '保存深度分析结果失败'
                                        })
                                else:
                                    self.update_step(task_id, 'generate', 'failed', step_elapsed)
                                    logger.warning(f"[{task_id}] ❌ 比赛 {match_code} 深度分析失败: 缺少预测信息")
                                    results.append({
                                        'match_code': match_code,
                                        'status': 'failed',
                                        'error': '缺少预测信息'
                                    })
                            except Exception as e:
                                self.update_step(task_id, 'generate', 'failed', step_elapsed)
                                logger.error(f"[{task_id}] 保存深度分析结果异常 {match_code}: {e}")
                                logger.error(f"[{task_id}] 异常详情: {type(e).__name__}: {str(e)}")
                                results.append({
                                    'match_code': match_code,
                                    'status': 'failed',
                                    'error': str(e)
                                })
                        else:
                            self.update_step(task_id, 'generate', 'failed', step_elapsed)
                            error = result.get('error', '未知错误') if result else '生成失败'
                            logger.warning(f"[{task_id}] ❌ 比赛 {match_code} 深度分析失败: {error}")
                            results.append({
                                'match_code': match_code,
                                'status': 'failed',
                                'error': error
                            })
                    
                    except Exception as e:
                        logger.error(f"[{task_id}] 比赛 {match_code} 处理异常: {e}")
                        results.append({
                            'match_code': match_code,
                            'status': 'failed',
                            'error': str(e)
                        })
                    
                    # 更新已完成数
                    self.update_task(task_id, completed_matches=idx + 1)
                
                loop.close()
                
                # 标记任务完成
                self.complete_task(task_id, results)
                
            except Exception as e:
                logger.error(f"[{task_id}] 任务执行失败: {e}")
                self.fail_task(task_id, str(e))
        
        # 在新线程中执行
        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
    
    def run_quick_prediction_async(self, task_id: str, matches: List[Dict]):
        """异步执行快速预测任务"""
        from .score_predictor import score_predictor
        from .prediction_manager import prediction_manager
        from .system_logger import system_logger
        
        def _run():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                results = []
                success_count = 0
                
                for idx, match in enumerate(matches):
                    # 检查是否被中断
                    if self.is_interrupted(task_id):
                        logger.info(f"[{task_id}] 快速预测任务被中断，停止执行")
                        with self._lock:
                            if task_id in self.tasks:
                                self.tasks[task_id]['status'] = 'interrupted'
                                self.tasks[task_id]['completed_at'] = datetime.now().isoformat()
                                self.tasks[task_id]['error'] = '用户中断'
                        return
                    
                    match_code = match.get('match_code')
                    self.update_task(task_id, 
                                    current_match=match_code,
                                    completed_matches=idx)
                    
                    try:
                        logger.info(f"[{task_id}] 开始预测比赛 {match_code} ({idx+1}/{len(matches)})")
                        
                        # 调用快速预测
                        prediction_result = loop.run_until_complete(
                            score_predictor.predict_match(match)
                        )
                        
                        if prediction_result and prediction_result.get('status') == 'success':
                            # 使用正确的预测结果格式
                            prediction = {
                                'scores': prediction_result.get('scores', []),
                                'short_reason': prediction_result.get('short_reason', ''),
                                'predicted_at': prediction_result.get('predicted_at', '')
                            }
                            
                            # 保存快速预测
                            prediction_manager.save_quick_prediction(match, prediction)
                            success_count += 1
                            
                            logger.info(f"[{task_id}] 快速预测完成: {match_code} ({success_count}/{len(matches)})")
                            
                            # 记录成功日志到运行日志数据库
                            system_logger.log_quick_prediction(
                                match_code,
                                'success',
                                '快速预测成功',
                                metadata={'scores': prediction.get('scores'), 'reason': prediction.get('short_reason')}
                            )
                            
                            results.append({
                                'match_code': match_code,
                                'status': 'success'
                            })
                        else:
                            # 获取失败原因和错误类型
                            error = prediction_result.get('error_message', prediction_result.get('message', '未知错误')) if prediction_result else '预测失败'
                            error_type = prediction_result.get('error_type', 'unknown_error') if prediction_result else 'unknown_error'
                            
                            logger.warning(f"[{task_id}] 快速预测失败: {match_code} - {error}")
                            
                            # 记录失败日志到运行日志数据库
                            system_logger.log_quick_prediction(
                                match_code,
                                'failed',
                                f'快速预测失败: {error}',
                                error_type=error_type,
                                error_details=error
                            )
                            
                            results.append({
                                'match_code': match_code,
                                'status': 'failed',
                                'error': error
                            })
                            
                    except Exception as e:
                        error_msg = str(e)
                        logger.error(f"[{task_id}] 比赛 {match_code} 快速预测异常: {e}")
                        
                        # 记录异常日志到运行日志数据库
                        system_logger.log_quick_prediction(
                            match_code,
                            'error',
                            f'快速预测异常: {error_msg}',
                            error_type='unknown_error',
                            error_details=error_msg
                        )
                        
                        results.append({
                            'match_code': match_code,
                            'status': 'failed',
                            'error': error_msg
                        })
                    
                    # 更新已完成数
                    self.update_task(task_id, completed_matches=idx + 1)
                
                loop.close()
                
                # 更新任务信息，包含成功统计（在完成之前）
                self.update_task(task_id, 
                               success_count=success_count,
                               total_matches=len(matches))
                
                # 标记任务完成，携带成功统计
                task_result = {
                    'results': results,
                    'success_count': success_count,
                    'total_matches': len(matches)
                }
                self.complete_task(task_id, results)
                
            except Exception as e:
                logger.error(f"[{task_id}] 快速预测任务执行失败: {e}")
                self.fail_task(task_id, str(e))
        
        # 在新线程中执行
        thread = threading.Thread(target=_run, daemon=True)
        thread.start()


# 创建全局单例
task_manager = TaskManager()

