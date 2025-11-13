/**
 * SportteryManager.js - 竞彩数据管理器（重构版）
 * 使用模块化架构，解决dateGroups未保存的问题
 * 
 * 注意：此版本为渐进式重构，保留所有公共方法接口，确保向后兼容
 */

// 确保工具类已加载
if (typeof SportteryUtils === 'undefined') {
    console.error('SportteryUtils未加载，请确保在SportteryManager之前加载');
}

// 确保状态管理器已加载
if (typeof SportteryState === 'undefined') {
    console.error('SportteryState未加载，请确保在SportteryManager之前加载');
}

// 确保数据服务已加载
if (typeof SportteryDataService === 'undefined') {
    console.error('SportteryDataService未加载，请确保在SportteryManager之前加载');
}

// 确保渲染器已加载
if (typeof SportteryRenderer === 'undefined') {
    console.error('SportteryRenderer未加载，请确保在SportteryManager之前加载');
}

const SPORTTERY_PANEL_ID = 'sporttery-panel';

function sportteryToast(type, title, message, options) {
    if (typeof window.showToast === 'function') {
        const toastOptions = Object.assign({}, options || {}, { panel: SPORTTERY_PANEL_ID });
        window.showToast(type, title, message, toastOptions);
    }
}

function markSportteryPanelVisited() {
    if (window.ToastRouter && typeof window.ToastRouter.markVisited === 'function') {
        window.ToastRouter.markVisited(SPORTTERY_PANEL_ID);
    }
}

if (window.ToastRouter && typeof window.ToastRouter.registerPanel === 'function') {
    window.ToastRouter.registerPanel(SPORTTERY_PANEL_ID);
}

class SportteryManager {
    constructor() {
        // 初始化模块
        this.state = new SportteryState();
        
        // 防重复执行标志（保留，用于防止快速连续调用）
        this._refreshingAccuracy = false;
        this._refreshingMatches = false;
        this.dataService = new SportteryDataService();
        this.renderer = new SportteryRenderer(this);
        
        // 兼容旧代码的属性
        this.currentData = null;
        this.allResultsData = null;
        this.dateGroups = {};  // 从状态中自动同步
        this._quickPredictionTimers = {}; // 记录快速预测轮询定时器
        this._processingStates = {}; // 记录比赛的预测执行状态
        this._currentWorkbenchArticle = null; // 当前工作台文章信息缓存
        this.currentTaskId = null;
        this._quickPredictionButtonState = null;
        this._deepAnalysisButtonState = null;
        this._quickPredictionPollingActive = false;
        this._deepAnalysisPollingActive = false;
        this._quickPredictionPollingTimer = null;
        this._deepAnalysisPollingTimer = null;
        
        // 监听状态变化，自动更新UI和兼容属性
        this.state.onChange((newState) => {
            // 同步到兼容属性
            this.currentData = newState.matches;
            this.allResultsData = newState.results;
            this.dateGroups = newState.dateGroups;  // 关键：自动同步dateGroups
        });
        
        // 只绑定事件，不自动加载数据（由 AppInitializer 统一控制）
        this.bindEvents();
    }
    
    init() {
        // 已废弃：数据加载由 AppInitializer 统一控制
        // 保留此方法仅为向后兼容
        this.bindEvents();
    }
    
