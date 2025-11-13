"""
三源数据搜集系统
整合竞彩官网、AI联网搜索、截图AI识别三个数据源
"""

import asyncio
import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from .lottery_scraper import lottery_scraper
from .score_predictor import score_predictor

logger = logging.getLogger(__name__)

class ThreeSourceCollector:
    """三源数据搜集器"""
    
    def __init__(self):
        self.lottery_scraper = lottery_scraper
        self.score_predictor = score_predictor
        self.cache_folder = "cache/three_source_data"
        
        # 确保缓存文件夹存在
        os.makedirs(self.cache_folder, exist_ok=True)
        
        logger.info("三源数据搜集系统初始化完成")
    
    def _get_zhipu_service(self):
        """延迟加载智谱AI服务"""
        try:
            from services.zhipu_service import zhipu_service
            return zhipu_service
        except Exception as e:
            logger.error(f"智谱AI服务加载失败: {str(e)}")
            return None
    
    def _get_screenshot_generator(self):
        """延迟加载截图生成器"""
        try:
            from services.sports_screenshot_generator import sports_screenshot_generator
            return sports_screenshot_generator
        except Exception as e:
            logger.error(f"截图生成器加载失败: {str(e)}")
            return None
    
    def _get_screenshot_analyzer(self):
        """延迟加载截图分析器"""
        try:
            from services.sports_screenshot_analyzer import sports_screenshot_analyzer
            return sports_screenshot_analyzer
        except Exception as e:
            logger.error(f"截图分析器加载失败: {str(e)}")
            return None
    
    def _get_deepseek_service(self):
        """延迟加载DeepSeek服务"""
        try:
            from services.deepseek_service import deepseek_service
            return deepseek_service
        except Exception as e:
            logger.error(f"DeepSeek服务加载失败: {str(e)}")
            return None
    
    async def collect_match_data(self, match_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        为单场比赛搜集三源数据
        :param match_info: 比赛基本信息
        :return: 整合后的三源数据
        """
        match_id = match_info.get('match_id', 'unknown')
        logger.info(f"开始搜集比赛 {match_id} 的三源数据")
        
        result = {
            'match_id': match_id,
            'match_info': match_info,
            'source_1': None,  # 竞彩官网数据
            'source_2': None,  # AI联网搜索数据
            'source_3': None,  # 截图AI识别数据
            'collected_at': datetime.now().isoformat(),
            'status': 'collecting'
        }
        
        try:
            # 并行搜集三个数据源
            tasks = [
                self._collect_source_1(match_info),
                self._collect_source_2(match_info),
                self._collect_source_3(match_info)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理结果
            for i, res in enumerate(results):
                if isinstance(res, Exception):
                    logger.error(f"数据源 {i+1} 搜集失败: {str(res)}")
                    result[f'source_{i+1}'] = {'error': str(res)}
                else:
                    result[f'source_{i+1}'] = res
            
            # 整合数据
            integrated_data = self._integrate_three_sources(result)
            result['integrated_data'] = integrated_data
            result['status'] = 'completed'
            
            # 保存到缓存
            self._save_to_cache(match_id, result)
            
            logger.info(f"比赛 {match_id} 三源数据搜集完成")
            return result
            
        except Exception as e:
            logger.error(f"搜集比赛 {match_id} 三源数据失败: {str(e)}")
            result['status'] = 'failed'
            result['error'] = str(e)
            return result
    
    async def _collect_source_1(self, match_info: Dict[str, Any]) -> Dict[str, Any]:
        """搜集源1：竞彩官网数据"""
        logger.info("搜集源1：竞彩官网数据")
        
        max_attempts = 3
        last_error = None
        
        for attempt in range(1, max_attempts + 1):
            try:
                scraped_result = await self.lottery_scraper.fetch_schedule()
            except Exception as e:
                last_error = str(e)
                logger.warning(f"源1抓取异常，第 {attempt}/{max_attempts} 次: {last_error}")
            else:
                if scraped_result.get('success'):
                    # 从抓取结果中查找当前比赛
                    matches = scraped_result.get('matches', [])
                    match_code = match_info.get('match_code', '')
                    
                    match_data = None
                    for match in matches:
                        if match.get('match_code') == match_code:
                            match_data = match
                            break
                    
                    return {
                        'source': 'lottery_official',
                        'data': match_data or {},
                        'all_matches_count': len(matches),
                        'collected_at': datetime.now().isoformat(),
                        'status': 'success' if match_data else 'not_found'
                    }
                else:
                    last_error = scraped_result.get('error', '抓取失败')
                    logger.warning(f"源1抓取失败，第 {attempt}/{max_attempts} 次: {last_error}")
            
            if attempt < max_attempts:
                await asyncio.sleep(2 * attempt)
        
        logger.error(f"源1抓取连续失败，已放弃: {last_error}")
        return {
            'source': 'lottery_official',
            'error': last_error or '抓取失败',
            'collected_at': datetime.now().isoformat(),
            'status': 'failed',
            'attempts': max_attempts
        }
    
    async def _collect_source_2(self, match_info: Dict[str, Any]) -> Dict[str, Any]:
        """搜集源2：AI联网搜索数据（使用score_predictor）"""
        logger.info("搜集源2：AI联网搜索数据")
        
        max_attempts = 3
        last_error = None
        
        for attempt in range(1, max_attempts + 1):
            try:
                prediction_result = await self.score_predictor.predict_match(match_info)
            except Exception as e:
                last_error = str(e)
                logger.warning(f"源2联网预测异常，第 {attempt}/{max_attempts} 次: {last_error}")
            else:
                status = prediction_result.get('status')
                if status == 'success':
                    return {
                        'source': 'ai_web_search',
                        'data': prediction_result,
                        'collected_at': datetime.now().isoformat(),
                        'status': 'success'
                    }
                else:
                    last_error = prediction_result.get('error') or prediction_result.get('error_message') or '预测失败'
                    logger.warning(f"源2联网预测失败，第 {attempt}/{max_attempts} 次: {last_error}")
            
            if attempt < max_attempts:
                await asyncio.sleep(2 * attempt)
        
        logger.error(f"源2联网预测连续失败，已放弃: {last_error}")
        return {
            'source': 'ai_web_search',
            'error': last_error or '预测失败',
            'collected_at': datetime.now().isoformat(),
            'status': 'failed',
            'attempts': max_attempts
        }
    
    async def _collect_source_3(self, match_info: Dict[str, Any]) -> Dict[str, Any]:
        """搜集源3：专业体育数据网站截图分析（增强版 - 主动生成截图）"""
        try:
            logger.info("搜集源3：专业体育数据网站截图分析")
            
            # 确保智谱AI服务已加载配置（避免新进程未加载导致API密钥为空）
            try:
                from services.zhipu_service import zhipu_service
                if not getattr(zhipu_service, 'api_key', None):
                    from services.config_service import config_service
                    _zcfg = config_service.get_zhipu_config()
                    api_key = _zcfg.get('api_key')
                    model = _zcfg.get('model')
                    if api_key and model:
                        zhipu_service.set_config(api_key=api_key, model=model)
                        logger.info("已为智谱AI服务自动加载配置")
            except Exception as _e:
                logger.warning(f"自动加载智谱AI配置失败: {_e}")
            
            # 获取截图生成器
            screenshot_generator = self._get_screenshot_generator()
            if not screenshot_generator:
                return {
                    'source': 'screenshot_ai',
                    'error': '截图生成器未配置',
                    'collected_at': datetime.now().isoformat(),
                    'status': 'failed'
                }
            
            # 获取截图分析器
            screenshot_analyzer = self._get_screenshot_analyzer()
            if not screenshot_analyzer:
                return {
                    'source': 'screenshot_ai',
                    'error': '截图分析器未配置',
                    'collected_at': datetime.now().isoformat(),
                    'status': 'failed'
                }
            
            # 快速检测目标站点连通性，避免无意义重试
            primary_site = "https://www.soccerstats.com/"
            if not await self._check_site_reachable(primary_site):
                logger.warning(f"截图站点无法访问，跳过截图流程: {primary_site}")
                return {
                    'source': 'screenshot_ai',
                    'error': '目标站点无法访问',
                    'note': '网络不可达，未生成截图',
                    'collected_at': datetime.now().isoformat(),
                    'status': 'no_screenshot'
                }
            
            match_code = match_info.get('match_code', '')
            league = match_info.get('league', '')
            home_team = match_info.get('home_team', '')
            away_team = match_info.get('away_team', '')
            
            max_attempts = 3
            last_error = None
            
            for attempt in range(1, max_attempts + 1):
                # 快速检测目标站点连通性，避免无意义重试
                primary_site = "https://www.soccerstats.com/"
                if not await self._check_site_reachable(primary_site):
                    last_error = '目标站点无法访问'
                    logger.warning(f"截图站点无法访问，第 {attempt}/{max_attempts} 次: {primary_site}")
                else:
                    # 构建新的文件命名格式：screenshot_{周x}{主任编号} {联赛类型} {对阵双方}.png
                    screenshot_filename = f"screenshot_{match_code} {league} {home_team}vs{away_team}.png"
                    screenshot_path = os.path.join(self.cache_folder, screenshot_filename)
                    
                    logger.info(f"开始为比赛 {match_code} 生成截图: {screenshot_filename} (尝试 {attempt}/{max_attempts})")
                    
                    generation_result = await screenshot_generator.generate_specific_match_screenshot(
                        match_info=match_info,
                        target_path=screenshot_path
                    )
                    
                    if generation_result.get('success', False):
                        logger.info(f"截图生成成功: {screenshot_path}")
                        
                        if not os.path.exists(screenshot_path):
                            last_error = '截图文件未生成'
                            logger.warning(f"截图文件未生成: {screenshot_path}")
                        else:
                            analysis_result = screenshot_analyzer.analyze_sports_screenshot(
                                screenshot_path, 
                                site_name="unknown",
                                match_info=match_info
                            )
                            
                            if analysis_result["success"]:
                                logger.info(f"截图分析成功: {match_code}")
                                return {
                                    'source': 'screenshot_ai',
                                    'data': analysis_result,
                                    'screenshot_path': screenshot_path,
                                    'site_info': analysis_result.get('site_info', {}),
                                    'parsed_data': analysis_result.get('parsed_data', {}),
                                    'collected_at': datetime.now().isoformat(),
                                    'status': 'success'
                                }
                            else:
                                last_error = analysis_result.get('message', '截图分析失败')
                                logger.warning(f"截图分析失败: {last_error}")
                    else:
                        last_error = generation_result.get('message', '截图生成失败')
                        logger.warning(f"截图生成失败: {last_error} (尝试 {attempt}/{max_attempts})")
                
                if attempt < max_attempts:
                    await asyncio.sleep(2 * attempt)
            
            logger.error(f"截图流程连续失败，已放弃: {last_error}")
            return {
                'source': 'screenshot_ai',
                'error': last_error or '截图流程失败',
                'collected_at': datetime.now().isoformat(),
                'status': 'failed',
                'attempts': max_attempts
            }
            
        except Exception as e:
            logger.error(f"搜集源3失败: {str(e)}")
            return {
                'source': 'screenshot_ai',
                'error': str(e),
                'collected_at': datetime.now().isoformat(),
                'status': 'failed'
            }
    
    def _integrate_three_sources(self, collection_result: Dict[str, Any]) -> Dict[str, Any]:
        """整合三源数据"""
        try:
            logger.info("开始整合三源数据")
            
            integrated = {
                'match_basic_info': collection_result['match_info'],
                'official_data': collection_result.get('source_1', {}).get('data', {}),
                'web_search_data': collection_result.get('source_2', {}).get('data', {}),
                'screenshot_data': collection_result.get('source_3', {}).get('data', {}),
                'data_quality': self._assess_data_quality(collection_result),
                'integrated_at': datetime.now().isoformat()
            }
            
            # 数据一致性检查
            integrated['consistency_check'] = self._check_data_consistency(integrated)
            
            # 生成综合分析
            integrated['comprehensive_analysis'] = self._generate_comprehensive_analysis(integrated)
            
            logger.info("三源数据整合完成")
            return integrated
            
        except Exception as e:
            logger.error(f"整合三源数据失败: {str(e)}")
            return {'error': str(e)}
    
    def _assess_data_quality(self, collection_result: Dict[str, Any]) -> Dict[str, Any]:
        """评估数据质量"""
        quality = {
            'source_1_quality': 'unknown',
            'source_2_quality': 'unknown',
            'source_3_quality': 'unknown',
            'overall_quality': 'unknown'
        }
        
        # 评估各数据源质量
        for i in range(1, 4):
            source_key = f'source_{i}'
            source_data = collection_result.get(source_key, {})
            
            if source_data.get('status') == 'success':
                quality[f'{source_key}_quality'] = 'high'
            elif source_data.get('status') == 'failed':
                quality[f'{source_key}_quality'] = 'low'
            elif source_data.get('status') == 'no_screenshot':
                quality[f'{source_key}_quality'] = 'not_available'
            else:
                quality[f'{source_key}_quality'] = 'unknown'
        
        # 评估整体质量
        success_count = sum(1 for i in range(1, 4) if quality[f'source_{i}_quality'] == 'high')
        
        if success_count >= 2:
            quality['overall_quality'] = 'high'
        elif success_count == 1:
            quality['overall_quality'] = 'medium'
        else:
            quality['overall_quality'] = 'low'
        
        return quality
    
    def _check_data_consistency(self, integrated_data: Dict[str, Any]) -> Dict[str, Any]:
        """检查数据一致性"""
        consistency = {
            'teams_consistent': True,
            'time_consistent': True,
            'odds_consistent': True,
            'overall_consistent': True,
            'inconsistencies': []
        }
        
        try:
            # 检查队伍名称一致性
            basic_info = integrated_data.get('match_basic_info', {})
            official_data = integrated_data.get('official_data', {})
            screenshot_data = integrated_data.get('screenshot_data', {})
            
            basic_home = basic_info.get('home_team', '')
            basic_away = basic_info.get('away_team', '')
            
            # 这里可以添加更详细的一致性检查逻辑
            # 暂时返回基本的一致性评估
            
        except Exception as e:
            logger.error(f"数据一致性检查失败: {str(e)}")
            consistency['overall_consistent'] = False
            consistency['inconsistencies'].append(str(e))
        
        return consistency
    
    def _generate_comprehensive_analysis(self, integrated_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成综合分析"""
        try:
            analysis = {
                'key_insights': [],
                'risk_factors': [],
                'opportunities': [],
                'recommendation': 'neutral',
                'confidence_level': 'medium'
            }
            
            # 这里可以添加更复杂的分析逻辑
            # 基于三源数据生成综合分析
            
            return analysis
            
        except Exception as e:
            logger.error(f"生成综合分析失败: {str(e)}")
            return {'error': str(e)}
    
    async def _check_site_reachable(self, url: str, timeout: int = 60) -> bool:
        """检测目标站点是否可达"""
        loop = asyncio.get_running_loop()

        def _probe() -> bool:
            try:
                import urllib.request
                with urllib.request.urlopen(url, timeout=timeout) as resp:
                    status = getattr(resp, "status", 200)
                    return 200 <= status < 500
            except Exception as exc:
                logger.warning(f"网络探测失败: {url} - {exc}")
                return False

        return await loop.run_in_executor(None, _probe)
    
    def _save_to_cache(self, match_id: str, data: Dict[str, Any]):
        """保存数据到缓存"""
        try:
            cache_file = os.path.join(self.cache_folder, f"three_source_{match_id}.json")
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"三源数据已保存到缓存: {cache_file}")
        except Exception as e:
            logger.error(f"保存三源数据到缓存失败: {str(e)}")
    
    def load_from_cache(self, match_id: str) -> Optional[Dict[str, Any]]:
        """从缓存加载数据"""
        try:
            cache_file = os.path.join(self.cache_folder, f"three_source_{match_id}.json")
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return None
        except Exception as e:
            logger.error(f"从缓存加载三源数据失败: {str(e)}")
            return None

# 创建全局实例
three_source_collector = ThreeSourceCollector()
