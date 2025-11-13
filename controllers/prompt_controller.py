"""
提示词管理控制器
提供提示词模板的CRUD操作和可视化管理的API接口
"""

import logging
from flask import request, jsonify, render_template
from typing import Dict, Any
from services.prompt_manager_enhanced import prompt_manager, PromptCategory, PromptTemplate

logger = logging.getLogger(__name__)

class PromptController:
    """提示词管理控制器类"""
    
    def __init__(self):
        logger.info("提示词管理控制器初始化完成")
    
    def prompt_manager_page(self):
        """显示提示词管理页面"""
        return render_template('prompt_manager.html')
    
    def get_templates(self) -> Dict[str, Any]:
        """获取提示词模板，可按分类筛选"""
        try:
            templates = prompt_manager.get_active_templates()
            
            category_param = request.args.get('category')
            if category_param:
                try:
                    category_enum = PromptCategory(category_param)
                except ValueError:
                    return jsonify({
                        'success': False,
                        'message': f'无效的分类: {category_param}'
                    })
                
                templates = {
                    key: template
                    for key, template in templates.items()
                    if template.category == category_enum
                }
            
            templates_dict = {}
            for key, template in templates.items():
                templates_dict[key] = template.to_dict()
            
            return jsonify({
                'success': True,
                'data': templates_dict
            })
        except Exception as e:
            logger.error(f"获取模板失败: {e}")
            return jsonify({
                'success': False,
                'message': f'获取模板失败: {str(e)}'
            })
    
    def get_template(self, key: str) -> Dict[str, Any]:
        """获取单个提示词模板"""
        try:
            template = prompt_manager.get_template(key)
            if template:
                return jsonify({
                    'success': True,
                    'data': template.to_dict()
                })
            else:
                return jsonify({
                    'success': False,
                    'message': '模板不存在'
                })
        except Exception as e:
            logger.error(f"获取模板失败: {e}")
            return jsonify({
                'success': False,
                'message': f'获取模板失败: {str(e)}'
            })
    
    def create_template(self) -> Dict[str, Any]:
        """创建新的提示词模板"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'message': '请求数据为空'
                })
            
            # 验证必要字段
            required_fields = ['name', 'category', 'content']
            for field in required_fields:
                if field not in data:
                    return jsonify({
                        'success': False,
                        'message': f'缺少必要字段: {field}'
                    })
            
            # 验证分类
            try:
                category = PromptCategory(data['category'])
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': f'无效的分类: {data["category"]}'
                })
            
            # 创建模板
            template = PromptTemplate(
                category=category,
                name=data['name'],
                content=data['content'],
                variables=data.get('variables', {}),
                is_active=data.get('is_active', True)
            )
            
            # 生成唯一key
            import hashlib
            import time
            key = f"{category.value}_{data['name']}_{int(time.time())}"
            key = hashlib.md5(key.encode()).hexdigest()[:16]
            
            prompt_manager.add_template(key, template)
            
            logger.info(f"创建模板成功: {key} - {data['name']}")
            
            return jsonify({
                'success': True,
                'message': '模板创建成功',
                'data': {'key': key}
            })
            
        except Exception as e:
            logger.error(f"创建模板失败: {e}")
            return jsonify({
                'success': False,
                'message': f'创建模板失败: {str(e)}'
            })
    
    def update_template(self, key: str) -> Dict[str, Any]:
        """更新提示词模板"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'message': '请求数据为空'
                })
            
            # 检查模板是否存在
            if not prompt_manager.get_template(key):
                return jsonify({
                    'success': False,
                    'message': '模板不存在'
                })
            
            # 更新模板
            update_data = {}
            if 'name' in data:
                update_data['name'] = data['name']
            if 'content' in data:
                update_data['content'] = data['content']
            if 'variables' in data:
                update_data['variables'] = data['variables']
            if 'is_active' in data:
                update_data['is_active'] = data['is_active']
            
            prompt_manager.update_template(key, **update_data)
            
            logger.info(f"更新模板成功: {key}")
            
            return jsonify({
                'success': True,
                'message': '模板更新成功'
            })
            
        except Exception as e:
            logger.error(f"更新模板失败: {e}")
            return jsonify({
                'success': False,
                'message': f'更新模板失败: {str(e)}'
            })
    
    def delete_template(self, key: str) -> Dict[str, Any]:
        """删除提示词模板"""
        try:
            if not prompt_manager.get_template(key):
                return jsonify({
                    'success': False,
                    'message': '模板不存在'
                })
            
            prompt_manager.delete_template(key)
            
            logger.info(f"删除模板成功: {key}")
            
            return jsonify({
                'success': True,
                'message': '模板删除成功'
            })
            
        except Exception as e:
            logger.error(f"删除模板失败: {e}")
            return jsonify({
                'success': False,
                'message': f'删除模板失败: {str(e)}'
            })
    
    def get_templates_by_category(self, category: str) -> Dict[str, Any]:
        """按分类获取提示词模板"""
        try:
            try:
                category_enum = PromptCategory(category)
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': f'无效的分类: {category}'
                })
            
            templates = prompt_manager.get_templates_by_category(category_enum)
            templates_dict = {}
            for key, template in templates.items():
                templates_dict[key] = template.to_dict()
            
            return jsonify({
                'success': True,
                'data': templates_dict
            })
            
        except Exception as e:
            logger.error(f"按分类获取模板失败: {e}")
            return jsonify({
                'success': False,
                'message': f'按分类获取模板失败: {str(e)}'
            })
    
    def render_template(self, key: str) -> Dict[str, Any]:
        """渲染提示词模板"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'message': '请求数据为空'
                })
            
            variables = data.get('variables', {})
            rendered_content = prompt_manager.render_template(key, variables)
            
            return jsonify({
                'success': True,
                'data': {
                    'rendered_content': rendered_content
                }
            })
            
        except Exception as e:
            logger.error(f"渲染模板失败: {e}")
            return jsonify({
                'success': False,
                'message': f'渲染模板失败: {str(e)}'
            })
    
    def record_usage(self, key: str) -> Dict[str, Any]:
        """记录模板使用情况"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'message': '请求数据为空'
                })
            
            is_success = data.get('is_success', True)
            prompt_manager.record_success(key, is_success)
            
            return jsonify({
                'success': True,
                'message': '使用记录已保存'
            })
            
        except Exception as e:
            logger.error(f"记录使用情况失败: {e}")
            return jsonify({
                'success': False,
                'message': f'记录使用情况失败: {str(e)}'
            })
    
    def export_templates(self) -> Dict[str, Any]:
        """导出提示词模板"""
        try:
            export_data = prompt_manager.export_templates()
            
            return jsonify({
                'success': True,
                'data': export_data
            })
            
        except Exception as e:
            logger.error(f"导出模板失败: {e}")
            return jsonify({
                'success': False,
                'message': f'导出模板失败: {str(e)}'
            })
    
    def import_templates(self) -> Dict[str, Any]:
        """导入提示词模板"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'message': '请求数据为空'
                })
            
            prompt_manager.import_templates(data)
            
            return jsonify({
                'success': True,
                'message': '模板导入成功'
            })
            
        except Exception as e:
            logger.error(f"导入模板失败: {e}")
            return jsonify({
                'success': False,
                'message': f'导入模板失败: {str(e)}'
            })
    
    def get_template_statistics(self) -> Dict[str, Any]:
        """获取模板统计信息"""
        try:
            templates = prompt_manager.get_active_templates()
            
            total_templates = len(templates)
            active_templates = len([t for t in templates.values() if t.is_active])
            total_usage = sum(t.usage_count for t in templates.values())
            avg_success_rate = sum(t.success_rate for t in templates.values()) / total_templates if total_templates > 0 else 0
            
            # 按分类统计
            category_stats = {}
            for category in PromptCategory:
                category_templates = prompt_manager.get_templates_by_category(category)
                category_stats[category.value] = {
                    'count': len(category_templates),
                    'active': len([t for t in category_templates.values() if t.is_active]),
                    'usage': sum(t.usage_count for t in category_templates.values()),
                    'avg_success_rate': sum(t.success_rate for t in category_templates.values()) / len(category_templates) if len(category_templates) > 0 else 0
                }
            
            return jsonify({
                'success': True,
                'data': {
                    'total_templates': total_templates,
                    'active_templates': active_templates,
                    'total_usage': total_usage,
                    'avg_success_rate': avg_success_rate,
                    'category_stats': category_stats
                }
            })
            
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return jsonify({
                'success': False,
                'message': f'获取统计信息失败: {str(e)}'
            })
    
    def sync_qwen_vl_prompt(self) -> Dict[str, Any]:
        """同步千问VL提示词到实际工作流"""
        try:
            data = request.get_json()
            if not data or 'prompt' not in data:
                return jsonify({
                    'success': False,
                    'message': '请求数据为空或缺少prompt字段'
                })
            
            prompt_content = data['prompt']
            
            # 这里需要更新sports_screenshot_analyzer.py中的提示词
            # 或者创建一个配置文件来存储千问VL的提示词
            try:
                # 更新sports_screenshot_analyzer.py中的提示词
                self._update_sports_screenshot_analyzer_prompt(prompt_content)
                
                logger.info("千问VL提示词同步成功")
                
                return jsonify({
                    'success': True,
                    'message': '千问VL提示词已同步到工作流'
                })
                
            except Exception as update_error:
                logger.error(f"更新sports_screenshot_analyzer失败: {update_error}")
                return jsonify({
                    'success': False,
                    'message': f'同步到工作流失败: {str(update_error)}'
                })
                
        except Exception as e:
            logger.error(f"同步千问VL提示词失败: {e}")
            return jsonify({
                'success': False,
                'message': f'同步失败: {str(e)}'
            })
    
    def _update_sports_screenshot_analyzer_prompt(self, prompt_content: str):
        """更新sports_screenshot_analyzer.py中的提示词"""
        import os
        
        analyzer_file = os.path.join('services', 'sports_screenshot_analyzer.py')
        
        if not os.path.exists(analyzer_file):
            raise FileNotFoundError(f"文件不存在: {analyzer_file}")
        
        # 读取文件内容
        with open(analyzer_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找并替换_build_analysis_prompt方法中的提示词
        import re
        
        # 查找_build_analysis_prompt方法
        pattern = r'(def _build_analysis_prompt\(self, site_info: Dict, match_info: Dict = None\) -> str:\s*"""构建分析提示词"""\s*)(.*?)(return base_prompt)'
        
        def replace_prompt(match):
            method_header = match.group(1)
            return_stmt = match.group(3)
            
            # 构建新的提示词内容
            new_prompt = f'''base_prompt = f"""请仔细分析这张体育数据截图，提取以下所有可能的数据：

