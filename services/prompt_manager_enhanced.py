"""
增强版提示词管理模块
支持可视化管理和动态调整AI提示词
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

class PromptCategory(Enum):
    """提示词分类"""
    DATA_COLLECTOR = "data_collector"  # 数据搜集员
    WRITER = "writer"  # 撰写主编
    QWEN_VL_ANALYZER = "qwen_vl_analyzer"  # 千问VL分析器
    
    @property
    def display_name(self):
        """获取分类的中文显示名称"""
        display_names = {
            self.DATA_COLLECTOR: "数据搜集员",
            self.WRITER: "撰写主编", 
            self.QWEN_VL_ANALYZER: "深度分析(源3)"
        }
        return display_names.get(self, self.value)
    
    @property
    def description(self):
        """获取分类的功能描述"""
        descriptions = {
            self.DATA_COLLECTOR: "负责收集和分析比赛数据，生成赛前情报摘要",
            self.WRITER: "负责撰写完整的分析文章，包含预测结果",
            self.QWEN_VL_ANALYZER: "负责分析体育数据截图，提取详细的比赛信息"
        }
        return descriptions.get(self, "未知分类")

class PromptTemplate:
    """提示词模板类"""
    
    def __init__(self, category: PromptCategory, name: str, content: str, 
                 variables: Dict[str, str] = None, is_active: bool = True,
                 created_at: datetime = None, updated_at: datetime = None,
                 usage_count: int = 0, success_rate: float = 0.0):
        self.category = category
        self.name = name
        self.content = content
        self.variables = variables or {}
        self.is_active = is_active
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.usage_count = usage_count
        self.success_rate = success_rate
    
    def to_dict(self):
        return {
            "category": self.category.value,
            "category_display": self.category.display_name,
            "category_description": self.category.description,
            "name": self.name,
            "content": self.content,
            "variables": self.variables,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "usage_count": self.usage_count,
            "success_rate": self.success_rate
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        try:
            category = PromptCategory(data["category"])
        except ValueError:
            logger.warning(f"忽略未知的提示词分类: {data.get('category')}")
            return None
        return cls(
            category=category,
            name=data["name"],
            content=data["content"],
            variables=data.get("variables", {}),
            is_active=data.get("is_active", True),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get("updated_at", datetime.now().isoformat())),
            usage_count=data.get("usage_count", 0),
            success_rate=data.get("success_rate", 0.0)
        )

class EnhancedPromptManager:
    """增强版提示词管理器"""
    
    def __init__(self, config_file: str = "prompt_templates.json"):
        self.config_file = config_file
        self.templates: Dict[str, PromptTemplate] = {}
        self.load_templates()
        self._initialize_default_templates()
    
    def load_templates(self):
        """加载提示词模板"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for key, template_data in data.items():
                        template = PromptTemplate.from_dict(template_data)
                        if template:
                            self.templates[key] = template
                logger.info(f"加载了 {len(self.templates)} 个提示词模板")
            else:
                logger.info("提示词模板文件不存在，将创建默认模板")
        except Exception as e:
            logger.error(f"加载提示词模板失败: {e}")
    
    def save_templates(self):
        """保存提示词模板"""
        try:
            data = {}
            for key, template in self.templates.items():
                data[key] = template.to_dict()
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"保存了 {len(self.templates)} 个提示词模板")
        except Exception as e:
            logger.error(f"保存提示词模板失败: {e}")
    
    def _initialize_default_templates(self):
        """初始化默认模板"""
        if not self.templates:
            # 数据搜集员模板
            self.add_template(
                key="data_collector_default",
                template=PromptTemplate(
                    category=PromptCategory.DATA_COLLECTOR,
                    name="专业数据分析师",
                    content="""你是一名专业的足球数据分析师。请根据以下信息生成《赛前情报摘要》：

**比赛信息：** {title}
**搜索资料：** {search_content}

请严格按照以下格式输出：

### 赛前情报摘要：{home_team} vs {away_team}

#### 一、双方近期状态与战绩
- **{home_team}**：{home_form}
- **{away_team}**：{away_form}

#### 二、历史交锋记录
{head_to_head}

#### 三、阵容情报
{injuries_suspensions}

#### 四、战术风格分析
{tactical_analysis}

#### 五、市场观点
{market_opinion}

#### 六、分析师初步判断
- **推荐：** {recommendation}
- **理由：** {reasoning}"""
                )
            )
            
            # 撰写主编模板
            self.add_template(
                key="writer_default",
                template=PromptTemplate(
                    category=PromptCategory.WRITER,
                    name="老k主编",
                    content="""你是公众号"老k看不准"的主编。请根据以下信息撰写文章，**必须严格参考历史文章的排版风格**：

**赛前情报摘要：** {intelligence_summary}
**昨日文章参考：** {yesterday_content}

请生成一篇完整的微信公众号文章，严格按照以下格式和排版要求：

**文章结构要求：**
1. **主标题**：在文章内容开头显示完整标题，如：周日006 韩职 水原FCVS首尔FC
2. **作者信息**：紧跟标题显示"老k"
3. **配图说明**：在文章开头添加配图说明，格式为：![比赛配图](match_image.jpg)
4. **前言部分**：使用"老k前言"作为小标题，内容以"各位老铁，午好！"开头
5. **主体内容**：使用"一、二、三、四"编号，每个标题都要加粗
6. **判断部分**：独立的"老k的判断"部分
7. **推荐部分**：独立的"推荐：{home_team}胜"，完整格式
8. **结尾部分**："老k多说一句"
9. **声明部分**：使用引用块格式

**排版要求：**
- 使用HTML标签控制格式，不使用Markdown
- 标题使用<strong>标签加粗
- 段落之间有充足的空行
- 关键信息加粗显示
- 声明使用<blockquote>引用块格式

请直接输出完整的HTML格式文章内容："""
                )
            )
            
            self.save_templates()
    
    def add_template(self, key: str, template: PromptTemplate):
        """添加模板"""
        self.templates[key] = template
        self.save_templates()
        logger.info(f"添加模板: {key} - {template.name}")
    
    def update_template(self, key: str, **kwargs):
        """更新模板"""
        if key in self.templates:
            template = self.templates[key]
            for attr, value in kwargs.items():
                if hasattr(template, attr):
                    setattr(template, attr, value)
            template.updated_at = datetime.now()
            self.save_templates()
            logger.info(f"更新模板: {key}")
        else:
            logger.warning(f"模板不存在: {key}")
    
    def delete_template(self, key: str):
        """删除模板"""
        if key in self.templates:
            del self.templates[key]
            self.save_templates()
            logger.info(f"删除模板: {key}")
    
    def get_template(self, key: str) -> Optional[PromptTemplate]:
        """获取模板"""
        return self.templates.get(key)
    
    def get_templates_by_category(self, category: PromptCategory) -> Dict[str, PromptTemplate]:
        """按分类获取模板"""
        return {k: v for k, v in self.templates.items() if v.category == category}
    
    def get_active_templates(self) -> Dict[str, PromptTemplate]:
        """获取活跃模板"""
        return {k: v for k, v in self.templates.items() if v.is_active}
    
    def render_template(self, key: str, variables: Dict[str, str]) -> str:
        """渲染模板"""
        template = self.get_template(key)
        if not template:
            raise ValueError(f"模板不存在: {key}")
        
        content = template.content
        for var_name, var_value in variables.items():
            content = content.replace(f"{{{var_name}}}", str(var_value))
        
        # 记录使用次数
        template.usage_count += 1
        self.save_templates()
        
        return content
    
    def record_success(self, key: str, is_success: bool):
        """记录成功/失败"""
        template = self.get_template(key)
        if template:
            if template.usage_count > 0:
                # 计算新的成功率
                current_successes = template.success_rate * (template.usage_count - 1)
                new_successes = current_successes + (1 if is_success else 0)
                template.success_rate = new_successes / template.usage_count
            else:
                template.success_rate = 1.0 if is_success else 0.0
            
            self.save_templates()
            logger.info(f"记录模板 {key} 成功率: {template.success_rate:.2%}")
    
    def export_templates(self) -> Dict[str, Any]:
        """导出模板数据"""
        return {
            "export_time": datetime.now().isoformat(),
            "templates": {k: v.to_dict() for k, v in self.templates.items()}
        }
    
    def import_templates(self, data: Dict[str, Any]):
        """导入模板数据"""
        try:
            templates_data = data.get("templates", {})
            for key, template_data in templates_data.items():
                self.templates[key] = PromptTemplate.from_dict(template_data)
            self.save_templates()
            logger.info(f"导入了 {len(templates_data)} 个模板")
        except Exception as e:
            logger.error(f"导入模板失败: {e}")
            raise

# 全局实例
prompt_manager = EnhancedPromptManager()
