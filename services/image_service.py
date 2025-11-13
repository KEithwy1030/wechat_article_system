"""
图像服务模块
处理图像生成和处理相关操作
"""

import os
import logging
import requests
from datetime import datetime
from typing import Optional, Dict, Any
from google import genai
from google.genai import types
from app_config import AppConfig
from services.prompt_manager import PromptManager

logger = logging.getLogger(__name__)

class ImageService:
    """图像服务类"""
    
    def __init__(self):
        self.client = None
        self.image_model = AppConfig.GEMINI_IMAGE_MODEL
        self.cache_folder = AppConfig.CACHE_FOLDER
        logger.info("图像服务初始化完成")
    
    def _get_gemini_client(self) -> genai.Client:
        """获取Gemini客户端"""
        if not self.client:
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("未设置GEMINI_API_KEY环境变量")
            
            self.client = genai.Client(api_key=api_key)
            logger.info("Gemini客户端创建成功")
        
        return self.client
    
    def generate_female_fan_image(self, match_info: dict, team_side: str = "home", 
                                  image_model: str = "gemini", ai_model: str = "gemini",
                                  reference_image_path: str = None,
                                  dashscope_params: dict = None) -> Optional[str]:
        """
        生成女球迷照片（真实、吸引眼球）
        
        :param match_info: 比赛信息字典，包含 home_team, away_team, league 等
        :param team_side: "home" 或 "away"，表示主队或客队
        :param image_model: 生图模型 (gemini, dashscope)
        :param ai_model: AI模型，用于润色提示词
        :param reference_image_path: 参考图片路径（可选）
        :param dashscope_params: DashScope专用参数
        :return: 图片文件路径
        """
        try:
            from services.prompt_manager import PromptManager
            
            team_name = match_info.get('home_team' if team_side == 'home' else 'away_team', '球队')
            logger.info(f"开始生成{team_name}女球迷照片，使用模型: {image_model}")
            
            # 如果有参考图片，先分析参考图片
            reference_description = ""
            if reference_image_path and os.path.exists(reference_image_path):
                try:
                    from services.gemini_service import gemini_service
                    analysis = gemini_service.analyze_image(
                        reference_image_path,
                        "请详细描述这张图片：人物外貌特征、身材特点、服装、表情、姿态、拍摄风格、背景等关键视觉元素"
                    )
                    if analysis.get('success'):
                        reference_description = analysis.get('content', '')
                        logger.info(f"参考图片分析完成: {reference_description[:100]}...")
                except Exception as e:
                    logger.warning(f"分析参考图片失败: {e}")
            
            # 生成中文提示词
            chinese_prompt = PromptManager.female_fan_image_prompt(
                match_info=match_info,
                team_side=team_side,
                reference_image_description=reference_description
            )
            
            # 用AI转换为英文提示词
            english_prompt = self._generate_prompt_with_ai(ai_model, chinese_prompt, match_info)
            
            # 根据模型生成图片
            if image_model == "gemini":
                return self._generate_with_gemini(english_prompt, reference_image_path)
            elif image_model == "dashscope":
                if dashscope_params is None:
                    dashscope_params = {}
                dashscope_params['positive_prompt'] = english_prompt
                return self._generate_with_dashscope_v2("", "", dashscope_params)
            else:
                logger.error(f"不支持的生图模型: {image_model}")
                return None
                
        except Exception as e:
            logger.error(f"生成女球迷照片时发生错误: {str(e)}")
            return None
    
    def generate_article_image(self, title: str, description: str = "", image_model: str = "gemini", 
                             article_content: str = "", ai_model: str = "gemini", 
                             image_index: int = 1, total_images: int = 1,
                             dashscope_params: dict = None,
                             user_custom_prompt: str = "") -> Optional[str]:
        """
        生成文章配图
        :param title: 文章标题
        :param description: 文章描述
        :param image_model: 生图模型 (gemini, deepseek, dashscope, pexels)
        :param article_content: 文章内容（用于Pexels搜索的AI提示词生成）
        :param ai_model: AI模型 (gemini, deepseek, dashscope) - 用于Pexels搜索提示词生成
        :param image_index: 当前图片索引（从1开始）
        :param total_images: 总图片数量
        :param dashscope_params: dict，阿里云百炼生图专用参数
        :param user_custom_prompt: str，用户自定义生图提示词
        :return: 图片文件路径
        """
        try:
            logger.info(f"开始生成文章配图，标题: {title}, 生图模型: {image_model}, AI模型: {ai_model}, 图片索引: {image_index}/{total_images}")
            # 推荐逻辑：阿里云百炼/Coze如无正向提示词和自定义提示词，则用PromptManager.image_prompt_with_style生成完整提示词
            if image_model in ["dashscope", "coze"]:
                # 优先用用户输入
                final_prompt = user_custom_prompt or (dashscope_params.get('positive_prompt') if dashscope_params else None)
                if not final_prompt:
                    final_prompt = PromptManager.image_prompt_with_style(title, description, user_custom_prompt)
            else:
                final_prompt = PromptManager.image_prompt_with_style(title, description, user_custom_prompt)
            if image_model == "gemini":
                # final_prompt 可能是中文或英文，需要转换为英文
                if user_custom_prompt:
                    # 如果用户提供了自定义提示词，直接使用
                    english_prompt = user_custom_prompt
                else:
                    # 否则用AI转换为英文
                    english_prompt = self._generate_prompt_with_ai(ai_model, final_prompt)
                return self._generate_with_gemini(english_prompt)
            elif image_model == "deepseek":
                return self._generate_with_deepseek(final_prompt)
            elif image_model == "dashscope":
                # 新增：支持 dashscope_params，正向提示词用统一拼接
                if dashscope_params is None:
                    dashscope_params = {}
                dashscope_params['positive_prompt'] = final_prompt
                return self._generate_with_dashscope_v2(title, description, dashscope_params)
            # Pexels和Coze功能已移除
            else:
                logger.error(f"不支持的生图模型: {image_model}")
                return None
        except Exception as e:
            logger.error(f"生成文章配图时发生错误: {str(e)}")
            return None
    
    def _generate_with_gemini(self, prompt: str, reference_image_path: str = None) -> Optional[str]:
        """
        使用Gemini生成图片
        
        :param prompt: 英文提示词
        :param reference_image_path: 参考图片路径（可选）
        :return: 图片文件路径
        """
        try:
            client = self._get_gemini_client()
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"article_gemini_{timestamp}.jpg"
            image_path = os.path.join(self.cache_folder, filename)
            
            logger.debug(f"Gemini图片保存路径: {image_path}")
            
            # 构建内容列表
            contents = [prompt]
            
            # 如果提供参考图片，添加到内容中
            if reference_image_path and os.path.exists(reference_image_path):
                try:
                    with open(reference_image_path, 'rb') as f:
                        image_data = f.read()
                    contents.append(types.Image.from_bytes(image_data))
                    logger.info(f"已添加参考图片: {reference_image_path}")
                except Exception as e:
                    logger.warning(f"加载参考图片失败: {e}")
            
            response = client.models.generate_content(
                model=AppConfig.GEMINI_IMAGE_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=['TEXT', 'IMAGE']
                )
            )
            
            if not response.candidates:
                logger.error("Gemini图片生成失败，无候选结果")
                return None
            
            content = response.candidates[0].content
            if not content or not content.parts:
                logger.error("Gemini图片生成失败，无内容部分")
                return None
            
            # 查找并保存图片数据
            image_saved = False
            for part in content.parts:
                if part.text:
                    logger.info(f"Gemini图片生成描述: {part.text}")
                elif part.inline_data and part.inline_data.data:
                    with open(image_path, 'wb') as f:
                        f.write(part.inline_data.data)
                    logger.info(f"Gemini文章配图生成成功: {image_path}")
                    image_saved = True
                    break
            
            if image_saved:
                return image_path
            else:
                logger.error("Gemini图片生成失败，未找到图片数据")
                return None
            
        except Exception as e:
            logger.error(f"Gemini生成文章配图时发生错误: {str(e)}")
            return None
    
    def _generate_with_deepseek(self, title: str, description: str = "") -> Optional[str]:
        """使用DeepSeek生成图片"""
        try:
            # 这里需要实现DeepSeek的图片生成API调用
            # 由于DeepSeek的图片生成API可能还在开发中，暂时返回None
            logger.warning("DeepSeek图片生成功能暂未实现")
            return None
            
        except Exception as e:
            logger.error(f"DeepSeek生成文章配图时发生错误: {str(e)}")
            return None
    
    def _generate_with_dashscope(self, title: str, description: str = "") -> Optional[str]:
        """使用阿里云百炼生成图片"""
        try:
            # 这里需要实现阿里云百炼的图片生成API调用
            # 由于阿里云百炼的图片生成API可能还在开发中，暂时返回None
            logger.warning("阿里云百炼图片生成功能暂未实现")
            return None
            
        except Exception as e:
            logger.error(f"阿里云百炼生成文章配图时发生错误: {str(e)}")
            return None
    
    # Coze功能已移除
    
    def _generate_with_dashscope_v2(self, title: str, description: str = "", dashscope_params: dict = None) -> Optional[str]:
        """新版：使用阿里云百炼SDK生成图片，支持正/反向提示词、图片比例、采样步数等参数"""
        try:
            import dashscope
            from dashscope import ImageSynthesis
            from http import HTTPStatus
            from urllib.parse import urlparse, unquote
            from pathlib import PurePosixPath
            # 参数准备
            if not dashscope_params:
                logger.error("未传递阿里云百炼生图参数")
                return None
            model_name = dashscope_params.get('model_name')
            positive_prompt = dashscope_params.get('positive_prompt') or title
            # 默认反向提示词
            negative_prompt = dashscope_params.get('negative_prompt')
            if not negative_prompt:
                negative_prompt = "模糊, 低质量, 扭曲, 失真, 过曝, 过暗, 低分辨率, artifact, blurry, bad anatomy, bad hands, watermark, signature, text, cropped, worst quality, low quality, jpeg artifacts"
            # 默认图片比例
            size = dashscope_params.get('size') or '1024*768'  # 4:3
            # 默认采样步数
            steps = dashscope_params.get('steps')
            if steps is None:
                steps = 25
            num_images = dashscope_params.get('num_images', 1)
            seed = dashscope_params.get('seed')
            guidance_scale = dashscope_params.get('guidance_scale')
            output_dir = self.cache_folder
            api_key = os.environ.get("DASHSCOPE_API_KEY")
            if not api_key:
                logger.error("未设置 DASHSCOPE_API_KEY 环境变量")
                return None
            params = {
                "api_key": api_key,
                "model": model_name,
                "prompt": positive_prompt,
                "n": num_images,
                "size": size,
            }
            if negative_prompt:
                params["negative_prompt"] = negative_prompt
            if steps is not None:
                params["steps"] = steps
            if seed is not None:
                params["seed"] = seed
            if guidance_scale is not None:
                params["guidance"] = guidance_scale
            logger.info(f"DashScope生图参数: {params}")
            try:
                rsp = ImageSynthesis.call(**params)
                logger.info(f"DashScope同步调用响应: {rsp}")
                if rsp.status_code == HTTPStatus.OK:
                    if not os.path.exists(output_dir):
                        os.makedirs(output_dir)
                    downloaded_urls = []
                    for result in rsp.output.results:
                        file_name = PurePosixPath(unquote(urlparse(result.url).path)).parts[-1]
                        file_path = os.path.join(output_dir, file_name)
                        try:
                            with open(file_path, 'wb+') as f:
                                f.write(requests.get(result.url).content)
                            logger.info(f"图片已保存到: {file_path}")
                            downloaded_urls.append(file_path)
                        except Exception as e:
                            logger.error(f"下载图片 {result.url} 失败: {e}")
                    if downloaded_urls:
                        return downloaded_urls[0]  # 只返回第一张
                    else:
                        logger.error("DashScope图片下载失败")
                        return None
                else:
                    logger.error(f"DashScope同步调用失败, 状态码: {rsp.status_code}, 错误码: {getattr(rsp, 'code', None)}, 消息: {getattr(rsp, 'message', None)}")
                    return None
            except Exception as e:
                logger.error(f"DashScope同步调用发生异常: {e}")
                return None
        except Exception as e:
            logger.error(f"阿里云百炼生成文章配图时发生错误: {str(e)}")
            return None
    
    # Pexels功能已移除
    
    # Pexels相关AI搜索功能已移除
    
    # Pexels相关辅助功能已移除
    
    # Pexels相关AI功能已移除
    
    # Pexels相关AI功能已移除
    
    # Pexels相关AI功能已移除
    
    # Pexels相关辅助功能已移除
    
    # Pexels相关辅助功能已移除
    
    # Pexels相关辅助功能已移除
    
    def validate_image_file(self, image_path: str) -> bool:
        """
        验证图片文件
        :param image_path: 图片路径
        :return: 验证结果
        """
        try:
            if not os.path.exists(image_path):
                logger.error(f"图片文件不存在: {image_path}")
                return False
            
            file_size = os.path.getsize(image_path)
            if file_size == 0:
                logger.error(f"图片文件为空: {image_path}")
                return False
            
            # 检查文件大小（微信限制10MB）
            max_size = 10 * 1024 * 1024  # 10MB
            if file_size > max_size:
                logger.error(f"图片文件过大: {file_size} bytes, 最大限制: {max_size} bytes")
                return False
            
            logger.info(f"图片文件验证通过: {image_path}, 大小: {file_size} bytes")
            return True
            
        except Exception as e:
            logger.error(f"验证图片文件时发生错误: {str(e)}")
            return False
    
    def get_image_info(self, image_path: str) -> Dict[str, Any]:
        """
        获取图片信息
        :param image_path: 图片路径
        :return: 图片信息
        """
        try:
            if not os.path.exists(image_path):
                return {'exists': False}
            
            file_size = os.path.getsize(image_path)
            file_name = os.path.basename(image_path)
            
            return {
                'exists': True,
                'file_name': file_name,
                'file_size': file_size,
                'file_size_mb': round(file_size / (1024 * 1024), 2),
                'full_path': image_path,
                'relative_path': os.path.relpath(image_path, '.'),
                'created_time': datetime.fromtimestamp(os.path.getctime(image_path)).strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            logger.error(f"获取图片信息时发生错误: {str(e)}")
            return {'exists': False, 'error': str(e)}
    
    def cleanup_old_images(self, days: int = 7) -> int:
        """
        清理旧图片文件
        :param days: 保留天数
        :return: 清理的文件数量
        """
        try:
            if not os.path.exists(self.cache_folder):
                return 0
            
            import time
            current_time = time.time()
            cutoff_time = current_time - (days * 24 * 60 * 60)
            
            cleaned_count = 0
            for filename in os.listdir(self.cache_folder):
                if filename.startswith('article_') and filename.endswith('.jpg'):
                    file_path = os.path.join(self.cache_folder, filename)
                    if os.path.getmtime(file_path) < cutoff_time:
                        os.remove(file_path)
                        cleaned_count += 1
                        logger.info(f"删除旧图片: {filename}")
            
            logger.info(f"清理完成，删除了 {cleaned_count} 个旧图片文件")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"清理旧图片时发生错误: {str(e)}")
            return 0
    
    def get_cache_folder_info(self) -> Dict[str, Any]:
        """
        获取缓存文件夹信息
        :return: 文件夹信息
        """
        try:
            if not os.path.exists(self.cache_folder):
                return {'exists': False}
            
            files = []
            total_size = 0
            
            for filename in os.listdir(self.cache_folder):
                file_path = os.path.join(self.cache_folder, filename)
                if os.path.isfile(file_path):
                    file_size = os.path.getsize(file_path)
                    total_size += file_size
                    files.append({
                        'name': filename,
                        'size': file_size,
                        'modified': datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S')
                    })
            
            return {
                'exists': True,
                'file_count': len(files),
                'total_size': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'files': files
            }
            
        except Exception as e:
            logger.error(f"获取缓存文件夹信息时发生错误: {str(e)}")
            return {'exists': False, 'error': str(e)}
    
    def _process_images_in_content(self, content: str, title: str, description: str, image_count: int, image_model: str = "gemini", ai_model: str = "gemini", custom_image_prompt: str = "", dashscope_params: dict = None, dashscope_image_model_code: str = "") -> str:
        try:
            logger.info(f"开始处理文章配图，计划生成{image_count}张图片（仅本地路径，不上传微信）")
            paragraphs = content.split('</p>')
            total_paragraphs = len(paragraphs)
            if total_paragraphs < 2 or image_count < 1:
                logger.warning("文章段落过少或配图数量小于1，跳过配图插入")
                return content
            if image_count >= total_paragraphs:
                insert_positions = list(range(1, total_paragraphs))[:image_count]
            else:
                insert_positions = [round((i + 1) * total_paragraphs / (image_count + 1)) for i in range(image_count)]
            logger.info(f"计划在第{insert_positions}段后插入配图")
            generated_images = []
            if dashscope_params is None:
                dashscope_params = {}
            for i, position in enumerate(insert_positions):
                try:
                    logger.info(f"生成第{i+1}张配图，使用模型: {image_model}")
                    # 1. 提取插图位置前100字+后100字内容
                    def extract_paragraph_content(paragraphs, pos, max_chars=100):
                        idx = max(0, pos-1)
                        text_before = paragraphs[idx] if idx < len(paragraphs) else ''
                        text_after = paragraphs[idx+1] if (idx+1) < len(paragraphs) else ''
                        import re
                        text_before = re.sub(r'<[^>]+>', '', text_before).strip()[:max_chars]
                        text_after = re.sub(r'<[^>]+>', '', text_after).strip()[:max_chars]
                        return text_before + (" " if text_before and text_after else "") + text_after
                    current_paragraph = extract_paragraph_content(paragraphs, position)
                    # 2. 拼接系统模板+用户风格
                    base_prompt = PromptManager.image_prompt_with_style(title, description, custom_image_prompt)
                    # 3. 拼接段落内容
                    full_prompt = f"{base_prompt}\n本段内容：{current_paragraph}"
                    # 4. 用AI大模型润色生成最终prompt（所有模型都适用）
                    ai_prompt = self._generate_prompt_with_ai(ai_model, full_prompt)
                    # dashscope模型ID优先用dashscope_params['model_name']，否则用dashscope_image_model_code
                    if image_model == 'dashscope':
                        if not dashscope_params.get('model_name') and dashscope_image_model_code:
                            dashscope_params['model_name'] = dashscope_image_model_code
                        if not dashscope_params.get('model_name'):
                            logger.error("阿里云百炼模型ID未传递")
                            return content
                    image_path = self.image_service.generate_article_image(
                        title=title,
                        description=description,
                        image_model=image_model,
                        article_content=content,
                        ai_model=ai_model,
                        image_index=i+1,
                        total_images=image_count,
                        dashscope_params=dashscope_params,
                        user_custom_prompt=ai_prompt
                    )
                    if image_path:
                        image_html = f'<img src="{image_path}" alt="文章配图" style="max-width: 100%; height: auto;">'
                        logger.info(f"第{i+1}张配图处理完成，使用本地路径: {image_path}")
                        generated_images.append({
                            'local_path': image_path,
                            'image_html': image_html,
                            'position': position
                        })
                    else:
                        logger.warning(f"第{i+1}张配图生成失败")
                except Exception as e:
                    logger.error(f"生成第{i+1}张配图时出错: {str(e)}")
            processed_content = content
            for img_info in sorted(generated_images, key=lambda x: -x['position']):
                position = img_info['position']
                image_html = f'<p style="text-align: center;">{img_info["image_html"]}</p>'
                parts = processed_content.split('</p>')
                if position < len(parts):
                    parts.insert(position, image_html)
                    processed_content = '</p>'.join(parts)
                    logger.info(f"在第{position}段后插入配图")
            logger.info(f"配图处理完成，共插入{len(generated_images)}张图片")
            return processed_content
        except Exception as e:
            logger.error(f"处理配图时发生错误: {str(e)}")
            return content  # 出错时返回原始内容
    
    def _generate_prompt_with_ai(self, ai_model, prompt, match_info=None):
        """
        用指定AI大模型润色/扩写生图提示词
        增强版：针对体育文章，确保输出包含两个球队元素
        
        :param ai_model: AI模型名称
        :param prompt: 中文提示词
        :param match_info: 比赛信息（可选，用于增强提示词）
        :return: 英文生图提示词
        """
        try:
            # 如果是体育文章，增强提示词要求
            enhanced_prompt = prompt
            if match_info:
                home_team = match_info.get('home_team', '')
                away_team = match_info.get('away_team', '')
                if home_team and away_team:
                    enhanced_prompt = f"""{prompt}

重要提醒：
- 必须确保图片包含两个球队的元素：{home_team} 和 {away_team}
- 如果提示包含女球迷，必须同时包含穿着两个球队球衣的女球迷
- 图片必须展现两队对抗的视觉效果
- 使用专业的美术术语，确保提示词详细且具体"""
            
            # 添加输出格式要求
            final_prompt = f"""请将以下中文图片生成需求转换为专业的英文图片生成提示词（prompt）。

{enhanced_prompt}

输出要求：
1. **必须使用英文输出**
2. **格式**：主体描述, 风格描述, 色彩描述, 构图描述, 氛围描述, 质量要求
3. **关键元素必须包含**：
   - 两个球队的球员形象（如果适用）
   - 女球迷元素（如果原提示要求）
   - 体育竞技感
4. **使用专业术语**：使用专业的美术、摄影、设计术语
5. **提示词长度**：80-120个英文单词
6. **不要包含**：markdown标记、代码块、引号等格式符号

示例格式：
"Professional sports poster, two football teams players in action, beautiful female fans wearing team jerseys, modern minimalist design, team colors, dynamic split-screen composition, competitive atmosphere, high quality, detailed, 4k, suitable for WeChat article cover"

请直接输出英文提示词，不要包含任何其他说明文字、markdown标记或引号："""
            
            if ai_model == 'gemini':
                from services.gemini_service import GeminiService
                gemini = GeminiService()
                ai_output = gemini.generate_content(final_prompt)
            elif ai_model == 'deepseek':
                from services.deepseek_service import DeepSeekService
                deepseek = DeepSeekService()
                ai_output = deepseek.generate_content(final_prompt)
            else:
                return prompt
            
            # 清理输出（移除可能的markdown标记、引号等）
            cleaned_output = ai_output.strip()
            # 移除代码块标记
            if cleaned_output.startswith('```'):
                lines = cleaned_output.split('\n')
                cleaned_output = '\n'.join(lines[1:-1]) if len(lines) > 2 else cleaned_output
            # 移除引号
            if cleaned_output.startswith('"') and cleaned_output.endswith('"'):
                cleaned_output = cleaned_output[1:-1]
            if cleaned_output.startswith("'") and cleaned_output.endswith("'"):
                cleaned_output = cleaned_output[1:-1]
            # 移除多余的说明文字
            if '提示词' in cleaned_output or 'prompt' in cleaned_output.lower():
                # 尝试提取引号内的内容
                import re
                quoted = re.search(r'["\']([^"\']+)["\']', cleaned_output)
                if quoted:
                    cleaned_output = quoted.group(1)
            
            logger.info(f"AI润色后的英文提示词: {cleaned_output[:100]}...")
            return cleaned_output.strip()
            
        except Exception as e:
            logger.error(f"AI大模型润色prompt失败: {str(e)}")
            return prompt