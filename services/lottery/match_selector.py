"""
比赛选择器 - AI自动选择3场比赛进行深度分析
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import random

logger = logging.getLogger(__name__)

class MatchSelector:
    """AI自动选择3场比赛进行深度分析"""
    
    def __init__(self):
        # 联赛重要性权重
        self.league_weights = {
            '欧冠': 10,
            '英超': 9,
            '西甲': 9,
            '德甲': 8,
            '意甲': 8,
            '法甲': 7,
            '世预赛': 8,
            '欧预赛': 7,
            '英冠': 5,
            '英甲': 4,
            '西乙': 4,
            '德乙': 4,
            '意乙': 4,
            '法乙': 4,
            '其他': 3
        }
        
        # 球队知名度权重（豪门球队）
        self.team_weights = {
            # 英超豪门
            '曼城': 9, '利物浦': 9, '阿森纳': 8, '切尔西': 8, '曼联': 8, '热刺': 7,
            # 西甲豪门
            '皇马': 10, '巴萨': 10, '马竞': 8, '塞维利亚': 6, '比利亚雷亚尔': 6,
            # 德甲豪门
            '拜仁': 9, '多特': 8, '莱比锡': 6, '勒沃库森': 6,
            # 意甲豪门
            '尤文': 8, '国米': 8, 'AC米兰': 8, '那不勒斯': 7, '罗马': 7,
            # 法甲豪门
            '巴黎': 8, '马赛': 6, '里昂': 6,
            # 其他知名球队
            '阿贾克斯': 6, '波尔图': 6, '本菲卡': 6, '凯尔特人': 5
        }
        
        # 特殊比赛类型权重
        self.special_match_types = {
            '德比': 3,  # 同城德比
            '榜首大战': 4,  # 积分榜前两名
            '保级大战': 2,  # 保级关键战
            '欧冠淘汰赛': 5,  # 欧冠淘汰赛
            '决赛': 6  # 各种决赛
        }
    
    def calculate_match_priority(self, match: Dict) -> float:
        """计算比赛优先级评分"""
        try:
            # 基础分数
            base_score = 0.0
            
            # 1. 联赛重要性 (30%)
            league = match.get('league', '其他')
            league_score = self.league_weights.get(league, 3)
            base_score += league_score * 0.3
            
            # 2. 球队知名度 (25%)
            home_team = match.get('home_team', '')
            away_team = match.get('away_team', '')
            home_weight = self.team_weights.get(home_team, 1)
            away_weight = self.team_weights.get(away_team, 1)
            team_score = (home_weight + away_weight) / 2
            base_score += team_score * 0.25
            
            # 3. 比赛时间权重 (20%) - 明天比后天重要
            match_time = match.get('match_time', '')
            time_score = self._calculate_time_score(match_time)
            base_score += time_score * 0.2
            
            # 4. 历史热度 (15%) - 基于比赛类型
            match_type_score = self._detect_special_match_type(match)
            base_score += match_type_score * 0.15
            
            # 5. 随机因子 (10%) - 避免完全可预测
            random_factor = random.uniform(0.8, 1.2)
            base_score += random_factor * 0.1
            
            # 6. 数据质量加分
            if match.get('is_official_active', False):
                base_score += 0.5  # 官方活跃比赛加分
            
            logger.info(f"比赛 {match.get('match_display', 'Unknown')} 优先级评分: {base_score:.2f}")
            return base_score
            
        except Exception as e:
            logger.error(f"计算比赛优先级失败: {e}")
            return 0.0
    
    def _calculate_time_score(self, match_time: str) -> float:
        """计算时间权重"""
        try:
            if not match_time:
                return 1.0
            
            # 解析比赛时间（支持多种格式）
            try:
                match_datetime = datetime.fromisoformat(match_time.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                try:
                    match_datetime = datetime.strptime(match_time, '%Y-%m-%d %H:%M')
                except ValueError:
                    match_datetime = datetime.strptime(match_time, '%Y-%m-%d %H:%M:%S')
            
            now = datetime.now()
            
            # 计算距离现在的小时数
            hours_diff = (match_datetime - now).total_seconds() / 3600
            
            # 时间越近权重越高
            if hours_diff <= 24:  # 明天
                return 5.0
            elif hours_diff <= 48:  # 后天
                return 3.0
            else:  # 更远
                return 1.0
                
        except Exception as e:
            logger.error(f"计算时间权重失败: {e}, match_time={match_time}")
            return 1.0
    
    def _detect_special_match_type(self, match: Dict) -> float:
        """检测特殊比赛类型"""
        try:
            home_team = match.get('home_team', '').lower()
            away_team = match.get('away_team', '').lower()
            league = match.get('league', '').lower()
            
            # 检测德比
            if self._is_derby(home_team, away_team):
                return self.special_match_types['德比']
            
            # 检测欧冠淘汰赛
            if '欧冠' in league and ('淘汰' in league or '1/8' in league or '1/4' in league):
                return self.special_match_types['欧冠淘汰赛']
            
            # 检测决赛
            if '决赛' in league or 'final' in league.lower():
                return self.special_match_types['决赛']
            
            return 1.0  # 普通比赛
            
        except Exception as e:
            logger.error(f"检测特殊比赛类型失败: {e}")
            return 1.0
    
    def _is_derby(self, home_team: str, away_team: str) -> bool:
        """检测是否为德比"""
        # 知名德比
        derbies = [
            ('曼城', '曼联'),  # 曼市德比
            ('利物浦', '埃弗顿'),  # 默西塞德德比
            ('阿森纳', '热刺'),  # 北伦敦德比
            ('皇马', '巴萨'),  # 国家德比
            ('国米', 'AC米兰'),  # 米兰德比
            ('尤文', '都灵'),  # 都灵德比
            ('拜仁', '多特'),  # 德国国家德比
            ('巴黎', '马赛'),  # 法国国家德比
        ]
        
        for derby in derbies:
            if (derby[0] in home_team and derby[1] in away_team) or \
               (derby[1] in home_team and derby[0] in away_team):
                return True
        
        return False
    
    def select_top_3_matches(self, matches: List[Dict]) -> List[Dict]:
        """自动选择优先级最高的3场比赛"""
        try:
            if not matches:
                logger.warning("没有比赛数据可供选择")
                return []
            
            if len(matches) <= 3:
                logger.info(f"比赛数量({len(matches)})不足3场，返回所有比赛")
                return matches
            
            # 计算每场比赛的优先级
            matches_with_scores = []
            for match in matches:
                score = self.calculate_match_priority(match)
                matches_with_scores.append({
                    'match': match,
                    'score': score
                })
            
            # 按分数排序，选择前3名
            sorted_matches = sorted(matches_with_scores, key=lambda x: x['score'], reverse=True)
            selected_matches = [item['match'] for item in sorted_matches[:3]]
            
            logger.info(f"从{len(matches)}场比赛中选择了3场:")
            for i, match in enumerate(selected_matches, 1):
                logger.info(f"  {i}. {match.get('match_display', 'Unknown')} (评分: {sorted_matches[i-1]['score']:.2f})")
            
            return selected_matches
            
        except Exception as e:
            logger.error(f"选择比赛失败: {e}")
            return []
    
    def select_random_3_matches(self, matches: List[Dict]) -> List[Dict]:
        """随机选择3场比赛进行深度分析"""
        try:
            if not matches:
                logger.warning("没有比赛数据可供选择")
                return []
            
            if len(matches) <= 3:
                logger.info(f"比赛数量({len(matches)})不足3场，返回所有比赛")
                return matches
            
            # 从所有比赛中随机选择3场
            selected_matches = random.sample(matches, 3)
            
            logger.info(f"从{len(matches)}场比赛中随机选择了3场:")
            for i, match in enumerate(selected_matches, 1):
                match_code = match.get('match_code', 'Unknown')
                match_display = match.get('match_display', f"{match.get('home_team', '')} vs {match.get('away_team', '')}")
                logger.info(f"  {i}. {match_code} - {match_display}")
            
            return selected_matches
            
        except Exception as e:
            logger.error(f"随机选择比赛失败: {e}")
            # 如果随机选择失败，fallback到前3场
            logger.warning("随机选择失败，使用前3场比赛")
            return matches[:3]
    
    def get_selection_reason(self, selected_matches: List[Dict]) -> str:
        """获取选择理由说明"""
        try:
            if not selected_matches:
                return "没有选择任何比赛"
            
            reasons = []
            for i, match in enumerate(selected_matches, 1):
                match_display = match.get('match_display', 'Unknown')
                league = match.get('league', 'Unknown')
                
                # 分析选择理由
                reason_parts = []
                
                # 联赛重要性
                if league in ['欧冠', '英超', '西甲', '德甲', '意甲', '法甲']:
                    reason_parts.append(f"重要联赛({league})")
                
                # 球队知名度
                home_team = match.get('home_team', '')
                away_team = match.get('away_team', '')
                if any(team in self.team_weights for team in [home_team, away_team]):
                    reason_parts.append("豪门对决")
                
                # 特殊比赛
                if self._is_derby(home_team, away_team):
                    reason_parts.append("德比大战")
                
                reason = f"{match_display}: {', '.join(reason_parts) if reason_parts else '综合评分较高'}"
                reasons.append(f"{i}. {reason}")
            
            return "选择理由:\n" + "\n".join(reasons)
            
        except Exception as e:
            logger.error(f"生成选择理由失败: {e}")
            return "选择理由生成失败"

# 全局实例
match_selector = MatchSelector()
