/**
 * SportteryRenderer.js - 竞彩数据渲染服务
 * 负责所有UI渲染逻辑，纯渲染功能，不管理数据
 */
class SportteryRenderer {
    constructor(manager) {
        // 保存manager引用，用于调用回调函数
        this.manager = manager;
    }
    
    /**
     * 渲染合并表格（包含赛程和赛果）
     * @param {Array} allMatches - 所有比赛数据（包含is_completed字段）
     */
    renderMergedTable(allMatches) {
        if (!allMatches || allMatches.length === 0) {
            this.renderEmptyMatches();
            return;
        }
        
        // 按日期分组
        const groupedMatches = this._groupMatchesByDate(allMatches);
        // 倒序排序（最新的日期在前）
        const sortedDates = Object.keys(groupedMatches).sort().reverse();
        
        // 显示日期导航栏（支持横向滚动，默认显示最多10个）
        this.renderDateNavbar(sortedDates);
        
        // 清空内容容器（延迟加载前）
        const contentContainer = document.getElementById('sporttery-matches-content');
        if (contentContainer) {
            contentContainer.innerHTML = '';
        }
        
        // 不一次性渲染所有日期内容，只保存分组数据供延迟加载使用
        this._saveGroupedMatchesForLazyLoad(groupedMatches, sortedDates);
        
        // 默认显示逻辑由Manager控制，避免覆盖用户选择
    }
    
    // renderMergedDateContents 方法已移除，改为延迟加载（renderSingleDateContent）
    
    /**
     * 渲染赛程表格
     * @param {Array} matches - 比赛数据数组
     */
    renderMatchesTable(matches) {
        if (!matches || matches.length === 0) {
            this.renderEmptyMatches();
            return;
        }
        
        // 使用状态管理器中的日期分组（如果可用）
        // 否则使用工具函数分组
        const groupedMatches = this._groupMatchesByDate(matches);
        // 倒序排序（最新的日期在前）
        const sortedDates = Object.keys(groupedMatches).sort().reverse();
        
        // 显示日期导航栏（支持横向滚动）
        this.renderDateNavbar(sortedDates);
        
        // 清空内容容器（延迟加载前）
        const contentContainer = document.getElementById('sporttery-matches-content');
        if (contentContainer) {
            contentContainer.innerHTML = '';
        }
        
        // 不一次性渲染所有日期内容，只保存分组数据供延迟加载使用
        this._saveGroupedMatchesForLazyLoad(groupedMatches, sortedDates);
        
        // 默认显示逻辑由Manager控制
    }
    
