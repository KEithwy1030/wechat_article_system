/**
 * AppInitializer.js - 应用初始化器
 * 负责应用启动时的初始化逻辑
 */
class AppInitializer {
    /**
     * 初始化应用
     */
    static init() {
        // 等待DOM加载完成
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                this.initialize();
            });
        } else {
            // DOM已经加载完成
            this.initialize();
        }
    }
    
    /**
     * 执行初始化逻辑
     */
    static initialize() {
        this._initializedPanels = new Set();
        this._dataMonitorInitialized = false;
        this._panelInitializers = {
            'sporttery-panel': () => this.initializeSportteryManager(),
            'config-panel': () => this.initializeConfigManager()
        };
        
        const activeNav = document.querySelector('.nav-item.active');
        const defaultPanelId = activeNav?.dataset?.target;
        if (defaultPanelId) {
            this.activatePanel(defaultPanelId);
        }
    }
    
    static activatePanel(panelId) {
        if (!panelId) {
            return;
        }
        
        // 对于其他面板，只初始化一次
        if (panelId !== 'sporttery-panel' && this._initializedPanels?.has(panelId)) {
            return;
        }
        
        const initializer = this._panelInitializers?.[panelId];
        if (typeof initializer === 'function') {
            // 对于 sporttery-panel，只在首次初始化时执行
            if (panelId === 'sporttery-panel') {
                // 如果已经初始化过，不再执行任何操作（避免重复刷新）
                if (this._sportteryInitialized && window.sportteryManager) {
                    console.log('SportteryManager 已初始化，跳过重复激活');
                    return;
                } else {
                    // 首次初始化（这里会调用刷新方法）
                    initializer.call(this);
                    this._initializedPanels.add(panelId);
                }
            } else {
                // 其他面板：只初始化一次
                initializer.call(this);
                this._initializedPanels.add(panelId);
            }
        }
    }
    
    /**
     * 初始化竞彩数据管理器
     */
    static initializeSportteryManager() {
        if (typeof SportteryManager === 'undefined') {
            console.warn('SportteryManager类未定义，跳过初始化');
            return;
        }
        
        if (this._sportteryInitialized) {
            console.log('SportteryManager 已初始化，跳过重复初始化');
            return;
        }
        
        const sportteryManager = new SportteryManager();
        
        // 兼容旧代码：将实例挂到app，避免onclick中找不到app
        window.app = sportteryManager;
        window.sportteryManager = sportteryManager;
        
        // 标记为已初始化（在调用刷新方法之前，避免重复调用）
        this._sportteryInitialized = true;
        
        // 页面加载时初始化统计卡片
        sportteryManager.refreshAccuracyStats();

        // 页面加载时拉取数据库中的最新赛程/赛果（保持与新架构一致）
        if (typeof sportteryManager.refreshMatchesData === 'function') {
            sportteryManager.refreshMatchesData();
        } else {
            console.warn('sportteryManager.refreshMatchesData 未定义，跳过初始化刷新');
        }
        
        // 绑定手动触发工作流按钮
        const runWorkflowBtn = document.getElementById('run-all-workflow');
        if (runWorkflowBtn) {
            runWorkflowBtn.addEventListener('click', () => {
                // 显示确认弹窗
                const modal = document.getElementById('runWorkflowModal');
                if (modal && typeof bootstrap !== 'undefined') {
                    const bsModal = new bootstrap.Modal(modal);
                    bsModal.show();
                } else if (modal) {
                    // 降级方案：直接显示
                    modal.style.display = 'block';
                    modal.classList.add('show');
                }
            });
        }
        
        // 绑定确认执行按钮（工作流功能暂未在新模块中实现，保留接口以便后续扩展）
        const confirmBtn = document.getElementById('confirmRunWorkflow');
        if (confirmBtn) {
            confirmBtn.addEventListener('click', async () => {
                try {
                    // 直接调用API执行工作流
                    const response = await fetch('/api/lottery/scheduler/run-all-tasks', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' }
                    });
                    
                    const result = await response.json();
                    
                    if (result.status === 'success') {
                        if (window.showToast) {
                            window.showToast('success', '执行完成', `成功执行 ${result.data?.success_tasks || 0}/${result.data?.total_tasks || 0} 个任务`);
                        }
                    } else {
                        if (window.showToast) {
                            window.showToast('error', '执行失败', result.message || '未知错误');
                        }
                    }
                } catch (error) {
                    console.error('执行工作流失败:', error);
                    if (window.showToast) {
                        window.showToast('error', '网络错误', '无法连接到服务器');
                    }
                }
                
                // 关闭弹窗
                const modal = document.getElementById('runWorkflowModal');
                if (modal && typeof bootstrap !== 'undefined') {
                    const bsModal = bootstrap.Modal.getInstance(modal);
                    if (bsModal) {
                        bsModal.hide();
                    }
                }
            });
        }
        
        // 绑定统计卡片点击事件
        const accuracyStatsCard = document.getElementById('accuracy-stats-card');
        if (accuracyStatsCard) {
            console.log('✅ 找到统计卡片元素，绑定点击事件');
            accuracyStatsCard.addEventListener('click', () => {
                console.log('✅ 统计卡片被点击了！');
                if (sportteryManager && typeof sportteryManager.refreshAccuracyStats === 'function') {
                    console.log('✅ 调用 sportteryManager.refreshAccuracyStats');
                    sportteryManager.refreshAccuracyStats();
                } else {
                    console.error('❌ sportteryManager.refreshAccuracyStats 方法未找到');
                }
            });
        } else {
            console.warn('⚠️ 未找到统计卡片元素 accuracy-stats-card');
        }
        
        this.initializeDataCollectionMonitor();
        // _sportteryInitialized 已在方法开始处设置，避免重复调用
    }
    
    /**
     * 初始化配置管理
     */
    static initializeConfigManager() {
        // 使用app.js中已存在的ConfigManager类
        if (typeof ConfigManager !== 'undefined') {
            if (this._configInitialized) {
                return;
            }
            
            // 绑定保存配置按钮事件
            const saveConfigBtn = document.getElementById('save-config');
            if (saveConfigBtn) {
                saveConfigBtn.addEventListener('click', () => {
                    ConfigManager.saveConfig();
                });
            }
            
            // 页面加载时自动加载配置
            ConfigManager.loadConfig();
            this._configInitialized = true;
        } else {
            console.warn('ConfigManager类未定义，配置管理功能可能不可用');
        }
    }
    
    /**
     * 初始化数据搜集监控器
     */
    static initializeDataCollectionMonitor() {
        if (this._dataMonitorInitialized) {
            return;
        }
        
        const dataCollectionMonitor = new DataCollectionMonitor();
        window.dataCollectionMonitor = dataCollectionMonitor;
        
        // 检查是否有未完成的深度分析任务（兼容旧代码）
        if (window.app && typeof window.app.checkPendingTask === 'function') {
            window.app.checkPendingTask();
        }
        
        this._dataMonitorInitialized = true;
    }
}

// 自动初始化（等待所有模块加载完成）
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        // 确保所有依赖已加载
        setTimeout(() => {
            AppInitializer.init();
        }, 100);
    });
} else {
    setTimeout(() => {
        AppInitializer.init();
    }, 100);
}

// 导出为全局类
window.AppInitializer = AppInitializer;

