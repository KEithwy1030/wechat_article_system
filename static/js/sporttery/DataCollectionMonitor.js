/**
 * DataCollectionMonitor.js - 数据搜集状态监控管理器
 * 负责监控和管理数据搜集状态
 */
class DataCollectionMonitor {
    constructor() {
        this.statusData = null;
        this.refreshInterval = null;
    }
    
    async loadStatus() {
        try {
            const response = await fetch('/api/data-collection/status');
            const result = await response.json();
            
            if (result.success) {
                this.statusData = result.data;
                this.renderStatus();
            } else {
                if (window.showToast) {
                    window.showToast('error', '加载失败', result.message);
                }
            }
        } catch (error) {
            console.error('加载数据搜集状态失败:', error);
            if (window.showToast) {
                window.showToast('error', '加载失败', '无法连接到服务器');
            }
        }
    }
    
    renderStatus() {
        if (!this.statusData) return;
        
        // 更新状态概览
        this.updateStatusOverview();
        
        // 更新数据源状态
        this.updateDataSourcesStatus();
        
        // 更新搜集计划
        this.updateCollectionSchedule();
        
        // 更新即将进行的比赛
        this.updateUpcomingMatches();
    }
    
    updateStatusOverview() {
        const status = this.statusData.status;
        
        // 当前状态
        const statusBadge = document.getElementById('collection-status-badge');
        if (statusBadge) {
            if (status.is_running) {
                statusBadge.textContent = '运行中';
                statusBadge.className = 'h4 mb-1 text-success';
            } else {
                statusBadge.textContent = '待机中';
                statusBadge.className = 'h4 mb-1 text-muted';
            }
        }
        
        // 搜集进度
        const progress = document.getElementById('collection-progress');
        if (progress) {
            progress.textContent = `${status.progress}%`;
        }
        
        // 数据源数量
        const sourcesCount = document.getElementById('data-sources-count');
        if (sourcesCount) {
            sourcesCount.textContent = Object.keys(this.statusData.data_sources).length;
        }
        
        // 最后搜集时间
        const lastTime = document.getElementById('last-collection-time');
        if (lastTime && status.last_update) {
            const time = new Date(status.last_update);
            lastTime.textContent = time.toLocaleTimeString('zh-CN', { 
                hour: '2-digit', 
                minute: '2-digit' 
            });
        }
    }
    
    updateDataSourcesStatus() {
        const container = document.getElementById('data-sources-status');
        if (!container) return;
        
        const sources = this.statusData.data_sources;
        container.innerHTML = '';
        
        Object.entries(sources).forEach(([key, source]) => {
            const statusClass = this.getStatusClass(source.status);
            const statusText = this.getStatusText(source.status);
            
            const sourceCard = document.createElement('div');
            sourceCard.className = 'col-md-4 mb-2';
            sourceCard.innerHTML = `
                <div class="card">
                    <div class="card-body p-2">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <h6 class="mb-1">${source.name}</h6>
                                <small class="text-muted">成功: ${source.success_count} | 失败: ${source.error_count}</small>
                            </div>
                            <span class="badge ${statusClass}">${statusText}</span>
                        </div>
                    </div>
                </div>
            `;
            container.appendChild(sourceCard);
        });
    }
    
    updateCollectionSchedule() {
        const tbody = document.getElementById('collection-schedule-table');
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        this.statusData.schedule.forEach(schedule => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${schedule.name}</td>
                <td>${schedule.trigger_time}</td>
                <td>${schedule.data_sources.join(', ')}</td>
                <td>${schedule.target_matches}</td>
                <td>
                    <span class="badge ${schedule.enabled ? 'bg-success' : 'bg-secondary'}">
                        ${schedule.enabled ? '启用' : '禁用'}
                    </span>
                </td>
                <td>${schedule.next_run}</td>
            `;
            tbody.appendChild(row);
        });
    }
    
    async updateUpcomingMatches() {
        try {
            const response = await fetch('/api/data-collection/upcoming-matches');
            const result = await response.json();
            
            if (result.success) {
                const tbody = document.getElementById('upcoming-matches-table');
                if (!tbody) return;
                
                tbody.innerHTML = '';
                
                result.data.forEach(match => {
                    const priorityClass = this.getPriorityClass(match.priority);
                    const collectedStatus = match.data_collected ? 
                        '<span class="badge bg-success">已搜集</span>' : 
                        '<span class="badge bg-warning">待搜集</span>';
                    
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${match.home_team} vs ${match.away_team}</td>
                        <td>${match.match_time}</td>
                        <td>${match.league}</td>
                        <td><span class="badge ${priorityClass}">${match.priority}</span></td>
                        <td>${collectedStatus}</td>
                    `;
                    tbody.appendChild(row);
                });
            }
        } catch (error) {
            console.error('加载即将进行的比赛失败:', error);
        }
    }
    
    getStatusClass(status) {
        switch (status) {
            case 'running': return 'bg-primary';
            case 'success': return 'bg-success';
            case 'error': return 'bg-danger';
            default: return 'bg-secondary';
        }
    }
    
    getStatusText(status) {
        switch (status) {
            case 'running': return '运行中';
            case 'success': return '正常';
            case 'error': return '错误';
            default: return '待机';
        }
    }
    
    getPriorityClass(priority) {
        switch (priority) {
            case 'high': return 'bg-danger';
            case 'medium': return 'bg-warning';
            case 'low': return 'bg-info';
            default: return 'bg-secondary';
        }
    }
    
    startAutoRefresh() {
        // 每30秒自动刷新一次
        this.refreshInterval = setInterval(() => {
            this.loadStatus();
        }, 30000);
    }
    
    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }
}

// 全局函数：刷新数据搜集状态
async function refreshDataCollectionStatus() {
    if (window.dataCollectionMonitor) {
        await window.dataCollectionMonitor.loadStatus();
        if (window.showToast) {
            window.showToast('success', '刷新成功', '数据搜集状态已更新');
        }
    }
}

// 全局函数：触发自动搜集
async function triggerAutoCollection() {
    try {
        const response = await fetch('/api/data-collection/trigger-auto', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const result = await response.json();
        
        if (result.success) {
            if (window.showToast) {
                window.showToast('success', '触发成功', result.message);
            }
            // 刷新状态
            setTimeout(() => {
                refreshDataCollectionStatus();
            }, 1000);
        } else {
            if (window.showToast) {
                window.showToast('warning', '触发失败', result.message);
            }
        }
    } catch (error) {
        console.error('触发自动搜集失败:', error);
        if (window.showToast) {
            window.showToast('error', '触发失败', '无法连接到服务器');
        }
    }
}

// 导出全局函数和类
window.refreshDataCollectionStatus = refreshDataCollectionStatus;
window.triggerAutoCollection = triggerAutoCollection;
window.DataCollectionMonitor = DataCollectionMonitor;

