#!/usr/bin/env python3
"""
体育数据截图分析服务
使用智谱AI分析专业体育数据网站的截图
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from .zhipu_service import zhipu_service

logger = logging.getLogger(__name__)

class SportsScreenshotAnalyzer:
    """体育数据截图分析器"""
    
    def __init__(self):
        self.zhipu = zhipu_service
        self.supported_sites = {
            "flashscore": {
                "name": "FlashScore",
                "url": "https://www.flashscore.com",
                "priority": "high",
                "description": "专业体育数据网站，包含详细统计数据"
            },
            "sofascore": {
                "name": "SofaScore", 
                "url": "https://www.sofascore.com",
                "priority": "high",
                "description": "实时体育数据和统计"
            },
            "whoscored": {
                "name": "WhoScored",
                "url": "https://www.whoscored.com",
                "priority": "high", 
                "description": "专业足球数据分析和统计"
            },
            "espn": {
                "name": "ESPN足球",
                "url": "https://www.espn.com/soccer",
                "priority": "medium",
                "description": "知名体育媒体数据"
            },
            "bbc_sport": {
                "name": "BBC Sport",
                "url": "https://www.bbc.com/sport",
                "priority": "medium",
                "description": "权威体育新闻和数据"
            }
        }
    
    def analyze_sports_screenshot(self, image_path: str, site_name: str = "unknown", match_info: Dict = None) -> Dict:
        """
        分析体育数据截图
        
        Args:
            image_path: 截图文件路径
            site_name: 网站名称 (flashscore, sofascore, whoscored, espn, bbc_sport)
            match_info: 比赛基本信息
            
        Returns:
            分析结果字典
        """
        if not os.path.exists(image_path):
            return {
                "success": False,
                "message": f"截图文件不存在: {image_path}",
                "timestamp": datetime.now().isoformat()
            }
        
        # 获取网站信息
        if isinstance(site_name, str):
            site_key = site_name.lower()
        else:
            site_key = "soccerstats"
        
        site_info = self.supported_sites.get(site_key, {
            "name": "未知网站",
            "priority": "low",
            "description": "未知体育数据网站"
        })
        
        # 构建专业的分析提示词
        prompt = self._build_analysis_prompt(site_info, match_info)
        
        logger.info(f"开始分析 {site_info['name']} 截图: {image_path}")
        
        try:
            # 调用智谱AI分析截图
            result = self.zhipu.analyze_image(image_path, prompt)
            
            if result["success"]:
                # 尝试解析结构化的数据
                parsed_data = self._parse_analysis_result(result["content"], site_name)
                
                analysis_result = {
                    "success": True,
                    "site_info": site_info,
                    "image_path": image_path,
                    "raw_analysis": result["content"],
                    "parsed_data": parsed_data,
                    "usage": result.get("usage", {}),
                    "timestamp": datetime.now().isoformat()
                }
                
                logger.info(f"截图分析成功: {site_info['name']}")
                return analysis_result
            else:
                logger.error(f"截图分析失败: {result['message']}")
                return {
                    "success": False,
                    "message": result["message"],
                    "site_info": site_info,
                    "image_path": image_path,
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"截图分析异常: {str(e)}")
            return {
                "success": False,
                "message": f"分析过程发生异常: {str(e)}",
                "site_info": site_info,
                "image_path": image_path,
                "timestamp": datetime.now().isoformat()
            }
    
    def _build_analysis_prompt(self, site_info: Dict, match_info: Dict = None) -> str:
        """构建分析提示词"""
        
        base_prompt = f"""请仔细分析这张来自 {site_info['name']} 的体育数据截图，提取以下关键信息：

## 比赛基本信息
- 比赛时间（日期和时间）
- 主队 vs 客队（球队名称）
- 联赛名称
- 比赛状态（未开始/进行中/已结束）

## 统计数据
- 比分情况（主队:客队）
- 射门次数
- 射正次数  
- 控球率
- 角球数
- 黄牌/红牌数
- 传球成功率
- 其他重要统计指标

## 赔率信息（如有）
- 胜平负赔率
- 让球赔率
- 大小球赔率
- 其他投注选项

## 预测分析
- 历史交锋记录
- 近期状态
- 关键球员信息
- 伤病情况
- 战术分析

## 其他重要信息
- 实时更新数据
- 专家分析
- 推荐信息
- 特殊标识

