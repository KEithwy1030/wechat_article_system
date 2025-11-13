"""
AI预测准确率统计服务 - WechatBOT版本
从ai_content_system迁移，负责计算和更新AI预测的命中率
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class AccuracyTracker:
    """AI预测准确率统计器"""
    
    def __init__(self):
        """初始化统计器"""
        logger.info("准确率统计器初始化")
        self._stats_cache = {
            'total_predictions': 0,
            'hit_count': 0,
            'miss_count': 0
        }
    
    def calculate_hit(self, predictions: List[str], actual_score: str) -> Dict:
        """
        计算单场比赛的命中情况
        
        Args:
            predictions: 预测比分列表 ["2-1", "1-0"]
            actual_score: 实际比分 "2-1" 或 "2:1"
        
        Returns:
            命中结果字典
        """
        if not predictions or not actual_score:
            return {
                'is_hit': False,
                'hit_type': None,
                'matched_score': None
            }
        
        try:
            # 统一比分格式
            normalized_actual = actual_score.replace(':', '-').strip()
            
            for i, pred_score in enumerate(predictions):
                normalized_pred = pred_score.replace(':', '-').strip()
                if normalized_pred == normalized_actual:
                    logger.info(f'预测命中：{pred_score} = {actual_score}')
                    return {
                        'is_hit': True,
                        'hit_type': f"预测{i+1}",
                        'matched_score': pred_score
                    }
            
            logger.info(f'预测未命中：{predictions} != {actual_score}')
            return {
                'is_hit': False,
                'hit_type': None,
                'matched_score': None
            }
            
        except Exception as e:
            logger.error(f'计算命中情况失败: {str(e)}')
            return {
                'is_hit': False,
                'hit_type': None,
                'matched_score': None,
                'error': str(e)
            }
    
    def update_hit_rate(self, match_code: str, predictions: List[str], 
                        actual_score: str) -> bool:
        """
        更新单场比赛的命中率统计
        
        Args:
            match_code: 比赛编号
            predictions: 预测比分列表
            actual_score: 实际比分
        
        Returns:
            是否更新成功
        """
        try:
            # 计算命中情况
            hit_result = self.calculate_hit(predictions, actual_score)
            
            # 更新统计缓存
            self._stats_cache['total_predictions'] += 1
            if hit_result['is_hit']:
                self._stats_cache['hit_count'] += 1
            else:
                self._stats_cache['miss_count'] += 1
            
            logger.info(f'更新命中率统计：{match_code} - {hit_result}')
            
            # TODO: 后续集成数据库后，这里保存到数据库
            
            return True
            
        except Exception as e:
            logger.error(f'更新命中率失败 {match_code}: {str(e)}')
            return False
    
    def batch_update_hit_rates(self, match_results: Dict[str, Dict]) -> int:
        """
        批量更新多场比赛的命中率
        
        Args:
            match_results: 比赛结果字典
                {
                    "周五001": {
                        "predictions": ["2-1", "1-0"],
                        "actual_score": "2-1"
                    }
                }
        
        Returns:
            更新成功的数量
        """
        updated_count = 0
        
        for match_code, data in match_results.items():
            try:
                predictions = data.get('predictions', [])
                actual_score = data.get('actual_score', '')
                
                if self.update_hit_rate(match_code, predictions, actual_score):
                    updated_count += 1
                    
            except Exception as e:
                logger.error(f'批量更新失败 {match_code}: {str(e)}')
        
        logger.info(f'批量更新完成，成功 {updated_count}/{len(match_results)} 场')
        return updated_count
    
    def get_accuracy_stats(self) -> Dict:
        """
        获取当前准确率统计
        
        Returns:
            统计数据字典
        """
        try:
            total = self._stats_cache['total_predictions']
            hits = self._stats_cache['hit_count']
            
            # 计算命中率
            hit_rate = (hits / total * 100) if total > 0 else 0.0
            
            stats = {
                'total_predictions': total,
                'hit_count': hits,
                'miss_count': self._stats_cache['miss_count'],
                'hit_rate': round(hit_rate, 2),
                'last_updated': datetime.now().isoformat()
            }
            
            logger.info(f'准确率统计：{stats}')
            return stats
            
        except Exception as e:
            logger.error(f'获取统计数据失败: {str(e)}')
            return {
                'total_predictions': 0,
                'hit_count': 0,
                'miss_count': 0,
                'hit_rate': 0.0,
                'last_updated': datetime.now().isoformat(),
                'error': str(e)
            }
    
    def get_detailed_stats(self) -> Dict:
        """
        获取详细统计信息
        
        Returns:
            详细统计数据
        """
        basic_stats = self.get_accuracy_stats()
        
        # 添加更多统计维度
        total = basic_stats['total_predictions']
        
        detailed = {
            **basic_stats,
            'accuracy_level': self._get_accuracy_level(basic_stats['hit_rate']),
            'performance': {
                'excellent': basic_stats['hit_count'] if basic_stats['hit_rate'] >= 70 else 0,
                'good': basic_stats['hit_count'] if 50 <= basic_stats['hit_rate'] < 70 else 0,
                'average': basic_stats['hit_count'] if 30 <= basic_stats['hit_rate'] < 50 else 0,
                'poor': basic_stats['hit_count'] if basic_stats['hit_rate'] < 30 else 0
            },
            'trend': 'stable'  # TODO: 计算趋势
        }
        
        return detailed
    
    def _get_accuracy_level(self, hit_rate: float) -> str:
        """获取准确率等级"""
        if hit_rate >= 70:
            return 'excellent'
        elif hit_rate >= 50:
            return 'good'
        elif hit_rate >= 30:
            return 'average'
        else:
            return 'poor'
    
    def reset_stats(self):
        """重置统计数据（用于测试或新周期开始）"""
        self._stats_cache = {
            'total_predictions': 0,
            'hit_count': 0,
            'miss_count': 0
        }
        logger.info('统计数据已重置')


# 创建统计器实例
accuracy_tracker = AccuracyTracker()

