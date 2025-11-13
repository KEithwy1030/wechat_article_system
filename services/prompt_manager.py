"""
AI提示词管理模块
统一管理所有AI模型的提示词模板（文章、摘要、生图等）
"""

class PromptManager:
    """AI提示词统一管理"""

    # 角色定位
    ROLE_PROMPT = """
你是一位专业的微信公众号内容创作者，拥有丰富的数字媒体经验，精通内容策划、用户心理分析和新媒体营销。你擅长为不同目标受众（如年轻人、职场人士、兴趣爱好者等）创作引人入胜、易于传播的内容，熟悉微信公众号的运营规则、排版规范和传播机制。你能够根据主题和用户需求，灵活调整写作风格（例如专业干货、轻松幽默、温暖治愈），并结合热点、数据或故事提升文章吸引力，确保高阅读量和分享率。
"""

    # 文章生成提示词（通用，Gemini/DeepSeek/阿里云百炼）
    @staticmethod
    def article_prompt(title, word_count=None, char_limit=20000):
        word_count_str = f"{word_count}字" if word_count else "1200-1800字"
        return f"""{PromptManager.ROLE_PROMPT}\n请帮我撰写一篇关于《{title}》的微信公众号文章。

**重要：输出格式要求**
1. **使用Markdown格式**：必须使用标准的Markdown语法输出文章内容
2. **不要包含文章标题**：文章标题《{title}》将由系统自动处理，请直接输出文章正文内容
3. **字数要求**：文章正文约{word_count_str}（不含图片占位符）
4. **图片占位符**：需要插入图片的地方使用 `![图片描述](IMAGE_PLACEHOLDER_N)`，其中N为序号（1,2,3...）

**Markdown格式规范：**
- 使用 `##` 或 `###` 标记段落标题
- 使用 `**文本**` 标记重点内容
- 使用 `> 引用内容` 标记引用或重要观点
- 使用 `1. 条目` 或 `- 条目` 标记列表
- 使用空行分隔段落

**示例输出：**
```markdown
## 引言

这是文章的开头段落...

![图片描述](IMAGE_PLACEHOLDER_1)

## 核心观点

这里是核心内容，**重点强调**的文字。

> 这是一个重要的引用或观点

### 详细分析

1. 第一个要点
2. 第二个要点
3. 第三个要点

![图片描述](IMAGE_PLACEHOLDER_2)

## 总结

文章的总结部分...
```

请直接输出Markdown格式的文章内容，不要包含其他说明文字或代码块标记："""

    # 摘要生成提示词（通用）
    @staticmethod
    def digest_prompt(title, content_preview):
        return f"""{PromptManager.ROLE_PROMPT}\n请为以下文章生成一个简洁的摘要：\n\n标题：{title}\n内容预览：{content_preview}\n\n要求：\n1. 摘要长度不超过100字\n2. 概括文章的核心内容和价值\n3. 语言吸引人，能激发读者的阅读兴趣\n4. 不要包含HTML标签，纯文本即可\n5. 使用中文表达\n\n请直接输出摘要内容，不要包含任何其他说明文字："""

    # 生图生成提示词（Gemini/海报风格）
    # @staticmethod
    # def image_prompt(title, description="", user_custom=""):
    #     if user_custom:
    #         base_prompt = f"{PromptManager.ROLE_PROMPT}\n{user_custom}"
    #     else:
    #         base_prompt = f"{PromptManager.ROLE_PROMPT}\n为文章《{title}》生成一张高质量的海报风格配图。\n\n要求：\n1. 图片风格现代、简洁、专业，具有海报感\n2. 色调温和，适合微信公众号\n3. 构图美观，有设计感\n4. 与文章主题相关\n5. 图片中不要包含过多文字，最好无文字，仅以视觉元素表达主题\n6. 尺寸比例适合作为文章封面\n7. 使用中国读者喜欢的视觉元素\n"
    #     if description:
    #         base_prompt += f"\n\n文章描述：{description}\n请根据文章内容生成相关的视觉元素。"
    #     return base_prompt

    # 生图生成提示词（带风格）
    @staticmethod
    def image_prompt_with_style(title, description="", user_style=""):
        # user_style 动态替换风格/景别/运镜部分
        base_prompt = f"为文章《{title}》生成一张高质量的配图。"
        if user_style:
            # 用户输入替换默认风格
            style_line = f"图片风格：{user_style}。"
        else:
            style_line = "图片风格现代、简洁、专业，具有海报感。"
        base_prompt += f"\n要求：\n1. {style_line}\n2. 色调温和，适合微信公众号\n3. 构图美观，有设计感\n4. 与文章主题相关\n5. 图片中不要包含过多文字，最好无文字，仅以视觉元素表达主题\n6. 尺寸比例适合作为文章封面\n7. 使用中国读者喜欢的视觉元素"
        if description:
            base_prompt += f"\n\n文章描述：{description}\n请根据文章内容生成相关的视觉元素。"
        # 追加英文提示
        base_prompt += "\n\n请用英文输出提示词。"
        return base_prompt

    # 体育文章专用图片提示词（包含两个球队元素）
    @staticmethod
    def image_prompt_for_sports_match(match_info: dict, article_section: str = "", image_index: int = 1, include_fans: bool = True):
        """
        为体育竞彩文章生成包含两个球队元素的图片提示词
        
        :param match_info: 比赛信息字典，包含 home_team, away_team, league 等
        :param article_section: 文章段落内容（用于判断图片类型）
        :param image_index: 图片索引（1=封面图，2+ =内文配图）
        :param include_fans: 是否包含女球迷元素（吸引眼球）
        :return: 中文提示词（后续由AI转换为英文）
        """
        home_team = match_info.get('home_team', '主队')
        away_team = match_info.get('away_team', '客队')
        league = match_info.get('league', '足球联赛')
        
        # 根据图片索引和文章内容判断图片类型
        if image_index == 1:
            # 封面图：强调对抗感和吸引力
            image_type = "封面海报"
            composition = "左右分屏或对角线构图，展现两队对抗感"
            if include_fans:
                elements = f"包含两个球队的球员形象，以及穿着两队球衣的美丽女球迷，营造激烈对抗和吸引眼球的视觉效果"
            else:
                elements = f"包含两个球队的球员形象，展现激烈对抗的视觉效果"
        else:
            # 内文配图：根据段落内容判断
            section_lower = article_section.lower() if article_section else ""
            if '预测' in section_lower or '分析' in section_lower:
                image_type = "数据分析图"
                composition = "数据可视化风格，包含比分预测元素"
                elements = f"两个球队的球员形象，配合数据图表元素"
            elif '历史' in section_lower or '交锋' in section_lower:
                image_type = "历史对比图"
                composition = "历史感、对比风格"
                elements = f"两个球队的球员形象，展现历史交锋感"
            elif '球员' in section_lower or '阵容' in section_lower:
                image_type = "球员特写图"
                composition = "球员特写、运动风格"
                elements = f"两个球队的关键球员形象"
            else:
                image_type = "体育海报"
                composition = "现代体育海报风格"
                if include_fans:
                    elements = f"两个球队的球员形象，以及穿着两队球衣的美丽女球迷"
                else:
                    elements = f"两个球队的球员形象"
        
        base_prompt = f"""为体育竞彩文章生成{image_type}风格的配图。

比赛信息：
- 主队：{home_team}
- 客队：{away_team}
- 联赛：{league}

图片要求：
1. **必须包含的元素**：{elements}
2. **构图方式**：{composition}
3. **视觉风格**：现代、专业、具有体育感和竞技感
4. **色彩方案**：使用两队主色调或联赛标志色，营造对抗氛围
5. **氛围营造**：激烈对抗、竞技感、专业感
6. **适合场景**：微信公众号文章配图，吸引读者点击
7. **图片质量**：高清、专业、细节丰富
8. **无文字要求**：纯视觉表达，不包含文字或数字

{"9. **女球迷元素**：如果包含女球迷，要求美丽、健康、穿着球队球衣，展现球迷热情，但不要过于暴露或低俗" if include_fans else ""}

{"段落内容参考：" + article_section[:200] + "（请根据此内容调整图片元素）" if article_section else ""}

请用英文输出详细的图片生成提示词，格式要求：
- 主体描述（subject）：两个球队的球员、女球迷等
- 风格描述（style）：现代体育海报、专业摄影风格
- 色彩描述（color scheme）：两队主色调
- 构图描述（composition）：左右分屏、对角线等
- 氛围描述（atmosphere）：激烈对抗、竞技感
- 质量要求（quality）：高清、专业、细节丰富

提示词长度：80-120个英文单词，使用专业的美术和摄影术语。"""
        
        return base_prompt

    # 女球迷照片专用提示词（真实、吸引眼球）
    @staticmethod
    def female_fan_image_prompt(match_info: dict, team_side: str = "home", reference_image_description: str = ""):
        """
        为体育文章生成真实、吸引眼球的女球迷照片提示词
        
        :param match_info: 比赛信息字典，包含 home_team, away_team, league 等
        :param team_side: "home" 或 "away"，表示主队或客队
        :param reference_image_description: 参考图片的描述（如果提供）
        :return: 中文提示词（后续由AI转换为英文）
        """
        team_name = match_info.get('home_team' if team_side == 'home' else 'away_team', '球队')
        league = match_info.get('league', '足球联赛')
        
        # 根据球队确定球衣颜色
        if '英格兰' in team_name or 'England' in team_name:
            jersey_colors = "白色和红色（St. George's Cross colors）"
        elif '塞尔维亚' in team_name or 'Serbia' in team_name:
            jersey_colors = "红色和蓝色（Serbian flag colors）"
        else:
            jersey_colors = "球队主色调"
        
        base_prompt = f"""为{team_name}球队生成一张真实、吸引眼球的女球迷照片。

**核心要求：**
1. **真实性**：照片必须看起来像真实拍摄的照片，不能有明显的AI生成痕迹，不能"一眼假"
2. **吸引力**：针对男性观众，必须非常吸引眼球，不能平庸
3. **合规性**：在合规的前提下，尽可能吸引眼球

**人物要求：**
1. **外貌特征**：
   - 长相甜美、妩媚、有魅力
   - 身材曲线优美：胸部丰满、腰细、身材比例好
   - 整体形象健康、阳光、有活力
   - 不能是平庸或普通的外貌

2. **服装要求**：
   - 穿着{team_name}球队的球衣（{jersey_colors}）
   - 球衣可以是紧身款，展现身材曲线
   - 可以搭配短裤或短裙，展现腿部线条
   - 服装要时尚、有吸引力，但不能过于暴露

3. **表情和姿态**：
   - 表情可以是甜美微笑、妩媚、自信等
   - 姿态要自然、有魅力，展现球迷热情
   - 可以有一些吸引人的动作（如挥手、比心等），但要自然不做作

**拍摄要求：**
1. **摄影风格**：
   - 专业摄影风格，像真实拍摄的照片
   - 高质量、细节丰富、真实感强
   - 自然光线或专业打光，避免过度处理

2. **背景**：
   - 可以是球场、看台、或简洁的背景
   - 背景要真实，不能有明显的AI生成痕迹

3. **构图**：
   - 人物为主体，突出女球迷的形象
   - 可以是半身照或全身照
   - 构图要专业，有视觉吸引力

**质量要求：**
- 高清、专业、细节丰富
- 真实感强，不能"一眼假"
- 适合微信公众号文章配图
- 吸引眼球，提升点击率

{"参考图片描述：" + reference_image_description if reference_image_description else ""}

请用英文输出详细的图片生成提示词，要求：
- 使用专业摄影术语
- 明确描述人物特征（外貌、身材、表情）
- 明确描述服装和姿态
- 强调真实感和吸引力
- 提示词长度：100-150个英文单词
- 使用专业的美术和摄影术语，确保生成的照片真实、吸引人

**特别强调：**
- 必须强调"professional photography", "realistic", "authentic", "not AI-generated"
- 必须强调"attractive", "eye-catching", "appealing to male audience"
- 必须强调人物特征："beautiful", "curvaceous", "full bust", "slim waist", "well-proportioned"
- 必须强调"NOT average or ordinary looking"
- 必须避免明显的AI生成痕迹"""
        
        return base_prompt

    # Pexels搜索提示词已移除 