请以JSON格式返回结果，结构如下：
{{
    "match_info": {{
        "home_team": "主队名称",
        "away_team": "客队名称", 
        "league": "联赛名称",
        "match_time": "比赛时间",
        "status": "比赛状态"
    }},
    "statistics": {{
        "score": "主队:客队",
        "shots": "射门次数",
        "shots_on_target": "射正次数",
        "possession": "控球率",
        "corners": "角球数",
        "cards": "牌数统计",
        "pass_accuracy": "传球成功率"
    }},
    "odds": {{
        "match_odds": "胜平负赔率",
        "handicap_odds": "让球赔率", 
        "over_under": "大小球赔率"
    }},
    "analysis": {{
        "form_analysis": "状态分析",
        "key_players": "关键球员",
        "injuries": "伤病情况",
        "tactics": "战术分析"
    }},
    "confidence_level": "数据可信度(1-10)",
    "data_quality": "数据完整性评估"
}}"""

        if match_info:
            base_prompt += f"\n\n## 补充信息\n已知比赛信息: {json.dumps(match_info, ensure_ascii=False)}"
        
        return base_prompt
    
    def _parse_analysis_result(self, content: str, site_name: str) -> Dict:
        """解析分析结果"""
        try:
            # 清理JSON格式
            cleaned_content = content.strip()
            if cleaned_content.startswith("```json"):
                cleaned_content = cleaned_content.replace("```json", "").replace("```", "").strip()
            elif cleaned_content.startswith("```"):
                cleaned_content = cleaned_content.replace("```", "").strip()
            
            # 尝试解析JSON
            parsed_data = json.loads(cleaned_content)
            
            # 验证必要字段
            required_fields = ["match_info", "statistics", "analysis"]
            for field in required_fields:
                if field not in parsed_data:
                    parsed_data[field] = {}
            
            # 添加解析状态
            parsed_data["parse_status"] = "success"
            parsed_data["parse_timestamp"] = datetime.now().isoformat()
            
            return parsed_data
            
        except json.JSONDecodeError as e:
            logger.warning(f"JSON解析失败，返回原始文本: {str(e)}")
            return {
                "parse_status": "failed",
                "raw_content": content,
                "error": str(e),
                "parse_timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"解析结果异常: {str(e)}")
            return {
                "parse_status": "error", 
                "raw_content": content,
                "error": str(e),
                "parse_timestamp": datetime.now().isoformat()
            }
    
    def batch_analyze_screenshots(self, screenshot_dir: str, match_info: Dict = None) -> List[Dict]:
        """
        批量分析截图目录中的所有截图
        
        Args:
            screenshot_dir: 截图目录路径
            match_info: 比赛基本信息
            
        Returns:
            分析结果列表
        """
        if not os.path.exists(screenshot_dir):
            return [{
                "success": False,
                "message": f"截图目录不存在: {screenshot_dir}",
                "timestamp": datetime.now().isoformat()
            }]
        
        results = []
        image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.webp']
        
        # 遍历目录中的图片文件
        for filename in os.listdir(screenshot_dir):
            if any(filename.lower().endswith(ext) for ext in image_extensions):
                image_path = os.path.join(screenshot_dir, filename)
                
                # 根据文件名推断网站类型
                site_name = self._infer_site_from_filename(filename)
                
                # 分析截图
                result = self.analyze_sports_screenshot(image_path, site_name, match_info)
                results.append(result)
                
                logger.info(f"完成截图分析: {filename}")
        
        logger.info(f"批量分析完成，共处理 {len(results)} 个截图")
        return results
    
    def _infer_site_from_filename(self, filename: str) -> str:
        """从文件名推断网站类型"""
        filename_lower = filename.lower()
        
        if "flashscore" in filename_lower:
            return "flashscore"
        elif "sofascore" in filename_lower:
            return "sofascore"
        elif "whoscored" in filename_lower:
            return "whoscored"
        elif "espn" in filename_lower:
            return "espn"
        elif "bbc" in filename_lower:
            return "bbc_sport"
        else:
            return "unknown"
    
    def get_supported_sites(self) -> Dict:
        """获取支持的网站列表"""
        return self.supported_sites
    
    def test_analysis_capability(self) -> Dict:
        """测试分析能力"""
        if not self.zhipu.api_key:
            return {
                "success": False,
                "message": "智谱AI未配置API密钥"
            }
        
        # 检查是否支持多模态模型
        if self.zhipu.model != "glm-4.5v":
            return {
                "success": False,
                "message": f"当前模型 {self.zhipu.model} 不支持图片分析，请切换到 glm-4.5v"
            }
        
        # 测试连接
        test_result = self.zhipu.test_connection()
        if test_result["success"]:
            return {
                "success": True,
                "message": "截图分析功能可用",
                "model": self.zhipu.model,
                "supported_sites": len(self.supported_sites)
            }
        else:
            return {
                "success": False,
                "message": f"智谱AI连接失败: {test_result['message']}"
            }

# 创建全局实例
sports_screenshot_analyzer = SportsScreenshotAnalyzer()
