/**
 * SportteryUtils.js - 竞彩数据工具函数
 * 提供日期格式化、日期键提取等通用功能
 */
class SportteryUtils {
    /**
     * 格式化时间戳为本地时间字符串
     * @param {string|number} timestamp - 时间戳或日期字符串
     * @returns {string} 格式化后的时间字符串
     */
    static formatTime(timestamp) {
        if (!timestamp) return '--';
        const date = new Date(timestamp);
        // 检查日期是否有效
        if (isNaN(date.getTime())) return '--';
        return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    }
    
    /**
     * 格式化秒数为可读时间（用于任务剩余时间等）
     * @param {number} seconds - 秒数
     * @returns {string} 格式化后的时间字符串（如："5分30秒"）
     */
    static formatDuration(seconds) {
        // 处理无效或负数时间
        if (!seconds || seconds < 0 || isNaN(seconds)) {
            return '0秒';
        }
        
        if (seconds < 60) {
            return `${Math.floor(seconds)}秒`;
        } else {
            const minutes = Math.floor(seconds / 60);
            const secs = Math.floor(seconds % 60);
            return `${minutes}分${secs}秒`;
        }
    }
    
    /**
     * 从比赛数据中提取日期键（MM-DD格式）
     * 必须使用 group_date（下注时间）进行分组，不使用 match_time（比赛时间）
     * 与赛程分组逻辑保持一致
     * @param {Object} data - 比赛数据对象
     * @returns {string|null} 日期键（如："11-04"），如果没有有效的group_date则返回null
     */
    static extractDateKey(data) {
        // 必须使用下注时间（group_date）进行分组，不使用比赛时间
        const groupDate = data.group_date;
        
        // 检查group_date是否存在且不为空字符串
        if (groupDate && groupDate.trim() !== '') {
            try {
                // group_date格式：YYYY-MM-DD -> MM-DD
                if (groupDate.length >= 10) {
                    return `${groupDate.slice(5, 7)}-${groupDate.slice(8, 10)}`;
                }
            } catch (e) {
                console.warn('解析分组日期失败:', groupDate, e);
            }
        }
        
        // 如果没有有效的group_date，返回null
        // 这样在分组时可以过滤掉没有下注时间的赛果
        return null;
    }
    
    /**
     * 从比赛编号中提取数字部分（用于排序）
     * @param {string} matchCode - 比赛编号（如："周一001"）
     * @returns {number} 数字部分（如：1）
     */
    static extractMatchNumber(matchCode) {
        const match = matchCode.match(/(\d+)$/);
        return match ? parseInt(match[1]) : 0;
    }
    
    /**
     * 从比赛数据中提取日期键（用于赛程分组）
     * 必须使用 group_date（下注时间）进行分组，不使用 match_time（比赛时间）
     * @param {Object} match - 比赛数据对象
     * @returns {string|null} 日期键（如："11-04"），如果没有有效的group_date则返回null
     */
    static extractMatchDateKey(match) {
        // 必须使用下注时间（group_date）进行分组，不使用比赛时间
        const groupDate = match.group_date;
        
        // 检查group_date是否存在且不为空字符串
        if (groupDate && groupDate.trim() !== '') {
            try {
                // group_date格式：YYYY-MM-DD -> MM-DD
                if (groupDate.length >= 10) {
                    return `${groupDate.slice(5, 7)}-${groupDate.slice(8, 10)}`;
                }
            } catch (e) {
                console.warn('分组日期解析失败:', groupDate, e);
            }
        }
        
        // 如果没有有效的group_date，返回null
        // 这样在分组时可以过滤掉没有下注时间的比赛
        return null;
    }
    
    /**
     * 判断比赛是否正在进行中
     * 判断逻辑：开赛时间 <= 当前时间 < 开赛时间 + 2小时
     * @param {string} matchTime - 比赛时间字符串（格式：YYYY-MM-DD HH:MM 或 ISO格式）
     * @returns {boolean} 是否正在进行中
     */
    static isMatchInProgress(matchTime) {
        if (!matchTime) return false;
        
        try {
            const matchDateTime = new Date(matchTime);
            if (isNaN(matchDateTime.getTime())) return false;
            
            const now = new Date();
            const endTime = new Date(matchDateTime.getTime() + 2 * 60 * 60 * 1000); // 开赛时间 + 2小时
            
            // 判断：开赛时间 <= 当前时间 < 开赛时间 + 2小时
            return matchDateTime <= now && now < endTime;
        } catch (e) {
            console.warn('判断比赛进行中状态失败:', matchTime, e);
            return false;
        }
    }
}

