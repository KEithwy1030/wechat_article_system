"""
文章生成引擎
基于三源数据生成"老k看不准"风格的文章
"""

import json
import os
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from .three_source_collector import three_source_collector

logger = logging.getLogger(__name__)

class ArticleGenerator:
    """文章生成器"""
    
    def __init__(self):
        self.three_source_collector = three_source_collector
        self.article_cache_folder = "cache/generated_articles"
        
        # 确保缓存文件夹存在
        os.makedirs(self.article_cache_folder, exist_ok=True)
        
        logger.info("文章生成引擎初始化完成")
    
    def _get_deepseek_service(self):
        """延迟加载DeepSeek服务"""
        try:
            from services.deepseek_service import deepseek_service
            return deepseek_service
        except Exception as e:
            logger.error(f"DeepSeek服务加载失败: {str(e)}")
            return None
    
    async def generate_article(self, match_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成文章
        :param match_info: 比赛基本信息
        :return: 生成的文章数据
        """
        # 统一以比赛编号作为主键，兼容无编号时退回match_id
        match_code = str(match_info.get('match_code') or '').strip()
        match_id = match_code if match_code else str(match_info.get('match_id', 'unknown'))
        logger.info(f"开始为比赛 {match_id} 生成文章")
        
        result = {
            'match_id': match_id,
            'match_info': match_info,
            'article_status': 'generating',
            'generated_at': datetime.now().isoformat(),
            'article_content': None,
            'article_metadata': {},
            'error': None
        }
        
        try:
            # 1. 搜集三源数据
            logger.info("步骤1：搜集三源数据")
            three_source_data = await self.three_source_collector.collect_match_data(match_info)
            
            if three_source_data.get('status') != 'completed':
                raise Exception(f"三源数据搜集失败: {three_source_data.get('error', '未知错误')}")
            
            # 2. 生成文章内容
            logger.info("步骤2：生成文章内容")
            article_content = await self._generate_article_content(three_source_data)
            
            # 3. 生成文章元数据
            logger.info("步骤3：生成文章元数据")
            article_metadata = self._generate_article_metadata(match_info, three_source_data, article_content)
            
            # 4. 保存文章
            logger.info("步骤4：保存文章")
            self._save_article(match_id, article_content, article_metadata)
            
            # 生成article_id
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            article_id = f"article_{match_id}_{timestamp}"

            prediction_result = await self._generate_prediction_insights(match_info, three_source_data)

            prediction_scores = prediction_result.get('scores') or []
            prediction_reason = prediction_result.get('reason') or f"基于深度分析，{match_info.get('home_team', '主队')} vs {match_info.get('away_team', '客队')}的预测分析已完成"

            if not prediction_scores:
                logger.warning(f"深度分析未返回比分，尝试回退到快速预测结果: {match_code}")
                try:
                    from .prediction_manager import prediction_manager
                    existing_prediction = prediction_manager.get_prediction_data(match_code)
                    if existing_prediction and existing_prediction.get('source_type') == 'quick':
                        prediction_scores = existing_prediction.get('scores', [])
                        if existing_prediction.get('reason'):
                            prediction_reason = existing_prediction.get('reason')
                        logger.info(f"已使用快速预测比分作为回退: {match_code} -> {prediction_scores}")
                except Exception as fallback_error:
                    logger.error(f"获取快速预测比分失败: {fallback_error}")
            
            result.update({
                'article_status': 'completed',
                'article_content': article_content,
                'article_metadata': article_metadata,
                'three_source_data': three_source_data,
                'article_id': article_id,
                'article_data': {
                    'prediction': {
                        'scores': prediction_scores,
                        'analysis': prediction_reason
                    }
                }
            })
            
            logger.info(f"比赛 {match_id} 文章生成完成")
            return result
            
        except Exception as e:
            logger.error(f"生成比赛 {match_id} 文章失败: {str(e)}")
            
            # 即使失败也要生成article_data，确保深度分析状态能正确保存
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            article_id = f"article_{match_id}_{timestamp}"
            fallback_scores = []
            fallback_reason = f"深度分析失败，保留既有预测结果（若存在）。"

            try:
                from .prediction_manager import prediction_manager
                existing_prediction = prediction_manager.get_prediction_data(match_code)
                if existing_prediction and existing_prediction.get('scores'):
                    fallback_scores = existing_prediction.get('scores', [])
                    if existing_prediction.get('reason'):
                        fallback_reason = existing_prediction.get('reason')
            except Exception as fallback_error:
                logger.error(f"异常回退快速预测比分失败: {fallback_error}")
            
            result.update({
                'article_status': 'failed',
                'error': str(e),
                'article_id': article_id,
                'article_data': {
                    'prediction': {
                        'scores': fallback_scores,
                        'analysis': fallback_reason
                    }
                }
            })
            return result
    
    async def _generate_article_content(self, three_source_data: Dict[str, Any]) -> str:
        """生成文章内容"""
        try:
            # 构建文章生成提示词
            prompt = self._build_article_prompt(three_source_data)
            
            # 使用DeepSeek生成文章
            deepseek_service = self._get_deepseek_service()
            if not deepseek_service:
                raise Exception("DeepSeek服务未配置")
            
            # 调用同步方法generate_content
            response = deepseek_service.generate_content(prompt)
            
            if response:
                logger.info(f"文章生成成功，长度: {len(response)} 字符")
                return response
            else:
                raise Exception("AI返回空响应")
                
        except Exception as e:
            logger.error(f"生成文章内容失败: {str(e)}")
            raise
    
    def _build_article_prompt(self, three_source_data: Dict[str, Any]) -> str:
        """构建文章生成提示词"""
        
        # 提取关键数据
        match_info = three_source_data.get('match_info', {})
        integrated_data = three_source_data.get('integrated_data', {})
        
        home_team = match_info.get('home_team', '主队')
        away_team = match_info.get('away_team', '客队')
        match_time = match_info.get('match_time', '未知时间')
        league = match_info.get('league', '未知联赛')
        
        # 构建详细提示词
        prompt = f"""
你是一位专业的足球竞彩分析师，需要为"老k看不准"公众号撰写一篇深度分析文章。

## 比赛信息
- 比赛：{home_team} vs {away_team}
- 时间：{match_time}
- 联赛：{league}

## 三源数据信息

### 源1：竞彩官网数据
{json.dumps(integrated_data.get('official_data', {}), ensure_ascii=False, indent=2)}

### 源2：AI联网搜索数据
{json.dumps(integrated_data.get('web_search_data', {}), ensure_ascii=False, indent=2)}

### 源3：截图AI识别数据
{json.dumps(integrated_data.get('screenshot_data', {}), ensure_ascii=False, indent=2)}

## 写作要求

请按照"老k看不准"的写作风格，撰写一篇800-1200字的深度分析文章。要求：

### 1. 文章结构
- **主标题**：吸引眼球，体现"老k"风格
- **老k前言**：开场白，体现个人观点
- **球队基础速览**：双方球队基本情况
- **老k的深度琢磨**：核心分析内容
- **老k多说一句**：总结和预测
- **合规声明**：必要的法律声明

### 2. 写作风格
- 专业但不失幽默
- 数据驱动但有个人观点
- 语言生动，有"老k"特色
- 避免过于技术化的表述

### 3. 内容要求
- 基于三源数据进行客观分析
- 突出关键信息和数据
- 提供清晰的判断和理由
- 避免绝对化的表述

### 4. 格式要求
- 使用Markdown格式
- 适当使用**粗体**突出重点
- 使用>引用块进行合规声明
- 确保文章逻辑清晰，层次分明

请开始撰写文章：
"""
        
        return prompt
    
    def _generate_article_metadata(self, match_info: Dict[str, Any], 
                                 three_source_data: Dict[str, Any], 
                                 article_content: str) -> Dict[str, Any]:
        """生成文章元数据"""
        
        metadata = {
            'title': self._extract_title_from_content(article_content),
            'word_count': len(article_content),
            'generated_at': datetime.now().isoformat(),
            'match_info': match_info,
            'data_quality': three_source_data.get('integrated_data', {}).get('data_quality', {}),
            'source_summary': self._generate_source_summary(three_source_data),
            'article_type': 'deep_analysis',
            'status': 'generated'
        }
        
        return metadata
    
    async def _generate_prediction_insights(self, match_info: Dict[str, Any], three_source_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        基于三源数据生成比分预测
        """
        try:
            deepseek_service = self._get_deepseek_service()
            if not deepseek_service:
                logger.warning("深度分析比分生成失败：DeepSeek服务未配置")
                return {}
            
            prompt = self._build_prediction_prompt(match_info, three_source_data)
            logger.info("开始生成深度分析预测比分")
            response = deepseek_service.generate_content(prompt)
            if not response:
                logger.warning("深度分析比分生成失败：AI返回空响应")
                return {}
            
            prediction = self._parse_prediction_response(response)
            if prediction.get('scores'):
                logger.info(f"深度分析预测比分生成成功: {prediction['scores']}")
            else:
                logger.warning("深度分析预测比分生成为空，将尝试回退逻辑")
            return prediction
        except Exception as e:
            logger.error(f"生成深度分析预测比分失败: {e}")
            return {}
    
    def _build_prediction_prompt(self, match_info: Dict[str, Any], three_source_data: Dict[str, Any]) -> str:
        """
        构造比分预测提示词，让模型返回结构化JSON
        """
        home_team = match_info.get('home_team', '主队')
        away_team = match_info.get('away_team', '客队')
        match_time = match_info.get('match_time', '未知时间')
        league = match_info.get('league', '未知联赛')
        integrated = three_source_data.get('integrated_data', {})
        
        return f"""
你是一位专业的足球数据分析师。请根据以下资料，为比赛 {home_team} vs {away_team} 给出两个可能的比分和一段综合分析，并仅输出JSON。

比赛时间：{match_time}
赛事：{league}

官网数据：
{json.dumps(integrated.get('official_data', {}), ensure_ascii=False, indent=2)}

联网搜索数据：
{json.dumps(integrated.get('web_search_data', {}), ensure_ascii=False, indent=2)}

截图识别数据：
{json.dumps(integrated.get('screenshot_data', {}), ensure_ascii=False, indent=2)}

请输出如下JSON，勿添加额外说明：
{{
  "scores": ["主队比分-客队比分", "主队比分-客队比分"],
  "reason": "不超过120字的综合分析"
}}
"""
    
    def _parse_prediction_response(self, response: str) -> Dict[str, Any]:
        """
        解析AI返回的JSON结构
        """
        try:
            content = response.strip()
            if content.startswith("```"):
                content = content.lstrip("`")
                content = content.strip("`")
            data = json.loads(content)
            scores = data.get('scores') if isinstance(data.get('scores'), list) else []
            normalized_scores = []
            for score in scores:
                if isinstance(score, str) and score.count('-') == 1:
                    parts = score.split('-')
                    if all(part.strip().isdigit() for part in parts):
                        normalized_scores.append(f"{int(parts[0])}-{int(parts[1])}")
            reason = data.get('reason') if isinstance(data.get('reason'), str) else ''
            return {
                'scores': normalized_scores,
                'reason': reason.strip()
            }
        except Exception as e:
            logger.error(f"解析深度分析预测比分失败: {e}")
            return {}
    
    def _extract_title_from_content(self, content: str) -> str:
        """从文章内容中提取标题"""
        try:
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('# ') and len(line) > 2:
                    return line[2:].strip()
            return "未提取到标题"
        except:
            return "标题提取失败"
    
    def _generate_source_summary(self, three_source_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成数据源摘要"""
        summary = {
            'total_sources': 3,
            'successful_sources': 0,
            'source_details': {}
        }
        
        for i in range(1, 4):
            source_key = f'source_{i}'
            source_data = three_source_data.get(source_key, {})
            status = source_data.get('status', 'unknown')
            
            summary['source_details'][source_key] = {
                'status': status,
                'collected_at': source_data.get('collected_at'),
                'has_error': 'error' in source_data
            }
            
            if status == 'success':
                summary['successful_sources'] += 1
        
        return summary
    
    def _save_article(self, match_id: str, content: str, metadata: Dict[str, Any]):
        """保存文章到缓存"""
        try:
            article_data = {
                'match_id': match_id,
                'content': content,
                'metadata': metadata,
                'saved_at': datetime.now().isoformat()
            }
            
            # 文件名去除不安全字符，保证跨平台稳定
            safe_id = str(match_id).replace('/', '-').replace('\\', '-').replace(' ', '')
            article_file = f"{self.article_cache_folder}/article_{safe_id}.json"
            with open(article_file, 'w', encoding='utf-8') as f:
                json.dump(article_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"文章已保存: {article_file}")
            
        except Exception as e:
            logger.error(f"保存文章失败: {str(e)}")
    
    def load_article(self, match_id: str) -> Optional[Dict[str, Any]]:
        """加载文章"""
        try:
            # 先按原样尝试
            direct_file = f"{self.article_cache_folder}/article_{match_id}.json"
            if os.path.exists(direct_file):
                with open(direct_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            # 再按安全文件名规则尝试
            safe_id = str(match_id).replace('/', '-').replace('\\', '-').replace(' ', '')
            safe_file = f"{self.article_cache_folder}/article_{safe_id}.json"
            if os.path.exists(safe_file):
                with open(safe_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            # 兜底：目录内模糊匹配
            for filename in os.listdir(self.article_cache_folder):
                if filename.endswith('.json') and str(match_id) in filename:
                    with open(os.path.join(self.article_cache_folder, filename), 'r', encoding='utf-8') as f:
                        return json.load(f)
        except Exception as e:
            logger.error(f"加载文章失败: {str(e)}")
            return None
    
    async def batch_generate_articles(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """批量生成文章"""
        logger.info(f"开始批量生成 {len(matches)} 篇文章")
        
        results = []
        for match in matches:
            try:
                result = await self.generate_article(match)
                results.append(result)
            except Exception as e:
                logger.error(f"批量生成文章失败: {str(e)}")
                results.append({
                    'match_id': match.get('match_id', 'unknown'),
                    'article_status': 'failed',
                    'error': str(e)
                })
        
        logger.info(f"批量生成完成，成功: {sum(1 for r in results if r.get('article_status') == 'completed')}")
        return results

# 创建全局实例
article_generator = ArticleGenerator()
