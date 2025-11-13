"""
AI比分预测服务 - WechatBOT版本
从ai_content_system迁移，适配WechatBOT的AI服务
"""
import asyncio
import json
import re
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta

from services.config_service import config_service
from services.zhipu_service import zhipu_service

logger = logging.getLogger(__name__)


class ScorePredictor:
    """AI比分预测器"""
    
    def __init__(self):
        """初始化预测器"""
        logger.info("AI比分预测器初始化")
        self._zhipu_client = None
        self._zhipu_search_engine = None
        self._zhipu_model = None
    
    def _ensure_zhipu_client(self):
        """延迟加载智谱 Web Search 客户端"""
        if self._zhipu_client is None:
            try:
                from zai import ZhipuAiClient  # type: ignore
            except Exception as e:
                logger.error("未安装zai-sdk，无法使用智谱联网搜索。请先运行：pip install zai-sdk")
                raise RuntimeError("未安装zai-sdk，无法使用智谱联网搜索") from e
            
            zhipu_cfg = config_service.get_zhipu_config()
            api_key = zhipu_cfg.get('api_key')
            model = zhipu_cfg.get('model', 'glm-4.5-air')
            if not api_key:
                raise ValueError("未配置智谱AI API密钥")
            
            self._zhipu_client = ZhipuAiClient(api_key=api_key)
            self._zhipu_model = model or 'glm-4.5-air'
            # 默认使用 search_std，后续可扩展为配置项
            self._zhipu_search_engine = 'search_std'
            # 确保 zhipu_service 使用相同配置
            try:
                zhipu_service.set_config(api_key, self._zhipu_model)
            except Exception as e:
                logger.warning(f"同步智谱配置失败（可忽略）：{e}")
        return self._zhipu_client
    
    async def predict_match(self, match_data: Dict) -> Dict:
        """
        预测单场比赛的比分
        
        Args:
            match_data: 比赛数据
                - match_code: 比赛编号
                - home_team: 主队
                - away_team: 客队
                - league: 联赛
                - match_time: 比赛时间
        
        Returns:
            预测结果字典
        """
        try:
            # 检查比赛时间：仅预测未来12小时内的比赛
            if not self._is_within_prediction_window(match_data):
                return {
                    'match_code': match_data.get('match_code'),
                    'scores': [],
                    'short_reason': '仅支持预测未来12小时内的比赛',
                    'status': 'skipped',
                    'predicted_at': datetime.now().isoformat()
                }
            
            # 使用DeepSeek进行预测
            prediction = await self._predict_with_ai(match_data)
            
            return {
                'match_code': match_data.get('match_code'),
                **prediction,
                'status': 'success',
                'predicted_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f'比分预测失败: {error_msg}')
            
            # 判断错误类型
            error_type = 'unknown_error'
            if '未使用联网搜索' in error_msg or '无参考价值' in error_msg:
                error_type = 'web_search_not_used'
            elif '网络' in error_msg or '连接' in error_msg or 'timeout' in error_msg.lower():
                error_type = 'network_error'
            elif 'API' in error_msg or '401' in error_msg or '403' in error_msg or '429' in error_msg or '500' in error_msg:
                error_type = 'api_error'
            elif '智谱AI API密钥' in error_msg:
                error_type = 'config_error'
            
            return {
                'match_code': match_data.get('match_code'),
                'scores': [],
                'short_reason': None,  # 预测失败返回null
                'status': 'error',
                'predicted_at': datetime.now().isoformat(),
                'error_type': error_type,
                'error_message': error_msg
            }
    
    def _is_within_prediction_window(self, match_data: Dict) -> bool:
        """
        判断是否在预测时间窗口内（未来12小时内）
        """
        try:
            match_time_str = match_data.get('match_time', '')
            if not match_time_str:
                logger.warning(f"比赛 {match_data.get('match_code')} 缺少比赛时间，跳过预测")
                return False
            
            # 解析比赛时间（支持多种格式）
            try:
                # 先尝试 ISO 格式（数据库可能存储的格式）
                match_time = datetime.fromisoformat(match_time_str.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                # 如果失败，尝试简单格式
                try:
            match_time = datetime.strptime(match_time_str, '%Y-%m-%d %H:%M')
                except ValueError:
                    # 如果还是失败，尝试带秒格式
                    match_time = datetime.strptime(match_time_str, '%Y-%m-%d %H:%M:%S')
            
            current_time = datetime.now()
            
            # 计算时间差
            time_diff = match_time - current_time
            hours_diff = time_diff.total_seconds() / 3600
            
            # 判断：比赛未开始且在12小时内
            is_not_started = match_time > current_time
            is_within_window = 0 < hours_diff <= 12
            
            logger.info(f"比赛 {match_data.get('match_code')} 时间检查: 比赛时间={match_time_str}, 当前时间差={hours_diff:.1f}小时, 允许预测={is_not_started and is_within_window}")
            
            return is_not_started and is_within_window
            
        except Exception as e:
            logger.warning(f'时间解析失败: {str(e)}, match_time={match_time_str}')
            return False
    
    async def _predict_with_ai(self, match_data: Dict) -> Dict:
        """使用智谱联网搜索 + GLM 模型进行比分预测"""
        home_team = match_data.get('home_team', '')
        away_team = match_data.get('away_team', '')
        league = match_data.get('league', '')
        match_time = match_data.get('match_time', '')
        
        # 1. 联网搜索最新资料
        search_query = self._build_search_query(match_data)
        search_results = await self._fetch_web_search_results(search_query)
        search_summary = self._format_search_results(search_results)
        
        # 2. 构建预测提示词
        prompt = self._build_prediction_prompt(
            home_team=home_team,
            away_team=away_team,
            league=league,
            match_time=match_time,
            search_summary=search_summary
        )
        
        # 3. 调用智谱模型生成预测
        response = await self._call_zhipu_async(prompt)
        if not response:
            raise Exception("智谱模型返回空响应")
        
        logger.info(f"AI返回内容长度: {len(response)} 字符")
        logger.info(f"AI原始返回内容(前500字符): {response[:500]}")
        if len(response) > 500:
            logger.info(f"AI原始返回内容(中段): {response[500:1000] if len(response) > 1000 else response[500:]}")
        if len(response) > 1000:
            logger.info(f"AI原始返回内容(后500字符): ...{response[-500:]}")
        
        # 4. 解析预测结果
        prediction = self._parse_json_prediction(response)
        logger.info(f"解析后的预测结果: scores={prediction.get('scores')}, reason={prediction.get('short_reason')}")
        
        # 5. 质量校验
        if not self._validate_prediction_quality(prediction, match_data, search_results):
            logger.warning("预测结果缺乏足够的数据支撑，建议人工复核")
        
        return prediction
    
    def _build_prediction_prompt(self, home_team: str, away_team: str, 
                                 league: str, match_time: str,
                                 search_summary: str) -> str:
        """构建预测提示词"""
        current_date = datetime.now().strftime('%Y年%m月%d日')
        prompt = f"""你是一名专业的足球分析师，请分析以下比赛并给出比分预测。
请严格参考后文提供的最新联网搜索结果，引用其中的数据、时间和来源进行推理。

比赛信息：
- 主队：{home_team}
- 客队：{away_team}
- 联赛：{league}
- 比赛时间：{match_time}
- 当前日期：{current_date}

最新联网搜索结果：
{search_summary or '（未获取到有效的搜索结果，请谨慎给出结论）'}

请基于以下要点进行分析：
1. {home_team} 近期表现、主场战绩
2. {away_team} 近期表现、客场战绩
3. 双方历史交锋记录
4. 联赛排名和竞争形势
5. 战术风格和关键球员

请严格按照以下JSON格式输出：

{{
  "success": true,
  "match": {{
    "home": "{home_team}",
    "away": "{away_team}",
    "league": "{league}",
    "kickoff": "{match_time}"
  }},
  "prediction": {{
    "scores": ["X-Y", "A-B"],
    "short_reason": "不超过50字的简短理由，必须包含具体事实（如：近5场3胜、主场胜率60%等）"
  }},
  "evidence": [
    "证据1：具体事实",
    "证据2：具体事实",
    "证据3：具体事实"
  ],
  "predicted_at": "{datetime.now().isoformat()}"
}}

重要规则：
1. 必须输出严格的JSON格式
2. scores必须是2个不同的比分，格式为"X-Y"，其中X和Y在0-6之间
3. short_reason不超过50字，必须包含具体数据或事实
4. evidence每条都应具体、可验证
5. 如果信息不足，可输出：{{"success": false, "message": "信息不足"}}"""
        
        return prompt
    
    def _parse_prediction_response(self, response: str) -> Dict:
        """解析AI返回的预测结果"""
        try:
            # 尝试直接解析JSON
            data = None
            
            try:
                data = json.loads(response.strip())
            except:
                # 尝试从代码块中提取JSON
                json_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', response)
                if json_match:
                    try:
                        data = json.loads(json_match.group(1))
                    except:
                        pass
                
                # 尝试提取第一个JSON对象
                if not data:
                    json_match = re.search(r'\{[\s\S]*\}', response)
                    if json_match:
                        try:
                            data = json.loads(json_match.group(0))
                        except:
                            pass
            
            # 验证JSON结构
            if not data or not isinstance(data, dict):
                return {
                    'scores': [],  # 预测失败返回空数组（前端显示"暂无预测"）
                    'short_reason': None,  # 预测失败返回null（保持为空）
                    'analysis': response
                }
            
            # 检查是否为失败响应
            if not data.get('success', True):
                return {
                    'scores': [],  # 预测失败返回空数组（前端显示"暂无预测"）
                    'short_reason': None,  # 预测失败返回null（保持为空）
                    'analysis': response
                }
            
            # 提取预测结果
            prediction = data.get('prediction', {})
            scores = prediction.get('scores', [])
            short_reason = prediction.get('short_reason', '').strip()
            
            # 验证比分格式
            valid_scores = []
            for score in scores:
                if isinstance(score, str) and re.match(r'^\d+-\d+$', score):
                    home_score, away_score = map(int, score.split('-'))
                    if 0 <= home_score <= 6 and 0 <= away_score <= 6:
                        valid_scores.append(score)
            
            # 验证理由长度
            if short_reason and len(short_reason) > 50:
                short_reason = short_reason[:47] + '...'
            
            # 如果验证失败，比分返回空数组（前端会显示"暂无预测"），理由返回null
            if not valid_scores:
                valid_scores = []  # 比分验证失败，返回空数组
            
            # 如果理由为空或无效，返回None（保持为空）
            if not short_reason:
                short_reason = None
            
            return {
                'scores': valid_scores[:2] if valid_scores else [],  # 最多2个比分，失败返回空数组
                'short_reason': short_reason or None,  # 失败返回None
                'analysis': response,
                'short_article': data.get('short_article', '')
            }
            
        except Exception as e:
            logger.error(f'解析预测结果失败: {str(e)}')
            return {
                'scores': [],  # 预测失败返回空数组（前端显示"暂无预测"）
                'short_reason': None,  # 预测失败返回null（保持为空）
                'analysis': response
            }
    
    async def predict_multiple_matches(self, matches: List[Dict]) -> List[Dict]:
        """
        批量预测多场比赛
        
        Args:
            matches: 比赛列表
        
        Returns:
            预测结果列表
        """
        predictions = []
        
        for match in matches:
            try:
                prediction = await self.predict_match(match)
                predictions.append(prediction)
                
                # 添加延迟避免API限制
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f'预测比赛失败 {match.get("match_code")}: {str(e)}')
                predictions.append({
                    'match_code': match.get('match_code'),
                    'scores': [],
                    'short_reason': f'预测失败: {str(e)}',
                    'status': 'error',
                    'predicted_at': datetime.now().isoformat()
                })
        
        return predictions
    
    async def _fetch_web_search_results(self, query: str, count: int = 5) -> List[Dict[str, str]]:
        """调用智谱 Web Search API 获取结构化搜索结果"""
        self._ensure_zhipu_client()
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._fetch_web_search_results_sync, query, count)
    
    def _fetch_web_search_results_sync(self, query: str, count: int = 5) -> List[Dict[str, str]]:
        client = self._ensure_zhipu_client()
        logger.info(f"调用智谱 Web Search，query={query}, engine={self._zhipu_search_engine}")
        resp = client.web_search.web_search(
            search_engine=self._zhipu_search_engine,
            search_query=query,
            count=count,
            content_size="medium"
        )
        results = []
        for item in resp.search_result or []:
            results.append({
                "title": getattr(item, "title", "") or "",
                "url": getattr(item, "link", "") or "",
                "summary": getattr(item, "content", "") or "",
                "source": getattr(item, "media", "") or "",
                "publish_date": getattr(item, "publish_date", "") or ""
            })
        logger.info(f"智谱 Web Search 返回 {len(results)} 条结果")
        return results
    
    def _format_search_results(self, results: List[Dict[str, str]]) -> str:
        """将搜索结果整理成提示词中的参考文本"""
        if not results:
            return "（未获取到搜索结果，无法提供实时数据，请谨慎给出结论）"
        lines = []
        for idx, item in enumerate(results, start=1):
            title = item.get("title") or item.get("url") or f"结果 {idx}"
            summary = item.get("summary", "")
            source = item.get("source", "")
            publish_date = item.get("publish_date", "")
            url = item.get("url", "")
            lines.append(
                f"[结果 {idx}] 标题：{title}\n"
                f"摘要：{summary}\n"
                f"来源：{source or '未知'}，发布时间：{publish_date or '未知'}\n"
                f"链接：{url}\n"
            )
        return "\n".join(lines)
    
    def _build_search_query(self, match_data: Dict[str, Any]) -> str:
        """根据比赛信息构建搜索关键词"""
        home_team = match_data.get('home_team', '')
        away_team = match_data.get('away_team', '')
        league = match_data.get('league', '')
        match_time = match_data.get('match_time', '')
        return f"{home_team} 对 {away_team} {league} {match_time} 最新战况 伤停 情报"
    
    async def _call_zhipu_async(self, prompt: str) -> str:
        """异步调用智谱模型"""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._call_zhipu_sync, prompt)
    
    def _call_zhipu_sync(self, prompt: str) -> str:
        """同步调用智谱模型生成预测"""
        system_prompt = (
            "你是一名专业的足球数据分析师。请基于提供的比赛信息和联网搜索结果，"
            "输出严格遵循 JSON 结构的比分预测，必须引用搜索结果中的具体数据和日期。"
            "不要编造数据，也不要输出任何多余文本。"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        result = zhipu_service.chat_completion(messages, max_tokens=1500, temperature=0.6)
        if not result.get("success"):
            raise Exception(result.get("message", "智谱预测失败"))
        return result.get("content", "")
    
    def _validate_prediction_quality(self, prediction: Dict, match_data: Dict,
                                     search_results: List[Dict[str, str]]) -> bool:
        """基于预测内容和搜索结果进行质量校验"""
        try:
            evidence_text = prediction.get('analysis', '') or ''
            short_reason = prediction.get('short_reason', '') or ''
            content = (evidence_text + ' ' + short_reason).strip()
            
            if not content or len(content) < 10:
                logger.warning("返回内容为空或过短")
                return False
            
            number_patterns = [
                r'\d+胜', r'\d+负', r'\d+平', r'\d+%', r'排名第\d+', r'积分\d+',
                r'\d+球', r'\d+个', r'\d+次', r'\d+分', r'\d+场', r'第\d+名'
            ]
            has_specific_data = any(re.search(pattern, content) for pattern in number_patterns)
            
            if not has_specific_data:
                logger.warning("返回内容缺少具体数据")
                return False
            
            # 如果原始搜索结果为空，说明信息来源不足
            if not search_results:
                logger.warning("搜索结果为空，预测可能缺乏实时依据")
                return False
            
            return True
        
        except Exception as e:
            logger.error(f"验证预测质量失败: {str(e)}")
            return False
    
    def _parse_json_prediction(self, response: str) -> Dict:
        """严格JSON解析AI返回的预测结果"""
        try:
            import json
            import re
            
            data = None
            
            # 尝试直接解析
            try:
                data = json.loads(response.strip())
            except Exception:
                # 尝试从代码块中提取JSON
                json_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', response)
                if json_match:
                    try:
                        data = json.loads(json_match.group(1))
                    except Exception:
                        pass
                
                # 如果还是失败，尝试提取第一个完整的JSON对象
                if not data:
                    json_match = re.search(r'\{[\s\S]*\}', response)
                    if json_match:
                        try:
                            data = json.loads(json_match.group(0))
                        except Exception:
                            pass
            
            # 严格验证JSON结构
            if not data or not isinstance(data, dict):
                return {
                    'scores': [],
                    'short_reason': 'AI返回格式错误，无法解析',
                    'analysis': response
                }
            
            # 检查是否为失败响应 - 如果success为false，记录警告但继续处理
            if not data.get('success', True):
                error_message = data.get('message', '无法使用联网搜索功能获取实时数据')
                logger.warning(f"AI返回success:false，原因: {error_message}，但web_search已启用，继续处理")
                # 不直接返回失败，尝试从response中提取有用信息
            
            # 提取预测结果
            prediction = data.get('prediction', {})
            scores = prediction.get('scores', [])
            short_reason = prediction.get('short_reason', '').strip()
            
            # 验证比分格式
            valid_scores = []
            for score in scores:
                if isinstance(score, str) and re.match(r'^\d+-\d+$', score):
                    home_score, away_score = map(int, score.split('-'))
                    if 0 <= home_score <= 6 and 0 <= away_score <= 6:
                        valid_scores.append(score)
            
            # 验证理由长度
            if len(short_reason) > 50:
                short_reason = short_reason[:47] + '...'
            
            # 如果验证失败，返回错误
            if not valid_scores or not short_reason:
                return {
                    'scores': [],
                    'short_reason': 'AI返回数据格式不符合要求',
                    'analysis': response
                }
            
            return {
                'scores': valid_scores[:2],  # 最多2个比分
                'short_reason': short_reason,
                'analysis': response
            }
            
        except Exception as e:
            logger.error(f'解析预测结果失败: {str(e)}')
            return {
                'scores': [],
                'short_reason': 'AI返回格式错误',
                'analysis': response
            }


# 创建预测器实例
score_predictor = ScorePredictor()