    bindEvents() {
        // 刷新数据按钮 - 强制抓取新数据
        const refreshBtn = document.getElementById('refresh-sporttery-data');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                markSportteryPanelVisited();
                this.forceRefreshData();
            });
        }
        
        // 查看赛果按钮（保留用于触发赛果抓取）
        const viewResultsBtn = document.getElementById('view-results');
        if (viewResultsBtn) {
            viewResultsBtn.addEventListener('click', () => {
                markSportteryPanelVisited();
                this.loadResultsData();
            });
        }
        
        // 刷新显示按钮 - 仅从数据库读取最新数据，不触发抓取
        const refreshDisplayBtn = document.getElementById('refresh-display-data');
        if (refreshDisplayBtn) {
            refreshDisplayBtn.addEventListener('click', () => {
                markSportteryPanelVisited();
                this.refreshMatchesData();
            });
        }
        
        const quickPredictionBtn = document.getElementById('quick-prediction');
        if (quickPredictionBtn) {
            quickPredictionBtn.addEventListener('click', () => {
                this.runQuickPrediction();
            });
        }
        
        const deepAnalysisBtn = document.getElementById('deep-analysis');
        if (deepAnalysisBtn) {
            deepAnalysisBtn.addEventListener('click', () => {
                this.runDeepAnalysis();
            });
        }
        
        const interruptBtn = document.getElementById('interrupt-task-btn');
        if (interruptBtn) {
            interruptBtn.addEventListener('click', () => {
                this.interruptCurrentTask();
            });
        }
        
        // tab切换按钮已从HTML中移除，无需隐藏逻辑
        
        // 已移除编辑结果功能
        
        // 单场比赛快速预测按钮事件委托
        document.addEventListener('click', (e) => {
            if (e.target.closest('.quick-predict-single-btn')) {
                e.preventDefault();
                markSportteryPanelVisited();
                const link = e.target.closest('.quick-predict-single-btn');
                const matchCode = link.dataset.matchCode;
                this.quickPredictSingleMatch(matchCode);
            }
        });
        
        // 单场比赛深度分析按钮事件委托
        document.addEventListener('click', (e) => {
            if (e.target.closest('.deep-analysis-single-btn')) {
                e.preventDefault();
                markSportteryPanelVisited();
                const link = e.target.closest('.deep-analysis-single-btn');
                const matchCode = link.dataset.matchCode;
                this.deepAnalysisSingleMatch(matchCode);
            }
        });

        // 下拉选择"重新预测"事件委托（替代双按钮）
        document.addEventListener('change', (e) => {
            const select = e.target.closest('.predict-action-select');
            if (select) {
                const action = select.value;
                const matchCode = select.dataset.matchCode;
                console.log('下拉选择触发:', { action, matchCode, select: select });
                if (!action) {
                    console.log('未选择操作，跳过');
                    return;
                }
                if (action === 'quick') {
                    console.log('触发快速预测:', matchCode);
                    markSportteryPanelVisited();
                    this.quickPredictSingleMatch(matchCode);
                } else if (action === 'deep') {
                    console.log('触发深度分析:', matchCode);
                    markSportteryPanelVisited();
                    this.deepAnalysisSingleMatch(matchCode);
                }
                // 重置选择，避免重复误触
                select.value = '';
            }
        });
    }
    
    async loadInitialData() {
        // 统一使用合并数据加载
        await this.loadMergedData();
    }
    
    async loadMergedData(forceRefresh = false) {
        const scrollElement = document.scrollingElement || document.documentElement;
        const previousScrollTop = scrollElement ? scrollElement.scrollTop : 0;
        const previousSelectedDate = this.state.getState().selectedDate;

        this.showLoading(true);
        this.updateStatus('正在获取数据...', 'warning');
        
        try {
            const result = await this.dataService.fetchAllMatches(forceRefresh, 7);
            
            if (result.status === 'success') {
                // 合并文章状态
                try {
                    await this.dataService.mergeArticleStatus(result.data);
                } catch (e) {
                    console.warn('合并文章状态失败', e);
                }
                
                // 分离赛程和赛果
                const matches = result.data.filter(m => !m.is_completed);
                const results = result.data.filter(m => m.is_completed);
                
                // 更新状态
                this.state.setState({
                    matches: matches,
                    results: results,
                    currentView: 'matches'
                });
                
                // 渲染合并表格（包含赛程和赛果）
                this.renderer.renderMergedTable(result.data);

                // 如果正在执行的预测已有结果，则清理状态
                Object.keys(this._processingStates).forEach(code => {
                    const type = this._processingStates[code];
                    if (this._hasProcessingResult(code, type)) {
                        this._setMatchProcessing(code, null);
                    }
                });

                // 恢复用户此前选择的日期分组（优先保持用户当前选择）
                const stateAfter = this.state.getState();
                const sortedDatesCache = Array.isArray(this._sortedDatesCache) ? this._sortedDatesCache : [];
                const matchDates = Object.keys(stateAfter.matchDateGroups || {}).sort().reverse();
                const resultDates = Object.keys(stateAfter.dateGroups || {}).sort().reverse();
                let targetDate = null;

                // 优先使用用户之前选择的日期（如果该日期仍然存在）
                if (previousSelectedDate) {
                    const allAvailableDates = [...matchDates, ...resultDates];
                    if (allAvailableDates.includes(previousSelectedDate)) {
                        targetDate = previousSelectedDate;
                        console.log('保持用户之前选择的日期分组:', previousSelectedDate);
                    }
                }
                
                // 如果之前的日期不存在或未选择，才使用最新的日期
                if (!targetDate) {
                    if (matchDates.length > 0) {
                        targetDate = matchDates[0];
                    } else if (sortedDatesCache.length > 0) {
                        targetDate = sortedDatesCache[0];
                    } else if (resultDates.length > 0) {
                        targetDate = resultDates[0];
                    }
                    console.log('使用最新日期分组:', targetDate);
                }

                console.log('loadMergedData targetDate resolution', {
                    previousSelectedDate: previousSelectedDate,
                    currentSelectedDate: this.state.getState().selectedDate,
                    sortedDatesCache,
                    matchDates,
                    resultDates,
                    targetDate
                });

                if (targetDate) {
                    const renderedContent = document.getElementById(`date-content-${targetDate}`);
                    const hasRenderedContent = renderedContent && renderedContent.innerHTML.trim().length > 0;

                    // 只有在日期改变或内容未渲染时才切换
                    if (this.state.getState().selectedDate !== targetDate || !hasRenderedContent) {
                        this.showDateContent(targetDate);
                    } else {
                        console.log('保持当前日期分组，无需切换');
                    }
                } else {
                    console.warn('loadMergedData 未找到可用的目标日期', {
                        sortedDatesCache,
                        matchDates,
                        resultDates
                    });
                }
                
                if (result.count > 0) {
                    this.updateStatus(`已加载 ${result.count} 场比赛（赛程：${result.schedule_count}，赛果：${result.completed_count}）`, 'success');
                    this.updateLastUpdateTime(new Date().toLocaleString());
                    if (typeof showToast !== 'undefined') {
                        sportteryToast('success', '加载成功', `已加载 ${result.count} 场比赛`);
                    }
                } else {
                    this.updateStatus('暂无数据', 'info');
                }
                
                this.initializeTooltips();
                this.loadStats();

                if (scrollElement) {
                    requestAnimationFrame(() => {
                        scrollElement.scrollTo({ top: previousScrollTop, behavior: 'auto' });
                    });
                }
            } else {
                this.updateStatus('数据获取失败', 'danger');
                if (typeof showToast !== 'undefined') {
                    sportteryToast('error', '数据获取失败', result.message || '未知错误');
                }
            }
        } catch (error) {
            this.updateStatus('网络错误', 'danger');
            if (typeof showToast !== 'undefined') {
                sportteryToast('error', '网络错误', '无法连接到服务器');
            }
            console.error('获取合并数据失败:', error);
        } finally {
            this.showLoading(false);
        }
    }
    
    // _hideTabSwitcher 方法已移除，tab切换按钮已从HTML中删除
    
    async refreshMatchesData() {
        // 防重复执行：如果正在执行，直接返回（防止快速连续调用）
        if (this._refreshingMatches) {
            console.log('赛程数据正在加载中，跳过重复调用');
            return;
        }
        
        // 标记为正在执行
        this._refreshingMatches = true;
        
        try {
            // 统一使用合并数据加载
            return await this.loadMergedData(false);
        } finally {
            // 清除执行标志（延迟清除，避免快速连续调用）
            setTimeout(() => {
                this._refreshingMatches = false;
            }, 500);
        }
    }
    
    async forceRefreshData() {
        const button = document.getElementById('refresh-sporttery-data');
        const originalText = button ? button.innerHTML : '';
        
        try {
            markSportteryPanelVisited();
            if (button) {
                this._refreshButtonState = { originalText };
                button.disabled = true;
                button.innerHTML = '<i class="bi bi-hourglass-split"></i> 执行中...';
            }
            
            this.showInterruptButton(true);
            this.showLoading(true);
            this.updateStatus('正在强制更新数据...', 'warning');
            
            await this.loadMergedData(true);
        } catch (error) {
            console.error('强制更新数据失败:', error);
            this.updateStatus('强制更新数据失败', 'error');
            if (typeof showToast !== 'undefined') {
                sportteryToast('error', '强制更新数据失败', error.message);
            }
        } finally {
            this.showLoading(false);
            if (button && this._refreshButtonState) {
                button.disabled = false;
                button.innerHTML = this._refreshButtonState.originalText;
                this._refreshButtonState = null;
            }
            this.showInterruptButton(false);
        }
    }
    
    async loadResultsData() {
        // 赛果更新：触发抓取后重新加载合并数据
        const button = document.getElementById('view-results');
        const originalText = button ? button.innerHTML : '';
        
        try {
            markSportteryPanelVisited();
            if (button) {
                this._resultsButtonState = { originalText };
                button.disabled = true;
                button.innerHTML = '<i class="bi bi-hourglass-split"></i> 执行中...';
            }
            
            this.showInterruptButton(true);
            this.showLoading(true);
            this.updateStatus('正在抓取赛果...', 'warning');
            
            // 先触发抓取
            const scrapeResult = await this.dataService.triggerResultScraping();
            
            if (scrapeResult.status === 'success') {
                this.updateStatus('赛果抓取完成，正在加载数据...', 'info');
                
                // 重新加载合并数据（包含最新赛果）
                await this.loadMergedData(false);
                
                if (typeof showToast !== 'undefined') {
                    sportteryToast('success', '赛果更新成功', '赛果数据已更新并刷新显示');
                }
            } else {
                this.updateStatus('赛果抓取失败', 'error');
                if (typeof showToast !== 'undefined') {
                    sportteryToast('error', '赛果抓取失败', scrapeResult.message || '未知错误');
                }
            }
        } catch (error) {
            console.error('更新赛果数据失败:', error);
            this.updateStatus('更新赛果数据失败', 'error');
            if (typeof showToast !== 'undefined') {
                sportteryToast('error', '更新赛果数据失败', error.message);
            }
        } finally {
            this.showLoading(false);
            if (button && this._resultsButtonState) {
                button.disabled = false;
                button.innerHTML = this._resultsButtonState.originalText;
                this._resultsButtonState = null;
            }
            this.showInterruptButton(false);
        }
    }
    
    // loadExistingResultsOnly, switchView, _updateResultsUI 方法已移除（统一使用合并视图）
    
    // ========== 公共方法（供onclick调用，保持向后兼容） ==========
    
    /**
     * 显示指定日期的赛程内容
     * @param {string} date - 日期键
     */
    showDateContent(date) {
        this.renderer.showDateContent(date);
        this.state.setState({ selectedDate: date });
    }
    
    /**
     * 显示指定日期的赛果内容（已废弃，统一使用showDateContent）
     * @deprecated 使用 showDateContent 代替
     * @param {string} dateKey - 日期键
     */
    showResultsDateContent(dateKey) {
        // 统一使用合并视图的日期切换
        this.showDateContent(dateKey);
    }
    
    /**
     * 渲染赛程表格（兼容方法，已统一使用renderMergedTable）
     * @deprecated 已统一使用合并视图，此方法保留仅为向后兼容
     */
    renderMatchesTable(matches) {
        // 统一使用合并表格渲染
        this.renderer.renderMergedTable(matches);
    }
    
    /**
     * 渲染赛果表格（兼容方法，已统一使用renderMergedTable）
     * @deprecated 已统一使用合并视图，此方法保留仅为向后兼容
     */
    renderResultsTable(results) {
        // 统一使用合并表格渲染（需要将results标记为is_completed）
        const mergedData = results.map(r => ({ ...r, is_completed: true }));
        this.renderer.renderMergedTable(mergedData);
    }
    
    /**
     * 渲染赛果日期导航栏（兼容方法，已统一使用renderDateNavbar）
     * @deprecated 已统一使用合并视图，此方法保留仅为向后兼容
     */
    renderResultsDateNavbar(results) {
        // 如果传入results，更新状态（会自动计算dateGroups）
        if (results) {
            this.state.setState({ results: results });
        }
        
        // 统一使用合并视图的日期导航栏
        const state = this.state.getState();
        const allDates = new Set([
            ...Object.keys(state.matchDateGroups || {}),
            ...Object.keys(state.resultsDateGroups || {})
        ]);
        this.renderer.renderDateNavbar(Array.from(allDates).sort());
    }
    
    // ========== 工具方法（保持向后兼容） ==========
    
    showLoading(show) {
        const loading = document.getElementById('sporttery-loading');
        if (loading) {
            loading.style.display = show ? 'block' : 'none';
        } else {
            console.warn('sporttery-loading元素未找到');
        }
    }

    getMatchData(matchCode) {
        const state = this.state.getState();
        const allMatches = [...(state.matches || []), ...(state.results || [])];
        return allMatches.find(m => m.match_code === matchCode) || null;
    }

    getMatchProcessingType(matchCode) {
        return this._processingStates[matchCode] || null;
    }

    _setMatchProcessing(matchCode, type) {
        if (!type) {
            delete this._processingStates[matchCode];
            this._clearQuickPredictionTimer(matchCode);
        } else {
            this._processingStates[matchCode] = type;
        }
        if (this.renderer && typeof this.renderer.updatePredictAction === 'function') {
            this.renderer.updatePredictAction(matchCode);
        }
    }
 
    updateStatus(message, type = 'info') {
        const statusEl = document.getElementById('sporttery-status');
        if (statusEl) {
            statusEl.textContent = message;
            statusEl.className = `badge status-badge bg-${type} w-100 text-start`;
        }
    }
    
    updateLastUpdateTime(timeStr) {
        const timeEl = document.getElementById('last-update-time');
        if (timeEl) {
            timeEl.textContent = timeStr;
        }
    }
    
    showInterruptButton(show) {
        const btn = document.getElementById('interrupt-task-btn');
        if (btn) {
            btn.style.display = show ? 'block' : 'none';
        }
    }
    
    async runQuickPrediction() {
        markSportteryPanelVisited();
        const button = document.getElementById('quick-prediction');
        if (!button) {
            console.warn('quick-prediction按钮未找到');
            return;
        }
        if (button.disabled) {
            console.warn('快速预测按钮已禁用，忽略重复点击');
            return;
        }
        
        const originalText = button.innerHTML;
        this._quickPredictionButtonState = { originalText };
        
        button.disabled = true;
        button.innerHTML = '<i class="bi bi-hourglass-split"></i> 执行中...';
        this.updateStatus('正在启动快速预测...', 'warning');
        
        try {
            const payload = {};
            const selectedDate = this._resolveSelectedDateKey();
            if (selectedDate) {
                payload.date = selectedDate;
            }
            
            const response = await fetch('/api/lottery/trigger-quick-predictions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            
            let data = null;
            try {
                data = await response.json();
            } catch (parseError) {
                console.warn('解析快速预测响应失败:', parseError);
            }
            
            if (!response.ok || !data || data.status !== 'success') {
                const message = data?.message || `快速预测任务启动失败 (HTTP ${response.status})`;
                throw new Error(message);
            }
            
            const taskId = data.task_id;
            if (!taskId) {
                throw new Error('服务器未返回任务ID');
            }
            
            const totalMatches = data.total_matches ?? data.task_data?.total_matches ?? 0;
            this.updateStatus(`快速预测任务已启动（${totalMatches} 场）`, 'info');
            sportteryToast('success', '快速预测已启动', `共 ${totalMatches} 场比赛进入预测队列`);
            
            this.currentTaskId = taskId;
            this.showInterruptButton(true);
            this._startQuickPredictionPolling(taskId);
        } catch (error) {
            console.error('快速预测启动失败:', error);
            const message = error?.message || '无法启动快速预测任务';
            sportteryToast('error', '快速预测失败', message);
            if (typeof window.showToast !== 'function') {
                alert(`快速预测失败：${message}`);
            }
            this.updateStatus(`快速预测失败：${message}`, 'danger');
            this._restoreQuickPredictionButton();
        }
    }
    
    async runDeepAnalysis() {
        markSportteryPanelVisited();
        const button = document.getElementById('deep-analysis');
        if (!button) {
            console.warn('deep-analysis按钮未找到');
            return;
        }
        if (button.disabled) {
            console.warn('深度分析按钮已禁用，忽略重复点击');
            return;
        }
        
        const originalText = button.innerHTML;
        this._deepAnalysisButtonState = { originalText };
        
        button.disabled = true;
        button.innerHTML = '<i class="bi bi-hourglass-split"></i> 执行中...';
        this.updateStatus('正在启动深度分析...', 'warning');
        
        try {
            const payload = { date: this._resolveDeepAnalysisDate() };
            
            const response = await fetch('/api/lottery/deep-analysis', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            
            let data = null;
            try {
                data = await response.json();
            } catch (parseError) {
                console.warn('解析深度分析响应失败:', parseError);
            }
            
            if (!response.ok || !data || data.status !== 'success') {
                const message = data?.message || `深度分析任务启动失败 (HTTP ${response.status})`;
                throw new Error(message);
            }
            
            const taskInfo = data.data || {};
            const totalMatches = taskInfo.total_matches ?? 0;
            this.updateStatus(`深度分析任务已启动（${totalMatches} 场）`, 'info');
            sportteryToast('success', '深度分析已启动', `共 ${totalMatches} 场比赛进入深度分析队列`);
            
            const taskId = taskInfo.task_id || data.task_id;
            if (!taskId) {
                throw new Error('服务器未返回任务ID');
            }
            this.currentTaskId = taskId;
            this.showInterruptButton(true);
            this._startDeepAnalysisPolling(taskId);
        } catch (error) {
            console.error('深度分析启动失败:', error);
            const message = error?.message || '无法启动深度分析任务';
            sportteryToast('error', '深度分析失败', message);
            if (typeof window.showToast !== 'function') {
                alert(`深度分析失败：${message}`);
            }
            this.updateStatus(`深度分析失败：${message}`, 'danger');
            this._restoreDeepAnalysisButton();
        }
    }
    
    _resolveSelectedDateKey() {
        const state = this.state.getState();
        if (state.selectedDate) {
            return state.selectedDate;
        }
        if (Array.isArray(this._sortedDatesCache) && this._sortedDatesCache.length > 0) {
            return this._sortedDatesCache[0];
        }
        const matchDates = Object.keys(state.matchDateGroups || {}).sort();
        if (matchDates.length > 0) {
            return matchDates[matchDates.length - 1];
        }
        return null;
    }
    
    _resolveDeepAnalysisDate() {
        const key = this._resolveSelectedDateKey();
        if (key) {
            if (key.length === 5 && key.includes('-')) {
                const currentYear = new Date().getFullYear();
                return `${currentYear}-${key}`;
            }
            return key;
        }
        return new Date().toISOString().split('T')[0];
    }
    
    _startQuickPredictionPolling(taskId) {
        if (!taskId) {
            console.warn('未提供快速预测任务ID，无法轮询');
            return;
        }
        
        this._stopQuickPredictionPolling();
        this._quickPredictionPollingActive = true;
        
        const poll = async () => {
            if (!this._quickPredictionPollingActive) {
                return;
            }
            try {
                const response = await fetch(`/api/lottery/deep-analysis/status/${encodeURIComponent(taskId)}`);
                let data = null;
                try {
                    data = await response.json();
                } catch (parseError) {
                    console.warn('解析快速预测任务状态失败:', parseError);
                }
                
                if (response.status === 404 || (data && data.status === 'error')) {
                    this._handleQuickPredictionNotFound();
                    return;
                }
                
                if (data && data.status === 'success') {
                    this._handleQuickPredictionStatus(data.data);
                }
            } catch (error) {
                console.warn('快速预测任务状态轮询失败:', error);
            }
            
            if (this._quickPredictionPollingActive) {
                this._quickPredictionPollingTimer = setTimeout(poll, 3000);
            }
        };
        
        poll();
    }
    
    _stopQuickPredictionPolling() {
        this._quickPredictionPollingActive = false;
        if (this._quickPredictionPollingTimer) {
            clearTimeout(this._quickPredictionPollingTimer);
            this._quickPredictionPollingTimer = null;
        }
    }
    
    _handleQuickPredictionStatus(task) {
        if (!task) {
            console.warn('快速预测任务状态为空');
            return;
        }
        
        const total = task.total_matches ?? task.match_count ?? 0;
        const completed = task.completed_matches ?? task.success_count ?? 0;
        const stepDesc = this._describeTaskStep(task.current_step, task.current_match);
        
        if (['pending', 'running'].includes(task.status)) {
            const progressText = total ? `（${completed}/${total}）` : '';
            const stepText = stepDesc ? ` - ${stepDesc}` : '';
            this.updateStatus(`快速预测进行中${progressText}${stepText}`, 'info');
            return;
        }
        
        this._stopQuickPredictionPolling();
        this.showInterruptButton(false);
        this.currentTaskId = null;
        this._restoreQuickPredictionButton();
        
        if (task.status === 'completed') {
            const successCount = task.success_count ?? completed;
            const successText = total ? `${successCount}/${total}` : `${successCount}`;
            this.updateStatus(`快速预测完成，成功预测 ${successText} 场`, 'success');
            sportteryToast('success', '快速预测完成', `成功预测 ${successText} 场比赛`);
            this.refreshMatchesData();
        } else if (task.status === 'failed') {
            this.updateStatus('快速预测失败', 'danger');
            sportteryToast('error', '快速预测失败', task.error || '任务执行失败');
        } else if (task.status === 'interrupted') {
            this.updateStatus('快速预测已中断', 'warning');
            sportteryToast('warning', '快速预测已中断', task.error || '任务已被中断');
        } else {
            this.updateStatus(`快速预测状态：${task.status}`, 'info');
        }
    }
    
    _handleQuickPredictionNotFound() {
        console.warn('快速预测任务不存在或已过期');
        this._stopQuickPredictionPolling();
        this.showInterruptButton(false);
        this.currentTaskId = null;
        this._restoreQuickPredictionButton();
        this.updateStatus('快速预测任务不存在或已结束', 'warning');
    }
    
    _restoreQuickPredictionButton() {
        const button = document.getElementById('quick-prediction');
        if (button) {
            const defaultText = '<i class="bi bi-lightning"></i> 快速预测';
            const text = this._quickPredictionButtonState?.originalText || defaultText;
            button.disabled = false;
            button.innerHTML = text;
        }
        this._quickPredictionButtonState = null;
    }
    
    _startDeepAnalysisPolling(taskId) {
        if (!taskId) {
            console.warn('未提供深度分析任务ID，无法轮询');
            return;
        }
        
        this._stopDeepAnalysisPolling();
        this._deepAnalysisPollingActive = true;
        
        const poll = async () => {
            if (!this._deepAnalysisPollingActive) {
                return;
            }
            try {
                const response = await fetch(`/api/lottery/deep-analysis/status/${encodeURIComponent(taskId)}`);
                let data = null;
                try {
                    data = await response.json();
                } catch (parseError) {
                    console.warn('解析深度分析任务状态失败:', parseError);
                }
                
                if (response.status === 404 || (data && data.status === 'error')) {
                    this._handleDeepAnalysisNotFound();
                    return;
                }
                
                if (data && data.status === 'success') {
                    this._handleDeepAnalysisStatus(data.data);
                }
            } catch (error) {
                console.warn('深度分析任务状态轮询失败:', error);
            }
            
            if (this._deepAnalysisPollingActive) {
                this._deepAnalysisPollingTimer = setTimeout(poll, 3000);
            }
        };
        
        poll();
    }
    
    _stopDeepAnalysisPolling() {
        this._deepAnalysisPollingActive = false;
        if (this._deepAnalysisPollingTimer) {
            clearTimeout(this._deepAnalysisPollingTimer);
            this._deepAnalysisPollingTimer = null;
        }
    }
    
    _handleDeepAnalysisStatus(task) {
        if (!task) {
            console.warn('深度分析任务状态为空');
            return;
        }
        
        const total = task.total_matches ?? task.match_count ?? 0;
        const completed = task.completed_matches ?? 0;
        const stepDesc = this._describeTaskStep(task.current_step, task.current_match);
        
        if (['pending', 'running'].includes(task.status)) {
            const progressText = total ? `（${completed}/${total}）` : '';
            const stepText = stepDesc ? ` - ${stepDesc}` : '';
            this.updateStatus(`深度分析进行中${progressText}${stepText}`, 'info');
            return;
        }
        
        this._stopDeepAnalysisPolling();
        this.showInterruptButton(false);
        this.currentTaskId = null;
        this._restoreDeepAnalysisButton();
        
        if (task.status === 'completed') {
            let successCount = task.success_count ?? completed;
            let failedCount = task.failed_count ?? 0;
            if (Array.isArray(task.results)) {
                successCount = task.results.filter(r => r.status === 'success').length;
                failedCount = task.results.filter(r => r.status === 'failed').length;
            }
            const successText = total ? `${successCount}/${total}` : `${successCount}`;
            const failedText = failedCount > 0 ? `，失败 ${failedCount} 场` : '';
            this.updateStatus(`深度分析完成，成功生成 ${successText} 篇${failedText}`, 'success');
            sportteryToast('success', '深度分析完成', `成功生成 ${successText} 篇文章${failedText}`);
            this.refreshMatchesData();
        } else if (task.status === 'failed') {
            this.updateStatus('深度分析失败', 'danger');
            sportteryToast('error', '深度分析失败', task.error || '任务执行失败');
        } else if (task.status === 'interrupted') {
            this.updateStatus('深度分析已中断', 'warning');
            sportteryToast('warning', '深度分析已中断', task.error || '任务已被中断');
        } else {
            this.updateStatus(`深度分析状态：${task.status}`, 'info');
        }
    }
    
    _handleDeepAnalysisNotFound() {
        console.warn('深度分析任务不存在或已过期');
        this._stopDeepAnalysisPolling();
        this.showInterruptButton(false);
        this.currentTaskId = null;
        this._restoreDeepAnalysisButton();
        this.updateStatus('深度分析任务不存在或已结束', 'warning');
    }
    
    _restoreDeepAnalysisButton() {
        const button = document.getElementById('deep-analysis');
        if (button) {
            const defaultText = '<i class="bi bi-cpu"></i> 深度分析';
            const text = this._deepAnalysisButtonState?.originalText || defaultText;
            button.disabled = false;
            button.innerHTML = text;
        }
        this._deepAnalysisButtonState = null;
    }
    
    _describeTaskStep(step, currentMatch) {
        if (!step) {
            return '';
        }
        const matchLabel = currentMatch ? `：${currentMatch}` : '';
        switch (step) {
            case 'select':
                return `选择比赛${matchLabel}`;
            case 'collect':
                return `搜集资料${matchLabel}`;
            case 'generate':
                return `生成文章${matchLabel}`;
            case 'quick_predict':
                return `快速预测${matchLabel}`;
            default:
                return `${step}${matchLabel}`;
        }
    }
    
    async interruptCurrentTask() {
        if (!confirm('确定要中断所有正在执行的任务吗？')) {
            return;
        }
        
        try {
            const response = await fetch('/api/lottery/interrupt-all-tasks', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            let data = null;
            try {
                data = await response.json();
            } catch (parseError) {
                console.warn('解析中断任务响应失败:', parseError);
            }
            
            if (!response.ok || !data || data.status !== 'success') {
                const message = data?.message || `中断任务失败 (HTTP ${response.status})`;
                throw new Error(message);
            }
            
            this.updateStatus(data.message || '所有任务已中断', 'warning');
            sportteryToast('warning', '任务已中断', data.message || '所有运行中的任务已停止');
            
            this._stopQuickPredictionPolling();
            this._stopDeepAnalysisPolling();
            this.showInterruptButton(false);
            this.currentTaskId = null;
            this._restoreQuickPredictionButton();
            this._restoreDeepAnalysisButton();
        } catch (error) {
            console.error('中断任务失败:', error);
            sportteryToast('error', '中断失败', error.message || '无法中断当前任务');
        }
    }
    
    initializeTooltips() {
        // 初始化Bootstrap tooltips
        if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
            const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
            tooltipTriggerList.map(function (tooltipTriggerEl) {
                return new bootstrap.Tooltip(tooltipTriggerEl);
            });
        }
    }
    
    // ========== 其他兼容方法（占位，避免报错） ==========
    
    loadStats() {
        // 加载统计数据（暂不实现，保持接口兼容）
    }
    
    async refreshAccuracyStats() {
        // 防重复执行：如果正在执行，直接返回
        if (this._refreshingAccuracy) {
            console.log('命中率统计正在执行中，跳过重复调用');
            return;
        }
        
        // 标记为正在执行
        this._refreshingAccuracy = true;
        
        try {
            // 显示状态提示
            this.updateStatus('正在统计命中率...', 'warning');
            
            const response = await fetch('/api/lottery/accuracy/refresh', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({})
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                // 更新统计卡片显示
                this.updateStatsCard(data.data);
                
                // 显示成功状态
                const stats = data.data || {};
                const quickText = stats.quick_total > 0 
                    ? `快速预测 ${stats.quick_hits}/${stats.quick_total} (${(stats.quick_accuracy * 100).toFixed(1)}%)`
                    : '快速预测 暂无数据';
                const deepText = stats.deep_total > 0
                    ? `深度分析 ${stats.deep_hits}/${stats.deep_total} (${(stats.deep_accuracy * 100).toFixed(1)}%)`
                    : '深度分析 暂无数据';
                
                this.updateStatus(`命中率统计完成: ${quickText}, ${deepText}`, 'success');
                
                if (typeof sportteryToast === 'function') {
                    sportteryToast('success', '命中率已刷新', data.message || '统计数据已更新');
                }
            } else {
                this.updateStatus('命中率统计失败', 'danger');
                if (typeof sportteryToast === 'function') {
                    sportteryToast('error', '刷新失败', data.message || '未知错误');
                }
            }
        } catch (error) {
            console.error('刷新命中率失败:', error);
            this.updateStatus('命中率统计失败: 网络错误', 'danger');
            if (typeof sportteryToast === 'function') {
                sportteryToast('error', '网络错误', '无法连接到服务器');
            }
        } finally {
            // 清除执行标志
            this._refreshingAccuracy = false;
        }
    }
    
    updateStatsCard(stats) {
        const quickAccuracyEl = document.getElementById('quick-accuracy');
        const deepAccuracyEl = document.getElementById('deep-accuracy');
        
        if (quickAccuracyEl && stats.quick_accuracy !== undefined) {
            const percentage = (stats.quick_accuracy * 100).toFixed(1);
            quickAccuracyEl.textContent = `${percentage}%`;
        }
        
        if (deepAccuracyEl && stats.deep_accuracy !== undefined) {
            const percentage = (stats.deep_accuracy * 100).toFixed(1);
            deepAccuracyEl.textContent = `${percentage}%`;
        }
    }
    
    // 已移除编辑结果功能
    
    _clearQuickPredictionTimer(matchCode) {
        const timerId = this._quickPredictionTimers[matchCode];
        if (timerId) {
            clearTimeout(timerId);
            delete this._quickPredictionTimers[matchCode];
        }
    }

    _hasProcessingResult(matchCode, type) {
        const match = this.getMatchData(matchCode);
        if (!match) return false;
        if (type === 'quick') {
            return Array.isArray(match.scores) && match.scores.length > 0;
        }
        if (type === 'deep') {
            return match.source_type === 'deep' || match.prediction_type === 'deep';
        }
        return false;
    }

    _scheduleProcessingRefresh(matchCode, type, maxAttempts, intervalMs) {
        const attemptsLimit = typeof maxAttempts === 'number' ? maxAttempts : (type === 'deep' ? 18 : 5);
        const interval = typeof intervalMs === 'number' ? intervalMs : (type === 'deep' ? 10000 : 5000);
        let attempts = 0;
        const loop = async () => {
            attempts += 1;
            console.log(`预测任务自动刷新 (第${attempts}次): ${matchCode}, 类型: ${type}`);
            await this.refreshMatchesData();
            if (this._hasProcessingResult(matchCode, type)) {
                console.log('检测到预测结果，停止自动刷新:', matchCode);
                this._setMatchProcessing(matchCode, null);
                return;
            }
            if (attempts >= attemptsLimit) {
                console.log('预测未在预期时间内刷新到结果，停止自动刷新:', matchCode);
                this._setMatchProcessing(matchCode, null);
                return;
            }
            this._quickPredictionTimers[matchCode] = setTimeout(loop, interval);
        };

        this._clearQuickPredictionTimer(matchCode);
        this._quickPredictionTimers[matchCode] = setTimeout(loop, interval);
    }

    async quickPredictSingleMatch(matchCode) {
        console.log('快速预测开始:', matchCode);
        try {
            // 先检查状态
            console.log('检查预测状态:', matchCode);
            const statusResponse = await fetch(`/api/lottery/match/${matchCode}/prediction-status`);
            const statusData = await statusResponse.json();
            console.log('状态检查结果:', statusData);
            
            if (statusData.status !== 'success') {
                sportteryToast('error', '检查失败', statusData.message || (statusResponse.status + ' ' + statusResponse.statusText));
                return;
            }
            
            const { is_within_window, has_deep_analysis, can_quick_predict, queue_status } = statusData.data;
            
            // 检查时间窗口
            if (!is_within_window) {
                alert('仅支持预测未来12小时内的比赛，且比赛未开始');
                return;
            }
            
            // 检查是否已有深度分析
            if (has_deep_analysis) {
                alert('该比赛已有深度分析，不允许进行快速预测');
                return;
            }
            
            // 检查队列状态
            if (!can_quick_predict) {
                const current = queue_status.quick_prediction.current;
                const max = queue_status.quick_prediction.max;
                alert(`当前有 ${current} 场快速预测正在处理，最多支持 ${max} 场并发，请稍后重试`);
                return;
            }
            
            // 调用API
            console.log('调用快速预测API:', matchCode);
            this._setMatchProcessing(matchCode, 'quick');
            const response = await fetch(`/api/lottery/match/${matchCode}/quick-predict`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            console.log('API响应状态:', response.status, response.statusText);
            const data = await response.json();
            console.log('API响应数据:', data);
            
            if (data.status === 'success') {
                console.log('快速预测任务启动成功');
                sportteryToast('success', '任务已启动', `快速预测任务已启动: ${matchCode}，预计需要10-30秒完成`);
                // 先刷新一次并检测结果
                await this.refreshMatchesData();
                if (!this._hasProcessingResult(matchCode, 'quick')) {
                    this._scheduleProcessingRefresh(matchCode, 'quick');
                } else {
                    console.log('快速预测结果已立即刷新，无需轮询:', matchCode);
                    this._setMatchProcessing(matchCode, null);
                }
            } else {
                console.error('快速预测启动失败:', data);
                this._clearQuickPredictionTimer(matchCode);
                this._setMatchProcessing(matchCode, null);
                sportteryToast('error', '启动失败', data.message || '快速预测任务启动失败');
            }
        } catch (error) {
            console.error('快速预测异常:', error);
            this._clearQuickPredictionTimer(matchCode);
            this._setMatchProcessing(matchCode, null);
            sportteryToast('error', '网络错误', `无法连接到服务器: ${error.message}`);
        }
    }
    
    async deepAnalysisSingleMatch(matchCode) {
        try {
            // 先检查状态
            const statusResponse = await fetch(`/api/lottery/match/${matchCode}/prediction-status`);
            const statusData = await statusResponse.json();
            
            if (statusData.status !== 'success') {
                sportteryToast('error', '检查失败', statusData.message || '无法检查预测状态');
                return;
            }
            
            const { is_within_window, has_deep_analysis, can_deep_analysis, queue_status } = statusData.data;
            
            // 检查时间窗口
            if (!is_within_window) {
                alert('仅支持预测未来12小时内的比赛，且比赛未开始');
                return;
            }
            
            // 检查是否已有深度分析
            if (has_deep_analysis) {
                alert('该比赛已有深度分析，不允许重复生成');
                return;
            }
            
            // 检查队列状态
            if (!can_deep_analysis) {
                const current = queue_status.deep_analysis.current;
                const max = queue_status.deep_analysis.max;
                alert(`当前有 ${current} 场深度分析正在处理，最多支持 ${max} 场并发，请稍后重试`);
                return;
            }
            
            // 调用API
            this._setMatchProcessing(matchCode, 'deep');
            const response = await fetch(`/api/lottery/match/${matchCode}/deep-analysis`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                sportteryToast('success', '任务已启动', `深度分析任务已启动: ${matchCode}`);
                // 延迟刷新数据
                setTimeout(() => {
                    this.refreshMatchesData();
                }, 5000);
                this._scheduleProcessingRefresh(matchCode, 'deep', 24, 10000);
            } else {
                this._setMatchProcessing(matchCode, null);
                sportteryToast('error', '启动失败', data.message || '深度分析任务启动失败');
            }
        } catch (error) {
            console.error('深度分析失败:', error);
            this._setMatchProcessing(matchCode, null);
            sportteryToast('error', '网络错误', error.message);
        }
    }
    
    async viewArticleInWorkbench(matchCode) {
        if (!matchCode) {
            console.warn('viewArticleInWorkbench 缺少 matchCode');
            return;
        }
        
        try {
            sportteryToast('info', '加载文章', `正在加载 ${matchCode} 的深度分析文章...`);
            
            const response = await fetch(`/api/lottery/article/${encodeURIComponent(matchCode)}`);
            if (!response.ok) {
                const message = `服务器返回 ${response.status}`;
                sportteryToast('error', '加载失败', message);
                console.error('获取文章失败:', message);
                return;
            }
            
            const result = await response.json();
            if (result.status !== 'success' || !result.data) {
                const reason = result.message || '文章数据为空';
                sportteryToast('error', '加载失败', reason);
                console.warn('获取文章失败:', reason);
                return;
            }
            
            await this._openWorkbenchPanel();
            await this._applyArticleToWorkbench(result.data, matchCode);
        } catch (error) {
            console.error('加载文章异常:', error);
            sportteryToast('error', '加载失败', error.message || '无法加载文章');
        }
    }
    
    minimizeQuickProgressPanel() {
        // 最小化快速预测进度面板（暂不实现，保持接口兼容）
        console.log('minimizeQuickProgressPanel');
    }
    
    approveAnalysis(matchCode) {
        // 审核通过（暂不实现，保持接口兼容）
        console.log('approveAnalysis:', matchCode);
    }
    
    saveMatchResult(matchCode, button) {
        // 保存比赛结果（暂不实现，保持接口兼容）
        console.log('saveMatchResult:', matchCode, button);
    }
    
    async _openWorkbenchPanel() {
        const workbenchNav = document.querySelector('.nav-item[data-target="editor-panel"]');
        if (workbenchNav && !workbenchNav.classList.contains('active')) {
            workbenchNav.click();
            await this._waitFor(400);
        } else if (!workbenchNav) {
            this._switchToPanel('editor-panel');
            await this._waitFor(200);
        }
        
        await this._ensureMarkdownEditor();
    }
    
    async _applyArticleToWorkbench(articleData, matchCode) {
        const content = (articleData && (articleData.article_content || articleData.content)) || '';
        const metadata = (articleData && articleData.article_metadata) || {};
        
        const applyContent = () => {
            if (window.markdownEditor && typeof window.markdownEditor.setValue === 'function') {
                window.markdownEditor.setValue(content);
            } else {
                const editorElement = document.getElementById('markdown-editor');
                if (editorElement) {
                    editorElement.value = content;
                    editorElement.dispatchEvent(new Event('input', { bubbles: true }));
                }
            }
        };
        
        applyContent();
        // 再次尝试，确保编辑器在异步初始化后也能写入
        if (!window.markdownEditor) {
            await this._waitFor(200);
            applyContent();
        }
        
        this._currentWorkbenchArticle = {
            matchCode,
            metadata,
            articleStatus: articleData?.article_status,
            statusHistory: articleData?.status_history || []
        };
        
        const matchInfo = metadata?.match_info || {};
        const label = matchInfo.match_display || matchInfo.match_code || matchCode;
        sportteryToast('success', '文章已加载', `${label || matchCode} 深度分析文章已加载到工作台`);
    }
    
    _switchToPanel(panelId) {
        const navItems = document.querySelectorAll('.nav-item[data-target]');
        const panels = document.querySelectorAll('.content-panel');
        
        navItems.forEach(item => {
            const isTarget = item.dataset.target === panelId;
            item.classList.toggle('active', isTarget);
        });
        
        panels.forEach(panel => {
            const isTarget = panel.id === panelId;
            panel.classList.toggle('active', isTarget);
        });
    }
    
    async _ensureMarkdownEditor() {
        if (window.markdownEditor) {
            return;
        }
        
        if (typeof window.initMarkdownEditor === 'function') {
            try {
                window.initMarkdownEditor();
            } catch (error) {
                console.warn('initMarkdownEditor 调用失败:', error);
            }
        }
        
        await this._waitFor(300);
    }
    
    _waitFor(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    // 其他方法可以按需添加...
}

