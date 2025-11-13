/**
 * SportteryDataService.js - 竞彩数据获取服务
 * 统一处理所有数据获取请求，封装API调用逻辑
 */
class SportteryDataService {
    /**
     * 获取赛程数据（已废弃，请使用fetchAllMatches）
     * @deprecated 使用 fetchAllMatches 代替，该方法保留仅为向后兼容
     * @param {boolean} forceRefresh - 是否强制刷新（true=抓取新数据，false=使用缓存）
     * @returns {Promise<Object>} 包含 status, data, count 的结果对象
     */
    async fetchMatches(forceRefresh = false) {
        try {
            if (forceRefresh) {
                // 强制抓取新数据
                const response = await fetch('/api/lottery/collect-schedule', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
                
                if (!response.ok) {
                    throw new Error('收集赛程失败');
                }
                
                const result = await response.json();
                
                return {
                    status: 'success',
                    data: result.data?.matches || [],
                    count: result.data?.count || 0
                };
            } else {
                // 从缓存获取数据
                const response = await fetch(`/api/lottery/schedule?t=${Date.now()}`, {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json',
                        'Cache-Control': 'no-cache'
                    }
                });
                
                if (!response.ok) {
                    throw new Error('获取赛程数据失败');
                }
                
                const result = await response.json();
                
                if (result.status === 'success' && result.data && result.data.length > 0) {
                    // 确保状态字段一致性
                    result.data.forEach(match => {
                        if (match.source_type === 'deep') {
                            match.prediction_type = 'deep';
                        } else if (!match.prediction_type) {
                            match.prediction_type = 'waiting';
                        }
                    });
                    
                    return {
                        status: 'success',
                        data: result.data,
                        count: result.count || 0
                    };
                } else {
                    // 缓存为空
                    return {
                        status: 'success',
                        data: [],
                        count: 0
                    };
                }
            }
        } catch (error) {
            console.error('获取赛程数据失败:', error);
            return {
                status: 'error',
                message: error.message || '未知错误',
                data: [],
                count: 0
            };
        }
    }
    
    /**
     * 获取所有比赛数据（合并赛程和赛果）
     * @param {boolean} forceRefresh - 是否强制刷新赛程
     * @param {number} daysBack - 赛果查询天数（默认7天）
     * @returns {Promise<Object>} 包含 status, data, count 的结果对象
     */
    async fetchAllMatches(forceRefresh = false, daysBack = 7) {
        try {
            // 如果强制刷新，先触发赛程抓取
            if (forceRefresh) {
                await fetch('/api/lottery/collect-schedule', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
            }
            
            // 获取合并数据
            const response = await fetch(`/api/lottery/all-matches?days_back=${daysBack}&t=${Date.now()}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'Cache-Control': 'no-cache'
                }
            });
            
            if (!response.ok) {
                throw new Error('获取合并数据失败');
            }
            
            const result = await response.json();
            
            if (result.status === 'success') {
                return {
                    status: 'success',
                    data: result.data || [],
                    count: result.count || 0,
                    schedule_count: result.schedule_count || 0,
                    completed_count: result.completed_count || 0
                };
            } else {
                throw new Error(result.message || '获取数据失败');
            }
        } catch (error) {
            console.error('获取合并数据失败:', error);
            return {
                status: 'error',
                message: error.message || '未知错误',
                data: [],
                count: 0
            };
        }
    }
    
    /**
     * 获取赛果数据（已结束的比赛，包含预测和赛果）
     * @param {number} daysBack - 查询多少天前的数据（默认7天）
     * @returns {Promise<Object>} 包含 status, data, count 的结果对象
     */
    async fetchResults(daysBack = 7) {
        try {
            const response = await fetch(`/api/lottery/completed-matches?days_back=${daysBack}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error('获取赛果数据失败');
            }
            
            const result = await response.json();
            
            if (result.status === 'success') {
                return {
                    status: 'success',
                    data: result.data || [],
                    count: result.count || 0
                };
            } else {
                return {
                    status: 'error',
                    message: result.message || '未知错误',
                    data: [],
                    count: 0
                };
            }
        } catch (error) {
            console.error('获取赛果数据失败:', error);
            return {
                status: 'error',
                message: error.message || '未知错误',
                data: [],
                count: 0
            };
        }
    }
    
    /**
     * 触发赛果抓取（手动更新赛果）
     * @returns {Promise<Object>} 包含 status, message 的结果对象
     */
    async triggerResultScraping() {
        try {
            const response = await fetch('/api/lottery/update-results', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error('触发赛果抓取失败');
            }
            
            const result = await response.json();
            return result;
        } catch (error) {
            console.error('触发赛果抓取失败:', error);
            return {
                status: 'error',
                message: error.message || '未知错误'
            };
        }
    }
    
    /**
     * 合并文章状态（用于显示"查看文章"入口）
     * @param {Array} matches - 比赛数据数组
     * @returns {Promise<Array>} 合并后的比赛数据数组
     */
    async mergeArticleStatus(matches) {
        try {
            // 这里可以调用API获取文章状态，或者直接返回
            // 目前先返回原数据，后续可以扩展
            return matches;
        } catch (error) {
            console.warn('合并文章状态失败:', error);
            return matches;
        }
    }
    
    /**
     * 获取统计数据
     * @returns {Promise<Object>} 统计数据对象
     */
    async fetchStats() {
        try {
            const response = await fetch('/api/lottery/stats', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error('获取统计数据失败');
            }
            
            const result = await response.json();
            return result;
        } catch (error) {
            console.error('获取统计数据失败:', error);
            return {
                status: 'error',
                message: error.message || '未知错误'
            };
        }
    }
}

