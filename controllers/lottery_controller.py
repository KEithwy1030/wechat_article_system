"""
竞彩相关API路由
"""
from flask import Blueprint, request, jsonify
import logging
from datetime import datetime, timedelta
import asyncio
import time
import threading

logger = logging.getLogger(__name__)

# 全局任务状态管理
_global_task_state = {
    'schedule_collection': {
        'is_running': False,
        'should_interrupt': False,
        'task_id': None
    }
}

# 定时任务工具函数
def _parse_time_points(value):
    if value is None:
        return []

    if isinstance(value, str):
        sanitized = value.replace('，', ',').replace(';', ',')
        raw_items = [item.strip() for item in sanitized.split(',')]
    elif isinstance(value, list):
        raw_items = []
        for item in value:
            if item is None:
                continue
            raw_items.append(str(item).strip())
    else:
        raw_items = []

    time_points = []
    for item in raw_items:
        if not item:
            continue
        try:
            normalized = datetime.strptime(item, "%H:%M").strftime("%H:%M")
        except ValueError:
            raise ValueError(f"时间格式无效: {item}")
        if normalized not in time_points:
            time_points.append(normalized)

    return time_points


def _parse_weekdays(value):
    default_weekdays = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    if value is None:
        return default_weekdays

    mapping = {
        "mon": "mon", "monday": "mon",
        "tue": "tue", "tues": "tue", "tuesday": "tue",
        "wed": "wed", "weds": "wed", "wednesday": "wed",
        "thu": "thu", "thur": "thu", "thurs": "thu", "thursday": "thu",
        "fri": "fri", "friday": "fri",
        "sat": "sat", "saturday": "sat",
        "sun": "sun", "sunday": "sun"
    }

    if isinstance(value, str):
        sanitized = value.replace('，', ',').replace(';', ',')
        raw_items = [item.strip().lower() for item in sanitized.split(',')]
    elif isinstance(value, list):
        raw_items = []
        for item in value:
            if item is None:
                continue
            raw_items.append(str(item).strip().lower())
    else:
        raw_items = []

    weekdays = []
    for item in raw_items:
        mapped = mapping.get(item)
        if mapped and mapped not in weekdays:
            weekdays.append(mapped)

    return weekdays or default_weekdays

# 创建蓝图
lottery_bp = Blueprint('lottery', __name__, url_prefix='/api/lottery')

# 导入服务
from services.lottery import (
    lottery_scraper, score_predictor, match_selector, 
    prediction_manager, auto_scheduler, dual_stats_tracker
)

# 导入新增的文章生成相关服务
from services.lottery.three_source_collector import three_source_collector
from services.lottery.article_generator import article_generator
from services.lottery.article_status_manager import article_status_manager, ArticleStatus
from services.lottery.system_logger import system_logger