    /**
     * 渲染赛果表格
     * @param {Array} results - 赛果数据数组
     */
    renderResultsTable(results) {
        const tbody = document.getElementById('sporttery-results-tbody');
        
        if (!tbody) {
            console.warn('sporttery-results-tbody元素未找到');
            return;
        }
        
        if (!results || results.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center text-muted py-4">
                        <i class="bi bi-info-circle"></i> 暂无赛果数据
                    </td>
                </tr>
            `;
            return;
        }
        
        // 按比赛编号排序（正序：001在上，015在下）
        const sortedResults = [...results].sort((a, b) => {
            const numA = SportteryUtils.extractMatchNumber(a.match_code);
            const numB = SportteryUtils.extractMatchNumber(b.match_code);
            return numA - numB;
        });
        
        // 显示排序后的比赛
        const html = sortedResults.map(result => {
            const predictedScore = result.predicted_score || '--';
            const actualScore = result.actual_score || '--';
            const isHit = result.is_hit;
            const hitStatus = isHit ? '命中' : (actualScore !== '--' ? '未命中' : '待确认');
            const hitClass = isHit ? 'bg-success' : (actualScore !== '--' ? 'bg-danger' : 'bg-secondary');
            
            return `
                <tr>
                    <td><span class="badge bg-primary">${result.match_code}</span></td>
                    <td>${result.league || result.league_display || '未知联赛'}</td>
                    <td>
                        <strong>${result.home_team}</strong> vs <strong>${result.away_team}</strong>
                    </td>
                    <td>
                        <span class="badge bg-warning">${predictedScore}</span>
                    </td>
                    <td>
                        <span class="badge bg-info">${actualScore}</span>
                    </td>
                    <td>
                        <span class="badge ${hitClass}">${hitStatus}</span>
                    </td>
                    <td>${SportteryUtils.formatTime(result.match_time || result.time_display)}</td>
                </tr>
            `;
        }).join('');
        
        tbody.innerHTML = html;
    }
    
    /**
     * 渲染赛果日期导航栏（使用状态中的dateGroups）
     * @param {Object} dateGroups - 日期分组对象（从状态中获取）
     */
    renderResultsDateNavbar(dateGroups) {
        const navbar = document.getElementById('results-date-navbar');
        if (!navbar) {
            console.warn('results-date-navbar元素未找到');
            return;
        }
        
        const navbarContainer = navbar.querySelector('.d-flex');
        if (!navbarContainer) {
            console.warn('results-date-navbar .d-flex元素未找到');
            return;
        }
        
        if (!dateGroups || Object.keys(dateGroups).length === 0) {
            navbar.style.display = 'none';
            return;
        }
        
        // 转换为显示项
        const displayItems = [];
        Object.keys(dateGroups).forEach(dateKey => {
            const matches = dateGroups[dateKey];
            if (matches && matches.length > 0) {
                displayItems.push({
                    dateKey: dateKey,
                    displayDate: dateKey,
                    matches: matches
                });
            }
        });
        
        // 按日期倒序排列（最新的在前）
        displayItems.sort((a, b) => {
            return b.dateKey.localeCompare(a.dateKey);
        });
        
        if (displayItems.length <= 1) {
            navbar.style.display = 'none';
            return;
        }
        
        navbar.style.display = 'block';
        navbarContainer.innerHTML = displayItems.map(item => `
            <button class="date-nav-item" onclick="sportteryManager.showResultsDateContent('${item.dateKey}')" data-date="${item.dateKey}">
                ${item.displayDate}
            </button>
        `).join('');
    }
    
    /**
     * 显示指定日期的赛果内容（使用状态中的dateGroups）
     * @param {string} dateKey - 日期键（如："11-04"）
     * @param {Object} dateGroups - 日期分组对象（从状态中获取）
     */
    showResultsDateContent(dateKey, dateGroups) {
        console.log('显示赛果日期内容:', dateKey, 'dateGroups:', dateGroups);
        
        // 更新导航栏活动状态
        const navbar = document.getElementById('results-date-navbar');
        if (navbar) {
            const buttons = navbar.querySelectorAll('.date-nav-item');
            buttons.forEach(btn => {
                btn.classList.remove('active');
                if (btn.getAttribute('data-date') === dateKey) {
                    btn.classList.add('active');
                }
            });
        }
        
        // 从dateGroups中获取该日期的数据
        const filteredResults = dateGroups[dateKey] || [];
        console.log('过滤后的数据:', filteredResults.length, '条');
        
        if (filteredResults.length === 0) {
            console.warn('该日期没有数据，dateKey:', dateKey);
        }
        
        this.renderResultsTable(filteredResults);
    }
    
    /**
     * 渲染赛程日期导航栏
     * @param {Array<string>} sortedDates - 排序后的日期数组
     */
    renderDateNavbar(sortedDates) {
        const navbar = document.getElementById('date-navbar');
        if (!navbar) return;
        
        const navbarContainer = navbar.querySelector('.d-flex');
        if (!navbarContainer) return;
        
        // 始终展示导航栏，避免只有一个分组时被隐藏造成误解
        navbar.style.display = 'block';
        
        // 优化样式：支持横向滚动和鼠标拖动
        navbarContainer.style.cssText = `
            overflow-x: auto !important;
            overflow-y: hidden !important;
            scrollbar-width: thin;
            -webkit-overflow-scrolling: touch;
            white-space: nowrap;
            display: flex !important;
            flex-wrap: nowrap !important;
            cursor: grab;
            user-select: none;
        `.replace(/\s+/g, ' ').trim();
        
        // 添加鼠标拖动滚动支持
        let isDown = false;
        let startX;
        let scrollLeft;
        
        navbarContainer.addEventListener('mousedown', (e) => {
            isDown = true;
            navbarContainer.style.cursor = 'grabbing';
            startX = e.pageX - navbarContainer.offsetLeft;
            scrollLeft = navbarContainer.scrollLeft;
        });
        
        navbarContainer.addEventListener('mouseleave', () => {
            isDown = false;
            navbarContainer.style.cursor = 'grab';
        });
        
        navbarContainer.addEventListener('mouseup', () => {
            isDown = false;
            navbarContainer.style.cursor = 'grab';
        });
        
        navbarContainer.addEventListener('mousemove', (e) => {
            if (!isDown) return;
            e.preventDefault();
            const x = e.pageX - navbarContainer.offsetLeft;
            const walk = (x - startX) * 2; // 滚动速度
            navbarContainer.scrollLeft = scrollLeft - walk;
        });
        
        // 渲染所有日期按钮（支持横向滚动查看）
        navbarContainer.innerHTML = sortedDates.map((date, index) => {
            return `
                <button class="date-nav-item" 
                        onclick="sportteryManager.showDateContent('${date}')" 
                        data-date="${date}"
                        style="flex-shrink: 0; min-width: 60px; margin-right: 4px; white-space: nowrap; pointer-events: auto;">
                    ${date}
                </button>
            `;
        }).join('');
        
        // 确保第一个日期（最新的）可见并激活
        if (sortedDates.length > 0) {
            setTimeout(() => {
                const firstButton = navbarContainer.querySelector(`[data-date="${sortedDates[0]}"]`);
                if (firstButton) {
                    navbarContainer.scrollLeft = 0;
                }
            }, 100);
        }
    }
    
    /**
     * 渲染空赛程提示
     */
    renderEmptyMatches() {
        const contentContainer = document.getElementById('sporttery-matches-content');
        const navbar = document.getElementById('date-navbar');
        
        if (navbar) navbar.style.display = 'none';
        
        if (contentContainer) {
            contentContainer.innerHTML = `
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead class="table-light">
                            <tr>
                                <th>比赛编号</th>
                                <th>联赛</th>
                                <th class="text-center">对阵</th>
                                <th>比赛时间</th>
                                <th>状态</th>
                                <th>操作</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td colspan="6" class="text-center text-muted py-4">
                                    <i class="bi bi-info-circle"></i> 暂无比赛数据
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            `;
        }
    }
    
    /**
     * 保存分组数据供延迟加载使用
     * @private
     */
    _saveGroupedMatchesForLazyLoad(groupedMatches, sortedDates) {
        // 保存到manager实例中，供延迟加载使用
        if (this.manager) {
            this.manager._groupedMatchesCache = groupedMatches;
            this.manager._sortedDatesCache = sortedDates;
        }
    }
    
    /**
     * 渲染单个日期的内容（延迟加载）
     * @param {string} date - 日期键
     * @param {Array} matches - 该日期的比赛数据
     */
    renderSingleDateContent(date, matches) {
        const contentContainer = document.getElementById('sporttery-matches-content');
        if (!contentContainer) return;
        
        // 检查是否已存在该日期的内容
        let dateContent = document.getElementById(`date-content-${date}`);
        
        if (!dateContent) {
            // 创建新的日期内容区域
            dateContent = document.createElement('div');
            dateContent.className = 'date-content';
            dateContent.id = `date-content-${date}`;
            dateContent.style.display = 'none'; // 默认隐藏
            contentContainer.appendChild(dateContent);
        }
        
        // 如果内容已渲染且存在，直接显示
        if (dateContent.innerHTML.trim() && matches) {
            return;
        }
        
        // 渲染该日期的内容
        dateContent.innerHTML = this._generateDateContentHTML(matches);
    }
    
    /**
     * 生成单个日期的表格HTML
     * @private
     */
    _generateDateContentHTML(matches) {
        if (!matches || matches.length === 0) {
            return `
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead class="table-light">
                            <tr>
                                <th>比赛编号</th>
                                <th>联赛</th>
                                <th class="text-center">对阵</th>
                                <th>开赛时间</th>
                                <th>预测结果</th>
                                <th>实际比分</th>
                                <th>命中状态</th>
                                <th>预测类型</th>
                                <th>操作</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td colspan="9" class="text-center text-muted py-4">
                                    <i class="bi bi-info-circle"></i> 该日期暂无比赛数据
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            `;
        }
        
        return `
            <div class="table-responsive">
                <table class="table table-hover sporttery-matches-table">
                    <thead class="table-light">
                        <tr>
                            <th>比赛编号</th>
                            <th class="league-header">联赛</th>
                            <th class="text-center">对阵</th>
                            <th>开赛时间</th>
                            <th>预测结果</th>
                            <th>实际比分</th>
                            <th>命中状态</th>
                            <th>预测类型</th>
                            <th>操作</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${matches.map(match => {
                            const isCompleted = match.is_completed || false;
                            const isDeepAnalysis = match.source_type === 'deep';
                            const scores = match.scores || [];
                            const formattedScores = scores.map(score => {
                                if (typeof score === 'string') {
                                    return score.replace(':', '-');
                                }
                                return score;
                            });
                            const scoresText = formattedScores.length > 0 ? formattedScores.join(',') : '暂无预测';
                            const actualScore = match.actual_score || '';
                            const actualScoreDisplay = actualScore ? `<strong class="text-danger">${actualScore}</strong>` : '<span class="text-muted">未录入</span>';
                            const timeDisplay = match.time_display || match.match_time || '';
                            const escapeAttr = (value) => {
                                if (!value) return '';
                                return String(value)
                                    .replace(/&/g, '&amp;')
                                    .replace(/"/g, '&quot;')
                                    .replace(/</g, '&lt;')
                                    .replace(/>/g, '&gt;');
                            };
                            
                            // 判断比赛是否正在进行中（开赛时间 <= 当前时间 < 开赛时间 + 2小时）
                            const matchTime = match.match_time || match.time_display || '';
                            const isInProgress = SportteryUtils.isMatchInProgress(matchTime);
                            const timeDisplayClass = isInProgress ? 'match-time-in-progress' : '';
                            
                            // 命中状态（仅显示赛果状态，不显示比赛状态）
                            const isHit = match.is_hit || false;
                            const hitStatus = isCompleted ? (isHit ? '命中' : (actualScore ? '未命中' : '待确认')) : '--';
                            const hitClass = isCompleted ? (isHit ? 'bg-success' : (actualScore ? 'bg-danger' : 'bg-secondary')) : 'bg-light text-muted';
                            
                            // 行样式：已结束的比赛用不同颜色
                            const rowClass = isCompleted ? 'table-secondary' : (isDeepAnalysis ? 'table-warning' : '');
                            
                            return `
                                <tr class="${rowClass}">
                                    <td><span class="badge bg-primary">${match.match_code}</span></td>
                                    <td class="league-cell">${match.league_display || match.league || ''}</td>
                                    <td class="matchup-cell">
                                        <span class="team-name home-team" title="${match.home_team || ''}">${match.home_team || ''}</span>
                                        <span class="vs-divider">vs</span>
                                        <span class="team-name away-team" title="${match.away_team || ''}">${match.away_team || ''}</span>
                                    </td>
                                    <td class="${timeDisplayClass}">${timeDisplay}</td>
                                    <td>
                                        <div class="prediction-info">
                                            <div class="prediction-scores">${scoresText}</div>
                                            ${(() => {
                                                const reasonText = match.reason ? String(match.reason).trim() : '';
                                                if (!reasonText) {
                                                    return '';
                                                }
                                                const iconClass = isDeepAnalysis ? 'bi-journal-text text-warning' : 'bi-info-circle text-muted';
                                                return `<div class="reason-tooltip" data-bs-toggle="tooltip" data-bs-placement="top" title="${escapeAttr(reasonText)}">
                                                            <i class="bi ${iconClass}"></i>
                                                        </div>`;
                                            })()}
                                        </div>
                                    </td>
                                    <td>${actualScoreDisplay}</td>
                                    <td>
                                        <span class="badge ${hitClass}">${hitStatus}</span>
                                    </td>
                                    <td>
                                        ${(() => {
                                            // 统一“预测类型”显示逻辑
                                            if (scores.length > 0) {
                                                const baseClass = isDeepAnalysis ? 'bg-warning text-dark' : 'bg-info text-white';
                                                const iconClass = isDeepAnalysis ? 'bi-journal-text' : 'bi-lightning';
                                                const label = isDeepAnalysis ? '深度分析' : '快速预测';
                                                const classes = [
                                                    'badge',
                                                    baseClass,
                                                    isDeepAnalysis ? 'badge-action' : ''
                                                ].filter(Boolean).join(' ');
                                                // 修复：深度分析标签无论比赛是否完成都可以点击查看文章
                                                const attrs = isDeepAnalysis
                                                    ? `onclick="sportteryManager.viewArticleInWorkbench('${escapeAttr(match.match_code || '')}')" title="点击查看文章" style="cursor: pointer;"`
                                                    : '';
                                                return `<span class="${classes}" ${attrs}><i class="bi ${iconClass}"></i> ${label}</span>`;
                                            }

                                            // 无任何预测：统一展示等待徽章
                                            return `<span class="badge bg-secondary"><i class="bi bi-hourglass-split"></i> 等待分析</span>`;
                                        })()}
                                    </td>
                                    <td>
                                        <div class="d-flex gap-1 predict-action-wrapper" data-match-code="${match.match_code}">
                                            ${this._renderPredictAction(match)}
                                        </div>
                                    </td>
                                </tr>
                            `;
                        }).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }

    _renderPredictAction(match) {
        if (!match) {
            return '';
        }
        const processingType = this.manager ? this.manager.getMatchProcessingType(match.match_code) : null;
        if (processingType) {
            const text = processingType === 'deep' ? '深度分析中...' : '快速预测中...';
            return `
                <div class="d-flex align-items-center text-primary">
                    <div class="spinner-border spinner-border-sm me-2" role="status"></div>
                    <span>${text}</span>
                </div>
            `;
        }

        const isCompleted = match.is_completed || false;
        const isDeepAnalysis = match.source_type === 'deep';
        const scores = match.scores || [];
        const matchTime = match.match_time || match.time_display || '';
        const isInProgress = SportteryUtils.isMatchInProgress(matchTime);
        const canTrigger = (() => {
            try {
                const mt = new Date(match.match_time || match.time_display || '');
                if (isNaN(mt.getTime())) return false;
                const diffH = (mt.getTime() - Date.now()) / 3600000;
                return diffH > 0 && diffH <= 12;
            } catch (e) { return false; }
        })();

        if (!isCompleted && !isDeepAnalysis && scores.length === 0 && canTrigger) {
            return `
                <select class="form-select form-select-sm predict-action-select" data-match-code="${match.match_code}" style="width: 120px;">
                    <option value="">重新预测</option>
                    <option value="quick">快速预测</option>
                    <option value="deep">深度分析</option>
                </select>
            `;
        }

        const disabledReason = isCompleted ? '比赛已结束' : (isDeepAnalysis ? '已生成深度分析' : (!canTrigger ? '超过12小时窗口' : '当前不可重新预测'));
        return `
            <select class="form-select form-select-sm" style="width: 120px;" disabled title="${disabledReason}">
                <option>重新预测</option>
            </select>
        `;
    }

    updatePredictAction(matchCode) {
        const wrapper = document.querySelector(`.predict-action-wrapper[data-match-code="${matchCode}"]`);
        if (!wrapper) return;
        const match = this.manager ? this.manager.getMatchData(matchCode) : null;
        wrapper.innerHTML = this._renderPredictAction(match);
    }
    
    /**
     * 显示指定日期的赛程内容（延迟加载）
     * @param {string} date - 日期键
     */
    showDateContent(date) {
        // 隐藏所有日期内容
        document.querySelectorAll('.date-content').forEach(content => {
            content.style.display = 'none';
            content.classList.remove('active');
        });
        
        // 获取该日期的数据（延迟加载）
        let targetContent = document.getElementById(`date-content-${date}`);
        let matches = null;
        
        // 从缓存中获取该日期的比赛数据
        if (this.manager && this.manager._groupedMatchesCache) {
            matches = this.manager._groupedMatchesCache[date];
        }
        
        // 如果内容不存在，延迟加载渲染
        if (!targetContent || !targetContent.innerHTML.trim()) {
            if (matches) {
                this.renderSingleDateContent(date, matches);
                targetContent = document.getElementById(`date-content-${date}`);
            } else {
                // 如果没有数据，显示空状态
                const contentContainer = document.getElementById('sporttery-matches-content');
                if (contentContainer) {
                    contentContainer.innerHTML = `
                        <div class="text-center text-muted py-4">
                            <i class="bi bi-info-circle"></i> 该日期暂无比赛数据
                        </div>
                    `;
                }
                return;
            }
        }
        
        // 显示选中的日期内容
        if (targetContent) {
            targetContent.style.display = 'block';
            targetContent.classList.add('active');
        }
        
        // 更新导航栏活动状态
        document.querySelectorAll('.date-nav-item').forEach(item => {
            item.classList.remove('active');
        });
        
        const activeNav = document.querySelector(`[data-date="${date}"]`);
        if (activeNav) {
            activeNav.classList.add('active');
            // 仅调整横向滚动，避免拖动页面到顶部
            const navbarContainer = document.querySelector('#date-navbar .d-flex');
            if (navbarContainer) {
                const navRect = activeNav.getBoundingClientRect();
                const containerRect = navbarContainer.getBoundingClientRect();
                if (navRect.left < containerRect.left) {
                    navbarContainer.scrollLeft -= (containerRect.left - navRect.left);
                } else if (navRect.right > containerRect.right) {
                    navbarContainer.scrollLeft += (navRect.right - containerRect.right);
                }
            }
        }
    }
    
    /**
     * 按日期分组比赛数据（辅助方法）
     * @private
     */
    _groupMatchesByDate(matches) {
        const grouped = {};
        matches.forEach(match => {
            // 统一使用extractMatchDateKey提取日期键（所有数据都应有group_date字段）
            const dateKey = SportteryUtils.extractMatchDateKey(match);
            
            // 只处理有下注时间（group_date）的比赛，忽略没有下注时间的比赛
            if (dateKey) {
                if (!grouped[dateKey]) {
                    grouped[dateKey] = [];
                }
                grouped[dateKey].push(match);
            } else {
                // 如果没有下注时间，记录警告但不添加到分组中
                console.warn(`比赛 ${match.match_code} 没有下注时间（group_date），已跳过分组`);
            }
        });
        return grouped;
    }
}

