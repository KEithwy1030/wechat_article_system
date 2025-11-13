"""
竞彩数据服务 - 专门用于微信公众号系统
集成现有的竞彩抓取功能
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
import json

logger = logging.getLogger(__name__)

class SportteryService:
    """竞彩数据服务"""
    
    def __init__(self):
        self.base_url = 'https://www.sporttery.cn/jc/zqszsc/'
        self.logger = logger
    
    async def get_matches_data(self) -> Dict:
        """获取竞彩比赛数据"""
        try:
            # 导入快速抓取器
            from .fast_real_scraper import FastRealScraper
            
            scraper = FastRealScraper()
            result = await scraper.collect_all_matches()
            
            if result.get('matches'):
                return {
                    'success': True,
                    'data': result['matches'],
                    'total': len(result['matches']),
                    'message': f'成功获取 {len(result["matches"])} 场比赛数据',
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'success': False,
                    'data': [],
                    'total': 0,
                    'message': '未获取到比赛数据',
                    'error': result.get('error', '未知错误'),
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"获取竞彩数据失败: {str(e)}")
            return {
                'success': False,
                'data': [],
                'total': 0,
                'message': f'获取竞彩数据失败: {str(e)}',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def get_results_data(self, days_back: int = 3) -> Dict:
        """获取竞彩赛果数据 - 支持备选数据源"""
        try:
            self.logger.info("开始获取赛果数据...")
            
            # 主要数据源：竞彩官网
            try:
                from .sporttery_results_scraper import SportteryResultsScraper
                scraper = SportteryResultsScraper()
                results = await scraper.scrape_results(days_back=days_back, max_retries=2)
                
                if results:
                    self.logger.info(f"成功从竞彩官网获取到 {len(results)} 条赛果数据")
                    
                    # 统一更新缓存（手动抓取的赛果也要更新到显示缓存）
                    await self._update_cache_with_results(results, source="手动抓取")
                    
                    return {
                        'success': True,
                        'data': results,
                        'total': len(results),
                        'message': f'成功获取 {len(results)} 条赛果数据',
                        'source': '竞彩官网',
                        'timestamp': datetime.now().isoformat()
                    }
            except Exception as e:
                self.logger.warning(f"竞彩官网数据源失败: {e}")
            
            # 备选数据源1：从数据库获取历史数据
            try:
                historical_results = await self._get_historical_results()
                if historical_results:
                    self.logger.info(f"从历史数据获取到 {len(historical_results)} 条赛果数据")
                    return {
                        'success': True,
                        'data': historical_results,
                        'total': len(historical_results),
                        'message': f'获取历史赛果数据成功，共 {len(historical_results)} 条',
                        'source': '历史数据',
                        'timestamp': datetime.now().isoformat()
                    }
            except Exception as e:
                self.logger.warning(f"历史数据源失败: {e}")
            
            # 备选数据源2：从缓存获取
            try:
                cached_results = await self._get_cached_results()
                if cached_results:
                    self.logger.info(f"从缓存获取到 {len(cached_results)} 条赛果数据")
                    return {
                        'success': True,
                        'data': cached_results,
                        'total': len(cached_results),
                        'message': f'获取缓存赛果数据成功，共 {len(cached_results)} 条',
                        'source': '缓存数据',
                        'timestamp': datetime.now().isoformat()
                    }
            except Exception as e:
                self.logger.warning(f"缓存数据源失败: {e}")
            
            # 所有数据源都失败
            self.logger.warning("所有数据源均失败，返回空数据")
            return {
                'success': False,
                'data': [],
                'total': 0,
                'message': '未获取到赛果数据，所有数据源均不可用',
                'timestamp': datetime.now().isoformat()
            }
                
        except Exception as e:
            self.logger.error(f"获取竞彩赛果失败: {str(e)}")
            return {
                'success': False,
                'data': [],
                'total': 0,
                'message': f'获取竞彩赛果失败: {str(e)}',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def _get_historical_results(self):
        """从数据库获取历史赛果数据"""
        try:
            from .lottery.prediction_manager import prediction_manager
            
            # 获取最近3天的历史数据，使用现有的get_schedule_for_display方法
            from datetime import datetime, timedelta
            results = []
            
            # 获取最近3天的数据
            for i in range(3):
                target_date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
                historical_data = prediction_manager.get_schedule_for_display(target_date)
                
                for match in historical_data:
                    # 只获取有实际比分的比赛（已结束的比赛）
                    actual_score = match.get('actual_score')
                    if actual_score and actual_score.strip() and actual_score != '未录入':
                        results.append({
                            'match_code': match.get('match_code'),
                            'home_team': match.get('home_team'),
                            'away_team': match.get('away_team'),
                            'full_score': actual_score,
                            'match_date': match.get('match_date'),
                            'league': match.get('league'),
                            'scraped_at': datetime.now().isoformat(),
                            'source': '历史数据'
                        })
            
            return results
        except Exception as e:
            self.logger.error(f"获取历史数据失败: {e}")
            return []
    
    async def _get_cached_results(self):
        """从缓存获取赛果数据"""
        try:
            import os
            from datetime import timedelta
            
            cache_file = "cache/sporttery_results_cache.json"
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                # 检查缓存是否过期（1小时）
                cache_time = datetime.fromisoformat(cache_data.get('timestamp', '1970-01-01'))
                if datetime.now() - cache_time < timedelta(hours=1):
                    return cache_data.get('results', [])
            
            return []
        except Exception as e:
            self.logger.error(f"获取缓存数据失败: {e}")
            return []
    
    def format_matches_for_display(self, matches: List[Dict]) -> List[Dict]:
        """格式化比赛数据用于前端显示"""
        formatted_matches = []
        
        for match in matches:
            formatted_match = {
                'match_code': match.get('match_code', ''),
                'home_team': match.get('home_team', ''),
                'away_team': match.get('away_team', ''),
                'league': match.get('league', ''),
                'match_time': match.get('match_time', ''),
                'status': match.get('status', 'pending'),
                'actual_score': match.get('actual_score', ''),
                'display_text': f"{match.get('home_team', '')} vs {match.get('away_team', '')}",
                'time_display': self._format_time_display(match.get('match_time', '')),
                'league_display': match.get('league', '未知联赛')
            }
            formatted_matches.append(formatted_match)
        
        return formatted_matches
    
    def _format_time_display(self, match_time: str) -> str:
        """格式化时间显示"""
        if not match_time:
            return '时间未知'
        
        try:
            # 解析时间格式：2024-01-01 15:30
            if ' ' in match_time:
                date_part, time_part = match_time.split(' ')
                return f"{date_part} {time_part}"
            return match_time
        except:
            return match_time
    
    async def _update_cache_with_results(self, results: List[Dict], source: str = "未知") -> int:
        """统一更新缓存中的赛果数据"""
        try:
            from .lottery.prediction_manager import prediction_manager
            
            updated_count = 0
            for match_result in results:
                match_code = match_result.get('match_code')
                full_score = match_result.get('full_score')
                
                if match_code and full_score:
                    try:
                        update_info = prediction_manager.update_match_result_in_schedule(
                            match_code,
                            full_score,
                            match_result.get('half_score')
                        )
                        if update_info.get('success'):
                            updated_count += 1
                            if update_info.get('group_completed'):
                                self.logger.info(f"[{source}] 分组 {update_info.get('group_date')} 已完成，缓存命中率刷新")
                            self.logger.info(f"[{source}] 已更新缓存中比赛 {match_code} 的赛果: {full_score}")
                        else:
                            self.logger.warning(f"[{source}] 更新缓存失败: {match_code} -> {update_info.get('error', '未知错误')}")
                    except Exception as e:
                        self.logger.error(f"[{source}] 更新缓存单个比赛结果失败 {match_code}: {e}")
            
            self.logger.info(f"[{source}] 缓存更新完成，共更新了 {updated_count} 场比赛")
            return updated_count
            
        except Exception as e:
            self.logger.error(f"[{source}] 更新缓存失败: {e}")
            return 0

# 创建服务实例
sporttery_service = SportteryService()
