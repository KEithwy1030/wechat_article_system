"""
竞彩数据控制器
处理竞彩相关的API请求
"""
import asyncio
import logging
from flask import jsonify, request
from typing import Dict, Any

logger = logging.getLogger(__name__)

class SportteryController:
    """竞彩数据控制器"""
    
    def __init__(self):
        self.logger = logger
    
    def get_matches(self) -> Dict[str, Any]:
        """获取竞彩比赛数据"""
        try:
            self.logger.info("开始获取竞彩比赛数据")
            
            # 运行异步函数
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            from services.sporttery_service import sporttery_service
            result = loop.run_until_complete(sporttery_service.get_matches_data())
            
            loop.close()
            
            if result['success']:
                # 格式化数据用于前端显示
                formatted_matches = sporttery_service.format_matches_for_display(result['data'])
                result['data'] = formatted_matches
            
            self.logger.info(f"竞彩比赛数据获取完成，共 {result['total']} 场比赛")
            return result
            
        except Exception as e:
            self.logger.error(f"获取竞彩比赛数据失败: {str(e)}")
            return {
                'success': False,
                'data': [],
                'total': 0,
                'message': f'获取竞彩比赛数据失败: {str(e)}',
                'error': str(e)
            }
    
    def get_results(self) -> Dict[str, Any]:
        """获取竞彩赛果数据"""
        try:
            self.logger.info("开始获取竞彩赛果数据")
            
            # 获取请求参数
            days_back = request.args.get('days_back', 3, type=int)
            
            # 运行异步函数
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            from services.sporttery_service import sporttery_service
            result = loop.run_until_complete(sporttery_service.get_results_data(days_back))
            
            loop.close()
            
            self.logger.info(f"竞彩赛果数据获取完成，共 {result['total']} 条赛果")
            return result
            
        except Exception as e:
            self.logger.error(f"获取竞彩赛果数据失败: {str(e)}")
            return {
                'success': False,
                'data': [],
                'total': 0,
                'message': f'获取竞彩赛果数据失败: {str(e)}',
                'error': str(e)
            }
    
    def refresh_data(self) -> Dict[str, Any]:
        """刷新竞彩数据"""
        try:
            self.logger.info("开始刷新竞彩数据")
            
            # 运行异步函数
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            from services.sporttery_service import sporttery_service
            
            # 同时获取比赛和赛果数据
            matches_task = sporttery_service.get_matches_data()
            results_task = sporttery_service.get_results_data()
            
            matches_result, results_result = loop.run_until_complete(
                asyncio.gather(matches_task, results_task)
            )
            
            loop.close()
            
            return {
                'success': True,
                'matches': matches_result,
                'results': results_result,
                'message': f'数据刷新完成：{matches_result["total"]} 场比赛，{results_result["total"]} 条赛果',
                'timestamp': matches_result.get('timestamp')
            }
            
        except Exception as e:
            self.logger.error(f"刷新竞彩数据失败: {str(e)}")
            return {
                'success': False,
                'message': f'刷新竞彩数据失败: {str(e)}',
                'error': str(e)
            }


# 创建控制器实例
sporttery_controller = SportteryController()