## 必需提取的数据：

### 1. 比赛基本信息
- 主队名称（中英文）
- 客队名称（中英文）  
- 比赛时间（具体日期和时间）
- 联赛类型和级别
- 比赛状态（未开始/进行中/已结束）
- 比赛场地

### 2. 比分和结果
- 最终比分
- 半场比分
- 加时赛比分（如有）
- 点球大战比分（如有）
- 比赛结果

### 3. 详细技术统计
- 射门次数（总数和射正）
- 控球率百分比
- 角球数量
- 任意球数量
- 越位次数
- 犯规次数
- 黄牌和红牌数量
- 传球成功率和传球次数
- 拦截次数
- 抢断次数

### 4. 球员数据
- 进球球员姓名和进球时间
- 助攻球员姓名
- 被替换球员和替补球员
- 主要球员的详细统计

### 5. 赔率信息（如有）
- 胜平负赔率
- 让球盘赔率
- 大小球赔率
- 其他投注选项

### 6. 历史数据
- 双方历史交锋记录
- 最近几场比赛结果
- 主客场表现对比

### 7. 其他重要信息
- 天气条件
- 观众人数
- 裁判信息
- 伤病情况
- 停赛球员

请以详细的JSON格式返回所有提取到的数据，如果某些信息在截图中没有显示，请标注"未显示"。确保提取的数据与截图内容完全一致。"""'''
            
            return method_header + new_prompt + '\n\n        ' + return_stmt
        
        # 执行替换
        new_content = re.sub(pattern, replace_prompt, content, flags=re.DOTALL)
        
        if new_content == content:
            # 如果没有找到匹配的模式，尝试直接替换
            # 这里可以添加更多的替换逻辑
            logger.warning("未找到匹配的提示词模式，可能需要手动更新")
            return
        
        # 写回文件
        with open(analyzer_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        logger.info(f"已更新 {analyzer_file} 中的千问VL提示词")