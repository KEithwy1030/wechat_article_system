/**
 * MatchResultService.js - 比赛结果服务
 * 处理比赛结果的保存和更新
 */
class MatchResultService {
    /**
     * 保存比赛结果（行内编辑版本）
     * @param {string} matchCode - 比赛编号
     * @param {HTMLElement} button - 触发保存的按钮元素
     */
    static async saveMatchResult(matchCode, button) {
        const inputGroup = button.closest('.input-group');
        const input = inputGroup.querySelector('.score-input');
        const actualScore = input.value.trim();
        
        // 验证比分格式
        if (!actualScore) {
            if (window.showToast) {
                window.showToast('error', '格式错误', '请输入实际比分');
            }
            input.focus();
            return;
        }
            
        if (!/^\d+-\d+$/.test(actualScore)) {
            if (window.showToast) {
                window.showToast('error', '格式错误', '比分格式错误，应为"数字-数字"格式，如"2-1"');
            }
            input.focus();
            input.select();
            return;
        }
            
        try {
            // 显示保存中状态
            button.disabled = true;
            button.innerHTML = '<i class="bi bi-hourglass-split"></i>';
            
            const response = await fetch(`/api/lottery/match/${matchCode}/result`, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({actual_score: actualScore})
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                if (window.showToast) {
                    window.showToast('success', '保存成功', `比赛结果已更新: ${matchCode} -> ${actualScore}`);
                }
                
                // 更新单元格显示
                const scoreCell = inputGroup.parentElement;
                scoreCell.innerHTML = actualScore;
                
                // 刷新数据
                if (window.sportteryManager) {
                    window.sportteryManager.refreshMatchesData();
                }
            } else {
                if (window.showToast) {
                    window.showToast('error', '保存失败', data.message || '未知错误');
                }
                // 恢复按钮状态
                button.disabled = false;
                button.innerHTML = '<i class="bi bi-check"></i>';
            }
        } catch (error) {
            if (window.showToast) {
                window.showToast('error', '网络错误', '无法连接到服务器');
            }
            // 恢复按钮状态
            button.disabled = false;
            button.innerHTML = '<i class="bi bi-check"></i>';
        }
    }
}

// 导出为全局函数，保持向后兼容
window.saveMatchResult = MatchResultService.saveMatchResult.bind(MatchResultService);
window.MatchResultService = MatchResultService;

