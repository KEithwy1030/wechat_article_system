"""
Markdown到微信公众号HTML转换服务
将Markdown格式转换为符合微信公众号规范的HTML
"""

import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class MarkdownConverter:
    """Markdown到微信HTML转换器"""
    
    # 微信公众号样式配置
    WECHAT_STYLES = {
        'h1': 'font-size: 24px; color: #333; font-weight: 600; margin: 1.5em 0 0.8em; line-height: 1.4;',
        'h2': 'font-size: 20px; color: #333; font-weight: 600; margin: 1.5em 0 0.8em; line-height: 1.4;',
        'h3': 'font-size: 18px; color: #333; font-weight: 600; margin: 1.5em 0 0.8em; line-height: 1.4;',
        'p': 'margin-bottom: 1em; text-align: justify; line-height: 1.75; color: #333; font-size: 16px;',
        'strong': 'color: #1aad19; font-weight: 600;',
        'blockquote': 'border-left: 4px solid #1aad19; padding-left: 1em; margin: 1em 0; color: #666; background: #f7f7f7; padding: 1em; border-radius: 4px;',
        'ul': 'padding-left: 1.5em; margin: 1em 0;',
        'ol': 'padding-left: 1.5em; margin: 1em 0;',
        'li': 'margin-bottom: 0.5em; line-height: 1.75;',
        'img': 'max-width: 100%; height: auto; border-radius: 4px; margin: 1em 0; display: block;',
        'code': 'background: #f1f1f1; padding: 2px 4px; border-radius: 3px; font-family: Monaco, Menlo, Consolas, monospace; font-size: 0.9em;',
        'pre': 'background: #f1f1f1; padding: 1em; border-radius: 4px; overflow-x: auto; margin: 1em 0;'
    }
    
    @staticmethod
    def convert_to_wechat_html(markdown_content: str) -> str:
        """
        将Markdown转换为符合微信公众号规范的HTML
        :param markdown_content: Markdown格式的文章内容
        :return: 符合微信规范的HTML内容
        """
        try:
            html = markdown_content
            
            # 1. 转换标题
            html = re.sub(r'^### (.+)$', lambda m: f'<h3 style="{MarkdownConverter.WECHAT_STYLES["h3"]}">{m.group(1)}</h3>', html, flags=re.MULTILINE)
            html = re.sub(r'^## (.+)$', lambda m: f'<h2 style="{MarkdownConverter.WECHAT_STYLES["h2"]}">{m.group(1)}</h2>', html, flags=re.MULTILINE)
            html = re.sub(r'^# (.+)$', lambda m: f'<h1 style="{MarkdownConverter.WECHAT_STYLES["h1"]}">{m.group(1)}</h1>', html, flags=re.MULTILINE)
            
            # 2. 转换图片
            html = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', lambda m: f'<img src="{m.group(2)}" alt="{m.group(1)}" style="{MarkdownConverter.WECHAT_STYLES["img"]}">', html)
            
            # 3. 转换粗体
            html = re.sub(r'\*\*(.+?)\*\*', lambda m: f'<strong style="{MarkdownConverter.WECHAT_STYLES["strong"]}">{m.group(1)}</strong>', html)
            
            # 4. 转换斜体
            html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
            
            # 5. 转换引用块
            html = re.sub(r'^> (.+)$', lambda m: f'<blockquote style="{MarkdownConverter.WECHAT_STYLES["blockquote"]}">{m.group(1)}</blockquote>', html, flags=re.MULTILINE)
            
            # 6. 转换有序列表
            html = re.sub(r'^\d+\. (.+)$', r'<LIST_ITEM_OL>\1</LIST_ITEM_OL>', html, flags=re.MULTILINE)
            
            # 7. 转换无序列表
            html = re.sub(r'^- (.+)$', r'<LIST_ITEM_UL>\1</LIST_ITEM_UL>', html, flags=re.MULTILINE)
            
            # 8. 包装列表项
            html = MarkdownConverter._wrap_lists(html)
            
            # 9. 转换段落（多行文本包装为段落）
            html = MarkdownConverter._convert_paragraphs(html)
            
            # 10. 清理多余的空行
            html = re.sub(r'\n{3,}', '\n\n', html)
            
            logger.info("Markdown转换为微信HTML成功")
            return html.strip()
            
        except Exception as e:
            logger.error(f"Markdown转换失败: {str(e)}")
            return markdown_content
    
    @staticmethod
    def _wrap_lists(html: str) -> str:
        """包装列表项为完整的列表"""
        # 处理有序列表
        html = re.sub(
            r'(<LIST_ITEM_OL>.*?</LIST_ITEM_OL>(\n<LIST_ITEM_OL>.*?</LIST_ITEM_OL>)*)',
            lambda m: f'<ol style="{MarkdownConverter.WECHAT_STYLES["ol"]}">' + 
                     m.group(0).replace('<LIST_ITEM_OL>', f'<li style="{MarkdownConverter.WECHAT_STYLES["li"]}">').replace('</LIST_ITEM_OL>', '</li>') + 
                     '</ol>',
            html,
            flags=re.DOTALL
        )
        
        # 处理无序列表
        html = re.sub(
            r'(<LIST_ITEM_UL>.*?</LIST_ITEM_UL>(\n<LIST_ITEM_UL>.*?</LIST_ITEM_UL>)*)',
            lambda m: f'<ul style="{MarkdownConverter.WECHAT_STYLES["ul"]}">' + 
                     m.group(0).replace('<LIST_ITEM_UL>', f'<li style="{MarkdownConverter.WECHAT_STYLES["li"]}">').replace('</LIST_ITEM_UL>', '</li>') + 
                     '</ul>',
            html,
            flags=re.DOTALL
        )
        
        return html
    
    @staticmethod
    def _convert_paragraphs(html: str) -> str:
        """将普通文本行转换为段落"""
        lines = html.split('\n')
        result = []
        paragraph_buffer = []
        
        for line in lines:
            line = line.strip()
            
            # 如果是空行
            if not line:
                if paragraph_buffer:
                    # 将缓存的文本包装为段落
                    paragraph_text = ' '.join(paragraph_buffer)
                    result.append(f'<p style="{MarkdownConverter.WECHAT_STYLES["p"]}">{paragraph_text}</p>')
                    paragraph_buffer = []
                continue
            
            # 如果是已经转换的HTML标签
            if line.startswith('<'):
                if paragraph_buffer:
                    paragraph_text = ' '.join(paragraph_buffer)
                    result.append(f'<p style="{MarkdownConverter.WECHAT_STYLES["p"]}">{paragraph_text}</p>')
                    paragraph_buffer = []
                result.append(line)
            else:
                # 普通文本行，添加到段落缓存
                paragraph_buffer.append(line)
        
        # 处理最后的段落缓存
        if paragraph_buffer:
            paragraph_text = ' '.join(paragraph_buffer)
            result.append(f'<p style="{MarkdownConverter.WECHAT_STYLES["p"]}">{paragraph_text}</p>')
        
        return '\n'.join(result)
    
    @staticmethod
    def extract_title(markdown_content: str) -> str:
        """
        从Markdown内容中提取标题
        :param markdown_content: Markdown内容
        :return: 提取的标题
        """
        # 查找第一个一级或二级标题
        match = re.search(r'^#\s+(.+)$|^##\s+(.+)$', markdown_content, re.MULTILINE)
        if match:
            title = match.group(1) or match.group(2)
            logger.info(f"从Markdown中提取标题: {title}")
            return title.strip()
        
        logger.warning("未能从Markdown中提取标题，使用默认标题")
        return "微信公众号文章"
    
    @staticmethod
    def extract_image_placeholders(markdown_content: str) -> list:
        """
        提取Markdown中的图片占位符
        :param markdown_content: Markdown内容
        :return: 图片描述列表
        """
        pattern = r'!\[([^\]]*)\]\(IMAGE_PLACEHOLDER_\d+\)'
        matches = re.findall(pattern, markdown_content)
        logger.info(f"提取到 {len(matches)} 个图片占位符")
        return matches
    
    @staticmethod
    def replace_image_placeholders(markdown_content: str, image_urls: list) -> str:
        """
        替换Markdown中的图片占位符为实际URL
        :param markdown_content: Markdown内容
        :param image_urls: 图片URL列表
        :return: 替换后的Markdown内容
        """
        result = markdown_content
        for i, url in enumerate(image_urls, 1):
            placeholder_pattern = f'IMAGE_PLACEHOLDER_{i}'
            result = result.replace(placeholder_pattern, url)
        
        logger.info(f"已替换 {len(image_urls)} 个图片占位符")
        return result