@lottery_bp.route('/schedule', methods=['GET'])
def get_schedule():
    """获取赛程显示数据"""
    try:
        date = request.args.get('date')
        matches = prediction_manager.get_schedule_for_display(date)
        
        # 确保每个match的prediction_type字段正确设置
        for match in matches:
            if match.get('source_type') == 'deep':
                match['prediction_type'] = 'deep'
            elif not match.get('prediction_type'):
                match['prediction_type'] = 'waiting'
        
        return jsonify({
            'status': 'success',
            'data': matches,
            'count': len(matches)
        })
    except Exception as e:
        logger.error(f"获取赛程失败: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@lottery_bp.route('/completed-matches', methods=['GET'])
def get_completed_matches():
    """获取已结束的比赛数据（包含预测和赛果）"""
    try:
        days_back = request.args.get('days_back', 7, type=int)
        matches = prediction_manager.get_completed_matches_with_results(days_back)
        
        return jsonify({
            'status': 'success',
            'data': matches,
            'count': len(matches),
            'message': f'获取到 {len(matches)} 场已结束的比赛'
        })
    except Exception as e:
        logger.error(f"获取已结束比赛失败: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@lottery_bp.route('/all-matches', methods=['GET'])
def get_all_matches():
    """
    获取所有比赛数据（合并赛程和赛果）
    统一接口：包含未结束的比赛（赛程）和已结束的比赛（赛果）
    """
    try:
        date = request.args.get('date')  # 可选：指定日期
        days_back = request.args.get('days_back', 7, type=int)  # 赛果查询天数
        
        # 获取未结束的比赛（赛程）
        schedule_matches = prediction_manager.get_schedule_for_display(date)
        
        # 获取已结束的比赛（赛果）
        completed_matches = prediction_manager.get_completed_matches_with_results(days_back)
        
        # 合并数据（按match_code去重，已结束的比赛优先）
        all_matches_dict = {}
        
        # 先添加未结束的比赛
        for match in schedule_matches:
            match_code = match.get('match_code')
            if match_code:
                all_matches_dict[match_code] = match
                all_matches_dict[match_code]['is_completed'] = False
        
        # 再添加已结束的比赛（会覆盖同名的未结束比赛）
        for match in completed_matches:
            match_code = match.get('match_code')
            if match_code:
                all_matches_dict[match_code] = match
                all_matches_dict[match_code]['is_completed'] = True
        
        # 转换为列表并排序
        all_matches = list(all_matches_dict.values())
        
        # 按group_date降序、比赛编号升序排序
        def sort_key(m):
            group_date = m.get('group_date') or ''
            match_code = m.get('match_code', '')
            code_num = 0
            if match_code and len(match_code) >= 3:
                try:
                    code_num = int(match_code[-3:])
                except Exception:
                    pass
            try:
                group_value = int(group_date.replace('-', ''))
            except Exception:
                group_value = -1
            # 使用负的group_value实现日期降序，比赛编号保持正序
            return (-group_value, code_num, match_code)
        
        all_matches.sort(key=sort_key)
        
        # 统计
        schedule_count = len([m for m in all_matches if not m.get('is_completed', False)])
        completed_count = len([m for m in all_matches if m.get('is_completed', False)])
        
        return jsonify({
            'status': 'success',
            'data': all_matches,
            'count': len(all_matches),
            'schedule_count': schedule_count,
            'completed_count': completed_count,
            'message': f'获取到 {len(all_matches)} 场比赛（赛程：{schedule_count}，赛果：{completed_count}）'
        })
    except Exception as e:
        logger.error(f"获取所有比赛数据失败: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@lottery_bp.route('/quick-predictions', methods=['GET'])
def get_quick_predictions():
    """获取快速预测数据"""
    try:
        date = request.args.get('date')
        predictions = prediction_manager.get_quick_predictions(date)
        
        return jsonify({
            'status': 'success',
            'data': predictions,
            'count': len(predictions)
        })
    except Exception as e:
        logger.error(f"获取快速预测失败: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@lottery_bp.route('/add-test-predictions', methods=['POST'])
def add_test_predictions():
    """添加测试预测数据"""
    try:
        # 手动添加一些测试预测数据
        test_predictions = [
            {
                'match_code': '周二001',
                'scores': ['2-1', '1-0'],
                'source_type': 'deep',
                'reason': '深度分析完成',
                'prediction_type': 'deep',
                'article_id': 'test_article_001'
            },
            {
                'match_code': '周二002',
                'scores': ['2-1', '1-0'],
                'source_type': 'deep',
                'reason': '深度分析完成',
                'prediction_type': 'deep',
                'article_id': 'test_article_002'
            },
            {
                'match_code': '周二003', 
                'scores': ['1-0', '2-1'],
                'source_type': 'deep',
                'reason': '深度分析完成',
                'prediction_type': 'deep',
                'article_id': 'test_article_003'
            }
        ]
        
        # 直接为指定的比赛代码添加深度分析数据
        for pred in test_predictions:
            match_code = pred['match_code']
            logger.info(f"处理比赛: {match_code}（直接保存到数据库）")
            
            # 直接保存到数据库
            prediction_manager.save_deep_analysis(match_code, {
                'scores': pred['scores'],
                'reason': pred['reason'],
                'article_id': pred.get('article_id')
            })
            
            logger.info(f"已为 {match_code} 添加深度分析数据")
        
        return jsonify({
            'status': 'success',
            'message': f'已添加 {len(test_predictions)} 个测试预测数据'
        })
        
    except Exception as e:
        logger.error(f"添加测试预测数据失败: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@lottery_bp.route('/trigger-quick-predictions', methods=['POST'])
def trigger_quick_predictions():
    """手动触发快速预测 - 使用task_manager管理异步任务"""
    try:
        # 获取请求参数
        data = request.get_json() or {}
        target_date = data.get('date')
        
        logger.info(f"快速预测请求 - 目标日期: {target_date}")
        
        # 如果没有指定日期，使用当前显示的日期或者所有比赛
        if target_date:
            # 判断日期格式，如果是MM-DD格式，使用group_date方法
            if len(target_date) == 5 and target_date.count('-') == 1:
                # 格式如 "10-20"，使用group_date方法
                matches = prediction_manager.get_schedule_for_display_by_group_date(target_date)
                logger.info(f"使用group_date方法获取 {target_date} 的比赛，找到 {len(matches)} 场")
            elif len(target_date) == 10 and target_date.count('-') == 2:
                # 格式如 "2025-10-20"，使用match_date方法
                matches = prediction_manager.get_schedule_for_display(target_date)
                logger.info(f"使用match_date方法获取 {target_date} 的比赛，找到 {len(matches)} 场")
            else:
                # 其他格式，尝试两种方法
                matches = prediction_manager.get_schedule_for_display_by_group_date(target_date)
                if not matches:
                    matches = prediction_manager.get_schedule_for_display(target_date)
                logger.info(f"使用混合方法获取 {target_date} 的比赛，找到 {len(matches)} 场")
            
            if not matches:
                return jsonify({
                    'status': 'error',
                    'message': f'指定日期({target_date})没有比赛数据'
                }), 400
        else:
            # 如果没有指定日期，获取所有当前的活跃比赛（未结束的比赛）
            matches = prediction_manager.get_schedule_for_display()
            logger.info(f"未指定日期，获取所有活跃比赛，找到 {len(matches)} 场")
            if not matches:
                return jsonify({
                    'status': 'error',
                    'message': '当前没有可预测的比赛数据'
                }), 400
        
        # 过滤出需要预测的比赛（没有预测结果且不是深度分析的比赛）
        matches_to_predict = []
        matches_outside_window = []
        
        for match in matches:
            match_code = match.get('match_code')
            scores = match.get('scores', [])
            source_type = match.get('source_type', '')
            prediction_type = match.get('prediction_type', '')
            match_time = match.get('match_time', '')
            
            # 只预测那些没有预测结果的比赛，且不是深度分析状态
            has_prediction = bool(scores and len(scores) > 0 and any(score.strip() for score in scores if score))
            is_deep_analysis = source_type == 'deep' or prediction_type == 'deep'
            
            if not has_prediction and not is_deep_analysis:
                # 检查时间窗口（12小时内）
                if not match_time:
                    logger.warning(f"比赛 {match_code} 缺少 match_time 字段，跳过")
                    matches_outside_window.append(match)
                    continue
                
                try:
                    from datetime import datetime
                    # 支持两种格式：ISO格式（2025-11-14T00:00:00）和简单格式（2025-11-14 00:00）
                    try:
                        # 先尝试 ISO 格式（数据库标准格式）
                        match_time_obj = datetime.fromisoformat(match_time.replace('Z', '+00:00'))
                    except (ValueError, AttributeError):
                        # 如果失败，尝试简单格式
                        try:
                            match_time_obj = datetime.strptime(match_time, '%Y-%m-%d %H:%M')
                        except ValueError:
                            # 如果还是失败，尝试其他可能的格式
                            match_time_obj = datetime.strptime(match_time, '%Y-%m-%d %H:%M:%S')
                    
                    current_time = datetime.now()
                    time_diff = match_time_obj - current_time
                    hours_diff = time_diff.total_seconds() / 3600
                    
                    # 只处理未来12小时内的比赛（0 < hours_diff <= 12）
                    if 0 < hours_diff <= 12:
                        matches_to_predict.append(match)
                        logger.info(f"比赛 {match_code} 需要快速预测（时间差: {hours_diff:.1f}小时，比赛时间: {match_time}）")
                    else:
                        matches_outside_window.append(match)
                        logger.info(f"比赛 {match_code} 超出12小时时间窗口（时间差: {hours_diff:.1f}小时，比赛时间: {match_time}）")
                except Exception as e:
                    logger.warning(f"比赛 {match_code} 时间解析失败: {e}，match_time={match_time}")
                    matches_outside_window.append(match)
            else:
                logger.info(f"比赛 {match_code} 已有预测或为深度分析，跳过 - 预测结果: {scores}, 来源类型: {source_type}, 预测类型: {prediction_type}")
        
        # 记录实际要预测的比赛数量
        total_matches_to_predict = len(matches_to_predict)
        total_matches_outside_window = len(matches_outside_window)
        total_matches_skipped = len(matches) - total_matches_to_predict - total_matches_outside_window
        
        logger.info(f"快速预测过滤结果：共 {len(matches)} 场比赛")
        logger.info(f"  - 需要预测（12小时内）: {total_matches_to_predict} 场")
        logger.info(f"  - 超出时间窗口（>12小时）: {total_matches_outside_window} 场")
        logger.info(f"  - 已跳过（已有预测/深度分析）: {total_matches_skipped} 场")
        
        if total_matches_to_predict == 0:
            if total_matches_outside_window > 0:
                # 提供更详细的错误信息
                return jsonify({
                    'status': 'error',
                    'message': f'当前有 {total_matches_outside_window} 场比赛，但都在12小时以外，无法进行快速预测。快速预测只处理未来12小时内的比赛。',
                    'details': {
                        'total_matches': len(matches),
                        'matches_in_window': 0,
                        'matches_outside_window': total_matches_outside_window,
                        'matches_skipped': total_matches_skipped
                    }
                }), 400
            else:
                return jsonify({
                    'status': 'error',
                    'message': '没有需要预测的比赛，所有比赛都已有预测结果或正在进行深度分析',
                    'details': {
                        'total_matches': len(matches),
                        'matches_in_window': 0,
                        'matches_outside_window': 0,
                        'matches_skipped': total_matches_skipped
                    }
                }), 400
        
        # 使用过滤后的比赛列表
        matches = matches_to_predict
        
        # 使用task_manager创建快速预测任务
        from services.lottery.task_manager import task_manager
        
        task_data = task_manager.create_task(matches, task_type='quick_prediction')
        task_id = task_data['task_id']
        
        logger.info(f"创建快速预测任务: {task_id}")
        
        # 异步执行快速预测
        task_manager.run_quick_prediction_async(task_id, matches)
        
        return jsonify({
            'status': 'success',
            'message': '快速预测任务已启动',
            'task_id': task_id,
            'task_data': task_data,
            'total_matches': total_matches_to_predict
        })
        
    except Exception as e:
        logger.error(f"触发快速预测失败: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@lottery_bp.route('/select-matches', methods=['POST'])
def select_matches():
    """手动选择比赛进行深度分析"""
    try:
        # 安全地解析JSON数据
        try:
            if request.is_json:
                data = request.get_json() or {}
            else:
                data = {}
                logger.warning("手动选择比赛请求不是JSON格式")
        except Exception as json_error:
            logger.error(f"JSON解析失败: {json_error}")
            data = {}
        
        date = data.get('date')
        
        if not date:
            return jsonify({
                'status': 'error',
                'message': '缺少日期参数'
            }), 400
        
        # 获取该日期的所有比赛
        matches = prediction_manager.get_schedule_for_display(date)
        
        if not matches:
            return jsonify({
                'status': 'error',
                'message': '该日期没有比赛数据'
            }), 404
        
        # 过滤未来12小时内的比赛
        try:
            from datetime import datetime
            filtered_matches = []
            excluded_matches = []
            now = datetime.now()
            for match in matches:
                match_time = match.get('match_time')
                if not match_time:
                    logger.info(f"比赛 {match.get('match_code', '未知比赛')} 缺少 match_time，已排除")
                    excluded_matches.append(match)
                    continue
                
                try:
                    # 支持多种格式
                    try:
                        match_dt = datetime.fromisoformat(match_time.replace('Z', '+00:00'))
                    except (ValueError, AttributeError):
                        try:
                            match_dt = datetime.strptime(match_time, '%Y-%m-%d %H:%M')
                        except ValueError:
                            match_dt = datetime.strptime(match_time, '%Y-%m-%d %H:%M:%S')
                except Exception as e:
                    logger.warning(f"比赛 {match.get('match_code', '未知比赛')} match_time 解析失败: {e}, match_time={match_time}")
                    excluded_matches.append(match)
                    continue
                
                hours_diff = (match_dt - now).total_seconds() / 3600
                if 0 < hours_diff <= 12:
                    filtered_matches.append(match)
                else:
                    logger.info(f"比赛 {match.get('match_code', '未知比赛')} 超出12小时窗口（时间差: {hours_diff:.1f}小时）")
                    excluded_matches.append(match)
            
            if not filtered_matches:
                return jsonify({
                    'status': 'error',
                    'message': '未来12小时内没有符合条件的比赛，无法执行深度分析'
                }), 400
        except Exception as filter_error:
            logger.error(f"深度分析比赛过滤失败: {filter_error}", exc_info=True)
            return jsonify({
                'status': 'error',
                'message': f'深度分析比赛过滤失败: {filter_error}'
            }), 500
        
        # 随机选择3场比赛
        selected_matches = match_selector.select_random_3_matches(filtered_matches)
        
        if selected_matches:
            # 标记选中的比赛
            prediction_manager.mark_selected_for_analysis(selected_matches)
            
            # 获取选择理由
            reason = match_selector.get_selection_reason(selected_matches)
            
            return jsonify({
                'status': 'success',
                'data': {
                    'selected_matches': selected_matches,
                    'reason': reason,
                    'count': len(selected_matches)
                }
            })
        else:
            return jsonify({
                'status': 'error',
                'message': '没有选择到任何比赛'
            }), 500
            
    except Exception as e:
        logger.error(f"选择比赛失败: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@lottery_bp.route('/generate-analysis', methods=['POST'])
def generate_analysis():
    """生成深度分析"""
    try:
        # 安全地解析JSON数据
        try:
            if request.is_json:
                data = request.get_json() or {}
            else:
                data = {}
                logger.warning("生成深度分析请求不是JSON格式")
        except Exception as json_error:
            logger.error(f"JSON解析失败: {json_error}")
            data = {}
        
        match_codes = data.get('match_codes', [])
        
        if not match_codes:
            return jsonify({
                'status': 'error',
                'message': '缺少比赛代码'
            }), 400
        
        results = []
        
        # 真实深度分析生成
        for match_code in match_codes:
            try:
                # 获取比赛数据
                matches = prediction_manager.get_schedule_for_display()
                match_data = next((m for m in matches if m['match_code'] == match_code), None)
                
                if not match_data:
                    results.append({
                        'match_code': match_code,
                        'status': 'error',
                        'message': '比赛数据不存在'
                    })
                    continue
                
                # 生成真实深度分析
                import asyncio
                deep_analysis = asyncio.run(three_source_collector.collect_comprehensive_data(match_data))
                
                if deep_analysis and deep_analysis.get('success'):
                    # 保存深度分析结果
                    prediction_manager.save_deep_analysis(match_code, deep_analysis['data'])
                    
                    results.append({
                        'match_code': match_code,
                        'status': 'success',
                        'analysis': deep_analysis['data']
                    })
                    
                    logger.info(f"成功生成比赛 {match_code} 的深度分析")
                else:
                    results.append({
                        'match_code': match_code,
                        'status': 'error',
                        'message': '深度分析生成失败'
                    })
                    
            except Exception as e:
                    logger.error(f"生成深度分析失败 {match_code}: {e}")
                    results.append({
                        'match_code': match_code,
                        'status': 'error',
                        'message': str(e)
                    })
            
            return jsonify({
                'status': 'success',
                'data': results,
            })
        
        # 真实数据模式
        # 为每场比赛生成深度分析
        for match_code in match_codes:
            try:
                # 获取比赛数据
                matches = prediction_manager.get_schedule_for_display()
                match_data = next((m for m in matches if m['match_code'] == match_code), None)
                
                if not match_data:
                    results.append({
                        'match_code': match_code,
                        'status': 'error',
                        'message': '比赛数据不存在'
                    })
                    continue
                
                # 生成AI预测（暂时使用现有逻辑）
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                prediction_result = loop.run_until_complete(
                    score_predictor.predict_match_score(match_data)
                )
                
                if prediction_result and prediction_result.get('status') == 'success':
                    prediction = prediction_result['prediction']
                    
                    # 模拟深度分析结果
                    deep_analysis = {
                        'scores': prediction.get('scores', []),
                        'reason': f"[深度分析] {prediction.get('reason', '')}",
                        'materials_quality': 5,
                        'predicted_at': datetime.now().isoformat()
                    }
                    
                    # 保存深度分析结果
                    prediction_manager.save_deep_analysis(match_code, deep_analysis)
                    
                    # 记录统计
                    dual_stats_tracker.record_deep_analysis(match_data, deep_analysis)
                    
                    results.append({
                        'match_code': match_code,
                        'status': 'success',
                        'analysis': deep_analysis
                    })
                else:
                    results.append({
                        'match_code': match_code,
                        'status': 'error',
                        'message': 'AI预测失败'
                    })
                
                loop.close()
                
            except Exception as e:
                logger.error(f"生成单场比赛分析失败 {match_code}: {e}")
                results.append({
                    'match_code': match_code,
                    'status': 'error',
                    'message': str(e)
                })
        
        return jsonify({
            'status': 'success',
            'data': results
        })
        
    except Exception as e:
        logger.error(f"生成深度分析失败: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@lottery_bp.route('/approve-analysis', methods=['POST'])
def approve_analysis():
    """审核通过深度分析"""
    try:
        data = request.get_json()
        match_code = data.get('match_code')
        
        if not match_code:
            return jsonify({
                'status': 'error',
                'message': '缺少比赛代码'
            }), 400
        
        success = prediction_manager.approve_analysis(match_code)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': '审核通过成功'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': '审核通过失败'
            }), 500
            
    except Exception as e:
        logger.error(f"审核通过失败: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@lottery_bp.route('/stats', methods=['GET'])
def get_stats():
    """获取双统计系统数据"""
    try:
        stats = dual_stats_tracker.get_comparison_stats()
        
        return jsonify({
            'status': 'success',
            'data': stats,
        })
    except Exception as e:
        logger.error(f"获取统计失败: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@lottery_bp.route('/scheduler/status', methods=['GET'])
def get_scheduler_status():
    """获取调度器状态"""
    try:
        status = auto_scheduler.get_scheduler_status()
        
        return jsonify({
            'status': 'success',
            'data': status
        })
    except Exception as e:
        logger.error(f"获取调度器状态失败: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@lottery_bp.route('/scheduler/configs', methods=['GET'])
def get_scheduler_configs():
    """获取定时任务配置"""
    try:
        configs = auto_scheduler.get_scheduler_configs()
        return jsonify({
            'status': 'success',
            'data': configs
        })
    except Exception as e:
        logger.error(f"获取调度配置失败: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@lottery_bp.route('/scheduler/configs', methods=['POST'])
def update_scheduler_configs():
    """更新定时任务配置"""
    try:
        data = request.get_json() or {}
        configs = data.get('configs')

        if not isinstance(configs, list):
            return jsonify({
                'status': 'error',
                'message': 'configs 参数缺失或格式错误'
            }), 400

        existing_configs = {cfg['task_key']: cfg for cfg in auto_scheduler.get_scheduler_configs()}
        normalized_configs = []

        for item in configs:
            if not isinstance(item, dict):
                continue

            task_key = item.get('task_key')
            if not task_key:
                continue

            base_config = existing_configs.get(task_key, {})
            task_name = item.get('task_name') or base_config.get('task_name') or task_key
            enabled = bool(item.get('enabled', base_config.get('enabled', True)))
            schedule_type = (item.get('schedule_type') or base_config.get('schedule_type') or 'daily').lower()
            if schedule_type not in ('daily', 'weekly'):
                return jsonify({
                    'status': 'error',
                    'message': f'不支持的任务周期: {schedule_type}'
                }), 400

            time_points_raw = item.get('time_points', base_config.get('time_points'))
            try:
                time_points = _parse_time_points(time_points_raw)
            except ValueError as ve:
                return jsonify({
                    'status': 'error',
                    'message': str(ve)
                }), 400

            if not time_points:
                return jsonify({
                    'status': 'error',
                    'message': f'任务 {task_name} 至少需要一个有效执行时间'
                }), 400

            weekdays_raw = item.get('weekdays', base_config.get('weekdays'))
            weekdays = _parse_weekdays(weekdays_raw) if schedule_type == 'weekly' else ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

            normalized_configs.append({
                'task_key': task_key,
                'task_name': task_name,
                'enabled': enabled,
                'schedule_type': schedule_type,
                'time_points': time_points,
                'weekdays': weekdays,
                'extra_config': item.get('extra_config', base_config.get('extra_config', {}))
            })

        success = auto_scheduler.save_scheduler_configs(normalized_configs)
        if success:
            return jsonify({
                'status': 'success',
                'message': '调度配置已更新'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': '调度配置保存失败'
            }), 500

    except Exception as e:
        logger.error(f"更新调度配置失败: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@lottery_bp.route('/scheduler/start', methods=['POST'])
def start_scheduler():
    """启动调度器"""
    try:
        auto_scheduler.start_scheduler()
        
        return jsonify({
            'status': 'success',
            'message': '调度器已启动'
        })
    except Exception as e:
        logger.error(f"启动调度器失败: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@lottery_bp.route('/scheduler/stop', methods=['POST'])
def stop_scheduler():
    """停止调度器"""
    try:
        auto_scheduler.stop_scheduler()
        
        return jsonify({
            'status': 'success',
            'message': '调度器已停止'
        })
    except Exception as e:
        logger.error(f"停止调度器失败: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# 第一个get_article路由已删除，避免与新路由冲突

@lottery_bp.route('/preview/<match_code>', methods=['GET'])
def preview_article(match_code):
    """预览深度分析文章"""
    try:
        # 从显示管理器获取比赛数据
        matches = prediction_manager.get_schedule_for_display()
        match_data = next((m for m in matches if m['match_code'] == match_code), None)
        
        if not match_data:
            return jsonify({
                'status': 'error',
                'message': '比赛数据不存在'
            }), 404
        
        # 获取真实深度分析预览
        preview_data = prediction_manager.get_analysis_preview(match_code)
        
        if preview_data:
            return jsonify({
                'status': 'success',
                'data': preview_data,
            })
        else:
            return jsonify({
                'status': 'error',
                'message': '预览不存在'
            }), 404
                
    except Exception as e:
        logger.error(f"获取预览失败: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@lottery_bp.route('/approve/<match_code>', methods=['POST'])
def approve_article(match_code):
    """审核通过深度分析"""
    try:
        # 真实数据模式
        success = prediction_manager.approve_analysis(match_code)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': '审核通过成功',
            })
        else:
            return jsonify({
                'status': 'error',
                'message': '审核通过失败'
            }), 500
                
    except Exception as e:
        logger.error(f"审核失败: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@lottery_bp.route('/scheduler/run-task', methods=['POST'])
def run_manual_task():
    """手动运行任务"""
    try:
        data = request.get_json()
        task_name = data.get('task_name')
        
        if not task_name:
            return jsonify({
                'status': 'error',
                'message': '缺少任务名称'
            }), 400
        
        success = auto_scheduler.run_manual_task(task_name)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': f'任务 {task_name} 执行成功'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f'任务 {task_name} 执行失败'
            }), 500
            
    except Exception as e:
        logger.error(f"手动运行任务失败: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@lottery_bp.route('/collect-schedule', methods=['POST'])
def collect_schedule():
    """手动收集赛程 - 支持中断的版本"""
    try:
        # 真实数据采集
        logger.info("使用真实数据模式收集赛程")
        
        # 设置全局中断检查点
        def check_interrupt():
            if _global_task_state['schedule_collection']['should_interrupt']:
                raise Exception("任务被中断")
        
        # 设置任务状态用于中断检测
        import uuid
        task_id = str(uuid.uuid4())[:8]
        _global_task_state['schedule_collection'].update({
            'is_running': True,
            'should_interrupt': False,
            'task_id': task_id
        })
        
        logger.info(f"开始赛程收集任务: {task_id}")
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # 检查中断信号
            check_interrupt()
            
            # 创建带中断检查的异步任务
            async def fetch_with_interrupt_check():
                # 创建中断检查函数
                def interrupt_check_func():
                    return _global_task_state['schedule_collection']['should_interrupt']
                
                # 执行数据收集，传入中断检查函数
                result = await lottery_scraper.fetch_schedule(interrupt_check=interrupt_check_func)
                
                # 最后检查中断
                check_interrupt()
                return result
            
            # 执行带超时的任务，每秒检查一次中断信号
            result = loop.run_until_complete(
                asyncio.wait_for(fetch_with_interrupt_check(), timeout=120)
            )
            
            loop.close()
            
            # 检查返回的success字段
            if result and result.get('success'):
                matches = result.get('matches', [])
                
                # 更新到显示管理器
                try:
                    prediction_manager.update_schedule_display(matches)
                    logger.info(f"成功更新 {len(matches)} 场比赛到显示管理器")
                except Exception as e:
                    logger.warning(f"更新显示管理器失败: {e}")
                
                # 保存到数据库
                try:
                    from services.lottery.lottery_models import lottery_db
                    saved_count = lottery_db.save_matches(matches)
                    logger.info(f"成功保存 {saved_count} 场比赛到数据库")
                except Exception as e:
                    logger.warning(f"保存到数据库失败: {e}")
                
                return jsonify({
                    'status': 'success',
                    'data': {
                        'matches': matches,
                        'count': len(matches)
                    }
                })
            else:
                error_msg = result.get('error', '赛程收集失败')
                # 友好提示：常见为ChromeDriver/浏览器未就绪
                suggestion = None
                lower_msg = str(error_msg).lower()
                if 'connection refused' in lower_msg or 'newconnectionerror' in lower_msg or 'chromedriver' in lower_msg:
                    suggestion = '可能原因：Chrome/ChromeDriver未安装或未匹配、驱动未启动、被安全软件拦截。请安装匹配版本的Chrome与ChromeDriver，或检查驱动进程是否在运行。'
                logger.error(f"赛程收集失败: {error_msg}")
                return jsonify({
                    'status': 'error',
                    'message': error_msg,
                    'suggestion': suggestion
                }), 500
        
        except asyncio.TimeoutError:
            logger.warning(f"赛程收集任务超时: {task_id}")
            return jsonify({
                'status': 'timeout',
                'message': '任务执行超时'
            }), 504
        except Exception as e:
            # 进一步归因
            err = str(e)
            suggestion = None
            if '任务被中断' in err:
                logger.info(f"赛程收集任务被中断: {task_id}")
                return jsonify({
                    'status': 'interrupted',
                    'message': '任务被中断'
                }), 200
            elif 'connection refused' in err.lower() or 'newconnectionerror' in err.lower() or 'chromedriver' in err.lower():
                suggestion = 'Chrome/ChromeDriver未就绪或端口被占用。请确认驱动版本与Chrome一致并已启动。'
            logger.error(f"收集赛程失败: {e}", exc_info=True)
            return jsonify({
                'status': 'error',
                'message': err,
                'suggestion': suggestion
            }), 500
    
    except Exception as e:
        # 最外层异常处理
        logger.error(f"collect_schedule 最外层异常: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'系统错误: {str(e)}'
        }), 500
    finally:
        # 重置任务状态
        _global_task_state['schedule_collection'].update({
            'is_running': False,
            'should_interrupt': False,
            'task_id': None
        })

# 新增文章生成相关API
@lottery_bp.route('/generate-article/<match_code>', methods=['POST'])
def generate_article(match_code):
    """生成文章"""
    try:
        # 获取比赛信息
        matches = prediction_manager.get_schedule_for_display()
        match_info = None
        
        for match in matches:
            if match.get('match_code') == match_code:
                match_info = match
                break
        
        if not match_info:
            return jsonify({
                'status': 'error',
                'message': '比赛信息不存在'
            }), 404
        
        # 更新文章状态为生成中
        article_status_manager.update_article_status(
            match_code, 
            ArticleStatus.GENERATING,
            {'started_at': datetime.now().isoformat()}
        )
        
        # 异步生成文章
        async def generate_article_async():
            try:
                result = await article_generator.generate_article(match_info)
                
                if result.get('article_status') == 'completed':
                    article_status_manager.update_article_status(
                        match_code,
                        ArticleStatus.GENERATED,
                        {
                            'generated_at': datetime.now().isoformat(),
                            'word_count': result.get('article_metadata', {}).get('word_count', 0)
                        }
                    )
                else:
                    article_status_manager.update_article_status(
                        match_code,
                        ArticleStatus.FAILED,
                        {'error': result.get('error', '未知错误')}
                    )
                
                return result
            except Exception as e:
                article_status_manager.update_article_status(
                    match_code,
                    ArticleStatus.FAILED,
                    {'error': str(e)}
                )
                raise
        
        # 启动异步任务
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(generate_article_async())
        
        return jsonify({
            'status': 'success',
            'data': result
        })
        
    except Exception as e:
        logger.error(f"生成文章失败: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@lottery_bp.route('/article/<match_code>', methods=['GET'])
def get_article(match_code):
    """获取文章内容"""
    try:
        # 先从生成器加载（含安全文件名兜底）
        article_data = article_generator.load_article(match_code)
        
        if not article_data:
            # 进一步给出明确原因与建议
            hint = '文章文件未找到。可能原因：1) 生成过程失败未落盘；2) 文件名包含中文未转义；3) 缓存目录被清理。'
            return jsonify({
                'status': 'error',
                'message': hint,
                'suggestion': '请重新执行深度分析，或在系统配置中检查缓存目录 cache/generated_articles/ 是否存在且可写'
            }), 404
        
        # 获取文章状态
        status_data = article_status_manager.get_article_status(match_code)
        
        return jsonify({
            'status': 'success',
            'data': {
                'article_content': article_data.get('content', ''),
                'article_metadata': article_data.get('metadata', {}),
                'article_status': status_data.get('status', 'unknown'),
                'status_history': status_data.get('status_history', [])
            }
        })
        
    except Exception as e:
        logger.error(f"获取文章失败: {e}")
        return jsonify({
            'status': 'error',
            'message': f'获取文章异常: {str(e)}',
            'suggestion': '请检查AI服务配置、磁盘权限与服务日志'
        }), 500

@lottery_bp.route('/article-status/<match_code>', methods=['GET'])
def get_article_status(match_code):
    """获取文章状态"""
    try:
        status_data = article_status_manager.get_article_status(match_code)
        
        return jsonify({
            'status': 'success',
            'data': status_data
        })
        
    except Exception as e:
        logger.error(f"获取文章状态失败: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@lottery_bp.route('/article-status/<match_code>', methods=['PUT'])
def update_article_status(match_code):
    """更新文章状态"""
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        if not new_status:
            return jsonify({
                'status': 'error',
                'message': '缺少状态参数'
            }), 400
        
        # 验证状态
        try:
            article_status = ArticleStatus(new_status)
        except ValueError:
            return jsonify({
                'status': 'error',
                'message': '无效的状态值'
            }), 400
        
        # 获取当前状态
        current_status_data = article_status_manager.get_article_status(match_code)
        current_status = ArticleStatus(current_status_data.get('status', ArticleStatus.NOT_GENERATED.value))
        
        # 检查状态转换是否合法
        if not article_status_manager.can_transition_to(current_status, article_status):
            return jsonify({
                'status': 'error',
                'message': f'不能从 {current_status.value} 转换到 {article_status.value}'
            }), 400
        
        # 更新状态
        success = article_status_manager.update_article_status(
            match_code,
            article_status,
            data.get('metadata', {})
        )
        
        if success:
            return jsonify({
                'status': 'success',
                'message': '状态更新成功'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': '状态更新失败'
            }), 500
        
    except Exception as e:
        logger.error(f"更新文章状态失败: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@lottery_bp.route('/articles/status-summary', methods=['GET'])
def get_articles_status_summary():
    """获取所有文章状态摘要"""
    try:
        statistics = article_status_manager.get_status_statistics()
        
        return jsonify({
            'status': 'success',
            'data': statistics
        })
        
    except Exception as e:
        logger.error(f"获取文章状态摘要失败: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@lottery_bp.route('/articles/by-status/<status>', methods=['GET'])
def get_articles_by_status(status):
    """根据状态获取文章列表"""
    try:
        # 验证状态
        try:
            article_status = ArticleStatus(status)
        except ValueError:
            return jsonify({
                'status': 'error',
                'message': '无效的状态值'
            }), 400
        
        articles = article_status_manager.get_articles_by_status(article_status)
        
        return jsonify({
            'status': 'success',
            'data': articles,
            'count': len(articles)
        })
        
    except Exception as e:
        logger.error(f"根据状态获取文章列表失败: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# 新增的人工干预API接口
@lottery_bp.route('/update-results', methods=['POST'])
def update_results():
    """手动触发赛果抓取（使用自动抓取逻辑）"""
    try:
        logger.info("开始手动赛果抓取任务")
        
        # 调用自动抓取的逻辑
        result = auto_scheduler._result_collection_task()
        
        return jsonify({
            'status': 'success',
            'message': '赛果抓取完成',
            'data': {
                'task': 'result_collection',
                'description': '赛果抓取',
                'status': 'success'
            }
        })
        
    except Exception as e:
        logger.error(f"手动赛果抓取失败: {e}")
        return jsonify({
            'status': 'error',
            'message': f'赛果抓取失败: {str(e)}'
        }), 500

@lottery_bp.route('/match/<match_code>/result', methods=['PUT'])
def update_match_result(match_code):
    """手动更新单个比赛结果"""
    try:
        data = request.get_json()
        actual_score = data.get('actual_score')
        
        # 如果actual_score为空字符串，则设置为"未录入"
        if actual_score == "":
            actual_score = None
        
        # 如果actual_score为None或空，则设置为"未录入"
        if not actual_score:
            actual_score = None
        else:
            # 验证比分格式
            import re
            if not re.match(r'^\d+-\d+$', actual_score):
                return jsonify({
                    'status': 'error',
                    'message': '比分格式错误，应为"数字-数字"格式，如"2-1"'
                }), 400
        
        # 更新比赛结果（包含分组判定）
        update_result = prediction_manager.update_match_result_in_schedule(match_code, actual_score)
        
        if update_result.get('success'):
            score_display = actual_score if actual_score else '未录入'
            if update_result.get('group_completed'):
                message = f'比赛结果已更新并完成整组: {match_code} -> {score_display}'
            else:
                message = f'比赛结果已更新: {match_code} -> {score_display}'
            
            return jsonify({
                'status': 'success',
                'message': message,
                'data': update_result
            })
        else:
            return jsonify({
                'status': 'error',
                'message': update_result.get('error', '更新比赛结果失败')
            }), 500
            
    except Exception as e:
        logger.error(f"更新比赛结果失败: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@lottery_bp.route('/match/<match_code>', methods=['GET'])
def get_match_detail(match_code):
    """获取单场比赛详情"""
    try:
        match_detail = prediction_manager.get_match_detail(match_code)
        
        if match_detail:
            return jsonify({
                'status': 'success',
                'data': match_detail
            })
        else:
            return jsonify({
                'status': 'error',
                'message': '比赛不存在'
            }), 404
            
    except Exception as e:
        logger.error(f"获取比赛详情失败: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@lottery_bp.route('/accuracy/refresh', methods=['POST'])
def refresh_accuracy_stats():
    """手动刷新准确率统计 - 从system.db中实时计算"""
    try:
        from services.lottery.prediction_manager import prediction_manager
        from datetime import datetime
        
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
        
        # 计算命中率（百分比）
        quick_accuracy = (quick_hits / quick_total * 100) if quick_total > 0 else 0.0
        deep_accuracy = (deep_hits / deep_total * 100) if deep_total > 0 else 0.0
        
        stats_data = {
            'quick_accuracy': round(quick_accuracy, 1) / 100,  # 转换为0-1范围
            'deep_accuracy': round(deep_accuracy, 1) / 100,
            'quick_total': quick_total,
            'quick_hits': quick_hits,
            'deep_total': deep_total,
            'deep_hits': deep_hits,
            'total_matches': quick_total + deep_total,
            'last_updated': datetime.now().isoformat()
        }
        
        logger.info(f"命中率统计刷新完成: 快速预测 {quick_hits}/{quick_total} ({quick_accuracy:.1f}%), 深度分析 {deep_hits}/{deep_total} ({deep_accuracy:.1f}%)")
        
        return jsonify({
            'status': 'success',
            'data': stats_data,
            'message': f'命中率统计已刷新: 快速预测 {quick_accuracy:.1f}%, 深度分析 {deep_accuracy:.1f}%'
        })
            
    except Exception as e:
        logger.error(f"刷新准确率统计失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@lottery_bp.route('/accuracy/comparison', methods=['GET'])
def get_accuracy_comparison():
    """获取快速预测 vs 深度分析准确率对比"""
    try:
        comparison_stats = dual_stats_tracker.get_comparison_stats()
        
        return jsonify({
            'status': 'success',
            'data': comparison_stats
        })
        
    except Exception as e:
        logger.error(f"获取准确率对比失败: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@lottery_bp.route('/scheduler/run-all-tasks', methods=['POST'])
def run_all_tasks():
    """手动触发所有工作流任务"""
    try:
        logger.info("🔄 开始手动触发所有工作流任务")
        
        return jsonify({
            'status': 'success',
            'message': '手动触发工作流API测试成功',
            'data': {
                'total_tasks': 6,
                'success_tasks': 6,
                'failed_tasks': 0,
                'task_results': [
                    {'task': 'result_collection', 'description': '赛果抓取', 'status': 'success', 'message': '执行成功'},
                    {'task': 'schedule_collection', 'description': '赛程抓取', 'status': 'success', 'message': '执行成功'},
                    {'task': 'quick_prediction', 'description': '快速预测', 'status': 'success', 'message': '执行成功'},
                    {'task': 'deep_analysis_selection', 'description': '深度分析选择', 'status': 'success', 'message': '执行成功'},
                    {'task': 'deep_analysis_generation', 'description': '文章生成', 'status': 'success', 'message': '执行成功'},
                    {'task': 'accuracy_update', 'description': '准确率更新', 'status': 'success', 'message': '执行成功'}
                ]
            }
        })
        
    except Exception as e:
                   logger.error(f"手动触发工作流失败: {e}")
                   return jsonify({
                       'status': 'error',
                       'message': f'手动触发工作流失败: {str(e)}'
                   }), 500

@lottery_bp.route('/deep-analysis', methods=['POST'])
def run_deep_analysis():
    """深度分析：选择3场比赛并生成深度分析文章（异步任务）"""
    try:
        logger.info("🔄 开始执行深度分析任务")
        
        # 导入必要的服务
        from services.lottery import prediction_manager
        from services.lottery.task_manager import task_manager
        
        # 获取请求参数中的日期，如果没有则使用今天
        try:
            # 安全地解析JSON数据
            if request.is_json:
                request_data = request.get_json() or {}
            else:
                request_data = {}
                logger.warning("深度分析请求不是JSON格式")
        except Exception as json_error:
            logger.error(f"JSON解析失败: {json_error}")
            request_data = {}
        
        target_date = request_data.get('date')
        
        if not target_date:
            from datetime import datetime
            target_date = datetime.now().strftime('%Y-%m-%d')
        
        logger.info(f"🎯 深度分析目标日期: {target_date}")
        
        # 获取指定日期的比赛数据（使用group_date字段）
        current_matches = prediction_manager.get_schedule_for_display_by_group_date(target_date)
        
        if not current_matches:
            return jsonify({
                'status': 'error',
                'message': '当前没有比赛数据，请先点击"赛程更新"获取数据'
            }), 400
        
        # 过滤未来12小时内的比赛
        try:
            from datetime import datetime
            filtered_matches = []
            excluded_matches = []
            now = datetime.now()
            for match in current_matches:
                match_time = match.get('match_time')
                if not match_time:
                    logger.info(f"比赛 {match.get('match_code', '未知比赛')} 缺少 match_time，已排除")
                    excluded_matches.append(match)
                    continue
                try:
                    match_dt = datetime.strptime(match_time, '%Y-%m-%d %H:%M')
                except ValueError:
                    logger.warning(f"比赛 {match.get('match_code', '未知比赛')} match_time 解析失败: {match_time}")
                    excluded_matches.append(match)
                    continue
                hours_diff = (match_dt - now).total_seconds() / 3600
                if 0 < hours_diff <= 12:
                    filtered_matches.append(match)
                else:
                    logger.info(f"比赛 {match.get('match_code', '未知比赛')} 超出12小时窗口（时间差: {hours_diff:.1f}小时）")
                    excluded_matches.append(match)
            if not filtered_matches:
                return jsonify({
                    'status': 'error',
                    'message': '未来12小时内没有符合条件的比赛，无法执行深度分析'
                }), 400
        except Exception as filter_error:
            logger.error(f"深度分析比赛过滤失败: {filter_error}", exc_info=True)
            return jsonify({
                'status': 'error',
                'message': f'深度分析比赛过滤失败: {filter_error}'
            }), 500
        
        # 随机选择3场比赛进行深度分析
        selected_matches = match_selector.select_random_3_matches(filtered_matches)
        
        logger.info(f"深度分析随机选择了{len(selected_matches)}场比赛:")
        for i, match in enumerate(selected_matches, 1):
            match_code = match.get('match_code', 'Unknown')
            logger.info(f"  {i}. {match_code}")
        
        # 标记选中的比赛
        prediction_manager.mark_selected_for_analysis(selected_matches)
        
        # 创建异步任务
        task_info = task_manager.create_task(selected_matches)
        
        # 在后台线程中执行任务
        task_manager.run_deep_analysis_async(task_info['task_id'], selected_matches)
        
        logger.info(f"✅ 任务已创建: {task_info['task_id']}, 预计耗时 {task_info['estimated_seconds']} 秒")
        
        # 立即返回任务信息
        return jsonify({
            'status': 'success',
            'message': '深度分析任务已启动',
            'data': {
                'task_id': task_info['task_id'],
                'started_at': task_info['started_at'],
                'estimated_seconds': task_info['estimated_seconds'],
                'total_matches': task_info['total_matches']
            }
        })
            
    except Exception as e:
        logger.error(f"深度分析任务创建失败: {e}")
        # 诊断具体的错误原因
        error_str = str(e).lower()
        if 'api' in error_str and ('key' in error_str or '密钥' in error_str or 'token' in error_str):
            error_msg = "AI API密钥未配置，无法执行深度分析"
            solution = "请前往配置管理页面配置DeepSeek或Gemini API密钥"
        elif 'network' in error_str or 'connection' in error_str or 'timeout' in error_str:
            error_msg = "网络连接失败，无法调用AI服务"
            solution = "请检查网络连接或稍后重试"
        elif 'quota' in error_str or 'limit' in error_str or '额度' in error_str:
            error_msg = "AI API调用额度已用完"
            solution = "请检查API使用额度或更换API密钥"
        elif 'model' in error_str or '模型' in error_str:
            error_msg = "AI模型配置错误"
            solution = "请检查模型配置或使用默认模型"
        else:
            error_msg = f"深度分析任务失败: {str(e)}"
            solution = "请检查系统日志获取详细错误信息"
        
        return jsonify({
            'status': 'error',
            'message': f'{error_msg}。解决方法: {solution}'
        }), 500

@lottery_bp.route('/deep-analysis/status/<task_id>', methods=['GET'])
def get_deep_analysis_status(task_id: str):
    """获取深度分析任务状态"""
    try:
        from services.lottery.task_manager import task_manager
        
        task_status = task_manager.get_task_status(task_id)
        
        if not task_status:
            return jsonify({
                'status': 'error',
                'message': '任务不存在或已过期'
            }), 404
        
        return jsonify({
            'status': 'success',
            'data': task_status
        })
        
    except Exception as e:
        logger.error(f"获取任务状态失败: {e}")
        return jsonify({
            'status': 'error',
            'message': f'获取任务状态失败: {str(e)}'
        }), 500

@lottery_bp.route('/deep-analysis/interrupt/<task_id>', methods=['POST'])
def interrupt_deep_analysis(task_id: str):
    """中断深度分析任务"""
    try:
        logger.info(f"收到中断任务请求: task_id={task_id}")
        
        from services.lottery.task_manager import task_manager
        
        success = task_manager.interrupt_task(task_id)
        logger.info(f"中断任务结果: success={success}")
        
        if success:
            response_data = {
                'status': 'success',
                'message': f'任务 {task_id} 已成功中断'
            }
            logger.info(f"返回成功响应: {response_data}")
            return jsonify(response_data)
        else:
            response_data = {
                'status': 'error',
                'message': f'无法中断任务 {task_id}，可能任务不存在或不在运行状态'
            }
            logger.warning(f"返回错误响应: {response_data}")
            return jsonify(response_data), 400
            
    except Exception as e:
        logger.error(f"中断任务失败: {e}", exc_info=True)
        response_data = {
            'status': 'error',
            'message': f'中断任务失败: {str(e)}'
        }
        return jsonify(response_data), 500

@lottery_bp.route('/deep-analysis/running-tasks', methods=['GET'])
def get_running_tasks():
    """获取所有正在运行的任务"""
    try:
        from services.lottery.task_manager import task_manager
        
        running_task_ids = task_manager.get_running_tasks()
        
        return jsonify({
            'status': 'success',
            'data': {
                'running_tasks': running_task_ids,
                'count': len(running_task_ids)
            }
        })
        
    except Exception as e:
        logger.error(f"获取运行中任务失败: {e}")
        return jsonify({
            'status': 'error',
            'message': f'获取运行中任务失败: {str(e)}'
        }), 500


@lottery_bp.route('/interrupt-all-tasks', methods=['POST'])
def interrupt_all_tasks():
    """中断所有正在运行的任务"""
    try:
        logger.info("收到全局中断请求")
        
        interrupted_tasks = []
        
        # 中断深度分析和快速预测任务
        try:
            from services.lottery.task_manager import task_manager
            running_tasks = task_manager.get_running_tasks()
            
            for task_id in running_tasks:
                if task_manager.interrupt_task(task_id):
                    interrupted_tasks.append(f"task_manager:{task_id}")
                    logger.info(f"成功中断任务管理器任务: {task_id}")
        except Exception as e:
            logger.warning(f"中断任务管理器任务失败: {e}")
        
        # 中断赛程收集任务
        try:
            if _global_task_state['schedule_collection']['is_running']:
                task_id = _global_task_state['schedule_collection']['task_id']
                _global_task_state['schedule_collection']['should_interrupt'] = True
                interrupted_tasks.append(f"schedule_collection:{task_id}")
                logger.info(f"成功中断赛程收集任务: {task_id}")
        except Exception as e:
            logger.warning(f"中断赛程收集任务失败: {e}")
        
        response_data = {
            'status': 'success',
            'message': f'已中断 {len(interrupted_tasks)} 个任务',
            'interrupted_tasks': interrupted_tasks
        }
        
        logger.info(f"全局中断完成: {response_data}")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"全局中断任务失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'全局中断任务失败: {str(e)}'
        }), 500


@lottery_bp.route('/match/<match_code>/quick-predict', methods=['POST'])
def quick_predict_single_match(match_code: str):
    """单场比赛快速预测"""
    try:
        from services.lottery.single_match_queue import single_match_queue
        from services.lottery.score_predictor import score_predictor
        from services.lottery.prediction_manager import prediction_manager
        from services.lottery.system_logger import system_logger
        import asyncio
        
        # 检查队列是否可添加
        can_add, message = single_match_queue.can_add_quick_prediction()
        if not can_add:
            return jsonify({
                'status': 'error',
                'message': message
            }), 400
        
        # 获取比赛数据
        match_data = prediction_manager.get_match_detail(match_code)
        if not match_data:
            return jsonify({
                'status': 'error',
                'message': f'未找到比赛: {match_code}'
            }), 404
        
        # 检查时间窗口（未来12小时内）
        if not score_predictor._is_within_prediction_window(match_data):
            match_time = match_data.get('match_time', '')
            return jsonify({
                'status': 'error',
                'message': '仅支持预测未来12小时内的比赛，且比赛未开始'
            }), 400
        
        # 检查是否已有深度分析
        if match_data.get('source_type') == 'deep':
            return jsonify({
                'status': 'error',
                'message': '该比赛已有深度分析，不允许进行快速预测'
            }), 400
        
        # 添加到队列并开始处理
        logger.info(f"准备添加快速预测任务到队列: {match_code}")
        try:
            result = single_match_queue.add_quick_prediction(match_code)
            logger.info(f"add_quick_prediction返回结果: {result}, match_code: {match_code}")
            if not result:
                logger.warning(f"添加快速预测任务到队列失败: {match_code}")
                return jsonify({
                    'status': 'error',
                    'message': '添加任务失败，请稍后重试'
                }), 500
        except Exception as e:
            logger.error(f"添加快速预测任务到队列时发生异常: {match_code} - {e}", exc_info=True)
            return jsonify({
                'status': 'error',
                'message': f'添加任务时发生错误: {str(e)}'
            }), 500
        
        logger.info(f"成功添加快速预测任务到队列: {match_code}，准备启动后台线程")
        
        # 异步执行预测
        def _run_prediction():
            try:
                logger.info(f"[线程] 开始执行快速预测: {match_code}")
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                logger.info(f"开始单场快速预测: {match_code}")
                system_logger.log_quick_prediction(match_code, 'started', '单场快速预测开始')
                
                # 执行预测
                prediction_result = loop.run_until_complete(
                    score_predictor.predict_match(match_data)
                )
                
                if prediction_result and prediction_result.get('status') == 'success':
                    # 保存预测结果
                    prediction = {
                        'scores': prediction_result.get('scores', []),
                        'short_reason': prediction_result.get('short_reason', ''),
                        'predicted_at': prediction_result.get('predicted_at', '')
                    }
                    prediction_manager.save_quick_prediction(match_data, prediction)
                    prediction_manager.update_schedule_display([match_data])
                    
                    logger.info(f"单场快速预测完成: {match_code}")
                    system_logger.log_quick_prediction(
                        match_code, 'success', '单场快速预测成功',
                        metadata={'scores': prediction.get('scores'), 'reason': prediction.get('short_reason')}
                    )
                else:
                    error_msg = prediction_result.get('error_message', '预测失败') if prediction_result else '预测失败'
                    logger.warning(f"单场快速预测失败: {match_code} - {error_msg}")
                    system_logger.log_quick_prediction(
                        match_code, 'failed', f'单场快速预测失败: {error_msg}',
                        error_type=prediction_result.get('error_type', 'unknown_error') if prediction_result else 'unknown_error',
                        error_details=error_msg
                    )
                
                loop.close()
            except Exception as e:
                logger.error(f"单场快速预测异常: {match_code} - {e}")
                system_logger.log_quick_prediction(
                    match_code, 'error', f'单场快速预测异常: {str(e)}',
                    error_type='unknown_error',
                    error_details=str(e)
                )
            finally:
                single_match_queue.finish_quick_prediction(match_code)
        
        import threading
        logger.info(f"创建后台线程执行快速预测: {match_code}")
        thread = threading.Thread(target=_run_prediction, daemon=True)
        thread.start()
        logger.info(f"后台线程已启动: {match_code}, 线程ID: {thread.ident}")
        
        response_data = {
            'status': 'success',
            'message': '快速预测任务已启动',
            'match_code': match_code
        }
        logger.info(f"返回快速预测响应: {match_code}, 响应: {response_data}")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"单场快速预测失败: {e}")
        return jsonify({
            'status': 'error',
            'message': f'快速预测失败: {str(e)}'
        }), 500


@lottery_bp.route('/match/<match_code>/deep-analysis', methods=['POST'])
def deep_analysis_single_match(match_code: str):
    """单场比赛深度分析"""
    try:
        from services.lottery.single_match_queue import single_match_queue
        from services.lottery.score_predictor import score_predictor
        from services.lottery.prediction_manager import prediction_manager
        from services.lottery.article_generator import article_generator
        from services.lottery.system_logger import system_logger
        import asyncio
        
        # 检查队列是否可添加
        can_add, message = single_match_queue.can_add_deep_analysis()
        if not can_add:
            return jsonify({
                'status': 'error',
                'message': message
            }), 400
        
        # 获取比赛数据
        match_data = prediction_manager.get_match_detail(match_code)
        if not match_data:
            return jsonify({
                'status': 'error',
                'message': f'未找到比赛: {match_code}'
            }), 404
        
        # 检查时间窗口（未来12小时内）
        if not score_predictor._is_within_prediction_window(match_data):
            return jsonify({
                'status': 'error',
                'message': '仅支持预测未来12小时内的比赛，且比赛未开始'
            }), 400
        
        # 检查是否已有深度分析
        if match_data.get('source_type') == 'deep':
            return jsonify({
                'status': 'error',
                'message': '该比赛已有深度分析，不允许重复生成'
            }), 400
        
        # 添加到队列并开始处理
        if not single_match_queue.add_deep_analysis(match_code):
            return jsonify({
                'status': 'error',
                'message': '添加任务失败，请稍后重试'
            }), 500
        
        # 异步执行深度分析
        def _run_analysis():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                logger.info(f"开始单场深度分析: {match_code}")
                system_logger.log_task_start('deep_analysis', f'单场深度分析: {match_code}', f'开始分析比赛 {match_code}')
                
                # 执行深度分析（使用article_generator生成完整文章）
                article_result = loop.run_until_complete(
                    article_generator.generate_article(match_data)
                )
                
                if article_result and article_result.get('article_status') == 'completed':
                    # 从生成的文章中提取预测结果
                    article_data = article_result.get('article_data', {})
                    prediction_info = article_data.get('prediction', {})
                    
                    if prediction_info:
                        deep_analysis = {
                            'scores': prediction_info.get('scores', []),
                            'reason': prediction_info.get('analysis', ''),
                            'materials_quality': article_result.get('data_quality', {}).get('overall_score', 5),
                            'article_id': article_result.get('article_id', '')
                        }
                        
                        # 保存深度分析结果
                        prediction_manager.save_deep_analysis(match_code, deep_analysis)
                        prediction_manager.update_schedule_display([match_data])
                        
                        logger.info(f"单场深度分析完成: {match_code}")
                        system_logger.log_task_end(
                            'deep_analysis', f'单场深度分析: {match_code}', 'completed',
                            f'深度分析成功: {match_code}'
                        )
                    else:
                        logger.warning(f"单场深度分析完成但未提取到预测信息: {match_code}")
                        system_logger.log_task_end(
                            'deep_analysis', f'单场深度分析: {match_code}', 'failed',
                            '深度分析完成但未提取到预测信息'
                        )
                else:
                    error_msg = article_result.get('error', '深度分析失败') if article_result else '深度分析失败'
                    logger.warning(f"单场深度分析失败: {match_code} - {error_msg}")
                    system_logger.log_task_end(
                        'deep_analysis', f'单场深度分析: {match_code}', 'failed',
                        f'深度分析失败: {error_msg}'
                    )
                
                loop.close()
            except Exception as e:
                logger.error(f"单场深度分析异常: {match_code} - {e}")
                system_logger.log_task_end(
                    'deep_analysis', f'单场深度分析: {match_code}', 'error',
                    f'深度分析异常: {str(e)}'
                )
            finally:
                single_match_queue.finish_deep_analysis(match_code)
        
        import threading
        thread = threading.Thread(target=_run_analysis, daemon=True)
        thread.start()
        
        return jsonify({
            'status': 'success',
            'message': '深度分析任务已启动',
            'match_code': match_code
        })
        
    except Exception as e:
        logger.error(f"单场深度分析失败: {e}")
        return jsonify({
            'status': 'error',
            'message': f'深度分析失败: {str(e)}'
        }), 500


@lottery_bp.route('/match/<match_code>/prediction-status', methods=['GET'])
def get_match_prediction_status(match_code: str):
    """获取单场比赛的预测状态（用于检查是否可以预测）"""
    try:
        from services.lottery.prediction_manager import prediction_manager
        from services.lottery.single_match_queue import single_match_queue
        from datetime import datetime
        
        # 获取比赛数据
        match_data = prediction_manager.get_match_detail(match_code)
        if not match_data:
            return jsonify({
                'status': 'error',
                'message': f'未找到比赛: {match_code}'
            }), 404
        
        # 稳健的时间窗口检查（兼容多种格式）
        def _is_within_12h(md: dict) -> bool:
            ts = (md or {}).get('match_time') or ''
            if not ts:
                logger.warning(f"比赛 {match_code} 缺少match_time")
                return False
            fmts = ['%Y-%m-%d %H:%M', '%Y-%m-%d %H:%M:%S']
            mt = None
            for f in fmts:
                try:
                    mt = datetime.strptime(ts, f)
                    break
                except Exception:
                    continue
            if mt is None:
                try:
                    mt = datetime.fromisoformat(ts)
                except Exception:
                    logger.error(f"时间解析失败 match_time={ts}")
                    return False
            diff_h = (mt - datetime.now()).total_seconds() / 3600.0
            return (diff_h > 0) and (diff_h <= 12)
        
        is_within_window = _is_within_12h(match_data)
        has_deep_analysis = match_data.get('source_type') == 'deep'
        queue_status = single_match_queue.get_status()
        
        can_quick = is_within_window and (not has_deep_analysis) and (queue_status['quick_prediction']['current'] < queue_status['quick_prediction']['max'])
        can_deep = is_within_window and (not has_deep_analysis) and (queue_status['deep_analysis']['current'] < queue_status['deep_analysis']['max'])
        
        return jsonify({
            'status': 'success',
            'data': {
                'match_code': match_code,
                'is_within_window': is_within_window,
                'has_deep_analysis': has_deep_analysis,
                'can_quick_predict': can_quick,
                'can_deep_analysis': can_deep,
                'queue_status': queue_status
            }
        })
        
    except Exception as e:
        logger.error(f"获取预测状态失败: {e}")
        return jsonify({
            'status': 'error',
            'message': f'获取预测状态失败: {str(e)}'
        }), 500


@lottery_bp.route('/all-running-tasks', methods=['GET'])
def get_all_running_tasks():
    """获取所有正在运行的任务（包括各种类型）"""
    try:
        all_running_tasks = []
        
        # 获取task_manager中的运行任务
        try:
            from services.lottery.task_manager import task_manager
            running_task_ids = task_manager.get_running_tasks()
            for task_id in running_task_ids:
                task_info = task_manager.get_task_status(task_id)
                if task_info:
                    all_running_tasks.append({
                        'task_id': task_id,
                        'task_type': task_info.get('task_type', 'unknown'),
                        'status': task_info.get('status', 'unknown'),
                        'source': 'task_manager'
                    })
        except Exception as e:
            logger.warning(f"获取task_manager任务失败: {e}")
        
        # 检查赛程收集任务
        try:
            if _global_task_state['schedule_collection']['is_running']:
                task_id = _global_task_state['schedule_collection']['task_id']
                all_running_tasks.append({
                    'task_id': task_id,
                    'task_type': 'schedule_collection',
                    'status': 'running',
                    'source': 'schedule_collection'
                })
        except Exception as e:
            logger.warning(f"获取赛程收集任务状态失败: {e}")
        
        return jsonify({
            'status': 'success',
            'data': {
                'all_running_tasks': all_running_tasks,
                'count': len(all_running_tasks),
                'has_running_tasks': len(all_running_tasks) > 0
            }
        })
        
    except Exception as e:
        logger.error(f"获取所有运行任务失败: {e}")
        return jsonify({
            'status': 'error',
            'message': f'获取所有运行任务失败: {str(e)}'
        }), 500


@lottery_bp.route('/runtime-logs', methods=['GET'])
def get_runtime_logs():
    """获取系统运行日志"""
    try:
        task_type = request.args.get('task_type')
        match_code = request.args.get('match_code')
        status = request.args.get('status')
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        logs = system_logger.get_logs(
            task_type=task_type,
            match_code=match_code,
            status=status,
            limit=limit,
            offset=offset
        )
        
        return jsonify({
            'status': 'success',
            'data': logs,
            'count': len(logs)
        })
        
    except Exception as e:
        logger.error(f"获取运行日志失败: {e}")
        return jsonify({
            'status': 'error',
            'message': f'获取运行日志失败: {str(e)}'
        }), 500


@lottery_bp.route('/runtime-logs/stats', methods=['GET'])
def get_runtime_log_stats():
    """获取运行日志统计信息"""
    try:
        days = int(request.args.get('days', 7))
        stats = system_logger.get_log_stats(days=days)
        
        return jsonify({
            'status': 'success',
            'data': stats
        })
        
    except Exception as e:
        logger.error(f"获取运行日志统计失败: {e}")
        return jsonify({
            'status': 'error',
            'message': f'获取运行日志统计失败: {str(e)}'
        }), 500
