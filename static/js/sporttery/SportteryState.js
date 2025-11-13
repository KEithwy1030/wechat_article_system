/**
 * SportteryState.js - 竞彩数据状态管理
 * 统一管理所有状态数据，自动计算日期分组，避免数据不一致问题
 */
class SportteryState {
    constructor() {
        // 单一数据源：所有状态数据都在这里
        this.state = {
            matches: [],              // 赛程数据
            results: [],              // 赛果数据
            dateGroups: {},           // 日期分组（自动计算，无需手动维护）
            matchDateGroups: {},      // 赛程日期分组
            currentView: 'matches',   // 当前视图：'matches' 或 'results'
            loading: false,           // 加载状态
            selectedDate: null        // 当前选中的日期
        };
        
        // 状态变化监听器（用于自动更新UI）
        this.listeners = [];
    }
    
    /**
     * 更新状态（自动计算日期分组）
     * @param {Object} updates - 要更新的状态对象
     */
    setState(updates) {
        // 合并更新到当前状态
        this.state = { ...this.state, ...updates };
        
        // 如果更新了 results 或 matches，自动重新计算日期分组
        if (updates.results !== undefined) {
            this._updateResultsDateGroups();
        }
        if (updates.matches !== undefined) {
            this._updateMatchDateGroups();
        }
        
        // 通知所有监听器状态已更新
        this._notifyListeners();
    }
    
    /**
     * 获取当前状态（返回副本，防止外部直接修改）
     * @returns {Object} 状态对象副本
     */
    getState() {
        return { ...this.state };
    }
    
    /**
     * 添加状态变化监听器
     * @param {Function} listener - 监听器函数
     */
    onChange(listener) {
        this.listeners.push(listener);
    }
    
    /**
     * 移除状态变化监听器
     * @param {Function} listener - 要移除的监听器函数
     */
    removeListener(listener) {
        const index = this.listeners.indexOf(listener);
        if (index > -1) {
            this.listeners.splice(index, 1);
        }
    }
    
    /**
     * 自动计算赛果日期分组（解决 dateGroups 未保存的问题）
     * @private
     */
    _updateResultsDateGroups() {
        const dateGroups = {};
        let skippedCount = 0;
        
        if (!this.state.results || this.state.results.length === 0) {
            this.state.dateGroups = {};
            return;
        }
        
        this.state.results.forEach(result => {
            const dateKey = SportteryUtils.extractDateKey(result);
            if (dateKey) {
                if (!dateGroups[dateKey]) {
                    dateGroups[dateKey] = [];
                }
                dateGroups[dateKey].push(result);
            } else {
                skippedCount++;
                console.warn('无法提取日期键，跳过:', result.match_code, {
                    group_date: result.group_date,
                    match_time: result.match_time,
                    result_scraped_at: result.result_scraped_at,
                    time_display: result.time_display
                });
            }
        });
        
        // 更新状态中的 dateGroups（关键：确保保存到状态中）
        this.state.dateGroups = dateGroups;
        
        if (skippedCount > 0) {
            console.warn(`有 ${skippedCount} 条数据无法提取日期键，已跳过分组`);
        }
    }
    
    /**
     * 自动计算赛程日期分组
     * 只处理有有效下注时间（group_date）的比赛
     * @private
     */
    _updateMatchDateGroups() {
        const dateGroups = {};
        
        this.state.matches.forEach(match => {
            const dateKey = SportteryUtils.extractMatchDateKey(match);
            // 只处理有下注时间的比赛（dateKey不为null）
            if (dateKey) {
                if (!dateGroups[dateKey]) {
                    dateGroups[dateKey] = [];
                }
                dateGroups[dateKey].push(match);
            } else {
                // 记录警告但不添加到分组（避免创建"null"分组）
                console.warn(`比赛 ${match.match_code} 没有有效的下注时间（group_date），已跳过分组`);
            }
        });
        
        this.state.matchDateGroups = dateGroups;
    }
    
    /**
     * 通知所有监听器状态已更新
     * @private
     */
    _notifyListeners() {
        this.listeners.forEach(listener => {
            try {
                listener(this.getState());
            } catch (error) {
                console.error('状态监听器执行失败:', error);
            }
        });
    }
    
    /**
     * 获取指定日期的赛果数据
     * @param {string} dateKey - 日期键（如："11-04"）
     * @returns {Array} 该日期的赛果数据
     */
    getResultsByDate(dateKey) {
        return this.state.dateGroups[dateKey] || [];
    }
    
    /**
     * 获取指定日期的赛程数据
     * @param {string} dateKey - 日期键（如："11-04"）
     * @returns {Array} 该日期的赛程数据
     */
    getMatchesByDate(dateKey) {
        return this.state.matchDateGroups[dateKey] || [];
    }
    
    /**
     * 获取所有日期键（按日期倒序排列）
     * @returns {Array<string>} 日期键数组
     */
    getDateKeys() {
        return Object.keys(this.state.dateGroups).sort((a, b) => {
            return b.localeCompare(a);  // 倒序：最新的在前
        });
    }
    
    /**
     * 获取赛程日期键（按日期正序排列）
     * @returns {Array<string>} 日期键数组
     */
    getMatchDateKeys() {
        return Object.keys(this.state.matchDateGroups).sort();
    }
}

